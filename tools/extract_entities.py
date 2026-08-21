#!/usr/bin/env python3
"""检测对象提取

从Pair Dataset + VLM提取 + chunks中提取5类检测对象:
  1. 功能名+ID (术语层8项)
  2. 接口属性 (PARAM-003)
  3. 数值参数 (参数层10项)
  4. 流程步骤 (逻辑层6项)
  5. 表头字段 (GJB合规层)

输出: data/gjb_438c/data_assets/eval_entities.json
"""
import csv
import json
import os
import re
from pathlib import Path
from collections import defaultdict

BASE = Path(__file__).resolve().parent.parent
PAIR_DIR = BASE / "data/gjb_438c/pair_dataset"
VLM_USECASE = BASE / "data/gjb_438c/data_assets/vlm_usecase_extract.jsonl"
VLM_FLOWCHART = BASE / "data/gjb_438c/data_assets/vlm_flowchart_extract.jsonl"
CHUNKS_PATH = BASE / "data/gjb_438c/data_assets/chunks/srs_chunks.json"
SRS_KB = BASE / "knowledge/srs_kb.json"
OUT_PATH = BASE / "data/gjb_438c/data_assets/eval_entities.json"

# 数值正则
NUM_RE = re.compile(r'(\d+\.?\d*)\s*(GB|MB|KB|TB|GHz|MHz|kHz|ms|秒|分钟|小时|天|%|次|个|条|路|Mbps|Gbps|Kbps)')
ID_RE = re.compile(r'[A-Z]{2,8}(?:-[A-Z0-9]+){2,}')

# 字符映射表（T1错字注入用）
CHAR_MAP = {
    '数': '发', '据': '局', '获': '或', '取': '趣', '服': '付', '务': '雾',
    '界': '介', '面': '免', '开': '闩', '发': '友', '集': '及', '成': '城',
    '框': '狂', '架': '加', '转': '传', '换': '涣', '接': '按', '口': '叩',
    '管': '官', '理': '李', '控': '空', '制': '致', '监': '简', '测': '侧',
    '配': '陪', '置': '直', '注': '驻', '册': '测', '登': '灯', '录': '录',
    '启': '起', '停': '亭', '运': '云', '行': '形', '状': '妆', '态': '太',
    '异': '易', '常': '长', '告': '高', '警': '井', '信': '新', '号': '耗',
    '模': '摸', '式': '饰', '切': '窃', '换': '涣', '优': '忧', '先': '仙',
    '级': '极', '权': '全', '限': '线', '访': '防', '问': '闻',
}


def load_pairs():
    """加载所有Pair Dataset"""
    pairs = []
    for sc_dir in sorted(PAIR_DIR.iterdir()):
        if not sc_dir.is_dir():
            continue
        for pair_dir in sorted(sc_dir.iterdir()):
            if not pair_dir.is_dir():
                continue
            meta_path = pair_dir / "meta.json"
            if not meta_path.exists():
                continue
            meta = json.loads(meta_path.read_text())
            meta["_dir"] = str(pair_dir)
            pairs.append(meta)
    return pairs


def load_vlm_usecase():
    """加载用例图VLM提取"""
    results = []
    if VLM_USECASE.exists():
        with open(VLM_USECASE) as f:
            for line in f:
                results.append(json.loads(line))
    return results


def load_vlm_flowchart():
    """加载流程图VLM提取"""
    results = []
    if VLM_FLOWCHART.exists():
        with open(VLM_FLOWCHART) as f:
            for line in f:
                results.append(json.loads(line))
    return results


def load_chunks():
    """加载切片"""
    if CHUNKS_PATH.exists():
        return json.loads(CHUNKS_PATH.read_text())
    return []


def load_srs_kb():
    """加载专家词典"""
    if SRS_KB.exists():
        return json.loads(SRS_KB.read_text())
    return {}


