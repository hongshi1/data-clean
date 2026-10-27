r"""三模态对齐与混合召回 — 端到端演示与消融 (合成数据).

复现文档§12 P0-P6的最小闭环(合成三模态语料替代真实数据):
  P1 对齐训练 → 六方向R@K(B0无对齐 vs B1投影后)
  P3 混合检索(路由+双路融合) vs RRF基线(§8.4 B1/B2对照)
  P5 上下文扩展(关系图1-hop+MMR) → ContextPackage(§7.4)

合成协议: 每个"事件"有文本+图像+时序三个条目(共享语义因子),
native特征=语义因子经模态特定随机投影+噪声(模拟冻结编码器的
异构空间 — B0天然不对齐, 训练后B1应可跨模态检索).

用法: python tools/trimodal_demo.py [--n-events 120]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.context_association.trimodal import (  # noqa: E402
    Modality,
    MultimodalItem,
    PairSample,
    Relation,
    RelationType,
    TrainConfig,
    TrimodalContrastiveTrainer,
    ContextExpander,
    HybridRetriever,
    ModalityRouter,
    build_context_package,
)

_SEED = 42
_NATIVE_DIMS = {"text": 64, "image": 48, "timeseries": 32}  # 演示量级


def synth_events(n_events: int, noise: float = 0.35,
                 seed: int = _SEED) -> tuple[list[MultimodalItem],
                                             list[PairSample],
                                             dict[str, np.ndarray],
                                             dict[str, str]]:
    """合成三模态语料: 每事件{text,image,ts}三条目共享语义因子."""
    rng = np.random.default_rng(seed)
    sem_dim = 32
    # 模态特定投影(模拟冻结编码器的异构映射, 不可逆)
    proj = {m: rng.normal(0, 1.0, (sem_dim, d))
            for m, d in _NATIVE_DIMS.items()}
    items: list[MultimodalItem] = []
    features: dict[str, np.ndarray] = {}
    modality_map: dict[str, str] = {}
    pairs: list[PairSample] = []
    for ev in range(n_events):
        factor = rng.normal(0, 1, sem_dim)
        eid = f"event_{ev:04d}"
        ts_start = float(ev * 100)
        for mod in (Modality.TEXT, Modality.IMAGE, Modality.TIMESERIES):
            iid = f"it_{ev:03d}_{mod.value[:3]}"
            h = factor @ proj[mod.value] + noise * rng.normal(
                0, 1, _NATIVE_DIMS[mod.value])
            it = MultimodalItem(
                item_id=iid, modality=mod, source_id=f"src_{ev // 10:02d}",
                native_embedding=h.tolist(), entity_id=f"eng_{ev % 7}",
                event_id=eid,
                time_span=(ts_start, ts_start + 50.0),
                relations=[], payload_ref=f"payload://{iid}",
                metadata={"content": f"事件{ev}的{mod.value}证据",
                          "summary": f"窗口统计均值{factor[0]:.2f}",
                          "caption": f"事件{ev}曲线图" if mod is Modality.IMAGE
                          else ""})
            items.append(it)
            features[iid] = h.astype(np.float32)
            modality_map[iid] = mod.value
        # 关系: 事件内三条目互连(SAME_EVENT强关系)
        tri = [f"it_{ev:03d}_tex", f"it_{ev:03d}_ima", f"it_{ev:03d}_tim"]
        for a in tri:
            for b in tri:
                if a != b:
                    it = next(x for x in items if x.item_id == a)
                    it.relations.append(Relation(
                        RelationType.SAME_EVENT, b, confidence=0.95))
        # generated_from桥: 时序→图像
        ts_it = next(x for x in items if x.item_id == tri[2])
        ts_it.relations.append(Relation(
            RelationType.GENERATED_FROM, tri[1], confidence=0.9))
        # 训练对: 三对模态各一(强)
        pairs.append(PairSample("text-image", tri[0], tri[1]))
        pairs.append(PairSample("text-timeseries", tri[0], tri[2]))
        pairs.append(PairSample("image-timeseries", tri[1], tri[2]))
        # 弱正样本: 同源文档相邻事件(置信0.5)
        if ev > 0:
            pairs.append(PairSample(
                "text-image", f"it_{ev - 1:03d}_tex", tri[1],
                level="weak", confidence=0.5,
                relation_type=RelationType.SAME_SOURCE))
    return items, pairs, features, modality_map


def recall_at_k(query_vecs: dict[str, np.ndarray],
                targets: dict[str, str], mat: np.ndarray,
                ids: list[str], k: int = 5) -> float:
    """单方向R@K: 用query向量在mat(ids)里检索, 目标命中即得."""
    hits = 0
    m = mat / np.maximum(np.linalg.norm(mat, axis=1, keepdims=True), 1e-8)
    for qid, q in query_vecs.items():
        qn = q / max(np.linalg.norm(q), 1e-8)
        sims = m @ qn
        top = np.argsort(-sims)[:k]
        got = {ids[i] for i in top}
        if targets[qid] in got:
            hits += 1
    return hits / max(len(query_vecs), 1)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-events", type=int, default=120)
    args = ap.parse_args()

    items, pairs, features, modality_map = synth_events(args.n_events)
    print(f"合成语料: {len(items)}条目({args.n_events}事件×3模态), "
          f"{len(pairs)}训练对")

    # ═══ P1: 对齐训练 (B0 vs B1, §8.4) ═══
    split = int(args.n_events * 0.8)
    train_ids = {f"it_{i:03d}_{m}" for i in range(split)
                 for m in ("tex", "ima", "tim")}
    train_pairs = [p for p in pairs
                   if p.a_id in train_ids and p.b_id in train_ids]
    t0 = time.time()
    cfg = TrainConfig(shared_dim=64, lr=1e-3, epochs=30,
                      batch_size=48, temperature=0.07)
    trainer = TrimodalContrastiveTrainer(dict(_NATIVE_DIMS), cfg)
    trainer.train({i: f for i, f in features.items()
                   if i in train_ids}, modality_map, train_pairs)
    t_train = time.time() - t0
    print(f"训练: {t_train:.1f}s, {len(train_pairs)}对")

    # shared embedding全量产出
    shared = trainer.encode_all(features, modality_map)
    for it in items:
        it.shared_embedding = shared[it.item_id].tolist()

    # ═══ 六方向R@5评测 (测试集=后20%事件; §8.1) ═══
    test_events = range(split, args.n_events)
    directions = [
        ("T→I", Modality.TEXT, Modality.IMAGE),
        ("I→T", Modality.IMAGE, Modality.TEXT),
        ("T→S", Modality.TEXT, Modality.TIMESERIES),
        ("S→T", Modality.TIMESERIES, Modality.TEXT),
        ("I→S", Modality.IMAGE, Modality.TIMESERIES),
        ("S→I", Modality.TIMESERIES, Modality.IMAGE)]
    print("\n══ 六方向R@5 (B0 native直算 vs B1投影后) ══")
    print("  (B0: 异构native空间维度不同, 跨模态直接比较不可定义 —"
          " 即文档§1.3'独立encoder无coupling不自然对齐')")
    for name, qm, tm in directions:
        q_ids = [f"it_{i:03d}_{qm.value[:3]}" for i in test_events]
        t_ids = [f"it_{i:03d}_{tm.value[:3]}" for i in test_events]
        targets = {q: q.replace(qm.value[:3], tm.value[:3]) for q in q_ids}
        # B0: 仅当两侧native维度一致时才可直算(演示多数方向不可比)
        qd, td = _NATIVE_DIMS[qm.value], _NATIVE_DIMS[tm.value]
        if qd == td:
            b0_q = np.stack([features[i] for i in q_ids])
            b0_t = np.stack([features[i] for i in t_ids])
            b0 = recall_at_k({q: b0_q[idx] for idx, q in enumerate(q_ids)},
                             targets, b0_t, t_ids)
            b0_str = f"{b0:.3f}"
        else:
            b0_str = f"—({qd}d↔{td}d)"
        b1_q = np.stack([shared[i] for i in q_ids])
        b1_t = np.stack([shared[i] for i in t_ids])
        b1 = recall_at_k({q: b1_q[idx] for idx, q in enumerate(q_ids)},
                         targets, b1_t, t_ids)
        print(f"  {name}: B0={b0_str}  B1={b1:.3f}")

    # ═══ P3: 混合检索 vs RRF基线 (B2 vs B4, §8.4) ═══
    retriever = HybridRetriever(items, top_k_per_index=100)
    router = ModalityRouter()
    qev = split + 3
    q_text_id = f"it_{qev:03d}_tex"
    print(f"\n══ 检索演示(query=事件{qev}的文本) ══")
    dec = router.route("查询该事件的参数趋势与处置说明",
                       Modality.TEXT)
    print(f"  路由: {dec.modality_weights}")
    hyb = retriever.retrieve(
        query="查询该事件的参数趋势与处置说明",
        query_modality=Modality.TEXT,
        q_native=np.asarray(features[q_text_id], dtype=np.float32),
        q_shared=shared[q_text_id],
        decision=dec, final_k=6)
    print("  hybrid融合Top-6: " + ", ".join(
        f"{i.item_id}({i.modality.value[:4]})" for i, _ in hyb))
    rrf = retriever.rrf_baseline(shared[q_text_id], final_k=6)
    print("  RRF基线Top-6:   " + ", ".join(
        f"{i.item_id}({i.modality.value[:4]})" for i, _ in rrf))

    # ═══ P5: 上下文扩展 → ContextPackage (§7) ═══
    exp = ContextExpander(retriever, expansion_budget=10)
    expanded = exp.expand(hyb, query="查询该事件")
    pkg = build_context_package("demo_q1", "查询该事件", expanded)
    print("\n══ ContextPackage ══")
    print(f"  证据: {pkg.provenance['n_evidences']}条 "
          f"(按模态: {pkg.provenance['by_modality']})")
    print(f"  跨模态链接: {len(pkg.cross_modal_links)}个 "
          f"(同event_id聚合)")
    for ev in pkg.evidences[:5]:
        path = "→".join(ev.relation_path[-1:]) if ev.relation_path else "anchor"
        print(f"    [{ev.type:11s}] {ev.item_id} score={ev.score} {path}")
    with open(BASE / "data/gjb_438c/trimodal_demo_output.json",
              "w", encoding="utf-8") as f:
        import json
        json.dump({"evidences": [
            {"id": e.item_id, "type": e.type, "score": e.score,
             "path": e.relation_path} for e in pkg.evidences],
            "links": pkg.cross_modal_links}, f, ensure_ascii=False, indent=1)
    print("\n(演示输出已落盘 data/gjb_438c/trimodal_demo_output.json)")


if __name__ == "__main__":
    main()
