#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""17项LLM校验引擎: GLM-5.3(智谱官网) + mermaid结构化证据包

把40项体系中标记llm的17项(TERM-02/04, LOGIC-01~04/06~11, GJB-01~04, MM-03)
从"规划态"变为可执行:
  1. 上下文构建: 章节正文 + 表格数据 + mermaid图结构(节点/分支/条件边/拓扑序)
  2. 提示词工程: 结构化证据包 + GJB领域角色 + JSON输出约束
  3. GLM-5.3推理(温度0.1), 结果缓存到 data/gjb_438c/llm_check_results/{doc}.json

用法:
    from algorithms.consistency_check.llm_checks import run_llm_checks
    r = run_llm_checks("02")           # 全部17项
    r = run_llm_checks("02", ["GJB-01"])  # 单项
    # → {item_id: {"found": bool, "n": int, "findings": [{desc, section, evidence, reason}]}}
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from algorithms.common.llm_client import llm_json
from algorithms.consistency_check.mermaid_graph import parse_mermaid, seq_from_edges

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(BASE, "data/gjb_438c/llm_check_results")

SYSTEM = ("你是GJB 438C《军用软件开发文档通用要求》需求规格说明(SRS)一致性审查专家。"
          "基于给定证据判断需求文档中是否存在指定类型的不一致。"
          "只输出JSON, 格式: {\"found\": true/false, \"findings\": "
          "[{\"desc\": \"问题描述\", \"section\": \"章节或位置\", "
          "\"evidence\": \"证据原文片段\", \"reason\": \"判断理由\"}]}。"
          "没有充分证据时 found=false, 不猜测。")

# ---------------------------------------------------------------------------
# 上下文构建
# ---------------------------------------------------------------------------