def extract_function_entities(pairs, vlm_usecase):
    """提取功能名+ID实体（术语层8项的检测对象）"""
    entities = {}
    
    for pair in pairs:
        pair_id = pair.get("instance_id", "")
        doc = pair.get("doc", "")
        section = pair.get("section", "")
        func_names = pair.get("func_names", [])
        
        # 从table.csv提取功能名+ID
        table_path = Path(pair["_dir"]) / "table.csv"
        if table_path.exists():
            try:
                rows = list(csv.reader(open(table_path, encoding='utf-8')))
                for row in rows:
                    if len(row) >= 2:
                        # 找ID列
                        for cell in row:
                            if ID_RE.search(cell):
                                eid = ID_RE.search(cell).group()
                                # 找名称列（非ID、非数字的中文列）
                                for c in row:
                                    if c != cell and len(c) >= 2 and not c.isdigit():
                                        if eid not in entities:
                                            entities[eid] = {
                                                "entity_id": eid,
                                                "entity_type": "function_name",
                                                "canonical_name": c.strip(),
                                                "occurrences": []
                                            }
                                        entities[eid]["occurrences"].append({
                                            "location": "table",
                                            "section": section,
                                            "content": c.strip(),
                                            "pair_id": pair_id,
                                            "doc": doc
                                        })
                                        break
                                break
            except Exception:
                pass
        
        # 从func_names提取
        for fn in func_names:
            if len(fn) >= 2 and fn not in ("概述", "前置条件", "主事件流", "异常流", "后置条件"):
                # 用func_name作为key（没有ID时）
                key = f"FN-{fn}"
                if key not in entities:
                    entities[key] = {
                        "entity_id": key,
                        "entity_type": "function_name",
                        "canonical_name": fn,
                        "occurrences": []
                    }
                entities[key]["occurrences"].append({
                    "location": "meta",
                    "section": section,
                    "content": fn,
                    "pair_id": pair_id,
                    "doc": doc
                })
        
        # 从text.txt提取功能名
        text_path = Path(pair["_dir"]) / "text.txt"
        if text_path.exists():
            text = text_path.read_text(encoding='utf-8')
            # 匹配标题中的功能名
            for m in re.finditer(r'(?:创建|实现|完成|提供|支持|进行)([\u4e00-\u9fa5]{2,10})', text):
                fn = m.group(1)
                if fn not in ("功能", "操作", "处理", "管理", "控制", "服务"):
                    key = f"FN-{fn}"
                    if key not in entities:
                        entities[key] = {
                            "entity_id": key,
                            "entity_type": "function_name",
                            "canonical_name": fn,
                            "occurrences": []
                        }
                    entities[key]["occurrences"].append({
                        "location": "text",
                        "section": section,
                        "content": fn,
                        "pair_id": pair_id,
                        "doc": doc
                    })
    
    # 从VLM用例图提取
    for vlm in vlm_usecase:
        doc = vlm.get("doc", "")
        section = vlm.get("section", "")
        for uc in vlm.get("usecases", []):
            if len(uc) >= 2:
                key = f"FN-{uc}"
                if key not in entities:
                    entities[key] = {
                        "entity_id": key,
                        "entity_type": "function_name",
                        "canonical_name": uc,
                        "occurrences": []
                    }
                entities[key]["occurrences"].append({
                    "location": "image",
                    "section": section,
                    "content": uc,
                    "doc": doc
                })
    
    # 只保留有≥2个occurrence的实体
    return [e for e in entities.values() if len(e["occurrences"]) >= 2]


