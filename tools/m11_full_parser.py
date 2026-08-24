#!/usr/bin/env python3
"""
M11: 完整Visio解析器 (三限制全部修复)
======================================
实现 visio_format_deep_dive.md 的升级路线阶段1-6:
  阶段1 Master解析: masters.xml.rels → MasterID → masterN.xml → 三层继承(Cell/行/文本)
  阶段2 嵌套组变换: M = T(Pin)·R(Angle)·Flip·T(-LocPin) 逐级上溯
  阶段3 Geometry折线: 行级+Cell级master合并 → 完整路径(局部→页面系)
  阶段4 方向三重证据: Connect记录 + 箭头Cell + 粘合公式(PAR(PNT(Sheet.N!...)))
  阶段5 边标签: 线Text + TxtPin锚点 + 独立标签几何邻近
  阶段6 类型判定: Master NameU(最可靠) > 实例NameU > 实例Name

输出与M0兼容(nodes/edges/page), 增强:
  nodes: + abs_bbox(页面系) + master_type + via_master
  edges: + waypoints(完整折线) + direction_evidence + label_pos

用法: python3 tools/m11_full_parser.py [--docs 02界面...]
"""
import argparse
import io
import json
import math
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import olefile

BASE = Path(__file__).resolve().parent.parent
DOCX_DIR = BASE / "data/gjb_438c/visio_docx"
OUT_DIR = BASE / "data/gjb_438c/anchor_v2"
OUT_DIR.mkdir(parents=True, exist_ok=True)

NS = {'v': 'http://schemas.microsoft.com/office/visio/2012/main'}
R_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
V = NS['v']

# ── 类型规则: Master NameU(去.N后缀)优先, 兼容实例名 ──────────
TYPE_RULES_V2 = [
    (r'^Initial State$|^Start$|^Initial node$|^Start/End$|初始状态|开始状态', 'start'),
    (r'^Final State$|^End$|^Final node$|最终状态|结束状态', 'end'),
    (r'^Sequence Flow$|^Dynamic connector$|^Control Flow$|^Transition$|^Connector|^Arced arrow|^Message$|^Communicates$|序列流|动态连接|连接线|^直线|^转换$|^转换\.\d|条件流程', 'connector'),
    (r'^Transition \(Fork\)$|^Transition \(Join\)$|^Join node$|分叉|合并', 'fork'),
    (r'^Actor$|参与者|执行者|角色|^External interactor$', 'actor'),
    (r'^Use Case$|用例', 'usecase'),
    (r'^Discriminator$|^Decision|判定|决策|分支', 'decision'),
    (r'^Task$|^Process$|^Action$|^Action State$|^Data process$|^Data store$|^Circle$|^Ellipse$|^Diamond$|任务|过程|进程|活动', 'process'),
    (r'^State$|状态', 'state'),
    (r'^System Boundary$|^Boundary|系统边界|边界', 'boundary'),
    (r'^Generalization$|^Include$|^Extend$|^Association$|^Message Flow$|^Composition$|^Dependency$|归纳|泛化', 'relation'),
    (r'^Rectangle$|^Box$|^Component$|^Package$|^Subsystem$|^Group$|矩形|^框$|圆角矩形', 'process'),
    (r'^Gateway$|网关', 'gateway'),
    (r'^Off-page|页面引用|离页|^On-page reference', 'offpage'),
]


def classify(nameu: str, name: str) -> str | None:
    for pat, typ in TYPE_RULES_V2:
        for s in (nameu or '', name or ''):
            if s and re.search(pat, s):
                return typ
    return None


# ═══════════════════════════════════════════════════════════════
# Master仓库: 三层继承的供给侧
# ═══════════════════════════════════════════════════════════════

