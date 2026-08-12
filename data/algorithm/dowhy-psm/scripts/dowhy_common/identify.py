from __future__ import annotations

from typing import Any

from dowhy import CausalModel


def identify_effect(model: CausalModel, hp: dict[str, Any]):
    identify_cfg = hp.get("identify") or {}
    cm_cfg = hp.get("causalModel") or {}
    return model.identify_effect(
        estimand_type=cm_cfg.get("estimandType", "nonparametric-ate"),
        method_name=identify_cfg.get("methodName", "default"),
        proceed_when_unidentifiable=bool(cm_cfg.get("proceedWhenUnidentifiable", True)),
        optimize_backdoor=bool(identify_cfg.get("optimizeBackdoor", False)),
    )
