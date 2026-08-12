from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from lib.cli import log_info
from lib.feature_defaults import compute_feature_defaults

_SCATTER_SAMPLE_SIZES = frozenset({0, 500, 1000, 2000})


def _bindings(config: dict[str, Any]) -> list[str]:
    features = config.get("features")
    if not features or not isinstance(features, list):
        raise ValueError("config requires features[]")
    return [str(f) for f in features]


def _hyperparams(config: dict[str, Any]) -> tuple[int, bool, int]:
    n_clusters = int(config.get("nClusters", 4))
    standardize = bool(config.get("standardize", True))
    if n_clusters < 2:
        raise ValueError("config.nClusters must be >= 2")
    #
    raw = config.get("scatterSampleSize", 0)
    scatter_n = int(raw) if raw is not None else 0
    if scatter_n not in _SCATTER_SAMPLE_SIZES:
        raise ValueError("config.scatterSampleSize must be one of 0, 500, 1000, 2000")
    return n_clusters, standardize, scatter_n


def _sample_indices(
    labels: np.ndarray, max_n: int, n_clusters: int, rng: np.random.Generator
) -> np.ndarray:
    """按簇比例分层抽样，总量不超过 max_n。"""
    n = len(labels)
    if n <= max_n:
        return np.arange(n)
    #
    counts = np.bincount(labels, minlength=n_clusters).astype(float)
    total = float(counts.sum())
    if total <= 0:
        return np.arange(min(max_n, n))
    #
    raw = max_n * counts / total
    quotas = np.floor(raw).astype(int)
    for c in range(n_clusters):
        if counts[c] > 0 and quotas[c] == 0:
            quotas[c] = 1
    #
    while int(quotas.sum()) > max_n:
        c = int(np.argmax(quotas))
        if quotas[c] > 1:
            quotas[c] -= 1
        else:
            break
    #
    while int(quotas.sum()) < max_n:
        remainders = raw - quotas
        candidates = [c for c in range(n_clusters) if quotas[c] < counts[c]]
        if not candidates:
            break
        c = max(candidates, key=lambda i: remainders[i])
        quotas[c] += 1
    #
    parts: list[np.ndarray] = []
    for c in range(n_clusters):
        pool = np.where(labels == c)[0]
        k = min(len(pool), int(quotas[c]))
        if k <= 0:
            continue
        parts.append(rng.choice(pool, size=k, replace=False))
    if not parts:
        return np.arange(min(max_n, n))
    return np.concatenate(parts)


def _pad_to_2d(xy: np.ndarray) -> np.ndarray:
    if xy.ndim != 2:
        raise ValueError("expected 2d array")
    if xy.shape[1] >= 2:
        return xy[:, :2]
    if xy.shape[1] == 1:
        return np.column_stack([xy[:, 0], np.zeros(len(xy))])
    return np.zeros((len(xy), 2))


def _build_scatter_payload(
    x_train: np.ndarray,
    labels: np.ndarray,
    centers: np.ndarray,
    sample_size: int,
    n_clusters: int,
) -> dict[str, Any]:
    """PCA→2D 后分层抽样；返回 scatterPoints / pcaCenters。"""
    rng = np.random.default_rng(42)
    n_comp = min(2, x_train.shape[1], x_train.shape[0])
    if n_comp < 1:
        raise ValueError("cannot build scatter: empty training matrix")
    #
    pca = PCA(n_components=n_comp, random_state=42)
    xy_all = _pad_to_2d(pca.fit_transform(x_train))
    center_xy = _pad_to_2d(pca.transform(centers))
    #
    idx = _sample_indices(labels, sample_size, n_clusters, rng)
    points = [
        {
            "x": float(xy_all[i, 0]),
            "y": float(xy_all[i, 1]),
            "clusterId": int(labels[i]),
        }
        for i in idx
    ]
    return {
        "scatterPoints": points,
        "pcaCenters": center_xy.tolist(),
        "scatterSampleSize": len(points),
    }


def _round_float(value: float, ndigits: int = 4) -> float:
    return float(round(float(value), ndigits))


def _feature_dict(features: list[str], values: np.ndarray, ndigits: int = 4) -> dict[str, float]:
    return {f: _round_float(values[i], ndigits) for i, f in enumerate(features)}


def _vs_global_mark(center: float, mean: float, std: float) -> str:
    """相对全局: above / below / near(约 0.25σ 内)."""
    band = max(abs(std) * 0.25, 1e-9)
    if center > mean + band:
        return "above"
    if center < mean - band:
        return "below"
    return "near"


