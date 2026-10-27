# Scene1 Answer Mutation Coverage Diagnosis

> **更新（2026-10-22）**：算子库已从 6 个静态可归属实例扩充到 **54 个实例，覆盖 40 项 taxonomy 中的 39 项**（唯一缺口 PARAM-04 按 taxonomy 标注为 needs_data，有意不实现）。路由已补齐全部 40 项。新算子族（TERM-02/04/05/07、PARAM-01/02/03/05/07/08/09/10、LOGIC-01/02/03/07/08/09/10/11、GJB-01~11）分别位于 `term_mutations.py`、`param_mutations.py`、`logic_mutations.py`、`gjb_mutations.py`，并已接入统一 builder。builder 在 91 条真实冻结数据上现在产出 **3 个 proof-backed 候选**（TERM-07 接口标识显式冲突，refute），其余家族仍因 open-scope 证据被安全拒绝。详见 `tools/audit_operator_coverage.py` 与 `43_operator_coverage_matrix.json`。

## Scope

This report diagnoses `data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl` against the
current answer-side builder and operators. It does not modify operators, assign
Gold labels to the frozen QA, or create synthetic Gold data.

The commands used were:

```text
python tools/build_answer_mutation_candidates.py --input data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl ...
```

and a read-only scan of the 91 JSONL records plus the existing unit tests.

## Observed Result

The builder result is:

| Measure | Result |
|---|---:|
| Frozen QA rows | 91 |
| Evidence records traversed | 574 |
| Proof-backed candidates | 0 |
| Evidence-level `TERM-08` attempts rejected | 574 |
| Evidence-level `LOGIC-04` attempts rejected | 574 |
| Evidence-level numeric identity attempts rejected | 574 |
| Structural list-add attempts rejected | 1,612 |
| Question rows with no router hit | 49 / 91 |

The 574 figure is the number of evidence-level attempts, not 574 distinct QA
rows. The source contains multiple evidence blocks per question; 47 questions
have eight evidence blocks, and only two questions have fewer than three
blocks (one has zero and one has one).

## Why The Builder Emits Zero

The active builder is `tools/build_answer_mutation_candidates.py`. It now also
attempts the conservative structural operators for explicitly parsed list
members, aligned numbered steps, and prohibited exception outcomes. Each
operator still requires `completeness: closed` and a completeness proof. All
Scene1 evidence is marked open, so these attempts cannot yield candidates; the
zero result is a safety outcome, not a reason to relax the evidence contract.

1. `propose_abbreviation_expansion` requires evidence matching the form
   `ACRONYM（full form）`, and an answer containing that acronym in quotes. All
   574 attempts fail at the evidence-definition gate. The answers contain many
   ASCII identifiers such as `BLOB`, `SQL`, and `FLOAT`, but identifiers are not
   acronym definitions.
2. `propose_reversed_data_flow` requires a directed evidence statement matching
   `source向destination`, `source发送至destination`, or `source传输至destination`,
   plus the same directed phrase in the answer and a question naming the source.
   None of the 574 evidence blocks satisfies the directed-flow gate.
3. `propose_numeric_identity` is the only unconditional downstream attempt for
   answers that contain a number. It still requires both answer and evidence to
   contain the same explicit equality, with the same subject and unit, and the
   question to mention that subject. All 574 attempts fail the first gate:
   `operator requires an explicit numeric equality claim`. Numbers in the
   answers are mostly identifiers, counts, section references, limits copied
   into prose, or enumerated explanations rather than an equality claim.
4. The range and exact-conflict operators are not reached for this asset because
   the builder only enters their numeric branch when its answer-number search
   succeeds, and the equality proof still has to pass. The one range-like
   numeric fact in the evidence is not expressed as the answer/evidence pair
   required by `propose_out_of_range_conflict`.
5. The explicit quote/enum operators require a quoted answer term and a nearby
   explicit exclusion in the evidence. The answer scan found only one quoted
   answer, while the evidence scan found no usable exclusion phrase for this
   operator path. These operators consequently produce no rows.

The legacy `algorithms/qa_mutation_ops.py` does not change this conclusion. It
contains pair-level operators whose contract mutates a premise/hypothesis pair,
and its module documentation explicitly quarantines them from the answer-side
QA contract. Reusing their labels here would violate the frozen context and
answer-only mutation boundary.

## Text Morphology

The following counts are row-level counts over the 91 answers, using simple
deterministic lexical checks. They describe routing opportunity, not truth.

| Answer property | Rows |
|---|---:|
| Contains at least one digit | 70 |
| Contains a current numeric unit token (`ms`, `秒`, `GB`, etc.) | 6 |
| Contains `为`/`等于` plus a digit | 22 |
| Contains a matched quote pair (`「」` or `“”`) | 13 |
| Contains an ASCII identifier-like token | 74 |
| Contains directed-flow wording (`向`/`发送至`/`传输至`) | 11 |
| Contains range wording (`至`/`到`/`~`/`～`) | 44 |
| Contains list/explanation markers (`包括`/`包含`/`以下`/`分别`) | 80* |

`*` The marker scan is deliberately literal and does not treat Markdown or
general prose as a structured enumeration. The answers are visibly list-heavy,
but their lists are not serialized as the operator-specific claim forms.

Length and surface shape:

| Shape | Rows |
|---|---:|
| Short, numeric, Markdown/list-like | 23 |
| Medium, numeric, Markdown/list-like | 41 |
| Long, numeric, Markdown/list-like | 3 |
| Short, non-numeric, prose | 15 |
| Short, non-numeric, Markdown/list-like | 5 |
| Short, numeric, prose | 2 |
| Medium, non-numeric, prose | 1 |
| Long, numeric, prose | 1 |

The key distinction is semantic: the answer text explains workflows, actors,
conditions, exceptions, and functions. It rarely states a single atomic claim
in the exact surface form that the current proof rules can mutate safely.

## Router Coverage

`route_question()` routes only by configured question keywords. Its row-level
distribution is:

| Route result | Rows |
|---|---:|
| No route | 49 |
| `LOGIC-02` | 10 |
| `LOGIC-03` | 10 |
| `TERM-03` | 8 |
| `LOGIC-03` + `TERM-03` | 6 |
| `TERM-04` | 4 |
| `LOGIC-05` | 2 |
| `LOGIC-09` | 1 |
| `TERM-07` | 1 |

The routed types are mostly broad retrieval/question families. They do not
imply that the current corresponding answer mutation exists. In particular,
the active answer builder only has deterministic implementations for numeric
equality/range, unit-equivalent numeric surface, explicit quote/enum exclusion,
acronym expansion, and reversed directed flow. The router's `LOGIC-02`,
`LOGIC-03`, `LOGIC-05`, `LOGIC-09`, `TERM-03`, `TERM-04`, and `TERM-07` hits
therefore have no matching active answer operator in this builder.

## Safe-Operation Matrix

| Pattern observed in this asset | Current safe candidate | Reason for absence |
|---|---|---|
| Workflow/step explanation | None | No answer-side step deletion or reorder proof; legacy step operators are pair-level |
| Exception-flow explanation | None | No answer-side exception strategy operator; `LOGIC-02` is routed but not implemented here |
| Function list / capability enumeration | None | No structured answer list parser and no evidence-side complete-set proof |
| Actor description | None | No answer-side actor mutation; frozen evidence is open-scope and not exhaustive |
| ASCII identifiers (`BLOB`, `SQL`, `FLOAT`) | None | Identifier occurrence is not an acronym definition or a safe synonym relation |
| Numeric mentions | None in current run | No explicit answer/evidence equality with same subject/unit |
| Quoted term | None in current run | One quote-like answer does not pair with an explicit evidence exclusion |
| Directed flow | None in current run | No evidence and answer pair uses the required directed syntax |

The evidence is marked `completeness: open`. This is an important safety
constraint: absence from a frozen block cannot prove absence from the SRS, so
an operator that deletes an item or invents an unsupported answer would need
manual review rather than an automatic verdict.

Structural list, actor/role, step reorder/deletion, and exception-outcome
operator attempts are therefore not applicable to the frozen asset. Synthetic
closed-scope fixtures separately verify that a supported list addition receives
`support`, while removing an explicitly evidenced member receives `refute`; an
open-scope version is rejected. These fixture labels do not alter Scene1.
The list-add counter is 1,612 because the builder explicitly detects list-like
answer/evidence pairs even when evidence is open, then records the operator's
closed-scope rejection; the other structural operations have no detectable
explicit candidates in this asset.

## Recommended Next Operator Batch

These are follow-up opportunities, not generated examples or Scene1 Gold labels.
Structural mutation operators now exist and are exercised on hand-written
fixtures; measuring them against a future frozen slice requires closed,
scope-complete evidence.

1. **Broaden explicit answer list parsing (TERM-03 / LOGIC-05)**. Current
   structural list operators require an explicit enumeration in both answer
   and evidence; Markdown/list variants need fixtures and equally strict scope
   proofs before support is generated.
2. **Step reorder/deletion (LOGIC-03)**. The active operators require an
   explicitly aligned contiguous sequence, normative order wording for reorder,
   and a mandatory marker for deletion. Expand extraction only with matching
   closed evidence and tests.
3. **Exception outcome swap (LOGIC-02)**. Target explicit pairs such as
   failure condition -> E1 / termination / retry. Require the condition,
   outcome, and exception identifier to occur in evidence; do not infer a
   contradiction from generic “可能” prose.
4. **Actor/role answer operator (LOGIC-09 / structure family)**. The active
   operator requires actor/role markers in question, answer, and evidence as
   well as the closed-list predicate. Structured table extraction remains a
   follow-up; do not treat responsibility prose as a closed set.
5. **Identifier-to-definition operator (TERM-08)**. Extend the input pattern
   beyond the current `ACRONYM（full form）` only after recognizing an explicit
   definition relation such as `缩写：全称` or a table column pair. Occurrence
   of `SQL`/`BLOB` alone must remain non-actionable.
6. **Typed capability-list operator**. This is the highest-yield structural
   family for Scene1, but it needs an upstream answer segmentation contract:
   capability name, item boundaries, and evidence row/table scope. Until that
   contract exists, it is a review candidate rather than a proof-backed
   mutation operator.

The first batch should prioritize list/step/exception extraction because those
patterns dominate the answers and align with the router distribution. Numeric
operators should be expanded only after separating identifiers and counts from
parameter claims; broadening the current regex alone would create unsafe
mutations.

## Verification and Limits

The diagnosis is protected by `tests/test_mutation_coverage_diagnosis.py`.
It asserts the frozen row/evidence counts, the zero-candidate builder result
(including structural operators), the observed morphology counts, and the router no-hit count. It does not assert
any Gold verdict and does not change the frozen JSONL or core operators.