def extract_interface_entities(pairs):
    """提取接口属性实体（跨全部pair，不只sc3，按接口名聚合跨位置出现）"""
    entities = {}
    
    for pair in pairs:
        pair_id = pair.get("instance_id", "")
        doc = pair.get("doc", "")
        section = pair.get("section", "")
        
        table_path = Path(pair["_dir"]) / "table.csv"
        if not table_path.exists():
            continue
        
        try:
            rows = list(csv.reader(open(table_path, encoding='utf-8')))
            if len(rows) < 2:
                continue
            
            header = rows[0]
            # 找接口名/发送方/接收方/类型列
            name_idx = sender_idx = receiver_idx = type_idx = -1
            for i, h in enumerate(header):
                h_lower = h.lower()
                if ("名称" in h or "接口" in h) and name_idx == -1:
                    name_idx = i
                if "发送" in h or "源" in h:
                    sender_idx = i
                if "接收" in h or "目的" in h:
                    receiver_idx = i
                if "类型" in h:
                    type_idx = i
            
            # 只有找到至少名称列和另一个属性列才算接口表
            if name_idx == -1 or (sender_idx == -1 and receiver_idx == -1 and type_idx == -1):
                continue
            
            for row in rows[1:]:
                if not row or all(not c.strip() for c in row):
                    continue
                name = row[name_idx].strip() if name_idx < len(row) else ""
                if not name or len(name) < 2:
                    continue
                
                key = f"IF-{name}"
                if key not in entities:
                    entities[key] = {
                        "entity_id": key,
                        "entity_type": "interface",
                        "canonical_name": name,
                        "occurrences": []
                    }
                entities[key]["occurrences"].append({
                    "location": "table",
                    "section": section,
                    "content": {
                        "name": name,
                        "sender": row[sender_idx].strip() if sender_idx >= 0 and sender_idx < len(row) else "",
                        "receiver": row[receiver_idx].strip() if receiver_idx >= 0 and receiver_idx < len(row) else "",
                        "type": row[type_idx].strip() if type_idx >= 0 and type_idx < len(row) else "",
                    },
                    "pair_id": pair_id,
                    "doc": doc
                })
        except Exception:
            pass
    
    # 只保留有≥2个occurrence的实体（跨位置校验需要）
    return [e for e in entities.values() if len(e["occurrences"]) >= 2]


