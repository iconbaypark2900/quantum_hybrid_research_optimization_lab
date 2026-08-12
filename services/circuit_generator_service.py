"""DEPRECATED DUPLICATE — do not import. See src/circuit_generator_service/service.py.

This tree is a second, older copy of every service. `main.py` imports the
canonical implementations from `src/<name>_service/service.py`; only
`main_orchestrator.py` still imports this one, and it cannot run anyway
(this tree needs `pydantic`, which is not installed in .venv).

It is not merely redundant, it is actively misleading: these copies still
fabricate their results. The version of zero-noise extrapolation in this file's
sibling `error_mitigation_service.py` pushes every probability TOWARD 0.5 —
measured: peak 0.70 -> 0.62, entropy 1.32 -> 1.55 bits — which flattens the
distribution, the opposite of both its own comment ("increasing contrast") and
of what error mitigation does. The copy under src/ at least sharpens.

Importing raises rather than warns, because a warning on a module that
fabricates numbers is not proportionate to the harm of using it by accident.

TO RESOLVE: repoint main_orchestrator.py at the src/ tree, confirm the
constructor signatures line up, then delete this directory. Tracked in
SCAFFOLDING.md.
"""
raise ImportError(
    "services/circuit_generator_service.py is a deprecated duplicate that still fabricates "
    "its results. Import from src.circuit_generator_service.service instead. "
    "See SCAFFOLDING.md.")

