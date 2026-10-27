#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""悬空连线端点几何恢复 (1_007型丢边的解析层修复).

M0边重建的两处遗漏(本工具修复):
  1. 半粘连连线(begin有Connect而end无) → 整条被丢弃
  2. 这些线又因 glued_conn_ids 被排除在几何恢复之外 → 双重遗漏
恢复方法: 重读原始Visio XML, 对半粘连连线用其自身几何端点
(BeginX/EndX Cell)把自由端吸附到最近语义节点(点到bbox距离).

输出: data/gjb_438c/anchor_v2/recovered_edges.json
  {export_key: [{src,dst,src_text,dst_text,connector_id,
                 free_end:[x,y],distance,via:'dangling_snap'}]}
原则: canonical锚点不动 — 恢复边只并入投影层(export_pair_views消费),
      每条带距离证据, 阈值外的不猜.

用法: python tools/recover_dangling_edges.py [--debug 1_007] [--snap 0.5]
"""
import argparse
import io
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import olefile

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "tools"))
DOCX_DIR = BASE / "data/gjb_438c/visio_docx"
PAIR_ROOT = BASE / "data/gjb_438c/pair_dataset"
ANCHOR_V2 = BASE / "data/gjb_438c/anchor_v2/anchors_v2.json"
OUT_PATH = BASE / "data/gjb_438c/anchor_v2/recovered_edges.json"

NS = {'v': 'http://schemas.microsoft.com/office/visio/2012/main'}

SNAP_TH = 0.5  # 吸附阈值(英寸): 自由端到语义节点bbox的距离上限


# ═══════════════════════════════════════════════════════════════
# 原始XML读取(docx → OLE → Package → visio zip, 同m0链路)
# ═══════════════════════════════════════════════════════════════

_docx_cache: dict[str, dict[str, bytes]] = {}  # doc_name -> {page_file: xml}


def _load_doc_pages(doc_name: str) -> dict[str, bytes]:
    """docx → {visio/pages/pageN.xml: xml文本} (跨embed合并, 按embed文件名空间)."""
    if doc_name in _docx_cache:
        return _docx_cache[doc_name]
    pages: dict[str, bytes] = {}
    docx_path = DOCX_DIR / f"{doc_name}.docx"
    if not docx_path.exists():
        _docx_cache[doc_name] = pages
        return pages
    with zipfile.ZipFile(docx_path) as zf:
        embeds = sorted(
            [f for f in zf.namelist() if f.startswith('word/embeddings/')],
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
                    embed_tag = embed_path.split('/')[-1].split('.')[0]
                    for f in vz.namelist():
                        if re.match(r'visio/pages/page\d+\.xml$', f):
                            # 命名空间隔离: oleObject7_page1.xml
                            pages[f"{embed_tag}::{f.split('/')[-1]}"] = vz.read(f)
            except Exception:
                continue
    _docx_cache[doc_name] = pages
    return pages


def _get_cells(shape: ET.Element) -> dict:
    cells = {}
    for c in shape.findall('v:Cell', NS):
        n, v = c.get('N'), c.get('V')
        if n is not None and v is not None:
            cells[n] = v
    return cells


def parse_page_raw(xml: bytes) -> tuple[dict, list]:
    """原始page XML → (shape注册表{id: {cells,text}}, Connect记录列表)."""
    root = ET.fromstring(xml)
    registry: dict[str, dict] = {}
    for shape in root.findall('.//v:Shape', NS):
        sid = shape.get('ID', '')
        if not sid:
            continue
        cells = _get_cells(shape)
        txt = ''
        t = shape.find('v:Text', NS)
        if t is not None:
            txt = ''.join(t.itertext()).strip()
        # 子shape文本合并(m0同款: 文本常在子Shape)
        for sub in shape.findall('.//v:Shape', NS):
            st = sub.find('v:Text', NS)
            if st is not None:
                s = ''.join(st.itertext()).strip()
                if s and s not in txt:
                    txt = (txt + '\n' + s).strip('\n')
        if sid not in registry:  # 外层优先
            registry[sid] = {'cells': cells, 'text': txt}
    connects = [{'from': c.get('FromSheet', ''), 'cell': c.get('FromCell', ''),
                 'to': c.get('ToSheet', '')}
                for c in root.findall('.//v:Connect', NS)]
    return registry, connects


# ═══════════════════════════════════════════════════════════════
# 恢复核心
# ═══════════════════════════════════════════════════════════════

def _bbox_dist(px: float, py: float, node: dict) -> float:
    x1, x2 = node['cx'] - node['w'] / 2, node['cx'] + node['w'] / 2
    y1, y2 = node['cy'] - node['h'] / 2, node['cy'] + node['h'] / 2
    dx = max(x1 - px, 0, px - x2)
    dy = max(y1 - py, 0, py - y2)
    return (dx * dx + dy * dy) ** 0.5


def recover_edges(anchor: dict, registry: dict, connects: list,
                  snap_th: float, debug: bool = False) -> list[dict]:
    """半粘连连线 → 恢复边(带距离证据). 只新增, 不重复canonical已有边."""
    nodes = {n['id']: n for n in anchor.get('nodes', [])}
    # 吸附目标: 有文本且非boundary的语义节点
    # (1_007教训: 自由端落在boundary大框内→吸到框上dist=0, 3条边折叠成1条错误边;
    #  连线的视觉终点是用例椭圆/参与者, boundary不是连线目标)
    semantic = [n for n in anchor.get('nodes', [])
                if (n.get('text') or '').strip()
                and n.get('type') != 'boundary']
    existing = {(e['src'], e['dst']) for e in anchor.get('edges', [])}
    existing |= {(e['dst'], e['src']) for e in anchor.get('edges', [])}

    by_connector: dict[str, dict] = {}
    for c in connects:
        rec = by_connector.setdefault(c['from'], {'begin': [], 'end': []})
        side = 'begin' if c['cell'].startswith('Begin') else 'end'
        rec[side].append(c['to'])

    recovered: list[dict] = []
    for cid, ends in by_connector.items():
        begins, endl = ends['begin'], ends['end']
        if begins and endl:
            continue  # 双端粘连: m0已重建(或粘在非语义节点上, 由下面的
                      # 端点吸附路径统一处理——此处先保守只处理半粘连)
        cells = registry.get(cid, {}).get('cells', {})
        bx, by = cells.get('BeginX'), cells.get('BeginY')
        ex, ey = cells.get('EndX'), cells.get('EndY')
        if not all(v for v in (bx, by, ex, ey)):
            continue
        try:
            bx, by, ex, ey = float(bx), float(by), float(ex), float(ey)
        except ValueError:
            continue
        # 粘住端 → 锚点语义节点; 自由端 → 几何吸附
        if begins:
            glued_ids = [nodes[b] for b in begins if b in nodes]
            if not glued_ids:
                continue
            glued = glued_ids[0]
            free_x, free_y = ex, ey
            free_from_begin = False
        elif endl:
            glued_ids = [nodes[e] for e in endl if e in nodes]
            if not glued_ids:
                continue
            glued = glued_ids[0]
            free_x, free_y = bx, by
            free_from_begin = True
        else:
            continue
        # 自由端吸附最近语义节点(排除粘住端自身)
        best = None
        for n in semantic:
            if n['id'] == glued['id']:
                continue
            d = _bbox_dist(free_x, free_y, n)
            if best is None or d < best[0]:
                best = (d, n)
        if best is None or best[0] > snap_th:
            if debug:
                print(f"    [skip] conn {cid}: 自由端({free_x:.2f},{free_y:.2f})"
                      f"最近距离={None if best is None else f'{best[0]:.2f}'}"
                      f" > {snap_th}")
            continue
        d, target = best
        # 方向: m0约定 begin=源, end=目标
        src, dst = (target, glued) if free_from_begin else (glued, target)
        if (src['id'], dst['id']) in existing:
            continue
        edge = {
            'src': src['id'], 'dst': dst['id'],
            'src_text': (src.get('text') or '')[:30],
            'dst_text': (dst.get('text') or '')[:30],
            'connector_id': cid,
            'free_end': [round(free_x, 3), round(free_y, 3)],
            'distance': round(d, 3),
            'via': 'dangling_snap',
        }
        recovered.append(edge)
        existing.add((src['id'], dst['id']))
        if debug:
            print(f"    [recover] conn {cid}: {edge['src_text']} -> "
                  f"{edge['dst_text']} (自由端({free_x:.2f},{free_y:.2f})"
                  f" 吸附距离={d:.2f})")
    return recovered


# ═══════════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════════

def build_anchor_index() -> dict[tuple[str, str], dict]:
    """(doc, embed_base) → 最佳structure(m16同款: 文本节点最多)."""
    data = json.loads(ANCHOR_V2.read_text(encoding='utf-8'))
    idx: dict[tuple[str, str], dict] = {}
    for doc, d in data.items():
        for s in d.get('structures', []):
            key = (doc, s['embed_index'].split(':')[0])
            tn = sum(1 for n in s.get('nodes', []) if n.get('text'))
            if key not in idx or tn > sum(1 for n in idx[key].get('nodes', [])
                                          if n.get('text')):
                idx[key] = s
    return idx


def pair_targets(debug_pair: str = '') -> list[tuple[str, str, str]]:
    """[(pair_id, doc, embed_index)] (debug_pair限定时只跑该对)."""
    out = []
    for scene_dir in sorted(PAIR_ROOT.iterdir()):
        if not scene_dir.is_dir():
            continue
        for pd in sorted(scene_dir.iterdir()):
            va = pd / 'visio_anchor.json'
            if not va.exists():
                continue
            a = json.loads(va.read_text(encoding='utf-8'))
            doc, embed = a.get('doc', ''), a.get('embed_index', '')
            if doc and embed:
                out.append((pd.name, doc, embed))
    if debug_pair:
        out = [t for t in out if t[0] == debug_pair]
    return out


def main() -> int:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser(description="悬空连线端点几何恢复")
    ap.add_argument('--debug', default='', help='只跑指定pair并打印细节')
    ap.add_argument('--snap', type=float, default=SNAP_TH)
    args = ap.parse_args()

    anchor_idx = build_anchor_index()
    targets = pair_targets(args.debug)
    result: dict[str, list] = {}
    n_recovered = n_pairs_hit = 0
    for pair_id, doc, embed in targets:
        pages = _load_doc_pages(doc)
        embed_full, page_file = embed.split(':')[0], embed.split(':')[1]
        pages_key = f"{embed_full.split('.')[0]}::{page_file}"  # oleObject7::page1.xml
        xml = pages.get(pages_key)
        if xml is None:
            continue
        anchor = anchor_idx.get((doc, embed_full))  # 索引键带.bin
        if anchor is None:
            continue
        registry, connects = parse_page_raw(xml)
        rec = recover_edges(anchor, registry, connects, args.snap,
                            debug=bool(args.debug))
        if rec:
            export_key = f"{doc[:8]}:{embed}"
            result[export_key] = rec
            n_pairs_hit += 1
            n_recovered += len(rec)
            if args.debug:
                print(f"  {pair_id}: 恢复{len(rec)}条")
    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=1),
                        encoding='utf-8')
    n_edges_total = sum(len(v) for v in result.values())
    print(f"悬空端点恢复: {n_edges_total}条边 / {len(result)}个图"
          f" (按export_key去重; pair级计数含共享锚点重复) → {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