class LLMCheckContext:
    """文档级上下文: 正文/表格(全文)/mermaid结构"""

    def __init__(self, doc_num, cg):
        self.cg = cg
        self.doc_num = doc_num
        g = cg.docs.get(doc_num)
        if not g:
            raise ValueError(f"doc {doc_num} 不存在")
        self.doc = g["meta"]["doc"]
        self.graph = g
        self.sec_texts = cg.sec_texts.get(doc_num, {})
        # mermaid结构: IMG节点mermaid_key → 解析后的图
        self.mermaids = self._load_mermaids()
        # 表格: 从content_list直载全文行
        self.tables = self._load_tables()
        # 章节标题
        self.titles = {n["section"]: (n.get("payload", {}) or {}).get("title", "")
                       for n in g["nodes"] if n["type"] == "TXT"}

    def _load_tables(self):
        """从mineru content_list加载表格全文行(caption→rows)"""
        import glob
        import re as _re
        out = []
        for p in glob.glob(os.path.join(
                BASE, "data/gjb_438c/mineru_standard/*/office/*content_list.json")):
            if os.path.basename(p).replace("_content_list.json", "") != self.doc:
                continue
            cl = json.load(open(p, encoding="utf-8"))
            cur_sec = ""
            for it in cl:
                if not isinstance(it, dict):
                    continue
                if it.get("type") == "text":
                    m = _re.match(r"^(\d+(?:\.\d+)*)\s+", it.get("text", "").strip())
                    if m:
                        cur_sec = m.group(1)
                elif it.get("type") == "table":
                    caps = it.get("table_caption", [])
                    cap = caps[0] if caps else f"表@{cur_sec}"
                    body = it.get("table_body", "")
                    rows = []
                    for tr in _re.findall(r"<tr[^>]*>(.*?)</tr>", body, _re.S)[:12]:
                        cells = _re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, _re.S)[:8]
                        vals = [_re.sub(r"<[^>]+>", "", c).strip()[:20] for c in cells]
                        if any(vals):
                            rows.append(vals)
                    out.append({"caption": cap, "section": cur_sec, "rows": rows})
            break
        return out

    def _load_mermaids(self):
        out = []
        try:
            exp = json.load(open(os.path.join(
                BASE, "data/gjb_438c/anchor_v2/mermaid_export.json"), encoding="utf-8"))
        except FileNotFoundError:
            return out
        for n in self.graph["nodes"]:
            if n["type"] != "IMG":
                continue
            key = (n.get("payload", {}) or {}).get("mermaid_key")
            if key and key in exp:
                g = parse_mermaid(exp[key].get("mermaid", ""))
                g["caption"] = (n.get("payload", {}) or {}).get("caption", "")
                g["section"] = n.get("section", "")
                out.append(g)
        return out

    # ---- 证据片段提取 ----
    def texts_with(self, kws, limit=6, min_len=30, sec_prefix=None):
        """含关键词的章节正文片段(可限定章节前缀, 如"3."只搜需求章节)"""
        hits = []
        for sec, text in self.sec_texts.items():
            if sec_prefix and not sec.startswith(sec_prefix):
                continue
            if any(k in text for k in kws) and len(text) > min_len:
                idx = min((text.find(k) for k in kws if k in text), default=0)
                snippet = text[max(0, idx - 20): idx + 120]
                hits.append({"section": sec, "text": snippet})
                if len(hits) >= limit:
                    break
        return hits

    def mermaid_digest(self, limit=4):
        """mermaid结构摘要(给LLM的结构化证据)"""
        out = []
        for g in self.mermaids[:limit]:
            conds = [e["cond"] for e in g["cond_edges"] if e["cond"]][:6]
            out.append({
                "图": g["caption"][:20], "章节": g["section"],
                "节点": [label for label in g["labels"] if label][:10],
                "分支条件": conds,
                "决策节点": g["decision_labels"][:5],
                "主链顺序": [label for label in seq_from_edges(g) if label][:10],
            })
        return out

    def usecase_steps(self, limit=4):
        """用例表主事件流/异常流步骤(表格全文行)"""
        out = []
        for t in self.tables:
            cap = t["caption"]
            if "用例" not in cap and "Use" not in cap.lower():
                continue
            steps = []
            for r in t["rows"]:
                line = " ".join(str(c) for c in r)
                if any(k in line for k in ["主事件流", "步骤", "异常流", "执行"]):
                    steps.append(line[:70])
            if not steps:
                # 兜底: 前几行作为结构
                steps = [" | ".join(str(c) for c in r)[:70] for r in t["rows"][:4]]
            out.append({"表": cap[:20], "章节": t["section"], "步骤": steps[:8]})
            if len(out) >= limit:
                break
        return out


# ---------------------------------------------------------------------------
# 17项定义: 上下文构建器 + 提示词
# ---------------------------------------------------------------------------

def _ctx_generic(ctx):
    return ""


