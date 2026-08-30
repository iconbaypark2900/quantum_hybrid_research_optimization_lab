"""Oracle tests for the QAOA solver.

This file exists because `src/optimization/qaoa.py` was the only real quantum
solver in the repository and nothing tested or called it. When it was finally
run, it did not work:

    exact optimum on a 4-cycle : 4.0
    QAOA reported              : cut_value 0.0, partition [0 0 0 0], converged

The circuits were built as `QuantumCircuit(n, n)` and then measured with
`measure_all()`, which adds a *second* classical register. The counts key was
therefore "1000 0000" -- the measured register, then the one that was never
written. `_bits_from_counts_key` stripped the space and took the first n bits
of the reversed string, which came from the empty register. Every outcome
decoded to all-zeros, so every sampled partition scored a cut of 0, the
optimiser saw a flat landscape, and the result object came back complete and
confident.

Nothing about that failure is visible from the outside: the dict has the right
keys, the value is a float, and `convergence` reports iterations. It is the
same shape as the two failures already recorded in SCAFFOLDING.md -- a
plausible result over a computation that never happened.

The tests below are therefore built on oracles, not shape:

  - a prepared basis state has a known measurement, so the decoder can be
    checked deterministically with no sampling at all;
  - small graphs have hand-computable optima;
  - `ClassicalMaxCutSolver` is exact and already verified against brute force.
"""
import sys
from pathlib import Path

import numpy as np
import pytest
from qiskit import QuantumCircuit, transpile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.optimization.classical import ClassicalMaxCutSolver  # noqa: E402
from src.optimization.problems import MaxCutProblem, create_sample_maxcut  # noqa: E402
from src.optimization.qaoa import QAOA  # noqa: E402

FOUR_CYCLE = [(0, 1), (1, 2), (2, 3), (3, 0)]   # bipartite: all 4 edges cut
TRIANGLE = [(0, 1), (1, 2), (2, 0)]             # odd cycle: at most 2 cut


def cut_of(partition, problem) -> float:
    return float(sum(w for (i, j), w in zip(problem.edges, problem.weights)
                     if partition[i] != partition[j]))


# --- the regression: one classical register, not two ----------------------

@pytest.mark.parametrize("depth", [1, 2])
def test_circuit_has_exactly_one_classical_register(depth):
    """Two registers is the bug. The counts key then spans both."""
    qc = QAOA().create_maxcut_circuit(MaxCutProblem(edges=FOUR_CYCLE), p=depth)
    assert len(qc.cregs) == 1, [r.name for r in qc.cregs]
    assert qc.num_clbits == qc.num_qubits


def test_counts_keys_do_not_span_registers():
    q = QAOA(shots=64)
    problem = MaxCutProblem(edges=FOUR_CYCLE)
    qc = q.create_maxcut_circuit(problem, p=1)
    bound = qc.assign_parameters({p: 0.7 for p in qc.parameters})
    counts = q.backend.run(transpile(bound, q.backend), shots=64).result().get_counts()
    for key in counts:
        assert " " not in key.strip(), f"counts key {key!r} spans registers"


# --- the decoder, checked without any sampling ----------------------------

@pytest.mark.parametrize("bits", [
    (0, 0, 0, 0), (1, 0, 0, 0), (0, 0, 0, 1), (1, 0, 1, 0), (0, 1, 1, 0), (1, 1, 1, 1),
])
def test_decoder_round_trips_a_prepared_basis_state(bits):
    """Prepare |bits>, measure it, and require the decoder to return `bits`.

    This is the sharpest available oracle: the state is deterministic, so any
    disagreement is the decoder's, not the sampler's. Asymmetric patterns are
    included deliberately -- a reversed decoder round-trips 0000 and 1111 and
    fails only on the asymmetric ones.
    """
    q = QAOA(shots=32)
    n = len(bits)
    qc = QuantumCircuit(n)
    for i, b in enumerate(bits):
        if b:
            qc.x(i)
    qc.measure_all()

    counts = q.backend.run(transpile(qc, q.backend), shots=32).result().get_counts()
    assert len(counts) == 1, counts
    decoded = q._bits_from_counts_key(next(iter(counts)), n)
    assert tuple(int(v) for v in decoded) == bits


def test_decoder_refuses_a_key_spanning_two_registers():
    """It used to silently read the wrong register instead."""
    with pytest.raises(ValueError, match="more than one classical register"):
        QAOA()._bits_from_counts_key("1000 0000", 4)


def test_decoder_refuses_a_key_of_the_wrong_width():
    with pytest.raises(ValueError, match="expected"):
        QAOA()._bits_from_counts_key("10101", 4)


# --- circuit structure must encode the problem ----------------------------

@pytest.mark.parametrize("depth", [1, 2, 3])
def test_cost_and_mixer_layers_scale_with_depth_and_edges(depth):
    """p cost layers of |E| ZZ blocks each, and p mixer layers of n rotations.

    A cost layer that stopped encoding the graph -- dropping edges, or ignoring
    depth -- changes these counts.
    """
    problem = MaxCutProblem(edges=FOUR_CYCLE)
    qc = QAOA().create_maxcut_circuit(problem, p=depth)
    ops = qc.count_ops()
    n, n_edges = problem.n_nodes, len(problem.edges)

    assert qc.num_qubits == n
    assert ops["cx"] == 2 * n_edges * depth   # each ZZ block is cx, rz, cx
    assert ops["rz"] == n_edges * depth
    assert ops["rx"] == n * depth
    assert ops["h"] == n
    assert len(qc.parameters) == 2 * depth


