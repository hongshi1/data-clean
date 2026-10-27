#!/usr/bin/env python3
"""
P1-3: Visio提取与映射扩展到全部16份文档 + 全部场景
======================================================
当前只提取了5份文档(171个Visio)，需要扩展到16份。

流程:
  1. 批量转换所有16份.doc → .docx
  2. 提取全部Visio嵌入
  3. 对所有场景(sc1-sc7)做内容匹配映射

用法: python3 tools/sc_visio_expand.py
"""
import re
import io
import zipfile
import json
import csv
import subprocess
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DOC_DIR = BASE / "data/软件需归样例数据集"
DOCX_DIR = BASE / "data/gjb_438c/visio_docx"
DOCX_DIR.mkdir(parents=True, exist_ok=True)
PAIR_DIR = BASE / "data/gjb_438c/pair_dataset"
OUTPUT_DIR = BASE / "data/gjb_438c/visio_extracted"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

NS = {'v': 'http://schemas.microsoft.com/office/visio/2012/main'}


def doc_to_docx(doc_name: str) -> Path:
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
    """docx → OLE2 → Visio ZIP → page1.xml → 结构"""
    try:
        import olefile
    except ImportError:
        subprocess.run(['pip3', 'install', 'olefile', '--break-system-packages'],
                      capture_output=True)
        import olefile


    results = []

    with zipfile.ZipFile(docx_path) as zf:
        embeds = [f for f in zf.namelist() if f.startswith('word/embeddings/')]

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

                    page_files = [f for f in visio_files
                                  if f.startswith('visio/pages/page')
                                  and f.endswith('.xml')
                                  and 'rels' not in f and 'pages.xml' not in f]
                    if not page_files:
                        continue

                    page_xml = vz.read(page_files[0]).decode('utf-8', errors='replace')
                    structure = parse_visio_page(page_xml, embed_path)

                    if structure and (structure['nodes'] or structure['edges']):
                        structure['embed_index'] = embed_path.split('/')[-1]
                        results.append(structure)

            except Exception:
                continue

    return results


def parse_visio_page(page_xml: str, source: str) -> dict:
    from xml.etree import ElementTree as ET
    try:
        root = ET.fromstring(page_xml)
    except ET.ParseError:
        return None

    nodes = []
    for shape in root.findall('.//v:Shape', NS):
        sid = shape.get('ID', '')
        sname = shape.get('Name', '')
        text_elem = shape.find('v:Text', NS)
        text = ''
        if text_elem is not None:
            text = ''.join(text_elem.itertext()).strip()

        if '参与者' in sname:
            node_type = 'actor'
        elif '用例' in sname:
            node_type = 'usecase'
        elif '系统边界' in sname or '边界' in sname:
            node_type = 'boundary'
        elif '归纳' in sname:
            node_type = 'relation'
        else:
            node_type = 'other'

        nodes.append({'id': sid, 'name': sname, 'type': node_type, 'text': text})

    edges = []
    id_to_text = {n['id']: n['text'] for n in nodes if n['text']}
    for conn in root.findall('.//v:Connect', NS):
        from_id = conn.get('FromSheet', '')
        to_id = conn.get('ToSheet', '')
        edges.append({
            'from_id': from_id, 'to_id': to_id,
            'from_text': id_to_text.get(from_id, ''),
            'to_text': id_to_text.get(to_id, ''),
        })

    return {'source': source, 'node_count': len(nodes), 'edge_count': len(edges),
            'nodes': nodes, 'edges': edges}


def extract_table_steps(table_csv_path: Path) -> list[str]:
    if not table_csv_path.exists():
        return []
    with open(table_csv_path, encoding="utf-8") as f:
        rows = list(csv.reader(f))
    steps = []
    for r in rows:
        for cell in r[:2]:
            if cell and len(cell.strip()) > 5:
                clean = re.sub(r'^\d+[\.．]\s*', '', cell.strip())
                if clean:
                    steps.append(clean)
    return steps


def score_match(visio_texts: list[str], table_steps: list[str]) -> float:
    if not visio_texts or not table_steps:
        return 0.0
    matched = 0
    for vt in visio_texts:
        vt_chars = set(vt)
        if not vt_chars:
            continue
        for ts in table_steps:
            ts_chars = set(ts)
            overlap = len(vt_chars & ts_chars) / len(vt_chars)
            if overlap > 0.5:
                matched += 1
                break
    return matched / len(visio_texts)


