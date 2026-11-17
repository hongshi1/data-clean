"""D3叙事化增广: 教师把构造性answer改写为91QA叙事风格+重新标注.

攻分布墙(M97诊断: d3train构造性单句answer vs test46叙事长
answer): 每条d3train实例两次教师调用(全缓存):
  1. rewrite: 构造answer→叙事风格(引导句+编号子断言+解释,
     保留全部事实与值, 91QA Alpaca风格)
  2. relabel: 对改写后的(Q, 叙事A, 原证据)跑D3标注
     (verdict+issues——标签以重标为准, soundness由教师判定)

产物: data/gjb_438c/distillation/d3_narrative_labels_v1.jsonl
(与d3_teacher_labels_v1.jsonl同格式, corpus=d3narrative,
instance_id=NARR-{orig_id})
用法: $env:PYTHONUTF8='1'; $env:PYTHONPATH='.'
      python tools/d3_narrative_augment.py [--limit N]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from tools.d3_teacher_labels import (  # noqa: E402
    label_one,
)
from tools.llm_teacher import llm_json_teacher  # noqa: E402

SOURCE = (BASE / "data/gjb_438c/distillation"
          / "d3_train_instances_v1.jsonl")
OUT = (BASE / "data/gjb_438c/distillation"
       / "d3_narrative_labels_v1.jsonl")

_REWRITE_SYSTEM = (
    "你是需求文档问答数据的风格改写器。把给定的简短answer改写为"
    "GJB需求问答系统的标准叙事风格，要求：\n"
    "1.保留全部事实断言和值（设备名/参数值/标识符/阶段/枚举成员），"
    "一个都不能改、不能丢、不能新增\n"
    "2.风格：开头一句总述（'XX功能包括以下操作'式），然后编号列表"
    "（'1. **子项名**：描述'式，每项1-2句，描述含效果/用途解释），"
    "结尾可加一句概括\n"
    "3.长度约为原answer的2-3倍\n"
    "4.只输出JSON。"
)
_REWRITE_SPEC = (
    '输出JSON：{"rewritten_answer": "改写后的叙事风格answer"}'
)
_REWRITE_RETRY = "\n\n只输出一个JSON对象，不要markdown代码块。"


def rewrite_answer(question: str, answer: str) -> str:
    prompt = (f"【问题】{question}\n\n【原answer】\n{answer}\n\n"
              f"{_REWRITE_SPEC}")
    for suffix in ("", _REWRITE_RETRY):
        try:
            payload, _model, _hit = llm_json_teacher(
                prompt + suffix, _REWRITE_SYSTEM,
                max_tokens=8000, temperature=0.1,
                extra_payload={"response_contract": "json_final_content_v2",
                               "reasoning_effort": "low"})
        except (RuntimeError, OSError):
            return ""
        text = str(payload.get("rewritten_answer", "")).strip()
        if text and text != answer:
            return text
    return ""


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    rows = [json.loads(line) for line in
            SOURCE.read_text(encoding="utf-8").splitlines() if line.strip()]
    done_ids: set[str] = set()
    if OUT.exists():
        for line in OUT.read_text(encoding="utf-8").splitlines():
            if line.strip():
                done_ids.add(json.loads(line)["instance_id"])
    n_new = 0
    n_rewritten = 0
    started = time.time()
    with open(OUT, "a", encoding="utf-8") as fout:
        for rec in rows:
            narr_id = f"NARR-{rec['instance_id']}"
            if narr_id in done_ids:
                continue
            if args.limit and n_new >= args.limit:
                break
            rewritten = rewrite_answer(str(rec["question"]),
                                       str(rec["answer"]))
            if not rewritten:
                print(f"  rewrite失败 {rec['instance_id']}", flush=True)
                continue
            n_rewritten += 1
            narr_rec = dict(rec)
            narr_rec["instance_id"] = narr_id
            narr_rec["answer"] = rewritten
            row = label_one(narr_rec, "d3narrative")
            if row is None:
                continue
            row["orig_label"] = str(rec.get("sound_label", ""))
            fout.write(json.dumps(row, ensure_ascii=False) + "\n")
            fout.flush()
            n_new += 1
            verified = sum(1 for i in row["issues"] if i["span_verified"])
            if n_new % 50 == 0:
                print(f"[{n_new}] {narr_id} {row['verdict']:16s} "
                      f"issues={len(row['issues'])}(校验{verified}) "
                      f"orig={rec.get('sound_label', '')} "
                      f"({time.time() - started:.0f}s)", flush=True)
    print(f"新增{n_new}条(改写{n_rewritten}) → {OUT}")


if __name__ == "__main__":
    main()
