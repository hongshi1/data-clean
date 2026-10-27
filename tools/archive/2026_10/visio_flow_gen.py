"""
visio_flow_gen.py — 信息流交互图生成工具 (Visio .vsdx)

参考样式: 集成开发模式联试验证环境构建软件信息流交互图
(组件框 + 信息流箭头 + 标注)

用法:
  python visio_flow_gen.py                     # 生成全部两张图
  python visio_flow_gen.py feature_context     # 只生成特征提取与上下文关联智能体
  python visio_flow_gen.py consistency_check   # 只生成数据一致性校验智能体

输出:
  output/01_特征提取与上下文关联智能体_信息流交互图.vsdx
  output/02_数据一致性校验智能体_信息流交互图.vsdx
"""

from __future__ import annotations
import os
import re
import sys
import zipfile

import vsdx

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(SCRIPT_DIR, "output")
TEMPLATE = os.path.join(os.path.dirname(vsdx.__file__), "media", "media.vsdx")

VISIO_NS = "http://schemas.microsoft.com/office/visio/2012/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

FONT_ID_HEITI = "10"          # 黑体 Font ID (注入 document.xml)
FONT_SIZE_PT = 10             # 全部黑体 10px
COMP_W = 1.7                  # 组件框宽 (inch)
COMP_H = 0.85                 # 组件框高 (inch)
LBL_W = 1.6                   # 标注框宽
LBL_H = 0.32                  # 标注框高


class FlowNode:
    def __init__(self, text, x, y, w=COMP_W, h=COMP_H, is_input=False, is_output=False):
        self.text = text
        self.x = x            # 左下角 x
        self.y = y            # 左下角 y
        self.w = w
        self.h = h
        self.is_input = is_input
        self.is_output = is_output


def gen_vsdx(title, nodes, conns, out_path):
    """nodes: List[FlowNode]; conns: List[(from_text, to_text, label)]"""
    with vsdx.VisioFile(TEMPLATE) as vis:
        page = vis.get_page_by_name("Page-1")
        page.name = title
        src = page.find_shape_by_text("RECTANGLE")

        # 1) 建组件框
        shapes = {}
        for i, n in enumerate(nodes):
            if i == 0:
                sh = src
            else:
                sh = src.copy(page)
            sh.text = n.text
            sh.move(n.x - sh.x, n.y - sh.y)
            shapes[n.text] = sh

        # 2) 连线 + 标注
        for from_t, to_t, label in conns:
            fs, ts = shapes[from_t], shapes[to_t]
            vsdx.Connect.create(page, fs, ts)
            # 标注文字(独立小框,放在连线中点偏上)
            cx = (fs.center_x_y[0] + ts.center_x_y[0]) / 2
            cy = (fs.center_x_y[1] + ts.center_x_y[1]) / 2
            lbl = src.copy(page)
            lbl.text = label
            lbl.move(cx - LBL_W / 2 - lbl.x, cy + 0.12 - lbl.y)
            shapes[label] = lbl  # 后续后处理按 text 找

        vis.save_vsdx(out_path)


def postprocess(path):
    """命名空间修复 + 黑体10px注入 + 连接线箭头 + 页面横向"""
    VISIO_NS = "http://schemas.microsoft.com/office/visio/2012/main"
    src = zipfile.ZipFile(path)
    parts = {}
    for name in src.namelist():
        parts[name] = src.read(name)
    src.close()

    new_parts = {}
    for name, data in parts.items():
        if not (name.endswith(".xml") or name.endswith(".rels")):
            new_parts[name] = data
            continue
        text = data.decode("utf-8")
        # --- 命名空间修复 ---
        text = text.replace(f'xmlns:ns0="{VISIO_NS}"', f'xmlns="{VISIO_NS}"')
        text = text.replace("ns0:", "")
        new_parts[name] = text.encode("utf-8")

    # --- document.xml: 注入黑体 FaceName ---
    doc_name = "visio/document.xml"
    if doc_name in new_parts:
        doc = new_parts[doc_name].decode("utf-8")
        if "SimHei" not in doc:
            face = (f'<FaceName NameU="SimHei" ID="{FONT_ID_HEITI}" '
                    f'UnicodeRanges="-2147483648 0 0 0" CharSets="0 0" Panose="2 2 0 0 0 0 0 0 0 0" Flags="325"/>')
            doc = doc.replace("</FaceNames>", face + "</FaceNames>")
        new_parts[doc_name] = doc.encode("utf-8")

    # --- page1.xml: 形状黑体10px + 连接线箭头 ---
    page_name = "visio/pages/page1.xml"
    if page_name in new_parts:
        page = new_parts[page_name].decode("utf-8")
        char_section = (
            f'<Section N="Character"><Row IX="0">'
            f'<Cell N="Font" V="{FONT_ID_HEITI}"/>'
            f'<Cell N="Size" V="{FONT_SIZE_PT}"/>'
            f'<Cell N="Color" V="0"/>'
            f'<Cell N="Style" V="0"/>'
            f'</Row></Section>'
        )
        # 每个 Shape: 在 Geometry/Text 之前插入 Character section
        page = re.sub(
            r'(<Section N="Geometry"|</Section><Text|<Text)',
            lambda m: char_section + m.group(1),
            page,
        )
        # 连接线(ObjType=2 或含 BegTrigger)加 EndArrow
        page = re.sub(
            r'(<Section N="Line"><Cell N="LineWeight"[^>]*/></Section>)',
            r'\1', page
        )
        # 给所有 Shape 补 Line section EndArrow(组件框不需要箭头;只给连接线)
        # 连接线特征: Cell N='BegTrigger' 存在
        def add_arrow(m):
            block = m.group(0)
            if "BegTrigger" in block and '<Cell N="EndArrow"' not in block:
                arrow = ('<Section N="Line"><Cell N="EndArrow" V="13"/><Cell N="BeginArrow" V="0"/></Section>')
                # 插到 Property 之前(或 Geometry 之前)
                block = re.sub(r'(<Section N="(Geometry|Property)")', arrow + r'\1', block, count=1)
            return block
        page = re.sub(r'<Shape[^>]*>.*?</Shape>', add_arrow, page, flags=re.S)
        new_parts[page_name] = page.encode("utf-8")

    # --- pages.xml: 页面横向 A4 (11.69 x 8.27) ---
    pages_name = "visio/pages/pages.xml"
    if pages_name in new_parts:
        pages = new_parts[pages_name].decode("utf-8")
        pages = re.sub(r'<Cell N="PageWidth"[^>]*/>', '<Cell N="PageWidth" V="11.69291338582677"/>', pages)
        pages = re.sub(r'<Cell N="PageHeight"[^>]*/>', '<Cell N="PageHeight" V="8.26771653543307"/>', pages)
        new_parts[pages_name] = pages.encode("utf-8")

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in new_parts.items():
            zout.writestr(name, data)


