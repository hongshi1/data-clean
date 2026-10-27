r"""金标重裁(证据增强协议): 注入表格行+图节点实际内容, 本地Qwen2.5-1.5B-Instruct裁决.

协议变更(修复三缺陷): ①裁决可见图侧证据 ②条目是否真缺失可验证 ③理由须引用图内容
对照: 原CoT-1协议(无图证据)的标签位移 + 协议一致性
用法: python tools/md_gold_readjudicate.py [start] [end]   # 366条干净子集分段
产出: data/gjb_438c/human_gold/md_readjudicated.json (可续跑)
"""
from __future__ import annotations

import csv
import json
import sys
import time
from collections import Counter
from pathlib import Path

import torch

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.stdout.reconfigure(encoding="utf-8")

PD = BASE / "data/gjb_438c/pair_dataset"
QUEUE = json.loads((BASE / "data/gjb_438c/human_gold/multidoc_queue_579.json").read_text(encoding="utf-8"))
ORIG = json.loads((BASE / "data/gjb_438c/human_gold/md_cot_adjudication.json").read_text(encoding="utf-8"))
CLEAN = json.loads((BASE / "data/gjb_438c/human_gold/md_gold_clean_subset.json").read_text(encoding="utf-8"))
OUT = BASE / "data/gjb_438c/human_gold/md_readjudicated.json"

LLM_DIR = str(BASE / "models/nli/Qwen2.5-1.5B-Instruct")

PROMPT = """你是SRS需求文档审查专家。基于完整证据(表格内容+图的实际节点)判断差异性质。

[文档] {doc}
[表格相关内容]
{table_rows}
[图的实际节点文本]
{diag_nodes}
[差异声称] {evidence}
[待判条目] {item}

判定原则:
- real_bug: 条目确实在图的节点中无对应(核对上方节点列表!), 且该条目是核心功能/数据流必需
- benign_variation: ①条目实际在图中有对应或近似对应(核对!) ②图粒度粗/合并表示 ③辅助性内容(监控/日志/配置)

注意: 必须先核对"图的实际节点文本"再判断——差异声称可能因抽取错误而不成立。

只输出JSON: {{"label": "real_bug|benign_variation", "reason": "引用图节点内容的一句话理由"}}"""


def pair_dir(pair_key: str, scene: str) -> Path | None:
    d = PD / scene / pair_key
    return d if d.exists() else None


def load_evidence(q: dict) -> dict:
    d = pair_dir(q["pair"], q["scene"])
    if d is None:
        return {}
    out = {}
    va = d / "visio_anchor.json"
    if va.exists():
        try:
            v = json.loads(va.read_text(encoding="utf-8"))
            out["nodes"] = [str(n.get("text", "")) for n in v.get("nodes", []) if n.get("text")]
        except json.JSONDecodeError:
            out["nodes"] = []
    tc = d / "table.csv"
    if tc.exists():
        try:
            rows = list(csv.reader(open(tc, encoding="utf-8")))
            out["table_rows"] = "\n".join(",".join(r[:4]) for r in rows[:12] if any(r))
        except (OSError, csv.Error):
            out["table_rows"] = ""
    meta = d / "meta.json"
    if meta.exists():
        try:
            out["meta"] = json.loads(meta.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            out["meta"] = {}
    return out


def main() -> None:
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    end = int(sys.argv[2]) if len(sys.argv) > 2 else len(CLEAN)
    todo = CLEAN[start:end]
    print(f"重裁范围: [{start}:{end}] = {len(todo)}条")

    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(LLM_DIR, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(LLM_DIR, local_files_only=True,
                                                 torch_dtype=torch.bfloat16, device_map="auto")
    model.eval()

    res = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    queue_by_qid = {y["qid"]: y for y in QUEUE}
    t0 = time.time()
    for i, x in enumerate(todo):
        qid = x["qid"]
        if qid in res:
            continue
        q = queue_by_qid.get(qid)
        if q is None:
            continue
        ev = load_evidence(q)
        nodes = ev.get("nodes", [])
        rows = ev.get("table_rows", "")
        meta = ev.get("meta", {})
        item = str((q.get("table_side") or {}).get("text", ""))[:60]
        prompt = PROMPT.format(doc=meta.get("doc", q.get("doc", ""))[:30],
                               table_rows=rows[:800] or "(表格内容不可用)",
                               diag_nodes="; ".join(nodes[:25])[:600] or "(图节点不可用)",
                               evidence=q["evidence"][:100], item=item)
        msgs = [{"role": "user", "content": prompt}]
        text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        inputs = tok(text, return_tensors="pt", truncation=True, max_length=1200).to(model.device)
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=60, do_sample=False,
                                 pad_token_id=tok.eos_token_id)
        gen = tok.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        lab = "real_bug" if "real_bug" in gen else ("benign_variation" if "benign" in gen else "?")
        res[qid] = {"new_label": lab, "orig_label": x["label"],
                    "reason": gen[:120], "has_evidence": bool(nodes),
                    "dtype": x["dtype"], "doc": x["doc"]}
        if (i + 1) % 20 == 0:
            OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"  {i + 1}/{len(todo)} ({time.time() - t0:.0f}s)")
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")

    # 一致性统计
    valid = {k: v for k, v in res.items() if v["new_label"] in ("real_bug", "benign_variation")}
    agree = sum(1 for v in valid.values() if v["new_label"] == v["orig_label"])
    shifts = Counter((v["orig_label"], v["new_label"]) for v in valid.values())
    print(f"\n完成: {len(valid)}有效")
    print(f"协议一致率: {agree / len(valid):.2%}" if valid else "无有效")
    print(f"位移: {dict(shifts)}")
    print(f"新分布: {dict(Counter(v['new_label'] for v in valid.values()))}")
    n_ev = sum(1 for v in res.values() if v["has_evidence"])
    print(f"证据可用: {n_ev}/{len(res)}")


if __name__ == "__main__":
    main()
