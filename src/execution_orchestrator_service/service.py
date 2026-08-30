"""
Execution Orchestrator Service Implementation
"""
import asyncio
import logging
from typing import Dict, Any, Optional
import numpy as np
from datetime import datetime


logger = logging.getLogger(__name__)


def _not_implemented(what: str, needs: str) -> "NotImplementedError":
    """Refuse loudly, and say what it would take to stop refusing."""
    return NotImplementedError(
        f"{what} is not implemented. What was here returned invented numbers "
        f"that a caller reads as measurements, which is worse than failing. "
        f"To implement it: {needs}")


def run_circuit(circuit=None, shots: int = 1024, **_kw):
    """Execute a circuit on Aer. Synchronous, and the single execution path.

    Extracted from `_simulate_quantum_execution` so the Mitiq PEC and CDR
    paths can share it. Mitiq executors are synchronous, and duplicating the
    noise model to satisfy them would put two definitions of "the noise" in
    this repository -- the drift it keeps closing everywhere else.
    """
    _kw = dict(_kw, circuit=circuit)
    import time

    from qiskit import QuantumCircuit, transpile
    from qiskit_aer import AerSimulator

    circuit = _kw.get("circuit")
    if circuit is None:
        raise ValueError(
            f"execute_circuit needs the circuit itself, not just id "
            f"{_kw.get('circuit_id')!r}. Pass circuit=<QuantumCircuit or QASM string>. "
            "This service stores no circuits, and fabricating one to match "
            "an id is exactly the behaviour this replaced.")
    if isinstance(circuit, str):
        circuit = QuantumCircuit.from_qasm_str(circuit)
    if not isinstance(circuit, QuantumCircuit):
        raise TypeError(f"circuit must be a QuantumCircuit or QASM string, "
                        f"got {type(circuit).__name__}")

    noise_model = None
    noise_level = _kw.get("noise_level")
    if noise_level:
        from qiskit_aer.noise import NoiseModel, depolarizing_error
        noise_model = NoiseModel()
        noise_model.add_all_qubit_quantum_error(
            depolarizing_error(float(noise_level), 1), ["u1", "u2", "u3", "rz", "sx", "x", "h"])
        noise_model.add_all_qubit_quantum_error(
            depolarizing_error(float(noise_level), 2), ["cx", "cz"])

    sim = AerSimulator(noise_model=noise_model)
    work = circuit.copy()
    if not work.cregs:
        work.measure_all()
    # optimization_level=0 is REQUIRED, not a tuning choice. The default
    # optimiser cancels adjacent inverse pairs, which is exactly what
    # unitary folding inserts: measured here, a Bell circuit folded to
    # lambda = 1, 3, 5, 7 transpiled to 5 operations and depth 3 in EVERY
    # case. Folding did nothing, noise was never amplified, and ZNE was
    # extrapolating three measurements of the same circuit — producing a
    # confident "mitigated" number from no information at all.
    #
    # Level 0 still performs basis translation and layout, which is all
    # that is needed to run.
    compiled = transpile(work, sim, optimization_level=int(_kw.get("optimization_level", 0)))

    t0 = time.perf_counter()
    job = sim.run(compiled, shots=shots)
    counts = job.result().get_counts()
    runtime = time.perf_counter() - t0

    total = sum(counts.values())
    probabilities = {state: c / total for state, c in counts.items()}

    return {
        "counts": dict(counts),
        "probabilities": probabilities,
        "shots_used": total,
        "qubit_count": circuit.num_qubits,
        "circuit_depth": circuit.depth(),
        # Measured, not sampled.
        "execution_time": runtime,
        "noise_level": float(noise_level) if noise_level else 0.0,
        "backend_info": {"backend_name": "aer_simulator",
                         "backend_type": "simulator",
                         "noise_model": bool(noise_model)},
    }



