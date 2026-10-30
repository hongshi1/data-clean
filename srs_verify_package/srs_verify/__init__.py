"""srs-verify: GJB SRS答案一致性校验(独立分发包).

三行代码入口(preset=成本/质量档位, scene=词典+规则包场景):

    from srs_verify import CascadeVerifier

    verifier = CascadeVerifier(preset="fast", scene="srs_scene1")
    result = verifier.verify(question, answer, evidence)  # evidence=dict列表
    print(result.verdict, result.evidence_refs)

verdict三态: support / refute / not_in_evidence(开放世界).
包内自检: python -m srs_verify.smoke_test. 详见README.md.
"""
from srs_verify.qa_models import (
    ClaimResult,
    QAInput,
    RetrievedEvidence,
    SourceRef,
)
from srs_verify.verifier import (
    PRESETS,
    SCENES,
    CascadeVerifier,
    VerdictResult,
)

__version__ = "0.1.0"

__all__ = [
    "CascadeVerifier",
    "VerdictResult",
    "PRESETS",
    "SCENES",
    "ClaimResult",
    "QAInput",
    "RetrievedEvidence",
    "SourceRef",
    "__version__",
]
