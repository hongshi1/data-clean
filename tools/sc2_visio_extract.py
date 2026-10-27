#!/usr/bin/env python3
"""
M1: Visio源提取与映射
=======================
从5份SRS文档的docx中提取Visio嵌入 → 解析为结构化图 → 映射到pair_dataset

流程:
  1. .doc → LibreOffice → .docx
  2. docx → word/embeddings/*.bin (OLE2)
  3. OLE2 Package流 → Visio ZIP
  4. visio/pages/page1.xml → Shape/Text/Connect
  5. → networkx-style图结构(JSON)
  6. 与pair_dataset/sc2_flowchart_usecase映射

用法: python3 tools/sc2_visio_extract.py
"""
import re
import json
import zipfile
import io
import subprocess
from pathlib import Path
from xml.etree import ElementTree as ET

BASE = Path(__file__).resolve().parent.parent
DOC_DIR = BASE / "data/软件需归样例数据集"
DOCX_DIR = BASE / "data/gjb_438c/visio_docx"
DOCX_DIR.mkdir(parents=True, exist_ok=True)
PAIR_DIR = BASE / "data/gjb_438c/pair_dataset/sc2_flowchart_usecase"
OUTPUT_DIR = BASE / "data/gjb_438c/visio_extracted"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# sc2涉及的5份文档
SC2_DOCS = [
    "02界面集成框架软件需求规格说明-终稿",
    "04数据统一访问服务软件需求规格说明-终稿",
    "07报文处理服务软件需求规格说明-终稿",
    "09数据同步共享服务软件需求规格说明-终稿",
    "12文电处理需求规格说明-终端",
]

NS = {'v': 'http://schemas.microsoft.com/office/visio/2012/main'}


def doc_to_docx(doc_name: str) -> Path:
    """Step 1: .doc → .docx (LibreOffice)"""
    src = DOC_DIR / f"{doc_name}.doc"
    dst = DOCX_DIR / f"{doc_name}.docx"
    if dst.exists():
        return dst
    subprocess.run(
        ['soffice', '--headless', '--convert-to', 'docx',
         '--outdir', str(DOCX_DIR), str(src)],
        capture_output=True, timeout=120
    )
    return dst if dst.exists() else None


