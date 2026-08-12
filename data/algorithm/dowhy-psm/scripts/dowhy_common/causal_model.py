from __future__ import annotations

from typing import Any

import pandas as pd
from dowhy import CausalModel


def build_causal_model(
    work: pd.DataFrame,
    bindings: dict[str, Any],
    hp: dict[str, Any],
) -> CausalModel:
    cm_cfg = hp.get("causalModel") or {}
    kwargs: dict[str, Any] = {
        "data": work,
        "treatment": bindings["treatment"],
        "outcome": bindings["outcome"],
        "proceed_when_unidentifiable": bool(cm_cfg.get("proceedWhenUnidentifiable", True)),
        "missing_nodes_as_confounders": bool(cm_cfg.get("missingNodesAsConfounders", False)),
        "estimand_type": cm_cfg.get("estimandType", "nonparametric-ate"),
    }

    if bindings.get("graph"):
        kwargs["graph"] = bindings["graph"]
    if bindings.get("confounders"):
        kwargs["common_causes"] = bindings["confounders"]
    if bindings.get("instruments"):
        kwargs["instruments"] = bindings["instruments"]
    if bindings.get("effectModifiers"):
        kwargs["effect_modifiers"] = bindings["effectModifiers"]

    if not bindings.get("graph") and not bindings.get("confounders") and not bindings.get("instruments"):
        raise ValueError("CausalModel requires graph and/or confounders/instruments")

    return CausalModel(**kwargs)