class MasterStore:
    """masters.xml(+rels) → Master ID → {meta, 形状索引, 根形状}"""

    def __init__(self, vz: zipfile.ZipFile):
        self.meta = {}       # master_id -> {NameU, Name}
        self.shape_idx = {}  # (master_id, shape_id) -> Element
        self.root = {}       # master_id -> 根Shape Element
        names = vz.namelist()
        masters_xml_path = next((p for p in names
                                 if re.match(r'visio/masters/masters\d*\.xml$', p)), None)
        if not masters_xml_path:
            return
        # rels: rId → 目标文件名
        rel_map = {}
        rels_path = next((p for p in names
                          if re.match(r'visio/masters/_rels/masters\d*\.xml\.rels$', p)), None)
        if rels_path:
            rels = vz.read(rels_path).decode('utf-8', errors='replace')
            for m in re.finditer(r'Id="(rId\d+)"[^>]*Target="([^"]+)"', rels):
                rel_map[m.group(1)] = m.group(2).lstrip('./')

        try:
            root = ET.fromstring(vz.read(masters_xml_path).decode('utf-8', errors='replace'))
        except ET.ParseError:
            return
        for master in root.findall('v:Master', NS):
            mid = master.get('ID', '')
            self.meta[mid] = {'NameU': master.get('NameU', '') or '',
                              'Name': master.get('Name', '') or ''}
            rel = master.find('v:Rel', NS)
            target = ''
            if rel is not None:
                rid = rel.get(f'{{{R_NS}}}id', '')
                target = rel_map.get(rid, '')
            fpath = 'visio/masters/' + target
            if not target or fpath not in names:
                continue
            try:
                mroot = ET.fromstring(vz.read(fpath).decode('utf-8', errors='replace'))
            except (KeyError, ET.ParseError):
                continue
            # 索引全部形状 + 记根形状(MasterContents/Shapes的第一个Shape)
            for shapes in mroot.iter(f'{{{V}}}Shapes'):
                for s in shapes.findall('v:Shape', NS):
                    sid = s.get('ID', '')
                    self.shape_idx[(mid, sid)] = s
                    if mid not in self.root:
                        self.root[mid] = s

    def get_master_shape(self, master_id: str, master_shape_id: str | None):
        """继承目标: 有MasterShape→master树内该子形状; 无→master根形状"""
        if not master_id:
            return None
        if master_shape_id:
            return self.shape_idx.get((master_id, master_shape_id))
        return self.root.get(master_id)


# ═══════════════════════════════════════════════════════════════
# 变换与几何
# ═══════════════════════════════════════════════════════════════

def f(cells: dict, key: str, default=0.0) -> float:
    v = cells.get(key)
    if v is None or v == '':
        return default
    try:
        return float(v)
    except ValueError:
        return default


def local_to_parent(lx: float, ly: float, cells: dict) -> tuple[float, float]:
    """形状局部系 → 父容器系: M = T(Pin)·R(Angle)·Flip·T(-LocPin)"""
    pinx, piny = f(cells, 'PinX'), f(cells, 'PinY')
    locx, locy = f(cells, 'LocPinX', pinx), f(cells, 'LocPinY', piny)
    angle = f(cells, 'Angle')
    x, y = lx - locx, ly - locy
    if cells.get('FlipX') == '1':
        x = -x
    if cells.get('FlipY') == '1':
        y = -y
    if angle:
        ca, sa = math.cos(angle), math.sin(angle)
        x, y = x * ca - y * sa, x * sa + y * ca
    return x + pinx, y + piny


def to_page(rec: dict, lx: float, ly: float) -> tuple[float, float]:
    """局部坐标 → 页面坐标: 先过自身XForm, 再沿父链逐级上溯"""
    x, y = local_to_parent(lx, ly, rec['cells'])
    p = rec.get('parent')
    while p is not None:
        x, y = local_to_parent(x, y, p['cells'])
        p = p.get('parent')
    return x, y


def shape_bbox_page(rec: dict) -> list[float]:
    """局部bbox四角 → 页面系 → 外接AABB"""
    w, h = f(rec['cells'], 'Width'), f(rec['cells'], 'Height')
    corners = [(0, 0), (w, 0), (w, h), (0, h)]
    pts = [to_page(rec, cx, cy) for cx, cy in corners]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return [min(xs), min(ys), max(xs), max(ys)]