def extract_param_entities(pairs, chunks, srs_kb):
    """提取数值参数实体（从Pair Dataset + 5231条chunks按10种参数类型提取）"""
    entities = {}
    
    # 10种参数类型的正则模式（放宽匹配+增加关键词）
    PARAM_TYPES = {
        "time": {
            "regex": r'(\d+\.?\d*)\s*(ms|毫秒|秒|s|min|分钟)(?:以内|以内|之内|之内|以下|以下|不超过|不超过)',
            "fallback": r'(?:响应|执行|处理|完成|启动|关闭|延迟|时延|耗时|时间)[^。\n]{0,30}?(\d+\.?\d*)\s*(ms|毫秒|秒|s|min|分钟)'
        },
        "period": {
            "regex": r'(?:周期|间隔|频率|定时|定期|刷新|轮询|采样)[^。\n]{0,30}?(\d+\.?\d*)\s*(ms|毫秒|秒|s|Hz|kHz|分钟)',
            "fallback": r'(\d+\.?\d*)\s*(ms|毫秒|秒|s|Hz|kHz)(?:.*?)(?:周期|间隔|频率|定时)'
        },
        "threshold": {
            "regex": r'(?:阈值|门限|触发|告警|报警|上限|下限|临界)[^。\n]{0,30}?(\d+\.?\d*)\s*(%|ms|秒|次)',
            "fallback": r'(\d+\.?\d*)\s*%(?:.*?)(?:阈值|门限|告警|报警|触发)'
        },
        "align": {
            "regex": r'(?:对齐|同步|校准|一致|偏差|时钟|授时|守时)[^。\n]{0,30}?(\d+\.?\d*)\s*(ms|us|μs|毫秒|微秒|ns|纳秒)',
            "fallback": r'(?:时间同步|时钟同步|时间对齐|时间偏差)[^。\n]{0,30}?(\d+\.?\d*)\s*(ms|us|μs|ns|纳秒|毫秒|微秒)'
        },
        "resource": {
            "regex": r'(?:CPU|内存|存储|磁盘|带宽|资源|占用|空间|容量)[^。\n]{0,30}?(\d+\.?\d*)\s*(GB|MB|KB|TB|GHz|MHz|%|Mbps|Gbps|核|个)',
            "fallback": r'(\d+\.?\d*)\s*(GB|MB|TB|GHz|MHz)(?:.*?)(?:内存|存储|磁盘|CPU|带宽|容量|空间|资源)'
        },
        "range": {
            "regex": r'(?:值域|范围|取值|不小于|不大于|不超过|不低于|不高于|最少|最多|至少|至多)[^。\n]{0,30}?(\d+\.?\d*)\s*(GB|MB|%|个|条|路|帧|M|K)',
            "fallback": r'(\d+\.?\d*)\s*(?:[-~～])(\d+\.?\d*)\s*(GB|MB|%|个|条|路)'
        },
        "storage": {
            "regex": r'(?:保存|存储|保留|保留期|存档|归档|历史|日志)[^。\n]{0,30}?(\d+\.?\d*)\s*(天|月|年|GB|TB|MB|小时)',
            "fallback": r'(\d+\.?\d*)\s*(天|月|年)(?:.*?)(?:保存|存储|保留|存档|归档)'
        },
        "precision": {
            "regex": r'(?:精度|误差|偏差|准确|误差范围|精度要求)[^。\n]{0,30}?(\d+\.?\d*)\s*(ms|us|μs|%|毫秒|微秒|ns|纳秒|ppm)',
            "fallback": r'(?:±|±|误差|偏差|精度)[^。\n]{0,10}?(\d+\.?\d*)\s*(ms|us|μs|%|毫秒|微秒|ns|ppm)'
        },
        "degrade": {
            "regex": r'(?:降级|退化|最低|最低功能|最低性能|降级运行|降级模式|最小|最小化)[^。\n]{0,30}?(\d+\.?\d*)\s*(%|ms|秒|个|路)',
            "fallback": r'(?:性能|功能|能力)[^。\n]{0,30}?(?:降级|退化|最低|最小)[^。\n]{0,30}?(\d+\.?\d*)\s*(%|ms|秒)'
        },
        "fault": {
            "regex": r'(?:故障|失效|超时|异常|断线|中断|恢复|重启|重试)[^。\n]{0,30}?(\d+\.?\d*)\s*(s|ms|秒|次|min|分钟|小时)',
            "fallback": r'(\d+\.?\d*)\s*(s|ms|秒|次)(?:.*?)(?:故障|失效|超时|异常|恢复|重启|重试)'
        },
    }
    
    # 通用数值正则（用于Pair Dataset）
    NUM_RE = re.compile(r'(\d+\.?\d*)\s*(GB|MB|KB|TB|GHz|MHz|kHz|ms|秒|分钟|小时|天|%|次|个|条|路|Mbps|Gbps|Kbps)')
    
    # 从chunks提取（主要来源）
    for chunk in chunks:
        text = chunk.get("text", "")
        if not text or len(text) < 5:
            continue
        doc = chunk.get("doc", "")
        section = chunk.get("section", "")
        chunk_type = chunk.get("type", "text")
        
        for ptype, pinfo in PARAM_TYPES.items():
            # 主正则匹配
            patterns = [pinfo.get("regex", ""), pinfo.get("fallback", "")]
            for pat_str in patterns:
                if not pat_str:
                    continue
                pattern = re.compile(pat_str)
                for m in pattern.finditer(text):
                    val = m.group(1)
                    unit = m.group(2) if m.lastindex and m.lastindex >= 2 else ""
                    
                    # 识别操作符
                    start = max(0, m.start() - 20)
                    context = text[start:m.start()]
                    op = "eq"
                    if "不小于" in context or "至少" in context or "≥" in context or "不低于" in context:
                        op = "ge"
                    elif "不大于" in context or "至多" in context or "≤" in context or "不超过" in context:
                        op = "le"
                    elif "大于" in context or "超过" in context or ">" in context:
                        op = "gt"
                    elif "小于" in context or "低于" in context or "<" in context:
                        op = "lt"
                    
                    key = f"PARAM-{ptype}"
                    if key not in entities:
                        entities[key] = {
                            "entity_id": key,
                            "entity_type": "numeric_param",
                            "param_name": ptype,
                            "param_type": ptype,
                            "unit": unit,
                            "occurrences": []
                        }
                    entities[key]["occurrences"].append({
                        "location": chunk_type,
                        "section": section,
                        "content": val,
                        "op": op,
                        "unit": unit,
                        "context": text[max(0, m.start()-10):m.end()+10],
                        "doc": doc
                    })
    
    # 也从Pair Dataset的text.txt和table.csv补充提取
    for pair in pairs:
        pair_id = pair.get("instance_id", "")
        doc = pair.get("doc", "")
        section = pair.get("section", "")
        
        text_path = Path(pair["_dir"]) / "text.txt"
        if text_path.exists():
            text = text_path.read_text(encoding='utf-8')
            for ptype, pinfo in PARAM_TYPES.items():
                patterns = [pinfo.get("regex", ""), pinfo.get("fallback", "")]
                for pat_str in patterns:
                    if not pat_str:
                        continue
                    pattern = re.compile(pat_str)
                    for m in pattern.finditer(text):
                        val = m.group(1)
                        unit = m.group(2) if m.lastindex and m.lastindex >= 2 else ""
                        start = max(0, m.start() - 20)
                        context = text[start:m.start()]
                        op = "eq"
                        if "不小于" in context or "至少" in context or "≥" in context:
                            op = "ge"
                        elif "不大于" in context or "至多" in context or "≤" in context:
                            op = "le"
                        elif "大于" in context or "超过" in context:
                            op = "gt"
                        elif "小于" in context or "低于" in context:
                            op = "lt"
                        
                        key = f"PARAM-{ptype}"
                        if key not in entities:
                            entities[key] = {
                                "entity_id": key,
                                "entity_type": "numeric_param",
                                "param_name": ptype,
                                "param_type": ptype,
                                "unit": unit,
                                "occurrences": []
                            }
                        entities[key]["occurrences"].append({
                            "location": "text",
                            "section": section,
                            "content": val,
                            "op": op,
                        "unit": unit,
                        "pair_id": pair_id,
                        "doc": doc
                    })
    
    # 只保留有≥2个occurrence的实体
    return [e for e in entities.values() if len(e["occurrences"]) >= 2]


