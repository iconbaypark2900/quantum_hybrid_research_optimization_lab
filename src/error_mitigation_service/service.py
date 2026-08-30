"""
Error Mitigation Service Implementation
"""
import asyncio
import logging
from typing import Dict, Any, List
import numpy as np
from datetime import datetime


logger = logging.getLogger(__name__)


def _not_implemented(what: str, needs: str) -> "NotImplementedError":
    """Refuse loudly, and say what it would take to stop refusing."""
    return NotImplementedError(
        f"{what} is not implemented. What was here produced plausible-looking "
        f"'mitigated' output without performing the technique, which is worse "
        f"than failing: the caller cannot tell a mitigated result from an "
        f"unmitigated one. To implement it: {needs}")


class ErrorMitigationService:
    """Service for applying quantum error mitigation techniques"""
    
    def __init__(self, **kwargs):
        self.mitigation_techniques = {
            "zne": self._apply_zne,
            "pec": self._apply_pec,
            "cdr": self._apply_cdr,
            "vnle": self._apply_vnle  # Variational Noise Learning Estimation
        }
        self.mitigation_results = {}
        logger.info("Error Mitigation Service initialized")
    
    async def apply_mitigation(self, raw_results: Dict[str, Any], 
                             technique: str = "zne", 
                             **kwargs) -> Dict[str, Any]:
        """Apply error mitigation technique to raw quantum results"""
        logger.info(f"Applying {technique} error mitigation")
        
        if technique.lower() not in self.mitigation_techniques:
            return {
                "status": "failed",
                "error": f"Technique {technique} not supported",
                "supported_techniques": list(self.mitigation_techniques.keys()),
                "message": f"Supported techniques: {', '.join(self.mitigation_techniques.keys())}"
            }
        
        try:
            # Apply the requested mitigation technique
            mitigation_func = self.mitigation_techniques[technique.lower()]
            mitigated_results = await mitigation_func(raw_results, **kwargs)
            
            # Generate mitigation ID
            mitigation_id = f"mit_{hash(str(raw_results) + technique) % 100000:05d}"
            
            # Store the results
            self.mitigation_results[mitigation_id] = {
                "raw_results": raw_results,
                "mitigated_results": mitigated_results,
                "technique": technique,
                "applied_at": datetime.utcnow().isoformat(),
                "status": "completed"
            }
            
            logger.info(f"Applied {technique} mitigation successfully")
            
            return {
                "mitigation_id": mitigation_id,
                "technique": technique,
                "raw_results": raw_results,
                "mitigated_results": mitigated_results,
                "status": "completed",
                "message": f"{technique.upper()} error mitigation applied successfully"
            }
        
        except NotImplementedError:
            # Must propagate. Catching this would convert a loud refusal back
            # into a soft {"status": "failed"} dict — the exact silent-failure
            # pattern this change exists to remove.
            raise
        except Exception as e:
            logger.error(f"Error applying {technique} mitigation: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "failed",
                "error": str(e),
                "technique": technique,
                "message": f"Error applying {technique} mitigation: {str(e)}"
            }
    
    async def _measure_at_scale_factors(self, circuit, observable=None,
                                        scale_factors=(1, 3, 5),
                                        noise_level: float = 0.02,
                                        shots: int = 8192) -> Dict[float, float]:
        """Run the SAME logical circuit at amplified noise and measure it.

        This is the half of ZNE that cannot be done with arithmetic: fold the
        circuit to each odd scale factor (which leaves the ideal unitary
        unchanged while multiplying the noisy operations), execute each one
        under the same noise model, and record the observable.

        Folding uses Mitiq's `fold_global`, which the PRD names and which
        tests/test_zne_vs_mitiq.py confirms agrees with this repo's own
        implementation.

        `observable` maps a measured bitstring to a value; the default is the
        parity (+1 for even weight, -1 for odd), the standard choice for a
        Bell-type correlation.
        """
        from mitiq.zne.scaling import fold_global
        from qiskit import QuantumCircuit

        from ..execution_orchestrator_service.service import (
            ExecutionOrchestratorService,
        )

        if isinstance(circuit, str):
            circuit = QuantumCircuit.from_qasm_str(circuit)
        if observable is None:
            def observable(bitstring: str) -> float:
                return 1.0 if bitstring.replace(" ", "").count("1") % 2 == 0 else -1.0

        executor = ExecutionOrchestratorService()
        out: Dict[float, float] = {}
        for factor in scale_factors:
            if factor % 2 == 0:
                raise ValueError(
                    f"scale factor {factor} is even; folding appends "
                    "inverse/forward pairs, so only odd factors leave the ideal "
                    "circuit unchanged")
            folded = fold_global(circuit, scale_factor=float(factor))
            result = await executor.execute_circuit(
                f"zne_lambda_{factor}", shots=shots, circuit=folded,
                noise_level=noise_level)
            probs = result["result"]["probabilities"]
            out[float(factor)] = sum(p * observable(state) for state, p in probs.items())
        return out

    async def _apply_zne(self, raw_results: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Zero-noise extrapolation from measurements at amplified noise levels.

        Requires what ZNE actually needs and what the previous version never
        had: expectation values measured at two or more noise scale factors.
        Supply them as

            raw_results["noise_scaled_values"] = {1.0: <E>, 3.0: <E>, 5.0: <E>}

        obtained by running the SAME logical circuit folded to each factor (see
        zne.fold_gates). Given a single unamplified run there is nothing to
        extrapolate from, and this says so instead of reshaping the one
        distribution it has and calling the result mitigated.

        Sources: Temme et al. (2017); Li & Benjamin (2017); Giurgica-Tiron et
        al. (2020) for unitary folding as digital noise scaling.
        """
        from .zne import extrapolate_to_zero_noise

        # Closed loop: given a circuit and an observable, produce the
        # amplified-noise measurements here rather than demanding them.
        circuit = kwargs.get("circuit")
        if circuit is not None and not raw_results.get("noise_scaled_values"):
            raw_results = dict(raw_results)
            raw_results["noise_scaled_values"] = await self._measure_at_scale_factors(
                circuit,
                observable=kwargs.get("observable"),
                scale_factors=kwargs.get("scale_factors", (1, 3, 5)),
                noise_level=kwargs.get("noise_level", 0.02),
                shots=kwargs.get("shots", 8192),
            )

        measured = raw_results.get("noise_scaled_values")
        if not measured:
            raise _not_implemented(
                "ZNE from a single unamplified run",
                "supply raw_results['noise_scaled_values'] as "
                "{scale_factor: expectation_value} with at least two distinct "
                "factors. Producing them end-to-end needs circuit execution, "
                "which is itself not implemented (see SCAFFOLDING.md) and needs "
                "qiskit-aer installed into .venv. The extrapolation half is "
                "implemented and tested in src/error_mitigation_service/zne.py")

        factors = [float(k) for k in measured.keys()]
        values = [float(v) for v in measured.values()]
        method = kwargs.get("method", "richardson")

        out = extrapolate_to_zero_noise(factors, values, method=method)
        mitigated = dict(raw_results)
        mitigated["average_objective_value"] = out["zero_noise_estimate"]
        mitigated["mitigation_applied"] = "zne"
        mitigated["zne"] = out
        return mitigated

    def _make_executor(self, observable, noise_level: float, shots: int):
        """A Mitiq executor: circuit -> expectation of `observable` under noise.

        Synchronous, because Mitiq's executors are. It calls the same
        `run_circuit` the rest of this repository executes through, so the
        noise model has one definition rather than two that can drift.
        """
        from ..execution_orchestrator_service.service import run_circuit

        def executor(circuit) -> float:
            result = run_circuit(circuit=circuit, shots=shots,
                                 noise_level=noise_level)
            return sum(p * observable(state)
                       for state, p in result["probabilities"].items())

        return executor

    @staticmethod
    def _strip_measurements(circuit):
        """Mitiq rewrites the circuit; the executor is what measures it.

        `run_circuit` appends `measure_all()` when a circuit carries no
        classical register, so handing Mitiq an unmeasured circuit keeps the
        measurement in exactly one place.
        """
        work = circuit.copy()
        work.remove_final_measurements(inplace=True)
        return work

    @staticmethod
    def _default_observable(observable):
        if observable is not None:
            return observable

        def parity(bitstring: str) -> float:
            return 1.0 if bitstring.replace(" ", "").count("1") % 2 == 0 else -1.0

        return parity

    async def _apply_pec(self, raw_results: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Probabilistic error cancellation, via Mitiq.

        PEC needs a characterised noise channel: a quasi-probability
        decomposition of each ideal operation into noisy ones, Monte-Carlo
        sampled with the sign correction. Writing that by hand is the mistake
        SCAFFOLDING.md records about the ZNE maths -- the spec named Mitiq and
        it was hand-written anyway, then had to be verified against Mitiq
        afterwards. There is no reason to repeat it twice more, so this is
        Mitiq's implementation against the local depolarising model this
        repository's executor actually applies.

        The noise model is an assumption, not a measurement: PEC is exact only
        insofar as the representations match the hardware. Here the executor
        applies exactly the depolarising channel the representations assume, so
        this is a self-consistent test of the method rather than a claim about
        any real device.
        """
        import asyncio

        from mitiq.pec import execute_with_pec
        from mitiq.pec.representations.depolarizing import (
            represent_operations_in_circuit_with_local_depolarizing_noise,
        )

        circuit = kwargs.get("circuit")
        if circuit is None:
            raise ValueError(
                "PEC needs the circuit itself. Pass circuit=<QuantumCircuit>; "
                "there is nothing to build a quasi-probability representation "
                "from without it.")

        noise_level = float(kwargs.get("noise_level", 0.02))
        shots = int(kwargs.get("shots", 4096))
        observable = self._default_observable(kwargs.get("observable"))
        ideal = self._strip_measurements(circuit)

        representations = represent_operations_in_circuit_with_local_depolarizing_noise(
            ideal, noise_level)
        executor = self._make_executor(observable, noise_level, shots)

        unmitigated = await asyncio.to_thread(executor, ideal)
        mitigated_value = await asyncio.to_thread(
            execute_with_pec, ideal, executor,
            representations=representations,
            num_samples=int(kwargs.get("num_samples", 50)),
            random_state=int(kwargs.get("random_state", 0)),
        )

        out = dict(raw_results)
        out["average_objective_value"] = float(mitigated_value)
        out["unmitigated_value"] = float(unmitigated)
        out["mitigation_applied"] = "pec"
        out["pec"] = {
            "library": "mitiq.pec.execute_with_pec",
            "noise_model": "local depolarising",
            "noise_level": noise_level,
            "num_representations": len(representations),
            "shots_per_sample": shots,
        }
        return out

    async def _apply_cdr(self, raw_results: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Clifford data regression, via Mitiq.

        CDR builds near-Clifford training circuits whose ideal expectation
        values are classically simulable, measures them noisily, and fits the
        map from noisy to ideal. It therefore needs two executors: the noisy
        one, and a noiseless simulator for the training set.

        Like PEC, this is Mitiq's implementation rather than a hand-written
        one, for the reason SCAFFOLDING.md gives.
        """
        import asyncio

        from mitiq.cdr import execute_with_cdr

        circuit = kwargs.get("circuit")
        if circuit is None:
            raise ValueError(
                "CDR needs the circuit itself. Pass circuit=<QuantumCircuit>; "
                "the near-Clifford training set is built from it.")

        noise_level = float(kwargs.get("noise_level", 0.02))
        shots = int(kwargs.get("shots", 4096))
        observable = self._default_observable(kwargs.get("observable"))
        ideal = self._strip_measurements(circuit)

        noisy = self._make_executor(observable, noise_level, shots)
        noiseless = self._make_executor(observable, 0.0, shots)

        unmitigated = await asyncio.to_thread(noisy, ideal)
        mitigated_value = await asyncio.to_thread(
            execute_with_cdr, ideal, noisy,
            simulator=noiseless,
            num_training_circuits=int(kwargs.get("num_training_circuits", 10)),
            fraction_non_clifford=float(kwargs.get("fraction_non_clifford", 0.1)),
        )

        out = dict(raw_results)
        out["average_objective_value"] = float(mitigated_value)
        out["unmitigated_value"] = float(unmitigated)
        out["mitigation_applied"] = "cdr"
        out["cdr"] = {
            "library": "mitiq.cdr.execute_with_cdr",
            "noise_level": noise_level,
            "num_training_circuits": int(kwargs.get("num_training_circuits", 10)),
            "shots_per_circuit": shots,
        }
        return out

    async def _apply_vnle(self, raw_results: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Virtual/noise-less estimation. NOT IMPLEMENTED."""
        raise _not_implemented("VNLE error mitigation", "implement the estimator properly, or remove the technique from the advertised list rather than shipping a placeholder for it")

    async def compare_mitigation_techniques(self, raw_results: Dict[str, Any], 
                                          techniques: List[str] = None) -> Dict[str, Any]:
        """Compare multiple mitigation techniques on the same results"""
        logger.info(f"Comparing mitigation techniques: {techniques or list(self.mitigation_techniques.keys())}")
        
        if techniques is None:
            techniques = list(self.mitigation_techniques.keys())
        
        comparison_results = {}
        
        for technique in techniques:
            if technique in self.mitigation_techniques:
                result = await self.apply_mitigation(raw_results, technique)
                comparison_results[technique] = result
            else:
                comparison_results[technique] = {
                    "status": "failed",
                    "error": f"Technique {technique} not supported",
                    "message": f"Technique {technique} is not available"
                }
        
        # Identify best performing technique based on some metric (e.g., objective improvement)
        best_technique = None
        best_improvement = float('-inf')
        
        for tech, result in comparison_results.items():
            if result["status"] == "completed" and "mitigated_results" in result:
                mitigated = result["mitigated_results"]
                raw = result["raw_results"]
                
                if "average_objective_value" in raw and "average_objective_value" in mitigated:
                    improvement = mitigated["average_objective_value"] - raw["average_objective_value"]
                    if improvement > best_improvement:
                        best_improvement = improvement
                        best_technique = tech
        
        comparison_summary = {
            "raw_results": raw_results,
            "mitigation_results": comparison_results,
            "best_technique": best_technique,
            "best_improvement": best_improvement if best_technique else 0,
            "techniques_compared": len([k for k, v in comparison_results.items() if v["status"] == "completed"]),
            "status": "completed"
        }
        
        logger.info(f"Mitigation comparison completed. Best technique: {best_technique}")
        return comparison_summary
    
    async def get_mitigation_result(self, mitigation_id: str) -> Dict[str, Any]:
        """Get a specific mitigation result"""
        result = self.mitigation_results.get(mitigation_id)
        if result:
            return {
                "mitigation_id": mitigation_id,
                "result": result,
                "status": "found"
            }
        else:
            return {
                "mitigation_id": mitigation_id,
                "status": "not_found",
                "message": f"Mitigation result {mitigation_id} not found"
            }