def extract_visio_from_docx(docx_path: Path) -> list[dict]:
    """Step 2-4: docx → OLE2 → Visio ZIP → page1.xml → 结构"""
    try:
        import olefile
    except ImportError:
        subprocess.run(['pip3', 'install', 'olefile', '--break-system-packages'],
                      capture_output=True)
        import olefile

    results = []

    with zipfile.ZipFile(docx_path) as zf:
        embeds = sorted(
            [f for f in zf.namelist() if f.startswith('word/embeddings/')],
            key=lambda x: int(re.search(r'(\d+)', x.split('/')[-1]).group(1)) if re.search(r'(\d+)', x) else 0
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

                pkg_data = ole.openstream('Package').read()
                ole.close()

                if pkg_data[:2] != b'PK':
                    continue

                with zipfile.ZipFile(io.BytesIO(pkg_data)) as vz:
                    visio_files = vz.namelist()
                    if not any(f.startswith('visio/') for f in visio_files):
                        continue

                    # 找page XML
                    page_files = [f for f in visio_files
                                  if f.startswith('visio/pages/page') and f.endswith('.xml')
                                  and 'rels' not in f and 'pages.xml' not in f]
                    if not page_files:
                        continue

                    # 解析第一个page
                    page_xml = vz.read(page_files[0]).decode('utf-8', errors='replace')
                    structure = parse_visio_page(page_xml, embed_path)

                    if structure and (structure['nodes'] or structure['edges']):
                        structure['embed_index'] = embed_path.split('/')[-1]
                        results.append(structure)

            except Exception:
                continue

    return results


def parse_visio_page(page_xml: str, source: str) -> dict:
    """Step 4: 解析page1.xml → 节点+边"""
    try:
        root = ET.fromstring(page_xml)
    except ET.ParseError:
        return None

    # 提取Shape(节点)
    nodes = []
    all_shapes = root.findall('.//v:Shape', NS)

    for shape in all_shapes:
        sid = shape.get('ID', '')
        sname = shape.get('Name', '')

        # 提取文本
        text_elem = shape.find('v:Text', NS)
        text = ''
        if text_elem is not None:
            text = ''.join(text_elem.itertext()).strip()

        # 提取位置
        pinx = shape.find('.//v:PinX', NS)
        piny = shape.find('.//v:PinY', NS)
        pos_x = float(pinx.text) if pinx is not None else 0.0
        pos_y = float(piny.text) if piny is not None else 0.0

        # 分类节点类型
        if '参与者' in sname:
            node_type = 'actor'
        elif '用例' in sname:
            node_type = 'usecase'
        elif '系统边界' in sname or '边界' in sname:
            node_type = 'boundary'
        elif '归纳' in sname or 'include' in sname.lower() or 'extend' in sname.lower():
            node_type = 'relation'
        else:
            node_type = 'other'

        nodes.append({
            'id': sid,
            'name': sname,
            'type': node_type,
            'text': text,
            'x': pos_x,
            'y': pos_y,
        })

    # 提取Connect(边)
    edges = []
    all_connects = root.findall('.//v:Connect', NS)

    # 构建shape_id→text映射用于边标注
    id_to_text = {n['id']: n['text'] for n in nodes if n['text']}

    for conn in all_connects:
        from_id = conn.get('FromSheet', '')
        to_id = conn.get('ToSheet', '')
        from_cell = conn.get('FromCell', '')
        to_cell = conn.get('ToCell', '')

        edges.append({
            'from_id': from_id,
            'to_id': to_id,
            'from_text': id_to_text.get(from_id, ''),
            'to_text': id_to_text.get(to_id, ''),
            'from_cell': from_cell,
            'to_cell': to_cell,
        })

    return {
        'source': source,
        'node_count': len(nodes),
        'edge_count': len(edges),
        'nodes': nodes,
        'edges': edges,
    }


def extract_pair_dataset_info() -> dict:
    """加载pair_dataset的meta信息用于映射"""
    pairs = {}
    for sample_dir in sorted(PAIR_DIR.iterdir()):
        meta_path = sample_dir / 'meta.json'
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            meta['_dir'] = sample_dir.name
            pairs[sample_dir.name] = meta
    return pairs


def build_mapping(visio_structures: dict, pair_info: dict) -> dict:
    """
    Step 5: 建立Visio结构 → pair_dataset样本的映射

    策略: 内容匹配(非顺序匹配)
    1. 按文档分组
    2. 对每个pair样本, 计算Visio嵌入与table.csv步骤的文本匹配度
    3. 选择匹配度最高的Visio嵌入
    """
    mapping = {}

    for doc_name, structures in visio_structures.items():
        doc_pairs = {k: v for k, v in pair_info.items() if v.get('doc') == doc_name}
        if not doc_pairs or not structures:
            continue

        # 为每个pair样本找最佳匹配的Visio嵌入
        used_visio = set()  # 避免一个Visio被多个pair使用

        for pair_key in sorted(doc_pairs.keys()):
            pair_meta = doc_pairs[pair_key]
            pair_dir = PAIR_DIR / pair_meta['_dir']
            table_path = pair_dir / 'table.csv'

            # 读取table.csv的主事件流步骤
            table_text = ''
            if table_path.exists():
                table_text = table_path.read_text(encoding='utf-8')

            # 提取table中的步骤关键词
            table_keywords = set()
            for line in table_text.split('\n'):
                # 去除编号前缀
                clean = re.sub(r'^\d+[\.．、]\s*', '', line.strip())
                if len(clean) > 5:
                    # 提取中文关键词(2-8字)
                    for kw in re.findall(r'[\u4e00-\u9fa5]{2,8}', clean):
                        table_keywords.add(kw)

            # 也加入func_names
            for fn in pair_meta.get('func_names', []):
                if len(fn) >= 2:
                    table_keywords.add(fn)

            # 计算每个Visio嵌入的匹配度
            best_match = None
            best_score = 0.0

            for i, structure in enumerate(structures):
                if i in used_visio:
                    continue

                visio_texts = [n['text'] for n in structure['nodes'] if n['text']]
                if not visio_texts:
                    continue

                # 计算关键词覆盖: Visio节点文本中有多少关键词被table覆盖
                
                # 方法1: Visio节点文本在table中出现
                matched_nodes = 0
                for vt in visio_texts:
                    vt_clean = vt.strip()
                    if len(vt_clean) >= 3:
                        # 检查visio文本的关键片段是否在table中
                        vt_keywords = re.findall(r'[\u4e00-\u9fa5]{2,6}', vt_clean)
                        if vt_keywords:
                            hits = sum(1 for kw in vt_keywords if kw in table_text)
                            if hits >= len(vt_keywords) * 0.3:
                                matched_nodes += 1

                score = matched_nodes / max(1, len(visio_texts))

                if score > best_score:
                    best_score = score
                    best_match = (i, structure)

            if best_match and best_score > 0.1:
                i, structure = best_match
                used_visio.add(i)

                visio_texts = [n['text'] for n in structure['nodes'] if n['text']]
                func_names = set(pair_meta.get('func_names', []))
                visio_set = set(visio_texts)
                func_overlap = len(visio_set & func_names)

                mapping[pair_key] = {
                    'pair_dir': pair_meta['_dir'],
                    'doc': doc_name,
                    'section': pair_meta.get('section', ''),
                    'image_caption': pair_meta.get('image_caption', ''),
                    'visio_index': i,
                    'visio_embed': structure.get('embed_index', ''),
                    'match_score': round(best_score, 3),
                    'matched_nodes': sum(1 for vt in visio_texts
                                         if any(kw in table_text for kw in re.findall(r'[\u4e00-\u9fa5]{2,6}', vt))),
                    'total_visio_text_nodes': len(visio_texts),
                    'func_overlap': func_overlap,
                    'visio_nodes': len(structure['nodes']),
                    'visio_edges': len(structure['edges']),
                    'structure': structure,
                }
            elif best_match:
                # 匹配度太低, 仍然记录但标注
                i, structure = best_match
                mapping[pair_key] = {
                    'pair_dir': pair_meta['_dir'],
                    'doc': doc_name,
                    'section': pair_meta.get('section', ''),
                    'image_caption': pair_meta.get('image_caption', ''),
                    'visio_index': i,
                    'visio_embed': structure.get('embed_index', ''),
                    'match_score': round(best_score, 3),
                    'matched_nodes': 0,
                    'total_visio_text_nodes': len([n['text'] for n in structure['nodes'] if n['text']]),
                    'func_overlap': 0,
                    'visio_nodes': len(structure['nodes']),
                    'visio_edges': len(structure['edges']),
                    'structure': structure,
                }

    return mapping


def main():
    print("=" * 60)
    print("M1: Visio源提取与映射")
    print("=" * 60)

    # Step 1: 转换docx
    print("\n[1] 转换 .doc → .docx")
    for doc_name in SC2_DOCS:
        docx_path = doc_to_docx(doc_name)
        status = "✓" if docx_path and docx_path.exists() else "✗"
        print(f"  {status} {doc_name[:30]}")

    # Step 2-4: 提取Visio结构
    print("\n[2] 提取Visio结构")
    all_visio = {}
    for doc_name in SC2_DOCS:
        docx_path = DOCX_DIR / f"{doc_name}.docx"
        if not docx_path.exists():
            print(f"  ✗ {doc_name[:30]} (docx不存在)")
            continue

        structures = extract_visio_from_docx(docx_path)
        all_visio[doc_name] = structures
        total_nodes = sum(s['node_count'] for s in structures)
        total_edges = sum(s['edge_count'] for s in structures)
        print(f"  ✓ {doc_name[:30]}: {len(structures)}个Visio, "
              f"{total_nodes}节点, {total_edges}边")

    # Step 5: 加载pair_dataset并映射
    print("\n[3] 建立映射")
    pair_info = extract_pair_dataset_info()
    print(f"  pair_dataset样本: {len(pair_info)}")

    mapping = build_mapping(all_visio, pair_info)
    mapped = sum(1 for v in mapping.values() if v['match_score'] > 0)
    avg_score = sum(v['match_score'] for v in mapping.values()) / max(1, len(mapping))
    print(f"  映射样本: {len(mapping)}")
    print(f"  有文本匹配: {mapped}")
    print(f"  平均匹配度: {avg_score:.1%}")

    # Step 6: 保存
    print("\n[4] 保存结果")

    # 保存Visio结构(不含映射)
    visio_output = {}
    for doc_name, structures in all_visio.items():
        visio_output[doc_name] = {
            'visio_count': len(structures),
            'structures': structures,
        }
    visio_path = OUTPUT_DIR / "visio_structures.json"
    visio_path.write_text(json.dumps(visio_output, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"  Visio结构: {visio_path}")

    # 保存映射
    mapping_output = {}
    for pair_key, m in mapping.items():
        # 不保存完整structure(太大), 只保存摘要
        mapping_output[pair_key] = {
            k: v for k, v in m.items() if k != 'structure'
        }
    mapping_path = OUTPUT_DIR / "visio_mapping.json"
    mapping_path.write_text(json.dumps(mapping_output, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"  映射关系: {mapping_path}")

    # 保存完整数据(含structure)
    full_path = OUTPUT_DIR / "visio_full_data.json"
    full_path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"  完整数据: {full_path}")

    # 汇总
    print(f"\n{'=' * 60}")
    print("汇总")
    print(f"{'=' * 60}")
    total_visio = sum(len(s) for s in all_visio.values())
    total_nodes = sum(s['node_count'] for ss in all_visio.values() for s in ss)
    total_edges = sum(s['edge_count'] for ss in all_visio.values() for s in ss)
    print(f"  Visio嵌入: {total_visio}个")
    print(f"  总节点: {total_nodes}")
    print(f"  总边: {total_edges}")
    print(f"  映射到pair: {len(mapping)}个")

    # 按文档统计
    for doc_name, structures in all_visio.items():
        doc_pairs = [k for k, v in mapping.items() if v['doc'] == doc_name]
        if doc_pairs:
            scores = [mapping[k]['match_score'] for k in doc_pairs]
            print(f"  {doc_name[:25]}: {len(structures)}Visio → {len(doc_pairs)}pair, "
                  f"匹配度{sum(scores)/max(1,len(scores)):.1%}")


if __name__ == "__main__":
    main()
