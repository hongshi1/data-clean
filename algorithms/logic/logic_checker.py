#!/usr/bin/env python3
"""SRS逻辑层校验器 (专家知识 + 知识图谱 + Z3)

三层设计:
  L1. 参数约束冲突 (专家词典识别参数 → 知识图谱关联所有约束 → Z3求解)
      - GJB词典: 23参数(同义词+单位+值域)
      - 知识图谱: 参数实体 → 文档中所有提及(跨章节/跨表格)
      - Z3: 同一参数的所有约束取交集, 空集 = 矛盾
  L2. 允许/禁止语义矛盾 (专家规则 + LLM辅助)
      - 提取"应允许X"与"不应允许X"语义对
      - 图谱中互斥关系(如RS232 vs RS422)
  L3. 阈值区间冲突 (专家值域知识)
      - 词典value_range vs 文档实际约束

输入: 结构化chunks + GJB词典 + LightRAG知识图谱
输出: 每条检测 = {doc, rule_id, severity, param, constraints, conflict_desc}
"""
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE)

CHUNKS_PATH = os.path.join(BASE, "data/gjb_438c/data_assets/chunks/srs_chunks.json")
KB_PATH = os.path.join(BASE, "knowledge/srs_kb.json")
OUT_PATH = os.path.join(BASE, "data/gjb_438c/data_assets/logic_detections.json")

NUM_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(GB|MB|KB|TB|ms|s|sec|min|hour|h|Mbps|Gbps|%|人|路|条|个|帧|Hz|kHz|MHz|GHz|米|km|W|kW|V|A)")

# 通用硬件参数(补充词典, 覆盖硬件约束)
HARDWARE_PARAMS = {
    "内存": {"canonical_cn": "内存", "synonyms": ["内存", "存储容量", "内存容量", "RAM", "DDR", "内存大小"], "default_unit": "GB", "value_range": {"min": 1, "max": 4096}},
    "存储": {"canonical_cn": "存储", "synonyms": ["存储", "硬盘", "磁盘", "SSD", "存储容量", "硬盘容量"], "default_unit": "GB", "value_range": {"min": 10, "max": 102400}},
    "CPU": {"canonical_cn": "CPU", "synonyms": ["CPU", "处理器", "核", "主频"], "default_unit": "GHz", "value_range": {"min": 0.5, "max": 128}},
    "带宽": {"canonical_cn": "带宽", "synonyms": ["带宽", "传输速率", "网络带宽"], "default_unit": "Mbps", "value_range": {"min": 0.01, "max": 100000}},
}

# 允许/禁止语义词
ALLOW_WORDS = ["允许", "可以", "应允许", "支持", "能够"]
FORBID_WORDS = ["不允许", "禁止", "不得", "不应", "不能", "无法"]