def _build_cluster_profiles(
    df: pd.DataFrame,
    features: list[str],
    labels: np.ndarray,
    centers_std: np.ndarray,
    centers_raw: np.ndarray,
    cluster_sizes: list[int],
) -> list[dict[str, Any]]:
    """训期可计算的簇画像: 原始中心/分位/相对全局/可查询门槛(无业务 label)."""
    total = max(int(sum(cluster_sizes)), 1)
    global_mean = df[features].astype(float).mean()
    global_std = df[features].astype(float).std(ddof=0).fillna(0.0)
    #
    profiles: list[dict[str, Any]] = []
    for cid, size in enumerate(cluster_sizes):
        sub = df.loc[labels == cid, features].astype(float)
        percentiles: dict[str, dict[str, float]] = {}
        for f in features:
            series = sub[f] if len(sub) else pd.Series(dtype=float)
            qs = series.quantile([0.1, 0.25, 0.5, 0.75, 0.9]) if len(series) else None
            percentiles[f] = {
                "p10": _round_float(float(qs.loc[0.1])) if qs is not None else 0.0,
                "p25": _round_float(float(qs.loc[0.25])) if qs is not None else 0.0,
                "p50": _round_float(float(qs.loc[0.5])) if qs is not None else 0.0,
                "p75": _round_float(float(qs.loc[0.75])) if qs is not None else 0.0,
                "p90": _round_float(float(qs.loc[0.9])) if qs is not None else 0.0,
            }
        #
        center_raw = _feature_dict(features, centers_raw[cid])
        vs_global: dict[str, str] = {}
        rules: list[dict[str, Any]] = []
        for f in features:
            mark = _vs_global_mark(
                float(center_raw[f]), float(global_mean[f]), float(global_std[f])
            )
            vs_global[f] = mark
            # 偏高簇用 P25 下界; 偏低簇用 P75 上界; near 不写门槛
            if mark == "above":
                rules.append(
                    {
                        "feature": f,
                        "op": "gte",
                        "value": percentiles[f]["p25"],
                    }
                )
            elif mark == "below":
                rules.append(
                    {
                        "feature": f,
                        "op": "lte",
                        "value": percentiles[f]["p75"],
                    }
                )
        #
        profiles.append(
            {
                "clusterId": cid,
                "size": int(size),
                "share": _round_float(size / total, 4),
                "centerRaw": center_raw,
                "centerStd": _feature_dict(features, centers_std[cid]),
                "percentiles": percentiles,
                "vsGlobal": vs_global,
                "queryHint": {
                    "logic": "and",
                    "rules": rules,
                    "note": "Approximate thresholds from in-cluster percentiles; overlaps possible",
                },
            }
        )
    return profiles


def _reorder_clusters_by_size(
    model: KMeans, labels: np.ndarray, n_clusters: int
) -> tuple[np.ndarray, np.ndarray, list[int]]:
    """按簇样本量升序重标号; 同步 model.cluster_centers_ 使 predict 与 summary 一致."""
    sizes = np.bincount(labels, minlength=n_clusters)
    # 升序; 同人数时保持原相对顺序
    order = np.argsort(sizes, kind="stable")
    remap = np.empty(n_clusters, dtype=int)
    for new_id, old_id in enumerate(order):
        remap[int(old_id)] = int(new_id)
    #
    new_labels = remap[labels]
    new_centers = model.cluster_centers_[order]
    model.cluster_centers_ = new_centers
    if getattr(model, "labels_", None) is not None:
        model.labels_ = new_labels
    new_sizes = [int(v) for v in np.bincount(new_labels, minlength=n_clusters)]
    return new_labels, new_centers, new_sizes


