"""CLI helpers for algorithm plugin scripts (§5.2 contract)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

REQUEST_JSON = "request.json"
DATA_CSV = "data.csv"
ARTIFACTS_DIR = "artifacts"
INVOKE_INPUT_JSON = "invokeInput.json"
RESULT_JSON = "result.json"

# 与平台 DataType 枚举对齐；训练 CSV 禁止 OBJECT
_SUPPORTED_DATA_TYPES = frozenset(
    {"STRING", "INTEGER", "DECIMAL", "BOOLEAN", "DATE", "TIMESTAMP"}
)


def _configure_stdio_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8")
            except (OSError, ValueError):
                pass


_configure_stdio_encoding()


def build_train_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, help="Training run directory")
    return parser


def paths_from_run_dir(run_dir: str | Path) -> tuple[Path, Path, Path]:
    root = Path(run_dir)
    return root / REQUEST_JSON, root / DATA_CSV, root / ARTIFACTS_DIR


def build_invoke_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, help="Training run directory")
    parser.add_argument("--work-dir", required=True, help="Invoke work directory")
    return parser


def invoke_paths_from_dirs(
    run_dir: str | Path, work_dir: str | Path
) -> tuple[Path, Path, Path, Path]:
    run_root = Path(run_dir)
    work_root = Path(work_dir)
    return (
        run_root / ARTIFACTS_DIR,
        work_root / INVOKE_INPUT_JSON,
        work_root / RESULT_JSON,
        run_root / REQUEST_JSON,
    )


def load_invoke_input(work_dir: str | Path) -> dict[str, Any]:
    path = Path(work_dir) / INVOKE_INPUT_JSON
    if not path.is_file():
        raise ValueError(f"{INVOKE_INPUT_JSON} not found under {work_dir}")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{INVOKE_INPUT_JSON} must be an object")
    return data


def write_invoke_result(
    work_dir: str | Path,
    *,
    ok: bool,
    data: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> Path:
    body: dict[str, Any] = {"result": ok}
    if ok:
        if data is None:
            raise ValueError("data is required when result is true")
        body["data"] = data
    else:
        body["error_message"] = error_message or "invoke failed"
    result_path = Path(work_dir) / RESULT_JSON
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
    return result_path


def emit_invoke_ok(work_dir: str | Path, payload: dict[str, Any]) -> None:
    data = {key: value for key, value in payload.items() if key != "status"}
    write_invoke_result(work_dir, ok=True, data=data)
    sys.exit(0)


def emit_invoke_error(work_dir: str | Path, message: str, code: int = 1) -> None:
    write_invoke_result(work_dir, ok=False, error_message=message)
    sys.exit(code)


def load_request(path: str | Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def config_from_request(request: dict[str, Any]) -> dict[str, Any]:
    config = request.get("config")
    if not isinstance(config, dict):
        raise ValueError("config must be an object")
    return config


def data_meta_from_request(request: dict[str, Any]) -> dict[str, Any]:
    data_meta = request.get("dataMeta")
    if not isinstance(data_meta, dict):
        raise ValueError("dataMeta must be an object")
    return data_meta


def column_codes(data_meta: dict[str, Any]) -> list[str]:
    columns = data_meta.get("columns")
    if not isinstance(columns, list):
        raise ValueError("dataMeta.columns must be an array")
    codes: list[str] = []
    for item in columns:
        if not isinstance(item, dict):
            raise ValueError("dataMeta.columns item must be an object")
        code = item.get("code")
        if not code:
            raise ValueError("dataMeta.columns[].code is required")
        codes.append(str(code))
    return codes


def column_data_types(data_meta: dict[str, Any]) -> dict[str, str]:
    """code → 大写 dataType；缺项或非法类型 fail-fast。"""
    columns = data_meta.get("columns")
    if not isinstance(columns, list):
        raise ValueError("dataMeta.columns must be an array")
    out: dict[str, str] = {}
    for item in columns:
        if not isinstance(item, dict):
            raise ValueError("dataMeta.columns item must be an object")
        code = item.get("code")
        data_type = item.get("dataType")
        if not code:
            raise ValueError("dataMeta.columns[].code is required")
        if not data_type:
            raise ValueError(f"dataMeta.columns[].dataType is required for {code}")
        normalized = str(data_type).upper()
        if normalized not in _SUPPORTED_DATA_TYPES:
            raise ValueError(f"unsupported dataType {data_type} for column {code}")
        out[str(code)] = normalized
    return out


def cast_series_by_data_type(series: pd.Series, data_type: str) -> pd.Series:
    """按 dataMeta.dataType 强制转换；禁止样本推断，非法值直接抛错。"""
    dt = data_type.upper()
    if dt == "STRING":
        return series.astype(str)
    # CSV 空串表示 null
    cleaned = series.mask(series.astype(str) == "", pd.NA)
    if dt == "INTEGER":
        return pd.to_numeric(cleaned, errors="raise").astype("Int64")
    if dt == "DECIMAL":
        return pd.to_numeric(cleaned, errors="raise").astype(float)
    if dt == "BOOLEAN":
        return _cast_boolean_series(cleaned)
    if dt == "DATE" or dt == "TIMESTAMP":
        return pd.to_datetime(cleaned, errors="raise")
    raise ValueError(f"unsupported dataType: {data_type}")


def _cast_boolean_series(series: pd.Series) -> pd.Series:
    """平台 CSV 布尔为 true/false；亦接受 0/1。"""

    def _one(value: Any) -> Any:
        if value is pd.NA or value is None:
            return pd.NA
        text = str(value)
        lowered = text.lower()
        if lowered in ("true", "1"):
            return True
        if lowered in ("false", "0"):
            return False
        raise ValueError(f"invalid boolean value: {value!r}")

    return series.map(_one).astype("boolean")


def load_csv_typed(csv_path: str | Path, data_meta: dict[str, Any]) -> pd.DataFrame:
    """按 dataMeta.columns[].dataType 加载 CSV；禁止 pandas 自行推断类型。"""
    type_map = column_data_types(data_meta)
    # keep_default_na=False：空串由类型转换自行处理，避免误伤字符串列
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    missing_in_meta = [c for c in df.columns if c not in type_map]
    if missing_in_meta:
        raise ValueError(f"dataMeta.columns missing types for CSV columns: {missing_in_meta}")
    missing_in_csv = [c for c in type_map if c not in df.columns]
    if missing_in_csv:
        raise ValueError(f"CSV missing columns declared in dataMeta: {missing_in_csv}")
    for col, data_type in type_map.items():
        try:
            df[col] = cast_series_by_data_type(df[col], data_type)
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"failed to cast column {col} as {data_type}: {exc}") from exc
    return df


def emit_ok(data: dict[str, Any]) -> None:
    print(json.dumps(data, ensure_ascii=False))


def log_info(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def emit_error(message: str, code: int = 1) -> None:
    emit_ok({"status": "error", "message": message})
    sys.exit(code)


def ensure_out_dir(path: str | Path) -> Path:
    out = Path(path)
    out.mkdir(parents=True, exist_ok=True)
    return out
