"""公开中文三态NLI基准加载器 + 自建评测集的(premise, hypothesis, 三态)适配.

统一输出契约: 每个pair = {"id", "premise", "hypothesis", "label"},
label ∈ {support, refute, not_in_evidence} (语义映射:
entailment→support, contradiction→refute, neutral→not_in_evidence).

三个公开测试集(格式与规模已盘点):
  XNLI-zh test  5010条 (parquet, label列int): 0=entailment 1=neutral 2=contradiction
                (与xnli_zh_std.jsonl逐行对读校验一致)
  OCNLI官方test 2950条 (ocnli_official_test.json, prompt行格式):
                ⚠ 文件内prompt文本声称"0(蕴含)/1(中性)/2(矛盾)"与真实标签
                编码相反——语义锚点对校验(明显蕴含对齐label 2, 明显矛盾对齐
                label 0, 中性对齐1)与二值dev子集(ocnli.jsonl=官方test的
                0/2行重编码0/1, 947个2→1与900个0→0交叉一致)共同实证:
                真实编码 0=contradiction / 1=neutral / 2=entailment.
                文件内prompt语义不可信, 以本loader的实证映射为准.
  CMNLI test   12241条 (cmnli_test_std.jsonl, gold字符串直接可读;
                =cmnli_test_raw.json 12426行剔除185个'-'无效标签)

公开训练数据(BGE中心法的fit池来源, 与test零重叠已校验):
  OCNLI train  50437条 (ocnli_std.jsonl, gold字符串; 与官方test重叠0对)
  CMNLI train 391211对 (cmnli_train_raw.json; 与test有3个原始重复key,
                fit池构造时显式剔除)

子采样协议(全部seed=42, random.Random, 抽样后按原序恢复):
  模型视图: 测试集全量; n>3000 → 抽2000
  LLM视图 : 公开集从模型视图抽300; 自建集全量

自建集适配(premise构造复用nli_training.build_premise: 剥HTML+滑窗
锚定+每块500/总1500字符):
  91QA   : premise=冻结证据文本拼接, hypothesis=answer, label=silver(final_verdict)
  06跨文档: 同上, label=sound_label

模块顶层零I/O(全部读取在函数内, utf-8强制).
"""
from __future__ import annotations

import json
import random
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency.eval_lib import (  # noqa: E402
    QA_FROZEN,
    SILVER,
    load_frozen_qa,
    load_silver_labels,
    read_jsonl,
)
from algorithms.consistency.nli_training import (  # noqa: E402
    PER_BLOCK_CAP,
    TOTAL_CAP,
    build_premise,
)

PUBLIC_NLI_DIR = BASE / "data/gjb_438c/public_nli"
XNLI_ZH_TEST = PUBLIC_NLI_DIR / "xnli_zh_test.parquet"
OCNLI_TEST = PUBLIC_NLI_DIR / "ocnli_official_test.json"
CMNLI_TEST_STD = PUBLIC_NLI_DIR / "cmnli_test_std.jsonl"
OCNLI_TRAIN = PUBLIC_NLI_DIR / "ocnli_std.jsonl"
CMNLI_TRAIN_RAW = PUBLIC_NLI_DIR / "cmnli_train_raw.json"
CROSSDOC06 = BASE / "data/gjb_438c/qa_frozen/crossdoc06_evalset_v1.jsonl"

VERDICTS = ("support", "refute", "not_in_evidence")
NLI_TO_VERDICT = {"entailment": "support", "contradiction": "refute",
                  "neutral": "not_in_evidence"}

SEED = 42
MODEL_CAP_TRIGGER = 3000
MODEL_CAP_SIZE = 2000
LLM_SAMPLE_SIZE = 300

# OCNLI官方test的实证label编码 (见模块docstring: 文件内prompt文本不可信)
_OCNLI_CODE_TO_NLI = {0: "contradiction", 1: "neutral", 2: "entailment"}
_XNLI_CODE_TO_NLI = {0: "entailment", 1: "neutral", 2: "contradiction"}
_OCNI_PROMPT_RE = re.compile(r"句子1：(.+?)\n句子2：(.+)$", re.S)

Pair = dict


# ── 基础工具 ────────────────────────────────────────────────────────────────


def _check_verdict(label: str, where: str) -> str:
    if label not in VERDICTS:
        raise ValueError(f"{where}: label超出三态契约: {label!r}")
    return label