# =====================================================================
# 图 A: 特征提取与上下文关联智能体 — 信息流交互图
# =====================================================================
def build_feature_context(out_dir):
    nodes = [
        FlowNode("标准化预处理智能体", 0.4, 5.6, is_input=True),
        FlowNode("多模态特征提取", 2.6, 5.6),
        FlowNode("语义角色标注", 4.8, 5.6),
        FlowNode("跨章节实体链接", 7.0, 5.6),
        FlowNode("上下文聚合", 7.0, 2.2),
        FlowNode("条目库管理", 4.8, 2.2),
        FlowNode("数据一致性校验智能体", 2.6, 2.2, is_output=True),
    ]
    conns = [
        ("标准化预处理智能体", "多模态特征提取", "标准化特征数据"),
        ("多模态特征提取", "语义角色标注", "多模态特征"),
        ("语义角色标注", "跨章节实体链接", "语义角色"),
        ("跨章节实体链接", "上下文聚合", "实体关联关系"),
        ("上下文聚合", "条目库管理", "聚合条目"),
        ("条目库管理", "数据一致性校验智能体", "条目列表"),
    ]
    out = os.path.join(out_dir, "01_特征提取与上下文关联智能体_信息流交互图.vsdx")
    gen_vsdx("特征提取与上下文关联智能体", nodes, conns, out)
    postprocess(out)
    print(f"[A] 已生成: {out}")
    return out


# =====================================================================
# 图 B: 数据一致性校验智能体 — 信息流交互图
# =====================================================================
def build_consistency_check(out_dir):
    nodes = [
        FlowNode("上下文关联智能体", 0.4, 3.8, is_input=True),
        FlowNode("语法层校验", 2.8, 6.2),
        FlowNode("语义层校验", 2.8, 3.8),
        FlowNode("逻辑层校验", 2.8, 1.4),
        FlowNode("差异判别", 5.6, 3.8),
        FlowNode("不一致性报告生成", 8.4, 3.8),
        FlowNode("设计人员确认", 10.6, 3.8, is_output=True),
    ]
    conns = [
        ("上下文关联智能体", "语法层校验", "聚合条目对"),
        ("上下文关联智能体", "语义层校验", "聚合条目对"),
        ("上下文关联智能体", "逻辑层校验", "聚合条目对"),
        ("语法层校验", "差异判别", "语法检测结果"),
        ("语义层校验", "差异判别", "语义检测结果"),
        ("逻辑层校验", "差异判别", "逻辑检测结果"),
        ("差异判别", "不一致性报告生成", "不一致性清单"),
        ("不一致性报告生成", "设计人员确认", "不一致性报告"),
    ]
    out = os.path.join(out_dir, "02_数据一致性校验智能体_信息流交互图.vsdx")
    gen_vsdx("数据一致性校验智能体", nodes, conns, out)
    postprocess(out)
    print(f"[B] 已生成: {out}")
    return out


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    os.makedirs(OUT_DIR, exist_ok=True)
    results = []
    if which in ("all", "feature_context"):
        results.append(build_feature_context(OUT_DIR))
    if which in ("all", "consistency_check"):
        results.append(build_consistency_check(OUT_DIR))
    return results


if __name__ == "__main__":
    main()
