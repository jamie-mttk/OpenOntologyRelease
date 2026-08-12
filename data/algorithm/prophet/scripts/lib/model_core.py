from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from prophet import Prophet

from lib.cli import log_info

SUPPORTED_FREQ = {"D", "W", "MS", "ME", "QS", "YS", "Y"}

# 每个 freq 下启用某季节项时建议的最少样本点数（约 2 个季节周期）
MIN_POINTS_BY_FREQ: dict[str, dict[str, int]] = {
    "D": {"daily": 14, "weekly": 28, "yearly": 730},
    "W": {"daily": 0, "weekly": 28, "yearly": 104},
    "MS": {"daily": 0, "weekly": 0, "yearly": 24},
    "ME": {"daily": 0, "weekly": 0, "yearly": 24},
    "QS": {"daily": 0, "weekly": 0, "yearly": 8},
    "YS": {"daily": 0, "weekly": 0, "yearly": 4},
    "Y": {"daily": 0, "weekly": 0, "yearly": 4},
}


def _bindings(config: dict[str, Any]) -> tuple[str, str, list[str], list[dict[str, Any]]]:
    ds_col = config.get("ds")
    y_col = config.get("y")
    if not ds_col or not y_col:
        raise ValueError("config requires ds and y")
    regressors = config.get("regressors") or []
    if not isinstance(regressors, list):
        raise ValueError("config.regressors must be an array")
    regressors = [str(c) for c in regressors]

    holidays = config.get("holidays") or []
    if not isinstance(holidays, list):
        raise ValueError("config.holidays must be an array")
    holiday_defs: list[dict[str, Any]] = []
    for item in holidays:
        # UI AlgColumnBinding 传列名字符串; 对象形式保留 name/窗口
        if isinstance(item, str):
            column = item.strip()
            if not column:
                raise ValueError("holidays string item must be a non-empty column code")
            holiday_defs.append(
                {"name": "节假日", "column": column, "lowerWindow": 0, "upperWindow": 0}
            )
            continue
        if not isinstance(item, dict):
            raise ValueError("each holidays item must be a column string or object")
        name = str(item.get("name") or "").strip()
        column = str(item.get("column") or "").strip()
        if not name or not column:
            raise ValueError("holidays item requires name and column")
        holiday_defs.append(
            {
                "name": name,
                "column": column,
                "lowerWindow": int(item.get("lowerWindow", 0)),
                "upperWindow": int(item.get("upperWindow", 0)),
            }
        )
    return str(ds_col), str(y_col), regressors, holiday_defs


def _hyperparams(config: dict[str, Any]) -> dict[str, Any]:
    freq = str(config.get("freq", "D")).strip().upper()
    if freq not in SUPPORTED_FREQ:
        raise ValueError(f"config.freq must be one of {sorted(SUPPORTED_FREQ)}")
    return {
        "freq": freq,
        "yearlySeasonality": bool(config.get("yearlySeasonality", True)),
        "weeklySeasonality": bool(config.get("weeklySeasonality", True)),
        "dailySeasonality": bool(config.get("dailySeasonality", False)),
        "seasonalityMode": str(config.get("seasonalityMode", "additive")),
        "changepointPriorScale": float(config.get("changepointPriorScale", 0.05)),
        "growth": str(config.get("growth", "linear")),
        "historyTailPoints": config.get("historyTailPoints"),
    }


def _holiday_columns(holiday_defs: list[dict[str, Any]]) -> list[str]:
    return [h["column"] for h in holiday_defs]


def _validate_overlap(regressors: list[str], holiday_defs: list[dict[str, Any]]) -> None:
    holiday_cols = set(_holiday_columns(holiday_defs))
    overlap = set(regressors) & holiday_cols
    if overlap:
        raise ValueError(f"column cannot be both regressor and holiday: {sorted(overlap)}")


def _min_required_points(hp: dict[str, Any]) -> int:
    freq = hp["freq"]
    table = MIN_POINTS_BY_FREQ.get(freq, MIN_POINTS_BY_FREQ["D"])
    need = 2
    if hp["dailySeasonality"]:
        need = max(need, table.get("daily", 0))
    if hp["weeklySeasonality"]:
        need = max(need, table.get("weekly", 0))
    if hp["yearlySeasonality"]:
        need = max(need, table.get("yearly", 0))
    return max(need, 2)


def _resolve_history_tail_points(hp: dict[str, Any], row_count: int) -> int:
    explicit = hp.get("historyTailPoints")
    if explicit is not None and str(explicit).strip() != "":
        n = int(explicit)
        return max(1, min(n, row_count))
    return max(1, min(_min_required_points(hp), row_count))


