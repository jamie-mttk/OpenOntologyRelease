"""CLI helpers for algorithm plugin scripts (§5.2 contract)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REQUEST_JSON = "request.json"
DATA_CSV = "data.csv"
ARTIFACTS_DIR = "artifacts"
INVOKE_INPUT_JSON = "invokeInput.json"
RESULT_JSON = "result.json"


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
