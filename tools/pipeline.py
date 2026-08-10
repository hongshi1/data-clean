#!/usr/bin/env python3
"""
GJB SRS一致性校验 全流程Pipeline

流程: 数据 → 方法 → 评测
  Stage 1: ID-Graph(图构建+符号层+语义图)
  Stage 2: SC1检测(7种图方法)
  Stage 3: 评测报告汇总

用法:
  python tools/pipeline.py                # 全流程
  python tools/pipeline.py --skip-idgraph # 跳过ID-Graph(已有结果)
  python tools/pipeline.py --report-only  # 只生成报告
"""
import argparse
import json
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(BASE, "tools")
GRAPH_DIR = os.path.join(BASE, "data/gjb_438c/data_assets/graph")


def run(cmd, desc):
    """运行子命令"""
    print(f"\n{'='*60}")
    print(f"[{desc}]")
    print(f"{'='*60}")
    result = subprocess.run(cmd, shell=True, cwd=BASE, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout[-1000:])
    if result.returncode != 0:
        print(f"❌ {desc} 失败: {result.stderr[-300:]}")
    return result.returncode == 0


def stage1_idgraph(skip=False):
    """Stage 1: ID-Graph"""
    if skip:
        print("[Stage 1] 跳过ID-Graph(已有结果)")
        return True
    return run(f"{sys.executable} {TOOLS}/id_graph.py", "Stage 1: ID-Graph")


def stage2_sc1():
    """Stage 2: SC1检测"""
    return run(f"{sys.executable} {TOOLS}/sc1_detector.py --all", "Stage 2: SC1 7方法检测")


def stage3_report():
    """Stage 3: 汇总报告"""
    print(f"\n{'='*60}")
    print("[Stage 3] 评测报告")
    print(f"{'='*60}")

    report = {"pipeline": "GJB SRS一致性校验", "date": "2026-08-10"}

    # SC1结果
    sc1_file = os.path.join(GRAPH_DIR, "sc1_all_methods_eval.json")
    if os.path.exists(sc1_file):
        sc1 = json.loads(open(sc1_file).read())
        report["sc1_name_consistency"] = sc1
        print("\n=== SC1 名称一致性(7方法) ===")
        print(f"{'方法':<25} {'P':<8} {'R':<8} {'F1':<8}")
        for name, m in sc1.items():
            print(f"{name:<25} {m['P']:<8} {m['R']:<8} {m['F1']:<8}")

    # ID-Graph结果
    idg_file = os.path.join(GRAPH_DIR, "id_graph_report.json")
    if os.path.exists(idg_file):
        report["id_graph"] = json.loads(open(idg_file).read())

    # 描述级结果
    desc_file = os.path.join(BASE, "data/gjb_438c/data_assets/gold_standard/cove_desc_full_results.jsonl")
    if os.path.exists(desc_file):
        import time
        # 统计已完成
        results = []
        with open(desc_file) as f:
            for line in f:
                try:
                    results.append(json.loads(line))
                except:
                    pass
        if results:
            correct = sum(1 for r in results if (r.get('kimi_verdict') == 'inconsistent') == (r.get('gold_label') == 'inconsistent'))
            agree = sum(1 for r in results if r.get('models_agree'))
            report["desc_level"] = {
                "total": len(results),
                "accuracy": round(correct / len(results), 3),
                "models_agree": round(agree / len(results), 3),
            }
            print(f"\n=== 描述级({len(results)}条) ===")
            print(f"准确率: {report['desc_level']['accuracy']}, 双模型一致: {report['desc_level']['models_agree']}")

    out = os.path.join(BASE, "data/gjb_438c/data_assets/graph/pipeline_report.json")
    json.dump(report, open(out, 'w'), ensure_ascii=False, indent=2)
    print(f"\n报告已保存: {out}")
    return True


def main():
    parser = argparse.ArgumentParser(description='GJB SRS一致性校验全流程')
    parser.add_argument('--skip-idgraph', action='store_true', help='跳过ID-Graph')
    parser.add_argument('--report-only', action='store_true', help='只生成报告')
    args = parser.parse_args()

    if args.report_only:
        stage3_report()
        return

    # Stage 1
    if not stage1_idgraph(args.skip_idgraph):
        print("Stage 1失败, 继续Stage 2...")

    # Stage 2
    stage2_sc1()

    # Stage 3
    stage3_report()

    print("\n✅ Pipeline完成")


if __name__ == "__main__":
    main()