def merged_geometry_rows(shape_elem, master_shape) -> list[dict]:
    """Geometry行合并: master行打底, 实例行按IX覆盖(行内Cell级合并, Del=1删除)"""
    rows = {}

    def collect(elem):
        if elem is None:
            return
        for sec in elem.findall('v:Section', NS):
            if sec.get('N') != 'Geometry':
                continue
            for row in sec.findall('v:Row', NS):
                ix = row.get('IX', '')
                if row.get('Del') == '1':
                    rows.pop(ix, None)
                    continue
                t = row.get('T', '')
                cells = {c.get('N'): c.get('V') for c in row.findall('v:Cell', NS)}
                if ix in rows:
                    rows[ix]['cells'].update(cells)
                    if t:
                        rows[ix]['T'] = t
                else:
                    rows[ix] = {'T': t, 'cells': cells}

    collect(master_shape)   # master打底
    collect(shape_elem)     # 实例覆盖
    return [rows[k] for k in sorted(rows.keys(), key=lambda x: int(x) if x.isdigit() else 0)]


def arc_points(p0, p1, sagitta: float, n: int = 6) -> list[tuple]:
    """ArcTo(弓高A)离散化"""
    if abs(sagitta) < 1e-6 or not p0 or not p1:
        return [p1]
    (x0, y0), (x1, y1) = p0, p1
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy)
    if L < 1e-9:
        return [p1]
    # 弓高→半径: r = (L²/4 + h²) / (2h)
    h = abs(sagitta)
    r = (L * L / 4 + h * h) / (2 * h)
    # 法向偏移(符号随sagitta)
    nx, ny = -dy / L, dx / L
    sign = 1 if sagitta > 0 else -1
    # 圆心: 中点 + 法向*(r-h)*sign
    d = (r - h) * sign
    cx, cy = mx + nx * d, my + ny * d
    a0 = math.atan2(y0 - cy, x0 - cx)
    a1 = math.atan2(y1 - cy, x1 - cx)
    # 走短弧
    da = (a1 - a0) % (2 * math.pi)
    if da > math.pi:
        da -= 2 * math.pi
    pts = []
    for i in range(1, n + 1):
        a = a0 + da * i / n
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def reconstruct_path(rows: list[dict], cells: dict) -> list[tuple]:
    """Geometry行 → 折线点列表(局部坐标)"""
    W, H = abs(f(cells, 'Width')), abs(f(cells, 'Height'))
    pts, cur = [], None
    for row in rows:
        t, c = row['T'], row['cells']
        if c.get('X') is None:
            continue
        try:
            x, y = float(c['X']), float(c.get('Y', 0) or 0)
        except ValueError:
            continue
        if t.startswith('Rel'):
            x, y = x * W, y * H
        if t == 'MoveTo' or (not t and cur is None):
            cur = (x, y)
            pts.append(cur)
        elif t == 'ArcTo':
            a = float(c.get('A', 0) or 0)
            seg = arc_points(cur, (x, y), a)
            pts.extend(seg[1:] if seg and seg[0] == cur else seg)
            cur = (x, y)
        elif t == 'LineTo' or not t or t.startswith('Rel'):
            if cur is not None and (abs(x - cur[0]) > 1e-9 or abs(y - cur[1]) > 1e-9):
                cur = (x, y)
                pts.append(cur)
        # Spline/NURBS/Ellipse: 直线近似到端点
        elif t in ('SplineStart', 'SplineKnot', 'NURBSTo', 'EllipticalArcTo',
                   'InfiniteLine', 'PolylineTo'):
            if cur is not None:
                cur = (x, y)
                pts.append(cur)
    return pts


# ═══════════════════════════════════════════════════════════════
# 页面解析
# ═══════════════════════════════════════════════════════════════

def parse_glue_formula(cells: dict, key: str) -> str | None:
    """粘合公式: BeginX F='PAR(PNT(Sheet.60!Connections.X1,...))' → '60'"""
    # 注意F属性在Cell元素上, get_cells只取了V → 需要单独读
    return None  # 在walk里直接读F


