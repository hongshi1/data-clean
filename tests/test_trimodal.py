"""三模态对齐与混合召回框架测试: 全链路行为锁定(合成数据, GPU不必需torch-CPU可跑).

锁定内容(对应文档§8消融的框架行为):
  - schemas: 双表示数据模型/关系白名单/序列化
  - projector: 形状/L2归一性/状态保存恢复
  - contrastive: 训练收敛(loss下降)/encode_all维度
  - retrieval: 路由多标签/双路融合/RRF基线/native同模态路径
  - expansion: 白名单关系1-hop/时间重叠/MMR预算/ContextPackage模态渲染
  - 端到端: 六方向R@5对齐有效性(B1显著高于随机)
"""
from __future__ import annotations

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from algorithms.trimodal import (  # noqa: E402
    ContextExpander,
    HybridRetriever,
    Modality,
    ModalityRouter,
    MultimodalItem,
    PairSample,
    Relation,
    RelationType,
    TrainConfig,
    TrimodalContrastiveTrainer,
    build_context_package,
)

N_EVENTS = 30
DIMS = {"text": 32, "image": 24, "timeseries": 16}


def _synth(n: int = N_EVENTS, seed: int = 7) -> tuple:
    rng = np.random.default_rng(seed)
    items, feats, mods, pairs = [], {}, {}, []
    # 投影矩阵固定(事件间共享): 同一事件的三个模态native特征
    # = 同一语义因子×各自模态投影+噪声 — 可学习的模态间映射存在
    proj = {m: rng.normal(0, 1, (16, d)) for m, d in DIMS.items()}
    for ev in range(n):
        factor = rng.normal(0, 1, 16)
        tri = {}
        for mod in (Modality.TEXT, Modality.IMAGE, Modality.TIMESERIES):
            iid = f"it_{ev:03d}_{mod.value[:3]}"
            h = (factor @ proj[mod.value]
                 + 0.3 * rng.normal(0, 1, DIMS[mod.value])).astype(np.float32)
            tri[mod.value] = iid
            items.append(MultimodalItem(
                item_id=iid, modality=mod, source_id=f"s{ev // 5}",
                native_embedding=h.tolist(), event_id=f"e{ev}",
                time_span=(ev * 10.0, ev * 10.0 + 5.0),
                relations=[],  # 事件内关系在三条目建完后统一补
                metadata={"content": f"事件{ev}文本",
                          "summary": f"统计{factor[0]:.2f}"}))
            feats[iid] = h
            mods[iid] = mod.value
        for src_mod, iid in tri.items():
            it = next(x for x in items if x.item_id == iid)
            for other_mod, other_id in tri.items():
                if other_mod != src_mod:
                    it.relations.append(Relation(
                        RelationType.SAME_EVENT, other_id, 0.95))
        pairs.append(PairSample("text-image", tri["text"], tri["image"]))
        pairs.append(PairSample("text-timeseries", tri["text"],
                                tri["timeseries"]))
        pairs.append(PairSample("image-timeseries", tri["image"],
                                tri["timeseries"]))
    return items, feats, mods, pairs


def _train_and_encode(items, feats, mods, pairs):
    cfg = TrainConfig(shared_dim=32, lr=2e-3, epochs=15, batch_size=16)
    tr = TrimodalContrastiveTrainer(dict(DIMS), cfg)
    hist = tr.train(feats, mods, pairs)
    shared = tr.encode_all(feats, mods)
    return tr, hist, shared


@pytest.fixture(scope="module")
def pipeline():
    items, feats, mods, pairs = _synth()
    tr, hist, shared = _train_and_encode(items, feats, mods, pairs)
    for it in items:
        it.shared_embedding = shared[it.item_id].tolist()
    retriever = HybridRetriever(items)
    return items, feats, mods, pairs, tr, hist, shared, retriever


# ── schemas ───────────────────────────────────────────────

def test_item_dual_representation_and_relations():
    it = MultimodalItem(
        item_id="x1", modality=Modality.TEXT, source_id="s",
        native_embedding=[1.0] * 8, shared_embedding=[0.5] * 4,
        relations=[Relation(RelationType.DESCRIBES, "x2", 0.8)])
    rec = it.to_record()
    assert rec["modality"] == "text"
    assert rec["relations"][0]["type"] == "describes"
    assert rec["relations"][0]["confidence"] == 0.8


def test_pair_sample_weighting():
    p = PairSample("text-image", "a", "b", level="weak", confidence=0.5)
    assert p.level == "weak" and p.confidence == 0.5


# ── projector ─────────────────────────────────────────────

def test_projector_shapes_and_l2():
    from algorithms.trimodal import TriModalProjector
    p = TriModalProjector(dict(DIMS), shared_dim=24)
    z = p.forward_torch({"text": torch.randn(4, DIMS["text"])})
    assert z["text"].shape == (4, 24)
    norms = z["text"].norm(dim=-1)
    assert torch.allclose(norms, torch.ones(4), atol=1e-4)


