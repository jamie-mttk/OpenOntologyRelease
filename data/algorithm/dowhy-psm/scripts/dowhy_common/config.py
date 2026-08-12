from __future__ import annotations

from copy import deepcopy
from typing import Any

# flat config key -> (section, nested key)
NESTED_KEY_FROM_FLAT: dict[str, tuple[str, str]] = {
    "estimateMethodName": ("estimate", "methodName"),
    "identifyMethodName": ("identify", "methodName"),
    "refutationMethods": ("refutation", "methods"),
}

BINDING_KEYS = frozenset(
    {
        "treatment",
        "outcome",
        "confounders",
        "instruments",
        "effectModifiers",
        "mediators",
        "graph",
        "target",
        "features",
        "entity",
        "ds",
        "y",
        "regressors",
        "holidays",
    }
)

HYPERPARAM_SECTIONS = frozenset(
    {"causalModel", "identify", "estimate", "methodParams", "refutation", "mediation"}
)

DEFAULT_HYPERPARAMS: dict[str, Any] = {
    "causalModel": {
        "missingNodesAsConfounders": False,
        "proceedWhenUnidentifiable": True,
        "estimandType": "nonparametric-ate",
    },
    "identify": {
        "methodName": "default",
        "optimizeBackdoor": False,
    },
    "estimate": {
        "methodName": "backdoor.propensity_score_matching",
        "controlValue": 0,
        "treatmentValue": 1,
        "targetUnits": "ate",
        "confidenceIntervals": True,
        "testSignificance": False,
        "evaluateEffectStrength": False,
    },
    "methodParams": {
        "caliper": 0.1,
        "numStrata": 4,
        "propensityScoreModel": None,
        "weightingScheme": None,
    },
    "refutation": {
        "methods": ["random_common_cause", "placebo_treatment_refuter"],
        "randomSeed": None,
        "numSimulations": 100,
        "subsetFraction": 0.8,
        "unobservedConfounderStrength": None,
        "sensitivityAnalyzer": "none",
    },
    "mediation": {
        "runAll": False,
    },
}


def require_config(config: Any) -> dict[str, Any]:
    if isinstance(config, dict):
        return config
    raise ValueError("config must be an object")


def flat_to_bindings(config: dict[str, Any]) -> dict[str, Any]:
    return {key: config[key] for key in BINDING_KEYS if key in config}


def _merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def flat_to_hyperparams(config: dict[str, Any]) -> dict[str, Any]:
    nested: dict[str, Any] = {}
    for flat_key, value in config.items():
        mapped = NESTED_KEY_FROM_FLAT.get(flat_key)
        if mapped:
            section, nested_key = mapped
            nested.setdefault(section, {})[nested_key] = value
            continue
        if flat_key in HYPERPARAM_SECTIONS and isinstance(value, dict):
            nested[flat_key] = value
            continue
        for section in HYPERPARAM_SECTIONS:
            if section in DEFAULT_HYPERPARAMS and flat_key in DEFAULT_HYPERPARAMS[section]:
                nested.setdefault(section, {})[flat_key] = value
                break
    hp = _merge_dict(DEFAULT_HYPERPARAMS, nested)
    for section in HYPERPARAM_SECTIONS:
        if section not in hp or not isinstance(hp[section], dict):
            hp[section] = deepcopy(DEFAULT_HYPERPARAMS.get(section, {}))
    return hp
