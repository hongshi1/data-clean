r"""生成科研论文风格的结果矩阵表格图片(PNG, 高分辨率).

特性:
  - 指标名(R@1/R@5/R@10/MRR)明确标注在列头
  - 每列最优值自动加粗
  - 论文排版风格(白底/细网格/方法按家族分组着色/我们方法浅蓝高亮)
  - 300 DPI, 可直接投稿

用法: python tools/generate_results_table.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")
matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial"]
matplotlib.rcParams["axes.unicode_minus"] = False

BASE = Path(__file__).resolve().parents[1]
E = BASE / "data/gjb_438c/data_assets"
EV = E / "evalsets"
OUT_DIR = BASE / "docs/srs_project/figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)

METRICS = ["R@1", "R@5", "R@10", "MRR@10"]

# 加载所有数据
def load_all() -> dict:
    data = {}
    def load(name, path, sk=None):
        if not path.exists():
            return
        d = json.loads(path.read_text(encoding="utf-8"))
        rs = d.get("results", d)
        if sk:
            rs = rs.get(sk, {})
        for mk, mv in rs.items():
            if isinstance(mv, dict) and "R@1" in mv:
                data[(name, mk)] = mv
    load("GJB图", E/"va_colpali_eval.json")
    load("GJB表caption", E/"table_late_eval.json", "caption")
    load("GJB深行v1", E/"table_late_eval.json", "deep_v1")
    load("GJB深行v2", E/"table_late_eval.json", "deep_v2")
    load("WTQ", EV/"results"/"_public_en_raw.json", "wtq")
    load("FeTaQA", EV/"results"/"_public_en_raw.json", "fetaqa")
    load("DuRetrieval", EV/"results"/"_duret_full_raw.json")
    load("GJB图-token", EV/"results"/"_token_maxsim_raw.json", "gjb_image")
    load("GJB深行v1-token", EV/"results"/"_token_maxsim_raw.json",
         "gjb_table_deep")
    load("GJBcaption-token", EV/"results"/"_token_maxsim_raw.json",
         "gjb_table_caption")
    load("WTQ-token", EV/"results"/"_token_maxsim_raw.json", "wtq")
    load("FeTaQA-token", EV/"results"/"_token_maxsim_raw.json", "fetaqa")
    load("GJB深行v2全法", EV/"deep_v2_eval.json")
    load("GJB深行v2补充", EV/"deep_v2_extra_baselines.json")
    # V3统一评测 + 两阶段重排
    load("GJB深行v3", EV/"results"/"S1_deep_v3_all.json")
    load("GJB图v3", EV/"results"/"S4_image_all.json")
    load("GJB深行v1v3", EV/"results"/"S3_deep_v1_all.json")
    load("GJB深行v4", EV/"results"/"S5_deep_v4_all.json")
    load("GJB深行v34", EV/"results"/"S6_deep_v34_all.json")
    load("WTQ-rerank", EV/"results"/"public_rerank.json", "wtq")
    load("FeTaQA-rerank", EV/"results"/"public_rerank.json", "fetaqa")
    return data

NORM = {
    'B1_bridge': 'B1-dense', 'B1_dense': 'B1-dense',
    'O1-unit': 'O1-unit', 'O1-unit(对照)': 'O1-unit',
    'O1-unit(fixed-serialization)': 'O1-unit',
    'VA_colpali': 'O1-unit+CMSC',
    'TP-raw': 'O1-TP-raw', 'TP-cc': 'O1-TP-cc', 'TP-cf': 'O1-TP-cf',
    'BM25-doc': 'BM25-doc', 'BM25-unit': 'BM25-unit', 'Cell-BM25': 'Cell-BM25',
    'B1-dense': 'B1-dense', 'M3-dense': 'M3-dense', 'M3-colbert': 'M3-colbert',
    'M3-dense@4096': 'M3-dense', 'M3-sparse': 'M3-sparse',
    'Token-MaxSim': 'Token-MaxSim',
    'ROUTE4': 'ROUTE4', 'ROUTE5': 'ROUTE5',
    'R(d,raw)': 'R(d,TP-raw)', 'R(d,cc)': 'R(d,TP-cc)', 'R(d,cf)': 'R(d,TP-cf)',
    'ROUTE(O1+M3)': 'R(O1+M3)', 'O1+rrF': 'O1+Rerank', 'O1+rrS': 'O1+Rerank(S)',
    'M3+rrF': 'M3+Rerank',
    'O1-unit+Rerank@20(full)': 'O1+Rerank(全表)',
    'O1-unit+Rerank(top50,unit2,b0.1)': 'O1+Rerank(单元)',
    'Token-MaxSim+Rerank@50': 'TMS+Rerank(单元)',
    'stage2': 'O1+Rerank(en)',
    'HyDE-dense': 'HyDE-dense', 'HyDE-unit': 'HyDE-unit', 'HyDE-E5': 'HyDE-E5',
    'E5-dense': 'E5-dense', 'E5-unit': 'E5-unit',
}

def norm(data):
    out = {}
    for (sc, m), v in data.items():
        out[(sc, NORM.get(m, m))] = v
    return out

# 方法行定义: (显示名, json键, 是否我们的方法)
NATIVE_METHODS = [
    ("BM25-doc",        "BM25-doc",       False),
    ("BM25-unit",       "BM25-unit",      False),
    ("Cell-BM25",       "Cell-BM25",      False),
    ("B1-dense(zh)",    "B1-dense",       False),
    ("HyDE-dense",      "HyDE-dense",     False),
    ("E5-dense",        "E5-dense",       False),
    ("M3-dense",        "M3-dense",       False),
    ("Token-MaxSim",    "Token-MaxSim",   False),
    ("M3-colbert",      "M3-colbert",     False),
    ("O1-unit",         "O1-unit",        True),
    ("O1-TP-cc",        "O1-TP-cc",       True),
    ("O1-TP-cf",        "O1-TP-cf",       True),
    ("ROUTE4",          "ROUTE4",         True),
    ("O1+Rerank",       "O1+Rerank",      True),
    ("O1+Rerank(单元)", "O1+Rerank(单元)", True),
    ("TMS+Rerank(单元)", "TMS+Rerank(单元)", True),
]

EXT_METHODS = [
    ("BM25-doc",       "BM25-doc",   False),
    ("BM25-unit",      "BM25-unit",  False),
    ("B1-dense(en)",   "B1-dense",   False),
    ("B1-dense(zh)",   "B1-dense",   False),
    ("M3-dense",       "M3-dense",   False),
    ("M3-colbert",     "M3-colbert", False),
    ("Token-MaxSim",   "Token-MaxSim", False),
    ("O1-unit(en)",    "O1-unit",    True),
    ("O1-unit(zh)",    "O1-unit",    True),
    ("ROUTE4",         "ROUTE4",     True),
    ("O1+Rerank",      "O1+Rerank",  True),
    ("O1+Rerank(en)",  "O1+Rerank(en)", True),
]

NATIVE_SCENES = [
    ("GJB图\n(899q,v3)",    ["GJB图v3", "GJB图", "GJB图-token"]),
    ("GJB表caption\n(1532q)", ["GJB表caption", "GJBcaption-token"]),
    ("GJB深行v1\n(118q)",   ["GJB深行v1", "GJB深行v1v3", "GJB深行v1-token"]),
    ("GJB深行v2\n(155q)",   ["GJB深行v2", "GJB深行v2全法", "GJB深行v2补充"]),
    ("GJB深行v3\n(262q)",   ["GJB深行v3"]),
    ("GJB深行v34\n(16文档)", ["GJB深行v34", "GJB深行v4"]),
]

EXT_SCENES = [
    ("WTQ\n(en)",           ["WTQ", "WTQ-rerank"]),
    ("FeTaQA\n(en)",        ["FeTaQA", "FeTaQA-rerank"]),
    ("DuRetrieval\n(zh)",   ["DuRetrieval"]),
]


def get_val(data, scene_keys, method, metric):
    """从多场景源取值(优先精确匹配)."""
    for sk in scene_keys:
        v = data.get((sk, method))
        if v and metric in v:
            return v[metric]
    return None


def draw_table(data, scenes, methods, title, filename, figsize=(16, 8)):
    """画论文风格的表格图片."""
    n_rows = len(methods) + 2  # +header +指标行
    n_cols = 1 + len(scenes) * 4

    # 构建cell文本(全空, 后面填充)
    cell_text = [[""] * n_cols for _ in range(n_rows)]
    col_labels = [""] * n_cols

    fig, ax = plt.subplots(figsize=figsize)
    ax.axis("off")

    table = ax.table(cellText=cell_text, colLabels=col_labels,
                     cellLoc="center", loc="upper center",
                     colWidths=[0.12] + [0.22 / len(scenes)] * len(scenes) * 4)

    # 收集数据
    all_vals = []
    for disp, mkey, ours in methods:
        row = []
        for sc_label, sc_keys in scenes:
            vals = {}
            for met in METRICS:
                v = get_val(data, sc_keys, mkey, met)
                vals[met] = v
            row.append(vals)
        all_vals.append(row)

    # 找每列(场景×指标)最优值
    best = {}
    for sc_i, (sc_label, sc_keys) in enumerate(scenes):
        for met in METRICS:
            vals = [all_vals[r][sc_i][met] for r in range(len(methods))
                    if all_vals[r][sc_i][met] is not None]
            if vals:
                best[(sc_i, met)] = max(vals)

    # 填充cell文本 (matplotlib Cell的text需要直接操作_text属性)
    def set_cell(r, c, txt):
        cell = table[r, c]
        if hasattr(cell, "_text"):
            cell._text.set_text(txt)
        else:
            cell.get_text().set_text(txt)

    header_row = 0
    set_cell(header_row, 0, "Method")
    for sc_i, (sc_label, _) in enumerate(scenes):
        set_cell(header_row, 1 + sc_i * 4, sc_label.replace("\n", " "))
        # 合并该场景的4列(只写第一列, 其余写空)
        for extra in range(1, 4):
            set_cell(header_row, 1 + sc_i * 4 + extra, "")

    metric_row = 1
    set_cell(metric_row, 0, "")
    for sc_i in range(len(scenes)):
        for m_i, met in enumerate(METRICS):
            set_cell(metric_row, 1 + sc_i * 4 + m_i, met)

    # 数据行
    for r, (disp, mkey, ours) in enumerate(methods):
        row_idx = r + 2
        set_cell(row_idx, 0, disp)
        for sc_i in range(len(scenes)):
            for m_i, met in enumerate(METRICS):
                v = all_vals[r][sc_i][met]
                col_idx = 1 + sc_i * 4 + m_i
                if v is None:
                    set_cell(row_idx, col_idx, "—")
                else:
                    is_best = best.get((sc_i, met)) == v
                    txt = f"{v:.3f}"
                    set_cell(row_idx, col_idx, txt)
                    if is_best:
                        table[row_idx, col_idx].get_text().set_weight("bold")
                        table[row_idx, col_idx].set_facecolor("#C8E6C9")

    # 样式
    for i in range(n_rows):
        for j in range(n_cols):
            cell = table[i, j]
            cell.set_edgecolor("#CCCCCC")
            cell.set_linewidth(0.5)
            if i == 0:  # 场景头
                cell.set_facecolor("#2C3E50")
                cell.get_text().set_color("white")
                cell.get_text().set_weight("bold")
                cell.get_text().set_fontsize(9)
            elif i == 1:  # 指标行
                cell.set_facecolor("#E8EAF6")
                cell.get_text().set_fontsize(8)
                cell.get_text().set_color("#333")
            else:
                method_idx = i - 2
                disp, mkey, ours = methods[method_idx]
                if ours:
                    cell.set_facecolor("#E3F2FD")  # 我们方法浅蓝
                if j == 0:  # 方法名列
                    cell.get_text().set_fontsize(9)
                    cell.get_text().set_weight("bold" if ours else "normal")
                else:
                    cell.get_text().set_fontsize(8)

    table.auto_set_font_size(False)
    table.scale(1, 1.8)

    ax.set_title(title, fontsize=13, fontweight="bold", pad=20)
    plt.tight_layout()
    out = OUT_DIR / filename
    fig.savefig(str(out), dpi=300, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close()
    print(f"  → {out}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    data = norm(load_all())

    print("生成论文风格表格图片:")
    draw_table(data, NATIVE_SCENES, NATIVE_METHODS,
               "GJB-URE-v2 (Native) — R@1 / R@5 / R@10 / MRR@10",
               "results_native.png", figsize=(16, 10))
    draw_table(data, EXT_SCENES, EXT_METHODS,
               "External Datasets — R@1 / R@5 / R@10 / MRR@10",
               "results_external.png", figsize=(18, 8))
    print("完成.")


if __name__ == "__main__":
    main()
