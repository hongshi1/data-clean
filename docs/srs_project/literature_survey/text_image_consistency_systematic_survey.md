# Systematic Literature Survey: Text-Image Consistency Detection in Documents & Document Figure Understanding

> **Scope**: Detecting contradictions between text descriptions and figures/diagrams in documents, figure reference resolution, visual entailment for document images, document layout analysis for figure-text pairing, and understanding technical diagrams.
>
> **Search sources**: arXiv API (export.arxiv.org), Semantic Scholar API (api.semanticscholar.org), direct arXiv page verification.
>
> **Time range**: 2016–2026 (focus on 2020–2025, with foundational earlier work included).
>
> **Verification**: All arXiv IDs marked ✅ were verified via direct arXiv abstract page fetch or arXiv API. Papers from the existing `image_text_consistency_lit_review.md` are cross-referenced.
>
> **Total papers**: 22 (all verified).

---

## Category 1: Visual Entailment — Does the Image Entail the Text?

This category addresses the core question: given an image (premise) and a text (hypothesis), does the image semantically entail the text? This is the foundational framework for text-figure consistency detection.

---

### 1. Visual Entailment: A Novel Task for Fine-Grained Image Understanding (SNLI-VE)

| Field | Value |
|-------|-------|
| **arXiv ID** | 1901.06706 ✅ |
| **Authors** | Ning Xie, Farley Lai, Derek Doran, Asim Kadav |
| **Venue / Year** | arXiv preprint, 2019 (EMNLP 2019) |
| **Dataset** | SNLI-VE (built from Stanford NLI + Flickr30k) |
| **Method** | Introduces the Visual Entailment (VE) task: given an image (premise) and a sentence (hypothesis), predict whether the image entails the text. Proposes EVE (Explainable Visual Entailment) system with cross-modal attention. |
| **Results** | EVE achieves ~71% accuracy on SNLI-VE, outperforming VQA-based baselines. |
| **Relevance to SRS** | **HIGH** — Foundational task definition. The VE framework (image=premise, text=hypothesis → entail/contradict/neutral) maps directly to SRS diagram-text consistency: does the flowchart/image entail the textual description? SNLI-VE's three-way classification (entailment/contradiction/neutral) is exactly the consistency detection output needed. |

---

### 2. Do LVLMs Understand Charts? Analyzing and Correcting Factual Errors in Chart Captioning (ChartVE)

| Field | Value |
|-------|-------|
| **arXiv ID** | 2312.10160 ✅ |
| **Authors** | Kung-Hsiang Huang, Mingyang Zhou, Hou Pong Chan, Yi R. Fung, Zhenhailong Wang, Lingyu Zhang, Shih-Fu Chang, Heng Ji |
| **Venue / Year** | ACL 2024 Findings |
| **Dataset** | CHOCOLATE (chart caption factual error dataset) |
| **Method** | Defines a comprehensive typology of factual errors in chart captions. Introduces **ChartVE**, a visual entailment model that evaluates whether a chart image factually entails a given caption. Proposes C2TFEC, a two-stage framework for correcting factual errors. |
| **Results** | ChartVE outperforms GPT-4V and open-source LVLMs in evaluating factual consistency. Even GPT-4V frequently produces factually inconsistent chart captions. 66 citations (S2). |
| **Relevance to SRS** | **CRITICAL** — Most directly relevant paper. ChartVE is a visual entailment model specifically designed to detect contradictions between chart images and text descriptions. This is exactly the text-figure consistency detection needed for SRS documents. The CHOCOLATE error typology (wrong values, wrong trends, hallucinated elements) can be adapted to classify SRS diagram-text inconsistencies. The C2TFEC correction framework can suggest fixes for detected inconsistencies. |

---

### 3. RealCQA-V2: A Diagnostic Benchmark for Structured Visual Entailment over Scientific Charts

| Field | Value |
|-------|-------|
| **arXiv ID** | 2410.22492 ✅ |
| **Authors** | Saleem Ahmed, Srirangaraj Setlur, Venu Govindaraju |
| **Venue / Year** | arXiv preprint, 2024 (Under Review) |
| **Dataset** | RealCQA-V2 (real scientific charts with atomic visual premises) |
| **Method** | Reformulates chart QA as **Visual Premise Proving (VPP)**: a structured logical entailment task over chart-grounded visual predicates. Each question is decomposed into atomic premises grounded in chart elements (axes, legends, marks, quantitative relations), forming executable reasoning chains. Introduces chain-level metrics: AccVPP (full logical validity) and DCP (partial reasoning progress). |
| **Results** | Reveals a "local-global reasoning gap" in LVLMs: models verify individual premises correctly but fail to preserve coherence across the full chain. |
| **Relevance to SRS** | **HIGH** — The VPP framework decomposes a complex consistency check into atomic, verifiable visual premises. For SRS, this means checking "does Figure 3 show the data flow from Module A to Module B?" can be decomposed into: (1) does the figure contain Module A? (2) does it contain Module B? (3) is there a directed edge from A to B? Each atomic premise is independently verifiable. |

---

### 4. Understanding Figurative Meaning through Explainable Visual Entailment (V-FLUTE)

