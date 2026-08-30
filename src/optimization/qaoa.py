"""
Quantum Approximate Optimization Algorithm (QAOA) implementation.

Imported from qOptiSolve (migration_inbox/qOptiSolve/src/qoptisolve/qaoa.py).

# SIMULATION ONLY — this module uses Qiskit Aer simulator, not real quantum hardware.
"""

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit_aer import Aer
from qiskit.circuit import Parameter
from typing import Dict, List, Tuple, Callable, Optional, TYPE_CHECKING

# Optimizers location differs across Qiskit versions; provide robust imports with fallbacks
try:  # Qiskit Algorithms as separate package (newer)
    from qiskit_algorithms.optimizers import SPSA, COBYLA  # type: ignore
except Exception:  # Older Qiskit (pre-1.0)
    try:
        from qiskit.algorithms.optimizers import SPSA, COBYLA  # type: ignore
    except Exception:
        try:
            from scipy.optimize import minimize  # type: ignore
        except Exception:  # pragma: no cover
            minimize = None  # type: ignore

        class COBYLA:  # type: ignore
            def __init__(self, maxiter: int = 100):
                self.maxiter = maxiter

            def minimize(self, fun: Callable[[np.ndarray], float], x0: np.ndarray):
                if minimize is None:
                    best_x = np.array(x0, dtype=float)
                    best_val = float(fun(best_x))
                    for i in range(self.maxiter):
                        candidate = best_x + np.random.uniform(-0.1, 0.1, size=best_x.shape)
                        val = float(fun(candidate))
                        if val < best_val:
                            best_x, best_val = candidate, val
                    return type("Result", (), {"x": best_x, "fun": best_val, "nfev": self.maxiter})
                res = minimize(fun, x0, method="COBYLA", options={"maxiter": self.maxiter})  # type: ignore
                return res

        class SPSA:  # type: ignore
            def __init__(self, maxiter: int = 100):
                self.maxiter = maxiter

            def minimize(self, fun: Callable[[np.ndarray], float], x0: np.ndarray):
                best_x = np.array(x0, dtype=float)
                best_val = float(fun(best_x))
                for i in range(self.maxiter):
                    step = np.random.uniform(-0.2, 0.2, size=best_x.shape)
                    candidate = best_x + step
                    val = float(fun(candidate))
                    if val < best_val:
                        best_x, best_val = candidate, val
                return type("Result", (), {"x": best_x, "fun": best_val, "nfev": self.maxiter})

if TYPE_CHECKING:
    from .problems import PortfolioProblem, MaxCutProblem


