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


class ExecutionOrchestratorService:
    """Service for orchestrating quantum circuit execution on simulators and QPUs"""
    
    def __init__(self, host: str = "localhost", port: int = 8003, **kwargs):
        self.host = host
        self.port = port
        self.backends = {
            "simulator": {
                "type": "qiskit",
                "backend": "qasm_simulator",
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
        
        except NotImplementedError:
            # Must propagate: swallowing it would turn a loud refusal back into
            # a soft {"status": "failed"} dict, which is the pattern being removed.
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
        """Execute a circuit and return measurement counts. NOT IMPLEMENTED.

        This never simulated a circuit. It sampled counts from a binomial
        distribution without reference to any circuit, gate or state vector,
        then reported three things a caller reads as measurements:

          - `average_objective_value`, computed from a made-up function of a
            bitstring's Hamming weight (`hw*0.8 - hw^2*0.05`, labelled "Simple
            example" in the source) rather than from the problem's objective;
          - `execution_time`, drawn from np.random.uniform(0.1, 5.0);
          - `backend_info` advertising 32 qubits of a backend that does not exist.

        A simulator is a legitimate thing to run against — qiskit-aer and
        PennyLane's default.qubit are real simulators and using one is normal
        practice. The problem is not simulation; it is that no circuit was ever
        involved, while the output was shaped to look like it had been.
        """
        raise _not_implemented(
            "circuit execution",
            "run the circuit on a real simulator. qiskit-aer is pinned in "
            "requirements.txt (>=0.14.0) but is NOT installed in .venv, so this "
            "needs `./.venv/bin/pip install qiskit qiskit-aer` first. Then "
            "measure wall-clock time with time.perf_counter, and compute the "
            "objective from the problem definition rather than from bit counts")

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