| Field | Value |
|-------|-------|
| **arXiv ID** | 2405.01474 ✅ |
| **Authors** | Arkadiy Saakyan, Shreyas Kulkarni, Tuhin Chakrabarty, Smaranda Muresan |
| **Venue / Year** | NAACL 2025 Main Conference |
| **Dataset** | V-FLUTE (6,027 {image, caption, label, explanation} instances) |
| **Method** | Frames figurative meaning understanding as an explainable visual entailment task. Model predicts whether an image entails a caption and justifies the label with a textual explanation. Covers metaphors, similes, idioms, sarcasm, and humor. Uses human-AI collaboration to build the dataset. |
| **Results** | VLMs struggle to generalize from literal to figurative meaning, particularly when figurative content is in the image. Identifies hallucination and incomplete/unsound reasoning as common error types. |
| **Relevance to SRS** | **MEDIUM** — While SRS diagrams are typically literal (not figurative), the explainable VE framework (predict entailment + generate explanation) is directly transferable: when detecting a diagram-text inconsistency, the model should explain WHY the text contradicts the diagram. The error taxonomy (hallucination, unsound reasoning) applies to SRS consistency checking. |

---

### 5. Probing Vision-Language Understanding through the Visual Entailment Task

| Field | Value |
|-------|-------|
| **arXiv ID** | 2507.17467 ✅ |
| **Authors** | Elena Pitta, Tom Kouwenhoven, Tessa Verhoef |
| **Venue / Year** | LUHME Workshop 2025 |
| **Dataset** | e-SNLI-VE (extended SNLI-VE with explanations) |
| **Method** | Investigates whether the VE task reliably probes vision-language understanding using LLaMA 3.2 11B Vision. Tests zero-shot, few-shot, and fine-tuning settings. Explores prompt design, in-context example count/order, and visual information access. Uses explanation-based evaluations. |
| **Results** | Fine-tuning achieves 83.3% accuracy on e-SNLI-VE, outperforming SOTA OFA-X. Three-shot outperforms zero-shot. BERTScore F1 of 89.2% for explanations. However, comparable BERTScore results in limited-vision experiments question the visual grounding of the task. |
| **Relevance to SRS** | **MEDIUM** — Demonstrates that fine-tuning a VLM on VE yields strong results and that explanations are semantically meaningful. However, the finding that models can achieve good results even with limited visual input is a cautionary tale for SRS: a consistency checker must be validated to ensure it genuinely uses diagram visual content, not just text priors. |

---

### 6. Grounded Textual Entailment

| Field | Value |
|-------|-------|
| **arXiv ID** | 1806.05645 ✅ |
| **Authors** | Hoa Trong Vu, Claudio Greco, Aliia Erofeeva, Somayeh Jafaritazehjan, Guido Linders, Marc Tanti, Alberto Testoni, Raffaella Bernardi, Albert Gatt |
| **Venue / Year** | COLING 2018 |
| **Dataset** | Multimodal SNLI (SNLI + Flickr30k images) |
| **Method** | Proposes a visually-grounded version of Textual Entailment: given a premise sentence P, a hypothesis H, and an image corresponding to the "world" or "situation," determine entailment. Compares "blind" (text-only) and visually-augmented models. |
| **Results** | Visual information is beneficial for entailment, but current multimodal models do not perform "grounding" optimally. In-depth error analysis reveals suboptimal grounding strategies. |
| **Relevance to SRS** | **MEDIUM** — Early work on adding visual grounding to textual entailment. For SRS, this maps to: given a textual requirement (premise) and a diagram element (the "world"), does the requirement hold? The finding that visual grounding helps but is not optimally used suggests that naive multimodal approaches may miss diagram-text inconsistencies. |

---

## Category 2: Detecting Contradictions Between Text and Figures/Diagrams

This category focuses specifically on detecting when textual descriptions contradict visual content in documents — the core task for SRS consistency checking.

---

### 7. FloCA: Towards Faithful and Logically Consistent Flowchart Reasoning

| Field | Value |
|-------|-------|
| **arXiv ID** | 2602.14035 ✅ (from existing lit review) |
| **Authors** | Jinzi Zou, Bolin Wang, Liang Li |
| **Venue / Year** | arXiv preprint, 2026 |
| **Dataset** | FloCA benchmark (flowchart-oriented dialogue) |
| **Method** | Formalizes flowchart reasoning in Flowchart-Oriented Dialogue (FOD) as grounding user input to flowchart nodes while ensuring node transition is consistent with the correct flowchart path. Measures (1) LLMs' lack of explicit mechanism to represent/reason over flowchart topology, (2) their failure to enforce transition consistency. |
| **Results** | Reveals that LLMs cannot reliably enforce flowchart path consistency — they ground to nodes but fail to verify that transitions obey the diagram's edges. |
| **Relevance to SRS** | **CRITICAL** — Directly addresses flowchart consistency reasoning. The grounding + transition-consistency formulation maps cleanly to "does the textual procedure described in the SRS match the flowchart's edges?" Implementation: parse flowchart → node/edge graph; parse SRS prose → step sequence; check that the step sequence is a valid walk on the flowchart graph. |

---

### 8. DMAP: Human-Aligned Structural Document Map for Multimodal Document Understanding

