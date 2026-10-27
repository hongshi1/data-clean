"""SRS-Calib: 场景校准的SRS不一致检测器(本地部署).

方法组成(见 docs/srs_project/local_deploy_report.md):
  - router模式(推荐): 接口场景→v6@0.5(激进); 其余→v9@0.2(1.5B判别最优)
  - balanced模式: 仅v8-CCT, 场景分档阈值(接口0.5/其余0.9)
模型惰性加载(AGENTS.md: 模块顶层零I/O); GPU优先自动降CPU.
"""
from __future__ import annotations

import re

_INTERFACE_PAT = re.compile(r"接口|组件|收发|报文")

_V6 = "models/nli/erlangshen-330m-qlora-v6"
_V8 = "models/nli/erlangshen-330m-qlora-v8-cct"
_V9 = "models/nli/qwen1.5b-qlora-v9-cct"

_CACHE: dict[str, dict] = {}


def _load(model_dir: str):
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(model_dir, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir, local_files_only=True)
    model.to(device).eval()
    id2label = {int(k): str(v).lower() for k, v in model.config.id2label.items()}
    cid = next((k for k, v in id2label.items() if "contra" in v), 0)
    return {"tok": tok, "model": model, "cid": cid, "device": device, "torch": torch}


def _probs(bundle, pairs: list[tuple[str, str]], batch: int = 32) -> list[float]:
    torch = bundle["torch"]
    out: list[float] = []
    with torch.no_grad():
        for i in range(0, len(pairs), batch):
            b = pairs[i:i + batch]
            enc = bundle["tok"]([p for p, _ in b], [h for _, h in b],
                                padding=True, truncation=True, max_length=128,
                                return_tensors="pt").to(bundle["device"])
            logits = bundle["model"](**enc).logits
            out.extend(torch.softmax(logits, dim=-1)[:, bundle["cid"]].cpu().tolist())
    return out


def is_interface(premise: str) -> bool:
    return bool(_INTERFACE_PAT.search(str(premise)))


def _get(key: str, model_dir: str) -> dict:
    if _CACHE.get(key) is None:
        _CACHE[key] = _load(model_dir)
    return _CACHE[key]


def angle_route(scene: str, dtype: str) -> tuple[str, float]:
    """多角度路由表(角度×方法矩阵导出, runs/angle_method_matrix.json).

    返回(模型名, 阈值): 场景×类型 → 该角度实证最优检测器.
    """
    s = str(scene or "")
    d = str(dtype or "")
    if "sc3" in s or "接口" in s:
        return "v6", 0.5
    if "sc1" in s or "sc4" in s or "sc5" in s:
        return "v9", 0.2
    # doc02用例场景按类型
    if "STEP" in d:
        return "mdeberta", 0.5
    if "ACTOR" in d or "DIAGRAM" in d:
        return "v8", 0.5
    if "EXC" in d:
        return "v6", 0.5
    if "ORDER" in d:
        return "v9", 0.5
    return "v9", 0.2


_MODEL_DIRS = {"v6": _V6, "v8": _V8, "v9": _V9, "mdeberta": "models/nli/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"}


def predict(pairs: list[tuple[str, str]], mode: str = "router",
            meta: list[dict] | None = None) -> list[dict]:
    """判定SRS陈述对一致性.

    Args:
        pairs: [(premise, hypothesis), ...]
        mode: "router"(接口v6/其余v9) | "balanced"(仅v8) | "multi-angle"(场景×类型路由, 需meta)
        meta: [{scene, dtype}, ...] — 锚点管线元数据(部署时可得)
    Returns:
        [{"label", "prob", "scene"} 或 multi-angle时含"angle", "model"}, ...]
    """
    if mode not in ("router", "balanced", "multi-angle"):
        raise ValueError(f"未知mode: {mode}")

    if mode == "multi-angle":
        from pathlib import Path
        if meta is None or len(meta) != len(pairs):
            raise ValueError("multi-angle模式需要与pairs等长的meta(scene,dtype)")
        # 按路由分桶
        buckets: dict[tuple[str, float], list[int]] = {}
        for i, m in enumerate(meta):
            key = angle_route(m.get("scene", ""), m.get("dtype", m.get("check_item", "")))
            buckets.setdefault(key, []).append(i)
        results = [None] * len(pairs)
        for (mkey, th), idxs in buckets.items():
            mdir = _MODEL_DIRS[mkey]
            bundle = _get(mkey, mdir) if mkey != "mdeberta" else _get("mdeberta", mdir)
            ps = _probs(bundle, [pairs[i] for i in idxs])
            for i, pr in zip(idxs, ps):
                results[i] = {"label": "inconsistent" if pr >= th else "consistent",
                              "prob": round(pr, 4), "model": mkey, "th": th}
        for i, m in enumerate(meta):
            results[i]["angle"] = f"{m.get('scene', '')[:6]}|{m.get('dtype', m.get('check_item', ''))}"
        return results

    from pathlib import Path
    if mode == "router" and not (Path(_V6).exists() and Path(_V9).exists()):
        mode = "balanced"

    results: list[dict] = []
    if mode == "router":
        v6 = _get("v6", _V6)
        v9 = _get("v9", _V9)
        intf_idx = set(i for i, (p, _h) in enumerate(pairs) if is_interface(p))
        probs = [None] * len(pairs)
        for idxs, bundle in [(sorted(intf_idx), v6), (sorted(set(range(len(pairs))) - intf_idx), v9)]:
            if not idxs:
                continue
            for i, pr in zip(idxs, _probs(bundle, [pairs[i] for i in idxs])):
                probs[i] = pr
        for i, (p, _h) in enumerate(pairs):
            intf = i in intf_idx
            th = 0.5 if intf else 0.2
            results.append({"label": "inconsistent" if probs[i] >= th else "consistent",
                            "prob": round(probs[i], 4),
                            "scene": "interface" if intf else "other"})
    else:
        bundle = _get("v8", _V8)
        for i, pr in enumerate(_probs(bundle, pairs)):
            th = 0.5 if is_interface(pairs[i][0]) else 0.9
            results.append({"label": "inconsistent" if pr >= th else "consistent",
                            "prob": round(pr, 4),
                            "scene": "interface" if is_interface(pairs[i][0]) else "other"})
    return results