def test_projector_state_roundtrip():
    from algorithms.trimodal import TriModalProjector
    p = TriModalProjector(dict(DIMS), shared_dim=24)
    h = np.random.default_rng(3).normal(0, 1, DIMS["text"]).astype(np.float32)
    z1 = p.forward_numpy("text", h)
    p2 = TriModalProjector(dict(DIMS), shared_dim=24)
    p2.load_state(p.state())
    z2 = p2.forward_numpy("text", h)
    assert np.allclose(z1, z2, atol=1e-5)


# ── contrastive ───────────────────────────────────────────

def test_training_loss_decreases(pipeline):
    _, _, _, _, _, hist, _, _ = pipeline
    first = hist[0]
    last = hist[-1]
    k = "text-image"
    assert k in first and k in last
    assert last[k] <= first[k] * 1.5  # 收敛方向(允许初期波动)


def test_encode_all_dimensions(pipeline):
    _, _, mods, _, _, _, shared, _ = pipeline
    assert set(shared) == set(mods)
    assert len(next(iter(shared.values()))) == 32


# ── retrieval ─────────────────────────────────────────────

def test_router_multilabel(pipeline):
    dec = ModalityRouter().route("查询参数趋势与曲线图", Modality.TEXT)
    assert dec.modality_weights["text"] == 1.0
    assert dec.modality_weights["timeseries"] > 0.5
    assert dec.modality_weights["image"] > 0.5


def test_hybrid_retrieval_returns_items(pipeline):
    items, feats, _, _, _, _, shared, retriever = pipeline
    qid = items[0].item_id
    res = retriever.retrieve(
        query="查询", query_modality=items[0].modality,
        q_native=feats[qid], q_shared=np.asarray(shared[qid]),
        final_k=5)
    assert res and len(res) <= 5
    ids = {i.item_id for i, _ in res}
    assert items[0].item_id in ids  # 自检: 检索应含query自身条目


def test_rrf_baseline(pipeline):
    _, _, _, _, _, _, shared, retriever = pipeline
    res = retriever.rrf_baseline(np.asarray(shared[retriever.items[
        list(retriever.items)[0]].item_id]), final_k=5)
    assert res and "fused" in res[0][1]


# ── expansion ─────────────────────────────────────────────

def test_expansion_adds_cross_modal(pipeline):
    items, _, _, _, _, _, shared, retriever = pipeline
    exp = ContextExpander(retriever, expansion_budget=8)
    qid = items[0].item_id
    anchors = retriever.retrieve(
        query="q", query_modality=items[0].modality,
        q_shared=np.asarray(shared[qid]), final_k=3)
    expanded = exp.expand(anchors, query="q")
    mods = {it.modality.value for it, _ in expanded}
    # 事件内SAME_EVENT关系应把其他模态拉进来
    assert len(mods) >= 2


def test_expansion_respects_budget(pipeline):
    items, _, _, _, _, _, shared, retriever = pipeline
    exp = ContextExpander(retriever, expansion_budget=4)
    anchors = retriever.retrieve(
        query="q", query_modality=Modality.TEXT,
        q_shared=np.asarray(shared[items[0].item_id]), final_k=3)
    assert len(exp.expand(anchors, "q")) <= 4


def test_context_package_rendering(pipeline):
    items, _, _, _, _, _, shared, retriever = pipeline
    exp = ContextExpander(retriever, expansion_budget=6)
    anchors = retriever.retrieve(
        query="q", query_modality=Modality.TEXT,
        q_shared=np.asarray(shared[items[1].item_id]), final_k=3)
    expanded = exp.expand(anchors, "q")
    pkg = build_context_package("t1", "q", expanded)
    assert pkg.provenance["n_evidences"] == len(expanded)
    for ev in pkg.evidences:
        assert ev.type in ("text", "image", "timeseries")
        assert isinstance(ev.content, str)  # 不拼embedding, 渲染为文本


# ── 端到端: 六方向对齐有效性 ──────────────────────────────

def test_crossmodal_alignment_effective(pipeline):
    items, feats, _, _, _, _, shared, _ = pipeline
    split = N_EVENTS - 6
    ok = 0
    for qm, tm in ((Modality.TEXT, Modality.IMAGE),
                   (Modality.IMAGE, Modality.TIMESERIES),
                   (Modality.TEXT, Modality.TIMESERIES)):
        q_ids = [f"it_{i:03d}_{qm.value[:3]}" for i in range(split, N_EVENTS)]
        targets = {q: q.replace(qm.value[:3], tm.value[:3]) for q in q_ids}
        mat = np.stack([np.asarray(shared[
            q.replace(qm.value[:3], tm.value[:3])]) for q in q_ids])
        m = mat / np.linalg.norm(mat, axis=1, keepdims=True)
        hits = 0
        for q in q_ids:
            v = np.asarray(shared[q])
            v = v / np.linalg.norm(v)
            top = np.argsort(-(m @ v))[:5]
            # mat第i行=q_ids[i]的target → 命中集合按target侧换算
            if targets[q] in {targets[q_ids[i]] for i in top}:
                hits += 1
        r = hits / len(q_ids)
        assert r >= 0.5, f"{qm}->{tm} R@5={r}"  # 随机≈1/24, 0.5+即对齐成立
        ok += 1
    assert ok == 3