def extract_flow_entities(pairs, vlm_flowchart):
    """提取流程步骤实体（逻辑层6项的检测对象）"""
    entities = {}
    
    # 从VLM流程图提取
    for vlm in vlm_flowchart:
        doc = vlm.get("doc", "")
        section = vlm.get("section", "")
        caption = vlm.get("caption", "")
        nodes = vlm.get("nodes", [])
        
        if len(nodes) >= 2:
            key = f"FLOW-{doc}-{section}"
            if key not in entities:
                entities[key] = {
                    "entity_id": key,
                    "entity_type": "flow_sequence",
                    "canonical_name": caption,
                    "occurrences": []
                }
            entities[key]["occurrences"].append({
                "location": "image",
                "section": section,
                "content": nodes,
                "edges": vlm.get("edges", []),
                "branches": vlm.get("branches", []),
                "data_flow_direction": vlm.get("data_flow_direction", ""),
                "doc": doc
            })
    
    # 从Pair Dataset的text.txt提取步骤序列
    for pair in pairs:
        scenario = pair.get("scenario", "")
        if scenario not in ("2", "4"):  # sc2=sc4=flowchart
            continue
        
        pair_id = pair.get("instance_id", "")
        doc = pair.get("doc", "")
        section = pair.get("section", "")
        
        text_path = Path(pair["_dir"]) / "text.txt"
        if text_path.exists():
            text = text_path.read_text(encoding='utf-8')
            # 匹配步骤序列
            steps = []
            for m in re.finditer(r'(?:步骤|第|首先|然后|接着|最后|Step)\s*[\d一二三四五六七八九十]?[:：.\s]*([\u4e00-\u9fa5]{2,15})', text):
                steps.append(m.group(1))
            
            if len(steps) >= 2:
                key = f"FLOW-{doc}-{section}"
                if key not in entities:
                    entities[key] = {
                        "entity_id": key,
                        "entity_type": "flow_sequence",
                        "canonical_name": f"流程-{section}",
                        "occurrences": []
                    }
                entities[key]["occurrences"].append({
                    "location": "text",
                    "section": section,
                    "content": steps,
                    "pair_id": pair_id,
                    "doc": doc
                })
    
    return list(entities.values())


