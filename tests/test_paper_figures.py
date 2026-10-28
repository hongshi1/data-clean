"""CascadeVerify论文资产守卫测试: 图(fig1-fig6)+表(tables.tex)+数字提取锚点.

三层防护:
  1. 图文件存在/非空(>10KB)/PIL可读且尺寸非零;
  2. tables.tex含论文锚点数字(0.8286/0.9412/0.5294/-0.4857/0.800)与9个表label;
  3. paper_data提取层的锚点断言(防止run数据被篡改/漂移)与中文字体渲染探针.

资产缺失时自动调用生成脚本(自愈), 生成失败即测试失败.
"""
from __future__ import annotations

import os
import subprocess
import sys
import warnings
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
FIG_DIR = BASE / "docs/srs_project/paper/figures"
TABLES_TEX = BASE / "docs/srs_project/paper/tables.tex"
TOOLS = BASE / "tools"

FIGURES = [
    "fig1_cascade_architecture", "fig2_violation_evolution", "fig3_cost_quality_pareto",
    "fig4_mutation_vs_violation", "fig5_crossdoc_gap", "fig6_egt_grammar",
]
TABLE_LABELS = [
    "tab:main", "tab:ablation", "tab:bootstrap", "tab:violation", "tab:mutation",
    "tab:negative", "tab:test_honest", "tab:crossdoc", "tab:experts",
]


def _ensure_assets() -> None:
    """图或表缺失时, 调用生成脚本自愈(一次); 失败则给出可读错误."""
    missing = (not TABLES_TEX.exists()
               or any(not (FIG_DIR / f"{n}.png").exists() for n in FIGURES))
    if not missing:
        return
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONPATH": str(BASE)}
    for script in ("make_paper_figures.py", "make_paper_tables.py"):
        r = subprocess.run([sys.executable, str(TOOLS / script)], cwd=BASE, env=env,
                           capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            pytest.fail(f"{script}生成失败: {r.stderr[-800:]}")


@pytest.fixture(scope="module", autouse=True)
def _assets_ready():
    _ensure_assets()
    return None


# ═══════════════════════════════════════════════════════════════════
# 1. 图文件: 存在 + 非空(>10KB) + PIL可读
# ═══════════════════════════════════════════════════════════════════

def test_figures_png_exist_and_nonempty():
    for name in FIGURES:
        p = FIG_DIR / f"{name}.png"
        assert p.exists(), f"缺图: {p}"
        assert p.stat().st_size > 10 * 1024, f"图过小(<10KB): {p} = {p.stat().st_size}B"


def test_figures_pdf_exist_and_nonempty():
    for name in FIGURES:
        p = FIG_DIR / f"{name}.pdf"
        assert p.exists(), f"缺PDF: {p}"
        assert p.stat().st_size > 5 * 1024, f"PDF过小(<5KB): {p}"


def test_figures_png_dimensions_via_pil():
    from PIL import Image
    for name in FIGURES:
        with Image.open(FIG_DIR / f"{name}.png") as im:
            w, h = im.size
            assert w >= 1500 and h >= 1000, f"{name}: 尺寸异常 {im.size} (应≥300dpi出版级)"


# ═══════════════════════════════════════════════════════════════════
# 2. tables.tex: 锚点数字 + 表label + booktabs三线表
# ═══════════════════════════════════════════════════════════════════

def test_tables_tex_anchors():
    text = TABLES_TEX.read_text(encoding="utf-8")
    anchors = ["0.8286", "0.9412", "0.5294", "-0.4857", "0.800"]
    for a in anchors:
        assert a in text, f"tables.tex缺锚点数字 {a}"


def test_tables_tex_labels_and_booktabs():
    text = TABLES_TEX.read_text(encoding="utf-8")
    for label in TABLE_LABELS:
        assert f"\\label{{{label}}}" in text, f"tables.tex缺表 {label}"
    assert text.count("\\toprule") == len(TABLE_LABELS)
    assert text.count("\\bottomrule") == len(TABLE_LABELS)
    assert text.count("\\midrule") >= len(TABLE_LABELS)
    assert "\\usepackage{booktabs}" in text


# ═══════════════════════════════════════════════════════════════════
# 3. 数字提取锚点: 防run漂移/篡改 (与图/表共享同一提取层)
# ═══════════════════════════════════════════════════════════════════

def test_extraction_anchors():
    sys.path.insert(0, str(TOOLS))
    import paper_data as pdata

    cas = pdata.get_cascade_run()
    cq = {r["config"]: r for r in cas["cost_quality_table"]}
    assert cq["cascade"]["llm_invocations"] == 15
    assert cq["l3_llm"]["llm_invocations"] == 83
    assert cas["configs"]["cascade"]["per_class"]["refute"]["f1"] == 0.8

    stages = pdata.get_violation_evolution()
    assert [s["detected"] for s in stages] == [9, 12, 15, 16]
    assert stages[3]["rate"] == 0.9412

    honest = pdata.get_test_honest_rows()
    assert honest[2]["cfg"]["macro_f1"] == 0.8286
    assert honest[3]["llm"] == 7

    egt = pdata.get_egt_grammar()
    assert egt["near_copy"]["real_macro_f1"] == 0.4963
    assert egt["narrative"]["real_refute_recall"] == 0.875
    assert egt["narrative"]["dev_macro_f1"] == 0.9722

    gap = pdata.get_crossdoc_run()["generalization_gap"]
    assert gap["deterministic"]["delta_macro_f1"] == -0.4857
    assert gap["cascade"]["delta_macro_f1"] == -0.1876

    mut = pdata.get_mutation_run()["family_matrix"]["OVERALL"]
    assert (mut["n_injected"], mut["n_detected"]) == (394, 41)

    oracle = pdata.get_router_run()["oracle_router_ceiling"]
    assert (oracle["macro_f1"], oracle["llm_invocations"]) == (0.7867, 2)

    assert pdata.get_fp16_range() == (0.4325, 0.5298)
    assert pdata.get_l2_false_refute() == (19, 12)
    assert pdata.get_router_heldout()["routing_agreement"] == 0.0875


# ═══════════════════════════════════════════════════════════════════
# 4. 中文字体渲染探针: 与图同一rcParams下无Glyph missing警告
# ═══════════════════════════════════════════════════════════════════

def test_chinese_font_probe_no_missing_glyphs(tmp_path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
    plt.rcParams["axes.unicode_minus"] = False
    fig, ax = plt.subplots(figsize=(4, 2))
    ax.text(0.5, 0.5, "检出率、证据块、级联架构、跨claim聚合、违例演进、证据侧双登记、叙事文法",
            ha="center", va="center", fontsize=10)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        fig.savefig(tmp_path / "font_probe.png", dpi=100)
    plt.close(fig)
    glyph = [str(w.message) for w in caught if "missing from font" in str(w.message)]
    assert not glyph, f"中文字体渲染缺失(图内中文会乱码): {glyph[:2]}"
