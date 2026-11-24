r"""D2蒸馏claim切分器: 兼容re-export shim(M119迁移).

推理核心已原样迁至 ``algorithms/consistency/claim_segmenter_local.py``
(99号方案P1: algorithms侧的claim_typed_bridge需要切分器推理核心,
而algorithms/不import tools/). 本文件仅re-export保持既有消费方
(train_claim_segmenter/eval_claim_recognition/eval_claim_downstream_v2/
eval_agg_codesign/exp_model_replace/eval_segmenter)的import路径不变.

历史docstring见迁移目标模块; 接口:
  segment_claims(answer) -> list[dict]  每条{text, span, boundary_conf}
  distilled_decompose_claims(question, answer) -> list[AnswerClaim]
"""
from __future__ import annotations

from algorithms.consistency.claim_segmenter_local import (
    LABEL_B,
    LABEL_I,
    LABEL_O,
    LABELS,
    MODEL_PATH,
    char_labels_from_claims,
    decode_char_labels,
    distilled_decompose_claims,
    load_status,
    segment_claims,
)

__all__ = [
    "LABELS",
    "LABEL_B",
    "LABEL_I",
    "LABEL_O",
    "MODEL_PATH",
    "char_labels_from_claims",
    "decode_char_labels",
    "distilled_decompose_claims",
    "load_status",
    "segment_claims",
]
