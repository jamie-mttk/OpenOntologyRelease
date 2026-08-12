#!/usr/bin/env python3
"""Generate 24_seed_prophet_algorithm.sql from manifest.json."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
MANIFEST = ROOT / "backend" / "model" / "prophet" / "manifest.json"
OUT = ROOT / "backend" / "src" / "main" / "resources" / "db" / "demo" / "24_seed_prophet_algorithm.sql"


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    spec = manifest["spec"]

    def cast_segment(key: str) -> str:
        payload = json.dumps(spec[key], ensure_ascii=False, separators=(",", ":"))
        escaped = payload.replace("\\", "\\\\").replace("'", "''")
        return f"CAST('{escaped}' AS JSON)"

    sql = f"""-- Prophet algorithm seed (from data/algorithm/prophet/manifest.json)
USE ontology_new;

SET @sys = '000000000000000000000000000001';
SET @domain_id = 'd010000000000000000000000000001';

DELETE FROM algorithm WHERE code = 'prophet';

INSERT INTO algorithm (
  id, code, name, version, domain_id, description, category, impl_kind,
  spec_training_config, spec_training_result, spec_invoke_input, spec_invoke_result,
  status, create_by, update_by
) VALUES (
  'al010000000000000000000000000005',
  'prophet',
  'Prophet 时序预测',
  '1.0.0',
  @domain_id,
  '{manifest.get("description", "").replace("'", "''")}',
  3,
  0,
  {cast_segment("trainingConfig")},
  {cast_segment("trainingResult")},
  {cast_segment("invokeInput")},
  {cast_segment("invokeResult")},
  0,
  @sys,
  @sys
);
"""
    OUT.write_text(sql, encoding="utf-8")
    print(f"OK: {OUT}")


if __name__ == "__main__":
    main()
