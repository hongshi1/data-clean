#!/usr/bin/env python3
"""
SRS上下文关联+特征提取 (方向A)
================================
不依赖LLM，用embedding+规则实现条目聚合和特征提取。

7个子任务:
  A1: 实体识别 — 从XML提取候选实体(规则)
  A2: ID归一化 — 缩写词展开+embedding相似度
  A3: 章节号容错 — 序列对齐+偏移检测
  A4: 名称匹配 — embedding余弦相似度
  A5: 多信号融合 — 加权评分(≥0.5判定同一实体)
  A6: 特征提取 — 正则+semantic_role规则分类
  A7: 幽灵需求检测 — 引用-定义集合运算

产出: List[Item]，每个Item含occurrences+features

用法: 被srs_detect.py调用
"""
import re
import math
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from dataclasses import dataclass, field
from collections import defaultdict

BASE = Path(__file__).resolve().parent.parent

# Embedding API配置
EMB_URL = "https://wanqing-api.corp.kuaishou.com/api/gateway/v1/endpoints/embeddings"
from ai_config import WQ_API_KEY as EMB_KEY
EMB_MODEL = "ep-qrkeon-1785654358657880827"

# 需求ID正则
REQ_ID_RE = re.compile(r'[A-Z]{4,}-[A-Z]{2,}-[A-Z0-9]+')
# 数值约束正则
CONSTRAINT_RE = re.compile(
    r'(?:不超过|至多|最多|不大于|小于等于|≤|<=)'
    r'\s*(\d+\.?\d*)\s*'
    r'(ms|s|秒|KB|MB|GB|MHz|GHz|%|V|A|W|次|个|层|分钟|小时|天|字节|TB)?'
)
CONSTRAINT_RE_GE = re.compile(
    r'(?:不小于|至少|最少|不低于|大于等于|≥|>=)'
    r'\s*(\d+\.?\d*)\s*'
    r'(ms|s|秒|KB|MB|GB|MHz|GHz|%|V|A|W|次|个|层|分钟|小时|天|字节|TB)?'
)


# ── 数据结构 ──────────────────────────────────────────────────

@dataclass
class ItemOccurrence:
    """条目的一次出现"""
    section: str
    occ_type: str          # text / table_row / qualification_row / traceability_row
    content: str
    line: int = 0
    table_type: str = ""
    cells: list = field(default_factory=list)

@dataclass
class ItemFeature:
    """条目的语义特征"""
    param_name: str
    param_value: float
    param_unit: str
    operator: str          # ≤/≥/=/±/< >
    semantic_role: str     # threshold / config / capacity / description
    original_text: str
    section: str

@dataclass
class Item:
    """上下文关联产出的条目"""
    item_id: str
    item_type: str         # function / parameter / interface / state
    canonical_name: str
    occurrences: list = field(default_factory=list)
    features: list = field(default_factory=list)
    confidence: float = 0.0
    match_signals: dict = field(default_factory=dict)


# ── Embedding工具 ─────────────────────────────────────────────

_emb_cache = {}

def get_embeddings(texts: list[str]) -> list[list[float]]:
    """调用embedding API (带缓存)"""
    uncached = [(i, t) for i, t in enumerate(texts) if t not in _emb_cache]
    if uncached:
        try:
            resp = requests.post(EMB_URL, headers={
                "Authorization": f"Bearer {EMB_KEY}",
                "Content-Type": "application/json"
            }, json={
                "model": EMB_MODEL,
                "input": [t for _, t in uncached],
                "encoding_format": "float"
            }, timeout=30)
            resp.raise_for_status()
            for (idx, text), emb in zip(uncached, resp.json()["data"]):
                _emb_cache[text] = emb["embedding"]
        except Exception as e:
            print(f"  [embedding] API不可用: {e}")
            return [[] for _ in texts]
    return [_emb_cache.get(t, []) for t in texts]


def cosine_similarity(a: list, b: list) -> float:
    """余弦相似度"""
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na > 0 and nb > 0 else 0.0


# ── A1: 实体识别 ──────────────────────────────────────────────

