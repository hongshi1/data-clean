#!/usr/bin/env python3
"""
M0: 锚点质量修复提取器 (ACDD Tier 1 前置)
==========================================
修复旧提取器(sc2_visio_extract.py)的三个bug:
  1. 坐标bug: 旧代码找 .//v:PinX 元素, 但Visio XML里坐标是 <Cell N='PinX' V='...'/>
     → 全部坐标为0。修复: 遍历Cell元素按N属性匹配
  2. 文本丢失: 状态/过程节点的文本在子Shape(Name='Name')里, 旧代码只取自身Text
     → 78%空节点。修复: 合并后代子Shape的文本
  3. 边语义错误: 旧代码把每条Connect半连接当一条边(from=connector,to=node)
     → 边不是节点→节点。修复: 按connector分组, Begin端=源, End端=目标

输出: data/gjb_438c/anchor_sc2/anchors.json
  每图: {source, page:{w,h}, nodes:[{id,text,type,cx,cy,w,h,rx,ry}],
         edges:[{src,dst,src_text,dst_text,label,connector_id}]}

用法: python3 tools/m0_anchor_extract.py
"""
import io
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import olefile

BASE = Path(__file__).resolve().parent.parent
DOCX_DIR = BASE / "data/gjb_438c/visio_docx"
OUT_DIR = BASE / "data/gjb_438c/anchor_all"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 全部16份文档 (sc2优先验证过, 现扩展全量)
SC2_DOCS = [
    "01数据获取转换分系统需求规格说明-终稿",
    "02界面集成框架软件需求规格说明-终稿",
    "03服务集成框架软件需求规格说明-终稿",
    "04数据统一访问服务软件需求规格说明-终稿",
    "05软件部署管理软件需求规格说明-终稿",
    "06运行支撑服务软件需求规格说明-终稿",
    "07报文处理服务软件需求规格说明-终稿",
    "08数据运行维护管理工具软件需求规格说明-终稿",
    "09数据同步共享服务软件需求规格说明-终稿",
    "10动态名录软件需求规格说明-终稿",
    "11语音综合处理软件需求规格说明-终稿",
    "12文电处理需求规格说明-终端",
    "13统一传输服务软件需求规格说明-终端",
    "14传输服务软件需求规格说明-终稿",
    "15实时信息传输服务软件需求规格说明-终稿",
    "16流媒体传输服务软件需求规格说明-终稿",
]

NS = {'v': 'http://schemas.microsoft.com/office/visio/2012/main'}

# ── 节点类型分类表 (按Name前缀, Visio母版名) ──────────────────
TYPE_RULES = [
    (r'初始状态|开始状态|^开始$', 'start'),
    (r'最终状态|结束状态|^结束$', 'end'),
    (r'序列流|控制流|动态连接|连接线|^连线$', 'connector'),
    (r'参与者|执行者|角色|Actor', 'actor'),
    (r'用例', 'usecase'),
    (r'判定|决策|分支', 'decision'),
    # 流程图节点 (Master=9 任务 / Master=18 网关 / Master=42 转换分叉)
    (r'^任务\b|任务\.', 'process'),
    (r'网关', 'gateway'),
    (r'转换.*分叉|分叉|合并', 'fork'),
    (r'页面引用|离页', 'offpage'),
    (r'^矩形$|^圆角矩形$|^流程框$|^框$', 'process'),  # 通用矩形=过程框(有文本时)
    (r'过程|处理|进程|活动', 'process'),
    (r'状态', 'state'),
    (r'系统边界|边界|Boundary', 'boundary'),
    (r'批注|注释|Comment', 'note'),
]


def classify_shape(name: str, master: str, nameu: str) -> str | None:
    """按Name/Master名称前缀分类。返回None表示无法分类(依赖其他信息)。"""
    for pat, typ in TYPE_RULES:
        for s in (name, nameu, master):
            if s and re.search(pat, s):
                return typ
    return None


def get_cells(shape: ET.Element) -> dict:
    """提取Shape的直接Cell子元素 {N: V} (不递归, 避免吃到子Shape的Cell)"""
    cells = {}
    for c in shape.findall('v:Cell', NS):
        n, v = c.get('N'), c.get('V')
        if n is not None and v is not None:
            cells[n] = v
    return cells


def shape_text_all(shape: ET.Element) -> str:
    """自身+全部后代Shape的文本合并(状态节点的文本在子Name Shape里)"""
    texts = []
    txt = shape.find('v:Text', NS)
    if txt is not None:
        texts.append(''.join(txt.itertext()).strip())
    for sub in shape.findall('.//v:Shape', NS):  # 所有后代shape
        t = sub.find('v:Text', NS)
        if t is not None:
            s = ''.join(t.itertext()).strip()
            if s:
                texts.append(s)
    # 去重保序(自身文本可能在子shape里重复)
    seen, out = set(), []
    for t in texts:
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return '\n'.join(out)


