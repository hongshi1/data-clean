#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""增强Visio XML深度解析器 v2: UML全关系提取

核心增强:
  1. 边样式提取: LinePattern(实线/虚线) + EndArrow/BeginArrow(箭头类型)
  2. UML关系分类: include/extend/dependency/generalization/composition/aggregation/realization
  3. 构造型提取: «include»/«extend»/«trace» 等
  4. 增强节点分类: 30+种类型(替代当前10种的粗糙分类)
  5. 泳道/分区提取
  6. 约束提取: {precondition}/{postcondition}

输入: visio_docx/*.docx (内嵌OLE Visio)
输出: data/gjb_438c/anchor_v3/anchors_v3.json (增强版锚点)

UML关系分类规则:
  ┌────────────┬─────────────┬──────────────────┬──────────────────┐
  │ LinePattern│ EndArrow    │ Label含          │ UML关系类型      │
  ├────────────┼─────────────┼──────────────────┼──────────────────┤
  │ solid      │ none        │ -                │ ASSOCIATION      │
  │ solid      │ open(1)     │ -                │ DIRECTED         │
  │ dashed(2)  │ open(1)     │ -                │ DEPENDENCY       │
  │ dashed(2)  │ open(1)     │ include/«include»│ INCLUDE          │
  │ dashed(2)  │ open(1)     │ extend/«extend»  │ EXTEND           │
  │ dashed(2)  │ none        │ -                │ USAGE            │
  │ solid      │ hollow_tri  │ -                │ GENERALIZATION   │
  │ solid      │ filled_dia  │ -                │ COMPOSITION      │
  │ solid      │ hollow_dia  │ -                │ AGGREGATION      │
  │ dashed(2)  │ filled_tri  │ -                │ REALIZATION      │
  │ dotted(3)  │ any         │ -                │ NOTE_LINK        │
  └────────────┴─────────────┴──────────────────┴──────────────────┘

Visio Arrow Code参考:
  0=None, 1=Open, 2=Block, 3=Closed, 4=FilledTriangle,
  5=HollowTriangle, 6=FilledDiamond, 7=HollowDiamond,
  8=FilledCircle, 9=HollowCircle, 13=FilledDiamondSmall,
  14=FilledCircleSmall, 15=FilledSquare, 16=FilledSquareSmall
"""
import json
import os
import re
import sys
import zipfile
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent
DOCX_DIR = BASE / "data/gjb_438c/visio_docx"
OUT_DIR = BASE / "data/gjb_438c/anchor_v3"
NS = {'v': 'http://schemas.microsoft.com/office/visio/2012/main'}

# ============================================================================
# UML箭头代码映射表
# ============================================================================
ARROW_TYPES = {
    '0': 'none',
    '1': 'open',             # 开放箭头 → DEPENDENCY / DIRECTED
    '2': 'block',            # 实心块
    '3': 'closed',           # 闭合箭头
    '4': 'filled_triangle',  # 实心三角 → REALIZATION
    '5': 'hollow_triangle',  # 空心三角 → GENERALIZATION
    '6': 'filled_diamond',   # 实心菱形 → COMPOSITION
    '7': 'hollow_diamond',   # 空心菱形 → AGGREGATION
    '8': 'filled_circle',    # 实心圆
    '9': 'hollow_circle',    # 空心圆
    '10': 'open_45',         # 45度开放
    '11': 'open_30',         # 30度开放
    '12': 'open_60',         # 60度开放
    '13': 'filled_diamond_s', # 小实心菱形
    '14': 'filled_circle_s',  # 小实心圆
    '15': 'filled_square',    # 实心方
    '16': 'filled_square_s',  # 小实心方
    '17': 'open_curved',     # 曲线开放
    '18': 'half_curved',     # 半曲线
}

LINE_PATTERNS = {
    '1': 'solid',      # 实线
    '2': 'dashed',     # 虚线
    '3': 'dotted',     # 点线
    '4': 'dash_dot',   # 点划线
    '5': 'dash_dot_dot', # 双点划线
    '9': 'long_dash',  # 长虚线
    '10': 'dash_dot_dot',
    '16': 'cross_hatch',
    '23': 'dashed_bold',
}

# UML构造型(stereotype)关键词
STEREOTYPES = {
    'include': 'INCLUDE',
    'extend': 'EXTEND',
    '«include»': 'INCLUDE',
    '«extend»': 'EXTEND',
    '<<include>>': 'INCLUDE',
    '<<extend>>': 'EXTEND',
    'trace': 'TRACE',
    '«trace»': 'TRACE',
    'refine': 'REFINE',
    '«refine»': 'REFINE',
    'call': 'CALL',
    '«call»': 'CALL',
    'bind': 'BIND',
    '«bind»': 'BIND',
}


def classify_uml_relationship(line_pattern: str, end_arrow: str,
                               begin_arrow: str, label: str) -> str:
    """根据线型+箭头+标签分类UML关系类型

    返回: ASSOCIATION/DIRECTED/DEPENDENCY/INCLUDE/EXTEND/GENERALIZATION/
          COMPOSITION/AGGREGATION/REALIZATION/USAGE/NOTE_LINK/UNKNOWN
    """
    lp = LINE_PATTERNS.get(str(line_pattern), 'solid')
    ea = ARROW_TYPES.get(str(end_arrow), 'unknown')
    ba = ARROW_TYPES.get(str(begin_arrow), 'unknown')
    lbl = (label or '').strip()

    # 1. 构造型优先(最准确)
    for kw, uml_type in STEREOTYPES.items():
        if kw in lbl.lower() or kw in lbl:
            return uml_type

    # 2. 线型+箭头组合判断
    if lp == 'dotted':
        return 'NOTE_LINK'

    if lp == 'dashed':
        if ea in ('open', 'open_45', 'open_30', 'open_60'):
            return 'DEPENDENCY'
        if ea == 'filled_triangle':
            return 'REALIZATION'
        if ea == 'none':
            return 'USAGE'
        return 'DEPENDENCY'  # 虚线默认为依赖

    # lp == 'solid' (实线)
    if ea == 'hollow_triangle':
        return 'GENERALIZATION'
    if ea == 'filled_diamond' or ea == 'filled_diamond_s':
        return 'COMPOSITION'
    if ea == 'hollow_diamond':
        return 'AGGREGATION'
    if ea == 'filled_triangle':
        return 'REALIZATION'
    if ea in ('open', 'block', 'closed', 'open_45', 'open_30', 'open_60'):
        return 'DIRECTED'
    if ea == 'none' or ea == 'unknown':
        if ba in ('open', 'open_45', 'block', 'closed'):
            return 'DIRECTED'  # 反向有箭头
        return 'ASSOCIATION'

    return 'ASSOCIATION'  # 默认: 关联


# ============================================================================
# 增强节点分类 (30+种)
# ============================================================================
ENHANCED_TYPE_RULES = [
    # UML用例图
    (r'参与者|执行者|角色|Actor|stick.?man', 'actor'),
    (r'用例|Use\s*Case', 'usecase'),
    (r'系统边界|边界|Boundary|frame', 'boundary'),
    (r'包|Package', 'package'),
    # UML关系节点(标签节点)
    (r'[«»]|<<include>>|<<extend>>', 'stereotype'),
    (r'\{.*?\}', 'constraint'),  # {precondition} etc.
    # 流程图
    (r'初始状态|开始状态|^开始$|^Start$', 'start'),
    (r'最终状态|结束状态|^结束$|^End$', 'end'),
    (r'任务|活动|进程|过程|处理|Process|Activity', 'process'),
    (r'判定|决策|分支|Decision|Gateway|菱形', 'decision'),
    (r'分叉|合并|Fork|Join|转换.*分叉', 'fork'),
    (r'页面引用|离页|Off.?page', 'offpage'),
    (r'泳道|分区|Swimlane|Pool', 'swimlane'),
    # 状态图
    (r'状态|State', 'state'),
    (r'初始|Initial', 'start'),
    (r'终止|Final|Terminate', 'end'),
    # 组件/部署图
    (r'组件|构件|Component', 'component'),
    (r'节点|部署|Node|Deploy', 'deployment'),
    (r'接口|Interface|lollipop', 'interface'),
    (r'端口|Port', 'port'),
    (r'提供|Require|Provided', 'interface'),
    # 序列图
    (r'生命线|Lifeline', 'lifeline'),
    (r'激活|Activation|执行', 'activation'),
    (r'消息|Message|调用', 'message'),
    # 类图
    (r'类|Class', 'class'),
    (r'属性|Attribute', 'attribute'),
    (r'操作|方法|Operation|Method', 'operation'),
    # 注释
    (r'批注|注释|Comment|Note', 'note'),
    # 通用
    (r'^矩形$|^圆角矩形$|^流程框$|^框$', 'process'),
    (r'数据|存储|Data.?Store', 'datastore'),
    (r'文档|Document', 'document'),
    (r'输入|输出|Input|Output', 'io'),
    (r'连接|Connection|Link', 'connector'),
    (r'序列流|控制流|动态连接|连接线|^连线$', 'connector'),
]


def classify_shape_enhanced(name: str, master: str, nameu: str,
                            text: str = '') -> str:
    """增强节点分类: 30+种类型"""
    for pat, typ in ENHANCED_TYPE_RULES:
        for s in (name, nameu, master, text[:50]):
            if s and re.search(pat, s, re.IGNORECASE):
                return typ
    return 'other'


def get_shape_cells(shape: ET.Element) -> dict:
    """提取Shape的直接Cell子元素(含样式信息)"""
    cells = {}
    for c in shape.findall('v:Cell', NS):
        n, v = c.get('N'), c.get('V')
        if n is not None:
            cells[n] = v
    return cells


def shape_text(shape: ET.Element) -> str:
    """提取Shape的全部文本(含子Shape)"""
    texts = []
    txt = shape.find('v:Text', NS)
    if txt is not None:
        texts.append(''.join(txt.itertext()).strip())
    for sub in shape.findall('.//v:Shape', NS):
        t = sub.find('v:Text', NS)
        if t is not None:
            s = ''.join(t.itertext()).strip()
            if s:
                texts.append(s)
    seen, out = set(), []
    for t in texts:
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return '\n'.join(out)


def extract_edge_style(cells: dict) -> dict:
    """从连接线的Cell中提取样式信息"""
    lp = cells.get('LinePattern', '1')
    ea = cells.get('EndArrow', '0')
    ba = cells.get('BeginArrow', '0')
    lc = cells.get('LineColor', '')
    lw = cells.get('LineWeight', '')

    return {
        'line_pattern': LINE_PATTERNS.get(str(lp), 'solid'),
        'line_pattern_code': lp,
        'end_arrow': ARROW_TYPES.get(str(ea), 'unknown'),
        'end_arrow_code': ea,
        'begin_arrow': ARROW_TYPES.get(str(ba), 'unknown'),
        'begin_arrow_code': ba,
        'line_color': lc,
        'line_weight': lw,
    }


def parse_page_v2(page_xml: str, source: str, embed_index: str,
                  page_dims: tuple | None = None) -> dict | None:
    """增强版页面解析: 提取节点+边(含UML样式和关系类型)"""

    try:
        root = ET.fromstring(page_xml)
    except ET.ParseError:
        return None

    if page_dims:
        pw, ph = page_dims
    else:
        pw, ph = 8.5, 11.0
        ps = root.find('.//v:PageSheet', NS)
        if ps is not None:
            cells = get_shape_cells(ps)
            pw = float(cells.get('PageWidth', pw) or pw)
            ph = float(cells.get('PageHeight', ph) or ph)

    # === Pass 1: 收集全部Shape(含样式) ===
    registry = {}
    top_elems = []

    def walk(shapes_elem, depth):
        for s in shapes_elem.findall('v:Shape', NS):
            sid = s.get('ID', '')
            name = s.get('Name', '') or ''
            nameu = s.get('NameU', '') or ''
            master = s.get('Master', '') or ''
            cells = get_shape_cells(s)
            text = shape_text(s)
            typ = classify_shape_enhanced(name, master, nameu, text)

            # 提取连接线样式
            style = extract_edge_style(cells) if typ == 'connector' else {}

            registry[sid] = {
                'id': sid, 'name': name, 'nameu': nameu, 'master': master,
                'type': typ, 'cells': cells, 'text': text,
                'is_child': depth > 0, 'style': style,
            }
            if depth == 0:
                top_elems.append((sid, s))
            sub = s.find('v:Shapes', NS)
            if sub is not None:
                walk(sub, depth + 1)

    page_shapes_root = root.find('.//v:Shapes', NS)
    if page_shapes_root is None:
        return None
    walk(page_shapes_root, 0)

    # === Pass 2: 构建语义节点 ===
    semantic_nodes = []
    id_to_node = {}

    for sid, elem in top_elems:
        reg = registry.get(sid, {})
        typ = reg.get('type', 'other')

        if typ == 'connector':
            continue

        cells = reg.get('cells', {})
        cx = float(cells.get('PinX', 0) or 0)
        cy = float(cells.get('PinY', 0) or 0)
        w = abs(float(cells.get('Width', 0) or 0))
        h = abs(float(cells.get('Height', 0) or 0))
        text = reg.get('text', '')

        node = {
            'id': sid,
            'text': text,
            'type': typ,
            'cx': round(cx, 4), 'cy': round(cy, 4),
            'w': round(w, 4), 'h': round(h, 4),
            'rx': round(cx / pw, 4) if pw else 0,
            'ry': round(1 - cy / ph, 4) if ph else 0,
        }
        # 增强: 泳道信息
        if typ == 'swimlane':
            node['swimlane_name'] = text[:20]

        # 增强: 约束信息
        if typ == 'constraint':
            node['constraint'] = text[:50]

        # 增强: 构造型信息
        if typ == 'stereotype':
            node['stereotype'] = text[:30]

        semantic_nodes.append(node)
        id_to_node[sid] = node

    # === Pass 3: Connect重建边(含UML关系分类) ===
    conns = root.findall('.//v:Connect', NS)
    by_connector = defaultdict(lambda: {'begin': [], 'end': []})
    for conn in conns:
        from_id = conn.get('FromSheet', '')
        from_cell = conn.get('FromCell', '')
        to_id = conn.get('ToSheet', '')
        if from_cell and from_cell.startswith('Begin'):
            by_connector[from_id]['begin'].append(to_id)
        else:
            by_connector[from_id]['end'].append(to_id)

    # 连接线元素(用于提取标签和样式)
    connector_elems = {}
    for sid, elem in top_elems:
        connector_elems[sid] = elem
    for elem in page_shapes_root.findall('.//v:Shape', NS):
        connector_elems.setdefault(elem.get('ID', ''), elem)

    edges = []
    edge_stats = defaultdict(int)

    for cid, ends in by_connector.items():
        begins = ends['begin']
        endlist = ends['end']
        if not begins or not endlist:
            continue

        # 获取连接线信息
        conn_reg = registry.get(cid, {})
        conn_style = conn_reg.get('style', {})
        label = ''
        if cid in connector_elems:
            label = shape_text(connector_elems[cid])

        # UML关系分类
        uml_type = classify_uml_relationship(
            conn_style.get('line_pattern_code', '1'),
            conn_style.get('end_arrow_code', '0'),
            conn_style.get('begin_arrow_code', '0'),
            label)

        for b in begins:
            for e in endlist:
                src = id_to_node.get(b)
                dst = id_to_node.get(e)
                if src is None or dst is None:
                    continue

                edge = {
                    'src': b, 'dst': e,
                    'src_text': src['text'], 'dst_text': dst['text'],
                    'label': label,
                    'uml_type': uml_type,
                    'line_pattern': conn_style.get('line_pattern', 'solid'),
                    'end_arrow': conn_style.get('end_arrow', 'none'),
                    'begin_arrow': conn_style.get('begin_arrow', 'none'),
                    'connector_id': cid, 'via': 'glued',
                }

                # 构造型信息
                for kw, st in STEREOTYPES.items():
                    if kw in label.lower():
                        edge['stereotype'] = st
                        break

                edges.append(edge)
                edge_stats[uml_type] += 1

    # === Pass 3b: 几何边恢复(未粘合) ===
    SNAP_TH = 0.35
    existing = {(e['src'], e['dst']) for e in edges}

    def bbox_dist(px, py, node):
        x1, x2 = node['cx'] - node['w']/2, node['cx'] + node['w']/2
        y1, y2 = node['cy'] - node['h']/2, node['cy'] + node['h']/2
        dx = max(x1 - px, 0, px - x2)
        dy = max(y1 - py, 0, py - y2)
        return (dx*dx + dy*dy) ** 0.5

    for cid, elem in connector_elems.items():
        if cid in by_connector or cid not in registry:
            continue
        reg = registry[cid]
        if reg.get('type') != 'connector':
            continue

        cells = reg.get('cells', {})
        style = reg.get('style', {})
        bx, by = cells.get('BeginX'), cells.get('BeginY')
        ex, ey = cells.get('EndX'), cells.get('EndY')
        if not all(v for v in (bx, by, ex, ey)):
            continue
        try:
            bx, by, ex, ey = float(bx), float(by), float(ex), float(ey)
        except ValueError:
            continue
        if abs(bx-ex) < 0.01 and abs(by-ey) < 0.01:
            continue

        best_b = min(((bbox_dist(bx, by, n), n) for n in semantic_nodes),
                     default=None, key=lambda t: t[0])
        best_e = min(((bbox_dist(ex, ey, n), n) for n in semantic_nodes),
                     default=None, key=lambda t: t[0])
        if not best_b or not best_e:
            continue
        (db, nb), (de, ne) = best_b, best_e
        if db > SNAP_TH or de > SNAP_TH or nb['id'] == ne['id']:
            continue
        if (nb['id'], ne['id']) in existing:
            continue

        label = shape_text(elem)
        uml_type = classify_uml_relationship(
            style.get('line_pattern_code', '1'),
            style.get('end_arrow_code', '0'),
            style.get('begin_arrow_code', '0'),
            label)

        edges.append({
            'src': nb['id'], 'dst': ne['id'],
            'src_text': nb['text'], 'dst_text': ne['text'],
            'label': label,
            'uml_type': uml_type,
            'line_pattern': style.get('line_pattern', 'solid'),
            'end_arrow': style.get('end_arrow', 'none'),
            'begin_arrow': style.get('begin_arrow', 'none'),
            'connector_id': cid, 'via': 'geo',
        })
        existing.add((nb['id'], ne['id']))
        edge_stats[uml_type] += 1

    # === 统计信息 ===
    node_type_dist = defaultdict(int)
    for n in semantic_nodes:
        node_type_dist[n['type']] += 1

    return {
        'source': source,
        'embed_index': embed_index,
        'page': {'w': pw, 'h': ph},
        'nodes': semantic_nodes,
        'edges': edges,
        'meta': {
            'n_nodes': len(semantic_nodes),
            'n_edges': len(edges),
            'uml_edge_types': dict(edge_stats),
            'node_types': dict(node_type_dist),
            'n_glued': sum(1 for e in edges if e['via'] == 'glued'),
            'n_geo': sum(1 for e in edges if e['via'] == 'geo'),
        },
    }


def extract_all(docx_dir: Path):
    """从所有.docx中提取增强版锚点"""
    all_anchors = {}
    total_uml = defaultdict(int)

    docx_files = sorted(docx_dir.glob("*.docx"))
    print(f"发现{len(docx_files)}份docx文件")

    for docx_path in docx_files:
        doc_name = docx_path.stem
        structures = []

        try:
            with zipfile.ZipFile(docx_path, 'r') as zf:
                embeds = sorted(
                    [f for f in zf.namelist() if f.startswith('word/embeddings/')],
                    key=lambda x: int(re.search(r'oleObject(\d+)', x).group(1)) if re.search(r'oleObject(\d+)', x) else 0)

                for embed_path in embeds:
                    data = zf.read(embed_path)
                    if not data[:4].hex() == 'd0cf11e0':
                        continue

                    # OLE → Package → ZIP → Visio XML
                    import olefile
                    ole = olefile.OleFileIO(io.BytesIO(data))
                    if ['Package'] not in ole.listdir():
                        continue
                    pkg = ole.openstream('Package').read()
                    if pkg[:2] != b'PK':
                        continue

                    vz = zipfile.ZipFile(io.BytesIO(pkg))
                    page_files = [f for f in vz.namelist()
                                  if re.match(r'visio/pages/page\d+\.xml$', f)]

                    # 页面尺寸映射
                    page_dims_map = {}
                    try:
                        pages_xml = vz.read('visio/pages/pages.xml').decode('utf-8', errors='replace')
                        proot = ET.fromstring(pages_xml)
                        for pel in proot.findall('.//{*}Page'):
                            pid = pel.get('ID', '')
                            pcells = {}
                            for c in pel.findall('{*}Cell'):
                                pcells[c.get('N', '')] = c.get('V', '')
                            pw = float(pcells.get('PageWidth', 8.5) or 8.5)
                            ph = float(pcells.get('PageHeight', 11.0) or 11.0)
                            page_dims_map[pid] = (pw, ph)
                    except Exception:
                        pass

                    for pf in page_files:
                        xml = vz.read(pf).decode('utf-8', errors='replace')
                        embed_idx = embed_path.split('/')[-1]
                        structure = parse_page_v2(xml, embed_path,
                                                  f"{embed_idx}:{pf.split('/')[-1]}",
                                                  page_dims_map.get(
                                                      str(page_files.index(pf))))
                        if structure and structure['nodes']:
                            structures.append(structure)

        except Exception as e:
            print(f"  ⚠ {doc_name[:20]}: {e}")
            continue

        if structures:
            all_anchors[doc_name] = {
                'visio_count': len(structures),
                'structures': structures,
            }
            # 汇总UML关系统计
            for st in structures:
                for utype, cnt in st['meta']['uml_edge_types'].items():
                    total_uml[utype] += cnt

            n_nodes = sum(len(s['nodes']) for s in structures)
            n_edges = sum(len(s['edges']) for s in structures)
            uml_types = defaultdict(int)
            for s in structures:
                for ut, cnt in s['meta']['uml_edge_types'].items():
                    uml_types[ut] += cnt
            print(f"  {doc_name[:16]:18s} | {len(structures):2d}图 "
                  f"{n_nodes:4d}节点 {n_edges:4d}边 | "
                  f"UML: {dict(uml_types)}")

    # 全库UML统计
    print("\n全库UML关系分布:")
    for utype, cnt in sorted(total_uml.items(), key=lambda x: -x[1]):
        print(f"  {utype:20s}: {cnt}")

    return all_anchors


if __name__ == "__main__":
    import io
    os.makedirs(OUT_DIR, exist_ok=True)

    result = extract_all(DOCX_DIR)

    out_path = OUT_DIR / "anchors_v3.json"
    json.dump(result, open(out_path, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    total_struct = sum(d['visio_count'] for d in result.values())
    total_nodes = sum(len(s['nodes']) for d in result.values()
                      for s in d['structures'])
    total_edges = sum(len(s['edges']) for d in result.values()
                      for s in d['structures'])
    print(f"\n{'='*60}")
    print(f"增强锚点提取完成: {len(result)}文档 {total_struct}结构 "
          f"{total_nodes}节点 {total_edges}边")
    print(f"输出: {out_path}")