def extract_entities(content: ET.Element) -> list[dict]:
    """从content.xml提取所有候选实体(功能+接口+参数)"""
    entities = []
    
    for section in content.findall('.//Section'):
        sec_id = section.get('section_id', '')
        title = section.get('title', '')
        req_id = section.get('req_id', '')
        
        # 功能实体: 3.2.X章节
        if sec_id.startswith('3.2.') and sec_id.count('.') == 2:
            entities.append({
                "raw_id": req_id or title,
                "name": re.sub(r'[（(].*?[)）]', '', title).strip(),
                "type": "function",
                "section": sec_id,
            })
        
        # 接口实体: 3.3.X/3.4.X章节
        if sec_id.startswith(('3.3.', '3.4.')) and sec_id.count('.') == 2:
            entities.append({
                "raw_id": req_id or title,
                "name": re.sub(r'[（(].*?[)）]', '', title).strip(),
                "type": "interface",
                "section": sec_id,
            })
        
        # 参数实体: 3.10/3.11章节中的参数
        if sec_id.startswith(('3.10', '3.11', '3.9')):
            # 从段落文本中提取参数名
            for para in section.findall('Paragraph'):
                text = para.text or ''
                # 搜索包含数值的段落，提取参数名
                for m in CONSTRAINT_RE.finditer(text):
                    param = _extract_param_name(text, m.start())
                    entities.append({
                        "raw_id": None,
                        "name": param,
                        "type": "parameter",
                        "section": sec_id,
                    })
                    break  # 每段只取第一个参数
                for m in CONSTRAINT_RE_GE.finditer(text):
                    param = _extract_param_name(text, m.start())
                    entities.append({
                        "raw_id": None,
                        "name": param,
                        "type": "parameter",
                        "section": sec_id,
                    })
                    break
    
    return entities


# ── A2: ID归一化 ──────────────────────────────────────────────

def normalize_id(raw_id: str, all_ids: list[str]) -> str:
    """ID归一化: 取前两段作为归一化key"""
    if not raw_id:
        return ""
    parts = raw_id.split('-')
    if len(parts) >= 2:
        return f"{parts[0]}-{parts[1]}"  # PZXQ-GN / PZXQ-WBJK / PZXQ-NBJK
    return raw_id


def build_id_clusters(entities: list[dict]) -> dict[str, str]:
    """
    ID聚类: 完整ID精确匹配(不做前缀聚类)
    ID归一化只处理"完全相同ID"的情况
    不同ID的合并靠名称embedding(A4)而非ID前缀
    """
    ids = list(set(e["raw_id"] for e in entities if e["raw_id"]))
    return {id_: id_ for id_ in ids}


# ── A3: 章节号容错 ────────────────────────────────────────────

def detect_section_offset(ch3_sections: list[str], ch4_sections: list[str]) -> int:
    """检测第4章引用的章节号相对第3章的系统性偏移"""
    if not ch3_sections or not ch4_sections:
        return 0
    
    def adjust(sec: str, offset: int) -> str:
        parts = sec.split('.')
        if len(parts) >= 3:
            try:
                parts[-1] = str(int(parts[-1]) + offset)
                return '.'.join(parts)
            except ValueError:
                pass
        return sec
    
    best_offset, best_rate = 0, 0
    for offset in range(-2, 3):
        matched = sum(1 for s in ch4_sections if adjust(s, offset) in ch3_sections)
        rate = matched / len(ch4_sections)
        if rate > best_rate:
            best_offset, best_rate = offset, rate
    
    return best_offset if best_rate > 0.8 else 0


# ── A4: 名称匹配 ──────────────────────────────────────────────

def compute_name_similarity(name_a: str, name_b: str) -> float:
    """用embedding计算名称相似度"""
    embs = get_embeddings([name_a, name_b])
    if not any(embs):
        # fallback: 字符级Jaccard
        sa, sb = set(name_a), set(name_b)
        return len(sa & sb) / max(1, len(sa | sb))
    return cosine_similarity(embs[0], embs[1])


# ── A5: 多信号融合 ────────────────────────────────────────────

