"""Question routing (deprecated, always empty).

Historical role: 40 keyword rules mapping question text to candidate
check-item IDs ("detector families"). Two independent ablations proved
the routing inert at inference:

- M73 (docs/srs_project/84_architecture_audit.md): patching
  ``route_question`` to return () flipped **0/91** verdicts.
- M103 (data/gjb_438c/distillation/model_replace_v1.json): the same
  patch flipped **0/213** instances across test46/violations17/
  crossdoc150 — the keyword table is dead annotation weight.

The function is kept (returning an empty tuple) because offline
tooling (egt_synthesis label generation) still imports it; the
40-rule table and its consumers' gating behavior are retired.

Consumers tolerate the empty result by design:
- ``qa_module`` records the ``no_check_item_candidate`` diagnostic;
- ``answer_claims`` skips the bare-numeric subject completion path
  (proven inert by the same ablations);
- DEQ (opt-in) treats it as no routed items.
"""
from __future__ import annotations


def route_question(question: str) -> tuple[str, ...]:
    """Return ordered candidate types (deprecated: always empty)."""
    del question
    return ()