def _build_holidays_df(df: pd.DataFrame, ds_col: str, holiday_defs: list[dict[str, Any]]) -> pd.DataFrame | None:
    if not holiday_defs:
        return None
    rows: list[dict[str, Any]] = []
    for item in holiday_defs:
        col = item["column"]
        if col not in df.columns:
            raise ValueError(f"CSV missing holiday column: {col}")
        raw = df[col]
        if raw.dtype == bool:
            mask = raw.fillna(False)
        else:
            lowered = raw.astype(str).str.strip().str.lower()
            mask = lowered.isin(("1", "true", "yes", "y"))
            if not mask.any():
                mask = pd.to_numeric(raw, errors="coerce").fillna(0) > 0
        for ds in df.loc[mask, ds_col]:
            rows.append(
                {
                    "holiday": item["name"],
                    "ds": pd.to_datetime(ds),
                    "lower_window": int(item["lowerWindow"]),
                    "upper_window": int(item["upperWindow"]),
                }
            )
    if not rows:
        return None
    return pd.DataFrame(rows)


def _prepare_fit_frame(
    df: pd.DataFrame, ds_col: str, y_col: str, regressors: list[str], holiday_defs: list[dict[str, Any]]
) -> pd.DataFrame:
    missing = [c for c in [ds_col, y_col] + regressors + _holiday_columns(holiday_defs) if c not in df.columns]
    if missing:
        raise ValueError(f"CSV missing columns: {missing}")

    work = df[[ds_col, y_col] + regressors + _holiday_columns(holiday_defs)].copy()
    work[ds_col] = pd.to_datetime(work[ds_col], errors="coerce")
    if work[ds_col].isna().any():
        raise ValueError(f"column {ds_col} contains unparseable dates")
    work[y_col] = pd.to_numeric(work[y_col], errors="coerce")
    if work[y_col].isna().any():
        raise ValueError(f"column {y_col} contains non-numeric values")

    work = work.sort_values(ds_col).reset_index(drop=True)
    if work[ds_col].duplicated().any():
        raise ValueError(f"duplicate timestamps in {ds_col}; aggregate to unique ds before training")

    if not work[ds_col].is_monotonic_increasing:
        raise ValueError(f"{ds_col} must be strictly monotonic after sort")

    return work


def _build_prophet(hp: dict[str, Any], holidays_df: pd.DataFrame | None) -> Prophet:
    kwargs: dict[str, Any] = {
        "growth": hp["growth"],
        "seasonality_mode": hp["seasonalityMode"],
        "changepoint_prior_scale": hp["changepointPriorScale"],
        "yearly_seasonality": hp["yearlySeasonality"],
        "weekly_seasonality": hp["weeklySeasonality"],
        "daily_seasonality": hp["dailySeasonality"],
        "stan_backend": "CMDSTANPY",
    }
    if holidays_df is not None and not holidays_df.empty:
        kwargs["holidays"] = holidays_df
    try:
        return Prophet(**kwargs)
    except AttributeError as exc:
        if "stan_backend" in str(exc):
            raise RuntimeError(
                "Prophet 无法加载 CmdStan 后端（常见于 Windows 下 PYTHONUTF8=1 或缺少 cmdstanpy）。"
                "请重启后端后重试；本地可执行: python -m cmdstanpy.install_cmdstan"
            ) from exc
        raise



def _compute_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    mask = np.isfinite(actual) & np.isfinite(predicted)
    if not mask.any():
        return {"mape": 0.0, "mae": 0.0, "rmse": 0.0}
    a = actual[mask]
    p = predicted[mask]
    mae = float(np.mean(np.abs(a - p)))
    rmse = float(np.sqrt(np.mean((a - p) ** 2)))
    denom = np.where(np.abs(a) < 1e-9, 1e-9, np.abs(a))
    mape = float(np.mean(np.abs((a - p) / denom)) * 100)
    return {"mape": mape, "mae": mae, "rmse": rmse}


def _serialize_ds(value: Any) -> str:
    return pd.Timestamp(value).strftime("%Y-%m-%d %H:%M:%S")


def _history_tail_records(
    df: pd.DataFrame, ds_col: str, y_col: str, regressors: list[str], n: int
) -> list[dict[str, Any]]:
    tail = df.tail(n)
    records: list[dict[str, Any]] = []
    for _, row in tail.iterrows():
        rec: dict[str, Any] = {"ds": _serialize_ds(row[ds_col]), "y": float(row[y_col])}
        for col in regressors:
            rec[col] = float(row[col])
        records.append(rec)
    return records