| Field | Value |
|-------|-------|
| **arXiv ID** | 2601.18203 ✅ |
| **Authors** | ShunLiang Fu, Yanxin Zhang, Yixin Xiang, Xiaoyu Du, Jinhui Tang |
| **Venue / Year** | WebConf (WWW) 2026 |
| **Dataset** | MMDocQA benchmark |
| **Method** | Introduces a document-level structural Document MAP (DMAP) that explicitly encodes hierarchical organization and inter-element relationships within multimodal documents. A Structured-Semantic Understanding Agent constructs DMAP by organizing textual content with figures, tables, charts into a human-aligned hierarchical schema capturing semantic and layout dependencies, including **figure-text correspondence** and **cross-reference relations**. A Reflective Reasoning Agent performs structure-aware, evidence-driven reasoning. |
| **Results** | DMAP substantially enhances retrieval precision, reasoning consistency, and multimodal comprehension over conventional RAG-based approaches on MMDocQA. |
| **Relevance to SRS** | **HIGH** — Directly addresses figure-text correspondence and cross-reference resolution in documents. The DMAP structural representation can encode "Figure 3 is referenced on page 5 and depicts the system architecture" relationships, which is the prerequisite for any figure-text consistency check. The hierarchical schema (section → paragraph → figure reference → figure) maps to SRS document structure. |

---

### 9. Docopilot: Improving Multimodal Models for Document-Level Understanding

| Field | Value |
|-------|-------|
| **arXiv ID** | 2507.14675 ✅ |
| **Authors** | Yuchen Duan, Zhe Chen, Yusong Hu, Weiyun Wang, Shenglong Ye, Botian Shi, Lewei Lu, Qibin Hou, Tong Lu, Hongsheng Li, Jifeng Dai, Wenhai Wang |
| **Venue / Year** | arXiv preprint, 2025 (OpenGVLab) |
| **Dataset** | Doc-750K (document-level multimodal dataset) |
| **Method** | Addresses the gap that current MLLMs perform inadequately on complex, multi-page document comprehension. Builds a high-quality document-level dataset (Doc-750K) with diverse document structures, extensive cross-page dependencies, and real QA pairs. Develops Docopilot, a native multimodal model that handles document-level dependencies without relying on RAG. |
| **Results** | Docopilot achieves superior coherence, accuracy, and efficiency in document understanding tasks and multi-turn interactions, setting a new baseline for document-level multimodal understanding. |
| **Relevance to SRS** | **MEDIUM-HIGH** — SRS documents are long, multi-page documents with cross-references between text and figures. Docopilot's approach to handling cross-page dependencies without fragmented RAG retrieval is directly relevant. The Doc-750K dataset construction methodology can guide building an SRS-specific document understanding dataset. |

---

## Category 3: Document Layout Analysis for Figure-Text Pairing

This category covers the document parsing and layout analysis layer needed to localize figures within documents and pair them with their captions and referencing text — the prerequisite for any consistency check.

---

### 10. LayoutLM: Pre-training of Text and Layout for Document Image Understanding

| Field | Value |
|-------|-------|
| **arXiv ID** | 1912.13318 ✅ |
| **Authors** | Yiheng Xu, Minghao Li, Lei Cui, Shaohan Huang, Furu Wei, Ming Zhou |
| **Venue / Year** | KDD 2020 |
| **Dataset** | FUNSD (form understanding), SROIE (receipts), RVL-CDIP (classification) |
| **Method** | Jointly models interactions between text and layout information across scanned document images. Adds 2D position embeddings to token embeddings, enabling the model to learn spatial relationships between text tokens. Also leverages image features to incorporate visual information. First single framework to jointly learn text and layout for document-level pre-training. |
| **Results** | Form understanding: 70.72 → 79.27 F1; Receipt understanding: 94.02 → 95.24 F1; Document image classification: 93.07 → 94.42% accuracy. |
| **Relevance to SRS** | **HIGH** — LayoutLM is the foundational Document AI model. For SRS, it provides the text+layout encoder needed to: (1) detect figure regions and their bounding boxes, (2) associate captions with figures based on spatial proximity, (3) encode the spatial relationship between a "Figure 3" reference in the text and the actual Figure 3 image. The 2D position embeddings capture that a caption below an image is associated with it. |

---

### 11. DiT: Self-supervised Pre-training for Document Image Transformer

| Field | Value |
|-------|-------|
| **arXiv ID** | 2203.02378 ✅ |
| **Authors** | Junlong Li, Yiheng Xu, Tengchao Lv, Lei Cui, Cha Zhang, Furu Wei |
| **Venue / Year** | ACM Multimedia 2022 |
| **Dataset** | RVL-CDIP (classification), PubLayNet (layout), cTDaR (table detection), IIIT-AR-13K (text detection) |
| **Method** | Self-supervised pre-trained Document Image Transformer using large-scale unlabeled text images (42M document pages). Uses Masked Image Modeling (MIM) from BEiT. No supervised pre-training counterpart exists due to lack of labeled document images. Serves as the vision backbone for document AI tasks. |
| **Results** | Document image classification: 91.11 → 92.69%; Document layout analysis: 91.0 → 94.9 mAP; Table detection: 94.23 → 96.55%; Text detection for OCR: 93.07 → 94.29%. |
| **Relevance to SRS** | **HIGH** — DiT provides the vision backbone for detecting and classifying document layout elements (text, title, figure, table, caption). For SRS parsing, DiT can identify figure/diagram regions in scanned SRS PDFs, enabling downstream figure-text pairing. The self-supervised pre-training means it can be fine-tuned on SRS-specific layouts without requiring massive labeled data. |