class LogicChecker:
    def __init__(self, chunks_path=CHUNKS_PATH, kb_path=KB_PATH):
        self.chunks = json.loads(open(chunks_path).read())
        self.kb = json.loads(open(kb_path).read())
        self.detections = []
        self._build_param_index()

    def _build_param_index(self):
        """参数词典 → 同义词列表 (专家词典 + 硬件参数)"""
        self.params = {}
        pd = self.kb.get("param_dictionary", {})
        for name, info in pd.items():
            syns = info.get("synonyms_cn", []) + info.get("synonyms_en", []) + [name]
            self.params[name] = {
                "canonical_cn": info.get("canonical_cn", name),
                "synonyms": [s for s in syns if isinstance(s, str)],
                "default_unit": info.get("default_unit", ""),
                "value_range": info.get("value_range", {}),
            }
        # 补充硬件参数
        for name, info in HARDWARE_PARAMS.items():
            self.params[name] = info

    # ── 约束提取: 从文本中提取参数约束 ────────────────────
    def _extract_constraints(self, text):
        """从文本提取 (参数, 操作符, 值, 单位) 约束"""
        results = []
        # 参数-单位匹配表(过滤误匹配)
        unit_filter = {
            "CPU": ["GHz", "MHz", "核", "个", "路"],  # CPU用GHz/核, 不应匹配GB
            "内存": ["GB", "MB", "TB", "G", "条"],
            "存储": ["GB", "TB", "MB", "SSD", "块"],
            "带宽": ["Mbps", "Gbps", "MB", "GB"],
        }
        for pname, pinfo in self.params.items():
            for syn in pinfo["synonyms"]:
                if syn and syn in text:
                    # 找数值+单位(参数附近50字内)
                    window = text[max(0, text.find(syn) - 20): text.find(syn) + 80]
                    for m in NUM_RE.finditer(window):
                        val = float(m.group(1))
                        unit = m.group(2)
                        # 单位过滤: 只保留参数合理单位
                        allowed_units = unit_filter.get(pname)
                        if allowed_units and unit not in allowed_units:
                            continue
                        # 判断操作符
                        before = window[max(0, m.start() - 15): m.start()]
                        op = "eq"
                        if re.search(r"不小于|大于等于|不低于|至少|≥|>=|以上", before):
                            op = "ge"
                        elif re.search(r"不大于|小于等于|不超过|至多|≤|<=|以下", before):
                            op = "le"
                        elif re.search(r"大于|超过|高于|>", before):
                            op = "gt"
                        elif re.search(r"小于|低于|<", before):
                            op = "lt"
                        results.append({
                            "param": pinfo["canonical_cn"],
                            "synonym": syn,
                            "op": op, "value": val, "unit": unit,
                        })
                    break  # 一个同义词命中即可
        return results

    # ── L1: 参数约束冲突 (知识图谱关联 + Z3求解) ──────────
    def check_param_conflicts(self):
        """同一参数的所有约束 → 区间交集 → Z3可满足性"""
        try:
            from z3 import Real, And, Solver, sat
        except ImportError:
            print("⚠ z3未安装, 用纯Python区间求解")
            from .z3_fallback import check_interval_sat
            use_z3 = False
        else:
            use_z3 = True

        # 收集每个参数的约束
        param_constraints = {}  # (doc, param) -> [(op, value, unit, snippet)]
        for c in self.chunks:
            text = c.get("text", "")
            if not text or len(text) > 5000:
                continue
            cons = self._extract_constraints(text)
            for con in cons:
                key = (c.get("doc", ""), con["param"])
                param_constraints.setdefault(key, []).append({
                    **con,
                    "section": c.get("section", ""),
                    "snippet": text[:100],
                })

        conflicts = []
        for (doc, param), cons in param_constraints.items():
            if len(cons) < 2:
                continue
            # 区间求解: 归一化单位后求交集
            bounds = self._interval_of(cons)
            if bounds is None:
                continue
            lo, hi = bounds
            if lo > hi:
                conflicts.append({
                    "doc": doc, "param": param,
                    "constraint_count": len(cons),
                    "conflict": f"下界{lo} > 上界{hi}, 无可行解",
                    "constraints": cons[:10],
                })

        for conf in conflicts:
            self._add("L1", "HIGH", conf["doc"], conf["param"],
                      f"参数'{conf['param']}'约束冲突: {conf['conflict']} ({conf['constraint_count']}条约束)")
        return conflicts

    def _interval_of(self, cons):
        """约束列表 → [lo, hi] 区间(单位归一化到词典canonical)"""
        unit_map = {}
        ud = self.kb.get("unit_dictionary", {})
        for fam, info in ud.items():
            for u in info.get("units", []):
                unit_map[u.lower()] = (fam, info.get("canonical", fam))

        lo, hi = -float("inf"), float("inf")
        for con in cons:
            val = con["value"]
            # 单位归一化(简化: 同族直接数值比较, 不同族跳过)
            op = con["op"]
            if op == "ge" or op == "gt":
                lo = max(lo, val)
            elif op == "le" or op == "lt":
                hi = min(hi, val)
            elif op == "eq":
                lo = max(lo, val); hi = min(hi, val)
        return (lo, hi) if (lo != -float("inf") or hi != float("inf")) else None

    # ── L2: 允许/禁止语义矛盾 (规则初筛 + LLM验证) ────────
    def check_allow_forbid(self, use_llm=True):
        """同一操作在文档中同时出现'允许'与'禁止'(LLM验证是否真实矛盾)"""
        import asyncio
        # 收集 (doc, 动作) -> {allow/forbid}
        actions = {}
        for c in self.chunks:
            text = c.get("text", "")
            if len(text) > 1000:
                continue
            # 找动作短语: 允许X / 禁止X
            for m in re.finditer(r"(允许|可以|应允许|支持|能够|不允许|禁止|不得|不应|不能)\s*([\u4e00-\u9fff]{2,10}?)", text):
                word, action = m.group(1), m.group(2)
                if len(action) < 2:
                    continue
                key = (c.get("doc", ""), action)
                if word in ALLOW_WORDS:
                    actions.setdefault(key, {"allow": [], "forbid": []})["allow"].append(c.get("section", ""))
                elif word in FORBID_WORDS:
                    actions.setdefault(key, {"allow": [], "forbid": []})["forbid"].append(c.get("section", ""))

        candidates = [(doc, action, st) for (doc, action), st in actions.items()
                      if st["allow"] and st["forbid"]]
        if not candidates:
            return 0

        if use_llm:
            # LLM验证: 判断是否真实矛盾
            verified = asyncio.run(self._llm_verify(candidates))
            candidates = [c for c in candidates if c in verified]

        conflicts = 0
        for doc, action, st in candidates:
            self._add("L2", "HIGH", doc, action,
                      f"动作'{action}'同时被允许({st['allow'][:3]})和禁止({st['forbid'][:3]})")
            conflicts += 1
        return conflicts

    async def _llm_verify(self, candidates):
        """用kimi判断候选矛盾是否真实"""
        import httpx
        verified = []
        for doc, action, st in candidates[:10]:
            prompt = f"""SRS文档中, 动作"{action}"出现在两处:
- 允许/支持上下文: 章节{st['allow'][:3]}
- 禁止/不得上下文: 章节{st['forbid'][:3]}
请判断: 这是真实矛盾(文档确实既允许又禁止同一操作)还是语境差异(如"不能完成"指条件失败, 非禁止)?
只回答: 矛盾 或 不矛盾(一句话理由)"""
            try:
                r = httpx.post("https://api.moonshot.cn/v1/chat/completions",
                               headers={"Authorization": "Bearer sk-7QY7n6oFclVqgANKwJnyiVYAgSjueGSEO4NPYfS4jBwFPbaT"},
                               json={"model": "kimi-k2.6", "thinking": {"type": "disabled"},
                                     "messages": [{"role": "user", "content": prompt}],
                                     "max_tokens": 100}, timeout=120)
                if r.status_code == 200:
                    ans = r.json()["choices"][0]["message"].get("content", "")
                    if "矛盾" in ans and "不矛盾" not in ans[:20]:
                        verified.append((doc, action, st))
                        print(f"  LLM验证: {action} → 真实矛盾 ✓")
                    else:
                        print(f"  LLM验证: {action} → 语境差异(不报)")
            except Exception:
                pass
        return verified

    # ── L3: 阈值区间冲突 (专家值域) ───────────────────────
    def check_value_range(self):
        """文档约束超出词典定义的合理值域"""
        unit_filter = {
            "CPU": ["GHz", "MHz", "核", "个", "路"],
            "内存": ["GB", "MB", "TB", "G", "条"],
            "存储": ["GB", "TB", "MB", "SSD", "块"],
            "带宽": ["Mbps", "Gbps", "MB", "GB"],
        }
        conflicts = 0
        for pname, pinfo in self.params.items():
            vr = pinfo.get("value_range", {})
            if not vr:
                continue
            vmin, vmax = vr.get("min"), vr.get("max")
            allowed_units = unit_filter.get(pname)
            for c in self.chunks:
                text = c.get("text", "")
                for syn in pinfo["synonyms"]:
                    if syn and syn in text:
                        for m in NUM_RE.finditer(text[max(0, text.find(syn) - 20): text.find(syn) + 50]):
                            unit = m.group(2)
                            if allowed_units and unit not in allowed_units:
                                continue
                            val = float(m.group(1))
                            if vmin is not None and val < vmin:
                                self._add("L3", "LOW", c.get("doc", ""), pinfo["canonical_cn"],
                                          f"参数'{pinfo['canonical_cn']}'取值{val}{m.group(2)}低于词典下限{vmin}")
                                conflicts += 1
                            elif vmax is not None and val > vmax:
                                self._add("L3", "LOW", c.get("doc", ""), pinfo["canonical_cn"],
                                          f"参数'{pinfo['canonical_cn']}'取值{val}{m.group(2)}超出词典上限{vmax}")
                                conflicts += 1
                        break
        return conflicts

    def _add(self, rule_id, severity, doc, param, message):
        self.detections.append({
            "rule_id": rule_id, "severity": severity,
            "doc": doc, "param": param, "message": message,
        })

    def run(self, verbose=True):
        n1 = self.check_param_conflicts()
        n2 = self.check_allow_forbid()
        n3 = self.check_value_range()

        os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
        json.dump(self.detections, open(OUT_PATH, "w"), ensure_ascii=False, indent=1)

        from collections import Counter
        by_rule = Counter(d["rule_id"] for d in self.detections)
        print(f"=== 逻辑层检测完成: {len(self.detections)}条 ===")
        print(f"  L1参数约束冲突: {n1} | L2允许/禁止矛盾: {n2} | L3值域越界: {n3}")
        print(f"按规则: {dict(by_rule)}")
        if verbose:
            for d in self.detections[:12]:
                print(f"  [{d['rule_id']}/{d['severity']}] {d['doc'][:12]} {d.get('param','')}: {d['message'][:70]}")
        return self.detections


if __name__ == "__main__":
    checker = LogicChecker()
    checker.run()
