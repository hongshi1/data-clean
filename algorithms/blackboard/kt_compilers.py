"""κ_T表格编译器 (vendored from tools/m16_scene_tier1.py + tools/m1_compare_engine.py).

覆盖5种表型编译器:
  capability(能力表, sc1/sc4) / interface(接口表, sc3) /
  subfunction(子功能表, sc5) / usecase(用例描述表, sc2/sc7)

为什么vendor: m16/m1顶层依赖requests+emb_cache, 编译器本身纯stdlib.
同步性由tests/test_kt_sync.py保证(真实表格上与live版输出一致).

保持与tools/{m16_scene_tier1,m1_compare_engine}.py同步.
"""
from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path


def read_rows(csv_path: Path) -> list[list[str]]:
    with open(csv_path, encoding='utf-8') as f:
        return [[c.strip() for c in row] for row in csv.reader(f)]


ID_PAT = re.compile(r'^[A-Z][A-Z0-9-]{5,}$')


def split_name_id(s: str) -> tuple[str, str]:
    """'名称/标识' → ('名称','标识'); 标识须像ID(大写字母数字连字符)"""
    if '/' in s:
        name, _, tid = s.partition('/')
        name, tid = name.strip(), tid.strip()
        if tid and ID_PAT.match(tid):
            return name, tid
        if tid and len(tid) > len(name) and tid.replace('-', '').isalnum():
            return name, tid
    return s.strip(), ''


# ═══════════════════════════════════════════════════════════════
# 能力表 (sc1/sc4)
# ═══════════════════════════════════════════════════════════════

def compile_capability_table(csv_path: Path) -> dict:
    """能力表: 序号|Use case名称|标识|描述|...
    容错: 序号列可为空(按名称列判行); name/ID可能合并"""
    rows = read_rows(csv_path)
    caps = []
    seq = 0
    for r in rows[1:]:
        if not r:
            continue
        name_raw = r[1].strip() if len(r) > 1 else ''
        if not name_raw or ('名称' in name_raw[:6] and '标识' in ''.join(r[:3])):
            continue  # 空行或表头
        seq += 1
        name, split_id = split_name_id(name_raw)
        tid = (r[2].strip() if len(r) > 2 else '') or split_id
        caps.append({
            'seq': seq, 'name': name, 'id': tid,
            'desc': r[3].strip() if len(r) > 3 else '',
        })
    return {'type': 'capability', 'caps': caps,
            'nodes': [{'id': f'cap{c["seq"]}', 'text': c['name'], 'type': 'capability'}
                      for c in caps if c['name']]}


# ═══════════════════════════════════════════════════════════════
# 接口表 (sc3) — 表头驱动
# ═══════════════════════════════════════════════════════════════

def compile_interface_table(csv_path: Path) -> dict:
    """接口表: 兼容两种列序
    格式A: 序号|接口需求名称|标识|接口类型|发送方|接收方|接口内容|优先级
    格式B: 序号|接口名称/标识|接口描述|发送方|接收方|接口类型|优先级|备注
    """
    rows = read_rows(csv_path)
    if not rows:
        return {'type': 'interface', 'interfaces': [], 'components': [], 'nodes': []}
    header = [h.replace(' ', '') for h in rows[0]]

    def find_col(*keys):
        for i, h in enumerate(header):
            if any(k in h for k in keys):
                return i
        return None

    name_col = find_col('名称')
    desc_col = find_col('描述', '内容')
    sender_col = find_col('发送方')
    receiver_col = find_col('接收方')
    itype_col = find_col('类型')
    id_col = find_col('标识')
    if name_col is not None and '/' in header[name_col]:
        id_col = name_col

    def cell(r, col):
        if col is None or col >= len(r):
            return ''
        return r[col].strip()

    interfaces = []
    cur = None
    seq = 0
    for r in rows[1:]:
        if not r or not any(c.strip() for c in r):
            continue
        name_raw = cell(r, name_col)
        if name_raw and '名称' not in name_raw[:4]:
            seq += 1
            name, split_id = split_name_id(name_raw)
            tid = cell(r, id_col) if id_col != name_col else split_id
            cur = {'seq': seq, 'name': name, 'id': tid,
                   'itype': cell(r, itype_col), 'interactions': []}
            interfaces.append(cur)
            sender, receiver = cell(r, sender_col), cell(r, receiver_col)
            if sender or receiver:
                cur['interactions'].append({
                    'sender': sender, 'receiver': receiver,
                    'content': cell(r, desc_col)})
        elif cur is not None:
            # 续行: 名称空但有收发方
            sender, receiver = cell(r, sender_col), cell(r, receiver_col)
            if sender or receiver:
                cur['interactions'].append({
                    'sender': sender, 'receiver': receiver,
                    'content': cell(r, desc_col)})
    GENERIC = {'本系统', '本分系统', '系统', '用户', '外部系统', '高', '中', '低', '—', '-'}
    nodes, seen_comp = [], set()
    for itf in interfaces:
        if itf['name']:
            nodes.append({'id': f'itf{itf["seq"]}', 'text': itf['name'], 'type': 'interface'})
    for itf in interfaces:
        for ia in itf['interactions']:
            for role in ('sender', 'receiver'):
                comp = ia[role]
                if comp and comp not in seen_comp and comp not in GENERIC:
                    seen_comp.add(comp)
                    nodes.append({'id': f'comp{len(nodes)}', 'text': comp, 'type': 'component'})
    return {'type': 'interface', 'interfaces': interfaces,
            'components': sorted(seen_comp), 'nodes': nodes}


# ═══════════════════════════════════════════════════════════════
# 子功能表 (sc5)
# ═══════════════════════════════════════════════════════════════