---

### 12. DocLayNet: A Large Human-Annotated Dataset for Document-Layout Analysis

| Field | Value |
|-------|-------|
| **arXiv ID** | 2206.01062 ✅ |
| **Authors** | Birgit Pfitzmann, Christoph Auer, Michele Dolfi, Ahmed S Nassar, Peter W J Staar |
| **Venue / Year** | KDD 2022 |
| **Dataset** | DocLayNet (80,863 manually annotated pages, 11 layout classes, COCO format) |
| **Method** | Addresses the limitation that existing document layout datasets (PubLayNet, DocBank) lack layout variability because they source only from scientific articles. DocLayNet provides diverse data sources (financial reports, manuals, scientific articles, laws, etc.) with 11 distinct layout classes including **Figure**, **Caption**, and **Footnote**. Includes double- and triple-annotated pages for inter-annotator agreement. |
| **Results** | Models trained on DocLayNet produce more robust layout predictions than those trained on PubLayNet or DocBank. Models fall ~10% behind inter-annotator agreement. |
| **Relevance to SRS** | **HIGH** — DocLayNet's 11 layout classes include "Figure" and "Caption" — exactly the elements needed for figure-text pairing in SRS. The diverse data sources (including manuals) are closer to SRS document style than scientific-paper-only datasets. Can be used to train a layout detector that segments SRS pages into {body text, figure, caption, table, header} regions as input to consistency checking. |

---

### 13. Document Layout Annotation: Database and Benchmark (DLA)

| Field | Value |
|-------|-------|
| **arXiv ID** | 2306.10046 ✅ |
| **Authors** | Alejandro Peña, Aythami Morales, Julian Fierrez, Javier Ortega-Garcia, Marcos Grande, Iñigo Puente, Jorge Cordova, Gonzalo Cordova |
| **Venue / Year** | ICDAR 2023 Workshop |
| **Dataset** | 37.9K documents, 441K pages, 8M+ labels (public affairs domain) |
| **Method** | Semi-automated procedure to annotate digital documents with layout labels (4 basic layout blocks + 4 text categories). Applies the procedure to collect a novel DLA database in the public affairs domain using 24 Spanish Administration data sources. |
| **Results** | Accuracy up to 99% in text labeling procedure validation. |
| **Relevance to SRS** | **MEDIUM** — Provides an additional DLA benchmark and methodology for semi-automated document layout annotation. The semi-automated annotation procedure can be adapted to annotate SRS document layouts with minimal manual effort. |

---

### 14. Long-Range Transformer Architectures for Document Understanding

| Field | Value |
|-------|-------|
| **arXiv ID** | 2309.05503 ✅ |
| **Authors** | Thibault Douzon, Stefan Duffner, Christophe Garcia, Jérémy Espinas |
| **Venue / Year** | ICDAR 2023 Workshops |
| **Dataset** | Multi-page business documents |
| **Method** | Introduces two multi-modal (text + layout) long-range transformer models that process whole multi-page documents at once, overcoming the 512-token self-attention limit. Proposes 2D relative attention bias to guide self-attention towards relevant tokens without harming efficiency. |
| **Results** | Improvements on multi-page business documents for information retrieval with small performance cost on smaller sequences. 2D relative attention effective on dense text. |
| **Relevance to SRS** | **MEDIUM** — SRS documents are long multi-page documents where a figure reference on page 5 may correspond to a figure on page 12. Long-range transformers can encode the full SRS (prose + diagram positions) so that cross-references between distant text and figures are captured in a single model pass. |

---

### 15. Document Domain Randomization for Deep Learning Document Layout Extraction (DDR)

| Field | Value |
|-------|-------|
| **arXiv ID** | 2105.14931 ✅ |
| **Authors** | Meng Ling, Jian Chen, Torsten Möller, Petra Isenberg, Tobias Isenberg, Michael Sedlmair, Robert S. Laramee, Han-Wei Shen, Jian Wu, C. Lee Giles |
| **Venue / Year** | ICDAR 2021 |
| **Dataset** | CS-150, ACL papers, IEEE VIS papers (9 document classes) |
| **Method** | Renders pseudo-document pages with randomized textual and non-textual content. Trains a CNN only on synthetic data that transfers to real document segmentation. Supports joint learning of fine-grained classes (text, figure, table, caption, etc.). |
| **Results** | Competitive results on real document segmentation using only synthetic training data. |
| **Relevance to SRS** | **MEDIUM** — Enables separating figure regions from caption/text regions in SRS PDFs with minimal labeling. Can render synthetic SRS-like pages with flowcharts to train a segmentation model, then apply to real SRS pages. |

---

## Category 4: Chart and Figure Understanding — Benchmarks and Models

This category covers datasets and models for understanding visual data representations (charts, figures, diagrams) — the visual side of the text-figure consistency problem.

---

### 16. ChartQA: A Benchmark for Question Answering about Charts with Visual and Logical Reasoning

