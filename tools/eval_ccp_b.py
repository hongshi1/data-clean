r"""CCP-LLM baseline (ACL 2025 反事实一致性提示) — 全量896条(用户要求: 基线跑全部).

协议: 每对1次调用, 含反事实自检步骤; uncertain→consistent(保守).
输出: data/gjb_438c/ccp_full_baseline.json (增量保存, 4线程, 断点续跑).
"""
from __future__ import annotations

import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))
sys.stdout.reconfigure(encoding="utf-8")

OUT = BASE / "data/gjb_438c/ccp_full_baseline.json"

SYSTEM = "你是SRS顺序一致性审查专家. 使用反事实一致性自检. 只输出JSON."
PROMPT = """判断两段SRS描述中的条目/步骤顺序是否冲突(ORDER CONFLICT检测).

严格按以下步骤:
步骤1: 分别提取两段中的有序条目序列(编号条目如"2、X"按编号, 或顿号列表按出现顺序; 只列关键条目名)
步骤2: 比较两段序列的顺序是否矛盾(同条目相对顺序反转)
步骤3: 反事实自检——交换两段角色重新执行步骤2; 若两次结论矛盾, 判为"uncertain"

描述A: {premise}

描述B: {hypothesis}

输出JSON: {{"seq_A": ["条目1", "条目2"], "seq_B": ["条目1", "条目2"],
 "verdict": "consistent" 或 "inconsistent" 或 "uncertain"}}"""


def parse(text: str) -> str:
    m = re.search(r"\{.*\}", str(text), re.S)
    if not m:
        return "consistent"
    try:
        d = json.loads(m.group())
        v = str(d.get("verdict", "consistent"))
        return v if v in ("consistent", "inconsistent", "uncertain") else "consistent"
    except json.JSONDecodeError:
        return "consistent"


def main() -> None:
    from algorithms.common.llm_client import llm_chat

    data = json.loads((BASE / "data/gjb_438c/family_evalset_v1.json").read_text(encoding="utf-8"))["pairs"]
    all_ids = [x["id"] for x in data]
    print(f"CCP-LLM全量: {len(data)}条, 4线程(B族67条已有缓存)")

    id2pred: dict[str, str] = {}
    # 播种旧B族结果(ccp_b_baseline.json, 67条)
    old = BASE / "data/gjb_438c/ccp_b_baseline.json"
    if old.exists():
        ob = json.loads(old.read_text(encoding="utf-8"))
        for oid, op in zip(ob.get("meta", {}).get("ids", []), ob.get("preds", []), strict=False):
            if isinstance(op, str) and op in ("consistent", "inconsistent"):
                id2pred[oid] = op
    # 断点续跑
    if OUT.exists():
        existing = json.loads(OUT.read_text(encoding="utf-8"))
        if existing.get("meta", {}).get("ids") == all_ids:
            for oid, op in zip(existing.get("ids", []), existing.get("preds", []), strict=True):
                if isinstance(op, str) and op in ("consistent", "inconsistent"):
                    id2pred[oid] = op
    print(f"播种+续跑: 已有{len(id2pred)}条")
    todo = [x for x in data if x["id"] not in id2pred]
    print(f"已完成{len(id2pred)}, 待跑{len(todo)}")

    if todo:

        def work(x):
            try:
                out = llm_chat(PROMPT.format(premise=x["premise"], hypothesis=x["hypothesis"]),
                               system=SYSTEM, prefer="glm")
                v = parse(out)
                return x["id"], ("consistent" if v == "uncertain" else v)
            except Exception as e:  # noqa: BLE001
                return x["id"], f"ERR:{type(e).__name__}"

        t0 = time.time()
        with ThreadPoolExecutor(max_workers=4) as ex:
            for i, (pid, v) in enumerate(ex.map(work, todo)):
                id2pred[pid] = v
                if (i + 1) % 50 == 0:
                    _save(OUT, all_ids, id2pred)
                    print(f"  {len(id2pred)}/{len(data)} ({time.time() - t0:.0f}s)", flush=True)

    _save(OUT, all_ids, id2pred)

    # 汇总(错误按consistent保守计)
    preds = [id2pred[i] if not str(id2pred[i]).startswith("ERR") else "consistent" for i in all_ids]
    golds = [x["label"] for x in data]
    fams = [x["family"] for x in data]

    def bacc(ps, gs):
        npos, nneg = gs.count("inconsistent"), gs.count("consistent")
        if npos and nneg:
            tp = sum(1 for a, b in zip(ps, gs) if a == b == "inconsistent")
            tn = sum(1 for a, b in zip(ps, gs) if a == b == "consistent")
            return (tp / npos + tn / nneg) / 2
        return sum(1 for a, b in zip(ps, gs) if a == b) / len(gs)

    from collections import defaultdict
    by_fam = defaultdict(lambda: ([], []))
    for p, g, f in zip(preds, golds, fams):
        by_fam[f][0].append(p)
        by_fam[f][1].append(g)
    print("\n═══ CCP-LLM 全量896 ═══")
    for f in sorted(by_fam):
        ps, gs = by_fam[f]
        mixed = len(set(gs)) == 2
        v = bacc(ps, gs) if mixed else sum(1 for a, b in zip(ps, gs) if a == b) / len(gs)
        print(f"  {f}族: {'bAcc' if mixed else 'acc'}={v:.3f}")
    overall = bacc(preds, golds)
    print(f"  总体bAcc={overall:.3f}")

    OUT.write_text(json.dumps(
        {"meta": {"ids": all_ids, "method": "CCP-lite反事实一致性(ACL'25), 全量896"},
         "ids": all_ids, "preds": preds,
         "summary": {"overall_bAcc": round(overall, 3)}}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"保存 → {OUT}")


def _save(out_path: Path, ids: list[str], id2pred: dict) -> None:
    out_path.write_text(json.dumps({"meta": {"ids": ids}, "ids": ids,
                                    "preds": [id2pred.get(i, "PENDING") for i in ids]},
                                   ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