def _read_lines(path: Path) -> list[str]:
    return [line for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def subsample(pairs: list[Pair], k: int, seed: int = SEED) -> list[Pair]:
    """确定性子采样: random.Random(seed)抽下标, 按原序恢复(可复现)."""
    if k >= len(pairs):
        return list(pairs)
    rng = random.Random(seed)
    indices = sorted(rng.sample(range(len(pairs)), k))
    return [pairs[i] for i in indices]


def model_view(pairs: list[Pair], *, trigger: int = MODEL_CAP_TRIGGER,
               cap: int = MODEL_CAP_SIZE, seed: int = SEED) -> list[Pair]:
    """模型baseline视图: 全量; n>trigger → 抽cap条(seed)."""
    if len(pairs) > trigger:
        return subsample(pairs, cap, seed)
    return list(pairs)


def llm_view(pairs: list[Pair], *, k: int = LLM_SAMPLE_SIZE,
             seed: int = SEED) -> list[Pair]:
    """LLM baseline视图: 公开集抽k条(从模型视图), 自建集传全量(k>=n原样)."""
    return subsample(pairs, k, seed)


# ── 公开测试集 ──────────────────────────────────────────────────────────────


def load_xnli_zh(path: Path = XNLI_ZH_TEST) -> list[Pair]:
    """XNLI-zh test 5010条 → 三态pair (label int: 0=E 1=N 2=C, 实证校验)."""
    import pandas as pd

    frame = pd.read_parquet(path)
    out: list[Pair] = []
    for i, row in enumerate(frame.itertuples(index=False)):
        nli = _XNLI_CODE_TO_NLI[int(row.label)]
        out.append({
            "id": f"xnli-{i:05d}",
            "premise": str(row.premise).strip(),
            "hypothesis": str(row.hypothesis).strip(),
            "label": NLI_TO_VERDICT[nli],
        })
    for pair in out:
        _check_verdict(pair["label"], "xnli_zh")
    return out


def parse_ocnli_prompt(prompt: str) -> tuple[str, str]:
    """OCNLI prompt行 → (句子1, 句子2); 无法解析时报错(不静默)."""
    match = _OCNI_PROMPT_RE.search(prompt)
    if not match:
        raise ValueError(f"OCNLI prompt无法解析出句子1/句子2: {prompt[:120]!r}")
    return match.group(1).strip(), match.group(2).strip()


def load_ocnli_test(path: Path = OCNLI_TEST) -> list[Pair]:
    """OCNLI官方test 2950条 → 三态pair.

    label编码经语义锚点对+二值dev子集双重实证为
    0=contradiction/1=neutral/2=entailment (见模块docstring).
    """
    rows = [json.loads(line) for line in _read_lines(path)]
    out: list[Pair] = []
    for i, row in enumerate(rows):
        premise, hypothesis = parse_ocnli_prompt(str(row.get("input", "")))
        try:
            code = int(row["label"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"OCNLI第{i}行label缺失/非法: {row.get('label')!r}"
                             ) from exc
        if code not in _OCNLI_CODE_TO_NLI:
            raise ValueError(f"OCNLI第{i}行label超出0/1/2: {code}")
        out.append({
            "id": f"ocnli-{i:05d}",
            "premise": premise,
            "hypothesis": hypothesis,
            "label": NLI_TO_VERDICT[_OCNLI_CODE_TO_NLI[code]],
        })
    return out


def load_cmnli_test(path: Path = CMNLI_TEST_STD) -> list[Pair]:
    """CMNLI test 12241条(std jsonl, gold字符串) → 三态pair."""
    out: list[Pair] = []
    for i, row in enumerate(read_jsonl(path)):
        gold = str(row.get("gold", ""))
        if gold not in NLI_TO_VERDICT:
            raise ValueError(f"CMNLI第{i}行gold非法: {gold!r}")
        out.append({
            "id": f"cmnli-{i:05d}",
            "premise": str(row.get("premise", "")).strip(),
            "hypothesis": str(row.get("hypothesis", "")).strip(),
            "label": NLI_TO_VERDICT[gold],
        })
    return out


def load_public_tests() -> dict[str, list[Pair]]:
    """三个公开测试集 → {name: 全量pairs} (视图裁剪由调用方决定)."""
    return {
        "xnli_zh": load_xnli_zh(),
        "ocnli": load_ocnli_test(),
        "cmnli_test": load_cmnli_test(),
    }


# ── 公开训练数据 (BGE中心法fit池; 与test零重叠已校验) ───────────────────────


def load_ocnli_train(path: Path = OCNLI_TRAIN) -> list[Pair]:
    """OCNLI train 50437条(ocnli_std.jsonl) → 三态pair (与官方test重叠0对)."""
    out: list[Pair] = []
    for i, row in enumerate(read_jsonl(path)):
        gold = str(row.get("gold", ""))
        if gold not in NLI_TO_VERDICT:
            raise ValueError(f"OCNLI train第{i}行gold非法: {gold!r}")
        out.append({
            "id": f"ocnli-train-{i:05d}",
            "premise": str(row.get("premise", "")).strip(),
            "hypothesis": str(row.get("hypothesis", "")).strip(),
            "label": NLI_TO_VERDICT[gold],
        })
    return out


def load_cmnli_train(path: Path = CMNLI_TRAIN_RAW,
                     exclude_keys: set[tuple[str, str]] | None = None
                     ) -> list[Pair]:
    """CMNLI train 391k+ (sentence1/2/label) → 三态pair.

    exclude_keys: (premise, hypothesis)集合, 用于剔除与test的3个原始重复
    key(fit池零泄漏).
    """
    exclude = exclude_keys if exclude_keys is not None else set()
    out: list[Pair] = []
    skipped = 0
    for i, line in enumerate(_read_lines(path)):
        row = json.loads(line)
        premise = str(row.get("sentence1", "")).strip()
        hypothesis = str(row.get("sentence2", "")).strip()
        label = str(row.get("label", ""))
        if label not in NLI_TO_VERDICT or not premise or not hypothesis:
            skipped += 1
            continue
        if (premise, hypothesis) in exclude:
            skipped += 1
            continue
        out.append({
            "id": f"cmnli-train-{i:05d}",
            "premise": premise,
            "hypothesis": hypothesis,
            "label": NLI_TO_VERDICT[label],
        })
    if skipped:
        print(f"cmnli_train: 剔除{skipped}行(无效标签/空句/与test重复)")
    return out


def cmnli_test_keys(path: Path = CMNLI_TEST_STD) -> set[tuple[str, str]]:
    """CMNLI test的(premise, hypothesis)key集合 (train泄漏剔除用)."""
    return {(str(row.get("premise", "")).strip(),
             str(row.get("hypothesis", "")).strip())
            for row in read_jsonl(path)}


# ── 自建评测集适配 ──────────────────────────────────────────────────────────


def evidence_premise(answer: str, evidence_texts: list[str],
                      per_block: int = PER_BLOCK_CAP,
                      total: int = TOTAL_CAP) -> str:
    """自建集premise: 冻结证据文本 → build_premise(剥HTML+滑窗+截断)."""
    return build_premise(answer, evidence_texts, per_block=per_block,
                         total=total)


def _selfbuilt_pairs(rows: list[dict], label_of: dict[str, str] | None,
                     label_key: str, id_prefix: str) -> list[Pair]:
    """自建集行 → 三态pair; label优先取label_of(instance_id), 否则行内label_key."""
    out: list[Pair] = []
    for row in rows:
        answer = str(row["answer"])
        texts = [str(ev.get("text", "")) for ev in row["evidence"]]
        instance_id = str(row["instance_id"])
        if label_of is not None:
            if instance_id not in label_of:
                raise ValueError(f"{id_prefix}: {instance_id}不在标签映射中")
            label = label_of[instance_id]
        else:
            label = str(row[label_key])
        out.append({
            "id": f"{id_prefix}-{instance_id}",
            "premise": evidence_premise(answer, texts),
            "hypothesis": answer,
            "label": _check_verdict(label, f"{id_prefix}:{instance_id}"),
        })
    return out


def load_selfbuilt_91qa(path: Path = QA_FROZEN,
                        silver_path: Path = SILVER) -> list[Pair]:
    """91QA: premise=冻结证据拼接(≤1500字符), hypothesis=answer, label=silver."""
    rows = load_frozen_qa(path)
    silver = load_silver_labels(silver_path)
    missing = [str(r["instance_id"]) for r in rows
               if str(r["instance_id"]) not in silver]
    if missing:
        raise ValueError(f"91QA有{len(missing)}条无silver标签, 例: {missing[:3]}")
    return _selfbuilt_pairs(rows, silver, "final_verdict", "qa91")


def load_selfbuilt_crossdoc06(path: Path = CROSSDOC06) -> list[Pair]:
    """06号跨文档30条 → 三态pair (label=sound_label, 10/10/10)."""
    rows = read_jsonl(path)
    return _selfbuilt_pairs(rows, None, "sound_label", "crossdoc06")


__all__ = [
    "CROSSDOC06",
    "LLM_SAMPLE_SIZE",
    "MODEL_CAP_SIZE",
    "MODEL_CAP_TRIGGER",
    "NLI_TO_VERDICT",
    "SEED",
    "VERDICTS",
    "cmnli_test_keys",
    "evidence_premise",
    "llm_view",
    "load_cmnli_test",
    "load_cmnli_train",
    "load_ocnli_test",
    "load_ocnli_train",
    "load_public_tests",
    "load_selfbuilt_91qa",
    "load_selfbuilt_crossdoc06",
    "load_xnli_zh",
    "model_view",
    "parse_ocnli_prompt",
    "subsample",
]