def walk_shapes(shapes_elem, parent_rec, parent_master_id, master_store, records):
    for s in shapes_elem.findall('v:Shape', NS):
        sid = s.get('ID', '')
        local_cells = {}
        f_attrs = {}  # N -> F公式(粘合证据)
        for c in s.findall('v:Cell', NS):
            n, v = c.get('N'), c.get('V')
            if n is not None:
                local_cells[n] = v
                if c.get('F'):
                    f_attrs[n] = c.get('F')

        # ── Master继承解析 ──
        mid = s.get('Master')
        mshape_id = s.get('MasterShape')
        resolved_mid = mid or (parent_master_id if mshape_id else None)
        master_shape = None
        if mid and not mshape_id:
            master_shape = master_store.get_master_shape(mid, None)
        elif resolved_mid and mshape_id:
            master_shape = master_store.get_master_shape(resolved_mid, mshape_id)
        cells = dict(local_cells)
        master_meta = master_store.meta.get(resolved_mid or '', {})
        if master_shape is not None:
            mc = {}
            for c in master_shape.findall('v:Cell', NS):
                if c.get('N') is not None:
                    mc[c.get('N')] = c.get('V')
            for k, v in mc.items():
                cells.setdefault(k, v)

        # ── 文本(自身+子Shape合并) ──
        texts = []
        txt = s.find('v:Text', NS)
        if txt is not None:
            texts.append(''.join(txt.itertext()).strip())
        for sub in s.findall('.//v:Shape', NS):
            t = sub.find('v:Text', NS)
            if t is not None:
                tt = ''.join(t.itertext()).strip()
                if tt:
                    texts.append(tt)
        seen, text_parts = set(), []
        for t in texts:
            if t and t not in seen:
                seen.add(t)
                text_parts.append(t)
        text = '\n'.join(text_parts)

        # ── 类型判定(阶段6: Master NameU优先) ──
        nameu = (s.get('NameU', '') or '')
        inst_name = (s.get('Name', '') or '')
        master_nameu = master_meta.get('NameU', '')
        base_nameu = re.sub(r'\.\d+$', '', nameu)  # 实例NameU去序号后缀
        shape_type = (classify(master_nameu, '') or classify(base_nameu, '')
                      or classify('', inst_name) or 'other')

        # 语义细化: relation类型若为1D形状(BeginX/EndX存在) → 实为连接线
        if shape_type == 'relation' and ('BeginX' in cells or 'EndX' in cells):
            shape_type = 'connector'
        # 兜底: 任何1D形状(BeginX/EndX存在)无论类型名都按连接线处理
        if shape_type not in ('connector',) and 'BeginX' in cells and 'EndX' in cells \
                and not text_parts:
            shape_type = 'connector'

        rec = {
            'id': sid, 'elem': s, 'cells': cells, 'f_attrs': f_attrs,
            'master_id': resolved_mid, 'master_type': master_nameu,
            'name': inst_name, 'text': text, 'type': shape_type,
            'parent': parent_rec, 'depth': (parent_rec['depth'] + 1) if parent_rec else 0,
            'via_master': master_shape is not None,
            'geometry_rows': merged_geometry_rows(s, master_shape),
        }
        records.append(rec)
        sub = s.find('v:Shapes', NS)
        if sub is not None:
            walk_shapes(sub, rec, mid or parent_master_id, master_store, records)