def _fit_chart_view(fit_df: pd.DataFrame, forecast: pd.DataFrame, ds_col: str, y_col: str) -> dict[str, Any]:
    merged = fit_df[[ds_col, y_col]].merge(
        forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]],
        left_on=ds_col,
        right_on="ds",
        how="left",
    )
    data = []
    for _, row in merged.iterrows():
        data.append(
            {
                "ds": _serialize_ds(row[ds_col]),
                "y": float(row[y_col]),
                "yhat": float(row["yhat"]) if pd.notna(row["yhat"]) else None,
                "yhat_lower": float(row["yhat_lower"]) if pd.notna(row["yhat_lower"]) else None,
                "yhat_upper": float(row["yhat_upper"]) if pd.notna(row["yhat_upper"]) else None,
            }
        )
    return {
        "chartType": "line",
        "title": "训练集拟合",
        "xField": "ds",
        "series": [
            {"name": "实际", "field": "y"},
            {"name": "拟合", "field": "yhat"},
        ],
        "data": data,
    }


def train_from_csv(
    csv_path: Path, config: dict[str, Any], data_meta: dict[str, Any], out_dir: Path
) -> dict[str, Any]:
    ds_col, y_col, regressors, holiday_defs = _bindings(config)
    hp = _hyperparams(config)
    _validate_overlap(regressors, holiday_defs)
    log_info(f">>> Prophet train: freq={hp['freq']}, regressors={len(regressors)}, holidays={len(holiday_defs)}")

    raw = pd.read_csv(csv_path)
    fit_df = _prepare_fit_frame(raw, ds_col, y_col, regressors, holiday_defs)

    min_need = _min_required_points(hp)
    if len(fit_df) < min_need:
        raise ValueError(
            f"insufficient history: need at least {min_need} points for freq={hp['freq']} "
            f"and enabled seasonalities (got {len(fit_df)})"
        )

    prophet_df = fit_df.rename(columns={ds_col: "ds", y_col: "y"})
    holidays_df = _build_holidays_df(fit_df, ds_col, holiday_defs)

    model = _build_prophet(hp, holidays_df)
    for col in regressors:
        model.add_regressor(col)
    model.fit(prophet_df)

    in_sample = model.predict(prophet_df)
    metrics = _compute_metrics(prophet_df["y"].to_numpy(), in_sample["yhat"].to_numpy())

    history_n = _resolve_history_tail_points(hp, len(fit_df))

    meta = {
        "algorithmCode": "prophet",
        "dsCol": ds_col,
        "yCol": y_col,
        "freq": hp["freq"],
        "features": regressors,
        "regressors": regressors,
        "holidays": holiday_defs,
        "historyTailPoints": history_n,
        "historyTail": _history_tail_records(fit_df, ds_col, y_col, regressors, history_n),
        "hyperparams": hp,
    }
    joblib.dump(model, out_dir / "model.joblib")
    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    log_info(f">>> metrics: mape={metrics['mape']:.4f}, mae={metrics['mae']:.4f}, rmse={metrics['rmse']:.4f}")

    return {
        "status": "ok",
        "mape": metrics["mape"],
        "mae": metrics["mae"],
        "rmse": metrics["rmse"],
    }


def _default_holiday_name(meta: dict[str, Any]) -> str:
    holiday_defs: list[dict[str, Any]] = list(meta.get("holidays") or [])
    if holiday_defs:
        return str(holiday_defs[0].get("name") or "节假日").strip() or "节假日"
    return "节假日"


def _training_holiday_windows(meta: dict[str, Any], name: str) -> tuple[int, int]:
    """取训练时同名 holiday 的窗口; Prophet 推理窗口必须与拟合结构一致."""
    holiday_defs: list[dict[str, Any]] = list(meta.get("holidays") or [])
    matched = [h for h in holiday_defs if str(h.get("name") or "").strip() == name]
    if not matched:
        trained = ", ".join(
            str(h.get("name") or "").strip() for h in holiday_defs if str(h.get("name") or "").strip()
        ) or "(none)"
        raise ValueError(
            f"futureHolidays name {name!r} was not trained; trained holiday names: {trained}"
        )
    h = matched[0]
    return int(h.get("lowerWindow", 0)), int(h.get("upperWindow", 0))