LLM_ITEMS = {
    # ---- 术语层 ----
    "TERM-02": {
        "name": "同名异义",
        "evidence": lambda ctx: json.dumps(
            [{"alias": a[:12], "sections": [o.get("section", "") for o in
              []][:0] or []}
             for a in []][:0] or ctx.texts_with(["指", "是指", "定义为"], limit=5),
            ensure_ascii=False),
        "prompt": ("以下是文档中若干术语定义片段。检测是否存在【同一名称在不同位置含义不同】"
                   "(同名异义)。重点看同一术语在两处定义的内涵是否冲突。\n证据:\n{EV}\n"
                   "判断是否存在同名异义。"),
    },
    "TERM-04": {
        "name": "状态告警术语统一",
        "evidence": lambda ctx: json.dumps(
            ctx.texts_with(["报警", "告警", "故障标志", "状态指示"], limit=6),
            ensure_ascii=False),
        "prompt": ("以下是文档中状态/告警相关表述片段。检测是否存在【同一状态或告警在不同位置"
                   "使用不同术语】(如一处叫\"通信异常告警\"另一处叫\"链路故障标志\")。\n证据:\n{EV}\n"
                   "判断术语是否统一。"),
    },
    # ---- 逻辑层 ----
    "LOGIC-01": {
        "name": "模式切换优先级",
        "evidence": lambda ctx: json.dumps({
            "mermaid分支": ctx.mermaid_digest(3),
            "正文": ctx.texts_with(["优先级", "优先", "抢占", "模式切换"], limit=4)},
            ensure_ascii=False),
        "prompt": ("以下是流程图结构(含分支/顺序)与正文优先级表述。检测【正文声称的模式优先级"
                   "与图示分支逻辑是否矛盾】(如图中允许低优先级抢占高优先级)。\n证据:\n{EV}\n"
                   "判断是否存在优先级矛盾。"),
    },
    "LOGIC-02": {
        "name": "异常处置策略一致性",
        "evidence": lambda ctx: json.dumps({
            "mermaid异常分支": [g["cond_labels"] for g in ctx.mermaids if g["cond_labels"]][:3],
            "正文": ctx.texts_with(["异常", "失败", "重试", "备用", "切换"], limit=5)},
            ensure_ascii=False),
        "prompt": ("以下是图中的异常分支条件与正文异常处置表述。检测【不同位置对同一异常的处置"
                   "策略是否矛盾】(如一处说切换备用, 另一处说重试)。\n证据:\n{EV}\n判断策略是否一致。"),
    },
    "LOGIC-03": {
        "name": "事件时序逻辑",
        "evidence": lambda ctx: json.dumps({
            "流程图主链顺序": [label for g in ctx.mermaids[:3] for label in seq_from_edges(g) if label][:12],
            "用例表步骤": ctx.usecase_steps(3)},
            ensure_ascii=False),
        "prompt": ("以下是流程图的主链顺序(拓扑序)与用例表主事件流步骤。检测【图的步骤顺序与"
                   "表格步骤顺序是否矛盾】(如表格步骤1→2, 图中2→1)。\n证据:\n{EV}\n判断时序是否一致。"),
    },
    "LOGIC-04": {
        "name": "数据流流向一致性",
        "evidence": lambda ctx: json.dumps({
            "mermaid边方向": [{"from": e["src_label"][:10], "to": e["dst_label"][:10]}
                          for g in ctx.mermaids[:2] for e in g["edges"][:10]],
            "正文": ctx.texts_with(["数据流", "流向", "输入", "输出", "回传", "单向"], limit=4)},
            ensure_ascii=False),
        "prompt": ("以下是图中的数据流向(边方向)与正文流向表述。检测【正文声称的流向与图示"
                   "是否矛盾】(如正文说单向输入, 图中有反向输出)。\n证据:\n{EV}\n判断流向是否一致。"),
    },
    "LOGIC-06": {
        "name": "互斥控制逻辑",
        "evidence": lambda ctx: json.dumps(
            ctx.texts_with(["互斥", "不能同时", "并行", "同时执行", "独占"], limit=5),
            ensure_ascii=False),
        "prompt": ("以下是文档互斥/并行相关表述。检测【一处声明互斥执行, 另一处声明同时执行】"
                   "的矛盾。\n证据:\n{EV}\n判断是否存在互斥矛盾。"),
    },
    "LOGIC-07": {
        "name": "任务切换原子性",
        "evidence": lambda ctx: json.dumps(
            ctx.texts_with(["原子", "不可中断", "可中断", "切换"], limit=4),
            ensure_ascii=False),
        "prompt": ("以下是任务切换相关表述。检测【一处说原子不可中断, 另一处说可中断】的矛盾。\n"
                   "证据:\n{EV}\n判断是否矛盾。"),
    },
    "LOGIC-08": {
        "name": "数据冗余仲裁逻辑",
        "evidence": lambda ctx: json.dumps(
            ctx.texts_with(["主用", "备用", "仲裁", "优先数据", "冗余"], limit=4),
            ensure_ascii=False),
        "prompt": ("以下是冗余/仲裁相关表述。检测【主备数据优先级在不同位置是否矛盾】。\n"
                   "证据:\n{EV}\n判断是否矛盾。"),
    },
    "LOGIC-09": {
        "name": "权限访问控制逻辑",
        "evidence": lambda ctx: json.dumps({
            "mermaid可达路径": ctx.mermaid_digest(3),
            "正文": ctx.texts_with(["权限", "管理员", "普通用户", "访问控制", "授权"], limit=4)},
            ensure_ascii=False),
        "prompt": ("以下是图结构(可达路径)与权限表述。检测【正文限制某角色不可达的操作, 图中"
                   "却存在该角色的可达路径】类矛盾。\n证据:\n{EV}\n判断是否矛盾。"),
    },
    "LOGIC-10": {
        "name": "故障恢复逻辑",
        "evidence": lambda ctx: json.dumps(
            ctx.texts_with(["自动恢复", "手动恢复", "重启", "故障恢复"], limit=4),
            ensure_ascii=False),
        "prompt": ("以下是故障恢复相关表述。检测【一处说自动恢复, 另一处说需手动恢复】的矛盾。\n"
                   "证据:\n{EV}\n判断是否矛盾。"),
    },
    "LOGIC-11": {
        "name": "追踪重搜逻辑",
        "evidence": lambda ctx: json.dumps(
            ctx.texts_with(["重新搜索", "全库", "增量", "重搜"], limit=4),
            ensure_ascii=False),
        "prompt": ("以下是重搜/检索范围表述。检测【一处说全库重搜, 另一处说只搜增量】的矛盾。\n"
                   "证据:\n{EV}\n判断是否矛盾。"),
    },
    # ---- GJB合规层 ----
    "GJB-01": {
        "name": "可测试性合规",
        "evidence": lambda ctx: json.dumps(
            ctx.texts_with(["稳定", "可靠", "高效", "快速", "良好", "适当",
                            "合理", "及时"], limit=6, sec_prefix="3."),
            ensure_ascii=False),
        "prompt": ("以下是文档需求章节(3.x)中含模糊表述的需求片段(如\"运行稳定\"\"高效\")。"
                   "GJB 438C要求需求可验证。检测【缺少量化指标无法测试的模糊需求】。\n"
                   "证据:\n{EV}\n判断是否存在不可测试的模糊需求。"),
    },
    "GJB-02": {
        "name": "故障容错需求完备性",
        "evidence": lambda ctx: json.dumps({
            "故障相关": ctx.texts_with(["故障", "异常", "容错"], limit=4),
            "检测机制": ctx.texts_with(["故障检测", "检测机制", "自检", "监测"], limit=3)},
            ensure_ascii=False),
        "prompt": ("以下是故障处理与检测机制相关内容。检测【文档涉及故障处理但缺少故障检测"
                   "机制描述】的完备性缺陷。\n证据:\n{EV}\n判断容错需求是否完备。"),
    },
    "GJB-03": {
        "name": "安全访问控制合规",
        "evidence": lambda ctx: json.dumps(
            ctx.texts_with(["安全", "权限", "访问控制", "身份", "鉴权", "认证"], limit=5),
            ensure_ascii=False),
        "prompt": ("以下是安全相关内容。检测【文档缺少访问权限控制/身份认证类安全条款】的"
                   "合规缺陷(涉密军用系统必须有)。\n证据:\n{EV}\n判断安全条款是否完备。"),
    },
    "GJB-04": {
        "name": "审计日志合规",
        "evidence": lambda ctx: json.dumps(
            ctx.texts_with(["日志", "审计", "记录操作", "操作留痕"], limit=4),
            ensure_ascii=False),
        "prompt": ("以下是日志/审计相关内容。检测【文档缺少操作日志记录/审计条款】的合规缺陷。\n"
                   "证据:\n{EV}\n判断审计条款是否完备。"),
    },
    # ---- 多模态层 ----
    "MM-03": {
        "name": "步骤时序方向一致性",
        "evidence": lambda ctx: json.dumps({
            "mermaid主链": [label for g in ctx.mermaids[:3] for label in seq_from_edges(g) if label][:12],
            "mermaid条件边": [e for g in ctx.mermaids[:3] for e in g["cond_labels"]][:8],
            "用例表步骤": ctx.usecase_steps(3)},
            ensure_ascii=False),
        "prompt": ("以下是流程图解析出的步骤顺序(含条件分支)与用例表步骤。逐对比较: "
                   "【图中A→B的顺序是否与表格中A在B前的顺序矛盾】; 条件分支方向是否有反转。\n"
                   "证据:\n{EV}\n判断方向是否一致。"),
    },
}


