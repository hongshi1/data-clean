"""
visio_demo.py — 最小 Visio (.vsdx) 生成 demo

目的:验证 vsdx 库能否在 macOS 上生成"可在 Visio 里二次编辑"的 .vsdx 文件。

输出:tools/demo_output.vsdx
  - 1 个页面
  - 3 个矩形(分别命名 A / B / C)
  - 2 条连线(A->B, B->C)

关键约束:
  vsdx 库不能从零凭空创建形状,必须基于模板。
  本 demo 使用 vsdx 包自带的 media/media.vsdx 作为模板源,
  其中预置了 RECTANGLE / CIRCLE / STRAIGHT_CONNECTOR 等 master 形状。

运行:
  /Users/gexuancheng/Desktop/research2/data_clean/.venv-srs/bin/python tools/visio_demo.py
"""

from __future__ import annotations
import os
import sys
import vsdx


def main(out_path: str) -> None:
    # vsdx 包自带的模板,含 RECTANGLE/CIRCLE/CONNECTOR 等 master 形状
    template = os.path.join(os.path.dirname(vsdx.__file__), "media", "media.vsdx")
    print(f"[1/5] 打开模板: {template}")

    with vsdx.VisioFile(template) as vis:
        page = vis.get_page_by_name("Page-1")
        print(f"[2/5] 页面: {page.name}  尺寸 w={page.width:.2f} h={page.height:.2f}")

        # 找到模板里的 RECTANGLE 形状作为复制源
        rect_src = page.find_shape_by_text("RECTANGLE")
        if rect_src is None:
            raise RuntimeError("模板里找不到 RECTANGLE 形状")
        print(f"      源矩形 ID={rect_src.ID} 位置=({rect_src.x:.2f},{rect_src.y:.2f})")

        # 复制 2 份,加上源共 3 个矩形;分别移动到不同位置并改文字
        # Visio 坐标系:原点在左下角,单位英寸
        positions = [
            ("A", 2.0, 9.0),   # 左上
            ("B", 5.0, 9.0),   # 中上
            ("C", 5.0, 6.0),   # 中下
        ]

        shapes = []
        # 第一个用源形状本身
        rect_src.text = positions[0][0]
        # 把源形状移到目标位置(用 move 相对移动)
        dx = positions[0][1] - rect_src.x
        dy = positions[0][2] - rect_src.y
        rect_src.move(dx, dy)
        shapes.append(rect_src)
        print(f"[3/5] 形状 A: 移到 ({rect_src.x:.2f},{rect_src.y:.2f})")

        # 第二、三个用 copy
        for label, tx, ty in positions[1:]:
            new_shape = rect_src.copy(page)
            new_shape.text = label
            # copy 后位置与源相同,move 到目标
            new_shape.move(tx - new_shape.x, ty - new_shape.y)
            shapes.append(new_shape)
            print(f"      形状 {label}: 新 ID={new_shape.ID} 位置=({new_shape.x:.2f},{new_shape.y:.2f})")

        # 连线 A->B, B->C
        print("[4/5] 连线:")
        for from_s, to_s in [(shapes[0], shapes[1]), (shapes[1], shapes[2])]:
            conn = vsdx.Connect.create(page, from_s, to_s)
            print(f"      {from_s.text} -> {to_s.text}  connector_id={conn.ID}")

        # 保存
        vis.save_vsdx(out_path)
        print(f"[5/5] 已保存: {out_path}")
        print(f"      文件大小: {os.path.getsize(out_path)} bytes")


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "demo_output.vsdx"
    )
    main(out)
