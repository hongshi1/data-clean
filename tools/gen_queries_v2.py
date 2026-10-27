r"""假想查询多样化增强(A6-v2): 为已有假想查询的chunk追加"参数/数值型查询".

背景: gen_hypothetical_queries.py产出的查询偏"功能型/定位型"问句,
与真实检索分布存在偏置——真实SRS检索中大量查询携带具体数值
(容量"5000条"、周期"30秒"、"响应时间≤2s"、精度"99.9%").
本脚本对已生成假想查询的chunk, 每个追加1条参数/数值型查询,
数字必须原样取自片段(确定性约束: 生成后强校验查询含数字,
不含则丢弃), 使训练查询分布覆盖数值锚定检索模式.

谱系: 查询多样化是检索训练数据工程的标配(RocketQAv2的query
来自真实日志+人工模板双源; BGE训练对含数值型query) — LLM生成
+ 后置确定性过滤是可复现的域内替代方案.

LLM调用: algorithms/llm_client.llm_json(cache=True) — 磁盘缓存,
断点续跑零成本(硬规则: 禁止裸调用).

选择顺序(--limit N, 确定性): 已有假想查询的chunk → 片段含数字
(无数字无法构造数值型查询) → 沿用gen_hypothetical_queries的
文档round-robin×章节深度降序(与其选择谱系一致).

用法: python tools/gen_queries_v2.py [--limit 800] [--workers 6]
产出: data/gjb_438c/data_assets/doc_queries/doc_queries_v2.json
      格式 {chunk_id: ["参数型查询"]}
      元数据 → 同目录 doc_queries_v2.meta.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parents[1]
for _p in (str(BASE), str(Path(__file__).resolve().parent)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from algorithms.common.llm_client import llm_json  # noqa: E402
from gen_hypothetical_queries import (  # noqa: E402
    _clean_for_prompt,
    section_path,
    section_titles,
    selection_order,
)

CHUNKS = BASE / "data/gjb_438c/data_assets/chunks/srs_chunks.json"
HQ = BASE / "data/gjb_438c/data_assets/doc_queries/doc_queries.json"
OUT_DIR = BASE / "data/gjb_438c/data_assets/doc_queries"
OUT = OUT_DIR / "doc_queries_v2.json"
META = OUT_DIR / "doc_queries_v2.meta.json"

MAX_TEXT = 800         # prompt内chunk文本截断(与A6一致)
SNIPPET_MIN = 20       # prompt内数值片段最短长度

SYSTEM = "你是GJB 438C军用软件需求规格说明(SRS)检索专家, 只输出JSON."

_HAS_DIGIT = re.compile(r"\d")
_WS = re.compile(r"\s+")


def _numbers_in(text: str) -> list[str]:
    """片段中的数字锚(含单位上下文, 供prompt示例): 取前8个匹配."""
    return [m for m in re.findall(
        r"\d+(?:\.\d+)?\s*(?:%|s|ms|us|Gb|MB|KB|Gbps|Mbps|条|个|路|类|种|次|秒|分|时|天|年|字节|位|帧|户|万|亿)?",
        text) if m.strip()][:8]


def numeric_chunks(chunks: list[dict], hq: dict[str, list[str]]) -> list[dict]:
    """可增强chunk: 已有假想查询 且 清洗后文本含数字."""
    order = selection_order(chunks)
    return [c for c in order
            if c.get("chunk_id") in hq
            and _HAS_DIGIT.search(_clean_for_prompt(c.get("text") or ""))]


def build_prompt(chunk: dict, titles: dict[str, str]) -> str:
    text = _clean_for_prompt(chunk.get("text") or "")
    nums = "、".join(_numbers_in(text[:MAX_TEXT]))
    path = section_path(chunk.get("section", ""), titles)
    return (
        "为下面的SRS文档片段生成1个中文\"参数/数值型假想查询\""
        "(用户最可能用什么问题检索到它):\n"
        "- 查询必须围绕片段中的某个具体参数/数值/指标/容量/性能要求构造,\n"
        "  并把片段中的具体数字原样写进查询"
        "(如\"X的缓存容量是5000条吗\"\"同步周期30秒的任务在哪定义\")\n"
        f"- 片段中可引用的数字示例: {nums or '见片段内容'}\n"
        "- 查询必须原样保留片段或章节路径中的核心实体名"
        "(父章节名/叶子功能名/接口名/参数名)\n"
        "- 每条不超过30字; 不加解释。\n"
        '只输出JSON: {"query": "查询"}\n\n'
        f"文档: {chunk.get('doc', '')}\n"
        f"章节路径: {path}\n"
        f"片段类型: {chunk.get('type', 'text')}\n"
        f"片段内容:\n{text[:MAX_TEXT]}"
    )


def parse_query(out: Any) -> list[str]:
    """LLM JSON输出 → 干净的≤1条查询串(强校验: 必须含数字)."""
    if not isinstance(out, dict):
        return []
    q = out.get("query", out.get("queries"))
    if isinstance(q, list):
        q = q[0] if q else None
    if not isinstance(q, str):
        return []
    s = _WS.sub("", q.strip())
    if 2 <= len(s) <= 60 and _HAS_DIGIT.search(s):
        return [s]
    return []


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="参数/数值型假想查询增强")
    ap.add_argument("--limit", type=int, default=None,
                    help="目标chunk数(含已有条目, 断点续跑)")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    chunks = json.loads(CHUNKS.read_text(encoding="utf-8"))
    titles = section_titles(chunks)
    hq = json.loads(HQ.read_text(encoding="utf-8"))
    eligible = numeric_chunks(chunks, hq)
    print(f"chunks总={len(chunks)} 已有假想查询={len(hq)} "
          f"可数值增强={len(eligible)}(含数字)")

    results: dict[str, list[str]] = {}
    if OUT.exists():
        try:
            got = json.loads(OUT.read_text(encoding="utf-8"))
            if isinstance(got, dict):
                results = got
        except (OSError, json.JSONDecodeError):
            print("⚠ 既有输出损坏, 忽略并重新生成")
    done = set(results)
    todo = [c for c in eligible if c.get("chunk_id") not in done]
    if args.limit is not None:
        todo = todo[:max(args.limit - len(done), 0)]
    print(f"已有={len(done)} 新生成={len(todo)}"
          + (f" (目标{args.limit})" if args.limit is not None else ""))

    t0 = time.time()
    n_fail = 0
    n_drop = 0
    n_new = 0

    def _save() -> None:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1),
                       encoding="utf-8")

    def _gen(chunk: dict) -> tuple[str, list[str]]:
        out, _model = llm_json(build_prompt(chunk, titles), system=SYSTEM,
                               cache=True)
        return chunk.get("chunk_id", ""), parse_query(out)

    if todo:
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = [ex.submit(_gen, c) for c in todo]
            for fut in as_completed(futs):
                try:
                    cid, qs = fut.result()
                except Exception as e:
                    n_fail += 1
                    print(f"  ✗ LLM调用失败({n_fail}): {type(e).__name__} "
                          f"{str(e)[:80]}")
                    continue
                if cid and qs:
                    results[cid] = qs
                    n_new += 1
                elif cid:
                    n_drop += 1
                if n_new and n_new % 25 == 0:
                    _save()
                    print(f"  进度 {n_new}/{len(todo)} "
                          f"({time.time() - t0:.0f}s, 落盘{len(results)})")
    _save()

    docs_cov = len({cid.rsplit("_T", 1)[0] for cid in results})
    META.write_text(json.dumps({
        "n_chunks": len(results), "n_queries": sum(len(v) for v in results.values()),
        "n_chunks_total": len(chunks), "n_chunks_eligible": len(eligible),
        "n_new_this_run": n_new, "n_fail": n_fail, "n_drop_nodigit": n_drop,
        "limit": args.limit, "docs_covered": docs_cov,
        "selection": "已有假想查询(A6) ∩ 文本含数字; 文档round-robin; 章节深度降序",
        "query_constraint": "2-60字且必须含数字(LLM生成后确定性校验, 不含即弃)",
        "prompt": "chunk文本(≤800字)+数字锚示例+章节标题路径",
        "llm": "algorithms/llm_client.llm_json(cache=True, prefer=glm)",
        "elapsed_s": round(time.time() - t0, 1),
        "date": time.strftime("%Y-%m-%d"),
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n完成: {len(results)}个chunk / {sum(len(v) for v in results.values())}"
          f"条参数型查询 ({docs_cov}份文档, 失败{n_fail}, 无数字丢弃{n_drop}, "
          f"{time.time() - t0:.0f}s)")
    print(f"资产 → {OUT}")
    print(f"元数据 → {META}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
