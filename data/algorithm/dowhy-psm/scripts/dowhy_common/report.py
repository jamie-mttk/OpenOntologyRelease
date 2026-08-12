from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_artifacts(
    out_dir: Path,
    *,
    algorithm_code: str,
    scenario: str,
    report: dict[str, Any],
    report_filename: str = "causal_report.json",
    extra_files: dict[str, Any] | None = None,
) -> list[str]:
    files = [report_filename]
    (out_dir / report_filename).write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if extra_files:
        for name, content in extra_files.items():
            (out_dir / name).write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
            files.append(name)

    meta = {
        "reportFile": report_filename,
        "algorithmCode": algorithm_code,
        "scenario": scenario,
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    files.append("meta.json")
    return files