def train_from_csv(
    csv_path: Path, config: dict[str, Any], data_meta: dict[str, Any], out_dir: Path
) -> dict[str, Any]:
    features = _bindings(config)
    n_clusters, standardize, scatter_n = _hyperparams(config)
    log_info(
        f">>> KMeans: n_clusters={n_clusters}, standardize={standardize}, "
        f"scatterSampleSize={scatter_n}, features={len(features)}"
    )

    df = pd.read_csv(csv_path)
    missing = [c for c in features if c not in df.columns]
    if missing:
        raise ValueError(f"CSV missing columns: {missing}")

    x = df[features].astype(float).values
    if len(x) < n_clusters:
        raise ValueError("Not enough rows for nClusters")

    scaler = StandardScaler() if standardize else None
    x_train = scaler.fit_transform(x) if scaler else x

    model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = model.fit_predict(x_train)
    log_info(">>> 聚类完成，计算轮廓系数")

    sil = float(silhouette_score(x_train, labels)) if n_clusters > 1 and len(set(labels)) > 1 else 0.0
    inertia = float(model.inertia_)
    # 按样本量升序重标号(最少→簇0), 保证 summary 与 predict 一致
    labels, centers_std, cluster_sizes = _reorder_clusters_by_size(model, labels, n_clusters)
    log_info(f">>> 已按簇人数升序重标号 sizes={cluster_sizes}")
    centers_raw = scaler.inverse_transform(centers_std) if scaler is not None else centers_std
    #
    log_info(">>> 计算簇画像(原始中心/分位/queryHint)")
    cluster_profiles = _build_cluster_profiles(
        df, features, labels, centers_std, centers_raw, cluster_sizes
    )

    bundle = {"model": model, "scaler": scaler, "standardize": standardize}
    meta = {
        "algorithmCode": "kmeans",
        "features": features,
        "nClusters": n_clusters,
        "standardize": standardize,
        "centers": centers_std.tolist(),
        "centersRaw": centers_raw.tolist(),
        "clusterSizes": cluster_sizes,
        "featureDefaults": compute_feature_defaults(df, features),
    }
    #
    summary: dict[str, Any] = {
        "status": "ok",
        "silhouette": sil,
        "inertia": inertia,
        "features": features,
        "centers": meta["centers"],
        "centersRaw": meta["centersRaw"],
        "clusterSizes": cluster_sizes,
        "clusterProfiles": cluster_profiles,
    }
    if scatter_n > 0:
        log_info(f">>> 生成 PCA 散点样例，上限={scatter_n}")
        scatter = _build_scatter_payload(
            x_train, labels, centers_std, scatter_n, n_clusters
        )
        # 散点写入独立文件, 不进 summary(避免进入 LLM 上下文)
        scatter_name = "scatter.json"
        (out_dir / scatter_name).write_text(
            json.dumps(scatter, ensure_ascii=False), encoding="utf-8"
        )
        summary["scatterFile"] = f"artifacts/{scatter_name}"
        meta["pcaCenters"] = scatter["pcaCenters"]
        meta["scatterSampleSize"] = scatter["scatterSampleSize"]
        meta["scatterFile"] = summary["scatterFile"]
    #
    joblib.dump(bundle, out_dir / "model.joblib")
    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    log_info(f">>> 指标: silhouette={sil:.6f}, inertia={inertia:.6f}, sizes={cluster_sizes}")
    return summary


def _feature_bag(invoke_input: dict[str, Any]) -> dict[str, Any]:
    bag = invoke_input.get("features")
    if bag is None:
        return {}
    if not isinstance(bag, dict):
        raise ValueError("invokeInput.features must be an object")
    return bag


def _read_feature_values(invoke_input: dict[str, Any], features: list[str]) -> list[float]:
    bag = _feature_bag(invoke_input)
    row: list[float] = []
    for name in features:
        if name not in bag:
            raise ValueError(f"invokeInput.features missing key: {name}")
        row.append(float(bag[name]))
    return row


def invoke_assign(artifact_dir: Path, invoke_input: dict[str, Any]) -> dict[str, Any]:
    meta = json.loads((artifact_dir / "meta.json").read_text(encoding="utf-8"))
    features: list[str] = meta["features"]
    row = np.array([_read_feature_values(invoke_input, features)])
    bundle = joblib.load(artifact_dir / "model.joblib")
    model = bundle["model"]
    scaler = bundle.get("scaler")
    if bundle.get("standardize") and scaler is not None:
        row = scaler.transform(row)

    cluster_id = int(model.predict(row)[0])
    dist = float(np.linalg.norm(row[0] - model.cluster_centers_[cluster_id]))
    # 训练期簇规模（旧产物无此字段则省略）
    raw_sizes = meta.get("clusterSizes")
    cluster_sizes = (
        [int(x) for x in raw_sizes]
        if isinstance(raw_sizes, list)
        else None
    )

    result: dict[str, Any] = {
        "status": "ok",
        "clusterId": cluster_id,
        "distanceToCenter": dist,
        "features": features,
        "centers": model.cluster_centers_.tolist(),
    }
    if cluster_sizes is not None:
        result["clusterSizes"] = cluster_sizes
    return result
