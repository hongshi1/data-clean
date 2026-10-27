r"""86条裁决任务的最终仲裁: 机器意见(NLI) + 双LLM裁决融合(P3收尾).

协议(升级银标生产的三方融合):
  票1·机器意见: NLI sym信号(annotation_auto的compiler刀, 构造真值背书)
  票2·kimi: 看分歧证据+两侧声明的文本(语义判断)
  票3·GLM: 同输入独立判断(模型异构)
  融合: 2/3多数 → 标签; 无多数 → unsure(诚实保留)

LLM调用走llm_client缓存接口(cache=True, 可复现).
判定协议: 复用银标生产的四条优先级细则(对应性→惯例→声称覆盖→
举证责任在报bug方).

用法: python tools/annotation_llm.py [--limit N]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.common.llm_client import llm_json  # noqa: E402

TASKS86 = BASE / "data/gjb_438c/anchor_sc2/adjudication/adjudication_tasks.json"
MACHINE = BASE / "data/gjb_438c/human_gold/machine_gold_86.json"
SILVER = BASE / "data/gjb_438c/anchor_v2/final_adjudication.json"
OUT = BASE / "data/gjb_438c/human_gold/final_gold_86.json"

SYSTEM = """你是需求文档一致性裁决专家. 判断表格与图之间的分歧属于哪类:
- real_bug: 真实文档缺陷 — 文档该表示的内容图里确实缺失/矛盾, 需求工程师应修
- benign_variation: 合理差异 — 绘图惯例/粒度取舍(如流程图按惯例不画Actor、图只画主要项)
- compiler_bug: 引擎误报 — 图中实际有对应元素, 只是表述差异导致自动匹配失败
判定优先级(从高到低):
1. 图中存在语义对应元素 → compiler_bug
2. 图按惯例本就不画此类内容 → benign_variation
3. 文档声称图覆盖该类内容而图确实缺失 → real_bug
4. 拿不准 → benign_variation(举证责任在报缺陷方)
只输出JSON: {"label": "real_bug|benign_variation|compiler_bug", "reason": "一句话"}"""


def build_prompt(task: dict, machine: dict) -> str:
    nli = machine.get("nli_sym")
    nli_txt = {"矛盾": "NLI双向推理判定内容矛盾(内容真不一致)",
               "非矛盾": "NLI判定非矛盾(内容可能一致, 图里可能有)"}.get(nli, "NLI不适用")
    return f"""分歧任务 {task['task_id']}:
分歧类型: {task.get('dtype', '')}
分歧证据: {task.get('evidence', '')}
表格侧: {json.dumps(task.get('table_side') or {}, ensure_ascii=False)[:150]}
图侧: {json.dumps(task.get('diag_side') or {}, ensure_ascii=False)[:150]}
上下文: 用例「{task.get('uc_name', '')}」| {task.get('image_caption', '')} vs {task.get('table_caption', '')}
| 表{task.get('n_table_steps', '?')}项/图{task.get('n_diag_nodes', '?')}节点/匹配{task.get('n_matched', '?')} | 词法匹配分{task.get('match_score', '')}
机器意见(参考, 非决定性): {nli_txt}
请三分类."""


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    tasks = json.loads(TASKS86.read_text(encoding="utf-8"))
    machine = json.loads(MACHINE.read_text(encoding="utf-8"))["labels"]
    if args.limit:
        tasks = tasks[:args.limit]
    print(f"任务: {len(tasks)}条 | 双LLM(kimi+GLM)裁决+机器意见融合")

    results: dict[str, dict] = {}
    n_llm = 0
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _judge(t: dict) -> tuple[str, dict]:
        tid = t["task_id"]
        m = machine.get(tid, {})
        prompt = build_prompt(t, m)
        votes = {}
        for model in ("kimi", "glm"):
            try:
                r, _used = llm_json(prompt, system=SYSTEM, prefer=model,
                                    cache=True)
                label = r.get("label", "") if isinstance(r, dict) else ""
                votes[model] = label if label in (
                    "real_bug", "benign_variation", "compiler_bug") else ""
            except Exception as e:
                votes[model] = ""
                print(f"  ⚠ {tid} {model}: {type(e).__name__} {str(e)[:60]}")
        mv = "compiler_bug" if m.get("label") == "compiler_bug" else ""
        tally = {"real_bug": 0, "benign_variation": 0, "compiler_bug": 0}
        for v in list(votes.values()) + [mv]:
            if v in tally:
                tally[v] += 1
        best = max(tally, key=tally.get)
        final = best if tally[best] >= 2 else "unsure"
        return tid, {"label": final, "pair": t["pair_key"],
                     "dtype": t.get("dtype", ""),
                     "votes": {**votes, "machine": mv or "-"},
                     "reason": "多数决" if final != "unsure" else "无多数"}

    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(_judge, t): t for t in tasks}
        n_done = 0
        for fut in as_completed(futs):
            tid, rec = fut.result()
            results[tid] = rec
            n_done += 1
            n_llm += 2
            if n_done % 20 == 0:
                print(f"  进度: {n_done}/{len(tasks)}")

    from collections import Counter
    dist = Counter(r["label"] for r in results.values())
    print(f"\n最终仲裁: {len(results)}条 | 分布: {dict(dist)}")
    print(f"LLM调用: {n_llm}次(走缓存)")

    OUT.write_text(json.dumps({
        "n": len(results), "dist": dict(dist), "labels": results,
        "protocol": "机器意见(NLI)+kimi+GLM三方融合, 2/3多数决",
        "llm_cache": "llm_client cache=True", "date": "2026-09-16"},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"金标 → {OUT}")

    # 与664银标对比
    silver = json.loads(SILVER.read_text(encoding="utf-8"))["final_labels"]
    overlap = [(k, results[k]["label"], silver[k]["label"])
               for k in results if k in silver]
    if overlap:
        agree = sum(1 for _, g, s in overlap if g == s)
        print(f"\n与664银标对比: 重叠{len(overlap)}条, 三方融合一致"
              f"{agree}({agree/len(overlap):.0%})")
        conf = Counter(f"{g}|{s}" for _, g, s in overlap if g != s)
        print("分歧模式(融合|银标):", dict(conf))


if __name__ == "__main__":
    main()