"""
Circuit Generator Service - Implementation
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import numpy as np
from datetime import datetime


logger = logging.getLogger(__name__)


class CircuitParameters(BaseModel):
    """Parameters for quantum circuit generation"""
    depth: int = Field(3, ge=1, le=20, description="Circuit depth (number of layers)")
    problem_size: int = Field(4, ge=2, le=20, description="Size of the problem (n-qubits)")
    initial_state: str = Field("uniform", description="Initial state preparation")
    mixer_type: str = Field("x-mixer", description="Type of mixing operator for QAOA")
    ansatz_type: str = Field("real_amplitudes", description="Ansatz type for VQE (real_amplitudes, efficient_su2, etc.)")
    learning_rate: float = Field(0.01, gt=0, le=1.0, description="Learning rate for variational circuits")


class CircuitGeneratorService:
    """Service for generating QAOA/VQE/quantum kernel circuits"""
    
    def __init__(self, host: str = "localhost", port: int = 8002):
        self.host = host
        self.port = port
        self.generated_circuits = {}
        logger.info(f"Circuit Generator Service initialized on {host}:{port}")
    
    async def generate_circuit(self, template: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate quantum circuits based on template and parameters"""
        logger.info(f"Generating circuit with template: {template}")
        
        try:
            params = CircuitParameters(**parameters)
        except Exception as e:
            logger.error(f"Invalid circuit parameters: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "message": "Invalid circuit parameters provided"
            }
        
        # Generate circuit based on template
        if template.lower() == "qaoa":
            circuit_description = await self._generate_qaoa_circuit(params)
        elif template.lower() == "vqe":
            circuit_description = await self._generate_vqe_circuit(params)
        elif template.lower() == "quantum_kernel":
            circuit_description = await self._generate_quantum_kernel(params)
        else:
            logger.error(f"Unknown circuit template: {template}")
            return {
                "status": "failed", 
                "error": f"Unknown circuit template: {template}",
                "message": f"Template '{template}' is not supported. Supported templates: qaoa, vqe, quantum_kernel"
            }
        
        # Generate a unique circuit ID
        circuit_id = f"circ_{hash(template + str(params.dict())) % 10000:04d}"
        
        # Store the circuit
        self.generated_circuits[circuit_id] = {
            "template": template,
            "parameters": params.dict(),
            "circuit": circuit_description,
            "created_at": datetime.utcnow().isoformat(),
            "status": "generated"
        }
        
        logger.info(f"Circuit {circuit_id} generated successfully for template {template}")
        
        return {
            "circuit_id": circuit_id,
            "template": template,
            "circuit_type": template.lower(),
            "qubit_count": params.problem_size,
            "parameters": params.dict(),
            "circuit": circuit_description,
            "status": "generated",
            "message": f"{template.upper()} circuit with {params.problem_size} qubits and {params.depth} layers generated successfully"
        }
    
    async def _generate_qaoa_circuit(self, params: CircuitParameters) -> Dict[str, Any]:
        """Generate QAOA (Quantum Approximate Optimization Algorithm) circuit"""
        logger.info(f"Generating QAOA circuit with depth {params.depth}, problem size {params.problem_size}")
        
        circuit_description = {
            "type": "qaoa",
            "qubit_count": params.problem_size,
            "depth": params.depth,
            "structure": {
                "cost_layers": [],
                "mixer_layers": []
            },
            "parameters": {
                "beta": [float(np.random.uniform(0, 2*np.pi)) for _ in range(params.depth)],  # Mixer angles
                "gamma": [float(np.random.uniform(0, 2*np.pi)) for _ in range(params.depth)]   # Cost angles
            },
            "initial_state": params.initial_state,
            "mixer_type": params.mixer_type,
            "metadata": {
                "creation_timestamp": datetime.utcnow().isoformat(),
                "algorithm": "qaoa",
                "implementation": "parameterized_quantum_circuit"
            }
        }
        
        # Add layer descriptions
        for i in range(params.depth):
            cost_layer = {
                "layer_id": i,
                "operator_type": "problem_hamiltonian",  # Usually diagonal operators encoding the problem
                "interactions": f"all_to_all" if params.problem_size < 6 else "nearest_neighbor",  # Simplified connectivity
                "parameter_symbol": f"gamma_{i}"
            }
            
            mixer_layer = {
                "layer_id": i,
                "operator_type": params.mixer_type,
                "interactions": "single_qubit_x_rotation" if params.mixer_type == "x-mixer" else "pairwise_xy_rotation",
                "parameter_symbol": f"beta_{i}"
            }
            
            circuit_description["structure"]["cost_layers"].append(cost_layer)
            circuit_description["structure"]["mixer_layers"].append(mixer_layer)
        
        return circuit_description
    
    async def _generate_vqe_circuit(self, params: CircuitParameters) -> Dict[str, Any]:
        """Generate VQE (Variational Quantum Eigensolver) circuit"""
        logger.info(f"Generating VQE circuit with depth {params.depth}, problem size {params.problem_size}")
        
        circuit_description = {
            "type": "vqe",
            "qubit_count": params.problem_size,
            "depth": params.depth,
            "ansatz_type": params.ansatz_type,
            "structure": {
                "evolution_blocks": [],
                "entanglement_structure": "full" if params.problem_size < 6 else "linear"
            },
            "parameters": {
                "theta": [float(np.random.uniform(0, 2*np.pi)) for _ in range(params.depth * params.problem_size * 2)]  # More parameters for VQE
            },
            "metadata": {
                "creation_timestamp": datetime.utcnow().isoformat(),
                "algorithm": "vqe",
                "implementation": "parameterized_variational_ansatz"
            }
        }
        
        # Add evolution blocks for VQE ansatz
        for i in range(params.depth):
            block = {
                "block_id": i,
                "rotation_layers": [],
                "entanglement_layer": {
                    "type": circuit_description["structure"]["entanglement_structure"],
                    "gates": ["cx" if params.problem_size < 6 else "cz"]  # Different entangling gates based on connectivity
                }
            }
            
            # Add rotation layers
            for j in range(params.problem_size):
                rotation = {
                    "qubit": j,
                    "rotations": [
                        {"gate": "ry", "parameter_symbol": f"theta_{i}_{j}_0"},
                        {"gate": "rz", "parameter_symbol": f"theta_{i}_{j}_1"}
                    ]
                }
                block["rotation_layers"].append(rotation)
            
            circuit_description["structure"]["evolution_blocks"].append(block)
        
        return circuit_description
    
    async def _generate_quantum_kernel(self, params: CircuitParameters) -> Dict[str, Any]:
        """Generate quantum kernel circuit for machine learning"""
        logger.info(f"Generating quantum kernel with depth {params.depth}, problem size {params.problem_size}")
        
        circuit_description = {
            "type": "quantum_kernel",
            "qubit_count": params.problem_size,
            "feature_map_type": "ZZFeatureMap" if params.problem_size > 2 else "PauliFeatureMap",
            "reps": params.depth,
            "structure": {
                "feature_encoding_layers": [],
                "entanglement_layers": []
            },
            "parameters": {
                "data_parameters": [f"x_{i}" for i in range(params.problem_size)],
                "trainable_parameters": [f"theta_{i}" for i in range(params.depth * params.problem_size)]
            },
            "metadata": {
                "creation_timestamp": datetime.utcnow().isoformat(),
                "algorithm": "quantum_kernel",
                "implementation": "parameterized_feature_map"
            }
        }
        
        # Add feature encoding and entanglement layers
        for i in range(params.depth):
            # Feature encoding layer (uses data parameters)
            feature_layer = {
                "layer_id": i,
                "type": "feature_encoding",
                "encoding_gates": [
                    {"qubit": j, "gate": "ry", "parameter_symbol": f"x_{j}"} 
                    for j in range(params.problem_size)
                ]
            }
            
            # Entanglement layer (uses trainable parameters)
            entanglement_layer = {
                "layer_id": i,
                "type": "entanglement",
                "connectivity": "linear" if params.problem_size > 3 else "full",
                "gates": [
                    {"qubits": [j, (j+1) % params.problem_size], "gate": "cz"}  # Cycle connection for entanglement
                    for j in range(params.problem_size)
                ]
            }
            
            circuit_description["structure"]["feature_encoding_layers"].append(feature_layer)
            circuit_description["structure"]["entanglement_layers"].append(entanglement_layer)
        
        return circuit_description
    
    async def get_circuit(self, circuit_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a generated circuit"""
        return self.generated_circuits.get(circuit_id)
    
    async def list_circuits(self) -> Dict[str, Any]:
        """List all generated circuits"""
        return {
            "circuits": [
                {
                    "circuit_id": cid,
                    "template": c["template"], 
                    "qubits": c["parameters"]["problem_size"],
                    "depth": c["parameters"]["depth"],
                    "type": c["circuit"]["type"],
                    "created_at": c["created_at"]
                }
                for cid, c in self.generated_circuits.items()
            ],
            "total_count": len(self.generated_circuits),
            "status": "success"
        }
    
    async def update_circuit_parameters(self, circuit_id: str, new_parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Update parameters of an existing circuit"""
        if circuit_id not in self.generated_circuits:
            return {
                "status": "failed",
                "error": f"Circuit {circuit_id} not found",
                "message": f"Could not update circuit {circuit_id}: circuit does not exist"
            }
        
        # Validate new parameters
        try:
            params = CircuitParameters(**new_parameters)
        except Exception as e:
            logger.error(f"Invalid parameters for circuit update: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "message": "Invalid parameters provided for circuit update"
            }
        
        # Get the original circuit template
        original_circuit = self.generated_circuits[circuit_id]
        template = original_circuit["template"]
        
        # Regenerate the circuit with new parameters
        if template.lower() == "qaoa":
            new_circuit = await self._generate_qaoa_circuit(params)
        elif template.lower() == "vqe":
            new_circuit = await self._generate_vqe_circuit(params)
        elif template.lower() == "quantum_kernel":
            new_circuit = await self._generate_quantum_kernel(params)
        else:
            return {
                "status": "failed",
                "error": f"Unknown circuit template: {template}",
                "message": f"Template '{template}' is not supported for regeneration"
            }
        
        # Update the stored circuit
        self.generated_circuits[circuit_id].update({
            "parameters": params.dict(),
            "circuit": new_circuit,
            "last_modified": datetime.utcnow().isoformat()
        })
        
        return {
            "status": "success",
            "circuit_id": circuit_id,
            "message": f"Circuit {circuit_id} parameters updated successfully",
            "new_qubit_count": params.problem_size,
            "new_depth": params.depth
        }
    
    async def delete_circuit(self, circuit_id: str) -> Dict[str, Any]:
        """Delete a generated circuit"""
        if circuit_id not in self.generated_circuits:
            return {
                "status": "failed", 
                "error": f"Circuit {circuit_id} not found",
                "message": f"Circuit {circuit_id} does not exist"
            }
        
        del self.generated_circuits[circuit_id]
        
        return {
            "status": "success",
            "circuit_id": circuit_id,
            "message": f"Circuit {circuit_id} deleted successfully"
        }