from __future__ import annotations

from typing import Any

import pandas as pd

from dowhy_common.config import flat_to_bindings, require_config


def _as_str_list(value: Any) -> list[str]:
    if not value:
        return []
    if not isinstance(value, list):
        raise ValueError("expected string array")
    return [str(v) for v in value if v is not None and str(v).strip()]


def parse_bindings(config: dict[str, Any], *, require_confounders: bool = True) -> dict[str, Any]:
    bindings = flat_to_bindings(require_config(config))
    if not isinstance(bindings, dict):
        raise ValueError("config bindings must be an object")

    treatment = bindings.get("treatment")
    outcome = bindings.get("outcome")
    if not treatment or not outcome:
        raise ValueError("config requires treatment and outcome")

    confounders = _as_str_list(bindings.get("confounders"))
    instruments = _as_str_list(bindings.get("instruments"))
    effect_modifiers = _as_str_list(bindings.get("effectModifiers"))
    mediators = _as_str_list(bindings.get("mediators"))
    graph = bindings.get("graph")
    graph_text = str(graph).strip() if graph else ""

    if require_confounders and not graph_text and not confounders:
        raise ValueError("confounders[] is required when graph is empty")

    return {
        "treatment": str(treatment),
        "outcome": str(outcome),
        "confounders": confounders,
        "instruments": instruments,
        "effectModifiers": effect_modifiers,
        "mediators": mediators,
        "graph": graph_text or None,
    }


def precheck_bindings(bindings: dict[str, Any], hp: dict[str, Any]) -> None:
    method = (hp.get("estimate") or {}).get("methodName") or ""
    if method.startswith("iv.") and not bindings.get("instruments"):
        raise ValueError("instruments[] is required for IV estimation methods")
    if bindings.get("mediators") and not bindings.get("graph"):
        pass  # graph built programmatically in build_causal_model


def _prepare_treatment(series: pd.Series) -> pd.Series:
    unique = sorted(series.dropna().unique().tolist())
    if len(unique) == 2:
        return series.map({unique[0]: 0, unique[1]: 1}).astype(int)
    if pd.api.types.is_bool_dtype(series):
        return series.astype(int)
    if set(unique).issubset({0, 1, 0.0, 1.0}):
        return series.astype(int)
    raise ValueError("treatment must be binary (two distinct values or 0/1)")


def _coerce_bool_like_to_numeric(series: pd.Series) -> pd.Series:
    """bool / 二值 TrueFalse → int, 避免 DoWhy/numpy 对 bool 做减法报错."""
    if pd.api.types.is_bool_dtype(series):
        return series.astype(int)
    #
    sample = series.dropna()
    if sample.empty:
        return series
    unique = set(sample.unique().tolist())
    if unique.issubset({True, False}):
        return series.map({True: 1, False: 0}).astype(int)
    if unique.issubset({0, 1, 0.0, 1.0, True, False}):
        return series.astype(int)
    return series


def _build_mediation_graph(bindings: dict[str, Any]) -> str:
    t = bindings["treatment"]
    y = bindings["outcome"]
    lines = ["digraph {"]
    for m in bindings.get("mediators") or []:
        lines.append(f'  "{t}" -> "{m}";')
        lines.append(f'  "{m}" -> "{y}";')
    for c in bindings.get("confounders") or []:
        lines.append(f'  "{c}" -> "{t}";')
        lines.append(f'  "{c}" -> "{y}";')
        for m in bindings.get("mediators") or []:
            lines.append(f'  "{c}" -> "{m}";')
    lines.append("}")
    return "\n".join(lines)


def load_workframe(csv_path, bindings: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    df = pd.read_csv(csv_path)
    cols = {bindings["treatment"], bindings["outcome"]}
    for key in ("confounders", "instruments", "effectModifiers", "mediators"):
        cols.update(bindings.get(key) or [])

    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"CSV missing columns: {missing}")

    work = df[sorted(cols)].dropna().copy()
    treatment_col = bindings["treatment"]
    outcome_col = bindings["outcome"]
    work[treatment_col] = _prepare_treatment(work[treatment_col])
    if work[treatment_col].nunique() < 2:
        raise ValueError("treatment column must have both 0 and 1 after encoding")
    #
    # outcome / 协变量若为 bool, DoWhy 内部减法会触发 numpy boolean subtract
    work[outcome_col] = _coerce_bool_like_to_numeric(work[outcome_col])
    for key in ("confounders", "instruments", "effectModifiers", "mediators"):
        for col in bindings.get(key) or []:
            work[col] = _coerce_bool_like_to_numeric(work[col])

    effective_bindings = dict(bindings)
    if bindings.get("mediators") and not bindings.get("graph"):
        effective_bindings["graph"] = _build_mediation_graph(bindings)
        effective_bindings["graphAutoBuilt"] = True

    return work, effective_bindings
