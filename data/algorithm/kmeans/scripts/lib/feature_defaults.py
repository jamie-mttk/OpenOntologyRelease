"""Training feature presets for invoke (mean / median / last row).

Each preset value is a full invoke modelValue, e.g. {"features": {...}}.
"""

from __future__ import annotations

import pandas as pd


def _features_model(values: dict[str, float]) -> dict[str, dict[str, float]]:
    return {"features": values}


def compute_feature_defaults(df: pd.DataFrame, features: list[str]) -> dict[str, dict]:
    subset = df[features].astype(float)
    mean_s = subset.mean(numeric_only=True)
    median_s = subset.median(numeric_only=True)
    last_row = subset.iloc[-1]
    return {
        "mean": _features_model({name: float(mean_s[name]) for name in features}),
        "median": _features_model({name: float(median_s[name]) for name in features}),
        "last": _features_model({name: float(last_row[name]) for name in features}),
    }
