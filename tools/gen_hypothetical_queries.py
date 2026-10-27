r"""docT5query式文档扩展(A6): 为每个SRS chunk离线生成"假想查询".

谱系: Nogueira & Cho 2019 (docT5query / Passage Rewriting with Zero-shot
Inference) — 为passage生成"最可能检索到它"的假想查询并建独立索引,
在线把用户查询与假想查询匹配. 将"chunk正文↔短实体查询"的词汇失配
转化为"查询语言↔查询语言"的同空间匹配; 离线一次性成本, 在线零延迟.

攻两个召回瓶颈:
  1. 短实体查询信号不足(2-6字实体, bigram BM25噪声大)
  2. ID-Graph未登记的深层小节盲区(无ID mention锚的4级+小节)

LLM调用: algorithms/llm_client.llm_json(cache=True) — 磁盘缓存,
同prompt重跑零成本零漂移(断点续跑天然支持, 硬规则: 禁止裸调用).

选择顺序(--limit N, 确定性): 文本≥20字的chunk(排除目录/页眉/
"[图片]"占位) → 按文档round-robin(文档多样性) × 文档内章节深度
降序(深层小节盲区优先).

prompt带章节标题路径(heading chunk提取, 如"3.2.3 参数配置 >
3.2.3.1 时间配置功能"): 假想查询继承父章节实体词 — 查询实体常是
父章节标题(如"参数配置"), 仅含叶子词的hq无法词法桥接(评测校准依据).

用法: python tools/gen_hypothetical_queries.py [--limit 600] [--workers 6]
产出: data/gjb_438c/data_assets/doc_queries/doc_queries.json
      格式 {chunk_id: [假想查询1, 假想查询2]}
      元数据 → 同目录 doc_queries.meta.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.common.llm_client import llm_json  # noqa: E402

CHUNKS = BASE / "data/gjb_438c/data_assets/chunks/srs_chunks.json"
OUT_DIR = BASE / "data/gjb_438c/data_assets/doc_queries"
OUT = OUT_DIR / "doc_queries.json"
META = OUT_DIR / "doc_queries.meta.json"

TEXT_MIN = 20          # 过滤目录/页眉/纯图片占位等碎片chunk
MAX_TEXT = 800         # prompt内chunk文本截断(docT5query同用片段)

SYSTEM = "你是GJB 438C军用软件需求规格说明(SRS)检索专家, 只输出JSON."

_HTML_PAT = re.compile(r"<[^>]+>")
_WS_PAT = re.compile(r"\s+")
_HEADING_PAT = re.compile(r"^(\d+(?:\.\d+)*)[\s.、]*(\S.*)$")


def _depth(section: str) -> int:
    """章节深度: "3.3.5.1"→4 (深层小节口径)."""
    return len([p for p in (section or "").split(".") if p])


def _clean_for_prompt(text: str) -> str:
    """prompt用文本: 表格chunk的HTML标签剥离+空白压缩."""
    t = _HTML_PAT.sub(" ", text or "")
    return _WS_PAT.sub(" ", t).strip()


def section_titles(chunks: list[dict]) -> dict[str, str]:
    """章节号→标题: 来自heading chunk(文本以'章节号'开头且短)."""
    titles: dict[str, str] = {}
    for c in chunks:
        sec = c.get("section", "")
        if not sec:
            continue
        t = _clean_for_prompt(c.get("text") or "")
        if len(t) >= 80:
            continue
        m = _HEADING_PAT.match(t)
        if m and m.group(1) == sec:
            titles.setdefault(sec, m.group(2))
    return titles


def section_path(section: str, titles: dict[str, str]) -> str:
    """章节标题路径: "3.2.3 参数配置 > 3.2.3.1 时间配置功能"."""
    if not section:
        return "无"
    parts = [p for p in section.split(".") if p]
    if len(parts) < 2:
        return f"{section} {titles.get(section, '')}".strip()
    stops = [".".join(parts[:i]) for i in range(2, len(parts) + 1)]
    segs = [f"{s} {titles.get(s, '')}".strip() for s in stops]
    return " > ".join(segs)


def eligible_chunks(chunks: list[dict]) -> list[dict]:
    """可生成chunk: 文本≥20字(排除目录/页眉/纯图片占位)."""
    return [c for c in chunks
            if len(_clean_for_prompt(c.get("text") or "")) >= TEXT_MIN]


def selection_order(chunks: list[dict]) -> list[dict]:
    """生成顺序: 文档round-robin(多样性) × 章节深度降序(盲区优先)."""
    by_doc: dict[str, list[dict]] = defaultdict(list)
    for c in eligible_chunks(chunks):
        by_doc[c.get("doc", "")].append(c)
    for d in by_doc:
        by_doc[d].sort(key=lambda c: (-_depth(c.get("section", "")),
                                      c.get("chunk_id", "")))
    order: list[dict] = []
    docs = sorted(by_doc)
    for i in range(max((len(v) for v in by_doc.values()), default=0)):
        for d in docs:
            if i < len(by_doc[d]):
                order.append(by_doc[d][i])
    return order


def build_prompt(chunk: dict, titles: dict[str, str] | None = None) -> str:
    text = _clean_for_prompt(chunk.get("text") or "")[:MAX_TEXT]
    path = section_path(chunk.get("section", ""), titles or {})
    return (
        "为下面的SRS文档片段生成2个中文\"假想查询\""
        "(用户最可能用什么问题检索到它):\n"
        "- 查询1(功能型): 问它包含/提供什么, 如\"X包含哪些子功能\""
        "\"X的主要参数是什么\"\n"
        "- 查询2(定位型): 问它在文档哪里, 如\"X在哪个章节定义\""
        "\"X的定义位置在哪\"\n"
        "规则: 查询必须原样保留片段或章节路径中的核心实体名"
        "(父章节名/叶子功能名/接口名/参数名, 如\"参数配置中的时间配置\");"
        "每条不超过30字; 不加解释。\n"
        '只输出JSON: {"queries": ["查询1", "查询2"]}\n\n'
        f"文档: {chunk.get('doc', '')}\n"
        f"章节路径: {path}\n"
        f"片段类型: {chunk.get('type', 'text')}\n"
        f"片段内容:\n{text}"
    )


def parse_queries(out: Any) -> list[str]:
    """LLM JSON输出 → 干净的≤2条查询串(容错)."""
    if not isinstance(out, dict):
        return []
    qs = out.get("queries")
    if not isinstance(qs, list):
        return []
    clean: list[str] = []
    for q in qs:
        s = str(q).strip()
        if 2 <= len(s) <= 60 and s not in clean:
            clean.append(s)
    return clean[:2]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="docT5query式假想查询生成")
    ap.add_argument("--limit", type=int, default=None,
                    help="目标chunk数(含已有条目, 断点续跑)")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--regen", action="store_true",
                    help="忽略既有输出重新生成(prompt变更后使用)")
    args = ap.parse_args()

    chunks = json.loads(CHUNKS.read_text(encoding="utf-8"))
    titles = section_titles(chunks)
    order = selection_order(chunks)
    print(f"chunks总={len(chunks)} 可生成={len(order)}"
          f"(文本≥{TEXT_MIN}字; 深层小节优先+文档round-robin; "
          f"章节标题{len(titles)}个)")

    results: dict[str, list[str]] = {}
    if OUT.exists() and not args.regen:
        try:
            got = json.loads(OUT.read_text(encoding="utf-8"))
            if isinstance(got, dict):
                results = got
        except (OSError, json.JSONDecodeError):
            print("⚠ 既有输出损坏, 忽略并重新生成")
    done = set(results)
    todo = [c for c in order if c.get("chunk_id") not in done]
    if args.limit is not None:
        todo = todo[:max(args.limit - len(done), 0)]
    print(f"已有={len(done)} 新生成={len(todo)}"
          + (f" (目标{args.limit})" if args.limit is not None else ""))

    t0 = time.time()
    n_fail = 0
    n_new = 0

    def _save() -> None:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1),
                       encoding="utf-8")

    def _gen(chunk: dict) -> tuple[str, list[str]]:
        out, _model = llm_json(build_prompt(chunk, titles), system=SYSTEM,
                               cache=True)
        return chunk.get("chunk_id", ""), parse_queries(out)

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
                if n_new and n_new % 25 == 0:
                    _save()
                    print(f"  进度 {n_new}/{len(todo)} "
                          f"({time.time() - t0:.0f}s, 落盘{len(results)})")
    _save()

    n_q = sum(len(v) for v in results.values())
    docs_cov = len({cid.rsplit("_T", 1)[0] for cid in results})
    META.write_text(json.dumps({
        "n_chunks": len(results), "n_queries": n_q,
        "n_chunks_total": len(chunks), "n_chunks_eligible": len(order),
        "n_new_this_run": n_new, "n_fail": n_fail, "limit": args.limit,
        "docs_covered": docs_cov,
        "selection": f"文本≥{TEXT_MIN}字(HTML剥离后); 文档round-robin; "
                     "章节深度降序",
        "prompt": "chunk文本(≤800字) + 章节标题路径(父章节实体词桥接)",
        "prompt_text_max": MAX_TEXT,
        "llm": "algorithms/llm_client.llm_json(cache=True, prefer=glm)",
        "elapsed_s": round(time.time() - t0, 1),
        "date": time.strftime("%Y-%m-%d"),
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n完成: {len(results)}个chunk / {n_q}条假想查询 "
          f"({docs_cov}份文档, 失败{n_fail}, {time.time() - t0:.0f}s)")
    print(f"资产 → {OUT}")
    print(f"元数据 → {META}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