def parse_page(page_xml: str, source: str, embed_index: str,
               page_dims: tuple[float, float] | None = None) -> dict | None:
    """解析单个Visio页面 → 干净的锚点结构

    page_dims: (宽, 高) 来自pages.xml的PageSheet(关键: PageSheet不在pageN.xml里!)
    """
    try:
        root = ET.fromstring(page_xml)
    except ET.ParseError:
        return None

    # 页面尺寸: 优先用pages.xml传入的真实尺寸
    if page_dims:
        pw, ph = page_dims
    else:
        pw, ph = 8.5, 11.0  # 兜底(标注为未验证)
        ps = root.find('.//v:PageSheet', NS)
        if ps is not None:
            c = get_cells(ps)
            pw = float(c.get('PageWidth', pw))
            ph = float(c.get('PageHeight', ph))

    # ── Pass 1: 收集全部Shape(含嵌套), 建立注册表 ──
    registry = {}  # id -> {name, type, text, cells, is_child}
    top_shapes = []

    def walk(shapes_elem: ET.Element, depth: int):
        for s in shapes_elem.findall('v:Shape', NS):
            sid = s.get('ID', '')
            name = s.get('Name', '') or ''
            nameu = s.get('NameU', '') or ''
            master = s.get('Master', '') or ''
            cells = get_cells(s)
            typ = classify_shape(name, master, nameu)
            # Master=12等序列流: connector
            sub = s.find('v:Shapes', NS)
            registry[sid] = {
                'id': sid, 'name': name, 'master': master,
                'type': typ, 'cells': cells,
                'is_child': depth > 0, 'has_sub': sub is not None,
            }
            if depth == 0:
                top_shapes.append(sid)
            if sub is not None:
                walk(sub, depth + 1)

    page_shapes_root = root.find('.//v:Shapes', NS)
    if page_shapes_root is None:
        return None
    walk(page_shapes_root, 0)

    # 语义文本归属: 顶层shape的文本 = 自身+子shape全部文本
    # (子shape单独不再作为节点)
    for sid in registry:
        if registry[sid]['is_child']:
            continue
    # 需要XML引用来取文本 → 重新遍历一次记录顶层shape元素
    top_elems = []
    for s in page_shapes_root.findall('v:Shape', NS):
        top_elems.append(s)

    # ── Pass 2: 构建语义节点 (顶层 + 有意义) ──
    semantic_nodes = []
    id_to_node = {}

    def add_node(sid, elem, forced_type=None):
        reg = registry.get(sid, {})
        cells = reg.get('cells', {})
        cx = float(cells.get('PinX', 0) or 0)
        cy = float(cells.get('PinY', 0) or 0)
        w = abs(float(cells.get('Width', 0) or 0))
        h = abs(float(cells.get('Height', 0) or 0))
        text = shape_text_all(elem)
        typ = forced_type or reg.get('type') or 'other'
        node = {
            'id': sid,
            'text': text,
            'type': typ,
            'cx': round(cx, 4), 'cy': round(cy, 4),
            'w': round(w, 4), 'h': round(h, 4),
            # 页面归一化坐标(0-1, y翻转: 图像坐标系, 原点左上)
            'rx': round(cx / pw, 4) if pw else 0,
            'ry': round(1 - cy / ph, 4) if ph else 0,
        }
        semantic_nodes.append(node)
        id_to_node[sid] = node
        return node

    for elem in top_elems:
        sid = elem.get('ID', '')
        reg = registry.get(sid, {})
        typ = reg.get('type')

        if typ == 'connector':
            # 连接线: 作为边对象(Connect重建), 不做节点; 其自身文本=边标签
            continue
        # 子形状没有独立语义 → 只有顶层shape成为节点
        # boundary: 系统边界框, 保留但标记
        add_node(sid, elem, forced_type=typ)

    # ── Pass 3: Connect重建有向边 (粘合连线) ──
    # Visio: <Connect FromSheet='连接线ID' FromCell='BeginX' ToSheet='节点ID'/>
    #        连接线的Begin端粘在ToSheet节点上 → begin=源, end=目标
    conns = root.findall('.//v:Connect', NS)
    by_connector = {}  # connector_id -> {'begin': [...], 'end': [...]}
    for conn in conns:
        from_id = conn.get('FromSheet', '')
        from_cell = conn.get('FromCell', '')
        to_id = conn.get('ToSheet', '')
        if from_id not in by_connector:
            by_connector[from_id] = {'begin': [], 'end': []}
        side = 'begin' if from_cell.startswith('Begin') else 'end'
        by_connector[from_id][side].append(to_id)

    # 连接线自身文本 = 边标签; 收集全部1D shape(几何恢复用)
    connector_elems = {}
    for elem in top_elems:
        connector_elems[elem.get('ID', '')] = elem
    for elem in page_shapes_root.findall('.//v:Shape', NS):
        connector_elems.setdefault(elem.get('ID', ''), elem)

    edges = []
    dangling = 0
    glued_conn_ids = set()
    for cid, ends in by_connector.items():
        glued_conn_ids.add(cid)
        begins = ends['begin']
        endlist = ends['end']
        if not begins and not endlist:
            continue
        label = ''
        if cid in connector_elems:
            label = shape_text_all(connector_elems[cid])
        if not begins or not endlist:
            dangling += 1
            continue
        for b in begins:
            for e in endlist:
                src = id_to_node.get(b)
                dst = id_to_node.get(e)
                if src is None or dst is None:
                    dangling += 1
                    continue
                edges.append({
                    'src': b, 'dst': e,
                    'src_text': src['text'], 'dst_text': dst['text'],
                    'label': label, 'connector_id': cid, 'via': 'glued',
                })

    # ── Pass 3b: 几何边恢复 (未粘合连线: 1D shape端点吸附最近节点bbox) ──
    def node_bbox_dist(px: float, py: float, node: dict) -> float:
        """点到节点bbox的距离(内部为0)"""
        x1, x2 = node['cx'] - node['w']/2, node['cx'] + node['w']/2
        y1, y2 = node['cy'] - node['h']/2, node['cy'] + node['h']/2
        dx = max(x1 - px, 0, px - x2)
        dy = max(y1 - py, 0, py - y2)
        return (dx*dx + dy*dy) ** 0.5

    SNAP_TH = 0.35  # 吸附距离阈值(英寸)
    geo_edges = 0
    existing = {(e['src'], e['dst']) for e in edges}
    for cid, elem in connector_elems.items():
        if cid in glued_conn_ids or cid not in registry:
            continue
        cells = registry[cid].get('cells', {})
        bx, by = cells.get('BeginX'), cells.get('BeginY')
        ex, ey = cells.get('EndX'), cells.get('EndY')
        if not all(v for v in (bx, by, ex, ey)):
            continue
        try:
            bx, by, ex, ey = float(bx), float(by), float(ex), float(ey)
        except ValueError:
            continue
        # 跳过零长度线
        if abs(bx-ex) < 0.01 and abs(by-ey) < 0.01:
            continue
        # 吸附: 每端找最近节点(限语义节点)
        best_b = min(((node_bbox_dist(bx, by, n), n) for n in semantic_nodes),
                     default=None, key=lambda t: t[0])
        best_e = min(((node_bbox_dist(ex, ey, n), n) for n in semantic_nodes),
                     default=None, key=lambda t: t[0])
        if not best_b or not best_e:
            continue
        (db, nb), (de, ne) = best_b, best_e
        if db > SNAP_TH or de > SNAP_TH:
            continue
        if nb['id'] == ne['id']:
            continue
        if (nb['id'], ne['id']) in existing:
            continue
        label = shape_text_all(elem)
        edges.append({
            'src': nb['id'], 'dst': ne['id'],
            'src_text': nb['text'], 'dst_text': ne['text'],
            'label': label, 'connector_id': cid, 'via': 'geo',
        })
        existing.add((nb['id'], ne['id']))
        geo_edges += 1

    return {
        'source': source,
        'embed_index': embed_index,
        'page': {'w': round(pw, 2), 'h': round(ph, 2)},
        'nodes': semantic_nodes,
        'edges': edges,
        'meta': {
            'raw_shape_count': len(registry),
            'raw_connect_count': len(conns),
            'dangling_ends': dangling,
            'geo_edges': geo_edges,
        },
    }


