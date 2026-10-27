r"""锚点结构 → .vsdx生成器: 从解析出的nodes/edges重建Visio文件.

用途(M0解析的镜像):
  - 锚点提取(OLE→XML→nodes/edges) 的反向: nodes/edges→Open XML→ZIP(.vsdx)
  - 渲染回归验证: 重建的vsdx在Visio打开渲染→与原PNG对比=锚点保真度
    的可视化验证(比数字快照直观)
  - 修正编辑: 检测到图不一致→重建修正版供人工确认

技术: Visio 2013+ Open XML (ZIP包), 无master的自绘Shape:
  - 节点=矩形(Geometry四角) + 中心文本
  - 边=1D连接线(BeginX/EndX + EndArrow) + 边标签
  - 坐标系: 英寸, 页面尺寸来自锚点page字段

用法:
  from tools.anchor_to_vsdx import anchor_to_vsdx
  anchor_to_vsdx(structure, out_path)
"""
from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Any

NS = "http://schemas.microsoft.com/office/visio/2012/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

_CT = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="{CT_NS}">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="text/xml"/>
<Override PartName="/visio/document.xml" ContentType="application/vnd.ms-visio.drawing.main+xml"/>
<Override PartName="/visio/pages/pages.xml" ContentType="application/vnd.ms-visio.pages+xml"/>
<Override PartName="/visio/pages/page1.xml" ContentType="application/vnd.ms-visio.page+xml"/>
<Override PartName="/visio/masters/masters.xml" ContentType="application/vnd.ms-visio.masters+xml"/>
</Types>"""

_ROOT_RELS = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="{REL_NS}">
<Relationship Id="rId1" Type="http://schemas.microsoft.com/visio/2010/relationships/document" Target="visio/document.xml"/>
</Relationships>"""

_DOC = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<VisioDocument xmlns="{NS}" xmlns:r="{R_NS}">
<DocumentSettings TopPage="0"/>
<Pages/>
</VisioDocument>"""

_DOC_RELS = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="{REL_NS}">
<Relationship Id="rId1" Type="http://schemas.microsoft.com/visio/2010/relationships/pages" Target="pages/pages.xml"/>
<Relationship Id="rId2" Type="http://schemas.microsoft.com/visio/2010/relationships/masters" Target="masters/masters.xml"/>
</Relationships>"""

_PAGES = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Pages xmlns="{NS}" xmlns:r="{R_NS}">
<Page ID="0" NameU="页-1" Name="页-1">
<PageSheet LineAdjustDir="0" Scale="1" ScaleRelation="0">
<Cell N="PageWidth" V="{{W}}" U="IN"/>
<Cell N="PageHeight" V="{{H}}" U="IN"/>
<Cell N="ShdwOffsetX" V="0.125" U="IN"/>
<Cell N="ShdwOffsetY" V="-0.125" U="IN"/>
<Cell N="PageScale" V="1" U="IN"/>
<Cell N="DrawingScale" V="1" U="IN"/>
<Cell N="DrawingSizeType" V="3"/>
</PageSheet>
<Rel r:id="rId1"/>
</Page>
</Pages>"""

_PAGES_RELS = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="{REL_NS}">
<Relationship Id="rId1" Type="http://schemas.microsoft.com/visio/2010/relationships/page" Target="page1.xml"/>
</Relationships>"""

_MASTERS = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Masters xmlns="{NS}" xmlns:r="{R_NS}"/>
"""

# 颜色按节点类型(渲染预览的视觉区分)
_TYPE_COLORS = {
    "usecase": "#DEEBF7",
    "process": "#FFF2CC",
    "decision": "#E2F0D9",
    "state": "#FBE5D6",
    "actor": "#EDEDED",
}
_DEFAULT_COLOR = "#FFFFFF"


def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(
        ">", "&gt;").replace('"', "&quot;")


def _node_shape(n: dict, shape_id: int) -> str:
    """节点→无master自绘矩形Shape(Geometry四角+居中文本)."""
    w = n.get("w") or 1.4
    h = n.get("h") or 0.45
    color = _TYPE_COLORS.get(n.get("type", ""), _DEFAULT_COLOR)
    text = _esc(n.get("text", ""))
    return f"""<Shape ID='{shape_id}' Type='Shape'>