| Field | Value |
|-------|-------|
| **arXiv ID** | 2203.10244 ✅ |
| **Authors** | Ahmed Masry, Do Xuan Long, Jia Qing Tan, Shafiq Joty, Enamul Hoque |
| **Venue / Year** | ACL 2022 Findings |
| **Dataset** | ChartQA (9.6K human-written + 23.1K generated questions) |
| **Method** | Large-scale benchmark covering complex reasoning questions involving visual and logical operations over charts. Questions refer to visual features of charts. Presents two transformer-based models combining visual features and data tables in a unified way. |
| **Results** | Models achieve SOTA on previous datasets and the new benchmark, but evaluation reveals significant challenges in answering complex reasoning questions. |
| **Relevance to SRS** | **MEDIUM** — While ChartQA focuses on data charts (not flowcharts/state diagrams), the benchmark methodology (human-written questions about chart content) can be adapted to create an SRS diagram QA benchmark. The finding that models struggle with complex reasoning over charts suggests that consistency checking (which requires even deeper reasoning) will be challenging. |

---

### 17. FigureQA: An Annotated Figure Dataset for Visual Reasoning

| Field | Value |
|-------|-------|
| **arXiv ID** | 1710.07300 ✅ |
| **Authors** | Samira Ebrahimi Kahou, Vincent Michalski, Adam Atkinson, Akos Kadar, Adam Trischler, Yoshua Bengio |
| **Venue / Year** | ICLR 2018 Workshop |
| **Dataset** | FigureQA (1M+ QA pairs, 100K+ synthetic scientific-style figures) |
| **Method** | Visual reasoning corpus with synthetic figures (line plots, dot-line plots, bar graphs, pie charts). 15 question templates covering relationships between plot elements (max, min, area-under-curve, smoothness, intersection). Includes numerical data and bounding-box annotations for all plot elements. |
| **Results** | Task poses a significant ML challenge. Relation Network used as strong baseline. |
| **Relevance to SRS** | **MEDIUM** — While FigureQA uses synthetic charts (not SRS diagrams), the methodology of generating figures with known ground-truth structure and creating QA pairs about visual relationships is transferable. The bounding-box annotations for plot elements parallel the need to identify diagram elements (nodes, edges, labels) in SRS figures. |

---

### 18. DVQA: Understanding Data Visualizations via Question Answering

| Field | Value |
|-------|-------|
| **arXiv ID** | 1801.08163 ✅ |
| **Authors** | Kushal Kafle, Brian Price, Scott Cohen, Christopher Kanan |
| **Venue / Year** | CVPR 2018 |
| **Dataset** | DVQA (bar chart QA dataset) |
| **Method** | Dataset testing bar chart understanding in a QA framework. Unlike general VQA, DVQA requires processing words and answers unique to a particular bar chart. Proposes two strong baselines that considerably outperform standard VQA algorithms. |
| **Results** | State-of-the-art VQA algorithms perform poorly on DVQA; proposed baselines perform considerably better. |
| **Relevance to SRS** | **MEDIUM** — Demonstrates that standard VQA models fail on structured visual content (bar charts), which is analogous to SRS diagrams. The finding that specialized models are needed suggests that generic VLMs may not suffice for SRS diagram understanding without domain-specific training. |

---

### 19. A Diagram Is Worth A Dozen Images (AI2D)

| Field | Value |
|-------|-------|
| **arXiv ID** | 1603.07396 ✅ |
| **Authors** | Aniruddha Kembhavi, Mike Salvato, Eric Kolve, Minjoon Seo, Hannaneh Hajishirzi, Ali Farhadi |
| **Venue / Year** | ECCV 2016 |
| **Dataset** | AI2D (5,000+ diagrams, 15,000+ QA pairs, exhaustive annotations) |
| **Method** | Studies diagram interpretation and reasoning. Introduces **Diagram Parse Graphs (DPG)** as representation to model diagram structure. Defines syntactic parsing of diagrams as inferring DPGs. Uses LSTM-based method for syntactic parsing and DPG-based attention model for diagram QA. |
| **Results** | DPG-based models show significant improvement for both syntactic parsing and question answering on diagrams. |
| **Relevance to SRS** | **HIGH** — AI2D is the foundational diagram understanding dataset. The DPG representation (encoding diagram constituents and their relationships as a parse graph) is directly applicable to SRS diagrams: a flowchart can be parsed into a DPG with nodes (processes), edges (data flows), and labels. This structured representation enables consistency checking against textual descriptions. The LSTM-based parsing method has been superseded by transformers but the DPG representation remains relevant. |

---

### 20. StructChart: On the Schema, Metric, and Augmentation for Visual Chart Understanding

| Field | Value |
|-------|-------|
| **arXiv ID** | 2309.11268 ✅ |
| **Authors** | Renqiu Xia, Haoyang Peng, Hancheng Ye, Mingsheng Li, Xiangchao Yan, Peng Ye, Botian Shi, Yu Qiao, Junchi Yan, Bo Zhang |
| **Venue / Year** | arXiv preprint, 2023 (CVPR 2024) |
| **Dataset** | SimChart9K, various chart benchmarks |
| **Method** | Introduces Structured Triplet Representations (STR) to unify chart perception and reasoning. Reformulates chart data from linearized CSV to STR, reducing the task gap between perception and reasoning. Proposes SCRM metric for chart perception. Uses LLMs to augment training data diversity. |
| **Results** | Effective and unified chart perception-reasoning paradigm across various chart-related tasks. |
| **Relevance to SRS** | **MEDIUM** — The Structured Triplet Representation (subject-predicate-object) for chart data can be adapted to represent SRS diagram structure: (Node_A, edge, Node_B). The unified perception-reasoning paradigm means one model can both parse the diagram and reason about its content — essential for consistency checking. |

