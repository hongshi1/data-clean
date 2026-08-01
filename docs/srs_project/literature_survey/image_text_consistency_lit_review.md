# Image-Text Consistency Detection in Software Engineering Documents

## Literature Review: arXiv Papers + Industry Tools/Standards

> Scope: consistency between textual requirements (SRS) and visual diagrams
> (flowcharts, state diagrams, UML, DFDs) in software engineering documents.

---

## Part A — arXiv Papers (Ranked by SRS Applicability)

### Tier 1 — Directly Applicable to SRS Diagram-Text Consistency

#### 1. FloCA: Towards Faithful and Logically Consistent Flowchart Reasoning
- **arXiv**: 2602.14035 (2026)
- **Authors**: Jinzi Zou, Bolin Wang, Liang Li
- **Category**: cs.AI
- **Method**: Formalizes flowchart reasoning in flowchart-oriented dialogue
  (FOD) as grounding user input to flowchart nodes at each turn while ensuring
  node transition is consistent with the correct flowchart path. Introduces a
  benchmark measuring (1) LLMs lack explicit mechanism to represent/reason over
  flowchart topology, (2) they fail to enforce transition consistency.
- **Consistency checked**: Flowchart node-transition path consistency
  (does the traced path through the flowchart obey the diagram's edges?).
- **SRS applicability**: **HIGH**. Directly addresses flowchart consistency
  reasoning. The grounding + transition-consistency formulation maps cleanly to
  "does the textual procedure described in the SRS match the flowchart's edges?"
- **Implementable idea**: Parse flowchart image → node/edge graph (via VLM or
  detector); parse SRS prose procedure → step sequence; check that the step
  sequence is a valid walk on the flowchart graph using FloCA's transition-
  consistency formulation.

#### 2. Formalization of the Data Flow Diagram Rules for Consistency Check
- **arXiv**: 1011.0278 (2010)
- **Authors**: Rosziati Ibrahim, Siow Yen Yen
- **Category**: cs.SE
- **Method**: Formalizes DFD drawing rules (level balancing, data store rules,
  process numbering, external entity rules) and implements a tool that checks
  inter-diagram syntactic consistency across DFD levels (context → level-0 →
  level-1).
- **Consistency checked**: DFD inter-level consistency (inputs/outputs balance
  between parent and child diagrams), DFD syntax rules.
- **SRS applicability**: **HIGH**. DFDs are standard SRS artifacts; the
  formalized rule set is directly implementable as a rule-based checker over
  parsed DFD structure.
- **Implementable idea**: Extract DFD components (processes, data stores,
  external entities, data flows) via document parsing; encode Ibrahim's
  formalized rules as a constraint solver / Datalog program; flag violations.

#### 3. Integrating UML with Service Refinement for Requirements Modeling and Analysis
- **arXiv**: 1803.05367 (2018)
- **Authors**: Yilong Yang, Jing Yang, Xiaoshan Li
- **Category**: cs.SE
- **Method**: Integrates UML visual models with a service-refinement calculus
  to specify operation contracts precisely and verify consistency + refinement
  between requirements levels. UML alone cannot specify contracts or verify
  consistency; this adds a formal refinement layer.
- **Consistency checked**: Requirements refinement consistency (does a lower-
  level UML model correctly refine the higher-level requirement contract?).
- **SRS applicability**: **HIGH**. Directly targets the gap that UML diagrams
  in SRS lack precise contracts and cannot be checked for consistency.
- **Implementable idea**: Convert UML diagrams (sequence/activity) to the
  service-refinement representation; define pre/post-conditions for each
  requirement; run refinement checker to detect inconsistencies between
  diagram behavior and textual contracts.

#### 4. Natural Language Processing for Requirements Traceability (Survey)
- **arXiv**: 2405.10845 (2024)
- **Authors**: Jin L. C. Guo, Jan-Philipp Steghöfer, Andreas Vogelsang
- **Category**: cs.SE
- **Method**: Comprehensive survey of NLP techniques for requirements
  traceability over the past decade: IR-based link recovery, embedding-based
  methods, LLM-based approaches. Covers traceability between requirements and
  downstream artifacts (design, test, code).
- **Consistency checked**: Requirements-to-artifact traceability (are all
  requirements covered by design/test artifacts? are trace links correct?).
- **SRS applicability**: **HIGH**. The survey catalogs the exact NLP techniques
  (TF-IDF, LSA, word embeddings, BERT, LLM prompting) usable to link SRS
  textual requirements to diagram elements by name/reference.
- **Implementable idea**: Use the survey's taxonomy to select an embedding
  model; compute semantic similarity between requirement sentences and diagram
  node labels / captions; threshold to propose trace links; flag unmatched
  requirements as potential consistency gaps.

#### 5. TraceLLM: Leveraging LLMs with Prompt Engineering for Enhanced Requirements Traceability
- **arXiv**: 2602.01253 (2026)
- **Authors**: Nouf Alturayeif, Irfan Ahmad, Jameleddine Hassine
- **Category**: cs.SE
- **Method**: Uses LLMs with engineered prompts to recover traceability links
  between requirements and other SDLC artifacts. Compares zero-shot, few-shot,
  and chain-of-thought prompting against traditional IR methods.
- **Consistency checked**: Trace link recovery (does artifact X relate to
  requirement Y?).
- **SRS applicability**: **HIGH**. LLM-based traceability is directly applicable
  to linking SRS text requirements to diagram captions/labels.
- **Implementable idea**: For each diagram in the SRS, feed the diagram's
  caption + surrounding text + node labels to an LLM with a CoT prompt asking
  "which requirement statements does this diagram implement?"; compare LLM-
  proposed links against an expected traceability matrix.

#### 6. Early Requirements Traceability with Domain-Specific Taxonomies
- **arXiv**: 2311.12146 (2023)
- **Author**: Michael Unterkalmsteiner
- **Category**: cs.SE
- **Method**: Uses domain-specific taxonomies to establish early traceability
  from requirements to downstream artifacts (before they exist). Recommender
  system suggests trace links based on taxonomy concepts; raises perceived
  value of trace links so they persist into design/testing.
- **Consistency checked**: Requirements quality (completeness, consistency,
  redundancy) via taxonomy-grounded trace links.
- **SRS applicability**: **HIGH**. A taxonomy of SRS concepts (functions,
  inputs, outputs, states) can anchor traceability between prose and diagrams.
- **Implementable idea**: Build a domain taxonomy from the SRS glossary; map
  each diagram node to taxonomy concepts; map each requirement to concepts;
  detect requirements with no diagram coverage (orphan) and diagram nodes with
  no requirement (phantom).

#### 7. Verifiable UML Artifact-Centric Business Process Models
- **arXiv**: 1408.5094 (2014)
- **Authors**: Diego Calvanese, Marco Montali, Montserrat Estanol
- **Categories**: cs.DB, cs.SE
- **Method**: Merges UML-based business-process modeling with formal
  verification decidability results. Shows how theoretical verification
  (decidability of artifact-centric processes) transfers to a concrete UML
  modeling methodology, enabling automated consistency checking of UML
  business process models.
- **Consistency checked**: UML business-process model formal consistency
  (artifact lifecycle, data/process interaction).
- **SRS applicability**: **MEDIUM-HIGH**. Applicable when SRS contains UML
  activity/business-process diagrams; provides the formal backbone for
  verification.
- **Implementable idea**: Map SRS activity diagrams to artifact-centric
  representation; run the decidability-preserving verification to detect
  unreachable states / deadlocks / inconsistent lifecycles.

---

### Tier 2 — Foundational / Adjacent Methods

#### 8. How Requirements Quality Makes (or Breaks) Traceability Link Recovery
- **arXiv**: 2606.11834 (2026)
- **Authors**: Tobias Hey, Julian Frattini
- **Category**: cs.SE
- **Method**: Empirical study of how requirements quality defects (ambiguity,
  multiplicity, weakness) impact automated TLR performance. Shows which defects
  degrade which TLR approaches.
- **Consistency checked**: Requirements quality defect → traceability impact.
- **SRS applicability**: **MEDIUM**. Informs which SRS prose defects will break
  downstream diagram-text consistency checking.
- **Implementable idea**: Run a requirements-quality defect detector (per this
  paper's taxonomy) as a pre-filter; flag low-quality requirement sentences
  before attempting diagram-text matching.

#### 9. Morescient GAI for Software Engineering (Extended Version)
- **arXiv**: 2406.04710 (2024)
- **Authors**: Marcus Kessel, Colin Atkinson
- **Categories**: cs.SE, cs.AI
- **Method**: Argues that existing LLM code models are trained only on the
  syntactic facet of software and miss the semantic/multifacet structure
  (requirements, design, tests). Proposes "morescient" GAI that reasons over
  multiple facets of SE artifacts for checking/synthesis.
- **Consistency checked**: Cross-facet SE artifact consistency (requirements ↔
  design ↔ code ↔ tests).
- **SRS applicability**: **MEDIUM**. Conceptual framing for multi-facet
  consistency; the requirements↔design-diagram facet is exactly SRS diagram-
  text consistency.
- **Implementable idea**: Treat SRS prose and SRS diagrams as two facets of one
  system model; use a multi-facet representation to detect cross-facet
  inconsistencies.

#### 10. Using LLMs in Software Requirements Specifications: An Empirical Evaluation
- **arXiv**: 2404.17842 (2024)
- **Authors**: Madhava Krishna, Bhagesh Gaur, Arsh Verma
- **Categories**: cs.SE, cs.AI
- **Method**: Evaluates GPT-4 and CodeLlama for drafting SRS documents against
  8 quality criteria vs human benchmarks.
- **Consistency checked**: SRS generation quality (not verification).
- **SRS applicability**: **MEDIUM** (generation, not checking). Useful as a
  baseline for what a good SRS looks like, and for generating synthetic
  consistent/inconsistent pairs for training a consistency detector.
- **Implementable idea**: Use LLM-generated SRS + diagrams as positive examples;
  perturb one modality to create negative examples; train a consistency
  classifier.

#### 11. Long-Range Transformer Architectures for Document Understanding
- **arXiv**: 2309.05503 (2023)
- **Authors**: Thibault Douzon, Stefan Duffner, Christophe Garcia
- **Category**: cs.CL
- **Method**: Two new multi-modal (text + layout) long-range transformer models
  for document understanding that process whole multi-page documents at once,
  overcoming the 512-token self-attention limit.
- **Consistency checked**: Document-level text+layout understanding.
- **SRS applicability**: **MEDIUM**. Foundational document parser needed before
  any diagram-text consistency check — an SRS is a long multi-page document.
- **Implementable idea**: Use a long-range layout-aware transformer to encode
  the full SRS (prose + diagram positions) so that cross-references between
  distant text and diagrams are captured.

#### 12. Improving Information Extraction on Business Documents with Specific Pre-Training Tasks
- **arXiv**: 2309.05429 (2023)
- **Authors**: Thibault Douzon, Stefan Duffner, Christophe Garcia
- **Categories**: cs.CL, cs.AI
- **Method**: Adds two pre-training tasks to LayoutLM — one for complex layout
  understanding, one for numeric values and their organization — improving IE
  on business documents.
- **Consistency checked**: Business-document information extraction (layout +
  numeric).
- **SRS applicability**: **MEDIUM**. SRS documents are business documents with
  complex layout and numeric specs; the pre-training tasks transfer.
- **Implementable idea**: Fine-tune LayoutLM with these tasks on SRS corpora to
  extract structured requirement fields that can then be matched to diagram
  elements.

#### 13. Document Layout Annotation: Database and Benchmark
- **arXiv**: 2306.10046 (2023)
- **Authors**: Alejandro Peña, Aythami Morales, Julian Fierrez
- **Categories**: cs.IR, cs.CV, cs.DB
- **Method**: Semi-automated procedure to build a document layout analysis
  (DLA) benchmark in the public-affairs domain; detects and classifies basic
  document components.
- **Consistency checked**: Document layout segmentation.
- **SRS applicability**: **MEDIUM**. Provides the layout-detection layer that
  localizes diagrams within the SRS before consistency checking.
- **Implementable idea**: Adapt the DLA model to detect figure/diagram regions
  in SRS PDFs; feed each detected region to a diagram parser.

#### 14. Document Domain Randomization for Deep Learning Document Layout Extraction
- **arXiv**: 2105.14931 (2021)
- **Authors**: Meng Ling, Jian Chen, Torsten Möller
- **Categories**: cs.CV, cs.IR, cs.LG
- **Method**: Renders pseudo-document pages with randomized text/non-text
  content and trains a CNN that transfers to real document segmentation
  (9 classes) without real labeled data.
- **Consistency checked**: Document region segmentation (text vs figure vs
  table vs caption).
- **SRS applicability**: **MEDIUM**. Enables separating figure regions from
  caption/text regions in SRS PDFs with minimal labeling.
- **Implementable idea**: Render synthetic SRS-like pages with flowcharts; train
  DDR model; use it to segment real SRS pages into {caption, figure, body-text,
  table} regions as input to consistency checking.

#### 15. Enhanced Chart Understanding via Cross-modal Pre-training (ChartT5)
- **arXiv**: 2305.18641 (2023)
- **Authors**: Mingyang Zhou, Yi R. Fung, Long Chen
- **Categories**: cs.CL, cs.CV
- **Method**: ChartT5 learns to interpret the underlying table data of chart
  figures via two pre-training objectives: Masked Header Prediction and Masked
  Value Prediction on plot-table pairs.
- **Consistency checked**: Chart-image ↔ table-data consistency.
- **SRS applicability**: **MEDIUM**. While aimed at data charts (not
  flowcharts), the cross-modal "image ↔ structured-data" pre-training paradigm
  is directly transferable to "diagram ↔ textual-spec" consistency.
- **Implementable idea**: Adapt ChartT5's masked-prediction pre-training to
  flowchart/table pairs: mask a node label in the diagram, predict it from the
  surrounding SRS text (and vice versa) — a model that can do this has learned
  the cross-modal consistency.

#### 16. The UML as a Formal Modeling Notation (PUML)
- **arXiv**: 1409.6919 and 1409.6928 (2014)
- **Authors**: Andy Evans, Robert France, Kevin Lano
- **Category**: cs.SE
- **Method**: Precise UML (PUML) group approach — uses formal specification
  techniques to give UML notations rigorous semantics, enabling consistency
  checking that the informal UML standard cannot support.
- **Consistency checked**: UML semantic consistency (well-formedness,
  inter-diagram constraints).
- **SRS applicability**: **MEDIUM**. Provides the formal semantics layer needed
  to check UML diagrams in SRS for semantic (not just syntactic) consistency.
- **Implementable idea**: Translate SRS UML diagrams to PUML formal
  representation; run OCL-like well-formedness rules.

#### 17. Architectural Consistency Checking in Plugin-Based Software Systems
- **arXiv**: 1510.08510 (2015)
- **Authors**: Timo Greifenberg, Klaus Müller, Bernhard Rumpe
- **Category**: cs.SE
- **Method**: Domain-Specific Language (DepCoL) to define and check
  architectural constraints on plugin dependencies; counters architecture
  erosion.
- **Consistency checked**: Architecture-model ↔ implementation consistency.
- **SRS applicability**: **LOW-MEDIUM**. Architecture-focused, but the
  DSL-based constraint-checking pattern is transferable to defining SRS
  diagram-text constraints.
- **Implementable idea**: Define a DepCoL-like DSL for SRS consistency rules
  (e.g., "every process box in the DFD must appear in the requirements text");
  check automatically.

#### 18. Learning a Behavior Model of Hybrid Systems Through Model-Based Testing + ML
- **arXiv**: 1907.04708 (2019)
- **Authors**: Bernhard K. Aichernig, Roderick Bloem, Masoud Ebrahimi
- **Categories**: cs.LG, stat.ML
- **Method**: Combines automata learning with model-based testing to
  automatically generate sufficient training data and learn a hybrid-system
  behavior model.
- **Consistency checked**: Learned-model ↔ system-behavior consistency.
- **SRS applicability**: **LOW-MEDIUM**. Could learn a state-machine model from
  SRS behavior descriptions and compare to the SRS state diagram.
- **Implementable idea**: Use automata learning on SRS textual scenarios to
  infer a state machine; diff against the SRS state diagram.

---

### Tier 3 — General Vision-Language / Document-Understanding Background

These are not SE-specific but provide the multimodal ML substrate.

| arXiv ID | Title | Year | Relevance |
|----------|-------|------|-----------|
| 2210.09263 | Vision-Language Pre-training: Basics, Recent Advances, Future Trends | 2022 | VLP survey — image-text alignment foundations |
| 2202.09061 | VLP: A Survey on Vision-Language Pre-training | 2022 | VLP survey — image-text + video-text |
| 2508.19294 | Object Detection with Multimodal Large VLMs: In-depth Review | 2025 | LVLM object detection — for detecting diagram elements |
| 2504.09480 | VLM for Object Detection and Segmentation: Review & Evaluation | 2025 | VLM detection/segmentation evaluation |
| 2012.11760 | Acronym Identification & Disambiguation Shared Tasks | 2020 | Acronym disambiguation in scientific docs — SRS term consistency |
| 2510.11852 | Evaluating Open-Source VLMs for Multimodal Sarcasm Detection | 2025 | VLM image-caption consistency evaluation methodology |
| 2512.13747 | Why Text Prevails: Vision May Undermine Multimodal Medical Decision Making | 2025 | Cautionary — text-only can beat VLM; relevant to SRS where text dominates |
| 2412.02527 | The Multimodal Universe: 100TB Scientific Data | 2024 | Large-scale multimodal scientific data benchmarking |

---

## Part B — Industry Tools & Standards

### B1. IBM Engineering Requirements Management DOORS / DOORS Next

- **Vendor**: IBM (originally QSS 1991 → Telelogic 2000 → IBM 2008)
- **Current version**: DOORS 9.7.2.11 (2026-06); DOORS Next on IBM Jazz platform
- **Core capability**: Requirements management with bidirectional traceability
  - Requirements ↔ design items ↔ test plans ↔ test cases ↔ other requirements
  - Traceability matrix, traceability graph, surrogate-requirement import
- **Scripting**: DOORS eXtension Language (DXL) for custom checks
- **Integration**: OSLC (Open Services for Lifecycle Collaboration) for
  cross-tool traceability; integrates with IBM Engineering Test Management,
  Rhapsody (SysML/UML modeling), Workflow Management
- **Applicability to SRS diagram-text consistency**:
  - **Traceability layer**: DOORS can link a requirement to a diagram element
    (as a surrogate requirement or via OSLC to a modeling tool like Rhapsody).
  - **Gap**: DOORS does **not** automatically verify that the *content* of a
    flowchart matches the *content* of the requirement text — it only manages
    the *existence* of links. Content consistency still requires DXL scripts or
    external tools.
- **Implementable pattern**: Store each SRS requirement as a DOORS object;
  store each diagram node as a surrogate requirement; write DXL scripts to flag
  requirements with no diagram link and diagram nodes with no requirement link
  (coverage analysis). For *content* consistency, export both to an LLM-based
  checker.

### B2. SysML (OMG Systems Modeling Language)

- **Standard**: OMG SysML v1.6 (2019); ISO/IEC 19514:2017; **SysML v2.0
  approved July 2025, published September 2025**
- **Diagram types (9)**: Activity, Block Definition, Internal Block, Package,
  Parametric, **Requirement**, Sequence, **State Machine**, Use Case
- **Key consistency features**:
  - **Requirement diagrams** explicitly capture functional/performance/interface
    requirements with `satisfy`, `verify`, `derive`, `trace` relationships.
  - **Allocation tables** (requirements, functional, structural allocation)
    "facilitate automated verification and validation (V&V) and gap analysis."
  - **SysML v2** supports textual + graphic notation with consistent semantics,
    enabling "more automated model manipulation, consistent semantics, and
    reduced ambiguity."
  - Models exchangeable via XMI (XML Metadata Interchange) and ISO 10303 AP-233.
- **Applicability to SRS diagram-text consistency**: **HIGH**.
  - SysML Requirement diagrams + allocation tables are *the* standard way to
    make requirement-text ↔ diagram relationships machine-checkable.
  - The `satisfy`/`verify`/`trace` stereotypes are first-class consistency
    links.
  - SysML v2's textual notation means requirements can be parsed as text and
    checked against the graphical model programmatically.
- **Implementable pattern**: Author SRS in SysML v2 textual notation; use the
  v2 API to programmatically query every requirement's `satisfy`/`verify`
  links; flag requirements with no satisfying diagram element and diagram
  elements with no originating requirement. Use the model's execution semantics
  to verify state-machine/activity-diagram behavior against requirement
  contracts.

### B3. Model Checking Tools (for state-diagram / behavior consistency)

Model checking verifies whether a finite-state model satisfies a temporal-logic
specification. Directly applicable to SRS **state diagrams** and **activity
diagrams** (behavioral consistency).

| Tool | Strengths | Applicability to SRS |
|------|-----------|----------------------|
| **SPIN** | General distributed-software model checking; LTL | Verify SRS state-machine diagrams against LTL requirement properties |
| **NuSMV** | Symbolic model checking (BDD-based); CTL/LTL | Verify SRS state diagrams against temporal safety/liveness requirements |
| **UPPAAL** | Timed automata; real-time systems | Verify SRS state diagrams with timing requirements |
| **Alloy Analyzer** | Lightweight first-order relational modeling | Check SRS structural consistency (requirements ↔ components relationships) |
| **TLA+** | Leslie Lamport's specification language; behavioral | Specify SRS behavior as TLA+; model-check against invariants |
| **PRISM** | Probabilistic model checking | Verify SRS with probabilistic/uncertain requirements |
| **CADP** | Distributed process verification (CSP) | Verify SRS sequence/communication diagrams |
| **CPAchecker** | Open-source C program model checker | After generating code from SRS, verify against SRS contracts |
| **Java Pathfinder** | Java model checker | Verify Java implementation against SRS behavioral requirements |
| **PAT** | Concurrent + real-time refinement checker | Refinement checking between SRS levels |

- **Implementable pattern**:
  1. Translate SRS state diagram → input language of a model checker (e.g.,
     UML state machine → NuSMV via existing model-transformation tools).
  2. Translate each SRS textual requirement → a temporal-logic formula
     (LTL/CTL). (e.g., "the system shall never enter state X without first
     entering state Y" → `¬X W Y`).
  3. Run the model checker; any counterexample is a diagram-text inconsistency.

### B4. Requirements Traceability (Standards & Practice)

- **Definition** (IEEE 24765): degree to which a relationship can be
  established between development products; discernible association among
  requirements, system elements, verifications, tasks.
- **Mandated by safety standards**: **DO-178C** (avionics), **ISO 26262**
  (automotive), **IEC 61508** (functional safety) — critical requirements must
  be verified and verification demonstrated through traceability.
- **Visualization forms**: traceability matrix (table), traceability graph
  (nodes/edges), list, hyperlinks.
- **Technical realizations**:
  - Manual (spreadsheets — error-prone)
  - ALM-tool homogenization (single tool covers RM + design + test + code)
  - Surrogate requirements in RM tools (import non-requirement artifacts as
    traceable surrogates)
  - Dedicated traceability tool with a Traceability Information Model (TIM)
- **Empirical findings**:
  - Traceability support → 24% faster, 50% more correct maintenance tasks
    (Mäder & Egyed 2015, 71 subjects).
  - More complete traceability → statistically significant lower defect rate
    (24 OSS projects, Rempel & Mäder 2016).
  - FDA pre-market medical-device review found significant gaps between
    prescribed and filed traceability (2013).
- **Applicability to SRS diagram-text consistency**: Traceability establishes
  *that* a requirement and a diagram are linked; consistency checking verifies
  *that their content agrees*. Traceability is the prerequisite scaffold.
- **Implementable pattern**: Build a TIM (Traceability Information Model) with
  artifact types {stakeholder-requirement, system-requirement, diagram-node,
  diagram-edge, test-case}; define link types {satisfies, refines, verifies,
  depicts}; use a dedicated traceability tool or DOORS; then run content-
  consistency checks over each linked pair.

---

## Part C — Concrete Implementable Methods (Synthesis)

Combining the literature + industry standards, here are 7 concrete, ranked
methods for detecting image-text (diagram-text) inconsistency in SRS documents
with flowcharts/state diagrams:

### Method 1 (Highest leverage): SysML v2 + Allocation-Table Gap Analysis
- **What**: Author or convert SRS to SysML v2 textual+graphical notation; use
  the v2 API to query `satisfy`/`verify`/`trace` relationships and allocation
  tables; flag missing links as gaps.
- **Source**: SysML standard (B2); FloCA-style completeness (arXiv 2602.14035).
- **Checks**: Coverage consistency (every requirement depicted? every diagram
  element required?).
- **Effort**: Medium (requires SysML v2 authoring or conversion).

### Method 2: Flowchart Graph-Walk vs. Procedural-Text Walk
- **What**: Parse flowchart image → directed graph (nodes + edges) using a VLM
  or diagram parser; parse the SRS procedural text → ordered step list; check
  that the text step list is a valid walk on the flowchart graph (transition
  consistency, per FloCA).
- **Source**: arXiv 2602.14035 (FloCA); DFD rule formalization (arXiv 1011.0278).
- **Checks**: Behavioral consistency between flowchart and procedural text.
- **Effort**: Medium-High (diagram parsing is the hard part).

### Method 3: LLM-Based Trace Link Recovery + Content Verification
- **What**: Use an LLM (per TraceLLM) with chain-of-thought prompting to (a)
  recover trace links between requirement sentences and diagram
  elements/captions, then (b) for each linked pair, ask the LLM "does this
  diagram element's behavior match this requirement's stated behavior?"
- **Source**: arXiv 2602.01253 (TraceLLM); arXiv 2405.10845 (NLP traceability
  survey).
- **Checks**: Semantic content consistency per trace link.
- **Effort**: Low-Medium (prompt engineering; no training data needed for
  zero/few-shot).

### Method 4: Taxonomy-Grounded Orphan/Phantom Detection
- **What**: Build a domain taxonomy from the SRS glossary; map each diagram
  node and each requirement to taxonomy concepts; flag orphan requirements
  (no diagram coverage) and phantom diagram nodes (no requirement).
- **Source**: arXiv 2311.12146 (early traceability with taxonomies).
- **Checks**: Coverage consistency at the concept level.
- **Effort**: Medium (taxonomy construction; concept mapping).

### Method 5: Formal Rule Checker for DFD/State-Diagram Syntax
- **What**: Encode DFD rules (Ibrahim's formalization) and UML state-machine
  well-formedness rules (PUML) as a Datalog/constraint program; run over
  parsed diagram structure.
- **Source**: arXiv 1011.0278 (DFD rules); arXiv 1409.6919 (PUML semantics).
- **Checks**: Syntactic/structural consistency (level balancing, deadlock-free,
  well-formedness).
- **Effort**: Medium (rule encoding; relies on accurate diagram parsing).

### Method 6: Model Checking of State Diagrams Against Temporal Requirements
- **What**: Translate SRS state diagram → NuSMV/SPIN model; translate each SRS
  textual temporal requirement → LTL/CTL formula; run model checker.
- **Source**: Model checking tools (B3); arXiv 1408.5094 (verifiable UML
  processes); arXiv 1803.05367 (UML refinement).
- **Checks**: Behavioral/temporal consistency (safety + liveness properties).
- **Effort**: High (requires formal logic expertise + model translation).

### Method 7: Cross-Modal Masked Prediction (ChartT5-style)
- **What**: Fine-tune a vision-language model on (diagram, surrounding-text)
  pairs from SRS documents with two masked-prediction objectives: mask a
  diagram node label → predict from text; mask a text requirement → predict
  from diagram. A well-trained model's prediction confidence signals
  consistency.
- **Source**: arXiv 2305.18641 (ChartT5 cross-modal pre-training).
- **Checks**: Learned semantic consistency between diagram and text.
- **Effort**: High (needs training data; but generalizable).

---

## Part D — Recommended Pipeline (Combining Methods)

For a practical SRS diagram-text consistency checker, combine the methods:

```
SRS Document (PDF/DOCX)
  │
  ├─[Document Layout Analysis: arXiv 2105.14931, 2306.10046]
  │    → segment into {prose, figure, caption, table} regions
  │
  ├─[Diagram Parsing: VLM arXiv 2508.19294 + graph extraction]
  │    → flowchart → (nodes, edges) graph; state diagram → FSM
  │
  ├─[Text Extraction: Long-range Transformer arXiv 2309.05503]
  │    → requirement sentences + procedural descriptions + glossary
  │
  ├─[Trace Link Recovery: LLM arXiv 2602.01253 / taxonomy arXiv 2311.12146]
  │    → requirement ↔ diagram-node links
  │
  ├─[Consistency Checks (per linked pair):
  │    ├─ Coverage: Method 1 (SysML allocation) / Method 4 (taxonomy orphans)
  │    ├─ Behavioral: Method 2 (graph-walk) / Method 6 (model checking)
  │    ├─ Semantic: Method 3 (LLM content verification)
  │    └─ Syntactic: Method 5 (formal DFD/state rules)
  │
  └─[Report: inconsistencies with severity + location]
```

---

## Summary Table — All arXiv Papers

| # | arXiv ID | Title (short) | Year | Consistency Type | SRS Applicability |
|---|----------|---------------|------|------------------|-------------------|
| 1 | 2602.14035 | FloCA: Flowchart Reasoning Consistency | 2026 | Flowchart path transition | **HIGH** |
| 2 | 1011.0278 | DFD Rules Formalization for Consistency | 2010 | DFD inter-level syntax | **HIGH** |
| 3 | 1803.05367 | UML + Service Refinement for Requirements | 2018 | UML refinement consistency | **HIGH** |
| 4 | 2405.10845 | NLP for Requirements Traceability (survey) | 2024 | Requirement-artifact traceability | **HIGH** |
| 5 | 2602.01253 | TraceLLM: LLMs for Requirements Traceability | 2026 | Trace link recovery | **HIGH** |
| 6 | 2311.12146 | Early Traceability with Domain Taxonomies | 2023 | Requirements quality/coverage | **HIGH** |
| 7 | 1408.5094 | Verifiable UML Business Process Models | 2014 | UML process formal consistency | MEDIUM-HIGH |
| 8 | 2606.11834 | Requirements Quality vs TLR Performance | 2026 | Quality defect impact | MEDIUM |
| 9 | 2406.04710 | Morescient GAI for SE | 2024 | Cross-facet SE consistency | MEDIUM |
| 10 | 2404.17842 | LLMs in SRS (empirical) | 2024 | SRS generation quality | MEDIUM |
| 11 | 2309.05503 | Long-Range Transformer for Doc Understanding | 2023 | Doc text+layout | MEDIUM |
| 12 | 2309.05429 | IE on Business Documents (LayoutLM+) | 2023 | Business doc IE | MEDIUM |
| 13 | 2306.10046 | Document Layout Annotation Benchmark | 2023 | Doc layout segmentation | MEDIUM |
| 14 | 2105.14931 | Document Domain Randomization (DDR) | 2021 | Doc region segmentation | MEDIUM |
| 15 | 2305.18641 | ChartT5: Chart Understanding Cross-modal | 2023 | Chart↔table consistency | MEDIUM |
| 16 | 1409.6919 | UML as Formal Modeling Notation (PUML) | 2014 | UML semantic consistency | MEDIUM |
| 17 | 1510.08510 | Architectural Consistency (DepCoL) | 2015 | Architecture-impl consistency | LOW-MEDIUM |
| 18 | 1907.04708 | Behavior Model via MBT+ML | 2019 | Learned-model consistency | LOW-MEDIUM |

---

## Industry Tools Summary

| Tool/Standard | Type | Consistency Capability | SRS Diagram-Text Use |
|---------------|------|------------------------|----------------------|
| **IBM DOORS / DOORS Next** | Requirements management | Traceability links (existence, not content) | Link requirements to diagram elements; DXL scripts for coverage gaps |
| **SysML v1.6 / v2.0** | Modeling standard | Requirement diagrams, allocation tables, `satisfy`/`verify`/`trace` stereotypes | First-class machine-checkable requirement↔diagram links; v2 textual notation enables programmatic content checks |
| **SPIN / NuSMV / UPPAAL** | Model checkers | Temporal-logic verification of state machines | Translate SRS state diagrams → model; check against LTL/CTL requirement formulas |
| **Alloy Analyzer** | Relational model finder | Structural consistency | Check SRS structural relationships (requirements ↔ components) |
| **TLA+** | Specification language | Behavioral specification + model checking | Specify SRS behavior; check invariants |
| **DO-178C / ISO 26262 / IEC 61508** | Safety standards | Mandate traceability + verification | Require demonstrated requirement↔test↔design traceability for safety-critical SRS |
| **OSLC** | Integration standard | Lifecycle artifact linking | Cross-tool traceability between DOORS and modeling tools |

---

*Generated from arXiv API searches + Wikipedia/official documentation for
industry tools. arXiv IDs verified via the arXiv API.*
