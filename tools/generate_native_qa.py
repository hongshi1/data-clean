#!/usr/bin/env python3
"""
原生QA对生成 — 从16份GJB SRS的语义模态数据生成

原则:
1. 只从strong匹配实例生成(图+表+正文确实关联)
2. 每个实例生成1正1负(正例=正确回答, 负例=注入1个不一致)
3. 负例注入类型按场景区分:
   - 场景1/4/5(capability表): 功能名不一致
   - 场景2/7(usecase表): 异常流/步骤不一致
   - 场景3(interface表): 接口类型/发送方/优先级不一致
4. 每条QA对含完整evidence(召回章节+文档原始值)
"""
import json
import re
from pathlib import Path
from html.parser import HTMLParser

BASE = Path(__file__).resolve().parent.parent
CORRECT_DIR = BASE / "data/gjb_438c/mineru_correct"
MODALITY_PATH = BASE / "data/gjb_438c/data_assets/semantic_modality_data.json"
OUTPUT_PATH = BASE / "data/gjb_438c/data_assets/native_qa_pairs.json"

REQ_ID_RE = re.compile(r'[A-Z]{4,}-[A-Z]{2,}-[A-Z0-9-]+')


class TP(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.cur_row = []
        self.cur_cell = []
        self.in_cell = False
    def handle_starttag(self, tag, attrs):
        if tag == 'tr': self.cur_row = []
        elif tag in ('td', 'th'): self.in_cell = True; self.cur_cell = []
    def handle_data(self, data):
        if self.in_cell: self.cur_cell.append(data.strip())
    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.in_cell:
            self.cur_row.append(' '.join(self.cur_cell))
            self.in_cell = False
        elif tag == 'tr' and self.cur_row:
            self.rows.append(self.cur_row)

def parse_table(html):
    p = TP(); p.feed(html); return p.rows


def get_table_rows_from_content_list(doc_name, section, table_caption):
    """从content_list.json获取表格的完整行数据
    优先用caption匹配(caption更可靠), section作为辅助
    """
    cl_path = CORRECT_DIR / doc_name / "final" / "content_list.json"
    if not cl_path.exists():
        return None
    cl = json.loads(cl_path.read_text())
    current_section = ""
    section_candidates = []
    caption_matches = []
    for item in cl:
        if not isinstance(item, dict): continue
        if item.get('type') == 'text' and item.get('text_level', 0) > 0:
            m = re.match(r'^(\d+(?:\.\d+)*)\s+', item.get('text', '').strip())
            if m: current_section = m.group(1)
            continue
        if item.get('type') != 'table': continue
        body = item.get('table_body', '')
        if len(body) < 50: continue
        cap = ' '.join(item.get('table_caption', []))
        # 记录所有匹配的候选
        if current_section == section:
            section_candidates.append((cap, body))
        if table_caption and table_caption[:10] in cap:
            caption_matches.append((cap, body))
    # 优先caption匹配
    if caption_matches:
        return parse_table(caption_matches[0][1])
    if section_candidates:
        return parse_table(section_candidates[0][1])
    return None


def generate_qa_for_scenario1_4_5(inst, qa_id_counter, scenario_id):
    """场景1/4/5: 用例图/流程图/功能图 + capability表
    负例注入: 功能名不一致(从capability表行中修改1个功能名)
    对表的每一数据行生成正负QA对
    """
    qa_pairs = []
    tbl = inst.get('table', {})
    rows = get_table_rows_from_content_list(inst['doc'], inst['section'], tbl.get('caption', ''))
    if not rows or len(rows) < 2:
        return qa_pairs

    headers = rows[0]
    # 找名称列和ID列 (优先匹配第一个含"名称"的列, 避免"方式名称"覆盖)
    name_col = None
    id_col = None
    for i, h in enumerate(headers):
        h_str = str(h).strip()
        if name_col is None and '名称' in h_str and '序号' not in h_str:
            name_col = i
        if id_col is None and ('标识' in h_str or '唯一' in h_str):
            id_col = i

    if name_col is None or id_col is None:
        return qa_pairs

    doc_short = inst['doc'][:15]
    section_title = inst.get('section_title', '')[:20]

    # 名称合法性: 纯中文名(可含字母数字但不得含ID模式和描述特征)
    def is_valid_name(name):
        if not name or len(name) > 30:
            return False
        if re.search(r'[A-Z]{4,}-[A-Z]{2,}-', name):  # 名称含ID
            return False
        if re.match(r'^[A-Z]{4,}-', name):  # 名称以ID开头
            return False
        if re.match(r'^[a-zA-Z]', name):  # 名称以字母开头(如a)提供...)
            return False
        if re.search(r'^[一二三四五六七八九十\d]+[)）]', name):  # 编号列表开头
            return False
        if name.endswith('为') or len(name) < 2:
            return False
        return True

    # 收集所有数据行
    data_rows = []
    for row in rows[1:]:
        func_name = str(row[name_col]).strip() if name_col < len(row) else ""
        func_id = str(row[id_col]).strip() if id_col < len(row) else ""
        req_id_match = REQ_ID_RE.search(func_id)
        canonical_id = req_id_match.group(0) if req_id_match else func_id
        if not is_valid_name(func_name):
            continue
        if not req_id_match:  # ID必须是标准REQ格式
            continue
        if canonical_id.endswith('-') or '--' in canonical_id:
            continue
        data_rows.append((func_name, canonical_id))

    if not data_rows:
        return qa_pairs

    # 对每一行生成正负QA对
    for func_name, canonical_id in data_rows:
        # 正例
        qa_pairs.append({
            "id": f"native_s{scenario_id}_{qa_id_counter[0]:04d}",
            "source": "native",
            "doc_ref": inst['doc'][:30],
            "scenario": scenario_id,
            "instruction": f"根据{doc_short}的{inst['section']}节，该功能的功能标识是什么？",
            "output": f"{func_name}的功能标识为{canonical_id}",
            "label": "positive",
            "layer": "semantic",
            "inconsistency_type": None,
            "evidence": {
                "recall_sections": [inst['section']],
                "doc_values": [{"func_name": func_name, "req_id": canonical_id, "section": inst['section']}],
                "image_caption": inst.get('image', {}).get('caption', ''),
                "table_caption": tbl.get('caption', ''),
                "image_path": inst.get('image', {}).get('path', '')
            }
        })
        qa_id_counter[0] += 1

        # 负例: 从其他行取一个不同的名字(按ID段前缀相似度选择)
        other_name = None
        for oname, oid in data_rows:
            if oname != func_name:
                # 优先选ID前缀相似的名字(难度合理)
                if oid.startswith(canonical_id[:12]) or canonical_id.startswith(oid[:12]):
                    other_name = oname
                    break
        if other_name is None:
            for oname, oid in data_rows:
                if oname != func_name:
                    other_name = oname
                    break

        if other_name:
            qa_pairs.append({
                "id": f"native_s{scenario_id}_{qa_id_counter[0]:04d}",
                "source": "native",
                "doc_ref": inst['doc'][:30],
                "scenario": scenario_id,
                "instruction": f"根据{doc_short}的{inst['section']}节，该功能的功能标识是什么？",
                "output": f"{other_name}的功能标识为{canonical_id}",
                "label": "negative",
                "layer": "semantic",
                "inconsistency_type": "name_inconsistency",
                "inconsistency_type_detail": f"回答称功能名为'{other_name}'，但文档标注为'{func_name}'",
                "evidence": {
                    "recall_sections": [inst['section']],
                    "doc_values": [{"func_name": func_name, "req_id": canonical_id, "section": inst['section']}],
                    "image_caption": inst.get('image', {}).get('caption', ''),
                    "table_caption": tbl.get('caption', ''),
                    "image_path": inst.get('image', {}).get('path', '')
                }
            })
            qa_id_counter[0] += 1

    return qa_pairs


def generate_qa_for_scenario3(inst, qa_id_counter, scenario_id):
    """场景3: 接口图 + interface表
    负例注入: 接口类型/发送方/优先级不一致
    """
    qa_pairs = []
    tbl = inst.get('table', {})
    rows = get_table_rows_from_content_list(inst['doc'], inst['section'], tbl.get('caption', ''))
    if not rows or len(rows) < 2:
        return qa_pairs

    headers = rows[0]
    # 找各列
    col_map = {}
    for i, h in enumerate(headers):
        h_str = str(h).strip()
        if '标识' in h_str and '名称' not in h_str: col_map['id'] = i
        elif '名称' in h_str and '标识' in h_str: col_map['name_id'] = i
        elif '名称' in h_str: col_map['name'] = i
        elif '类型' in h_str: col_map['type'] = i
        elif '发送' in h_str: col_map['sender'] = i
        elif '接收' in h_str: col_map['receiver'] = i
        elif '优先' in h_str: col_map['priority'] = i

    data_row = rows[1]
    def gc(name):
        idx = col_map.get(name)
        return str(data_row[idx]).strip() if idx is not None and idx < len(data_row) else ""

    iface_name = gc('name') or gc('name_id')
    iface_id = gc('id')
    iface_type = gc('type')
    sender = gc('sender')
    receiver = gc('receiver')
    priority = gc('priority')

    # 名称/标识同格时("数据协议解析接口/ZZSJHQZHFW-..."), 取"/"前的纯名称
    if '/' in iface_name and re.search(r'[A-Z]{4,}', iface_name):
        iface_name = iface_name.split('/')[0].strip()
    # 从名称/标识同格中提取ID(若有)
    if not iface_id and '/' in gc('name_id'):
        m = re.search(r'[A-Z]{4,}-[A-Z]{2,}[\w-]*', gc('name_id'))
        if m: iface_id = m.group(0)

    id_match = REQ_ID_RE.search(iface_id)
    canonical_id = id_match.group(0) if id_match else iface_id

    if not iface_name or not iface_type:
        return qa_pairs
    if len(iface_name) > 30 or iface_name.endswith('-') or not re.search(r'[\u4e00-\u9fff]', iface_name):
        return qa_pairs

    # 正例
    qa_pairs.append({
        "id": f"native_s3_{qa_id_counter[0]:04d}",
        "source": "native",
        "doc_ref": inst['doc'][:30],
        "scenario": 3,
        "instruction": f"根据{inst['doc'][:15]}的{inst['section']}节，{iface_name[:20]}的接口类型是什么？",
        "output": f"{iface_name}的接口类型为{iface_type}，发送方为{sender}，接收方为{receiver}，优先级为{priority}",
        "label": "positive",
        "layer": None,
        "inconsistency_type": None,
        "evidence": {
            "recall_sections": [inst['section']],
            "doc_values": [{"name": iface_name, "id": canonical_id, "type": iface_type,
                          "sender": sender, "receiver": receiver, "priority": priority}],
            "image_caption": inst.get('image', {}).get('caption', ''),
            "table_caption": tbl.get('caption', ''),
            "image_path": inst.get('image', {}).get('path', '')
        }
    })
    qa_id_counter[0] += 1

    # 负例: 翻转接口类型
    wrong_types = {'API接口': '网络接口', '网络接口': 'API接口', 'HTTP接口': 'API接口',
                   '人机接口': 'API接口', '文件接口': '网络接口'}
    wrong_type = wrong_types.get(iface_type, 'API接口')
    if wrong_type != iface_type:
        qa_pairs.append({
            "id": f"native_s3_{qa_id_counter[0]:04d}",
            "source": "native",
            "doc_ref": inst['doc'][:30],
            "scenario": 3,
            "instruction": f"根据{inst['doc'][:15]}的{inst['section']}节，{iface_name[:20]}的接口类型是什么？",
            "output": f"{iface_name}的接口类型为{wrong_type}，发送方为{sender}，接收方为{receiver}，优先级为{priority}",
            "label": "negative",
            "layer": "semantic",
            "inconsistency_type": "interface_type_mismatch",
            "inconsistency_type_detail": f"回答称接口类型为'{wrong_type}'，但文档标注为'{iface_type}'",
            "evidence": {
                "recall_sections": [inst['section']],
                "doc_values": [{"name": iface_name, "id": canonical_id, "type": iface_type,
                              "sender": sender, "receiver": receiver, "priority": priority}],
                "image_caption": inst.get('image', {}).get('caption', ''),
                "table_caption": tbl.get('caption', ''),
                "image_path": inst.get('image', {}).get('path', '')
            }
        })
        qa_id_counter[0] += 1

    return qa_pairs


def generate_qa_for_scenario2_7(inst, qa_id_counter, scenario_id):
    """场景2/7: 流程图/用例图 + usecase表
    负例注入: 异常流引用不一致(引用不存在的异常流编号)
    """
    qa_pairs = []
    tbl = inst.get('table', {})
    rows = get_table_rows_from_content_list(inst['doc'], inst['section'], tbl.get('caption', ''))
    if not rows or len(rows) < 2:
        return qa_pairs

    # 从usecase表提取信息
    uc_name = ""
    uc_actors = ""
    if rows and rows[0]:
        m = re.search(r'Use\s*Case\s*[名称:：]+\s*(.+)', rows[0][0], re.IGNORECASE)
        if m: uc_name = m.group(1).strip()[:50]
        for cell in rows[0]:
            am = re.search(r'[Aa]ctors?\s*[：:]\s*(.+)', cell)
            if am: uc_actors = am.group(1).strip()[:50]; break

    # 提取异常流
    body = ''
    for item in json.loads(open(CORRECT_DIR / inst['doc'] / "final" / "content_list.json").read()):
        if not isinstance(item, dict) or item.get('type') != 'table': continue
        cap = ' '.join(item.get('table_caption', []))
        if tbl.get('caption', '')[:10] in cap:
            body = item.get('table_body', '')
            break

    defined = set(re.findall(r'异常流\s*(E\d+)\s*[：:]', body))
    referenced = set(re.findall(r'(?:进入|执行|转(?:至)?|触发)\s*异常流\s*(E\d+)', body))

    if not uc_name:
        return qa_pairs

    # 正例
    exception_info = f"定义了异常流{sorted(defined)}" if defined else "无异常流定义"
    qa_pairs.append({
        "id": f"native_s{scenario_id}_{qa_id_counter[0]:04d}",
        "source": "native",
        "doc_ref": inst['doc'][:30],
        "scenario": scenario_id,
        "instruction": f"根据{inst['doc'][:15]}的{inst['section']}节，用例'{uc_name[:20]}'的异常处理流程是什么？",
        "output": f"用例'{uc_name}'的参与者为{uc_actors}，{exception_info}",
        "label": "positive",
        "layer": None,
        "inconsistency_type": None,
        "evidence": {
            "recall_sections": [inst['section']],
            "doc_values": [{"uc_name": uc_name, "actors": uc_actors,
                          "exception_defined": sorted(defined), "exception_referenced": sorted(referenced)}],
            "image_caption": inst.get('image', {}).get('caption', ''),
            "table_caption": tbl.get('caption', '')
        }
    })
    qa_id_counter[0] += 1

    # 负例: 声称引用了不存在的异常流
    if defined:
        # 找一个不在defined中的编号
        max_num = max(int(e[1:]) for e in defined) if defined else 0
        fake_exception = f"E{max_num + 1}"
        qa_pairs.append({
            "id": f"native_s{scenario_id}_{qa_id_counter[0]:04d}",
            "source": "native",
            "doc_ref": inst['doc'][:30],
            "scenario": scenario_id,
            "instruction": f"根据{inst['doc'][:15]}的{inst['section']}节，用例'{uc_name[:20]}'的异常处理流程是什么？",
            "output": f"用例'{uc_name}'定义了异常流{fake_exception}，当异常发生时执行{fake_exception}处理",
            "label": "negative",
            "layer": "logic",
            "inconsistency_type": "dangling_exception_reference",
            "inconsistency_type_detail": f"回答引用了异常流{fake_exception}，但用例表只定义了{sorted(defined)}",
            "evidence": {
                "recall_sections": [inst['section']],
                "doc_values": [{"uc_name": uc_name, "actors": uc_actors,
                              "exception_defined": sorted(defined), "exception_referenced": sorted(referenced)}],
                "image_caption": inst.get('image', {}).get('caption', ''),
                "table_caption": tbl.get('caption', '')
            }
        })
        qa_id_counter[0] += 1

    return qa_pairs


def main():
    print("=" * 60)
    print("原生QA对生成 — 从16份GJB SRS")
    print("=" * 60)

    mod_data = json.loads(MODALITY_PATH.read_text())
    scenarios = mod_data['scenarios']

    all_qa = []
    qa_id_counter = [0]

    # 按场景生成
    for sid_str in ['1', '2', '3', '4', '5', '7']:
        if sid_str not in scenarios:
            continue

        sid = int(sid_str)
        scenario_qa = []

        for doc_name, instances in scenarios[sid_str].items():
            for inst in instances:
                if inst.get('match_quality') != 'strong':
                    continue  # 只从strong匹配实例生成

                if sid in (1, 4, 5):
                    qa = generate_qa_for_scenario1_4_5(inst, qa_id_counter, sid)
                elif sid == 3:
                    qa = generate_qa_for_scenario3(inst, qa_id_counter, sid)
                elif sid in (2, 7):
                    qa = generate_qa_for_scenario2_7(inst, qa_id_counter, sid)
                else:
                    continue

                scenario_qa.extend(qa)

        all_qa.extend(scenario_qa)
        pos = sum(1 for q in scenario_qa if q['label'] == 'positive')
        neg = sum(1 for q in scenario_qa if q['label'] == 'negative')
        print(f"  场景{sid}: {len(scenario_qa)}条 (正{pos}/负{neg})")

    # 保存
    OUTPUT_PATH.write_text(json.dumps(all_qa, ensure_ascii=False, indent=2))

    # 统计
    from collections import Counter
    pos = sum(1 for q in all_qa if q['label'] == 'positive')
    neg = sum(1 for q in all_qa if q['label'] == 'negative')
    by_scenario = Counter(q.get('scenario', 0) for q in all_qa)
    by_layer = Counter(q.get('layer', 'none') for q in all_qa if q['label'] == 'negative')
    by_type = Counter(q.get('inconsistency_type', '') for q in all_qa if q['label'] == 'negative')

    print(f"\n{'='*60}")
    print(f"原生QA对总计: {len(all_qa)}条 (正{pos}/负{neg})")
    print(f"正负比: 1:{neg/max(pos,1):.1f}")
    print(f"\n按场景: {dict(sorted(by_scenario.items(), key=lambda x: str(x[0])))}")
    print(f"负例按层: {dict(by_layer)}")
    print(f"负例按类型: {dict(by_type)}")
    print(f"\n保存: {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size//1024}KB)")


if __name__ == "__main__":
    main()
