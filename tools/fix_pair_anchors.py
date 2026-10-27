r"""pair锚点仲裁修复: 以表格条目为仲裁, 在本地/权威两个候选锚点中选优.

背景(实测发现的系统性不一致):
  - 117/226对pair的census重对齐(new_embed)与本地visio_anchor.json不同
  - M2.5的VLM桥重对齐有方向性偏差: align_score在稀疏图上容易得1.0
    (VLM只提取少数文本, 稀疏图子集匹配即满分)
  - 反例1_001: 本地oleObject2(13节点12边, 与表格8条目+4子功能完全对应)
    vs census权威oleObject3(6节点4边, 缺3表条目+混入"数据保障人员")
    → 重对齐把对的换成了错的

仲裁协议(确定性, 以表格为锚):
  对每个pair: ①读table.csv条目名(κ_T编译) ②计算两个候选锚点的
  表条目覆盖度(对齐分) ③取覆盖度高者写回本地
  特殊处理: 零边锚点若有覆盖度>0的候选, 修复; 无表(sc8)跳过.

用法: python tools/fix_pair_anchors.py [--dry-run]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.blackboard.lexical_kit import text_match_score  # noqa: E402
from algorithms.blackboard.kt_compilers import compile_for_scene  # noqa: E402

PAIR_ROOT = BASE / "data/gjb_438c/pair_dataset"
CENSUS = BASE / "data/gjb_438c/anchor_v2/scene_drift_census.json"
ANCHOR_V2 = BASE / "data/gjb_438c/anchor_v2/anchors_v2.json"


def load_v2_index() -> dict[tuple[str, str], dict]:
    data = json.loads(ANCHOR_V2.read_text(encoding="utf-8"))
    idx: dict[tuple[str, str], dict] = {}
    for doc, d in data.items():
        for s in d.get("structures", []):
            key = (doc, s.get("embed_index", "").split(":")[0])
            n_text = sum(1 for n in s.get("nodes", []) if n.get("text"))
            if key not in idx or n_text > sum(
                    1 for n in idx[key].get("nodes", []) if n.get("text")):
                idx[key] = s
    return idx


def table_items(scene: str, csv_path: Path) -> list[str]:
    """κ_T编译表格→条目名(仲裁锚)."""
    try:
        kt = compile_for_scene(scene, csv_path)
        if not kt:
            return []
        t = kt.get("type")
        if t in ("capability", "subfunction"):
            return [c["name"] for c in (kt.get("caps") or kt.get("subs")
                                        or []) if c.get("name")]
        if t == "interface":
            return [it["name"] for it in kt.get("interfaces", [])
                    if it.get("name")]
        if t == "usecase":
            return ([kt.get("uc_name", "")] if kt.get("uc_name") else []) + \
                   [s for s in (kt.get("steps") or {}).values() if s]
        return [n["text"] for n in (kt.get("nodes") or []) if n.get("text")]
    except Exception:
        # κ_T失败时退化: 直接读CSV非空单元格
        try:
            items = []
            for row in csv.reader(open(csv_path, encoding="utf-8")):
                for cell in row:
                    cell = cell.strip()
                    if cell and len(cell) >= 2 and cell not in (
                            "序号", "备注", "—", "-"):
                        items.append(cell.split("/")[0].strip())
            return items[:30]
        except OSError:
            return []


def coverage(struct: dict, items: list[str]) -> tuple[float, int]:
    """锚点结构对表条目的覆盖度: 命中条目的平均对齐分×覆盖率."""
    texts = [n.get("text", "").replace("\n", "") for n
             in struct.get("nodes", []) if n.get("text")]
    if not items or not texts:
        return 0.0, 0
    hit = 0
    score_sum = 0.0
    for item in items:
        best = max((text_match_score(item, t) for t in texts), default=0.0)
        if best >= 0.55:
            hit += 1
            score_sum += best
    return (score_sum / len(items)) if items else 0.0, hit


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    census = json.loads(CENSUS.read_text(encoding="utf-8"))
    v2_idx = load_v2_index()

    n_keep_local = 0       # 本地更好, 不动
    n_switch_to_auth = 0   # 权威更好, 换
    n_fixed_zero = 0       # 零边修复(权威有边且覆盖度>0)
    n_no_table = 0         # 无表格可仲裁
    total = 0
    for scene_dir in sorted(PAIR_ROOT.iterdir()):
        if not scene_dir.is_dir():
            continue
        for pd in sorted(scene_dir.iterdir()):
            va = pd / "visio_anchor.json"
            if not va.exists():
                continue
            table = pd / "table.csv"
            if not table.exists():
                continue
            total += 1
            local = json.loads(va.read_text(encoding="utf-8"))
            items = table_items(scene_dir.name, table)
            if not items:
                n_no_table += 1
                continue

            # 权威候选
            rec = census.get(pd.name, {})
            auth = None
            if isinstance(rec, dict) and rec.get("status") == "anchored" \
                    and rec.get("new_embed"):
                auth = v2_idx.get((rec.get("doc", ""),
                                   rec["new_embed"].split(":")[0]))

            cov_local, hit_local = coverage(local, items)
            cov_auth, hit_auth = coverage(auth, items) if auth else (0.0, 0)

            n_local_edges = len(local.get("edges", []))
            if n_local_edges == 0 and auth and hit_auth > 0:
                # 零边且权威有覆盖 → 修复
                n_fixed_zero += 1
                if not args.dry_run:
                    va.write_text(json.dumps(_build_anchor(
                        pd.name, scene_dir.name, rec, auth), ensure_ascii=False,
                        indent=1), encoding="utf-8")
                print(f"  [零边修复] {pd.name}: {hit_auth}/{len(items)}条目"
                      f"命中, {len(auth.get('edges', []))}边")
                continue
            if auth and cov_auth > cov_local + 0.05:
                # 权威显著更好 → 换
                n_switch_to_auth += 1
                if not args.dry_run:
                    va.write_text(json.dumps(_build_anchor(
                        pd.name, scene_dir.name, rec, auth), ensure_ascii=False,
                        indent=1), encoding="utf-8")
                print(f"  [权威更好] {pd.name}: 本地{hit_local}/"
                      f"{len(items)} vs 权威{hit_auth}/{len(items)}")
            else:
                n_keep_local += 1

    print(f"\n仲裁结果: 共{total}对")
    print(f"  保持本地锚点: {n_keep_local}")
    print(f"  切换到权威: {n_switch_to_auth}")
    print(f"  零边修复: {n_fixed_zero}")
    print(f"  无表格可仲裁: {n_no_table}"
          + (" [DRY-RUN]" if args.dry_run else ""))


def _build_anchor(pair_id: str, scene: str, rec: dict, struct: dict) -> dict:
    return {
        "pair_id": pair_id, "scene": scene,
        "doc": rec.get("doc", ""),
        "embed_index": struct.get("embed_index", ""),
        "mapping_confidence": "high",
        "mapping_source": "table_arbitrated",
        "page": struct.get("page", {}),
        "nodes": struct.get("nodes", []),
        "edges": struct.get("edges", []),
    }


if __name__ == "__main__":
    main()
