r"""评测集扩充·用户模拟型查询生成(与训练用假想查询prompt策略独立).

设计动机(防泄漏与防循环):
  - 训练侧hq查询="chunk反向查询"(生成者视角);
    本批评测查询="用户检索意图模拟"(使用者视角)——prompt策略独立
  - 期望=宿主chunk(LLM读chunk生成问题, 期望锚独立于检索算法——
    区别于legacy 300条的字符串匹配期望[与lexical通道同源])
  - 生成后从训练集triples中移除宿主chunk对应的训练对(评测chunks
    不进训练——chunk级防泄漏, 比query级更强)

用法: python tools/gen_eval_queries.py [--limit 1200]
产出: data/gjb_438c/data_assets/eval_queries/user_sim_queries.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))

from algorithms.common.llm_client import llm_json  # noqa: E402

CHUNKS = BASE / "data/gjb_438c/data_assets/chunks/srs_chunks.json"
OUT = BASE / "data/gjb_438c/data_assets/eval_queries/user_sim_queries.json"

# 与训练侧不同的视角: 使用者提问, 非chunk反向描述
PROMPT = """你是军工信息系统的软件工程师, 正在检索需求文档.
以下是一段需求文档内容(章节{section}):
{content}

请站在使用者角度提出1个你在工作中真实会问的检索问题, 要求:
1. 问题只能通过上面这段内容回答(不含其他章节信息)
2. 包含这段内容中的具体实体名(功能名/接口名/参数名)
3. 句式自然多样(避免都用"...包含哪些"句式; 可用"哪里定义了X"/"X的约束是什么"/"X和Y是什么关系"等)
4. 不要直接抄原文句子
输出JSON: {{"question": "..."}}"""


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=1200)
    args = ap.parse_args()

    chunks = json.loads(CHUNKS.read_text(encoding="utf-8"))
    # 与训练hq选择策略不同: 全chunks均匀采样(训练侧是文档round-robin×深度降序)
    cands = [c for c in chunks
             if c.get("type") == "text" and len(c.get("text") or "") >= 60]
    step = max(len(cands) // args.limit, 1)
    picked = cands[::step][:args.limit]
    print(f"候选chunks: {len(cands)} → 采样{len(picked)}")

    results: dict[str, dict] = {}
    if OUT.exists():  # 断点续跑
        results = json.loads(OUT.read_text(encoding="utf-8"))
        print(f"已有{len(results)}条, 续跑")
    t0 = time.time()
    n_err = 0
    for i, c in enumerate(picked):
        cid = c["chunk_id"]
        if cid in results:
            continue
        prompt = PROMPT.format(section=c.get("section", ""),
                               content=(c.get("text") or "")[:700])
        try:
            j, _ = llm_json(prompt, cache=True, prefer="glm")
        except (RuntimeError, OSError) as e:
            n_err += 1
            if n_err <= 3:
                print(f"  [err] {cid}: {str(e)[:80]}")
            continue
        q = ""
        if isinstance(j, dict):
            q = str(j.get("question", "")).strip()
        if not q or len(q) < 6:
            n_err += 1
            continue
        results[cid] = {"query": q, "chunk_id": cid,
                        "section": c.get("section", ""),
                        "doc": c.get("doc", ""),
                        "chunk_type": c.get("type", "text")}
        if (i + 1) % 50 == 0:
            OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1),
                           encoding="utf-8")
            print(f"  {i + 1}/{len(picked)} ({time.time() - t0:.0f}s, "
                  f"err={n_err})", flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"完成: {len(results)}条 → {OUT} (err={n_err}, "
          f"{time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
