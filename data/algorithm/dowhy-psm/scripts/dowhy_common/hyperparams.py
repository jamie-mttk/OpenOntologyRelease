from __future__ import annotations

from typing import Any

from dowhy_common.config import flat_to_hyperparams, require_config


def parse_hyperparams(config: dict[str, Any]) -> dict[str, Any]:
    return flat_to_hyperparams(require_config(config))
