r"""SOTA级LLM基线: GLM-5 few-shot CoT推理检测(强于裸zero-shot的标准基线).

用法: python tools/llm_cot_baseline.py bench|clean130
产出: data/gjb_438c/public_nli/llm_baseline/{name}_cot.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))
sys.stdout.reconfigure(encoding="utf-8")

from algorithms.common.llm_client import llm_json  # noqa: E402
from run_benchmark_suite import prf, load_sample  # noqa: E402

OUT = BASE / "data/gjb_438c/public_nli/llm_baseline"

FEWSHOT_COT = """你是SRS需求一致性审查专家。先分析两段陈述的关键差异, 再判定一致性。

分析要点: ①参数数值/单位是否一致 ②执行顺序是否矛盾 ③术语是否指同一事物 ④组成/范围是否冲突 ⑤一方是否缺失关键内容

示例1:
陈述1: 系统响应时间应不大于2s。
陈述2: 系统响应时间应不大于5s。
分析: 同一参数"响应时间"数值2s vs 5s冲突。
判定: inconsistent

示例2:
陈述1: 表格规定用例包含步骤「用户确认操作」。
陈述2: 流程图中没有与该步骤对应的节点。
分析: 确认类中间步骤常被图省略, 属画法粒度差异, 非内容矛盾。
判定: consistent

示例3:
陈述1: 数据缓存周期为30s。
陈述2: 数据缓存周期为60s。
分析: 同一周期参数数值冲突。
判定: inconsistent

示例4:
陈述1: 表格规定异常流E1「连接失败时提示用户」。
陈述2: 流程图中没有该异常分支。
分析: 流程图惯例只画主流程, 异常流不上图是常见画法。
判定: consistent

请对以下陈述判定(只输出JSON): {{"analysis": "一句话分析", "label": "inconsistent|consistent"}}

陈述1: {p}
陈述2: {h}"""


def main() -> None:
    which = sys.argv[1] if len(sys.argv) > 1 else "bench"
    if which == "bench":
        data = load_sample("gjb_bench_test")
    elif which == "clean130":
        data = json.loads((BASE / "data/gjb_438c/human_gold/gold_v2_clean_137.json").read_text(encoding="utf-8"))
    else:
        raise SystemExit(f"未知目标: {which}")

    print(f"GLM-5 few-shot CoT @ {which}: {len(data)}条")
    preds = []
    for i, x in enumerate(data):
        prompt = FEWSHOT_COT.format(p=x["premise"], h=x["hypothesis"])
        try:
            parsed, _ = llm_json(prompt, cache=True)
            lab = str((parsed or {}).get("label", "?")).lower()
        except Exception as e:
            lab = f"error:{type(e).__name__}"
        preds.append(lab if lab in ("inconsistent", "consistent") else "consistent")
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(data)}")

    ys = [x["label"] for x in data]
    m = prf(ys, preds)
    print(f"GLM-5 CoT @ {which}: F1={m['F1']} P={m['P']} R={m['R']}")
    res = {"source": which, "method": "GLM-5 few-shot CoT", "n": len(data), **m}
    json.dump(res, open(OUT / f"{which}_cot.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"saved → {OUT / f'{which}_cot.json'}")


if __name__ == "__main__":
    main()
