#!/usr/bin/env python3
"""Polynomial regression train script (§5.2)."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from lib.cli import (
    build_train_parser,
    config_from_request,
    data_meta_from_request,
    emit_error,
    emit_ok,
    ensure_out_dir,
    load_request,
    log_info,
    paths_from_run_dir,
)
from lib.model_core import train_from_csv  # noqa: E402


def main() -> None:
    args = build_train_parser().parse_args()
    try:
        request_path, data_path, artifacts_dir = paths_from_run_dir(args.run_dir)
        log_info(">>> 读取 request.json")
        request = load_request(request_path)
        config = config_from_request(request)
        data_meta = data_meta_from_request(request)
        log_info(f">>> 加载训练数据: {data_path}")
        out_dir = ensure_out_dir(artifacts_dir)
        log_info(f">>> 输出目录: {out_dir}")
        result = train_from_csv(data_path, config, data_meta, out_dir)
        log_info(">>> 训练完成，输出结果 JSON")
        emit_ok(result)
    except Exception as exc:  # noqa: BLE001
        emit_error(str(exc))


if __name__ == "__main__":
    main()