def main():

    print("=" * 60)
    print("P1-3: Visio提取扩展到全部16份文档")
    print("=" * 60)

    # 加载已有的Visio结构(5份文档)
    existing_path = OUTPUT_DIR / "visio_structures.json"
    if existing_path.exists():
        all_visio = json.loads(existing_path.read_text())
    else:
        all_visio = {}

    # Step 1: 转换所有docx
    print("\n[1] 转换 .doc → .docx")
    doc_files = sorted(DOC_DIR.glob("*.doc"))
    for doc_path in doc_files:
        doc_name = doc_path.stem
        if doc_name in all_visio:
            print(f"  ✓ {doc_name[:30]} (已有)")
            continue
        docx_path = doc_to_docx(doc_name)
        status = "✓" if docx_path and docx_path.exists() else "✗"
        print(f"  {status} {doc_name[:30]}")

    # Step 2: 提取新的Visio
    print("\n[2] 提取Visio结构")
    for doc_path in doc_files:
        doc_name = doc_path.stem
        if doc_name in all_visio:
            continue

        docx_path = DOCX_DIR / f"{doc_name}.docx"
        if not docx_path.exists():
            print(f"  ✗ {doc_name[:30]} (docx不存在)")
            continue

        structures = extract_visio_from_docx(docx_path)
        if structures:
            all_visio[doc_name] = {
                'visio_count': len(structures),
                'structures': structures,
            }
            total_nodes = sum(s['node_count'] for s in structures)
            total_edges = sum(s['edge_count'] for s in structures)
            print(f"  ✓ {doc_name[:30]}: {len(structures)}Visio, "
                  f"{total_nodes}节点, {total_edges}边")
        else:
            print(f"  - {doc_name[:30]}: 无Visio嵌入")

    # 保存全部Visio结构
    visio_path = OUTPUT_DIR / "visio_structures_all.json"
    visio_path.write_text(json.dumps(all_visio, ensure_ascii=False, indent=2), encoding='utf-8')
    total_visio = sum(d['visio_count'] for d in all_visio.values())
    print(f"\n总Visio嵌入: {total_visio}个 (来自{len(all_visio)}份文档)")

    # Step 3: 对所有场景做映射
    print("\n[3] 全场景映射")
    all_mappings = {}

    for sc_dir in sorted(PAIR_DIR.iterdir()):
        if not sc_dir.is_dir():
            continue
        sc_name = sc_dir.name
        sc_mappings = {}
        used_visio = set()

        for sample_dir in sorted(sc_dir.iterdir()):
            if not sample_dir.is_dir():
                continue
            meta_p = sample_dir / "meta.json"
            if not meta_p.exists():
                continue

            meta = json.loads(meta_p.read_text())
            doc_name = meta.get('doc', '')
            if doc_name not in all_visio:
                continue

            table_steps = extract_table_steps(sample_dir / "table.csv")
            structures = all_visio[doc_name]['structures']

            best_score = 0
            best_struct = None

            for struct in structures:
                embed_key = f"{doc_name}:{struct['embed_index']}"
                if embed_key in used_visio:
                    continue

                visio_texts = [n['text'] for n in struct['nodes']
                               if n.get('text', '').strip() and len(n['text'].strip()) > 3]
                score = score_match(visio_texts, table_steps)

                if score > best_score:
                    best_score = score
                    best_struct = struct

            if best_struct and best_score > 0.15:
                used_visio.add(f"{doc_name}:{best_struct['embed_index']}")
                visio_texts = [n['text'] for n in best_struct['nodes']
                              if n.get('text', '').strip() and len(n['text'].strip()) > 3]

                sc_mappings[sample_dir.name] = {
                    'pair_id': meta.get('instance_id', ''),
                    'doc': doc_name,
                    'section': meta.get('section', ''),
                    'image_caption': meta.get('image_caption', ''),
                    'visio_embed': best_struct['embed_index'],
                    'match_score': round(best_score, 3),
                    'table_steps_count': len(table_steps),
                    'visio_text_nodes': len(visio_texts),
                    'visio_total_nodes': best_struct['node_count'],
                    'visio_edges': best_struct['edge_count'],
                    'visio_structure': {
                        'nodes': best_struct['nodes'],
                        'edges': best_struct['edges'],
                    },
                    'table_steps': table_steps,
                }

        if sc_mappings:
            all_mappings[sc_name] = sc_mappings
            scores = [m['match_score'] for m in sc_mappings.values()]
            high = sum(1 for s in scores if s > 0.5)
            print(f"  {sc_name}: {len(sc_mappings)}映射 "
                  f"(avg={sum(scores)/len(scores):.1%}, high={high})")

    # 保存映射
    mapping_path = OUTPUT_DIR / "all_scene_visio_mapping.json"
    mapping_path.write_text(json.dumps(all_mappings, ensure_ascii=False, indent=2), encoding='utf-8')

    # 汇总
    total_mapped = sum(len(m) for m in all_mappings.values())
    print(f"\n{'=' * 60}")
    print("汇总")
    print(f"{'=' * 60}")
    print(f"Visio嵌入: {total_visio}个")
    print(f"映射样本: {total_mapped}对")

    for sc_name, mappings in all_mappings.items():
        scores = [m['match_score'] for m in mappings.values()]
        avg = sum(scores) / len(scores) if scores else 0
        print(f"  {sc_name:30s}: {len(mappings):3d}对 (avg={avg:.1%})")

    print(f"\n保存: {mapping_path}")


if __name__ == "__main__":
    main()