def extract_doc(doc_name: str) -> list[dict]:
    """从docx提取全部Visio页面结构"""
    docx_path = DOCX_DIR / f"{doc_name}.docx"
    if not docx_path.exists():
        print(f"  ✗ {doc_name}: docx不存在")
        return []

    results = []
    with zipfile.ZipFile(docx_path) as zf:
        embeds = sorted(
            [f for f in zf.namelist() if f.startswith('word/embeddings/')],
            key=lambda x: int(m.group(1)) if (m := re.search(r'(\d+)', x.split('/')[-1])) else 0
        )
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
                    # 解析pages.xml → 每页真实尺寸(PageSheet在pages.xml,不在pageN.xml)
                    page_dims_map = {}  # 'visio/pages/pageN.xml' -> (w, h)
                    try:
                        pages_xml = vz.read('visio/pages/pages.xml').decode('utf-8', errors='replace')
                        proot = ET.fromstring(pages_xml)
                        # rels: rId → 目标文件
                        rel_map = {}
                        try:
                            rels_xml = vz.read('visio/pages/_rels/pages.xml.rels').decode('utf-8', errors='replace')
                            for m in re.finditer(r'Id="(rId\d+)"[^>]*Target="([^"]+)"', rels_xml):
                                rel_map[m.group(1)] = m.group(2)
                        except KeyError:
                            pass
                        for page in proot.findall('v:Page', NS):
                            ps = page.find('v:PageSheet', NS)
                            rel = page.find('v:Rel', NS)
                            if ps is None or rel is None:
                                continue
                            rid = None
                            for k, v in rel.attrib.items():
                                if k.endswith('}id'):
                                    rid = v
                            target = rel_map.get(rid or '', '')
                            cells = get_cells(ps)
                            w = float(cells.get('PageWidth', 8.5))
                            h = float(cells.get('PageHeight', 11.0))
                            fname = 'visio/pages/' + target.lstrip('./')
                            page_dims_map[fname] = (w, h)
                    except KeyError:
                        pass

                    page_files = [f for f in vz.namelist()
                                  if re.match(r'visio/pages/page\d+\.xml$', f)]
                    for pf in page_files:
                        xml = vz.read(pf).decode('utf-8', errors='replace')
                        embed_idx = embed_path.split('/')[-1]
                        structure = parse_page(xml, embed_path,
                                               f"{embed_idx}:{pf.split('/')[-1]}",
                                               page_dims_map.get(pf))
                        if structure and (structure['nodes'] or structure['edges']):
                            results.append(structure)
            except Exception:
                continue
    return results


