"""本地NLI模型客户端: Erlangshen(中文) + mDeBERTa(多语言), GPU优先CPU兜底.

用途: pair级不一致性检测的语义通道(矛盾判定), 与词法/Tier1通道正交.

硬规则遵从:
  - 模块顶层零I/O/零重依赖: torch/transformers只在ensure()内import
  - 失败显式记录(last_error), 不静默吞
  - eval模式+no_grad: 同输入→同输出, 确定性可复现(结果落盘走runs协议)

零样本基线(tools/nli_realdata_test.py, 14条真实SRS对):
  Erlangshen 64.3% / mDeBERTa 71.4%; 共同弱点: 枚举矛盾误判entailment
  → 需配合nli_pair_claims的声明构造策略(闭世界模板), 不裸判.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parents[2]

LABELS = ("entailment", "neutral", "contradiction")

MODELS: dict[str, dict[str, str]] = {
    "erlangshen": {
        "dir": str(BASE / "models" / "nli" / "Erlangshen-Roberta-110M-NLI"),
        "display": "Erlangshen-Roberta-110M-NLI",
    },
    "erlangshen-330m": {
        "dir": str(BASE / "models" / "nli" / "Erlangshen-Roberta-330M-NLI"),
        "display": "Erlangshen-Roberta-330M-NLI",
    },
    "mdeberta": {
        "dir": str(BASE / "models" / "nli" / "mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"),
        "display": "mDeBERTa-v3-base-xnli-multilingual-nli-2mil7",
    },
    "mdeberta-mnli": {
        "dir": str(BASE / "models" / "nli" / "mDeBERTa-v3-base-mnli-xnli"),
        "display": "mDeBERTa-v3-base-mnli-xnli",
    },
    # S4残差NLI域适配微调的checkpoint(集中配置; tools/train_residual_nli.py产出)
    "egt_finetuned": {
        "dir": str(BASE / "models" / "nli" / "egt_finetuned"),
        "display": "mDeBERTa-v3-base-xnli + EGT residual finetune (S4)",
    },
    # S4-v2: 叙事文法升级数据集(跨行值绑定+效果性NIE)重训的checkpoint
    "egt_finetuned_v2": {
        "dir": str(BASE / "models" / "nli" / "egt_finetuned_v2"),
        "display": "mDeBERTa-v3-base-xnli + EGT narrative-grammar finetune (S4-v2)",
    },
    # D1: LLM仲裁蒸馏(GLM-5.3离线教师标签, dev split)在egt_finetuned_v2上
    # 继续微调的checkpoint(tools/train_distilled_nli.py产出);
    # 推理纯本地, 教师只在训练期使用
    "distilled_v1": {
        "dir": str(BASE / "models" / "nli" / "distilled_v1"),
        "display": "mDeBERTa + EGT + GLM-5.3 teacher distillation (D1)",
    },
    # CMNLI公开监督微调对照baseline(tools/train_cmnli_nli.py产出,
    # 供public_baselines矩阵/延迟基准使用, 非算法通道)
    "cmnli_finetuned": {
        "dir": str(BASE / "models" / "nli" / "cmnli_finetuned_mdeberta"),
        "display": "mDeBERTa-v3-base + CMNLI 50k finetune (public baseline)",
    },
}

_BATCH_GPU = 32
_BATCH_CPU = 8
_MAX_LEN = 256


def normalize_label(raw: str) -> str:
    """任意NLI标签(中英文变体) → entailment/neutral/contradiction."""
    s = raw.lower()
    if "entail" in s or "蕴含" in s:
        return "entailment"
    if "contradict" in s or "矛盾" in s:
        return "contradiction"
    return "neutral"


class NliLocal:
    """本地NLI推理客户端. mode: "unavailable" | "cpu" | "gpu".

    用法:
        nli = NliLocal("mdeberta")
        verdicts = nli.predict([("前提...", "假设...")])
        双向: nli.predict_bidirectional(pairs) → fwd/rev/symmetric_contradiction
    """

    def __init__(self, model: str = "mdeberta") -> None:
        if model not in MODELS:
            raise ValueError(f"unknown nli model: {model} (avail: {list(MODELS)})")
        self.model_key = model
        self.model_dir = Path(MODELS[model]["dir"])
        self.mode = "unavailable"
        self.last_error = ""
        self.stats: dict[str, Any] = {"n_calls": 0, "n_pairs": 0,
                                      "n_batches": 0, "infer_ms": 0.0,
                                      "device": "", "model": model}
        self._ready = False
        self._torch: Any = None
        self._tok: Any = None
        self._mdl: Any = None
        self._device = ""
        self._id2label: dict[int, str] = {}

    # ── 惰性初始化 ────────────────────────────────────────
    def ensure(self) -> str:
        """初始化并返回mode ("gpu"|"cpu"|"unavailable"). 失败原因在last_error."""
        if self._ready:
            return self.mode
        self._ready = True
        if not (self.model_dir / "config.json").exists():
            self.last_error = f"model not found: {self.model_dir}"
            return self.mode
        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except ImportError as e:
            self.last_error = f"torch/transformers unavailable: {e}"
            return self.mode
        try:
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            self._torch = torch
            self._tok = AutoTokenizer.from_pretrained(str(self.model_dir),
                                                      local_files_only=True)
            self._mdl = AutoModelForSequenceClassification.from_pretrained(
                str(self.model_dir), local_files_only=True)
            self._mdl.to(self._device)
            self._mdl.eval()
        except (OSError, ValueError, RuntimeError) as e:
            self.last_error = f"model load failed({self._device}): {e}"
            return self.mode
        self._id2label = {int(k): normalize_label(str(v))
                          for k, v in self._mdl.config.id2label.items()}
        self.mode = self._device
        self.stats["device"] = self._device
        return self.mode

    # ── 批量推理 ──────────────────────────────────────────
    def _infer_chunk(self, pairs: list[tuple[str, str]]) -> list[dict[str, float]]:
        torch = self._torch
        prem = [p for p, _ in pairs]
        hyp = [h for _, h in pairs]
        enc = self._tok(prem, hyp, padding=True, truncation="longest_first",
                        max_length=_MAX_LEN, return_tensors="pt")
        enc = {k: v.to(self._device) for k, v in enc.items()}
        with torch.no_grad():
            logits = self._mdl(**enc).logits
            probs = torch.softmax(logits, dim=-1).float().cpu().tolist()
        out = []
        for row in probs:
            # 归一到固定三键(缺失槽位补0)
            d = {lab: 0.0 for lab in LABELS}
            for idx, p in enumerate(row):
                lab = self._id2label.get(idx, "neutral")
                d[lab] = d.get(lab, 0.0) + float(p)
            out.append(d)
        return out

    def predict(self, pairs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        """单向批量推理(premise, hypothesis)→[{label, probs, p_contra, p_entail}].

        空串输入返回neutral(p=1.0), 不发模型.
        """
        mode = self.ensure()
        self.stats["n_calls"] += 1
        self.stats["n_pairs"] += len(pairs)

        def _neutral() -> dict[str, Any]:
            return {"label": "neutral",
                    "probs": {"entailment": 0.0, "neutral": 1.0, "contradiction": 0.0},
                    "p_contra": 0.0, "p_entail": 0.0}

        out: list[dict[str, Any]] = [_neutral() for _ in pairs]
        valid: list[tuple[int, tuple[str, str]]] = [
            (i, (p, h)) for i, (p, h) in enumerate(pairs)
            if p.strip() and h.strip()]
        if not valid or mode == "unavailable":
            return out
        batch = _BATCH_GPU if mode == "gpu" else _BATCH_CPU
        t0 = time.time()
        for i in range(0, len(valid), batch):
            chunk = valid[i:i + batch]
            probs = self._infer_chunk([pr for _, pr in chunk])
            for (idx, _), d in zip(chunk, probs):
                label = max(d, key=lambda k: d[k])
                out[idx] = {"label": label, "probs": d,
                            "p_contra": d["contradiction"], "p_entail": d["entailment"]}
            self.stats["n_batches"] += 1
        self.stats["infer_ms"] += round((time.time() - t0) * 1000, 1)
        return out

    def predict_bidirectional(
            self, pairs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        """双向推理: NLI方向敏感, 双向矛盾比单向更可信(降误报).

        返回 [{fwd, rev, sym_contra, contra_score}]:
          sym_contra     = 双向均为contradiction
          contra_score   = min(p_contra_fwd, p_contra_rev) (双向几何下界)
        """
        fwd = self.predict(pairs)
        rev = self.predict([(h, p) for p, h in pairs])
        out: list[dict[str, Any]] = []
        for f, r in zip(fwd, rev):
            sym = f["label"] == "contradiction" and r["label"] == "contradiction"
            score = min(f["p_contra"], r["p_contra"])
            out.append({"fwd": f, "rev": r, "sym_contra": sym,
                        "contra_score": score})
        return out