def aggregate_items(entities: list[dict], content: ET.Element) -> list[Item]:
    """多信号融合: 聚合描述同一事物的实体"""
    
    # A2: ID归一化
    id_clusters = build_id_clusters(entities)
    
    # A3: 章节号偏移
    ch4_secs = []
    for table in content.findall('.//Table[@type="qualification"]'):
        for row in table.findall('Row'):
            cells = [c.text or '' for c in row.findall('Cell')]
            for cell in cells:
                m = re.search(r'(3\.2\.\d+)', cell)
                if m:
                    ch4_secs.append(m.group(1))
    
    # 按ID预分组(完整ID)
    groups = defaultdict(list)
    for e in entities:
        cluster = id_clusters.get(e["raw_id"], e["raw_id"] or e["name"])
        groups[cluster].append(e)
    
    # A4: 名称匹配 — 对预分组内的实体用embedding进一步合并
    items = []
    used = set()
    
    all_names = [e["name"] for e in entities]
    name_embs = get_embeddings(all_names) if all_names else []
    
    for i, entity in enumerate(entities):
        if i in used:
            continue
        
        # 创建新条目
        item = Item(
            item_id=entity["raw_id"] or entity["name"],
            item_type=entity["type"],
            canonical_name=entity["name"],
            occurrences=[],
            features=[],
            confidence=1.0,
            match_signals={"init": True},
        )
        
        # 添加自身出现
        item.occurrences.append(ItemOccurrence(
            section=entity["section"], occ_type="text",
            content=entity["name"], line=0
        ))
        used.add(i)
        
        # 搜索其他出现位置
        search_text = entity["name"]
        for section in content.findall('.//Section'):
            sec_id = section.get('section_id', '')
            if sec_id == entity["section"]:
                continue
            for para in section.findall('Paragraph'):
                if search_text and search_text in (para.text or ''):
                    item.occurrences.append(ItemOccurrence(
                        section=sec_id, occ_type="text",
                        content=para.text[:200], line=int(para.get('line', 0))
                    ))
        
        # 搜索合格性表/追溯表中的引用
        for table in content.findall('.//Table'):
            table_type = table.get('type', '')
            for row_idx, row in enumerate(table.findall('Row')):
                cells = [c.text or '' for c in row.findall('Cell')]
                row_text = ' '.join(cells)
                if entity["raw_id"] and entity["raw_id"] in row_text:
                    item.occurrences.append(ItemOccurrence(
                        section=table.get('section', ''),
                        occ_type="table_row",
                        content=row_text[:200],
                        table_type=table_type,
                        cells=cells,
                    ))
        
        # 合并相似实体(A4+A5)
        for j in range(i + 1, len(entities)):
            if j in used:
                continue
            other = entities[j]
            
            # 信号1: ID完全匹配
            id_match = (entity["raw_id"] == other["raw_id"]) and bool(entity["raw_id"])
            
            # 信号2: 名称相似度
            if name_embs and name_embs[i] and name_embs[j]:
                name_sim = cosine_similarity(name_embs[i], name_embs[j])
            else:
                name_sim = 0.0
            
            # 信号3: 同类型
            type_match = entity["type"] == other["type"]
            
            # 多信号融合: 提高名称匹配阈值避免过度合并
            # 0.85: 只有"故障探测预警"="故障预警修复"这种才合并
            # 0.75会合并"服务开发支撑"="服务部署管理"(都是"服务XX"格式)
            strong_signals = sum([id_match, name_sim > 0.85, type_match])
            score = 0
            if id_match:
                score += 0.4
            if name_sim > 0.85:
                score += 0.3
            if type_match:
                score += 0.2
            if entity["section"][:3] == other["section"][:3]:
                score += 0.1
            
            # 合并条件: score>=0.6 且至少2个强信号
            if score >= 0.6 and strong_signals >= 2:
                # 合并
                item.occurrences.append(ItemOccurrence(
                    section=other["section"], occ_type="text",
                    content=other["name"]
                ))
                used.add(j)
                item.match_signals[f"merge_{j}"] = {
                    "id_match": id_match, "name_sim": round(name_sim, 3),
                    "type_match": type_match, "score": round(score, 3)
                }
        
        items.append(item)
    
    return items


# ── A6: 特征提取 ──────────────────────────────────────────────