def extract_header_entities(pairs):
    """提取表头字段实体（GJB合规层的检测对象）"""
    entities = {}
    
    for pair in pairs:
        pair_id = pair.get("instance_id", "")
        doc = pair.get("doc", "")
        section = pair.get("section", "")
        table_caption = pair.get("table_caption", "")
        
        table_path = Path(pair["_dir"]) / "table.csv"
        if not table_path.exists():
            continue
        
        try:
            rows = list(csv.reader(open(table_path, encoding='utf-8')))
            if not rows:
                continue
            
            header = [h.strip() for h in rows[0] if h.strip()]
            if len(header) < 2:
                continue
            
            # 判断表格类型
            table_type = "unknown"
            if "能力" in table_caption or "功能" in table_caption:
                table_type = "能力标识表"
            elif "接口" in table_caption:
                table_type = "接口需求表"
            elif "追溯" in table_caption:
                table_type = "追溯表"
            elif "合格" in table_caption:
                table_type = "合格性表"
            
            key = f"HEADER-{table_type}-{doc}"
            if key not in entities:
                entities[key] = {
                    "entity_id": key,
                    "entity_type": "table_header",
                    "table_type": table_type,
                    "canonical_name": table_caption,
                    "occurrences": []
                }
            entities[key]["occurrences"].append({
                "location": "table",
                "section": section,
                "content": header,
                "pair_id": pair_id,
                "doc": doc
            })
        except Exception:
            pass
    
    return list(entities.values())


def main():
    print("加载数据...")
    pairs = load_pairs()
    vlm_usecase = load_vlm_usecase()
    vlm_flowchart = load_vlm_flowchart()
    chunks = load_chunks()
    srs_kb = load_srs_kb()
    
    print(f"  pairs: {len(pairs)}")
    print(f"  vlm_usecase: {len(vlm_usecase)}")
    print(f"  vlm_flowchart: {len(vlm_flowchart)}")
    print(f"  chunks: {len(chunks)}")
    
    print("\n提取检测对象...")
    
    func_entities = extract_function_entities(pairs, vlm_usecase)
    print(f"  功能名+ID: {len(func_entities)}")
    
    iface_entities = extract_interface_entities(pairs)
    print(f"  接口属性: {len(iface_entities)}")
    
    param_entities = extract_param_entities(pairs, chunks, srs_kb)
    print(f"  数值参数: {len(param_entities)}")
    
    flow_entities = extract_flow_entities(pairs, vlm_flowchart)
    print(f"  流程步骤: {len(flow_entities)}")
    
    header_entities = extract_header_entities(pairs)
    print(f"  表头字段: {len(header_entities)}")
    
    all_entities = func_entities + iface_entities + param_entities + flow_entities + header_entities
    print(f"\n总计: {len(all_entities)} 个检测对象")
    
    # 按类型统计
    type_counts = defaultdict(int)
    for e in all_entities:
        type_counts[e["entity_type"]] += 1
    print("按类型:")
    for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {t}: {c}")
    
    # 保存
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump({
            "total": len(all_entities),
            "by_type": dict(type_counts),
            "entities": all_entities
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n保存到 {OUT_PATH}")


if __name__ == "__main__":
    main()