def parse_page(vz, page_file: str, master_store: MasterStore,
               page_dims: tuple | None, source: str) -> dict | None:
    try:
        root = ET.fromstring(vz.read(page_file).decode('utf-8', errors='replace'))
    except (KeyError, ET.ParseError):
        return None
    shapes_root = root.find('.//v:Shapes', NS)
    if shapes_root is None:
        return None

    pw, ph = page_dims if page_dims else (8.5, 11.0)

    # ── Pass 1: 遍历+继承解析 ──
    records = []
    walk_shapes(shapes_root, None, None, master_store, records)

    # ── Pass 2: 语义节点(顶层Shape成节点; 多文本组爆炸) ──
    nodes, id_to_node = [], {}
    connectors = []
    exploded_ids = set()  # 被爆炸的组的id(其边引用转移到子)
    for rec in records:
        if rec['type'] == 'connector':
            connectors.append(rec)
            continue
        if rec['depth'] > 0:
            continue  # 子形状不独立成节点(默认并入父)
        # 组爆炸: 顶层组有≥2个带文本直接子Shape → 每个子独立成节点
        sub = rec['elem'].find('v:Shapes', NS)
        if sub is not None:
            text_children = []
            for cs in sub.findall('v:Shape', NS):
                ctxt = cs.find('v:Text', NS)
                if ctxt is not None and ''.join(ctxt.itertext()).strip():
                    text_children.append(cs)
            if len(text_children) >= 2:
                exploded_ids.add(rec['id'])
                for cs in text_children:
                    # 子Shape的rec(已在records里, depth=1)
                    cid = cs.get('ID', '')
                    crec = next((r for r in records if r['id'] == cid), None)
                    if crec is None:
                        continue
                    bbox = shape_bbox_page(crec)
                    node = {
                        'id': cid, 'text': crec['text'], 'type': crec['type'],
                        'master_type': crec['master_type'],
                        'via_master': crec['via_master'],
                        'bbox': [round(v, 4) for v in bbox],
                        'cx': round((bbox[0] + bbox[2]) / 2, 4),
                        'cy': round((bbox[1] + bbox[3]) / 2, 4),
                        'w': round(abs(bbox[2] - bbox[0]), 4),
                        'h': round(abs(bbox[3] - bbox[1]), 4),
                        'rx': round(((bbox[0] + bbox[2]) / 2) / pw, 4) if pw else 0,
                        'ry': round(1 - ((bbox[1] + bbox[3]) / 2) / ph, 4) if ph else 0,
                        'exploded_from': rec['id'],
                    }
                    nodes.append(node)
                    id_to_node[cid] = node
                continue  # 组本身不再成节点
        bbox = shape_bbox_page(rec)
        node = {
            'id': rec['id'], 'text': rec['text'], 'type': rec['type'],
            'master_type': rec['master_type'],
            'via_master': rec['via_master'],
            'bbox': [round(v, 4) for v in bbox],
            'cx': round((bbox[0] + bbox[2]) / 2, 4),
            'cy': round((bbox[1] + bbox[3]) / 2, 4),
            'w': round(abs(bbox[2] - bbox[0]), 4),
            'h': round(abs(bbox[3] - bbox[1]), 4),
            'rx': round(((bbox[0] + bbox[2]) / 2) / pw, 4) if pw else 0,
            'ry': round(1 - ((bbox[1] + bbox[3]) / 2) / ph, 4) if ph else 0,
        }
        nodes.append(node)
        id_to_node[rec['id']] = node

    # ── Pass 3: 边重建(三重证据) ──
    # 证据1: Connect记录
    conns = root.findall('.//v:Connect', NS)
    by_connector = {}
    for conn in conns:
        fid = conn.get('FromSheet', '')
        fc = conn.get('FromCell', '')
        tid = conn.get('ToSheet', '')
        if fid not in by_connector:
            by_connector[fid] = {'begin': [], 'end': []}
        if fc.startswith('Begin'):
            by_connector[fid]['begin'].append(tid)
        elif fc.startswith('End'):
            by_connector[fid]['end'].append(tid)

    # 证据3: 粘合公式(从F属性提取Sheet.N) — 供Connect缺失时的边恢复
    glue = {}  # connector_id -> {'begin': shape_id, 'end': shape_id}
    for rec in connectors:
        g = {}
        for side in ('Begin', 'End'):
            fx = rec['f_attrs'].get(f'{side}X', '')
            m = re.search(r'Sheet\.(\d+)!', fx or '')
            if m:
                g[side] = m.group(1)
        if g:
            glue[rec['id']] = g
    glue_emitted = 0  # 实际发出的粘合公式边数

    rec_by_id = {r['id']: r for r in records}

    def node_bbox_dist(px, py, node) -> float:
        x1, y1, x2, y2 = node['bbox']
        dx = max(x1 - px, 0, px - x2)
        dy = max(y1 - py, 0, py - y2)
        return math.hypot(dx, dy)

    SNAP_TH = 0.4
    edges = []
    existing = set()
    used_connectors = set()

    def emit_edge(src_id, dst_id, rec, evidence, waypoints=None):
        key = (src_id, dst_id)
        if key in existing or src_id == dst_id:
            return
        src, dst = id_to_node.get(src_id), id_to_node.get(dst_id)
        if src is None or dst is None:
            return
        existing.add(key)
        # 边标签: 连接线Text + TxtPin位置
        label = rec['text']
        label_pos = None
        tx, ty = f(rec['cells'], 'TxtPinX'), f(rec['cells'], 'TxtPinY')
        if label and (tx or ty):
            lx, ly = to_page(rec, tx, ty)
            label_pos = [round(lx, 3), round(ly, 3)]
        edges.append({
            'src': src_id, 'dst': dst_id,
            'src_text': src['text'], 'dst_text': dst['text'],
            'label': label, 'label_pos': label_pos,
            'connector_id': rec['id'],
            'via': evidence,
            'waypoints': [[round(x, 3), round(y, 3)] for x, y in (waypoints or [])],
        })

    # 3a: Connect记录(权威)
    for cid, ends in by_connector.items():
        used_connectors.add(cid)
        rec = rec_by_id.get(cid)
        if rec is None:
            continue
        begins, endlist = ends['begin'], ends['end']
        if not begins or not endlist:
            continue
        # waypoints: 折线重建
        wp = [to_page(rec, x, y) for x, y in reconstruct_path(rec['geometry_rows'], rec['cells'])]
        for b in begins:
            for e in endlist:
                emit_edge(b, e, rec, 'glued', wp)

    # 3b: 粘合公式(Connect缺失时)
    for cid, g in glue.items():
        if cid in used_connectors:
            continue
        rec = rec_by_id.get(cid)
        if rec is None or 'begin' not in g or 'end' not in g:
            continue
        used_connectors.add(cid)
        wp = [to_page(rec, x, y) for x, y in reconstruct_path(rec['geometry_rows'], rec['cells'])]
        before = len(edges)
        emit_edge(g['begin'], g['end'], rec, 'glue_formula', wp)
        glue_emitted += len(edges) - before

    # 3c: 几何吸附(未粘合: Begin/End端点或折线端点)
    geo_edges = 0
    for rec in connectors:
        if rec['id'] in used_connectors:
            continue
        # 端点: Begin/End(父系坐标→页面系: 过父链变换)
        bx, by = f(rec['cells'], 'BeginX'), f(rec['cells'], 'BeginY')
        ex, ey = f(rec['cells'], 'EndX'), f(rec['cells'], 'EndY')
        # Begin/End在父系 → 直接过父链(不含自身XForm)
        def parent_chain_transform(x, y):
            p = rec.get('parent')
            while p is not None:
                x, y = local_to_parent(x, y, p['cells'])
                p = p.get('parent')
            return x, y
        pbx, pby = parent_chain_transform(bx, by)
        pex, pey = parent_chain_transform(ex, ey)
        # 折线(若能重建, 更准)
        wp_local = reconstruct_path(rec['geometry_rows'], rec['cells'])
        wp = [to_page(rec, x, y) for x, y in wp_local]
        if len(wp) >= 2:
            use_pts = wp
        else:
            use_pts = [(pbx, pby), (pex, pey)]

        def snap(px, py):
            """吸附到最近节点; 平局(同距)时选bbox面积最小者=最具体节点(避免吸到容器框)"""
            cands = []
            for n in nodes:
                d = node_bbox_dist(px, py, n)
                area = abs(n['bbox'][2] - n['bbox'][0]) * abs(n['bbox'][3] - n['bbox'][1])
                cands.append((d, area, n))
            if not cands:
                return None
            cands.sort(key=lambda c: (round(c[0], 4), c[1]))
            return (cands[0][0], cands[0][2])

        best_b = snap(use_pts[0][0], use_pts[0][1])
        best_e = snap(use_pts[-1][0], use_pts[-1][1])
        if not best_b or not best_e:
            continue
        (db, nb), (de, ne) = best_b, best_e
        if db > SNAP_TH or de > SNAP_TH or nb['id'] == ne['id']:
            continue

        # 方向证据2: 箭头Cell
        end_arrow = f(rec['cells'], 'EndArrow')
        begin_arrow = f(rec['cells'], 'BeginArrow')
        if end_arrow > 0 and begin_arrow == 0:
            emit_edge(nb['id'], ne['id'], rec, 'geo_arrow', wp)
        elif begin_arrow > 0 and end_arrow == 0:
            emit_edge(ne['id'], nb['id'], rec, 'geo_arrow_rev', wp)  # 箭头在Begin端
        else:
            emit_edge(nb['id'], ne['id'], rec, 'geo', wp)
        geo_edges += 1

    # ── Pass 3b: 爆炸组的边端点转移 ──
    for e in edges:
        for side in ('src', 'dst'):
            if e[side] in exploded_ids:
                ep = id_to_node.get(e[side])
                # 找该组的孩子节点中最近的
                children = [n for n in nodes if n.get('exploded_from') == e[side]]
                if children and ep:
                    ecx = (ep['bbox'][0] + ep['bbox'][2]) / 2 if ep else 0
                    ecy = (ep['bbox'][1] + ep['bbox'][3]) / 2 if ep else 0
                    # ep是组本身? 组不在nodes里了——用边另一端的位置就近选择
                    other = id_to_node.get(e['dst' if side == 'src' else 'src'])
                    if other:
                        ox = (other['bbox'][0] + other['bbox'][2]) / 2
                        oy = (other['bbox'][1] + other['bbox'][3]) / 2
                        best = min(children, key=lambda c: math.hypot(
                            (c['cx'] - ox), (c['cy'] - oy)))
                        e[side] = best['id']
                        e[f'{side}_text'] = best['text']

    # ── Pass 4: 标签收养 ──
    # UML惯例: actor/形状本体无文本, 文字在旁边的独立标签Shape里
    # 边的无文本端点 → 重定向到最近的文本节点(中心距<1.2英寸)
    text_nodes = [n for n in nodes if n['text']]

    def center(n):
        return ((n['bbox'][0] + n['bbox'][2]) / 2, (n['bbox'][1] + n['bbox'][3]) / 2)

    adopted = 0
    for e in edges:
        for side in ('src', 'dst'):
            ep = id_to_node.get(e[side])
            if ep and not ep['text'] and text_nodes:
                ecx, ecy = center(ep)
                best, bd = None, 1.2
                for tn in text_nodes:
                    tcx, tcy = center(tn)
                    d = math.hypot(ecx - tcx, ecy - tcy)
                    if d < bd:
                        bd, best = d, tn
                if best and best['id'] != e['src' if side == 'dst' else 'dst']:
                    e[side] = best['id']
                    e[f'{side}_text'] = best['text']
                    adopted += 1
    # 去重(收养后可能出现重复边)
    seen, dedup = set(), []
    for e in edges:
        key = (e['src'], e['dst'])
        if key not in seen and e['src'] != e['dst']:
            seen.add(key)
            dedup.append(e)
    edges = dedup

    return {
        'source': source,
        'embed_index': source.split('/')[-1] + ':' + page_file.split('/')[-1],
        'page': {'w': round(pw, 3), 'h': round(ph, 3)},
        'nodes': nodes,
        'edges': edges,
        'meta': {
            'raw_shape_count': len(records),
            'raw_connect_count': len(conns),
            'via_master_shapes': sum(1 for r in records if r['via_master']),
            'glue_formula_connectors': len(glue),
            'glue_formula_edges': glue_emitted,
            'geo_edges': geo_edges, 'label_adopted': adopted,
            'parser': 'm11_full (master继承+嵌套变换+geometry重建+三重方向证据)',
        },
    }