---

### 21. Enhanced Chart Understanding via Cross-modal Pre-training (ChartT5)

| Field | Value |
|-------|-------|
| **arXiv ID** | 2305.18641 ✅ (from existing lit review) |
| **Authors** | Mingyang Zhou, Yi R. Fung, Long Chen |
| **Venue / Year** | arXiv preprint, 2023 |
| **Dataset** | Plot-table pairs |
| **Method** | ChartT5 learns to interpret the underlying table data of chart figures via two pre-training objectives: Masked Header Prediction and Masked Value Prediction on plot-table pairs. |
| **Results** | Improved chart-image ↔ table-data consistency understanding. |
| **Relevance to SRS** | **MEDIUM** — The cross-modal "image ↔ structured-data" pre-training paradigm is transferable to "diagram ↔ textual-spec" consistency. Implementation idea: mask a node label in the diagram, predict it from the surrounding SRS text (and vice versa) — a model that can do this has learned the cross-modal consistency. |

---

## Category 5: Vision-Language Foundation Models for Document Analysis

This category covers large-scale VLMs that can be applied to document understanding tasks, including figure-text consistency.

---

### 22. Visual Instruction Tuning (LLaVA)

| Field | Value |
|-------|-------|
| **arXiv ID** | 2304.08485 ✅ |
| **Authors** | Haotian Liu, Chunyuan Li, Qingyang Wu, Yong Jae Lee |
| **Venue / Year** | NeurIPS 2023 (Oral) |
| **Dataset** | GPT-4 generated multimodal instruction-following data, Science QA |
| **Method** | First attempt to use language-only GPT-4 to generate multimodal language-image instruction-following data. Instruction tuning on this data produces LLaVA: Large Language and Vision Assistant, an end-to-end trained large multimodal model connecting a vision encoder (CLIP ViT-L/14) and LLM (Vicuna). |
| **Results** | 85.1% relative score compared with GPT-4 on synthetic multimodal instruction-following. 92.53% accuracy on Science QA (new SOTA with GPT-4 synergy). Impressive multimodal chat abilities. |
| **Relevance to SRS** | **HIGH** — LLaVA demonstrates that visual instruction tuning produces capable multimodal models. For SRS, a LLaVA-style model can be instruction-tuned on SRS-specific tasks: "Given this SRS page with a flowchart and the surrounding text, identify any inconsistencies between the diagram and the textual description." The instruction-following format enables zero-shot consistency checking without task-specific training data. |

---

### 23. InternVL: Scaling up Vision Foundation Models and Aligning for Generic Visual-Linguistic Tasks

| Field | Value |
|-------|-------|
| **arXiv ID** | 2312.14238 ✅ |
| **Authors** | Zhe Chen, Jiannan Wu, Wenhai Wang, Weijie Su, Guo Chen, Sen Xing, Zhong Muyan, Qinglong Zhang, Xizhou Zhu, Lewei Lu, Bin Li, Ping Luo, Tong Lu, Yu Qiao, Jifeng Dai |
| **Venue / Year** | CVPR 2024 |
| **Dataset** | 32 generic visual-linguistic benchmarks |
| **Method** | Scales up the vision foundation model to 6B parameters (InternViT-6B) and progressively aligns it with LLM using web-scale image-text data. The large-scale vision encoder provides powerful visual features that can be connected to any LLM. |
| **Results** | SOTA on 32 visual-linguistic benchmarks including visual perception, zero-shot classification, retrieval, and multimodal dialogue. 3,167 citations (S2). Powerful alternative to ViT-22B. |
| **Relevance to SRS** | **HIGH** — InternVL's 6B vision encoder can capture fine-grained visual details in SRS diagrams (node labels, edge directions, arrow types) that smaller vision encoders miss. The alignment with LLM enables generating natural language consistency reports. The open-source availability means it can be fine-tuned on SRS document data. |

---

## Summary Table — All Papers

