r"""多文档金标裁决: scene_tier1的579条差异, CoT协议, 分批可续跑(缓存幂等).

用法: python tools/md_gold_adjudicate.py <batch_idx>   # 每批40条
      python tools/md_gold_adjudicate.py status        # 查看进度
产出: data/gjb_438c/human_gold/md_cot_adjudication.json
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.stdout.reconfigure(encoding="utf-8")

from algorithms.common.llm_client import llm_json  # noqa: E402

QUEUE = BASE / "data/gjb_438c/human_gold/multidoc_queue_579.json"
OUT = BASE / "data/gjb_438c/human_gold/md_cot_adjudication.json"
BATCH = 40

COT_PROMPT = """你是SRS需求文档审查专家。判断表格与图之间的差异是「真实矛盾」还是「合理差异」。

判定原则:
- 真实矛盾(real_bug): ①核心能力/功能/接口在图中完全缺失(该内容是系统必须提供的关键功能) ②图中存在表格没有的实质性功能/接口(不是纯视觉元素) ③接口的收发组件缺失导致数据流断裂 ④同一事物名称在两处指代不同的内容
- 合理差异(benign_variation): ①图粒度粗于表格是常态(能力图常只画顶层, 子功能合并为节点) ②图中容器/分组/页签类节点非功能项 ③图省略辅助性组件(日志、监视、配置类) ④同一功能的不同表述粒度(名称不完全一致但指同一事物)

示例1: 表格条目"流式数据归集"在能力图中无匹配, 图只画了数据获取大框 → benign(粒度合并)
示例2: 表格条目"数据加密传输"在图中无任何对应, 加密是核心安全功能 → real(核心功能缺失)
示例3: 接口图中多出"日志记录"组件, 表格无此接口 → benign(辅助组件)
示例4: 表格规定接口由服务端发给客户端, 图中组件方向相反 → real(数据流矛盾)

请判断, 只输出JSON: {{"label": "real_bug|benign_variation", "reason": "一句话理由"}}

差异描述: {evidence}
表格侧: {ts}
图侧: {ds}"""


def load_results() -> dict:
    if OUT.exists():
        return json.loads(OUT.read_text(encoding="utf-8"))
    return {}


def save_results(res: dict) -> None:
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


def main() -> None:
    arg = sys.argv[1] if len(sys.argv) > 1 else "status"
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    res = load_results()

    if arg == "status":
        done = [q for q in queue if q["qid"] in res]
        labs = Counter(res[q["qid"]].get("label", "?") for q in done)
        print(f"进度: {len(done)}/{len(queue)} ({len(done)/len(queue):.0%})")
        print(f"标签: {dict(labs)}")
        docs = Counter(q["doc"] for q in done)
        print(f"文档覆盖: {len([d for d in docs if d])}份")
        return

    batch_idx = int(arg)
    lo, hi = batch_idx * BATCH, min((batch_idx + 1) * BATCH, len(queue))
    todo = [q for q in queue[lo:hi] if q["qid"] not in res]
    print(f"批次{batch_idx}: 条目{lo}-{hi}, 待裁{len(todo)}(已完成{hi-lo-len(todo)})")
    if not todo:
        print("本批已全部完成")
        return

    t0 = time.time()
    n_ok = 0
    for i, q in enumerate(todo):
        ts = json.dumps(q.get("table_side") or {}, ensure_ascii=False)[:120]
        ds = json.dumps(q.get("diag_side") or {}, ensure_ascii=False)[:120]
        prompt = COT_PROMPT.format(evidence=q["evidence"][:110], ts=ts, ds=ds)
        try:
            parsed, _model = llm_json(prompt, cache=True)
            lab = str((parsed or {}).get("label", "?"))
            reason = str((parsed or {}).get("reason", ""))[:80]
        except Exception as e:
            lab = f"error:{type(e).__name__}"
            reason = ""
        if lab in ("real_bug", "benign_variation"):
            n_ok += 1
        res[q["qid"]] = {"label": lab, "reason": reason, "doc": q["doc"],
                         "scene": q["scene"], "dtype": q["dtype"],
                         "premise": q["premise"], "hypothesis": q["hypothesis"]}
        if (i + 1) % 10 == 0:
            save_results(res)
            el = time.time() - t0
            print(f"  {i + 1}/{len(todo)} ({el:.0f}s, 均{el/(i+1):.0f}s/条)")
    save_results(res)
    labs = Counter(v["label"] for v in res.values())
    print(f"批次完成: 成功{n_ok}/{len(todo)}")
    print(f"累计: {len(res)}/{len(queue)}, 标签{dict(labs)}")


if __name__ == "__main__":
    main()