def _parse_future_holidays(invoke_input: dict[str, Any], meta: dict[str, Any]) -> pd.DataFrame | None:
    raw = invoke_input.get("futureHolidays")
    if raw is None:
        return None
    if not isinstance(raw, list):
        raise ValueError("invokeInput.futureHolidays must be an array")
    if not raw:
        return None

    default_name = _default_holiday_name(meta)
    rows: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("each futureHolidays item must be an object")
        ds = item.get("ds")
        if ds is None or str(ds).strip() == "":
            raise ValueError("futureHolidays item requires ds")
        name = str(item.get("name") or default_name).strip() or default_name
        train_lower, train_upper = _training_holiday_windows(meta, name)
        # 未传则用训练窗口; 显式传入但与训练不一致则 fail-fast(避免 Prophet constructing regressors)
        lower = train_lower if item.get("lowerWindow") is None else int(item.get("lowerWindow"))
        upper = train_upper if item.get("upperWindow") is None else int(item.get("upperWindow"))
        if lower != train_lower or upper != train_upper:
            raise ValueError(
                f"futureHolidays windows must match training for {name!r}: "
                f"lowerWindow={train_lower}, upperWindow={train_upper} "
                f"(got lowerWindow={lower}, upperWindow={upper}). "
                "Holiday windows are fixed at train time; keep 0/0 or retrain with the desired windows."
            )
        rows.append(
            {
                "holiday": name,
                "ds": pd.to_datetime(ds),
                "lower_window": train_lower,
                "upper_window": train_upper,
            }
        )
    return pd.DataFrame(rows)


def _merge_holidays_into_model(model: Prophet, future_holidays_df: pd.DataFrame | None) -> int:
    if future_holidays_df is None or future_holidays_df.empty:
        return 0
    existing = getattr(model, "holidays", None)
    if existing is not None and not existing.empty:
        combined = pd.concat([existing, future_holidays_df], ignore_index=True)
        combined = combined.drop_duplicates(subset=["holiday", "ds"], keep="last")
    else:
        combined = future_holidays_df.copy()
    model.holidays = combined
    return len(future_holidays_df)


def _forecast_chart_rows(
    history: list[dict[str, Any]],
    forecast_df: pd.DataFrame,
    regressors: list[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in history:
        row: dict[str, Any] = {
            "ds": item["ds"],
            "y": item.get("y"),
            "yhat": None,
            "yhat_lower": None,
            "yhat_upper": None,
        }
        rows.append(row)
    for _, frow in forecast_df.iterrows():
        row = {
            "ds": _serialize_ds(frow["ds"]),
            "y": None,
            "yhat": float(frow["yhat"]),
            "yhat_lower": float(frow["yhat_lower"]),
            "yhat_upper": float(frow["yhat_upper"]),
        }
        rows.append(row)
    return rows


def _forecast_table_rows(chart_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """预测明细行：无历史 y、仅有 yhat 的点。"""
    rows: list[dict[str, Any]] = []
    for row in chart_data:
        has_y = row.get("y") is not None
        has_yhat = row.get("yhat") is not None
        if not has_y and has_yhat:
            rows.append(row)
    return rows


def invoke_forecast(artifact_dir: Path, invoke_input: dict[str, Any]) -> dict[str, Any]:
    meta_path = artifact_dir / "meta.json"
    model_path = artifact_dir / "model.joblib"
    if not meta_path.is_file() or not model_path.is_file():
        raise ValueError(f"artifact missing model or meta under {artifact_dir}")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    model = joblib.load(model_path)

    periods = int(invoke_input.get("periods", 8))
    if periods < 1:
        raise ValueError("invokeInput.periods must be >= 1")

    freq = str(meta.get("freq", "D"))
    regressors: list[str] = list(meta.get("regressors") or [])

    future_holidays_df = _parse_future_holidays(invoke_input, meta)
    future_holiday_count = _merge_holidays_into_model(model, future_holidays_df)

    future = model.make_future_dataframe(periods=periods, freq=freq, include_history=False)
    feature_bag = invoke_input.get("features") or {}
    if not isinstance(feature_bag, dict):
        raise ValueError("invokeInput.features must be an object")
    for col in regressors:
        if col not in feature_bag or feature_bag[col] is None:
            raise ValueError(f"invokeInput.features.{col} is required")
        future[col] = float(feature_bag[col])

    forecast = model.predict(future)
    history = list(meta.get("historyTail") or [])
    chart_data = _forecast_chart_rows(history, forecast, regressors)

    horizon_start = _serialize_ds(forecast["ds"].iloc[0])
    horizon_end = _serialize_ds(forecast["ds"].iloc[-1])

    return {
        "status": "ok",
        "periods": periods,
        "freq": freq,
        "horizonStart": horizon_start,
        "horizonEnd": horizon_end,
        "futureHolidayCount": future_holiday_count,
        "forecast": chart_data,
    }
