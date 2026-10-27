r"""零边pair手绘细矩形连线恢复.

问题: 7个pair的锚点0边,根因是作者画连线用细2D矩形(W>>H或H>>W)
而非Visio标准1D连接线(BeginX/EndX)——M11只恢复Connect+1D,漏了这类.

方案: 对每个pair的锚点结构,从原始Visio XML中:
  ① 找细长2D shape(宽高比>8 或 最小边<0.1英寸, 且无文本)
  ② 将其视为连线,两端点=该shape的bbox中心±半宽/半高
  ③ 吸附到最近的两个有文本节点(距离<0.5英寸)
  ④ 恢复为(src→dst)边

用法: python tools/fix_zero_edge_pairs.py [--dry-run]
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

PAIR_ROOT = BASE / "data/gjb_438c/pair_dataset"
DOCX_DIR = BASE / "data/gjb_438c/visio_docx"
NS = {"v": "http://schemas.microsoft.com/office/visio/2012/main"}

# 细长判定: 宽高比>8 或 最小边<0.1英寸
_ASPECT_TH = 8.0
_MIN_DIM_TH = 0.1
_SNAP_TH = 1.0  # 端点吸附距离(英寸)


def find_thin_shapes(xml: str) -> list[dict]:
    """从Visio XML中找细长2D shape(疑似手绘连线)."""
    root = ET.fromstring(xml)
    shapes = root.findall(".//v:Shape", NS)
    thin = []
    for s in shapes:
        cells = {}
        for c in s.findall("v:Cell", NS):
            cells[c.get("N")] = c.get("V")
        # 有文本的不是连线
        texts = s.findall(".//v:Text", NS)
        all_text = " ".join((t.text or "").strip() for t in texts).strip()
        if all_text:
            continue
        w = float(cells.get("Width", 0))
        h = float(cells.get("Height", 0))
        if w <= 0 or h <= 0:
            continue
        aspect = max(w, h) / max(min(w, h), 0.001)
        if aspect > _ASPECT_TH or min(w, h) < _MIN_DIM_TH:
            pin_x = float(cells.get("PinX", 0))
            pin_y = float(cells.get("PinY", 0))
            # 线的两端: 沿长轴方向
            if w > h:  # 水平线
                p1 = (pin_x - w / 2, pin_y)
                p2 = (pin_x + w / 2, pin_y)
            else:  # 垂直线
                p1 = (pin_x, pin_y - h / 2)
                p2 = (pin_x, pin_y + h / 2)
            thin.append({
                "id": s.get("ID"), "w": w, "h": h,
                "p1": p1, "p2": p2,
            })
    return thin


def snap_to_nodes(p: tuple, nodes: list) -> tuple:
    """点→最近的有文本节点(距离<阈值)."""
    best, best_d = None, _SNAP_TH
    for n in nodes:
        d = ((p[0] - n["cx"]) ** 2 + (p[1] - n["cy"]) ** 2) ** 0.5
        if d < best_d:
            best, best_d = n, d
    return best


def extract_visio_xml(pair_dir: Path, doc_name: str,
                      embed_index: str) -> str | None:
    """从docx中提取指定embed的Visio XML."""
    docx = DOCX_DIR / f"{doc_name}.docx"
    if not docx.exists():
        return None
    embed_file = embed_index.split(":")[0]
    try:
        with zipfile.ZipFile(docx) as zf:
            embed_names = [f for f in zf.namelist()
                           if f.startswith("word/embeddings/")]
            for en in sorted(embed_names):
                data = zf.read(en)
                if data[:4].hex() != "d0cf11e0":
                    continue
                import olefile
                ole = olefile.OleFileIO(io.BytesIO(data))
                streams = ["/".join(s) for s in ole.listdir()]
                if "Package" not in streams:
                    ole.close()
                    continue
                pkg = ole.openstream("Package").read()
                ole.close()
                if pkg[:2] != b"PK":
                    continue
                with zipfile.ZipFile(io.BytesIO(pkg)) as vz:
                    page_files = [f for f in vz.namelist()
                                  if "page1.xml" in f or
                                  embed_file.replace(".bin", "") in f]
                    if not page_files:
                        page_files = ["visio/pages/page1.xml"]
                    for pf in page_files:
                        if pf in vz.namelist():
                            return vz.read(pf).decode(
                                "utf-8", errors="replace")
    except (OSError, KeyError, zipfile.BadZipFile):
        return None
    return None


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    zero_pairs = []
    for scene_dir in sorted(PAIR_ROOT.iterdir()):
        if not scene_dir.is_dir():
            continue
        for pd in sorted(scene_dir.iterdir()):
            va = pd / "visio_anchor.json"
            if va.exists():
                a = json.loads(va.read_text(encoding="utf-8"))
                if len(a.get("edges", [])) == 0:
                    zero_pairs.append((scene_dir.name, pd, a))

    print(f"零边pair: {len(zero_pairs)}个")
    total_recovered = 0
    for scene, pd, anchor in zero_pairs:
        doc_name = anchor.get("doc", "")
        embed = anchor.get("embed_index", "")
        print(f"\n{scene}/{pd.name}: doc={doc_name[:20]}, embed={embed}")

        # 提取原始XML
        xml = extract_visio_xml(pd, doc_name, embed)
        if not xml:
            print("  无法提取Visio XML, 跳过")
            continue

        # 找细长shape
        thin = find_thin_shapes(xml)
        print(f"  细长shape: {len(thin)}个")

        # 锚点节点(有文本的)
        nodes = [n for n in anchor.get("nodes", []) if n.get("text")]
        if not nodes:
            print("  无有文本节点, 跳过")
            continue

        # 吸附恢复边
        new_edges = []
        for t in thin:
            n1 = snap_to_nodes(t["p1"], nodes)
            n2 = snap_to_nodes(t["p2"], nodes)
            if n1 and n2 and n1["id"] != n2["id"]:
                new_edges.append({
                    "src": n1["id"], "dst": n2["id"],
                    "src_text": n1["text"][:15],
                    "dst_text": n2["text"][:15],
                    "label": "",
                    "via": "thin_rect_recovery",
                })

        if new_edges:
            total_recovered += len(new_edges)
            print(f"  恢复边: {len(new_edges)}条")
            for e in new_edges[:5]:
                print(f"    {e['src_text']} → {e['dst_text']}")
            if not args.dry_run:
                anchor["edges"] = new_edges
                (pd / "visio_anchor.json").write_text(
                    json.dumps(anchor, ensure_ascii=False, indent=1),
                    encoding="utf-8")
        else:
            print("  无可恢复边")

    print(f"\n总计恢复: {total_recovered}条边"
          + (" [DRY-RUN]" if args.dry_run else ""))


if __name__ == "__main__":
    main()
