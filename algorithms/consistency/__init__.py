"""QA consistency verification over upstream-frozen retrieved context.

Primary module API: ``QAConsistencyModule.verify(QAInput)``. The old
``ConsistencyChecker.check(premise, hypothesis)`` remains a low-level legacy
pair primitive and must not be used as a complete QA verdict interface.

Converged facade: ``CascadeVerifier`` (preset/scene 三行代码入口, 委托
QAConsistencyModule; 见 algorithms/consistency/verifier.py).
"""

from algorithms.consistency.qa_models import QAInput, RetrievedEvidence, SourceRef
from algorithms.consistency.qa_module import QAConsistencyModule
from algorithms.consistency.verifier import CascadeVerifier, VerdictResult

__all__ = [
    "QAInput",
    "QAConsistencyModule",
    "RetrievedEvidence",
    "SourceRef",
    "CascadeVerifier",
    "VerdictResult",
]