def extract_features(items: list[Item], content: ET.Element) -> list[Item]:
    """从条目关联的章节文本中提取语义特征"""
    
    for item in items:
        # 收集该条目涉及的所有章节文本(含表格cells)
        section_texts = {}
        for occ in item.occurrences:
            if occ.section not in section_texts:
                section = content.find(f'.//Section[@section_id="{occ.section}"]')
                if section is not None:
                    # 段落文本
                    text = '\n'.join(p.text or '' for p in section.findall('Paragraph'))
                    # 表格cells文本
                    for table in section.findall('Table'):
                        for row in table.findall('Row'):
                            cells = [c.text or '' for c in row.findall('Cell')]
                            text += '\n' + ' '.join(cells)
                    section_texts[occ.section] = text
        
        # 也从全局Table提取(不在章节内的表格)
        for table in content.findall('Table'):
            table_type = table.get('type', '')
            if table_type in ('qualification', 'traceability'):
                for row in table.findall('Row'):
                    cells = [c.text or '' for c in row.findall('Cell')]
                    row_text = ' '.join(cells)
                    # 表格中的约束也提取
                    for m in CONSTRAINT_RE.finditer(row_text):
                        value = float(m.group(1))
                        unit = m.group(2) or ""
                        param = _extract_param_name(row_text, m.start())
                        role = _classify_role(param, table_type)
                        existing = any(f.param_name == param and f.param_value == value 
                                      and f.section == table_type for f in item.features)
                        if not existing:
                            item.features.append(ItemFeature(
                                param_name=param, param_value=value, param_unit=unit,
                                operator="≤", semantic_role=role,
                                original_text=row_text[:100],
                                section=table_type,
                            ))
        
        # 也从条目自身章节提取
        for occ in item.occurrences:
            if occ.content and occ.occ_type == "text":
                section_texts.setdefault(occ.section, '')
                section_texts[occ.section] += '\n' + occ.content
        
        # 从所有相关章节文本中提取约束
        for sec_id, text in section_texts.items():
            if not text:
                continue
            for m in CONSTRAINT_RE.finditer(text):
                value = float(m.group(1))
                unit = m.group(2) or ""
                param = _extract_param_name(text, m.start())
                role = _classify_role(param, sec_id)
                # 去重: 同一参数+同一值+同一章节不重复
                existing = any(f.param_name == param and f.param_value == value 
                              and f.section == sec_id for f in item.features)
                if not existing:
                    item.features.append(ItemFeature(
                        param_name=param, param_value=value, param_unit=unit,
                        operator="≤", semantic_role=role,
                        original_text=text[max(0,m.start()-20):m.end()+20],
                        section=sec_id,
                    ))
            
            for m in CONSTRAINT_RE_GE.finditer(text):
                value = float(m.group(1))
                unit = m.group(2) or ""
                param = _extract_param_name(text, m.start())
                role = _classify_role(param, sec_id)
                existing = any(f.param_name == param and f.param_value == value 
                              and f.section == sec_id for f in item.features)
                if not existing:
                    item.features.append(ItemFeature(
                        param_name=param, param_value=value, param_unit=unit,
                        operator="≥", semantic_role=role,
                        original_text=text[max(0,m.start()-20):m.end()+20],
                        section=sec_id,
                    ))
    
    return items


def _extract_param_name(text: str, constraint_pos: int) -> str:
    """从约束前的文本提取参数名"""
    before = text[max(0, constraint_pos - 15):constraint_pos]
    # 取最后的中文词
    m = re.search(r'([\u4e00-\u9fa5]{2,8})$', before)
    return m.group(1) if m else before[-8:].strip()


def _classify_role(param: str, section: str) -> str:
    """semantic_role分类(规则,不用LLM)"""
    # threshold: 阈值约束(必须一致)
    threshold_keywords = ['时间', '间隔', '延迟', '误差', '精度', '响应', '定时', '偏差', '周期']
    # config: 配置参数(可以不同)
    config_keywords = ['版本', '型号', '主频', '内存', '硬盘', '存储', '分辨率', '显存', '架构']
    # capacity: 能力上限(可以不同)
    capacity_keywords = ['最多', '支持', '容量', '数量', '上限', '最大', '并发']
    
    for kw in threshold_keywords:
        if kw in param:
            return "threshold"
    for kw in config_keywords:
        if kw in param:
            return "config"
    for kw in capacity_keywords:
        if kw in param:
            return "capacity"
    
    # 按章节判断
    if section.startswith('3.10'):
        return "config"  # 资源配置
    if section.startswith('3.11'):
        return "threshold"  # 质量因素(阈值)
    if section.startswith('3.2'):
        return "threshold"  # 能力需求(阈值)
    
    return "description"


