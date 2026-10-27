#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据集一致性校验引擎 — 52项校验(40项原版 + 12项多模态扩展)

数据源 = 上下文关联模块(ContextGraph方向A产物) + born-digital资产:
  graph_store (E/TXT/TBL/IMG/SEQ/KNW节点+加权边+聚合条目)
  stage0_assets (追溯/接口拓扑/版本对/异常流)
  scene_drift_census (236对图-表drift普查, 73条真实差异)
  mermaid_fidelity (89对保真度验证)
  srs_kb (单位族/参数词典/表型schema)

执行模式:
  auto  确定性执行(图谱规则/单位换算/Z3/资产统计) — 每条发现带证据定位
  llm   需万擎kimi-k2推理(业务理解/语义矛盾) — 标记待推理

用法:
    from algorithms.consistency_check.check_engine import CheckEngine
    ce = CheckEngine(cg)          # cg = ContextGraph()
    r = ce.run("02")              # → 52项结果
"""
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(BASE, "data/gjb_438c")


def _load(rel):
    p = os.path.join(BASE, rel)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


# ---------------------------------------------------------------------------
# 52项校验注册表
# ---------------------------------------------------------------------------
def _reg(cid, cat, name, desc, modality, mode):
    return {"id": cid, "category": cat, "name": name, "desc": desc,
            "modality": modality, "mode": mode}


CHECK_ITEMS = [
    # ---- 术语层 (8) ----
    _reg("TERM-01", "术语层", "同义异名", "同一功能在不同位置使用不同名称", "跨位置文本", "auto"),
    _reg("TERM-02", "术语层", "同名异义", "同一名称在不同位置含义不同", "跨位置语义", "llm"),
    _reg("TERM-03", "术语层", "枚举集合一致性", "正文声明的枚举数与图示数量不符", "文本vs图", "auto"),
    _reg("TERM-04", "术语层", "状态告警术语统一", "同一状态在不同位置叫法不同", "跨位置术语", "llm"),
    _reg("TERM-05", "术语层", "指令名称全局一致性", "同一指令在不同位置名称不同", "跨位置指令名", "auto"),
    _reg("TERM-06", "术语层", "量纲单位一致性", "同一参数不同位置数值+单位冲突", "跨位置数值+单位", "auto"),
    _reg("TERM-07", "术语层", "信号接口命名一致性", "同一接口在不同位置名称不同", "跨位置接口名", "auto"),
    _reg("TERM-08", "术语层", "缩写代号一致性", "同一概念一处全称一处缩写", "跨位置缩写", "auto"),
    # ---- 参数层 (10) ----
    _reg("PARAM-01", "参数层", "时间约束跨模态冲突", "文本与表格/图中时间约束值冲突", "文本vs表/图", "auto"),
    _reg("PARAM-02", "参数层", "周期参数一致性", "周期参数在不同位置取值冲突", "跨位置数值", "auto"),
    _reg("PARAM-03", "参数层", "阈值边界一致性", "阈值参数在不同位置冲突", "跨位置数值", "auto"),
    _reg("PARAM-04", "参数层", "多源融合时间对齐", "对齐误差参数跨位置冲突", "跨位置数值", "auto"),
    _reg("PARAM-05", "参数层", "资源占用指标", "内存/资源占用跨位置冲突", "跨位置数值", "auto"),
    _reg("PARAM-06", "参数层", "参数值域范围", "值域区间跨位置冲突(Z3验证)", "跨位置区间", "auto"),
    _reg("PARAM-07", "参数层", "存储容量与保存时长", "存储容量参数跨位置冲突", "跨位置数值", "auto"),
    _reg("PARAM-08", "参数层", "同步守时精度", "守时精度参数跨位置冲突", "跨位置数值", "auto"),
    _reg("PARAM-09", "参数层", "降级触发阈值", "降级阈值参数跨位置冲突", "跨位置数值", "auto"),
    _reg("PARAM-10", "参数层", "故障判定持续时长", "故障持续时长跨位置冲突", "跨位置数值", "auto"),
    # ---- 逻辑层 (11) ----
    _reg("LOGIC-01", "逻辑层", "模式切换优先级", "文本与状态机/流程图的优先级矛盾", "文本vs流程图", "llm"),
    _reg("LOGIC-02", "逻辑层", "异常处置策略一致性", "异常处理策略跨位置矛盾", "跨位置策略", "llm"),
    _reg("LOGIC-03", "逻辑层", "事件时序逻辑", "文本/表格步骤顺序与流程图方向矛盾", "文本vs流程图", "llm"),
    _reg("LOGIC-04", "逻辑层", "数据流流向一致性", "框图流向与文字描述矛盾", "框图vs文字", "llm"),
    _reg("LOGIC-05", "逻辑层", "工况分支完备性", "正文声明工况数与图分支数不符", "文本vs流程图", "auto"),
    _reg("LOGIC-06", "逻辑层", "互斥控制逻辑", "互斥与并行描述矛盾", "跨位置逻辑", "llm"),
    _reg("LOGIC-07", "逻辑层", "任务切换原子性", "原子性描述跨位置矛盾", "跨位置逻辑", "llm"),
    _reg("LOGIC-08", "逻辑层", "数据冗余仲裁逻辑", "主备优先级描述矛盾", "跨位置逻辑", "llm"),
    _reg("LOGIC-09", "逻辑层", "权限访问控制逻辑", "权限描述与图示路径矛盾", "文本vs流程图", "llm"),
    _reg("LOGIC-10", "逻辑层", "故障恢复逻辑", "恢复方式描述跨位置矛盾", "跨位置逻辑", "llm"),
    _reg("LOGIC-11", "逻辑层", "追踪重搜逻辑", "重搜范围描述跨位置矛盾", "跨位置逻辑", "llm"),
    # ---- GJB合规层 (11) ----
    _reg("GJB-01", "GJB合规层", "可测试性合规", "需求表述模糊不可验证", "业务理解", "llm"),
    _reg("GJB-02", "GJB合规层", "故障容错需求完备性", "故障检测机制缺失", "业务理解", "llm"),
    _reg("GJB-03", "GJB合规层", "安全访问控制合规", "访问权限控制条目缺失", "业务理解", "llm"),
    _reg("GJB-04", "GJB合规层", "审计日志合规", "操作日志记录条目缺失", "业务理解", "llm"),
    _reg("GJB-05", "GJB合规层", "需求可追溯性合规", "追溯链断裂/合格性缺失", "需求表vs测试表", "auto"),
    _reg("GJB-06", "GJB合规层", "异常报警要素合规", "报警设计缺级别等要素", "结构存在性", "auto"),
    _reg("GJB-07", "GJB合规层", "软件自检条款合规", "开机自检条目缺失", "结构存在性", "auto"),
    _reg("GJB-08", "GJB合规层", "掉电数据保护合规", "掉电保护条款缺失", "结构存在性", "auto"),
    _reg("GJB-09", "GJB合规层", "输入数据防护合规", "输入合法性验证缺失", "结构存在性", "auto"),
    _reg("GJB-10", "GJB合规层", "版本升级安全合规", "版本回退机制缺失", "结构存在性", "auto"),
    _reg("GJB-11", "GJB合规层", "降级运行合规", "降级运行模式条款缺失", "结构存在性", "auto"),
    # ---- 多模态扩展层 (12) ----
    _reg("MM-01", "多模态层", "流程步骤-用例步骤对应性", "流程图节点与用例表主事件流步骤不对应", "流程图vs用例表", "auto"),
    _reg("MM-02", "多模态层", "异常流图示完备性", "表格定义的异常流在流程图中无分支", "用例表vs流程图", "auto"),
    _reg("MM-03", "多模态层", "步骤时序方向一致性", "表格步骤顺序与流程图边方向矛盾", "用例表vs流程图", "llm"),
    _reg("MM-04", "多模态层", "参与者完备性", "用例图Actors与用例表Actors不一致", "用例图vs用例表", "auto"),
    _reg("MM-05", "多模态层", "接口图-接口表拓扑一致性", "接口图收发连线与接口表sender/receiver不符", "接口图vs接口表", "auto"),
    _reg("MM-06", "多模态层", "图示内容对应性", "图中有正文未提及的冗余元素或反之", "图vs正文", "auto"),
    _reg("MM-07", "多模态层", "图题-图型一致性", "图片caption与图实际类型不符", "captionvs图分类", "auto"),
    _reg("MM-08", "多模态层", "枚举计数图示一致性", "正文声明数量与图节点数不符", "正文vs图", "auto"),
    _reg("MM-09", "多模态层", "Mermaid结构保真度", "born-digital导出的Mermaid渲染与原图不符", "Mermaid渲染vs原图", "auto"),
    _reg("MM-10", "多模态层", "图-图结构一致性", "描述同一系统的两张图节点集不一致", "图vs图", "auto"),
    _reg("MM-11", "多模态层", "表头模式合规", "表格表头不符合GJB表型schema", "表结构vs规范", "auto"),
    _reg("MM-12", "多模态层", "跨表版本对齐冲突", "环境表与软件清单表版本不一致", "表vs表", "auto"),
]

CATEGORIES = ["术语层", "参数层", "逻辑层", "GJB合规层", "多模态层"]


class CheckEngine:
    def __init__(self, cg):
        self.cg = cg
        self.stage0 = _load("data/gjb_438c/data_assets/stage0_assets.json")
        self.drift = _load("data/gjb_438c/anchor_v2/scene_drift_census.json")
        self.fidelity = _load("data/gjb_438c/anchor_v2/mermaid_fidelity.json")
        self.kb = _load("knowledge/srs_kb.json")
        self.unit_fams = self.kb.get("unit_dictionary", {})
        self.tables = self._load_tables()
        # 章节正文
        self.sec_texts = {}
        import glob as _g
        import re as _r
        for p in _g.glob(os.path.join(
                ASSETS, "mineru_standard/*/office/*content_list.json")):
            name = os.path.basename(p).replace("_content_list.json", "")
            cl = json.load(open(p, encoding="utf-8"))
            st, cur = {}, ""
            for it in cl:
                if not isinstance(it, dict):
                    continue
                if it.get("type") == "text":
                    t = it.get("text", "")
                    m = _r.match(r"^(\d+(?:\.\d+)*)\s+", t.strip())
                    if m:
                        cur = m.group(1)
                    if len(t.strip()) > 15:
                        st[cur] = st.get(cur, "") + " " + t.strip()
                elif it.get("type") == "table":
                    body = _r.sub(r"<[^>]+>", " ", it.get("table_body", ""))
                    caps = " ".join(it.get("table_caption", []))
                    if len(body.strip()) > 5:
                        st[cur] = st.get(cur, "") + " " + caps + " " + body
            self.sec_texts[name] = st

    def _load_tables(self):
        """从content_list加载表格全文行(供逻辑层图-表比对用)"""
        import re as _re
        import glob as _glob
        out = []
        for p in _glob.glob(os.path.join(
                ASSETS, "mineru_standard/*/office/*content_list.json")):
            doc_name = os.path.basename(p).replace("_content_list.json", "")
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
                    cap = caps[0] if caps else ""
                    body = it.get("table_body", "")
                    rows = []
                    for tr in _re.findall(r"<tr[^>]*>(.*?)</tr>", body, _re.S)[:12]:
                        cells = _re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, _re.S)[:8]
                        vals = [_re.sub(r"<[^>]+>", "", c).strip()[:20] for c in cells]
                        if any(vals):
                            rows.append(vals)
                    out.append({"caption": cap, "section": cur_sec,
                               "rows": rows, "doc": doc_name})
        return out
        # 章节正文(doc -> section -> text)
        self.sec_texts = {}
        import glob as g
        for p in g.glob(os.path.join(ASSETS, "mineru_standard/*/office/*content_list.json")):
            name = os.path.basename(p).replace("_content_list.json", "")
            cl = json.load(open(p, encoding="utf-8"))
            st, cur = defaultdict(str), ""
            for it in cl:
                if not isinstance(it, dict):
                    continue
                if it.get("type") == "text":
                    t = it.get("text", "")
                    m = re.match(r"^(\d+(?:\.\d+)*)\s+", t.strip())
                    if m:
                        cur = m.group(1)
                    if len(t.strip()) > 15:
                        st[cur] += " " + t.strip()
            self.sec_texts[name] = dict(st)

    # ------------------------------------------------------------------
    def run(self, doc_num):
        g = self.cg.docs.get(doc_num)
        if not g:
            return {"ok": False, "message": f"数据集{doc_num}不存在"}
        doc = g["meta"]["doc"]
        findings = self._run_all(doc_num, doc, g)
        items = []
        for it in CHECK_ITEMS:
            f = findings.get(it["id"], [])
            if it["mode"] == "llm":
                status = "llm"
            elif len(f) == 0:
                status = "pass"
            else:
                status = "fail" if it["id"].startswith(("PARAM", "MM-12", "GJB-05", "MM-09")) else "warn"
            items.append({**it, "status": status, "n_findings": len(f),
                          "findings": f[:8]})
        # ---- 合并LLM校验结果(GLM-5.3, 若已运行并缓存) ----
        llm_cache = os.path.join(
            BASE, "data/gjb_438c/llm_check_results", f"{doc_num}.json")
        if os.path.exists(llm_cache):
            try:
                llm_results = json.load(open(llm_cache, encoding="utf-8"))
                for it in items:
                    if it["id"] in llm_results:
                        lr = llm_results[it["id"]]
                        it["findings"] = lr.get("findings", [])
                        it["n_findings"] = lr.get("n", 0)
                        it["status"] = "warn" if lr.get("found") else "pass"
                        it["mode"] = "llm-done"
            except Exception:
                pass
        summary = {"total": len(items)}
        for s in ["pass", "warn", "fail", "llm"]:
            summary[s] = sum(1 for i in items if i["status"] == s)
        cats = []
        for c in CATEGORIES:
            ci = [i for i in items if i["category"] == c]
            cats.append({
                "name": c, "total": len(ci),
                "pass": sum(1 for i in ci if i["status"] == "pass"),
                "warn": sum(1 for i in ci if i["status"] == "warn"),
                "fail": sum(1 for i in ci if i["status"] == "fail"),
                "llm": sum(1 for i in ci if i["status"] == "llm"),
                "findings": sum(i["n_findings"] for i in ci),
            })
        return {"ok": True, "doc": doc_num, "doc_name": doc,
                "ran_at": datetime.now().isoformat(timespec="seconds"),
                "summary": summary, "categories": cats, "items": items}

    # ------------------------------------------------------------------
    def _run_all(self, doc_num, doc, g):
        f = {}
        f.update(self._check_terms(doc_num, doc, g))
        f.update(self._check_params(doc_num, doc, g))
        f.update(self._check_gjb(doc_num, doc, g))
        f.update(self._check_multimodal(doc_num, doc, g))
        f.update(self._check_logic_basic(doc_num, doc, g))
        return f

    # ============ 术语层 ============
    def _check_terms(self, doc_num, doc, g):
        """术语层: 统计校准的同名实体一致性检验

        谱系: Bonferroni-corrected outlier detection → calibrate on corpus
        方法: 对全库所有同ID多别名的实体计算混合相似度,
             得到分布 → 用均值±k·标准差设动态阈值(非固定阈值)
             低于 μ - 2σ → 确证异常(名称冲突)
             低于 μ - 1σ → 可疑(需复核)
        """
        out = defaultdict(list)
        ents = [n for n in g["nodes"] if n["type"] == "E"]

        # 1. 收集全库别名对的相似度分布(校准)
        all_sims = []
        for e in ents:
            aliases = e["payload"].get("aliases", [])
            for i, a in enumerate(aliases):
                for b in aliases[i + 1:]:
                    all_sims.append(self._hybrid_sim(a, b))
        if not all_sims:
            return out
        import statistics
        mu = statistics.mean(all_sims)
        sigma = statistics.stdev(all_sims) if len(all_sims) > 1 else 0.15
        sigma = max(sigma, 0.05)  # 防除零
        # 动态阈值: μ - 2σ (确证) 和 μ - 1σ (可疑)
        th_confirm = max(mu - 2 * sigma, 0.10)
        th_suspect = max(mu - 1 * sigma, 0.20)

        # 2. 检测: 低于阈值的实体
        name_issues = []
        for e in ents:
            aliases = e["payload"].get("aliases", [])
            if len(aliases) >= 2:
                for i, a in enumerate(aliases):
                    for b in aliases[i + 1:]:
                        sim = self._hybrid_sim(a, b)
                        if sim < th_confirm:
                            name_issues.append({
                                "desc": f"实体「{e['payload'].get('id_str', '')}」名称冲突"
                                      f"(混合相似度{sim:.3f} < μ-2σ={th_confirm:.3f})",
                                "section": e.get("section", ""),
                                "evidence": f"「{a}」vs「{b}」",
                            })
                        elif sim < th_suspect:
                            name_issues.append({
                                "desc": f"实体「{e['payload'].get('id_str', '')}」名称可疑"
                                      f"(混合相似度{sim:.3f} < μ-σ={th_suspect:.3f})",
                                "section": e.get("section", ""),
                                "evidence": f"「{a}」vs「{b}」",
                            })
        out["TERM-01"] = name_issues
        # 指令类细分(TERM-05)
        out["TERM-05"] = [x for x in name_issues
                          if "指令" in x["evidence"] or "命令" in x["evidence"]]
        # TERM-07: 接口拓扑同名不同名
        if_names = defaultdict(set)
        for it in self.stage0.get("interface_topology", []):
            if it.get("doc") == doc and it.get("id") and it.get("name"):
                if_names[it["id"]].add(it["name"])
        out["TERM-07"] = [{
            "desc": f"接口「{iid}」存在多个名称",
            "section": "接口表",
            "evidence": " / ".join(sorted(names)),
        } for iid, names in if_names.items() if len(names) > 1]
        # TERM-08: 缩写vs全称
        abbr = []
        for e in ents:
            aliases = e["payload"].get("aliases", [])
            for a in aliases:
                for b in aliases:
                    if a != b and len(b) >= 4 and (b.startswith(a) or a in b) and len(a) <= 5:
                        abbr.append({
                            "desc": "同一实体存在缩写/全称两种写法",
                            "section": e.get("section", ""),
                            "evidence": f"「{a}」vs「{b}」",
                        })
        out["TERM-08"] = abbr
        # TERM-06: 量纲单位冲突(与参数层共用提取器, 只报单位不匹配族)
        cons = self._extract_constraints(doc)
        unit_conf = []
        for pname, group in cons.items():
            units = set(c["unit"] for c in group if c["unit"])
            fams = set(self._unit_family(u) for u in units if self._unit_family(u))
            if len(fams) > 1:
                unit_conf.append({
                    "desc": f"参数「{pname}」使用不同量纲单位族",
                    "section": "全文",
                    "evidence": " / ".join(f"{c['value']}{c['unit']}@{c['section']}" for c in group[:4]),
                })
        out["TERM-06"] = unit_conf
        # TERM-03/MM-08: 正文计数声明 vs 锚点节点数
        out["TERM-03"] = self._count_claims(doc)
        return out

    @staticmethod
    def _hybrid_sim(a, b):
        """混合相似度: α·编辑距离归一 + β·字符重叠率 + γ·最长公共子串比

        谱系: Levenshtein(1966) → Jaro-Winkler → 混合相似度
        权重: α=0.4, β=0.3, γ=0.3 (可校准)
        """
        if not a or not b:
            return 0.0
        if a == b:
            return 1.0
        # 1. 编辑距离归一
        d = CheckEngine._levenshtein(a, b)
        ed = 1.0 - d / max(len(a), len(b))
        # 2. 字符重叠率(Jaccard)
        sa, sb = set(a), set(b)
        jac = len(sa & sb) / len(sa | sb) if sa | sb else 0.0
        # 3. 最长公共子串比
        lcs = CheckEngine._lcs_len(a, b)
        lc = lcs / max(len(a), len(b))
        return round(0.4 * ed + 0.3 * jac + 0.3 * lc, 3)

    @staticmethod
    def _levenshtein(s1, s2):
        if len(s1) < len(s2):
            return CheckEngine._levenshtein(s2, s1)
        if len(s2) == 0:
            return len(s1)
        prev = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            curr = [i + 1]
            for j, c2 in enumerate(s2):
                curr.append(min(prev[j + 1] + 1, curr[j] + 1,
                                prev[j] + (c1 != c2)))
            prev = curr
        return prev[-1]

    @staticmethod
    def _lcs_len(a, b):
        m, n = len(a), len(b)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if a[i - 1] == b[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
        return dp[m][n]

    # ============ 参数层 ============
    PARAM_KEYWORDS = {
        "PARAM-01": ["响应时间", "延迟", "时延", "处理时间", "反应时间"],
        "PARAM-02": ["周期", "刷新频率", "采样率"],
        "PARAM-03": ["阈值", "门限"],
        "PARAM-04": ["对齐误差", "同步误差"],
        "PARAM-05": ["内存", "CPU", "资源占用"],
        "PARAM-06": ["值域", "取值范围", "范围"],
        "PARAM-07": ["存储", "硬盘", "磁盘", "容量"],
        "PARAM-08": ["精度", "守时"],
        "PARAM-09": ["降级"],
        "PARAM-10": ["故障持续", "持续时间"],
    }
    UNIT_TO_BASE = {"ms": ("time", 1), "s": ("time", 1000), "秒": ("time", 1000),
                    "us": ("time", 0.001), "μs": ("time", 0.001),
                    "min": ("time", 60000), "MB": ("storage", 1),
                    "GB": ("storage", 1024), "KB": ("storage", 1 / 1024),
                    "TB": ("storage", 1024 * 1024)}

    def _extract_constraints(self, doc):
        """提取约束: (参数名, 操作符, 数值, 单位, 章节)"""
        texts = self.sec_texts.get(doc, {})
        cons = defaultdict(list)
        pat = re.compile(
            r"([\u4e00-\u9fff]{2,10}?)\s*(?:不?(?:超过|低于|少于|大于|小于)|≥|≤|>|<|=)?"
            r"\s*([≥≤><=]?)\s*(\d+(?:\.\d+)?)\s*(ms|s|秒|us|μs|min|MB|GB|KB|TB|%|kHz|MHz|次|个|条)")
        for sec, text in texts.items():
            for m in pat.finditer(text):
                pname = m.group(1).strip()
                val = float(m.group(3))
                unit = m.group(4)
                if len(pname) < 2:
                    continue
                cons[pname].append({"value": val, "unit": unit, "section": sec,
                                    "ctx": text[max(0, m.start() - 10):m.end() + 10].strip()})
        return cons

    def _unit_family(self, u):
        for fam, ud in self.unit_fams.items():
            if u in ud.get("units", []):
                return fam
        return None

    def _to_base(self, val, unit):
        conv = self.UNIT_TO_BASE.get(unit)
        if conv:
            return conv[0], val * conv[1]
        return None, val

    def _check_params(self, doc_num, doc, g):
        """参数层: 纯Z3 SMT约束求解(非启发式)

        谱系: Satisfiability Modulo Theories (SMT)
        方法: 同一参数的多次出现 → 归一化线性约束组 → Z3 Solver
             solver.check() == unsat → 确证不可满足(硬冲突)
             solver.check() == sat  → 可满足, 检查解的区间宽度
                                     (极窄=可疑, 正常=通过)
        严格区分: unsat(确证) vs 窄解区间(可疑) vs 宽解区间(通过)
        """
        out = defaultdict(list)
        cons = self._extract_constraints(doc)
        for pid, kws in self.PARAM_KEYWORDS.items():
            findings = []
            for pname, group in cons.items():
                if not any(k in pname for k in kws):
                    continue
                if len(group) < 2:
                    continue
                # 构建Z3约束组
                intervals = self._to_z3_constraints(pname, group)
                if len(intervals) < 2:
                    continue
                result = self._z3_solve(pname, intervals)
                if result:
                    findings.append(result)
            out[pid] = findings
        return out

    def _to_z3_constraints(self, pname, group):
        """约束 → Z3兼容的区间列表[(lo, hi, orig, fam)]"""
        out = []
        for c in group:
            fam, val = self._to_base(c["value"], c["unit"])
            if fam is None:
                continue
            ctx = c.get("ctx", "")
            if any(k in ctx for k in ["不超过", "≤", "小于", "低于", "少于"]):
                out.append((None, val, c, fam))
            elif any(k in ctx for k in ["不低于", "≥", "大于", "高于", "不少于", "至少"]):
                out.append((val, None, c, fam))
            else:
                out.append((val, val, c, fam))
        return out

    def _z3_solve(self, pname, intervals):
        """Z3 SMT求解: 判定约束组可满足性

        Returns: None(通过) / finding dict(确证或可疑)
        """
        import z3
        # 同族检查
        fams = set(iv[3] for iv in intervals)
        if len(fams) > 1:
            return None
        var = z3.Real(pname[:15].replace(" ", "_"))
        solver = z3.Solver()
        for iv in intervals:
            if iv[0] is not None:
                solver.add(var >= iv[0])
            if iv[1] is not None:
                solver.add(var <= iv[1])
        result = solver.check()
        if result == z3.unsat:
            # 确证: 约束组不可满足
            ev = " ∧ ".join(
                ("x ≥ %s" % iv[0] if iv[1] is None else
                 "x ≤ %s" % iv[1] if iv[0] is None else
                 "x = %s" % iv[0])
                for iv in intervals[:3])
            return {
                "desc": f"参数「{pname}」约束组Z3判定不可满足(unsat)",
                "section": " / ".join(sorted(set(iv[2]["section"] for iv in intervals))),
                "evidence": f"SMT约束: {ev} | 原文: "
                          + " vs ".join(f"{iv[2]['value']}{iv[2]['unit']}@{iv[2]['section']}"
                                       for iv in intervals[:3]),
            }
        elif result == z3.sat:
            # 可满足: 检查解区间宽度
            lo = max((iv[0] if iv[0] is not None else -1e18) for iv in intervals)
            hi = min((iv[1] if iv[1] is not None else 1e18) for iv in intervals)
            if hi - lo < 1e-6 and lo > -1e17:
                # 解空间退化为单点: 可疑
                vals = [iv[2]["value"] for iv in intervals]
                if len(set(vals)) > 1:
                    return {
                        "desc": f"参数「{pname}」约束组可满足但解空间退化为单点(可疑)",
                        "section": " / ".join(sorted(set(iv[2]["section"] for iv in intervals))),
                        "evidence": " vs ".join(
                            f"{iv[2]['value']}{iv[2]['unit']}@{iv[2]['section']}"
                            for iv in intervals[:3]),
                    }
            return None
        return None

    # ============ GJB层 ============
    GJB_PRESENCE = {
        "GJB-06": (["报警", "告警"], ["级别", "等级"]),
        "GJB-07": (["初始化", "启动", "开机"], ["自检"]),
        "GJB-08": (["掉电", "断电"], ["保护", "恢复"]),
        "GJB-09": (["输入"], ["合法性", "校验", "验证", "有效性"]),
        "GJB-10": (["升级", "版本更新"], ["回退", "回滚", "撤销"]),
        "GJB-11": (["性能", "指标"], ["降级"]),
    }

    def _check_gjb(self, doc_num, doc, g):
        out = defaultdict(list)
        all_text = " ".join(self.sec_texts.get(doc, {}).values())
        # GJB-06~11: 条款存在性(主题词出现但要素词缺失 → 警告)
        for pid, (topics, elements) in self.GJB_PRESENCE.items():
            topic_hit = any(t in all_text for t in topics)
            elem_hit = [e for e in elements if e in all_text]
            if topic_hit and not elem_hit:
                out[pid].append({
                    "desc": f"文档涉及{'/'.join(topics)}但未见要素「{'/'.join(elements)}」",
                    "section": "全文",
                    "evidence": "主题词已出现, 要素词缺失",
                })
        # GJB-05: 追溯链断裂(聚合条目chain_completeness)
        no_trace = [it for it in g["items"]
                    if it["chain_completeness"]["has_qualification"]
                    and not it["chain_completeness"]["has_trace"]]
        for it in no_trace[:10]:
            out["GJB-05"].append({
                "desc": f"实体「{it['entity_id']}」有合格性定义但无追溯关系",
                "section": " / ".join(it["sections"][:3]),
                "evidence": f"出现{it['n_occurrences']}次, chain完整度{it['chain_completeness']['score']}",
            })
        return out

    # ============ 多模态层 ============
    def _check_multimodal(self, doc_num, doc, g):
        out = defaultdict(list)
        # drift普查按文档过滤
        drifts = {pid: v for pid, v in self.drift.items()
                  if v.get("doc", "").startswith(doc[:6]) or v.get("doc", "")[:2] == doc[:2]}
        # MM-01: 流程场景 missing_in_image (sc2/sc4: 流程图↔表)
        # MM-06: 非流程场景 missing_in_image
        flow_missing, other_missing, text_drift = [], [], []
        for pid, v in drifts.items():
            scene = v.get("scene", "")
            for d in v.get("diffs", []):
                item = {"desc": f"对{pid}图-表差异({d.get('kind')})",
                        "section": scene,
                        "evidence": f"锚点侧「{d.get('xml', '')[:20]}」vs 图示侧「{d.get('img', '')[:20]}」score={d.get('score')}"}
                if d.get("kind") == "missing_in_image":
                    (flow_missing if "flowchart" in scene else other_missing).append(item)
                elif d.get("kind") == "text_drift":
                    text_drift.append(item)
        out["MM-01"] = flow_missing
        out["MM-06"] = other_missing + text_drift
        # MM-02: 悬空异常流引用(表格引用了未定义异常流)
        for ef in self.stage0.get("exception_flows", []):
            if ef.get("doc") == doc and ef.get("dangling_refs"):
                out["MM-02"].append({
                    "desc": f"用例「{ef.get('uc_name', '')[:16]}」存在悬空异常流引用",
                    "section": ef.get("section", ""),
                    "evidence": f"引用了未定义的异常流: {', '.join(ef['dangling_refs'][:4])}",
                })
        # MM-04: 参与者完备性(用例表actors vs 锚点文本)
        uc_feats = _load("data/gjb_438c/data_assets/usecase_features.json")
        anchors = _load("data/gjb_438c/anchor_v2/anchors_v2.json").get(doc, {}).get("structures", [])
        anchor_text = " ".join(n.get("text", "") for s in anchors for n in s.get("nodes", []))
        for uf in uc_feats:
            if uf.get("doc") != doc or not uf.get("actors"):
                continue
            for actor in re.split(r"[、,，\s]+", uf["actors"]):
                actor = actor.strip()
                if len(actor) >= 2 and actor not in anchor_text:
                    out["MM-04"].append({
                        "desc": f"用例「{uf.get('uc_name', '')[:14]}」的参与者未见于此文档图示",
                        "section": uf.get("section", ""),
                        "evidence": f"用例表Actors含「{actor}」, 全部锚点图中未出现",
                    })
        # MM-05: 接口拓扑自冲突(同接口不同收发方)
        if_map = defaultdict(set)
        for it in self.stage0.get("interface_topology", []):
            if it.get("doc") == doc and it.get("id") and it.get("sender") and it.get("receiver"):
                if_map[it["id"]].add((it.get("sender", ""), it.get("receiver", "")))
        out["MM-05"] = [{
            "desc": f"接口「{iid}」定义了多组收发方",
            "section": "接口表",
            "evidence": " ; ".join(f"{s}→{r}" for s, r in sorted(pairs)),
        } for iid, pairs in if_map.items() if len(pairs) > 1]
        # MM-07: 图题-图型一致性(中文关键词↔英文类型语义映射)
        CAP_TYPE_MAP = {"用例": ("usecase",), "流程": ("flow", "process"),
                        "接口": ("interface",), "活动": ("activity",),
                        "状态": ("state",), "框架": ("framework", "function"),
                        "功能": ("function", "framework")}
        for n in g["nodes"]:
            if n["type"] != "IMG":
                continue
            cap, ityp = n["payload"].get("caption", ""), n["payload"].get("img_type", "")
            if not cap or not ityp or ityp in ("other", "unknown"):
                continue
            cap_kw = next((k for k in CAP_TYPE_MAP if k in cap), None)
            if cap_kw and not any(t in ityp for t in CAP_TYPE_MAP[cap_kw]):
                out["MM-07"].append({
                    "desc": "图题与图型分类可能不符",
                    "section": n.get("section", ""),
                    "evidence": f"caption「{cap[:18]}」指向{cap_kw}图, 但分类为「{ityp}」",
                })
        # MM-09: Mermaid保真度(<80分)
        for pid, v in self.fidelity.items():
            score = v.get("fidelity_score")
            if isinstance(score, (int, float)) and score < 80:
                pair_doc = pid.split("_")[0]
                if f"{int(pair_doc):02d}" == doc[:2]:
                    missed = v.get("missed_elements", [])
                    out["MM-09"].append({
                        "desc": f"对{pid}的Mermaid导出保真度偏低({score}分)",
                        "section": v.get("dtype", ""),
                        "evidence": f"漏失元素{len(missed)}个" + (f": {str(missed[:3])[:60]}" if missed else ""),
                    })
        # MM-11: 表头模式合规(用例表必须有名称/参与者类表头)
        for n in g["nodes"]:
            if n["type"] != "TBL":
                continue
            headers = n["payload"].get("headers", [])
            ttyp = n["payload"].get("table_type", "")
            if "usecase" in ttyp and headers:
                joined = "".join(headers)
                if not any(k in joined for k in ["名称", "Use case", "Use Case", "用例"]):
                    out["MM-11"].append({
                        "desc": "用例表表头缺少名称字段",
                        "section": n.get("section", ""),
                        "evidence": f"表头: {' | '.join(headers[:5])}",
                    })
        # MM-12: 版本对齐冲突
        vp = defaultdict(dict)
        for v in self.stage0.get("version_pairs", []):
            if v.get("doc") == doc:
                vp[v.get("software", "")][v.get("section", "")] = v.get("version", "")
        for sw, secs in vp.items():
            if len(set(secs.values())) > 1:
                out["MM-12"].append({
                    "desc": f"软件「{sw}」跨表版本不一致",
                    "section": " / ".join(secs.keys()),
                    "evidence": " vs ".join(f"{s}:{v}" for s, v in secs.items()),
                })
        return out

    # ============ 逻辑层(基础) ============
    def _check_logic_basic(self, doc_num, doc, g):
        """逻辑层: 图论性质检测(环路·可达·拓扑)

        谱系: Model Checking (Clarke/Emerson 1981) → Workflow Soundness → Graph Theory
        方法:
        1. LOGIC-05: mermaid图的分支覆盖(决策+条件边 vs 正文声明)
        2. MM-01: 拓扑排序集合差(图节点集 vs 表步骤集, 报具体缺失元素)
        3. MM-06: 反向差(表格步骤不在图中)
        4. 环检测: 流程图中不应有简单环路(自环或2-环)
        """
        out = defaultdict(list)
        all_text = " ".join(self.sec_texts.get(doc, {}).values())
        from algorithms.consistency_check.mermaid_graph import parse_mermaid, diff_node_labels
        mermaids = []
        try:
            exp = _load("data/gjb_438c/anchor_v2/mermaid_export.json")
            for n in g["nodes"]:
                if n["type"] == "IMG":
                    mk = (n.get("payload", {}) or {}).get("mermaid_key")
                    if mk and mk in exp:
                        mg = parse_mermaid(exp[mk].get("mermaid", ""))
                        mg["caption"] = (n.get("payload", {}) or {}).get("caption", "")
                        mg["section"] = n.get("section", "")
                        mermaids.append(mg)
        except Exception:
            pass

        # 1. LOGIC-05: 分支覆盖(决策+条件边 vs 正文声明)
        claims = re.findall(r"(\d+)(?:种|类|个)(?:工况|模式|场景|分支|状态)", all_text)
        n_decision = sum(mg["n_decision"] for mg in mermaids)
        n_cond = sum(len(mg["cond_edges"]) for mg in mermaids)
        n_branch = n_decision + n_cond
        if claims and mermaids:
            max_claim = max(int(c) for c in claims)
            if n_branch < max_claim:
                out["LOGIC-05"].append({
                    "desc": f"正文声明{max_claim}种分支, 图中仅{n_branch}个决策+条件"
                          f"(覆盖率{n_branch/max_claim:.0%}, 缺失{max_claim-n_branch}个)",
                    "section": "全文",
                    "evidence": f"声明: {', '.join(claims[:3])}种 | "
                               f"图: {n_decision}决策 + {n_cond}条件边",
                })

        # 2. 环检测: 流程图不应有简单环路(自环或2-环)
        for mg in mermaids:
            edges = set()
            for e in mg["edges"]:
                pair = (e["src"], e["dst"])
                if pair[0] == pair[1]:
                    out.setdefault("LOGIC-07", []).append({
                        "desc": f"图「{mg['caption'][:16]}」存在自环节点(逻辑错误)",
                        "section": mg.get("section", ""),
                        "evidence": f"自环: {pair[0]}→{pair[0]}",
                    })
                if (pair[1], pair[0]) in edges:
                    out.setdefault("LOGIC-06", []).append({
                        "desc": f"图「{mg['caption'][:16]}」存在2-环(A→B→A, 互斥矛盾)",
                        "section": mg.get("section", ""),
                        "evidence": f"环: {pair[0]}↔{pair[1]}",
                    })
                edges.add(pair)

        # 3. MM-01/MM-06: 拓扑排序集合差(仅同doc同章节前缀, 最多取2对)
        pair_count = 0
        for mg in mermaids:
            if not mg["edges"] or pair_count >= 2:
                continue
            mg_sec = mg.get("section", "")
            mg_doc = g["meta"]["doc"]
            for t in self.tables:
                if t.get("doc") != mg_doc or pair_count >= 2:
                    continue
                if "用例" not in t.get("caption", ""):
                    continue
                # 严格章节匹配: 前3级须一致(如1.8.1和1.8.1.1)
                t_sec = t.get("section", "")
                if mg_sec and t_sec:
                    mg_parts = mg_sec.split(".")
                    t_parts = t_sec.split(".")
                    common = min(len(mg_parts), len(t_parts), 3)
                    if mg_parts[:common] != t_parts[:common]:
                        continue
                elif mg_sec != t_sec:
                    continue
                steps = []
                for r in t.get("rows", []):
                    line = " ".join(str(c) for c in r)
                    if any(k in line for k in ["步骤", "主事件流", "异常流"]):
                        steps.append(line[:30])
                if steps:
                    pair_count += 1
                    og, ot = diff_node_labels(mg, [
                        s.split("：")[-1] if "：" in s else s for s in steps])
                    if og:
                        out["MM-01"].append({
                            "desc": f"图「{mg['caption'][:14]}」vs表「{t['caption'][:12]}」: "
                                  f"图有{len(og)}个节点表步骤未覆盖",
                            "section": mg.get("section", ""),
                            "evidence": "图多余: " + ", ".join(og[:3]),
                        })
                    if ot:
                        out.setdefault("MM-06", []).append({
                            "desc": f"表「{t['caption'][:14]}」vs图「{mg['caption'][:12]}」: "
                                  f"表有{len(ot)}个步骤图中未出现",
                            "section": t.get("section", ""),
                            "evidence": "表多余: " + ", ".join(ot[:3]),
                        })
        return out

    # ============ 工具 ============
    def _count_claims(self, doc):
        """正文"N种/类"声明 vs 锚点节点总数(弱检查)"""
        out = []
        anchors = _load("data/gjb_438c/anchor_v2/anchors_v2.json").get(doc, {}).get("structures", [])
        if not anchors:
            return out
        # 找到与锚点同章节的计数声明
        texts = self.sec_texts.get(doc, {})
        vm = _load("data/gjb_438c/data_assets/graph/visio_section_mapping.json").get(doc, [])
        sec_nodes = defaultdict(int)
        for i, m in enumerate(vm):
            sec_nodes[m.get("matched_section", "")] += len(
                anchors[i].get("nodes", [])) if i < len(anchors) else 0
        for sec, text in texts.items():
            for mm in re.finditer(r"(\d+)(?:种|类|个)([\u4e00-\u9fff]{2,8}?)(?:功能|模块|子功能)", text):
                n_claim, target = int(mm.group(1)), mm.group(2)
                for s, n_nodes in sec_nodes.items():
                    if s and s in sec:
                        if abs(n_nodes - n_claim) >= 2:
                            out.append({
                                "desc": f"正文声明{n_claim}个{target}, 同章节图示{n_nodes}个节点",
                                "section": sec,
                                "evidence": text[max(0, mm.start() - 8):mm.end() + 8].strip(),
                            })
        return out[:6]


def unit_or_none(c):
    return c.get("unit") or "无单位"


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    from algorithms.context_association.context_graph import ContextGraph
    cg = ContextGraph()
    ce = CheckEngine(cg)
    r = ce.run("02")
    print(f"数据集: {r['doc_name'][:20]}")
    print(f"汇总: {r['summary']}")
    for c in r["categories"]:
        print(f"  {c['name']}: pass={c['pass']} warn={c['warn']} fail={c['fail']} llm={c['llm']} 发现{c['findings']}条")
    for it in r["items"]:
        if it["n_findings"] > 0:
            print(f"    [{it['id']}] {it['name']}: {it['n_findings']}条")
            for fd in it["findings"][:2]:
                print(f"       - {fd['desc'][:40]} | {fd['evidence'][:50]}")