class QAOA:
    """Quantum Approximate Optimization Algorithm implementation.

    # SIMULATION ONLY — uses Qiskit Aer simulator backend.
    """

    def __init__(self, backend_name: str = 'qasm_simulator', shots: int = 1000):
        """
        Initialize QAOA solver.

        Args:
            backend_name: Quantum backend to use
            shots: Number of shots for measurement
        """
        self.backend_name = backend_name
        self.shots = shots
        self.backend = Aer.get_backend(backend_name)

    def create_portfolio_circuit(self, problem: 'PortfolioProblem', p: int = 1) -> QuantumCircuit:
        """
        Create QAOA circuit for portfolio optimization.

        Args:
            problem: Portfolio problem instance
            p: QAOA depth parameter

        Returns:
            Quantum circuit implementing QAOA
        """
        n_qubits = problem.n_assets

        # No explicit classical register: measure_all() adds its own ("meas").
        # Declaring one here as well produced a circuit with 2n clbits, only n
        # of which were ever written, and a counts key of the form "1000 0000".
        # _bits_from_counts_key strips the space and takes the first n bits of
        # the reversed string -- which was the never-written register. Every
        # outcome decoded to all-zeros. See tests/test_qaoa_oracle.py.
        qc = QuantumCircuit(n_qubits)
        qc.h(range(n_qubits))

        for layer in range(p):
            gamma = Parameter(f'γ_{layer}')
            self._add_portfolio_cost_hamiltonian(qc, problem, gamma)

            beta = Parameter(f'β_{layer}')
            self._add_mixing_hamiltonian(qc, beta)

        qc.measure_all()

        return qc

    def create_maxcut_circuit(self, problem: 'MaxCutProblem', p: int = 1) -> QuantumCircuit:
        """
        Create QAOA circuit for Max-Cut problem.

        Args:
            problem: Max-Cut problem instance
            p: QAOA depth parameter

        Returns:
            Quantum circuit implementing QAOA
        """
        n_qubits = problem.n_nodes

        # See create_portfolio_circuit: measure_all() supplies the register.
        qc = QuantumCircuit(n_qubits)
        qc.h(range(n_qubits))

        for layer in range(p):
            gamma = Parameter(f'γ_{layer}')
            self._add_maxcut_cost_hamiltonian(qc, problem, gamma)

            beta = Parameter(f'β_{layer}')
            self._add_mixing_hamiltonian(qc, beta)

        qc.measure_all()

        return qc

    def _add_portfolio_cost_hamiltonian(self, qc: QuantumCircuit, problem: 'PortfolioProblem', gamma: Parameter):
        """Add portfolio cost Hamiltonian to circuit."""
        n_assets = problem.n_assets

        for i in range(n_assets):
            for j in range(n_assets):
                if i != j:
                    scalar_coeff = float(problem.covariances[i, j]) / 2.0
                    if abs(scalar_coeff) > 1e-6:
                        angle_ij = scalar_coeff * gamma
                        qc.rz(angle_ij, i)
                        qc.cx(i, j)
                        qc.rz(angle_ij, j)
                        qc.cx(i, j)

    def _add_maxcut_cost_hamiltonian(self, qc: QuantumCircuit, problem: 'MaxCutProblem', gamma: Parameter):
        """Add Max-Cut cost Hamiltonian to circuit."""
        for (i, j), weight in zip(problem.edges, problem.weights):
            qc.cx(i, j)
            qc.rz(weight * gamma, j)
            qc.cx(i, j)

    def _add_mixing_hamiltonian(self, qc: QuantumCircuit, beta: Parameter):
        """Add mixing Hamiltonian to circuit."""
        n_qubits = qc.num_qubits
        for i in range(n_qubits):
            qc.rx(2 * beta, i)

    def _bits_from_counts_key(self, key: str, num_qubits: int) -> np.ndarray:
        """Convert a Qiskit counts key to a bit array indexed by qubit.

        Qiskit writes the key most-significant-qubit first, so it is reversed
        here to give bits[i] == the measurement of qubit i.

        Refuses a key carrying more than one classical register rather than
        silently reading the wrong one. That is not hypothetical: these
        circuits used to declare a classical register *and* call measure_all(),
        which adds a second. The key was then "1000 0000", the space was
        stripped, and the first n bits of the reversed string came from the
        register that was never written -- so every outcome decoded to
        all-zeros, and solve_maxcut reported cut_value 0.0 with a converged
        optimiser on a graph whose optimum is 4.
        """
        if ' ' in key.strip():
            raise ValueError(
                f"counts key {key!r} spans more than one classical register. "
                "Build the circuit with a single register (measure_all() adds "
                "one) -- concatenating them here silently reads the wrong bits.")
        sanitized = key.strip()
        if len(sanitized) < num_qubits:
            sanitized = sanitized.zfill(num_qubits)
        if len(sanitized) != num_qubits:
            raise ValueError(
                f"counts key {key!r} has {len(sanitized)} bits, expected "
                f"{num_qubits}")
        ordered = sanitized[::-1]
        return np.fromiter((1 if ch == '1' else 0 for ch in ordered),
                           dtype=int, count=num_qubits)

    def solve_portfolio(self, problem: 'PortfolioProblem', p: int = 1,
                        optimizer: str = 'SPSA', max_iter: int = 100) -> Dict:
        """
        Solve portfolio optimization using QAOA.

        Args:
            problem: Portfolio problem instance
            p: QAOA depth parameter
            optimizer: Optimization algorithm to use
            max_iter: Maximum optimization iterations

        Returns:
            Dictionary with solution and metadata
        """
        qc = self.create_portfolio_circuit(problem, p)
        param_list = list(qc.parameters)

        def cost_function(params):
            bound_qc = qc.assign_parameters({par: float(val) for par, val in zip(param_list, params)}, inplace=False)
            compiled = transpile(bound_qc, self.backend)
            job = self.backend.run(compiled, shots=self.shots)
            result = job.result()
            counts = result.get_counts()

            total_cost = 0
            total_shots = 0

            for bitstring, count in counts.items():
                allocation = self._bits_from_counts_key(bitstring, problem.n_assets)
                portfolio_return = np.dot(allocation, problem.returns)
                portfolio_risk = np.sqrt(allocation.T @ problem.covariances @ allocation)
                cost = -portfolio_return / (portfolio_risk + 1e-6)
                total_cost += cost * count
                total_shots += count

            return total_cost / total_shots

        if optimizer == 'SPSA':
            opt = SPSA(maxiter=max_iter)
        elif optimizer == 'COBYLA':
            opt = COBYLA(maxiter=max_iter)
        else:
            raise ValueError(f"Unknown optimizer: {optimizer}")

        n_params = 2 * p
        initial_params = np.random.uniform(0, 2 * np.pi, n_params)

        result = opt.minimize(cost_function, initial_params)

        final_qc = qc.assign_parameters({par: float(val) for par, val in zip(param_list, result.x)}, inplace=False)
        final_compiled = transpile(final_qc, self.backend)
        final_job = self.backend.run(final_compiled, shots=self.shots)
        final_result = final_job.result()
        final_counts = final_result.get_counts()

        def portfolio_cost_from_bits(bits: np.ndarray) -> float:
            portfolio_return = float(np.dot(bits, problem.returns))
            portfolio_risk = float(np.sqrt(max(0.0, bits.T @ problem.covariances @ bits)))
            return -(portfolio_return) / (portfolio_risk + 1e-6)

        best_allocation = None
        best_cost = float("inf")
        for bitstring, _count in final_counts.items():
            alloc = self._bits_from_counts_key(bitstring, problem.n_assets)
            cost_val = portfolio_cost_from_bits(alloc)
            if cost_val < best_cost:
                best_cost = cost_val
                best_allocation = alloc

        return {
            'allocation': best_allocation,
            'optimal_params': result.x,
            'final_cost': best_cost,
            'convergence': result.nfev,
            'circuit': final_qc,
            'counts': final_counts
        }

    def solve_maxcut(self, problem: 'MaxCutProblem', p: int = 1,
                     optimizer: str = 'SPSA', max_iter: int = 100) -> Dict:
        """
        Solve Max-Cut problem using QAOA.

        Args:
            problem: Max-Cut problem instance
            p: QAOA depth parameter
            optimizer: Optimization algorithm to use
            max_iter: Maximum optimization iterations

        Returns:
            Dictionary with solution and metadata
        """
        qc = self.create_maxcut_circuit(problem, p)
        param_list = list(qc.parameters)

        def cost_function(params):
            bound_qc = qc.assign_parameters({par: float(val) for par, val in zip(param_list, params)}, inplace=False)
            compiled = transpile(bound_qc, self.backend)
            job = self.backend.run(compiled, shots=self.shots)
            result = job.result()
            counts = result.get_counts()

            total_cost = 0
            total_shots = 0

            for bitstring, count in counts.items():
                partition = self._bits_from_counts_key(bitstring, problem.n_nodes)
                cut_value = 0
                for (i, j), weight in zip(problem.edges, problem.weights):
                    if partition[i] != partition[j]:
                        cut_value += weight
                total_cost += cut_value * count
                total_shots += count

            return -total_cost / total_shots

        if optimizer == 'SPSA':
            opt = SPSA(maxiter=max_iter)
        elif optimizer == 'COBYLA':
            opt = COBYLA(maxiter=max_iter)
        else:
            raise ValueError(f"Unknown optimizer: {optimizer}")

        n_params = 2 * p
        initial_params = np.random.uniform(0, 2 * np.pi, n_params)

        result = opt.minimize(cost_function, initial_params)

        final_qc = qc.assign_parameters({par: float(val) for par, val in zip(param_list, result.x)}, inplace=False)
        final_compiled = transpile(final_qc, self.backend)
        final_job = self.backend.run(final_compiled, shots=self.shots)
        final_result = final_job.result()
        final_counts = final_result.get_counts()

        def cut_value_from_bits(bits: np.ndarray) -> float:
            value = 0.0
            for (i, j), weight in zip(problem.edges, problem.weights):
                if bits[i] != bits[j]:
                    value += weight
            return float(value)

        best_partition = None
        best_cut = float("-inf")
        for bitstring, _count in final_counts.items():
            part = self._bits_from_counts_key(bitstring, problem.n_nodes)
            value = cut_value_from_bits(part)
            if value > best_cut:
                best_cut = value
                best_partition = part

        return {
            'partition': best_partition,
            'cut_value': best_cut,
            'optimal_params': result.x,
            'final_cost': -result.fun,
            'convergence': result.nfev,
            'circuit': final_qc,
            'counts': final_counts
        }