# ═══════════════════════════════════════════════════════════════
# 文档级入口
# ═══════════════════════════════════════════════════════════════

def extract_doc(docx_path: Path) -> list[dict]:
    results = []
    with zipfile.ZipFile(docx_path) as zf:
        embeds = sorted(
            [fp for fp in zf.namelist() if fp.startswith('word/embeddings/')],
            key=lambda x: int(m.group(1)) if (m := re.search(r'(\d+)', x.split('/')[-1])) else 0)
        for embed_path in embeds:
            data = zf.read(embed_path)
            if data[:4].hex() != 'd0cf11e0':
                continue
            try:
                ole = olefile.OleFileIO(io.BytesIO(data))
                streams = ['/'.join(s) for s in ole.listdir()]
                if 'Package' not in streams:
                    ole.close()
                    continue
                pkg = ole.openstream('Package').read()
                ole.close()
                if pkg[:2] != b'PK':
                    continue
                with zipfile.ZipFile(io.BytesIO(pkg)) as vz:
                    # 页面尺寸(pages.xml)
                    page_dims_map = {}
                    try:
                        proot = ET.fromstring(
                            vz.read('visio/pages/pages.xml').decode('utf-8', errors='replace'))
                        rel_map = {}
                        try:
                            rels = vz.read('visio/pages/_rels/pages.xml.rels').decode('utf-8', errors='replace')
                            for m in re.finditer(r'Id="(rId\d+)"[^>]*Target="([^"]+)"', rels):
                                rel_map[m.group(1)] = m.group(2).lstrip('./')
                        except KeyError:
                            pass
                        for page in proot.findall('v:Page', NS):
                            ps = page.find('v:PageSheet', NS)
                            rel = page.find('v:Rel', NS)
                            if ps is None or rel is None:
                                continue
                            rid = rel.get(f'{{{R_NS}}}id', '')
                            target = rel_map.get(rid, '')
                            cells = {c.get('N'): c.get('V') for c in ps.findall('v:Cell', NS)}
                            page_dims_map['visio/pages/' + target] = (
                                float(cells.get('PageWidth', 8.5)),
                                float(cells.get('PageHeight', 11.0)))
                    except KeyError:
                        pass

                    master_store = MasterStore(vz)
                    page_files = [fp for fp in vz.namelist()
                                  if re.match(r'visio/pages/page\d+\.xml$', fp)]
                    for pf in page_files:
                        structure = parse_page(vz, pf, master_store,
                                               page_dims_map.get(pf), embed_path)
                        if structure and (structure['nodes'] or structure['edges']):
                            results.append(structure)
            except Exception:
                continue
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--docs', nargs='*', default=None)
    args = ap.parse_args()

    doc_files = sorted(DOCX_DIR.glob('*.docx'))
    if args.docs:
        doc_files = [d for d in doc_files if any(k in d.stem for k in args.docs)]

    all_anchors = {}
    agg = {'nodes': 0, 'edges': 0, 'via_master': 0, 'geo': 0, 'glue': 0,
           'types': {}, 'via_dist': {}}

    for docx in doc_files:
        structures = extract_doc(docx)
        if not structures:
            continue
        all_anchors[docx.stem] = {'visio_count': len(structures), 'structures': structures}
        dn = sum(len(s['nodes']) for s in structures)
        de = sum(len(s['edges']) for s in structures)
        vm = sum(s['meta']['via_master_shapes'] for s in structures)
        ge = sum(s['meta']['geo_edges'] for s in structures)
        gl = sum(s['meta']['glue_formula_edges'] for s in structures)
        agg['nodes'] += dn
        agg['edges'] += de
        agg['via_master'] += vm
        agg['geo'] += ge
        agg['glue'] += gl
        for s in structures:
            for n in s['nodes']:
                agg['types'][n['type']] = agg['types'].get(n['type'], 0) + 1
                via = 'master' if n['via_master'] else 'local'
                agg['via_dist'][via] = agg['via_dist'].get(via, 0) + 1
        print(f"  ✓ {docx.stem[:30]:32s}: {len(structures):3d}图 "
              f"节点{dn:4d} 边{de:4d} (master继承{vm} 几何边{ge} 粘合公式{gl})")

    out_path = OUT_DIR / "anchors_v2.json"
    out_path.write_text(json.dumps(all_anchors, ensure_ascii=False, indent=1))

    print(f"\n{'='*64}")
    print(f"M11全量: {len(all_anchors)}文档 "
          f"{agg['nodes']}节点 {agg['edges']}边")
    print(f"  master继承形状: {agg['via_master']}")
    print(f"  几何恢复边: {agg['geo']}, 粘合公式边: {agg['glue']}")
    print(f"  节点类型分布: {dict(sorted(agg['types'].items(), key=lambda x: -x[1]))}")
    other_rate = agg['types'].get('other', 0) / max(1, agg['nodes'])
    print(f"  other占比: {other_rate:.1%} (目标<10%)")
    print(f"\n  输出: {out_path}")


if __name__ == "__main__":
    main()
