from __future__ import annotations

from typing import Any

from dowhy import CausalModel

MEDIATION_ESTIMAND_TYPES = frozenset(
    {
        "nonparametric-nde",
        "nonparametric-nie",
        "nonparametric-cde",
    }
)

BACKDOOR_TO_MEDIATION_METHOD = {
    "linear_regression": "mediation.two_stage_regression",
    "generalized_linear_model": "mediation.two_stage_regression",
    "propensity_score_weighting": "mediation.two_stage_regression",
    "propensity_score_matching": "mediation.two_stage_regression",
    "propensity_score_stratification": "mediation.two_stage_regression",
}


def resolve_estimate_method(hp: dict[str, Any]) -> str:
    estimate_cfg = hp.get("estimate") or {}
    method = estimate_cfg.get("methodName", "backdoor.propensity_score_matching")
    estimand_type = (hp.get("causalModel") or {}).get("estimandType", "nonparametric-ate")
    if estimand_type not in MEDIATION_ESTIMAND_TYPES:
        return method
    if method.startswith("mediation."):
        return method
    if method.startswith("backdoor."):
        suffix = method.split(".", 1)[1]
        return BACKDOOR_TO_MEDIATION_METHOD.get(suffix, "mediation.two_stage_regression")
    return "mediation.two_stage_regression"


def _build_method_params(hp: dict[str, Any]) -> dict[str, Any]:
    method_name = resolve_estimate_method(hp)
    params_cfg = hp.get("methodParams") or {}
    params: dict[str, Any] = {}

    if "propensity_score_matching" in method_name:
        params["caliper"] = float(params_cfg.get("caliper", 0.1))
    if "propensity_score_stratification" in method_name:
        params["num_strata"] = int(params_cfg.get("numStrata", 4))
    if params_cfg.get("propensityScoreModel"):
        params["propensity_score_model"] = params_cfg["propensityScoreModel"]
    if params_cfg.get("weightingScheme"):
        params["weighting_scheme"] = params_cfg["weightingScheme"]

    return params


def estimate_effect(model: CausalModel, estimand, hp: dict[str, Any]):
    estimate_cfg = hp.get("estimate") or {}
    method_name = resolve_estimate_method(hp)
    return model.estimate_effect(
        estimand,
        method_name=method_name,
        control_value=estimate_cfg.get("controlValue", 0),
        treatment_value=estimate_cfg.get("treatmentValue", 1),
        target_units=estimate_cfg.get("targetUnits", "ate"),
        confidence_intervals=bool(estimate_cfg.get("confidenceIntervals", True)),
        test_significance=bool(estimate_cfg.get("testSignificance", False)),
        evaluate_effect_strength=bool(estimate_cfg.get("evaluateEffectStrength", False)),
        method_params=_build_method_params(hp),
    )


def extract_ci(estimate) -> tuple[float | None, float | None]:
    ci = estimate.get_confidence_intervals() if hasattr(estimate, "get_confidence_intervals") else None
    if ci is not None and len(ci) >= 2:
        return float(ci[0]), float(ci[1])
    return None, None