class ExecutionOrchestratorService:
    """Service for orchestrating quantum circuit execution on simulators and QPUs"""
    
    def __init__(self, host: str = "localhost", port: int = 8003, **kwargs):
        self.host = host
        self.port = port
        self.backends = {
            "simulator": {
                "type": "qiskit-aer",
                "backend": "aer_simulator",
                "available": True
            },
            "aer_simulator": {
                "type": "qiskit-aer",
                "backend": "aer_simulator",
                "available": True
            },
            "qasm_simulator": {
                "type": "qiskit",
                "backend": "qasm_simulator", 
                "available": True
            },
            "statevector_simulator": {
                "type": "qiskit",
                "backend": "statevector_simulator",
                "available": True
            }
        }
        self.executions = {}
        logger.info(f"Execution Orchestrator Service initialized on {host}:{port}")
    
    async def execute_circuit(self, circuit_id: str, backend: str = "simulator", shots: int = 1024, **kwargs) -> Dict[str, Any]:
        """Execute a quantum circuit on the specified backend"""
        logger.info(f"Executing circuit {circuit_id} on {backend} with {shots} shots")
        
        # Validate backend
        if backend not in self.backends:
            available_backends = list(self.backends.keys())
            return {
                "status": "failed",
                "error": f"Backend {backend} not available",
                "available_backends": available_backends,
                "message": f"Available backends: {', '.join(available_backends)}"
            }
        
        try:
            # For this implementation, we'll simulate execution since we don't have real backend connections
            # In a real implementation, this would interface with Qiskit, PennyLane, etc.
            execution_result = await self._simulate_quantum_execution(circuit_id, backend, shots, **kwargs)
            
            execution_id = f"exec_{hash(f'{circuit_id}_{backend}_{shots}') % 100000:05d}"
            
            # Store execution result
            self.executions[execution_id] = {
                "circuit_id": circuit_id,
                "backend": backend,
                "shots": shots,
                "result": execution_result,
                "executed_at": datetime.utcnow().isoformat(),
                "status": "completed"
            }
            
            logger.info(f"Execution {execution_id} completed on {backend}")
            
            return {
                "execution_id": execution_id,
                "circuit_id": circuit_id,
                "backend": backend,
                "shots": shots,
                "result": execution_result,
                "executed_at": datetime.utcnow().isoformat(),
                "status": "completed",
                "message": f"Circuit {circuit_id} executed successfully on {backend}"
            }
        
        except (NotImplementedError, ValueError, TypeError):
            # Must propagate. Swallowing these turns a loud refusal back into a
            # soft {"status": "failed"} dict — the pattern this file exists to
            # remove. ValueError/TypeError were added after the first version
            # of this guard let a missing-circuit error be silently downgraded:
            # the caller got a dict saying "failed" and carried on, which is
            # how a run ends up with no measurements and no error either.
            raise
        except Exception as e:
            logger.error(f"Execution failed for circuit {circuit_id} on {backend}: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "failed",
                "error": str(e),
                "execution_id": f"exec_failed_{hash(f'{circuit_id}_{backend}_{shots}') % 10000:04d}",
                "message": f"Execution failed: {str(e)}"
            }
    
    async def _simulate_quantum_execution(self, circuit_id: str, backend: str, shots: int, **kwargs) -> Dict[str, Any]:
        """Execute a circuit on qiskit-aer and return real measurement counts.

        Previously this sampled counts from a binomial with no circuit involved,
        reported a random `execution_time`, and computed an objective from a
        Hamming-weight formula labelled "Simple example". Now a circuit is
        required, it is actually run, and the timing is measured.

        The circuit is supplied by the caller as `circuit=` — either a
        `QuantumCircuit` or an OpenQASM string. A circuit_id alone is not
        enough: nothing in this service stores circuits, and inventing one to
        match an id is how the previous version ended up simulating nothing.

        Noise is optional and explicit. `noise_level=p` attaches a depolarising
        model with probability p on 1- and 2-qubit gates, which is what makes
        the zero-noise extrapolation path meaningful — without a noise model
        every scale factor returns the same answer and there is nothing to
        extrapolate.
        """
        return run_circuit(shots=shots, circuit_id=circuit_id, **kwargs)
    async def execute_batch(self, circuit_ids: list, backend: str = "simulator", shots: int = 1024) -> Dict[str, Any]:
        """Execute multiple circuits in batch"""
        logger.info(f"Batch executing {len(circuit_ids)} circuits on {backend}")
        
        execution_results = []
        for circuit_id in circuit_ids:
            result = await self.execute_circuit(circuit_id, backend, shots)
            execution_results.append(result)
        
        batch_id = f"batch_{len(self.executions):05d}"
        
        batch_result = {
            "batch_id": batch_id,
            "circuits_executed": len(circuit_ids),
            "backend": backend,
            "shots_per_circuit": shots,
            "execution_results": execution_results,
            "completed_at": datetime.utcnow().isoformat(),
            "status": "completed",
            "message": f"Batch execution of {len(circuit_ids)} circuits completed"
        }
        
        logger.info(f"Batch execution {batch_id} completed with {len(circuit_ids)} circuits")
        return batch_result
    
    async def get_backend_info(self, backend_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific backend"""
        if backend_name not in self.backends:
            return None
        
        backend_info = self.backends[backend_name].copy()
        backend_info["backend_name"] = backend_name
        backend_info["status"] = "available" if backend_info["available"] else "unavailable"
        
        return backend_info
    
    async def list_backends(self) -> Dict[str, Any]:
        """List all available backends"""
        available_backends = []
        for name, info in self.backends.items():
            if info["available"]:
                available_backends.append({
                    "name": name,
                    "type": info["type"],
                    "backend": info["backend"],
                    "status": "available"
                })
        
        return {
            "available_backends": available_backends,
            "total_count": len(available_backends),
            "status": "success",
            "message": f"{len(available_backends)} backends available for circuit execution"
        }
    
    async def get_execution_result(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get result of a specific execution"""
        return self.executions.get(execution_id)
    
    async def list_executions(self) -> Dict[str, Any]:
        """List all executions"""
        return {
            "executions": [
                {
                    "execution_id": eid,
                    "circuit_id": e["circuit_id"],
                    "backend": e["backend"],
                    "shots": e["shots"],
                    "status": e["status"],
                    "executed_at": e["executed_at"]
                }
                for eid, e in self.executions.items()
            ],
            "total_count": len(self.executions),
            "status": "success"
        }