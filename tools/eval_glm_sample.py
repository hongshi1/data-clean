r"""GLM-5 LLM baseline抽样评测: zero-shot + 领域约定提示两种prompt.

协议: 分层抽样每族30条(共180), llm_chat缓存接口, 结果存JSON供eval_family合并.
"""
from __future__ import annotations

import json
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))
sys.stdout.reconfigure(encoding="utf-8")

SEED = 42
N_PER_FAMILY = 30

SYS_ZS = "你是软件需求规格说明(SRS)的一致性审查专家。判断两段需求描述是否一致。"
PROMPT_ZS = """判断以下两段SRS描述是否语义一致(同一约束的相同声称)还是不一致(矛盾/冲突/值差异)。

描述A: {premise}

描述B: {hypothesis}

只回答JSON: {{"verdict": "consistent" 或 "inconsistent"}}"""

SYS_KD = ("你是GJB军事软件SRS的一致性审查专家。判定域约定(领域等价约定):"
          "同一参数/条目在不同位置以不同表面表述同一值(单位换算如200G=204800MB、"
          "同义算子如不少于=≥、集合重排、同内容异名)视为一致; "
          "值突变、操作符方向冲突、集合成员差、顺序颠倒、条目缺失为不一致。")
PROMPT_KD = """依据上述域约定, 判断两段SRS描述是否一致。

描述A: {premise}

描述B: {hypothesis}

只回答JSON: {{"verdict": "consistent" 或 "inconsistent"}}"""


def parse_verdict(text: str) -> str:
    import re
    m = re.search(r"(consistent|inconsistent)", str(text))
    return m.group(1) if m else "consistent"


def main() -> None:
    from algorithms.common.llm_client import llm_chat

    only = sys.argv[1] if len(sys.argv) > 1 else None  # 可选: 只跑某变体
    data = json.loads((BASE / "data/gjb_438c/family_evalset_v1.json").read_text(encoding="utf-8"))["pairs"]
    rng = random.Random(SEED)
    by_fam = defaultdict(list)
    for x in data:
        by_fam[x["family"]].append(x)
    sample = []
    for f in sorted(by_fam):
        pool = by_fam[f][:]
        rng.shuffle(pool)
        sample.extend(pool[:N_PER_FAMILY])
    print(f"分层抽样: {len(sample)}条(每族{N_PER_FAMILY})")

    variants = {"GLM-5 ZS": (SYS_ZS, PROMPT_ZS),
                "GLM-5 领域约定提示": (SYS_KD, PROMPT_KD)}
    if only:
        variants = {k: v for k, v in variants.items() if only in k}

    # 合并已有结果(增量)
    out_path = BASE / "data/gjb_438c/glm_baseline_sample.json"
    existing = {}
    if out_path.exists():
        existing = json.loads(out_path.read_text(encoding="utf-8"))
        if existing.get("meta", {}).get("sample_ids") != [x["id"] for x in sample]:
            existing = {}  # 抽样不一致则重置
    results = dict(existing.get("predictions", {}))

    for variant, (sys_p, prompt_t) in variants.items():
        if variant in results:
            print(f"{variant}已有结果, 跳过")
            continue
        preds = []
        t0 = time.time()
        for i, x in enumerate(sample):
            try:
                out = llm_chat(prompt_t.format(premise=x["premise"], hypothesis=x["hypothesis"]),
                               system=sys_p, prefer="glm")
                preds.append(parse_verdict(out))
            except Exception as e:  # noqa: BLE001
                print(f"  [{variant}] #{i}失败: {type(e).__name__}: {e}")
                preds.append("consistent")
            if (i + 1) % 20 == 0:
                print(f"  {variant}: {i + 1}/{len(sample)} ({time.time() - t0:.0f}s)", flush=True)
                # 增量保存(超时中断后缓存重放, 断点续跑)
                _save(out_path, sample, results | {variant: preds})
        results[variant] = preds
        print(f"{variant}完成: {time.time() - t0:.0f}s")

    _save(out_path, sample, results)
    print(f"保存 → {out_path}")


def _save(out_path: Path, sample: list[dict], results: dict) -> None:
    out = {"meta": {"sample": "分层每族30条(共180), seed42",
                    "sample_ids": [x["id"] for x in sample],
                    "sample_families": [x["family"] for x in sample],
                    "sample_labels": [x["label"] for x in sample],
                    "n_per_family": N_PER_FAMILY},
           "predictions": results}
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