# ---------------------------------------------------------------------------
# 执行引擎
# ---------------------------------------------------------------------------

def run_llm_checks(doc_num, item_ids=None, use_cache=True, prefer="glm"):
    """执行LLM校验项 → {item_id: {found, n, findings}}"""
    from algorithms.context_association.context_graph import ContextGraph
    cg = ContextGraph()
    return run_llm_checks_ctx(cg, doc_num, item_ids, use_cache, prefer)


def run_llm_checks_ctx(cg, doc_num, item_ids=None, use_cache=True, prefer="glm"):
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, f"{doc_num}.json")
    cache = {}
    if use_cache and os.path.exists(cache_path):
        cache = json.load(open(cache_path, encoding="utf-8"))

    ids = item_ids or list(LLM_ITEMS.keys())
    ctx = LLMCheckContext(doc_num, cg)
    results = {}
    sys.stdout.reconfigure(encoding="utf-8")
    for iid in ids:
        if iid in cache and use_cache:
            results[iid] = cache[iid]
            print(f"  [{iid}] cache")
            continue
        spec = LLM_ITEMS[iid]
        try:
            ev = spec["evidence"](ctx)
            prompt = spec["prompt"].replace("{EV}", str(ev)[:3500])
            out, model = llm_json(prompt, system=SYSTEM, prefer=prefer)
            if "_parse_error" in out:
                results[iid] = {"found": False, "n": 0, "findings": [],
                                "error": out["_parse_error"][:100]}
            else:
                fs = out.get("findings", []) or []
                if out.get("found") and not fs:
                    fs = [{"desc": "LLM判定存在不一致(未给出明细)",
                           "section": "", "evidence": "", "reason": ""}]
                results[iid] = {
                    "found": bool(out.get("found")),
                    "n": len(fs),
                    "findings": [{"desc": f.get("desc", "")[:80],
                                  "section": f.get("section", "")[:20],
                                  "evidence": f.get("evidence", "")[:100],
                                  "reason": f.get("reason", "")[:100]}
                                 for f in fs[:5]],
                    "model": model}
            cache[iid] = results[iid]
            json.dump(cache, open(cache_path, "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)
            print(f"  [{iid}] {results[iid]['found']} "
                  f"({results[iid]['n']}条, {model})")
        except Exception as e:
            results[iid] = {"found": False, "n": 0, "findings": [],
                            "error": str(e)[:120]}
            print(f"  [{iid}] ERROR: {str(e)[:80]}")
    return results


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("doc")
    ap.add_argument("--items", help="逗号分隔的校验项ID")
    ap.add_argument("--no-cache", action="store_true")
    a = ap.parse_args()
    ids = a.items.split(",") if a.items else None
    r = run_llm_checks(a.doc, ids, use_cache=not a.no_cache)
    n_found = sum(1 for v in r.values() if v.get("found"))
    print(f"\n完成: {len(r)}项, {n_found}项发现")
    for k, v in r.items():
        if v.get("found"):
            print(f"  {k} {LLM_ITEMS[k]['name']}: {v['n']}条")
            for f in v["findings"][:2]:
                print(f"    - {f['desc'][:60]} @ {f['section']}")
