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

    async def _apply_pec(self, raw_results: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Probabilistic error cancellation. NOT IMPLEMENTED."""
        raise _not_implemented("PEC error mitigation", "characterise the noise channel, build a quasi-probability decomposition of the ideal operation, and Monte-Carlo sample it with the sign correction — PEC needs a noise model, and there is none here")

    async def _apply_cdr(self, raw_results: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Clifford data regression. NOT IMPLEMENTED."""
        raise _not_implemented("CDR error mitigation", "generate near-Clifford training circuits that are classically simulable, learn the map from noisy to exact expectation values on them, and apply it to the target circuit")

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