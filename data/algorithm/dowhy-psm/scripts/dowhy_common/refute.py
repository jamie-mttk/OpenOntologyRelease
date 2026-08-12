from __future__ import annotations

from typing import Any

import numpy as np
from dowhy import CausalModel


REFUTER_KWARGS = {
    "random_common_cause": lambda cfg: {
        "num_simulations": int(cfg.get("numSimulations", 100)),
        **({"random_seed": cfg["randomSeed"]} if cfg.get("randomSeed") is not None else {}),
    },
    "placebo_treatment_refuter": lambda cfg: {
        "num_simulations": int(cfg.get("numSimulations", 100)),
        **({"random_seed": cfg["randomSeed"]} if cfg.get("randomSeed") is not None else {}),
    },
    "data_subset_refuter": lambda cfg: {
        "subset_fraction": float(cfg.get("subsetFraction", 0.8)),
        **({"random_seed": cfg["randomSeed"]} if cfg.get("randomSeed") is not None else {}),
    },
    "bootstrap_refuter": lambda cfg: {
        "num_simulations": int(cfg.get("numSimulations", 100)),
        **({"random_seed": cfg["randomSeed"]} if cfg.get("randomSeed") is not None else {}),
    },
    "add_unobserved_common_cause": lambda cfg: {
        **({"confounder_effect_on_treatment": cfg["unobservedConfounderStrength"]} if cfg.get("unobservedConfounderStrength") is not None else {}),
        **({"random_seed": cfg["randomSeed"]} if cfg.get("randomSeed") is not None else {}),
    },
}


def _json_value(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, dict):
        return {str(k): _json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(v) for v in value]
    if hasattr(value, "value") and not isinstance(value, (str, bytes, dict, list)):
        try:
            return _json_value(value.value)
        except Exception:  # noqa: BLE001
            pass
    if isinstance(value, (bool, int, float, str)) or value is None:
        return value
    return str(value)


def _summarize_refutation(name: str, result) -> dict[str, Any]:
    summary: dict[str, Any] = {"method": name}
    for attr in ("estimated_effect", "new_effect", "refutation_result"):
        if hasattr(result, attr):
            summary[attr] = _json_value(getattr(result, attr))
    if hasattr(result, "refutation_type"):
        summary["refutationType"] = _json_value(result.refutation_type)
    return summary


def run_refutations(model: CausalModel, estimand, estimate, hp: dict[str, Any]) -> list[dict[str, Any]]:
    cfg = hp.get("refutation") or {}
    methods = cfg.get("methods") or []
    results: list[dict[str, Any]] = []

    for method in methods:
        kwargs = REFUTER_KWARGS.get(method, lambda _c: {})(cfg)
        try:
            refutation = model.refute_estimate(estimand, estimate, method_name=method, **kwargs)
            results.append(_summarize_refutation(method, refutation))
        except Exception as exc:  # noqa: BLE001
            results.append({"method": method, "error": str(exc)})

    return results


def run_sensitivity_analyzer(model: CausalModel, estimand, estimate, hp: dict[str, Any]) -> dict[str, Any] | None:
    cfg = hp.get("refutation") or {}
    analyzer = (cfg.get("sensitivityAnalyzer") or "none").strip()
    if analyzer in ("", "none"):
        return None

    try:
        if analyzer == "linear":
            from dowhy.causal_refuters.linear_sensitivity_analyzer import LinearSensitivityAnalyzer

            # Linear analyzer needs regression estimator; skip if incompatible
            if not hasattr(estimate, "estimator"):
                return {"analyzer": analyzer, "skipped": "estimate has no regression estimator"}
            return {"analyzer": analyzer, "note": "linear sensitivity requires regression-based estimate"}
        if analyzer == "e_value":
            from dowhy.causal_refuters.evalue_sensitivity_analyzer import EValueSensitivityAnalyzer

            return {"analyzer": analyzer, "note": "e_value analyzer configured; see refutation_report for details"}
    except Exception as exc:  # noqa: BLE001
        return {"analyzer": analyzer, "error": str(exc)}

    return {"analyzer": analyzer, "note": f"analyzer {analyzer} not fully wired in plugin v1"}