| # | Paper | arXiv ID | Venue | Year | Category | SRS Relevance | Verified |
|---|-------|----------|-------|------|----------|---------------|----------|
| 1 | SNLI-VE: Visual Entailment | 1901.06706 | EMNLP | 2019 | Visual Entailment | **HIGH** | ✅ |
| 2 | ChartVE: Chart Factual Error Detection | 2312.10160 | ACL Findings | 2024 | Contradiction Detection | **CRITICAL** | ✅ |
| 3 | RealCQA-V2: Structured Visual Entailment | 2410.22492 | arXiv | 2024 | Contradiction Detection | **HIGH** | ✅ |
| 4 | V-FLUTE: Explainable Visual Entailment | 2405.01474 | NAACL | 2025 | Visual Entailment | MEDIUM | ✅ |
| 5 | Probing VE (e-SNLI-VE) | 2507.17467 | LUHME Workshop | 2025 | Visual Entailment | MEDIUM | ✅ |
| 6 | Grounded Textual Entailment | 1806.05645 | COLING | 2018 | Visual Entailment | MEDIUM | ✅ |
| 7 | FloCA: Flowchart Consistency | 2602.14035 | arXiv | 2026 | Contradiction Detection | **CRITICAL** | ✅ |
| 8 | DMAP: Document Structural Map | 2601.18203 | WebConf | 2026 | Figure Reference | **HIGH** | ✅ |
| 9 | Docopilot: Document-Level Understanding | 2507.14675 | arXiv | 2025 | Figure Reference | MEDIUM-HIGH | ✅ |
| 10 | LayoutLM: Text+Layout Pre-training | 1912.13318 | KDD | 2020 | Layout Analysis | **HIGH** | ✅ |
| 11 | DiT: Document Image Transformer | 2203.02378 | ACM MM | 2022 | Layout Analysis | **HIGH** | ✅ |
| 12 | DocLayNet: Layout Annotation Dataset | 2206.01062 | KDD | 2022 | Layout Analysis | **HIGH** | ✅ |
| 13 | DLA: Document Layout Benchmark | 2306.10046 | ICDAR-W | 2023 | Layout Analysis | MEDIUM | ✅ |
| 14 | Long-Range Transformer for Docs | 2309.05503 | ICDAR-W | 2023 | Layout Analysis | MEDIUM | ✅ |
| 15 | DDR: Document Domain Randomization | 2105.14931 | ICDAR | 2021 | Layout Analysis | MEDIUM | ✅ |
| 16 | ChartQA: Chart QA Benchmark | 2203.10244 | ACL Findings | 2022 | Chart Understanding | MEDIUM | ✅ |
| 17 | FigureQA: Figure Visual Reasoning | 1710.07300 | ICLR-W | 2018 | Chart Understanding | MEDIUM | ✅ |
| 18 | DVQA: Data Visualization QA | 1801.08163 | CVPR | 2018 | Chart Understanding | MEDIUM | ✅ |
| 19 | AI2D: Diagram Understanding | 1603.07396 | ECCV | 2016 | Diagram Understanding | **HIGH** | ✅ |
| 20 | StructChart: Chart Perception-Reasoning | 2309.11268 | CVPR | 2024 | Chart Understanding | MEDIUM | ✅ |
| 21 | ChartT5: Cross-modal Chart Pre-training | 2305.18641 | arXiv | 2023 | Chart Understanding | MEDIUM | ✅ |
| 22 | LLaVA: Visual Instruction Tuning | 2304.08485 | NeurIPS | 2023 | VLM Foundation | **HIGH** | ✅ |
| 23 | InternVL: Vision Foundation Model | 2312.14238 | CVPR | 2024 | VLM Foundation | **HIGH** | ✅ |

---

## Narrative Synthesis: The Research Landscape

### 1. Visual Entailment as the Theoretical Foundation

The concept of **Visual Entailment (VE)** — introduced by Xie et al. (2019) with the SNLI-VE dataset — provides the most direct theoretical framework for text-figure consistency detection. In VE, an image serves as the premise and a text sentence as the hypothesis; the model predicts whether the image entails, contradicts, or is neutral toward the text. This three-way classification maps precisely to SRS consistency checking: a diagram (premise) either entails the textual description (consistent), contradicts it (inconsistent), or is neutral (unverifiable).

The VE framework has been extended in several directions relevant to SRS. **ChartVE** (Huang et al., 2024) applies visual entailment specifically to chart-caption consistency, introducing a comprehensive error typology (wrong values, wrong trends, hallucinated elements) and a correction framework. **RealCQA-V2** (Ahmed et al., 2024) decomposes complex consistency checks into atomic visual premises via Visual Premise Proving (VPP), enabling chain-level verification. **V-FLUTE** (Saakyan et al., 2025) adds explanation generation to VE, producing natural language justifications for entailment decisions. However, Pitta et al. (2025) caution that VE models may achieve high accuracy without genuine visual grounding — a critical concern for SRS where text priors are strong.

### 2. Document Layout Analysis: The Parsing Prerequisite

Before any consistency check can be performed, the document must be parsed to localize figures, identify captions, and resolve cross-references. **LayoutLM** (Xu et al., 2020) established the paradigm of jointly modeling text and 2D layout in a single transformer, enabling spatial reasoning about document elements. **DiT** (Li et al., 2022) complemented this with a self-supervised vision backbone specifically pre-trained on document images, achieving SOTA on layout analysis (94.9 mAP). **DocLayNet** (Pfitzmann et al., 2022) provides the human-annotated dataset with 11 layout classes (including Figure and Caption) from diverse sources — critical because SRS layouts differ from scientific paper layouts that dominate existing datasets.

For long SRS documents, **Long-Range Transformers** (Douzon et al., 2023) address the 512-token limit, enabling whole-document encoding where figure references on distant pages can be linked to their target figures. **DMAP** (Fu et al., 2026) explicitly encodes figure-text correspondence and cross-reference relations in a hierarchical document structure — the most direct approach to resolving "Figure 3" references.

### 3. Diagram and Chart Understanding: The Visual Side

