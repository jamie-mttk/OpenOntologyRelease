from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from lib.cli import log_info
from lib.feature_defaults import compute_feature_defaults


def _bindings(config: dict[str, Any]) -> tuple[list[str], str]:
    target = config.get("target")
    features = config.get("features")
    if not target or not features or not isinstance(features, list):
        raise ValueError("config requires target and features[]")
    return [str(f) for f in features], str(target)


def _hyperparams(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "n_estimators": int(config.get("nEstimators", 200)),
        "max_depth": int(config.get("maxDepth", 6)),
        "learning_rate": float(config.get("learningRate", 0.1)),
    }


def train_from_csv(
    csv_path: Path, config: dict[str, Any], data_meta: dict[str, Any], out_dir: Path
) -> dict[str, Any]:
    features, target = _bindings(config)
    params = _hyperparams(config)
    log_info(
        f">>> XGBoost: n_estimators={params['n_estimators']}, "
        f"max_depth={params['max_depth']}, features={len(features)}"
    )

    df = pd.read_csv(csv_path)
    missing = [c for c in features + [target] if c not in df.columns]
    if missing:
        raise ValueError(f"CSV missing columns: {missing}")

    x = df[features].astype(float)
    y = df[target].astype(float)

    model = xgb.XGBRegressor(
        n_estimators=params["n_estimators"],
        max_depth=params["max_depth"],
        learning_rate=params["learning_rate"],
        objective="reg:squarederror",
        random_state=42,
    )
    model.fit(x, y)
    log_info(">>> 拟合完成，计算指标")
    pred = model.predict(x)
    rmse = float(np.sqrt(mean_squared_error(y, pred)))
    mae = float(mean_absolute_error(y, pred))
    r2 = float(r2_score(y, pred))

    meta = {
        "algorithmCode": "xgboost-regressor",
        "features": features,
        "target": target,
        "hyperparams": params,
        "featureDefaults": compute_feature_defaults(df, features),
    }
    joblib.dump(model, out_dir / "model.joblib")
    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    log_info(f">>> 指标: rmse={rmse:.6f}, mae={mae:.6f}, r2={r2:.6f}")

    return {
        "status": "ok",
        "rmse": rmse,
        "mae": mae,
        "r2": r2,
    }


def _feature_bag(invoke_input: dict[str, Any]) -> dict[str, Any]:
    bag = invoke_input.get("features")
    if bag is None:
        return {}
    if not isinstance(bag, dict):
        raise ValueError("invokeInput.features must be an object")
    return bag


def _read_feature_values(invoke_input: dict[str, Any], features: list[str]) -> list[float]:
    bag = _feature_bag(invoke_input)
    row: list[float] = []
    for name in features:
        if name not in bag:
            raise ValueError(f"invokeInput.features missing key: {name}")
        row.append(float(bag[name]))
    return row


def invoke_predict(artifact_dir: Path, invoke_input: dict[str, Any]) -> dict[str, Any]:
    meta = json.loads((artifact_dir / "meta.json").read_text(encoding="utf-8"))
    features: list[str] = meta["features"]
    row = _read_feature_values(invoke_input, features)

    model = joblib.load(artifact_dir / "model.joblib")
    pred = float(model.predict(np.array([row]))[0])
    return {
        "status": "ok",
        "prediction": pred,
        "target": meta["target"],
    }
