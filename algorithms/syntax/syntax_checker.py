#!/usr/bin/env python3
"""SRS语法层校验器 (基于GJB 438C规则库)

检测类型(可落地的GJB规则子集):
  S1. 章节编号连续性: 3.1, 3.2, 3.3... 无跳跃
  S2. 需求ID唯一性: PZXQ-xxx 不重复
  S3. 需求ID格式合规: [A-Z]{2,8}(-[A-Z0-9]{2,8}){2,}
  S4. 图/表引用完整性: 文中引用的图N/表N必须存在
  S5. 章节结构完整性: GJB规定的6章结构(1范围/2引用文档/3需求/4合格性/5需求可追踪性/6注解)
  S6. 标题层级规范: 章节标题格式(数字编号+空格+标题)
  S7. 交叉引用完整性: "见X.X节"/"见表N"的引用目标存在

输入: 16份SRS的结构化chunks (srs_chunks.json)
输出: 每条检测 = {doc, rule_id, severity, section, message, snippet}
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE)

CHUNKS_PATH = os.path.join(BASE, "data/gjb_438c/data_assets/chunks/srs_chunks.json")
RULES_PATH = os.path.join(BASE, "knowledge/gjb_438c_rules_full.json")
OUT_PATH = os.path.join(BASE, "data/gjb_438c/data_assets/syntax_detections.json")

ID_RE = re.compile(r"[A-Z]{2,8}(?:-[A-Z0-9]{2,8}){2,}")
SECTION_RE = re.compile(r"^(\d+(?:\.\d+)*)\s+(.+)$")
FIG_REF_RE = re.compile(r"图\s*(\d+)")
TABLE_REF_RE = re.compile(r"表\s*(\d+)")

# GJB 438C SRS标准章节结构
SRS_SECTIONS = ["1", "2", "3", "4", "5", "6"]


class SyntaxChecker:
    def __init__(self, chunks_path=CHUNKS_PATH):
        self.chunks = json.loads(open(chunks_path).read())
        self.detections = []
        # 预索引
        self.docs = defaultdict(list)
        for c in self.chunks:
            self.docs[c["doc"]].append(c)
        self._id_counter = Counter()
        self._section_trees = {}
        self._figures = defaultdict(set)   # doc -> {fig_num}
        self._tables = defaultdict(set)    # doc -> {table_num}
        self._build_index()

    def _build_index(self):
        for doc, chunks in self.docs.items():
            # 章节树
            secs = set()
            for c in chunks:
                s = c.get("section", "")
                if s:
                    secs.add(s)
                    self._section_trees.setdefault(doc, set()).add(s)
            # 图表编号
            for c in chunks:
                text = c.get("text", "")
                for m in FIG_REF_RE.finditer(text):
                    # 若"图N"是定义(在caption/标题中), 记入figures
                    if c.get("type") == "image" or "[图" in text or text.strip().startswith("图"):
                        self._figures[doc].add(int(m.group(1)))
                for m in TABLE_REF_RE.finditer(text):
                    if c.get("type") == "table" or "[表格标题" in text:
                        self._tables[doc].add(int(m.group(1)))
            # 需求ID计数
            for c in chunks:
                for m in ID_RE.finditer(c.get("text", "")):
                    self._id_counter[(doc, m.group(0))] += 1

    def _add(self, rule_id, severity, doc, section, message, snippet=""):
        self.detections.append({
            "rule_id": rule_id,
            "severity": severity,
            "doc": doc,
            "section": section,
            "message": message,
            "snippet": snippet[:150],
        })

    # ── S1: 章节编号连续性 ────────────────────────────────
    def check_section_continuity(self):
        """同级章节编号应连续(如3.1, 3.2, 3.3无跳跃)"""
        for doc, secs in self._section_trees.items():
            # 提取一级章节
            l1 = sorted({int(s.split(".")[0]) for s in secs if s.split(".")[0].isdigit()})
            for i in range(1, len(l1)):
                if l1[i] != l1[i-1] + 1:
                    self._add("S1", "MEDIUM", doc, str(l1[i]),
                              f"一级章节编号跳跃: {l1[i-1]} → {l1[i]}, 缺少{l1[i-1]+1}")
            # 二级章节(3.x)
            l2 = sorted({int(s.split(".")[1]) for s in secs
                         if len(s.split(".")) >= 2 and s.split(".")[0] == "3" and s.split(".")[1].isdigit()})
            for i in range(1, len(l2)):
                if l2[i] != l2[i-1] + 1:
                    self._add("S1", "LOW", doc, f"3.{l2[i]}",
                              f"3.x章节编号跳跃: 3.{l2[i-1]} → 3.{l2[i]}, 缺少3.{l2[i-1]+1}")

    # ── S2: 需求ID唯一性(标题定义位置) ────────────────────
    def check_id_unique(self):
        """只查章节标题中的ID(定义位置), 多处引用不算重复"""
        title_ids = Counter()
        for doc, chunks in self.docs.items():
            for c in chunks:
                text = c.get("text", "")
                # 章节标题: 数字编号开头+短文本
                is_title = bool(re.match(r"^\d+(\.\d+)*\s+\S", text)) and len(text) < 80
                if not is_title:
                    continue
                for m in ID_RE.finditer(text):
                    iid = m.group(0)
                    if len(iid) > 15:
                        title_ids[(doc, iid)] += 1
        for (doc, iid), cnt in title_ids.items():
            if cnt > 1:
                self._add("S2", "HIGH", doc, "",
                          f"需求ID重复定义: {iid} 出现在{cnt}个章节标题")

    # ── S3: ID格式合规 ────────────────────────────────────
    def check_id_format(self):
        # 已在ID_RE中约束格式; 额外检查: 全部大写字母数字+连字符
        for (doc, iid), _ in self._id_counter.items():
            if not re.match(r"^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+$", iid):
                self._add("S3", "HIGH", doc, "",
                          f"ID格式异常: {iid}")

    # ── S4: 图/表引用完整性 ──────────────────────────────
    def check_fig_table_refs(self):
        for doc, chunks in self.docs.items():
            figs = self._figures.get(doc, set())
            tables = self._tables.get(doc, set())
            # 正文中引用的图/表号(引用 = 出现在非caption位置)
            for c in chunks:
                text = c.get("text", "")
                if c.get("type") in ("table", "image"):
                    continue
                for m in FIG_REF_RE.finditer(text):
                    num = int(m.group(1))
                    # 排除标题/图注中的"图N xxx"(那可能是定义)
                    if m.start() > 0 and text[max(0, m.start()-3):m.start()] in ("见图", "如下"):
                        if num not in figs:
                            self._add("S4", "LOW", doc, c.get("section", ""),
                                      f"引用的图{num}未找到(文档中已知图: {sorted(figs)[:5]})")
                for m in TABLE_REF_RE.finditer(text):
                    num = int(m.group(1))
                    if num not in tables:
                        self._add("S4", "LOW", doc, c.get("section", ""),
                                  f"引用的表{num}未找到(文档中已知表: {sorted(tables)[:5]})")

    # ── S5: 章节结构完整性 ────────────────────────────────
    def check_structure(self):
        for doc, secs in self._section_trees.items():
            l1 = {s.split(".")[0] for s in secs if s.split(".")[0].isdigit()}
            for must in SRS_SECTIONS:
                if must not in l1:
                    self._add("S5", "HIGH", doc, must,
                              f"缺少GJB要求的第{must}章(标准结构: 1范围/2引用文档/3需求/4合格性/5可追踪性/6注解)")

    # ── S6: 标题层级规范 ──────────────────────────────────
    def check_title_format(self):
        for doc, chunks in self.docs.items():
            for c in chunks:
                if c.get("type") != "text":
                    continue
                text = c.get("text", "").strip()
                m = SECTION_RE.match(text)
                if m and len(text) < 60:  # 短文本且是章节标题格式
                    sec, title = m.group(1), m.group(2)
                    # 标题不应以标点开头
                    if title and title[0] in "，。；：":
                        self._add("S6", "LOW", doc, sec,
                                  f"章节标题格式异常: '{text[:40]}'")

    # ── S7: 交叉引用完整性 ────────────────────────────────
    def check_cross_refs(self):
        for doc, chunks in self.docs.items():
            all_secs = self._section_trees.get(doc, set())
            for c in chunks:
                text = c.get("text", "")
                # 找"X.X.X节"引用
                for m in re.finditer(r"(\d+\.\d+(?:\.\d+)*)\s*节", text):
                    ref = m.group(1)
                    if ref not in all_secs:
                        # 父章节也算(3.2引用3.2.1的子节)
                        parents = [ref[:i] for i in range(len(ref), 0, -1) if ref[:i] in all_secs]
                        if not parents:
                            self._add("S7", "LOW", doc, c.get("section", ""),
                                      f"引用的章节{ref}不存在(已知章节示例: {sorted(all_secs)[:5]})")

    # ── 主流程 ────────────────────────────────────────────
    def run(self, verbose=True):
        self.check_section_continuity()
        self.check_id_unique()
        self.check_id_format()
        self.check_fig_table_refs()
        self.check_structure()
        self.check_title_format()
        self.check_cross_refs()

        # 汇总
        os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
        json.dump(self.detections, open(OUT_PATH, "w"), ensure_ascii=False, indent=1)

        from collections import Counter
        by_rule = Counter(d["rule_id"] for d in self.detections)
        by_sev = Counter(d["severity"] for d in self.detections)
        print(f"=== 语法层检测完成: {len(self.detections)}条 ===")
        print(f"按规则: {dict(by_rule)}")
        print(f"按严重度: {dict(by_sev)}")
        if verbose:
            print("\n样例检测:")
            for d in self.detections[:10]:
                print(f"  [{d['rule_id']}/{d['severity']}] {d['doc'][:12]} {d['section']}: {d['message'][:60]}")
        return self.detections


if __name__ == "__main__":
    checker = SyntaxChecker()
    checker.run()
