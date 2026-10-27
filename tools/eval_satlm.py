r"""SatLM-GLM baseline (NeurIPS 2023, arXiv:2305.09656 声明式prompting路线).

两个变体, 共享同一LLM编译层, 区分"提取的价值"与"判定语义的价值":
  neutral: LLM编译约束(同参数同变量+单位归一=常识提取) → Z3联合可满足性(逻辑级判定)
  spec:    同一编译 → 同参数规格等价比较(领域等价约定语义判定)
预期: neutral≈纯Z3的改进(覆盖率升但规格盲区仍在), spec≈0.95(用户直觉验证)
评测: A族150条, 4线程并行, 增量保存.
"""
from __future__ import annotations

import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))
sys.stdout.reconfigure(encoding="utf-8")

OUT_PATH = BASE / "data/gjb_438c/satlm_baseline.json"

SYSTEM = "你是形式化方法专家, 将SRS需求文本编译为Z3可求解的声明式约束. 只输出JSON."
PROMPT = """把以下两段SRS描述中的全部数值约束编译为声明式约束集合.

编译规则:
1. 每个独立参数一个变量(如 x_可用空间); **同一参数(含同义名/不同单位)必须映射到同一变量**, 单位归一到基本单位(G/MB→字节, s/min→秒, 种/个→无量纲)
2. 忠实保留数学关系: 不小于/不少于/至少→">=", 不大于/不超过/至多→"<=", 为/等于→"=="
3. 无数值约束的内容忽略; 某段没有约束则其列表为空

描述A: {premise}

描述B: {hypothesis}

输出JSON(不要其他文字):
{{"constraints_A": [{{"var": "x_参数名", "op": ">=", "value": 100}}],
 "constraints_B": [...]}}"""


def parse_json_loose(text: str) -> dict:
    m = re.search(r"\{.*\}", str(text), re.S)
    if not m:
        return {"constraints_A": [], "constraints_B": []}
    try:
        return json.loads(m.group())
    except json.JSONDecodeError:
        return {"constraints_A": [], "constraints_B": []}


def verdict_neutral(comp: dict) -> str:
    """Z3联合可满足性(逻辑级, 无领域知识)."""
    try:
        from z3 import Real, Solver, unsat
    except ImportError:
        return "consistent"
    solver = Solver()
    vars_map: dict[str, object] = {}
    n = 0
    for side in ("constraints_A", "constraints_B"):
        for c in comp.get(side, []):
            v, op = str(c.get("var", f"v{n}")), str(c.get("op", "=="))
            try:
                val = float(c.get("value"))
            except (TypeError, ValueError):
                continue
            if v not in vars_map:
                vars_map[v] = Real(v.replace("-", "_").replace(" ", "_"))
            x = vars_map[v]
            if op == ">=":
                solver.add(x >= val)
            elif op == "<=":
                solver.add(x <= val)
            else:
                solver.add(x == val)
            n += 1
    if n == 0:
        return "consistent"
    return "inconsistent" if solver.check() == unsat else "consistent"


def verdict_spec(comp: dict) -> str:
    """同参数规格等价(领域等价约定语义): 同var的(op,value)不同 → inconsistent."""
    a = {str(c.get("var")): (str(c.get("op")), c.get("value"))
         for c in comp.get("constraints_A", []) if c.get("var")}
    b = {str(c.get("var")): (str(c.get("op")), c.get("value"))
         for c in comp.get("constraints_B", []) if c.get("var")}
    for var, spec_a in a.items():
        if var in b:
            op_a, val_a = spec_a
            op_b, val_b = b[var]
            try:
                same_val = abs(float(val_a) - float(val_b)) < 1e-9
            except (TypeError, ValueError):
                same_val = str(val_a) == str(val_b)
            if not same_val or op_a != op_b:
                return "inconsistent"
    return "consistent"


def main() -> None:
    from algorithms.common.llm_client import llm_chat

    variant = sys.argv[1] if len(sys.argv) > 1 else "neutral"
    data = json.loads((BASE / "data/gjb_438c/family_evalset_v1.json").read_text(encoding="utf-8"))["pairs"]
    a_pairs = [x for x in data if x["family"] == "A"]
    print(f"SatLM-{variant}: A族{len(a_pairs)}条, 4线程")

    existing = {}
    if OUT_PATH.exists():
        existing = json.loads(OUT_PATH.read_text(encoding="utf-8"))
        if existing.get("meta", {}).get("variant") != variant:
            existing = {}

    done = existing.get("done", 0)
    results = existing.get("results", [])
    if done >= len(a_pairs):
        print("已完成, 直接汇总")
    else:
        todo = a_pairs[done:]

        def work(x):
            try:
                out = llm_chat(PROMPT.format(premise=x["premise"], hypothesis=x["hypothesis"]),
                               system=SYSTEM, prefer="glm")
                return parse_json_loose(out)
            except Exception as e:  # noqa: BLE001
                return {"error": f"{type(e).__name__}: {e}"}

        t0 = time.time()
        with ThreadPoolExecutor(max_workers=4) as ex:
            for i, comp in enumerate(ex.map(work, todo)):
                results.append(comp)
                if (i + 1) % 20 == 0:
                    elapsed = time.time() - t0
                    print(f"  {done + i + 1}/{len(a_pairs)} ({elapsed:.0f}s)", flush=True)
                    OUT_PATH.write_text(json.dumps(
                        {"meta": {"variant": variant, "n": len(a_pairs)},
                         "done": done + i + 1, "results": results}, ensure_ascii=False), encoding="utf-8")

    # 汇总
    vfn = verdict_neutral if variant == "neutral" else verdict_spec
    preds, golds = [], []
    for x, comp in zip(a_pairs, results, strict=True):
        preds.append(vfn(comp))
        golds.append(x["label"])
    n_pos = golds.count("inconsistent")
    n_neg = golds.count("consistent")
    tpr = sum(1 for p, g in zip(preds, golds) if p == g == "inconsistent") / n_pos
    tnr = sum(1 for p, g in zip(preds, golds) if p == g == "consistent") / n_neg
    bacc = (tpr + tnr) / 2
    print(f"\nSatLM-{variant} on A族: bAcc={bacc:.3f} (TPR={tpr:.3f}, TNR={tnr:.3f})")
    n_compiled = sum(1 for r in results if r.get("constraints_A") or r.get("constraints_B"))
    print(f"编译覆盖率: {n_compiled}/{len(results)}")

    final = {"meta": {"variant": variant, "n": len(a_pairs)},
             "done": len(results), "results": results,
             "summary": {"bAcc": round(bacc, 3), "TPR": round(tpr, 3), "TNR": round(tnr, 3),
                         "compile_coverage": n_compiled}}
    OUT_PATH.write_text(json.dumps(final, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"保存 → {OUT_PATH}")


if __name__ == "__main__":
    main()