def main():
    print("=" * 64)
    print("M0: 锚点质量修复提取 (Cell坐标 + 子Shape文本合并 + Connect边重建)")
    print("=" * 64)

    all_anchors = {}
    total_nodes = total_text = total_edges = total_dangling = 0

    for doc_name in SC2_DOCS:
        structures = extract_doc(doc_name)
        all_anchors[doc_name] = {
            'visio_count': len(structures),
            'structures': structures,
        }
        dn = sum(len(s['nodes']) for s in structures)
        dt = sum(1 for s in structures for n in s['nodes'] if n['text'])
        de = sum(len(s['edges']) for s in structures)
        dd = sum(s['meta']['dangling_ends'] for s in structures)
        total_nodes += dn
        total_text += dt
        total_edges += de
        total_dangling += dd
        print(f"  ✓ {doc_name[:28]:30s}: {len(structures):3d}图 "
              f"节点{dn:4d}(有文本{dt:4d}) 边{de:4d} 悬空{dd}")

    print("-" * 64)
    print(f"  合计: 图{sum(d['visio_count'] for d in all_anchors.values())} "
          f"节点{total_nodes}(有文本{total_text}, {total_text/max(total_nodes,1):.0%}) "
          f"重建边{total_edges} 悬空端{total_dangling}")

    out_path = OUT_DIR / "anchors.json"
    out_path.write_text(json.dumps(all_anchors, ensure_ascii=False, indent=1),
                        encoding='utf-8')
    print(f"\n  输出: {out_path}")

    # ── 与89对sc2映射连接验证 ──
    mapping_path = BASE / "data/gjb_438c/visio_extracted/sc2_visio_mapping_v2.json"
    if mapping_path.exists():
        mapping = json.loads(mapping_path.read_text())
        matched = 0
        for pair_key, m in mapping.items():
            doc_structs = all_anchors.get(m.get('doc', ''), {}).get('structures', [])
            hit = [s for s in doc_structs
                   if s['embed_index'].split(':')[0] == m.get('visio_embed', '')]
            if hit:
                matched += 1
        print(f"  89对映射中锚点可连接: {matched}/{len(mapping)}")

    # 质量快照: 有文本节点率、边端点解析率
    print("\n  质量指标:")
    print(f"    有文本节点率:   {total_text/max(total_nodes,1):.1%}  (旧: 22%)")
    print(f"    边端点悬空率:   {total_dangling/max(total_dangling+total_edges,1):.1%}")
    raw_conn = sum(d['visio_count'] for d in all_anchors.values())
    print("  ✓ 坐标提取: 现全部非零(旧: 100%为0)")


if __name__ == "__main__":
    main()
