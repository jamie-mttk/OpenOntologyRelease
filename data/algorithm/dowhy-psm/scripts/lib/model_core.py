from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dowhy_common.bindings import load_workframe, parse_bindings, precheck_bindings
from dowhy_common.causal_model import build_causal_model
from dowhy_common.estimate import estimate_effect, extract_ci
from dowhy_common.hyperparams import parse_hyperparams
from dowhy_common.identify import identify_effect
from dowhy_common.report import write_artifacts


def train_from_csv(
    csv_path: Path, config: dict[str, Any], data_meta: dict[str, Any], out_dir: Path
) -> dict[str, Any]:
    bindings = parse_bindings(config, require_confounders=True)
    hp = parse_hyperparams(config)
    precheck_bindings(bindings, hp)

    work, effective_bindings = load_workframe(csv_path, bindings)
    treatment_col = effective_bindings["treatment"]
    outcome_col = effective_bindings["outcome"]

    model = build_causal_model(work, effective_bindings, hp)
    estimand = identify_effect(model, hp)
    estimate = estimate_effect(model, estimand, hp)

    effect = float(estimate.value)
    ci_low, ci_high = extract_ci(estimate)

    baseline = float(work.loc[work[treatment_col] == 0, outcome_col].mean())
    treated = float(work.loc[work[treatment_col] == 1, outcome_col].mean())

    estimate_cfg = hp.get("estimate") or {}
    report = {
        "algorithmCode": "dowhy-psm",
        "scenario": "ate_policy_cf",
        "treatment": treatment_col,
        "outcome": outcome_col,
        "confounders": effective_bindings.get("confounders") or [],
        "instruments": effective_bindings.get("instruments") or [],
        "effectModifiers": effective_bindings.get("effectModifiers") or [],
        "graphUsed": effective_bindings.get("graph"),
        "graphAutoBuilt": effective_bindings.get("graphAutoBuilt", False),
        "ate": effect,
        "ciLow": ci_low,
        "ciHigh": ci_high,
        "baselineOutcomeMean": baseline,
        "treatedOutcomeMean": treated,
        "sampleSize": int(len(work)),
        "method": estimate_cfg.get("methodName"),
        "targetUnits": estimate_cfg.get("targetUnits"),
        "estimateConfig": estimate_cfg,
        "identifyConfig": hp.get("identify"),
        "causalModelConfig": hp.get("causalModel"),
        "methodParams": hp.get("methodParams"),
    }

    write_artifacts(
        out_dir,
        algorithm_code="dowhy-psm",
        scenario="ate_policy_cf",
        report=report,
    )

    return {
        "status": "ok",
        "ate": effect,
        "ciLow": ci_low,
        "ciHigh": ci_high,
        "sampleSize": len(work),
        "baselineOutcomeMean": baseline,
        "treatedOutcomeMean": treated,
    }


def invoke_simulate(artifact_dir: Path, invoke_input: dict[str, Any]) -> dict[str, Any]:
    report_path = artifact_dir / "causal_report.json"
    if not report_path.is_file():
        raise ValueError(f"causal_report.json not found under {artifact_dir}")

    report = json.loads(report_path.read_text(encoding="utf-8"))
    rate = invoke_input.get("treatmentRate")
    if rate is None:
        raise ValueError("invokeInput.treatmentRate is required")
    rate = float(rate)
    if rate < 0 or rate > 1:
        raise ValueError("treatmentRate must be between 0 and 1")

    baseline = float(report["baselineOutcomeMean"])
    ate = float(report["ate"])
    counterfactual_mean = baseline + ate * rate
    uplift = counterfactual_mean - baseline

    return {
        "status": "ok",
        "treatmentRate": rate,
        "expectedOutcomeMean": counterfactual_mean,
        "baselineOutcomeMean": baseline,
        "ate": ate,
        "upliftVsBaseline": uplift,
    }