# ── A7: 幽灵需求检测 ──────────────────────────────────────────

def detect_phantoms(items: list[Item], content: ET.Element) -> list[str]:
    """检测被引用但未定义的需求"""
    defined = {item.occurrences[0].section for item in items
               if item.item_type == "function" and item.occurrences}
    
    referenced = set()
    for table in content.findall('.//Table[@type="qualification"]'):
        for row in table.findall('Row'):
            cells = [c.text or '' for c in row.findall('Cell')]
            for cell in cells:
                m = re.search(r'(3\.2\.\d+)', cell)
                if m:
                    referenced.add(m.group(1))
    
    for table in content.findall('.//Table[@type="traceability"]'):
        for row in table.findall('Row'):
            cells = [c.text or '' for c in row.findall('Cell')]
            for cell in cells:
                m = re.search(r'(3\.2\.\d+)', cell)
                if m:
                    referenced.add(m.group(1))
    
    return sorted(referenced - defined)


# ── 主入口 ────────────────────────────────────────────────────

def run_context_aggregation(content_xml_path: str) -> tuple[list[Item], list[str]]:
    """
    方向A完整流程: 实体识别→ID归一化→章节容错→名称匹配→多信号融合→特征提取→幽灵需求
    
    返回: (items, phantoms)
    """
    content = ET.parse(content_xml_path).getroot()
    
    # A1
    entities = extract_entities(content)
    print(f"  A1 实体识别: {len(entities)}个候选实体")
    
    if not entities:
        return [], []
    
    # A2-A5: 聚合
    items = aggregate_items(entities, content)
    print(f"  A2-A5 多信号融合: {len(items)}个聚合条目")
    
    # A6: 特征提取(含全局参数提取)
    items = extract_features(items, content)
    
    # 从3.9/3.10/3.11章节全局提取参数特征
    for section in content.findall('.//Section'):
        sec_id = section.get('section_id', '')
        if not sec_id.startswith(('3.9', '3.10', '3.11')):
            continue
        text = '\n'.join(p.text or '' for p in section.findall('Paragraph'))
        for table in section.findall('Table'):
            for row in table.findall('Row'):
                cells = [c.text or '' for c in row.findall('Cell')]
                text += '\n' + ' '.join(cells)
        if not text:
            continue
        for m in CONSTRAINT_RE.finditer(text):
            value = float(m.group(1))
            unit = m.group(2) or ""
            param = _extract_param_name(text, m.start())
            role = _classify_role(param, sec_id)
            found = False
            for item in items:
                if any(f.param_name == param and f.param_value == value and f.section == sec_id 
                       for f in item.features):
                    found = True
                    break
            if not found:
                items.append(Item(
                    item_id=f"PARAM-{param}-{sec_id}",
                    item_type="parameter",
                    canonical_name=param,
                    occurrences=[ItemOccurrence(section=sec_id, occ_type="text", content=text[:100])],
                    features=[ItemFeature(param_name=param, param_value=value, param_unit=unit,
                                          operator="≤", semantic_role=role,
                                          original_text=text[max(0,m.start()-20):m.end()+20],
                                          section=sec_id)],
                ))
    
    total_features = sum(len(item.features) for item in items)
    print(f"  A6 特征提取: {total_features}个语义特征")
    
    # A7: 幽灵需求
    phantoms = detect_phantoms(items, content)
    if phantoms:
        print(f"  A7 幽灵需求: {len(phantoms)}个({', '.join(phantoms[:3])})")
    
    return items, phantoms


if __name__ == "__main__":
    # 自测
    outline_dir = BASE / "data/srs_outline"
    test_files = sorted(outline_dir.glob("*_content.xml"))
    if test_files:
        items, phantoms = run_context_aggregation(str(test_files[1]))
        print("\n=== 条目列表 ===")
        for item in items[:5]:
            print(f"  [{item.item_type}] {item.canonical_name[:25]:25s} "
                  f"出现{len(item.occurrences)}次 特征{len(item.features)}个")
            for f in item.features[:2]:
                print(f"    {f.param_name} {f.operator} {f.param_value} {f.param_unit} [{f.semantic_role}]")
