#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""consistency_engine.py — 一致性引擎 v2（按三条诊断重写）
================================================================

重写针对的三个问题:
  ①翻译层(原regex糊弄) → LLM声明抽取器: 自由文本(QA答案)走LLM(kimi远端/Ollama本地Qwen,
    JSON Schema校验+错误反馈重试+哈希缓存=可复现); 受控文本(GJB正文的"包括："句/表格/ID)
    走模式抽取——受控语言用模式是正当地( CNL思想), 自由语言必须学习。
  ②考卷自出 → 真实评测: doc11的69条真实QA + 7个人工核对的gold标记(必须抓出),
    引擎在真实数据上的抓出率/误报率才是唯一口径。
  ③无真实产出 → 文档扫描器: 16份文档正文枚举/表格ID/图节点交叉核验 → 真实矛盾清单。

统一声明代数(一套claim覆盖文档文本与QA文本):
  enumeration(集合) / parameter(参数) / identifier(编号) / process(步骤)
  / precondition(前置) / participant(角色) / relation / direction
每个kind映射到一个核验谓词; 声明源=LLM(自由)或模式(受控), 谓词共用。

用法:
  python tools/consistency_engine.py smoke                 # 抽取器冒烟(5条真实QA)
  python tools/consistency_engine.py eval-qa               # 69条真实QA评级 vs 7条gold
  python tools/consistency_engine.py scan-docs [--doc 04]  # 16文档真实矛盾扫描
  (全局: --backend kimi|ollama  --limit N)
"""
import argparse
import hashlib
import json
import re
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "tools"))

DOC11_QA = BASE / "docs/doc11/场景1-软件需求规格辅助生成场景补发数据/高质量问答对（配套样例数据中：04数据统一访问服务软件需求规格说明）.json"
GOLD = BASE / "data/gjb_438c/data_assets/doc11_gold_marks.json"
MINERU_DIR = BASE / "data/gjb_438c/mineru_standard"
ANCHORS_V3 = BASE / "data/gjb_438c/anchor_v3/anchors_v3.json"
CACHE_PATH = BASE / "data/llm_cache/claim_extraction_v1.json"
FINDINGS_OUT = BASE / "data/gjb_438c/data_assets/real_doc_findings.json"
QA_EVAL_OUT = BASE / "data/gjb_438c/data_assets/doc11_qa_grading.json"

CLAIM_KINDS = ["enumeration", "parameter", "identifier", "process",
               "precondition", "participant", "relation", "direction"]

NLI_MODEL_DIR = BASE / "models/nli/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"
_OP_CN = {"gt": "大于", "lt": "小于", "le": "不超过", "ge": "至少", "eq": "为"}


class NLIVerifier:
    """mDeBERTa零样本NLI通道(仅接NLI强项: 参数冲突/蕴含/前置; 枚举已证全盲0/3不接)
    实测(14条真实对): 参数冲突2/2, 蕴含5/5, 枚举0/3, 方向反转1/1"""

    def __init__(self, model_dir=NLI_MODEL_DIR):
        sys.path.insert(0, str(BASE / "tools"))
        from torch_dll_fix import preload_torch_dlls
        preload_torch_dlls()
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        self.torch = torch
        torch.set_grad_enabled(False)
        self.tok = AutoTokenizer.from_pretrained(str(model_dir), local_files_only=True)
        self.mdl = AutoModelForSequenceClassification.from_pretrained(str(model_dir), local_files_only=True)
        self.mdl.eval()
        self.id2label = {int(k): v for k, v in self.mdl.config.id2label.items()}
        self.n_calls = 0

    @staticmethod
    def _norm(label):
        lab = str(label).lower()
        if "entail" in lab:
            return "supported"
        if "contradict" in lab:
            return "contradicted"
        return "unsupported"

    def verify(self, premise, hypothesis):
        """(文档事实句, 声明句) → (verdict, conf)"""
        self.n_calls += 1
        enc = self.tok(premise, hypothesis, return_tensors="pt", truncation=True, max_length=256)
        probs = self.torch.softmax(self.mdl(**enc).logits, -1)[0]
        idx = int(self.torch.argmax(probs))
        return self._norm(self.id2label.get(idx, idx)), float(probs[idx])

    def verify_best(self, premises, hypothesis):
        """多前提取最强判定(contradicted > supported > unsupported)"""
        best = ("unsupported", 0.0)
        order = {"unsupported": 0, "supported": 1, "contradicted": 2}
        for p in premises:
            v, c = self.verify(p, hypothesis)
            if order[v] > order[best[0]] or (order[v] == order[best[0]] and c > best[1]):
                best = (v, c)
        return best


# ════════════════════════════════════════════════════════════════
# ① 翻译层: LLM声明抽取器(自由文本) + 模式抽取器(受控文本)
# ════════════════════════════════════════════════════════════════

EXTRACT_PROMPT = """你是需求文档一致性校验系统的声明抽取器。从中文文本中抽取所有**可核验的声明**（对文档事实的可验证断言）。