def test_every_edge_appears_in_the_cost_layer():
    """A path graph and a star on the same nodes must differ."""
    star = QAOA().create_maxcut_circuit(
        MaxCutProblem(edges=[(0, 1), (0, 2), (0, 3)]), p=1)
    path = QAOA().create_maxcut_circuit(
        MaxCutProblem(edges=[(0, 1), (1, 2), (2, 3)]), p=1)
    assert star.count_ops()["cx"] == path.count_ops()["cx"]
    # Same counts, different structure -- so compare the actual qubit pairs.
    pairs = lambda qc: sorted(tuple(qc.find_bit(b).index for b in inst.qubits)
                              for inst in qc.data if inst.operation.name == "cx")
    assert pairs(star) != pairs(path)


def test_gamma_zero_leaves_the_cost_layer_as_identity():
    """With gamma = 0 each ZZ block is cx . rz(0) . cx == identity.

    So the state before measurement is the uniform superposition the Hadamards
    made, mixed only by beta -- the graph has no influence at all.
    """
    q = QAOA(shots=4096)
    problem = MaxCutProblem(edges=FOUR_CYCLE)
    qc = q.create_maxcut_circuit(problem, p=1)
    binding = {p: (0.0 if p.name.startswith("γ") else 0.0) for p in qc.parameters}
    bound = qc.assign_parameters(binding)
    counts = q.backend.run(transpile(bound, q.backend), shots=4096).result().get_counts()

    # gamma = beta = 0 leaves H|0> on every qubit: uniform over 2**n.
    assert len(counts) == 2 ** problem.n_nodes
    expected = 4096 / 2 ** problem.n_nodes
    assert all(abs(c - expected) < expected * 0.6 for c in counts.values()), counts


# --- end to end, against known optima -------------------------------------

def test_qaoa_finds_the_four_cycle_optimum():
    problem = MaxCutProblem(edges=FOUR_CYCLE)
    result = QAOA(shots=1024).solve_maxcut(problem, p=1, max_iter=20)
    assert result["cut_value"] == pytest.approx(4.0)
    assert cut_of(result["partition"], problem) == pytest.approx(4.0)


def test_qaoa_cannot_beat_the_triangle_bound():
    """An odd cycle is not bipartite: 2 of 3, never 3."""
    problem = MaxCutProblem(edges=TRIANGLE)
    result = QAOA(shots=1024).solve_maxcut(problem, p=1, max_iter=20)
    assert result["cut_value"] == pytest.approx(2.0)


@pytest.mark.parametrize("n_nodes", [4, 5])
def test_qaoa_never_reports_more_than_the_exact_optimum(n_nodes):
    """The invariant that catches a decoder inventing cuts.

    A sampled heuristic may fall short; it must never exceed the optimum. When
    the decoder was broken this test would have passed -- 0.0 does not exceed
    anything -- which is why it is paired with the consistency check below.
    """
    problem = create_sample_maxcut(n_nodes=n_nodes, edge_prob=0.6)
    exact = ClassicalMaxCutSolver().solve(problem)
    assert exact["status"] == "optimal"

    result = QAOA(shots=1024).solve_maxcut(problem, p=1, max_iter=20)
    assert result["cut_value"] <= exact["cut_value"] + 1e-9


@pytest.mark.parametrize("n_nodes", [4, 5])
def test_reported_cut_matches_the_partition_it_reports(n_nodes):
    """Internal consistency: recompute the cut from the returned partition.

    This is what the all-zeros bug failed. It reported cut_value 0.0 with
    partition [0,0,0,0] -- consistent, but only because both were wrong -- so
    this is paired with the known-optimum tests above, which it could not pass.
    """
    problem = create_sample_maxcut(n_nodes=n_nodes, edge_prob=0.6)
    result = QAOA(shots=1024).solve_maxcut(problem, p=1, max_iter=20)

    partition = result["partition"]
    assert len(partition) == problem.n_nodes
    assert set(np.unique(partition)) <= {0, 1}
    assert result["cut_value"] == pytest.approx(cut_of(partition, problem))


def test_weighted_graph_is_not_treated_as_unweighted():
    """Uniform weights would pass every unweighted case above."""
    problem = MaxCutProblem(edges=[(0, 1), (1, 2)], weights=[5.0, 1.0])
    result = QAOA(shots=1024).solve_maxcut(problem, p=1, max_iter=20)
    assert result["cut_value"] == pytest.approx(6.0)


# --- the node-count fix this file also depends on -------------------------

@pytest.mark.parametrize("n_nodes,edge_prob", [(6, 0.2), (5, 0.3), (4, 0.2)])
def test_isolated_nodes_are_not_silently_dropped(n_nodes, edge_prob):
    """QAOA sizes its register from n_nodes, so losing a node loses a qubit.

    create_sample_maxcut(n_nodes=6, edge_prob=0.2) used to return a problem
    reporting 4 nodes, because n_nodes counted only nodes appearing in an edge.
    """
    problem = create_sample_maxcut(n_nodes=n_nodes, edge_prob=edge_prob)
    assert problem.n_nodes == n_nodes
    qc = QAOA().create_maxcut_circuit(problem, p=1)
    assert qc.num_qubits == n_nodes


def test_declared_node_count_cannot_contradict_the_edges():
    with pytest.raises(ValueError, match="num_nodes"):
        MaxCutProblem(edges=[(0, 5)], num_nodes=3)
