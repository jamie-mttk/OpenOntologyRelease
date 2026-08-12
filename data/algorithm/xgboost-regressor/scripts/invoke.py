#!/usr/bin/env python3
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from lib.cli import (
    build_invoke_parser,
    emit_invoke_error,
    emit_invoke_ok,
    ensure_out_dir,
    invoke_paths_from_dirs,
    load_invoke_input,
)
from lib.model_core import invoke_predict


def main() -> None:
    args = build_invoke_parser().parse_args()
    try:
        artifact_dir, _, _, _ = invoke_paths_from_dirs(args.run_dir, args.work_dir)
        ensure_out_dir(args.work_dir)
        invoke_input = load_invoke_input(args.work_dir)
        payload = invoke_predict(artifact_dir, invoke_input)
        emit_invoke_ok(args.work_dir, payload)
    except Exception as exc:  # noqa: BLE001
        emit_invoke_error(args.work_dir, str(exc))


if __name__ == "__main__":
    main()