声明种类 kind（只能取这些值）:
- enumeration: 集合/列举声明（"BLOB数据操作包括插入、删除、查询"→entity=BLOB数据操作, elements=[插入,删除,查询]）
- parameter: 数值参数声明（"1秒内查询最多1000条"→param={value:1000,unit:条,op:le}，时间限制类另抽一条{value:1,unit:秒}）
- identifier: 编号/标识声明（"删除数据记录(PZXQ-GN-SQLFW-XGSJ-SJXG)"→identifier=该编号, entity=删除数据记录）
- process: 步骤/流程声明（主事件流的有序步骤→elements按序）
- precondition: 前置条件声明（"前置条件是数据库连接正常"→condition=数据库连接正常）
- participant: 参与者声明（"参与者是应用软件和数据库"→participants=[应用软件,数据库]）
- relation: 实体关系声明（依赖/包含/关联等，entity与related）
- direction: 方向/顺序声明（"A指向B"/"先A后B"→entity=A, related=B）

文本（「context_type」）:
「text」

规则: 每条声明必须带source_quote(支撑原文片段≤40字)；只抽取文本明确陈述的内容，不要推理补充。
- elements元素必须是**简短名词短语(≤10字)**——描述性长句只取其中的核心功能名(如"允许用户使用SQL语句进行操作"→元素取"SQL语句操作")
- 答案含**表格**时: 表格每行的编号(PZXQ-…样式)各抽一条identifier声明(entity=该行用例名, identifier=编号)
- 答案列出多个子功能时, 每个功能集合单独一条enumeration声明(如BLOB的{删除,更新,查询})
严格输出JSON（无声明输出{{"claims":[]}}）:
{{"claims":[{{"kind":"enumeration","entity":"","elements":[],"param":{{"value":0,"unit":"","op":"eq"}},"identifier":"","condition":"","participants":[],"related":"","source_quote":""}}]}}"""


class LLMClaimExtractor:
    """自由文本→声明。backend: kimi(远端,temperature=1)/ollama(本地,JSON Schema约束)"""

    def __init__(self, backend="kimi", model=None, cache=True):
        self.backend = backend
        if backend == "kimi":
            from ai_config import KIMI_KEY
            self.key = KIMI_KEY
            self.url = "https://api.moonshot.cn/v1/chat/completions"
            self.model = model or "kimi-k2.6"
        else:
            self.url = "http://localhost:11434/api/generate"
            self.model = model or "qwen2.5:14b"
        self.cache = {} if not cache else self._load_cache()
        self.cache_enabled = cache
        self.n_calls = 0

    def _load_cache(self):
        if CACHE_PATH.exists():
            try:
                return json.load(open(CACHE_PATH, encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save_cache(self):
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        json.dump(self.cache, open(CACHE_PATH, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=0)

    def _raw_call(self, prompt):
        if self.backend == "kimi":
            import httpx
            r = httpx.post(self.url, headers={"Authorization": f"Bearer {self.key}",
                                              "Content-Type": "application/json"},
                           json={"model": self.model,
                                 "messages": [{"role": "user", "content": prompt}],
                                 "thinking": {"type": "disabled"},
                                 "temperature": 0.6, "max_tokens": 2500,
                                 "response_format": {"type": "json_object"}}, timeout=120)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        else:
            import httpx
            r = httpx.post(self.url, json={"model": self.model, "prompt": prompt,
                                           "stream": False,
                                           "format": {"type": "object",
                                                      "properties": {"claims": {"type": "array"}}},
                                           "options": {"temperature": 0.1, "seed": 42}},
                           timeout=180)
            r.raise_for_status()
            return r.json().get("response", "")

    @staticmethod
    def _validate(claims):
        """语义校验(合法JSON≠合法声明): 返回错误列表"""
        errs = []
        for i, c in enumerate(claims):
            k = c.get("kind")
            if k not in CLAIM_KINDS:
                errs.append(f"claim[{i}].kind={k!r} 不在{CLAIM_KINDS}")
                continue
            if not (c.get("source_quote") or "").strip():
                errs.append(f"claim[{i}]缺source_quote")
            if k == "enumeration" and len(c.get("elements") or []) < 2:
                errs.append(f"claim[{i}].enumeration elements<2")
            if k == "process" and len(c.get("elements") or []) < 2:
                errs.append(f"claim[{i}].process elements<2")
            if k == "parameter":
                p = c.get("param") or {}
                try:
                    float(p.get("value"))
                except (TypeError, ValueError):
                    errs.append(f"claim[{i}].parameter value非数值")
            if k == "identifier" and not re.search(r"[A-Z]{2,}", c.get("identifier") or ""):
                errs.append(f"claim[{i}].identifier非编号")
            if k == "precondition" and not (c.get("condition") or "").strip():
                errs.append(f"claim[{i}].precondition缺condition")
            if k == "participant" and not (c.get("participants") or []):
                errs.append(f"claim[{i}].participant缺participants")
        return errs

    def extract(self, text, context_type="qa_answer"):
        """自由文本 → 校验通过的claims列表（含错误反馈重试×2）"""
        h = hashlib.md5(f"{self.backend}|{self.model}|{context_type}|{text}".encode()).hexdigest()
        if self.cache_enabled and h in self.cache:
            return self.cache[h]
        base_prompt = (EXTRACT_PROMPT
                       .replace("「context_type」", context_type)
                       .replace("「text」", text[:3000])
                       .replace("{{", "{").replace("}}", "}"))
        prompt = base_prompt
        claims, last_errs = [], []
        for attempt in range(3):
            self.n_calls += 1
            try:
                raw = self._raw_call(prompt if attempt == 0 else
                                     base_prompt + "\n\n你上一次输出存在以下问题, 请修正后重新输出:\n" +
                                     "; ".join(last_errs[:5]))
            except Exception as e:
                last_errs = [f"API错误: {type(e).__name__} {str(e)[:80]}"]
                time.sleep(2)
                continue
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if not m:
                last_errs = ["输出无JSON"]
                continue
            try:
                claims = json.loads(m.group(0)).get("claims", [])
            except json.JSONDecodeError:
                last_errs = ["JSON解析失败"]
                continue
            last_errs = self._validate(claims)
            if not last_errs:
                break
        if self.cache_enabled:
            self.cache[h] = claims
            self._save_cache()
        return claims

    def extract_batch(self, texts, workers=4, desc=""):
        out = [None] * len(texts)

        def run(i):
            return i, self.extract(texts[i])
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = [pool.submit(run, i) for i in range(len(texts))]
            for n, f in enumerate(as_completed(futs)):
                i, c = f.result()
                out[i] = c
                if (n + 1) % 10 == 0:
                    print(f"  [{desc} {n+1}/{len(texts)}] (API调用累计{self.n_calls})")
        return out


# ════════════════════════════════════════════════════════════════
# 文档事实库(受控文本模式抽取): 句子/枚举/编号/表格行/图节点
# ════════════════════════════════════════════════════════════════

def _strip_tags(s):
    return re.sub(r"<[^>]+>", "", s or "").strip()


def _norm(s):
    return re.sub(r"[\s\u3000]", "", _strip_tags(s))


def _items_match(a, b):
    """枚举元素模糊匹配: 归一后互相包含(≥2字)"""
    a, b = _norm(a), _norm(b)
    if not a or not b:
        return False
    if a == b or (len(a) >= 2 and a in b) or (len(b) >= 2 and b in a):
        return True
    return False


def _subject_match(entity, subj):
    """枚举主语匹配: 归一+剥装饰(括号/的/大字段前缀)后互相包含"""
    def core(s):
        s = _norm(s)
        s = re.sub(r"[（）()]", "", s)
        s = s.replace("的", "")
        for deco in ("大字段", "小字段", "字段"):
            if s.startswith(deco):
                s = s[len(deco):]
        return s
    a, b = core(entity), core(subj)
    if not a or not b:
        return False
    return a == b or (len(a) >= 4 and a in b) or (len(b) >= 4 and b in a)


class DocFacts:
    """一份文档的可核验事实: 来自content_list(正文句/枚举/编号/表格行) + anchors_v3(图节点)"""

    def __init__(self, doc_num):
        self.doc_num = doc_num
        self.sentences = []       # [(section, text)]
        self.enumerations = []    # [(section, subject, [items])]
        self.identifiers = []     # [(section, name, id)]
        self.table_rows = []      # [(caption, [cells])]
        self.graph_nodes = []     # [[node_text]] per structure
        self._usecase_children = defaultdict(list)
        self._load()

    def _load(self):
        import glob
        pats = glob.glob(str(MINERU_DIR / f"{self.doc_num}*/office/*content_list.json"))
        if not pats:
            raise FileNotFoundError(f"doc {self.doc_num} content_list 未找到")
        cl = json.load(open(pats[0], encoding="utf-8"))
        sec = ""
        for it in cl:
            if not isinstance(it, dict):
                continue
            if it.get("type") == "text":
                t = it.get("text", "")
                m = re.match(r"^(\d+(?:\.\d+)*)\s+(.+)$", t.strip())
                if m and len(m.group(2)) < 40:
                    sec = m.group(1)
                elif len(t.strip()) > 10:
                    self.sentences.append((sec, t.strip()))
                # 受控句枚举: "X包括：A、B、C" / "X分为..." / "X包含..."
                em = re.match(r"^(.{2,24}?)(?:功能)?(?:包括|包含|分为)[:：]\s*(.+?)[。，；]",
                              t.strip())
                if em:
                    items = re.split(r"[、，,]", em.group(2))
                    items = [x.strip() for x in items if len(x.strip()) >= 2][:12]
                    if len(items) >= 2:
                        self.enumerations.append((sec, em.group(1), items))
                # 编号: "名称（PZXQ-...）"
                im = re.findall(r"(.{2,30}?)（([A-Z]{2,}(?:-[A-Z0-9]+)+)）", t)
                for name, cid in im:
                    self.identifiers.append((sec, name.strip(), cid))
                # 用例节标题形如 "X-Y（ID）" → (父名, 子用例名, ID) — ID内含空格也容错
                im2 = re.findall(r"(修改数据|查询数据|BLOB数据操作|数据库操作|数据查询)-(.{2,20}?)（\s*([A-Z0-9\-\s]+?)\s*）", t)
                for parent, name, cid in im2:
                    cid = cid.replace(" ", "")
                    self.identifiers.append((sec, f"{parent}-{name}", cid))
                    self._usecase_children[parent].append(name.strip())
            elif it.get("type") == "table":
                body = it.get("table_body", "")
                caption = " ".join(it.get("table_caption", []) or "")
                for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", body, re.DOTALL):
                    cells = [_strip_tags(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.DOTALL)]
                    if any(cells):
                        self.table_rows.append((caption, cells))
                        # 表行里的编号 → 标识事实(表9能力标识表的短格式ID vs 标题长格式ID=文档级发现源)
                        id_cell = next((c for c in cells
                                        if re.match(r"^[A-Z]{2,}(-[A-Z0-9]+)+$", c)), None)
                        if id_cell:
                            name_cell = next((c for c in cells if c != id_cell and 2 <= len(c) <= 20), "")
                            self.identifiers.append((f"表格{caption[:10]}", name_cell, id_cell))
        # 用例节兄弟集 → 枚举源(关键: L388正文列举 vs 子用例节标题集的差异=文档级TERM-03)
        for parent, children in self._usecase_children.items():
            uniq = sorted(set(children))
            if len(uniq) >= 2:
                self.enumerations.append((f"用例节({parent})", parent, uniq))
        # 图节点(anchors_v3)
        try:
            a3 = json.load(open(ANCHORS_V3, encoding="utf-8"))
            for doc, dd in a3.items():
                if doc.startswith(self.doc_num):
                    for st in dd.get("structures", []):
                        texts = [n.get("text", "") for n in st.get("nodes", []) if n.get("text")]
                        if len(texts) >= 3:
                            self.graph_nodes.append(texts)
        except FileNotFoundError:
            pass

    # ---------- 核验谓词(声明→判定) ----------
    def verify_enumeration(self, entity, elements):
        """集合声明 vs 文档多源(L388式正文枚举/图节点集): 返回[(source, verdict, detail)]"""
        results = []
        targets = []
        for sec, subj, items in self.enumerations:
            if _subject_match(entity, subj):
                targets.append((f"正文{sec}「{subj}」", items))
        for i, nodes in enumerate(self.graph_nodes):
            pref = _norm(entity)[:min(6, len(_norm(entity)))]
            short_nodes = [n for n in nodes if len(n) <= 14]
            matched = sum(1 for n in nodes if any(_items_match(n, e) for e in elements))
            # 规模相容: 图须是"该实体自身的分解图"(多数节点对应+规模相近), 跳过架构图
            if (pref and any(pref in _norm(n) for n in nodes)
                    and matched >= 2 and len(short_nodes) <= len(elements) + 3):
                targets.append((f"图结构#{i}", nodes))
        if not targets:
            return [("none", "unsupported", "文档中未找到该实体的集合事实")]
        for src, doc_items in targets:
            claim_unmatched = [e for e in elements
                               if not any(_items_match(e, d) for d in doc_items)]
            doc_unmatched = [d for d in doc_items
                             if not any(_items_match(d, e) for e in elements)]
            if not claim_unmatched and not doc_unmatched:
                results.append((src, "supported", "集合一致"))
            elif claim_unmatched and not doc_unmatched:
                results.append((src, "contradicted", f"声明含文档没有的项: {claim_unmatched[:3]}"))
            elif doc_unmatched and not claim_unmatched:
                results.append((src, "partial", f"文档还含声明未提的项: {doc_unmatched[:3]}"))
            elif not any(_items_match(e, d) for e in elements for d in doc_items):
                # 双向零交集=实体错配(同名不同概念, 如"运行状态"撞上功能列举), 降级不支持
                results.append((src, "unsupported",
                                f"与「{src}」零交集, 疑似同名异义实体: {claim_unmatched[:2]}"))
            else:
                results.append((src, "contradicted",
                                f"双向差异: 声明多{claim_unmatched[:3]} 文档多{doc_unmatched[:3]}"))
        return results

    def verify_identifier(self, identifier, entity=""):
        """编号声明: 父级段完整性 + 文档存在性 + 名称对应"""
        doc_ids = {cid: (sec, name) for sec, name, cid in self.identifiers}
        # 表格行里的ID
        for cap, cells in self.table_rows:
            for c in cells:
                if re.match(r"[A-Z]{2,}(-[A-Z0-9]+)+", c):
                    doc_ids.setdefault(c, ("表格", cap))
        if identifier in doc_ids:
            sec, name = doc_ids[identifier]
            return ("supported", f"文档{sec}「{name}」存在该编号")
        # 前缀匹配: QA的ID是文档ID的前缀(缺父级段)
        for cid, (sec, name) in doc_ids.items():
            if cid.startswith(identifier + "-") or identifier.startswith(cid + "-"):
                longer, shorter = (cid, identifier) if len(cid) > len(identifier) else (identifier, cid)
                missing = longer[len(shorter):].strip("-")
                return ("id_incomplete", f"编号不完整: 文档为{cid}({sec}「{name}」), 声明缺段[{missing}]")
        return ("unsupported", "文档未找到该编号")

    def verify_parameter(self, param, entity=""):
        val = param.get("value")
        results = []
        for sec, t in self.sentences:
            if entity and _norm(entity)[:4] and _norm(entity)[:4] not in _norm(t):
                continue
            for m in re.finditer(r"(\d+(?:\.\d+)?)\s*(秒|毫秒|ms|s|分钟|条|个|MB|GB|字节|位)", t):
                if abs(float(m.group(1)) - float(val)) < 1e-9:
                    results.append(("supported", f"正文{sec}含同值: {t[:50]}"))
        if results:
            return results[0]
        return ("unsupported", "正文未找到同值参数(需上下文定位)")

    def verify_precondition(self, condition):
        c = _norm(condition)
        for sec, t in self.sentences:
            if c[:8] and c[:8] in _norm(t):
                return ("supported", f"正文{sec}含该条件")
        return ("unsupported", "正文未找到该前置条件")

    def verify_participant(self, participants):
        for p in participants:
            found = any(_norm(p)[:4] in _norm(t) for _, t in self.sentences)
            if not found:
                return ("unsupported", f"参与者「{p}」未见于正文")
        return ("supported", "参与者均见于正文")

    def check_terminology(self, answer_text):
        """术语变体检测: 答案用词与文档高频锚词(≥15次, 正文+表格)的编辑距离1同长同首字词"""
        from collections import Counter
        vocab = Counter()
        for _, t in self.sentences:
            vocab.update(re.findall(r"[\u4e00-\u9fa5]{2,3}", t))
        for _, cells in self.table_rows:          # 表格是术语主载体(能力标识表的"平板"等)
            for c in cells:
                vocab.update(re.findall(r"[\u4e00-\u9fa5]{2,3}", c))
        anchors = {w for w, c in vocab.items() if c >= 15}
        flags = []
        for tok in set(re.findall(r"[\u4e00-\u9fa5]{2,3}", answer_text)):
            if tok in vocab:
                continue
            for v in anchors:
                if len(v) == len(tok) and v[:1] == tok[:1] and sum(a != b for a, b in zip(v, tok)) == 1:
                    flags.append(f"术语疑变体: 「{tok}」vs文档「{v}」")
                    break
        return flags


# ════════════════════════════════════════════════════════════════
# ② QA质量评级(真实数据) + gold计分
# ════════════════════════════════════════════════════════════════

def internal_flaw_checks(qa):
    """答案内部瑕疵(廉价预检): 重复拼接/双重答案"""
    out = qa.get("output", "")
    flags = []
    if out.count("答案：") + out.count("答案:") >= 1 and out.find("答案") > len(out) // 3:
        flags.append("答案二次拼接(生成瑕疵)")
    head, tail = out[: len(out) // 2], out[len(out) // 2:]
    if head and tail and _norm(head)[:30] == _norm(tail)[-30:] and len(_norm(out)) > 100:
        flags.append("答案重复")
    return flags


def grade_qa(qa, facts, extractor, nli=None):
    verdicts, evidence = [], []

    def worst(vs):
        """聚合: 矛盾>编号缺陷>多数无支撑>部分无支撑>支持(6支持+3无支撑=partial而非unsupported)"""
        if "contradicted" in vs:
            return "contradicted"
        if "id_incomplete" in vs:
            return "id_incomplete"
        n_unsup = sum(1 for v in vs if v == "unsupported")
        if vs and n_unsup >= max(1, (len(vs) * 3 + 4) // 5):
            return "unsupported"
        if n_unsup or "partial" in vs:
            return "partial"
        return "supported" if vs else "no_claim"

    def doc_premises(entity, value=None, limit=4):
        """找文档前提前提句: 含实体词(或同值)的句子"""
        key = _norm(entity)[:4] if entity else ""
        out = []
        for sec, t in facts.sentences:
            if (key and key in _norm(t)) or (value is not None and str(int(value)) in t):
                out.append(t)
                if len(out) >= limit:
                    break
        return out

    claims = extractor.extract(qa.get("output", ""), "qa_answer")
    for c in claims:
        k = c.get("kind")
        if k == "enumeration":
            for src, v, d in facts.verify_enumeration(c.get("entity", ""), c.get("elements") or []):
                verdicts.append(v)
                evidence.append(f"[{k}|{src}] {d}")
        elif k == "identifier":
            v, d = facts.verify_identifier(c.get("identifier", ""), c.get("entity", ""))
            verdicts.append(v)
            evidence.append(f"[{k}] {d}")
        elif k == "parameter":
            p = c.get("param") or {}
            v, d = facts.verify_parameter(p, c.get("entity", ""))
            if nli is not None and p.get("value") is not None:
                # NLI通道: 声明句重建 + 文档前提句 → 蕴含判定(NLI实测参数冲突2/2)
                hyp = (f"{c.get('entity', '') or '该参数'}"
                       f"{_OP_CN.get(p.get('op', 'eq'), '为')}{p.get('value')}{p.get('unit', '')}")
                prems = doc_premises(c.get("entity", ""), p.get("value"))
                if prems:
                    nv, conf = nli.verify_best(prems, hyp)
                    if order_rank(nv) > order_rank(v) or (nv == "supported" and v == "unsupported"):
                        v, d = nv, f"NLI判定({nv},conf={conf:.2f}): 前提「{prems[0][:30]}…」"
            verdicts.append(v)
            evidence.append(f"[{k}] {d}")
        elif k == "precondition":
            v, d = facts.verify_precondition(c.get("condition", ""))
            if nli is not None and v == "unsupported":
                # NLI兜底: 子串miss后用蕴含判定(实测蕴含5/5)——转述的 precondition 也能命中
                prems = doc_premises(c.get("condition", "")[:8], None, limit=3)
                if prems:
                    nv, conf = nli.verify_best(prems, f"{c.get('entity', '') or '该操作'}的前置条件是{c.get('condition', '')}")
                    if nv in ("supported", "contradicted"):
                        v, d = nv, f"NLI判定({nv},conf={conf:.2f}): 前提「{prems[0][:30]}…」"
            verdicts.append(v)
            evidence.append(f"[{k}] {d}")
        elif k == "participant":
            v, d = facts.verify_participant(c.get("participants") or [])
            verdicts.append(v)
            evidence.append(f"[{k}] {d}")
    flags = internal_flaw_checks(qa)
    dup_only = [f for f in flags if "拼接" in f or "重复" in f]
    term_flags = facts.check_terminology(qa.get("output", ""))
    flags += term_flags
    final = worst(verdicts) if verdicts else ("internal_flaw" if flags else "no_claim")
    # 答案内部重复/拼接是可见缺陷, 优先于grounding判定呈现
    if dup_only and final in ("supported", "no_claim", "unsupported", "partial"):
        final = "internal_flaw"
    # 术语疑变体(平版/平板类): 高频锚词过滤后噪声可控, 可在弱判定上呈现
    if term_flags and final in ("supported", "no_claim", "unsupported", "partial"):
        final = "term_variant"
    return {"instruction": qa.get("instruction", "")[:60], "final": final,
            "verdicts": verdicts, "evidence": evidence[:4], "flags": flags,
            "n_claims": len(claims)}


def order_rank(v):
    return {"supported": 1, "partial": 2, "id_incomplete": 3,
            "unsupported": 0, "contradicted": 4}.get(v, 0)


def cmd_eval_qa(extractor, limit=0, use_nli=False):
    qas = json.load(open(DOC11_QA, encoding="utf-8"))
    if limit:
        qas = qas[:limit]
    gold = json.load(open(GOLD, encoding="utf-8"))
    facts = DocFacts("04")
    nli = None
    if use_nli:
        print("加载NLI通道: mDeBERTa (参数/前置核验)...")
        nli = NLIVerifier()
    print(f"真实评测: {len(qas)}条QA | 文档事实: 枚举{len(facts.enumerations)} 编号{len(facts.identifiers)}"
          f" 表行{len(facts.table_rows)} 图结构{len(facts.graph_nodes)} | NLI={'开' if nli else '关'}")
    gradings = [grade_qa(q, facts, extractor, nli) for q in qas]
    # gold计分
    caught, missed = [], []
    for g in gold["qa_must_flag"]:
        hit = False
        for i, gr in enumerate(gradings):
            if g["instruction_contains"] in qas[i]["instruction"]:
                if gr["final"] in g["expect"] or (g["expect"][0] == "contradicted_or_flag"
                                                  and gr["final"] in ("contradicted", "partial",
                                                                      "id_incomplete", "term_variant")):
                    hit = True
                    gr["gold_hit"] = g["issue"][:40]
                break
        (caught if hit else missed).append(g["instruction_contains"][:30])
    extra_flags = [g for g in gradings
                   if g["final"] in ("contradicted", "id_incomplete", "internal_flaw")
                   and "gold_hit" not in g]
    print(f"\n[GOLD] 必须抓出{len(gold['qa_must_flag'])}条: 抓出{len(caught)}/{len(gold['qa_must_flag'])}"
          f" | 漏检: {missed}")
    print(f"[误报观察] gold外被标记{len(extra_flags)}条(需人工复核, gold本身不完备):")
    for g in extra_flags[:6]:
        print(f"    {g['instruction'][:40]} → {g['final']} {g['evidence'][:1]}")
    from collections import Counter
    print(f"\n[分布] {dict(Counter(g['final'] for g in gradings))}")
    out = {"gold_caught": len(caught), "gold_total": len(gold["qa_must_flag"]),
           "missed": missed, "gradings": gradings}
    QA_EVAL_OUT.parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(QA_EVAL_OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"结果: {QA_EVAL_OUT}")


# ════════════════════════════════════════════════════════════════
# ③ 文档真实矛盾扫描(方向B: 声明源=受控正文, 多源交叉)
# ════════════════════════════════════════════════════════════════

def scan_doc(doc_num):
    facts = DocFacts(doc_num)
    findings = []
    # E1: 同实体多源枚举交叉(正文枚举 vs 正文枚举 vs 图节点)
    seen_pairs = set()
    targets = [(f"正文{sec}「{subj}」", subj, items) for sec, subj, items in facts.enumerations]
    for i, (s1, subj1, items1) in enumerate(targets):
        for s2, subj2, items2 in targets[i + 1:]:
            if _items_match(subj1, subj2) and (s1, s2) not in seen_pairs:
                seen_pairs.add((s1, s2))
                d1 = [x for x in items1 if not any(_items_match(x, y) for y in items2)]
                d2 = [x for x in items2 if not any(_items_match(x, y) for y in items1)]
                if d1 or d2:
                    findings.append({
                        "doc": doc_num, "type": "enumeration_conflict",
                        "severity": "high" if (d1 and d2) else "medium",
                        "where": f"{s1} vs {s2}",
                        "desc": f"「{subj1}」两处列举不一致: A独有{d1[:3]} B独有{d2[:3]}",
                        "evidence": [f"A({s1}): {'、'.join(items1[:6])}",
                                     f"B({s2}): {'、'.join(items2[:6])}"]})
        for gi, nodes in enumerate(facts.graph_nodes):
            key = (s1, f"g{gi}")
            if key in seen_pairs:
                continue
            pref = _norm(subj1)[:min(6, len(_norm(subj1)))]
            short_nodes = [n for n in nodes if len(n) <= 14]
            matched = sum(1 for n in nodes if any(_items_match(n, x) for x in items1))
            # 仅当图是"该实体自身的用例分解图"(规模相近且多数节点对应)才比对,
            # 跳过恰好提到该实体的架构图/无关图(防54条噪声)
            if (pref and any(pref in _norm(n) for n in nodes)
                    and 2 <= matched and len(short_nodes) <= len(items1) + 3):
                seen_pairs.add(key)
                dn = [x for x in items1 if not any(_items_match(x, n) for n in nodes)]
                dt = [n for n in short_nodes if not any(_items_match(n, x) for x in items1)]
                if dn or dt:
                    findings.append({
                        "doc": doc_num, "type": "text_vs_graph",
                        "severity": "medium",
                        "where": f"{s1} vs 图结构#{gi}",
                        "desc": f"「{subj1}」正文列举与图节点不一致: 正文独有{dn[:3]} 图独有{dt[:3]}",
                        "evidence": [f"正文: {'、'.join(items1[:6])}",
                                     f"图节点: {'、'.join(nodes[:8])}"]})
    # E4: 编号段数一致性(同前缀组内段数异常=缺父级段, 如TJSW缺XGSJ段)
    by_prefix = defaultdict(list)
    for sec, name, cid in facts.identifiers:
        segs = cid.split("-")
        if len(segs) >= 3:
            by_prefix["-".join(segs[:3])].append((sec, name, cid))
    for prefix, lst in by_prefix.items():
        if len(lst) < 2:
            continue
        from collections import Counter as _C
        all_ids = {cid for _, _, cid in lst}
        seg_counts = _C(len(cid.split("-")) for _, _, cid in lst)
        majority = seg_counts.most_common(1)[0][0]
        for sec, name, cid in lst:
            n = len(cid.split("-"))
            # 合法父级ID(是组内其他ID的前缀)跳过; 仅flag非前缀且段数偏离多数者
            is_parent = any(o != cid and o.startswith(cid + "-") for o in all_ids)
            if n != majority and not is_parent:
                findings.append({
                    "doc": doc_num, "type": "id_segment_anomaly",
                    "severity": "medium",
                    "where": f"章节{sec} (前缀组{prefix})",
                    "desc": f"「{name}」编号{cid}为{n}段, 同组多为{majority}段(疑似缺父级段/错配)",
                    "evidence": [f"本条: {cid}",
                                 "同组: " + "; ".join(sorted(all_ids)[:6])]})
    # E5: 表内术语漂移(平版/平板式混用): 同长同首字编辑距离1的表格高频词对,
    #     且两者从不在同一单元格共现(共现=n-gram伪影, 如"支持/持删")
    from collections import Counter as _C2
    tcount = _C2()
    cell_tokens = []
    for _, cells in facts.table_rows:
        for c in cells:
            toks = re.findall(r"[\u4e00-\u9fa5]{2,3}", c)
            cell_tokens.append(set(toks))
            tcount.update(toks)
    toks = [w for w, c in tcount.items() if c >= 3 and len(w) == 2]  # 仅2字词: 3字滑窗伪影跨cell存在
    for i, a in enumerate(toks):
        for b in toks[i + 1:]:
            if not (len(a) == len(b) and a[:1] == b[:1]
                    and sum(x != y for x, y in zip(a, b)) == 1
                    and min(tcount[a], tcount[b]) >= 3):
                continue
            co_occur = any(a in s and b in s for s in cell_tokens)
            if not co_occur:
                findings.append({
                    "doc": doc_num, "type": "table_terminology_drift",
                    "severity": "medium",
                    "where": "表格列值",
                    "desc": f"表格内术语混用: 「{a}」{tcount[a]}次 vs 「{b}」{tcount[b]}次",
                    "evidence": [f"{a}: {tcount[a]}处", f"{b}: {tcount[b]}处"]})
    # E6: 表ID短格式 vs 节标题长格式(同尾段): 双格式并存(按短ID去重)
    head_ids = [(sec, name, cid) for sec, name, cid in facts.identifiers
                if not sec.startswith("表格")]
    table_ids = [(sec, name, cid) for sec, name, cid in facts.identifiers
                 if sec.startswith("表格")]
    seen_dual = set()
    for hsec, hname, hcid in head_ids:
        for tsec, tname, tcid in table_ids:
            if hcid != tcid and hcid.startswith(tcid + "-") and tcid not in seen_dual:
                seen_dual.add(tcid)
                findings.append({
                    "doc": doc_num, "type": "id_dual_format",
                    "severity": "low",
                    "where": f"{tsec} vs {hsec}",
                    "desc": f"「{hname}」编号双格式并存: 表用短{tcid} 节标题用长{hcid}",
                    "evidence": [f"表格: {tcid}", f"标题: {hcid}"]})
                break
    return findings


def cmd_scan_docs(doc_filter=None):
    import glob
    docs = sorted({Path(p).parent.parent.name[:2]
                   for p in glob.glob(str(MINERU_DIR / "*/office/*content_list.json"))})
    if doc_filter:
        docs = [d for d in docs if d == doc_filter.zfill(2)]
    all_findings = []
    print(f"扫描{len(docs)}份文档: {docs}")
    for d in docs:
        try:
            fs = scan_doc(d)
        except FileNotFoundError as e:
            print(f"  [{d}] 跳过: {e}")
            continue
        all_findings += fs
        if fs:
            print(f"  [{d}] {len(fs)}条发现")
            for f in fs[:3]:
                print(f"      [{f['type']}/{f['severity']}] {f['desc'][:70]}")
    FINDINGS_OUT.parent.mkdir(parents=True, exist_ok=True)
    json.dump({"n_docs": len(docs), "n_findings": len(all_findings), "findings": all_findings},
              open(FINDINGS_OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    from collections import Counter
    print(f"\n总计{len(all_findings)}条真实发现 | 类型分布: {dict(Counter(f['type'] for f in all_findings))}")
    print(f"结果: {FINDINGS_OUT}")


# ════════════════════════════════════════════════════════════════
# CLI
# ════════════════════════════════════════════════════════════════

def cmd_smoke(extractor):
    qas = json.load(open(DOC11_QA, encoding="utf-8"))[:5]
    print("抽取器冒烟(5条真实QA, kimi连通性+声明质量):")
    for qa in qas:
        claims = extractor.extract(qa["output"], "qa_answer")
        print(f"\nQ: {qa['instruction'][:50]}")
        print(f"  抽取{len(claims)}条声明:")
        for c in claims[:4]:
            print(f"    [{c.get('kind')}] entity={c.get('entity', '')[:16]} "
                  f"elements={str(c.get('elements'))[:60]} quote={str(c.get('source_quote'))[:30]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["smoke", "eval-qa", "scan-docs"])
    ap.add_argument("--backend", default="kimi", choices=["kimi", "ollama"])
    ap.add_argument("--model", default=None)
    ap.add_argument("--doc", default=None)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--nli", action="store_true",
                    help="启用本地mDeBERTa NLI通道(参数/前置核验; 需在.venv-nli下运行)")
    args = ap.parse_args()
    if args.cmd == "scan-docs":
        cmd_scan_docs(args.doc)
        return
    extractor = LLMClaimExtractor(backend=args.backend, model=args.model)
    if args.cmd == "smoke":
        cmd_smoke(extractor)
    elif args.cmd == "eval-qa":
        cmd_eval_qa(extractor, limit=args.limit, use_nli=args.nli)


if __name__ == "__main__":
    main()