<Cell N='PinX' V='{n["cx"]:.4f}' U='IN'/>
<Cell N='PinY' V='{n["cy"]:.4f}' U='IN'/>
<Cell N='Width' V='{w:.4f}' U='IN'/>
<Cell N='Height' V='{h:.4f}' U='IN'/>
<Cell N='LocPinX' V='{w / 2:.4f}' U='IN'/>
<Cell N='LocPinY' V='{h / 2:.4f}' U='IN'/>
<Cell N='LinePattern' V='1'/>
<Cell N='LineWeight' V='0.01' U='IN'/>
<Cell N='FillPattern' V='1'/>
<Cell N='FillForegnd' V='{color}'/>
<Section N='Geometry' ID='0' FillMode='1'>
<Row T='RelMoveTo' IX='0'><Cell N='X' V='0'/><Cell N='Y' V='0'/></Row>
<Row T='RelLineTo' IX='1'><Cell N='X' V='1'/><Cell N='Y' V='0'/></Row>
<Row T='RelLineTo' IX='2'><Cell N='X' V='1'/><Cell N='Y' V='1'/></Row>
<Row T='RelLineTo' IX='3'><Cell N='X' V='0'/><Cell N='Y' V='1'/></Row>
<Row T='RelLineTo' IX='4'><Cell N='X' V='0'/><Cell N='Y' V='0'/></Row>
</Section>
<Text><cp IX='0'/><pp IX='0'/>{text}</Text>
</Shape>"""


def _edge_shape(e: dict, nodes: dict[str, dict], shape_id: int) -> str:
    """边→1D连接线Shape(Begin/End端点+EndArrow+边标签)."""
    s, t = nodes.get(e["src"], {}), nodes.get(e["dst"], {})
    if not s or not t:
        return ""
    # 端点=节点中心的裁剪(简单版: 直接连中心, Visio渲染线穿框)
    bx, by = s.get("cx", 0), s.get("cy", 0)
    ex, ey = t.get("cx", 0), t.get("cy", 0)
    label = _esc(e.get("label", ""))
    label_xml = f"<Text><cp IX='0'/><pp IX='0'/>{label}</Text>" if label else ""
    return f"""<Shape ID='{shape_id}' Type='Shape'>
<Cell N='BeginX' V='{bx:.4f}' U='IN'/>
<Cell N='BeginY' V='{by:.4f}' U='IN'/>
<Cell N='EndX' V='{ex:.4f}' U='IN'/>
<Cell N='EndY' V='{ey:.4f}' U='IN'/>
<Cell N='LinePattern' V='1'/>
<Cell N='LineWeight' V='0.01' U='IN'/>
<Cell N='EndArrow' V='13'/>
<Cell N='EndArrowSize' V='2'/>
<Section N='Geometry' ID='0' FillMode='1'>
<Row T='MoveTo' IX='0'><Cell N='X' V='{bx:.4f}'/><Cell N='Y' V='{by:.4f}'/></Row>
<Row T='LineTo' IX='1'><Cell N='X' V='{ex:.4f}'/><Cell N='Y' V='{ey:.4f}'/></Row>
</Section>
{label_xml}
</Shape>"""


def anchor_to_vsdx(structure: dict[str, Any], out_path: Path | str) -> Path:
    """锚点结构(nodes/edges/page) → .vsdx文件.

    结构保真版重建: 节点(文本/坐标/类型着色)+有向边(箭头+标签);
    像素级格式(线型/填充/装饰)不还原——结构正确性验证用.
    """
    page = structure.get("page", {})
    pw = page.get("w") or 8.5
    ph = page.get("h") or 11.0
    nodes = {n["id"]: n for n in structure.get("nodes", [])}

    shapes: list[str] = []
    sid = 1
    for n in structure.get("nodes", []):
        if not n.get("text"):
            continue  # 装饰形状不重建
        shapes.append(_node_shape(n, sid))
        sid += 1
    for e in structure.get("edges", []):
        sh = _edge_shape(e, nodes, sid)
        if sh:
            shapes.append(sh)
            sid += 1

    page1 = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<PageContents xmlns="{NS}" xmlns:r="{R_NS}">
<Shapes>
{chr(10).join(shapes)}
</Shapes>
</PageContents>"""

    out_path = Path(out_path)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _CT)
        zf.writestr("_rels/.rels", _ROOT_RELS)
        zf.writestr("visio/document.xml", _DOC)
        zf.writestr("visio/_rels/document.xml.rels", _DOC_RELS)
        zf.writestr("visio/pages/pages.xml", _PAGES.replace("{W}", f"{pw}").replace("{H}", f"{ph}"))
        zf.writestr("visio/pages/_rels/pages.xml.rels", _PAGES_RELS)
        zf.writestr("visio/pages/page1.xml", page1)
        zf.writestr("visio/masters/masters.xml", _MASTERS)
    return out_path


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    import io
    import olefile
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tools.m0_anchor_extract import parse_page, get_cells
    from xml.etree import ElementTree as ET

    DOC = r"C:\Users\12488\Downloads\系统技术方案-第5版(修订).doc"
    POOL = "ObjectPool/_1234567894/Package"
    OUT = Path(r"C:\Users\12488\Downloads\特征提取与上下文关联智能体_重建版.vsdx")

    ole = olefile.OleFileIO(DOC)
    data = ole.openstream(POOL).read()
    ole.close()
    with zipfile.ZipFile(io.BytesIO(data)) as vz:
        xml = vz.read("visio/pages/page1.xml").decode("utf-8", errors="replace")
        dims = None
        try:
            proot = ET.fromstring(vz.read("visio/pages/pages.xml"))
            NSV = {"v": NS}
            ps = proot.find("v:Page/v:PageSheet", NSV)
            if ps is not None:
                cells = get_cells(ps)
                dims = (float(cells.get("PageWidth", 3.7)),
                        float(cells.get("PageHeight", 2.4)))
        except Exception:
            pass
    st = parse_page(xml, "user_fig5", "user_fig5:page1", dims)
    p = anchor_to_vsdx(st, OUT)
    print(f"重建: {p} ({p.stat().st_size}B, "
          f"{len(st['nodes'])}节点 {len(st['edges'])}边)")