def compile_subfunction_table(csv_path: Path) -> dict:
    """子功能表: 序号|子功能名称/标识|描述|优先级"""
    rows = read_rows(csv_path)
    subs = []
    seq = 0
    for r in rows[1:]:
        if not r:
            continue
        name_raw = r[1].strip() if len(r) > 1 else r[0].strip()
        if not name_raw or '名称' in name_raw[:6]:
            continue
        seq += 1
        name, tid = split_name_id(name_raw)
        subs.append({'seq': seq, 'name': name, 'id': tid,
                     'desc': r[2].strip() if len(r) > 2 else ''})
    return {'type': 'subfunction', 'subs': subs,
            'nodes': [{'id': f'sub{s["seq"]}', 'text': s['name'], 'type': 'subfunction'}
                      for s in subs if s['name']]}


# ═══════════════════════════════════════════════════════════════
# 用例描述表 (sc2/sc7) — from m1_compare_engine
# ═══════════════════════════════════════════════════════════════

def compile_usecase_table(csv_path: Path) -> dict:
    """GJB用例描述表 → 结构化图 X_T
    节点: 主事件流步骤(process) + 异常流(exception)
    边:   顺序边 s_i→s_{i+1}; 步骤引用"异常流E1" → E1节点
    """
    if not csv_path.exists():
        return {}
    rows = read_rows(csv_path)
    text_all = csv_path.read_text(encoding='utf-8')

    # ── 头部字段 ──
    uc_name, actors = '', []
    for row in rows[:4]:
        for cell in row:
            m = re.search(r'Use\s*Case\s*名称[：:]\s*(.+)', cell)
            if m:
                uc_name = m.group(1).strip()
            m = re.search(r'Actors?[：:]\s*(.+)', cell, re.I)
            if m:
                actors = [a.strip() for a in re.split(r'[、,，;；]', m.group(1)) if a.strip()]

    # ── 主事件流步骤: 仅Actor/系统动作列, 按步骤号边界切分 ──
    steps: dict[int, str] = {}
    in_main = False
    main_zone = []
    for row in rows:
        joined = ''.join(row)
        if re.search(r'主事件流|基本流', joined):
            in_main = True
            continue
        if re.search(r'^\s*(后置条件|异常流|扩展流)', joined) and in_main:
            in_main = False
        if in_main and joined:
            main_zone.append(' '.join(c for c in row[:2] if c))
    main_text = ' '.join(main_zone) if main_zone else text_all

    STEP_BOUND = re.compile(r'(?<![\w.])(\d{1,2})\s*[\.．、]\s*')
    parts = STEP_BOUND.split(main_text)
    i = 1
    while i < len(parts):
        num_s = parts[i]
        content = parts[i + 1] if i + 1 < len(parts) else ''
        try:
            num = int(num_s)
        except ValueError:
            i += 2
            continue
        # 截断到下一个步骤号边界
        content = re.split(r'[\s,，;；]\d{1,2}\s*[\.．、]\s*[\u4e00-\u9fff]', content)[0]
        content = content.strip()
        if len(content) >= 4 and (num not in steps or len(content) > len(steps[num])):
            steps[num] = content
        i += 2

    # ── 异常流 ──
    exceptions: dict[str, str] = {}
    for m in re.finditer(r'异常流\s*(E\d+)\s*[：:]\s*([^\n]{4,})', text_all):
        eid = m.group(1).upper()
        exceptions[eid] = m.group(2).strip()
    step_exc_refs: dict[int, list[str]] = defaultdict(list)
    for num, txt in steps.items():
        for m in re.finditer(r'异常流\s*(E\d+)', txt):
            step_exc_refs[num].append(m.group(1).upper())

    # ── 编译为图 ──
    nodes = []
    edges = []
    sorted_nums = sorted(steps.keys())
    for num in sorted_nums:
        nodes.append({'id': f's{num}', 'num': num, 'text': steps[num],
                      'type': 'process', 'exc_refs': step_exc_refs.get(num, [])})
    for eid, txt in exceptions.items():
        nodes.append({'id': f'exc_{eid}', 'text': txt, 'type': 'exception', 'eid': eid})
    for k in range(len(sorted_nums) - 1):
        edges.append({'src': f's{sorted_nums[k]}', 'dst': f's{sorted_nums[k + 1]}',
                      'type': 'sequence'})
    for num, eids in step_exc_refs.items():
        for eid in eids:
            if eid in exceptions:
                edges.append({'src': f's{num}', 'dst': f'exc_{eid}', 'type': 'exception'})

    return {'type': 'usecase', 'uc_name': uc_name, 'actors': actors,
            'steps': steps, 'exceptions': exceptions,
            'nodes': nodes, 'edges': edges}


# ═══════════════════════════════════════════════════════════════
# 场景→编译器路由
# ═══════════════════════════════════════════════════════════════

SCENE_COMPILER: dict[str, object] = {
    'sc1_usecase_capability': compile_capability_table,
    'sc2_flowchart_usecase': compile_usecase_table,
    'sc3_interface_interface': compile_interface_table,
    'sc4_flowchart_capability': compile_capability_table,
    'sc5_function_capability': compile_subfunction_table,
    'sc7_usecase_usecase': compile_usecase_table,
    # sc8_pure_image: 无表格 → 无编译器(诚实排除)
}


def compile_for_scene(scene: str, csv_path: Path) -> dict | None:
    """按场景选择κ_T编译器; sc8返回None(无表)."""
    compiler = SCENE_COMPILER.get(scene)
    if compiler is None or not csv_path.exists():
        return None
    return compiler(csv_path)  # type: ignore[operator]