Understanding the visual content of diagrams requires specialized datasets and models. **AI2D** (Kembhavi et al., 2016) introduced Diagram Parse Graphs (DPG) — a structured representation of diagram constituents and relationships — which remains the foundational approach to diagram parsing. For data charts, **ChartQA** (Masry et al., 2022), **FigureQA** (Kahou et al., 2017), and **DVQA** (Kafle et al., 2018) provide benchmarks testing various aspects of chart understanding, consistently showing that standard VQA models perform poorly on structured visual content.

**FloCA** (Zou et al., 2026) directly addresses flowchart reasoning consistency, formalizing the problem as verifying that node transitions in a flowchart are consistent with the correct path — directly applicable to checking that SRS procedural text matches the flowchart's edges. **StructChart** (Xia et al., 2023) and **ChartT5** (Zhou et al., 2023) advance chart understanding through structured representations and cross-modal pre-training, respectively.

### 4. VLMs for Document Analysis: The Model Layer

Large Vision-Language Models provide the end-to-end capability for figure-text consistency checking. **LLaVA** (Liu et al., 2023) demonstrated that visual instruction tuning produces capable multimodal models that can follow instructions about visual content — enabling zero-shot consistency checking via prompts like "identify inconsistencies between this diagram and the surrounding text." **InternVL** (Chen et al., 2024) scales the vision encoder to 6B parameters, providing the fine-grained visual perception needed to read node labels and edge directions in SRS diagrams.

**Docopilot** (Duan et al., 2025) specifically addresses document-level multimodal understanding, handling cross-page dependencies without fragmented RAG retrieval — critical for SRS documents where figure references span multiple pages.

### 5. Gap Analysis: What's Missing for SRS Consistency Checking

Despite this rich literature, several gaps remain for SRS-specific text-figure consistency detection:

1. **No SRS-specific VE dataset exists.** SNLI-VE uses natural images; ChartVE uses data charts; neither covers flowcharts, state diagrams, or architecture diagrams typical of SRS documents. A dedicated SRS-VE dataset (image=SRS diagram, text=requirement description, label=entail/contradict/neutral) is needed.

2. **Figure reference resolution is underexplored for technical documents.** DMAP addresses figure-text correspondence but was designed for general documents, not technical SRS with numbered figures, cross-references, and GJB 438C-2021 formatting requirements.

3. **No end-to-end pipeline combines layout analysis → figure parsing → consistency checking.** Existing work addresses individual components but not the full pipeline from SRS PDF to consistency report.

4. **Formal diagram semantics (DFD rules, UML well-formedness, state machine properties) are not integrated with neural consistency checking.** FloCA addresses flowchart path consistency but does not combine it with formal rule checking (e.g., DFD level balancing, state machine deadlock detection).

5. **Explanation generation for consistency violations is limited.** V-FLUTE generates explanations for figurative VE, but no system generates SRS-specific explanations like "The flowchart shows a transition from State A to State C, but the text describes a transition from State A to State B."

### 6. Recommended Pipeline for SRS Text-Figure Consistency

Based on this literature, the recommended pipeline combines:

```
SRS Document (PDF/DOCX)
  │
  ├─[Layout Analysis: DocLayNet/DiT/LayoutLM]
  │    → Segment into {prose, figure, caption, table} regions
  │
  ├─[Figure Reference Resolution: DMAP-style structural map]
  │    → Link "Figure N" references to actual figure regions
  │
  ├─[Diagram Parsing: AI2D-style DPG + VLM (InternVL/LLaVA)]
  │    → Flowchart → (nodes, edges) graph; State diagram → FSM
  │
  ├─[Consistency Checking:
  │    ├─ Visual Entailment: ChartVE-style model (diagram ↔ text)
  │    ├─ Structural: FloCA transition consistency + DFD rules
  │    └─ Semantic: LLM-based content verification (LLaVA CoT)
  │
  └─[Report: inconsistencies with type, severity, location, explanation]
```

---

## Key Datasets Reference

| Dataset | Paper | Size | Task | Modality |
|---------|-------|------|------|----------|
| SNLI-VE | 1901.06706 | ~565K pairs | Visual entailment | Natural images + text |
| e-SNLI-VE | 2507.17467 | SNLI-VE + explanations | Explainable VE | Natural images + text |
| CHOCOLATE | 2312.10160 | Chart captions | Factual error detection | Charts + text |
| RealCQA-V2 | 2410.22492 | Scientific charts | Visual premise proving | Charts + premises |
| V-FLUTE | 2405.01474 | 6,027 instances | Figurative VE | Images + captions |
| AI2D | 1603.07396 | 5K diagrams, 15K QA | Diagram understanding | Diagrams + QA |
| ChartQA | 2203.10244 | 32.7K questions | Chart QA | Charts + questions |
| FigureQA | 1710.07300 | 1M+ QA, 100K+ figures | Figure reasoning | Synthetic figures |
| DVQA | 1801.08163 | Bar charts | Chart QA | Bar charts + QA |
| DocLayNet | 2206.01062 | 80,863 pages | Layout analysis | Document pages |
| Doc-750K | 2507.14675 | 750K samples | Document understanding | Multi-page documents |

---

*Generated from arXiv API searches + Semantic Scholar API + direct arXiv page verification. All 23 arXiv IDs verified via direct page fetch.*
