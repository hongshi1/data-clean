# Literature Survey: Text-Table Consistency Detection and Table Understanding in Documents

**Survey Date**: July 2026  
**Focus**: 2020-2025 papers on text-table consistency, table understanding, table fact verification, and table extraction  
**Sources**: arXiv API, Google Scholar, Semantic Scholar API

---

## 1. Executive Summary

This survey systematically reviews **20 papers** across five research themes relevant to detecting contradictions between text descriptions and tables in documents (particularly SRS documents). The key finding is that while **table fact verification** (checking if a claim about table data is correct) and **table-to-text faithfulness** (ensuring generated text matches table content) are well-studied, **direct text-table contradiction detection within the same document** remains a significant research gap. No paper was found that specifically addresses detecting inconsistencies between prose descriptions and embedded tables in requirements/technical documents. This gap represents a clear opportunity for novel contribution.

---

## 2. Structured Literature Table

| # | Paper | Venue | Year | Method | Key Result | Relevance to Text-Table Consistency | Source | Verified |
|---|-------|-------|------|--------|------------|--------------------------------------|--------|----------|
| 1 | TabFact: A Large-scale Dataset for Table-based Fact Verification | ICLR 2020 | 2020 | Table-BERT + LPA (Latent Program Algorithm) | 118k statements over 16k Wikipedia tables; LPA ~65% accuracy vs. human ~92% | **Foundational**: Defines table fact verification task; LPA program synthesis approach directly applicable to checking text claims against table cells | arXiv:1909.02164 | ✅ verified (arxiv) |
| 2 | TaBERT: Pretraining for Joint Understanding of Textual and Tabular Data | ACL 2020 | 2020 | BERT extension with table column alignment; trained on 26M tables | SOTA on WikiTableQuestions; competitive on Spider | **Core method**: Joint text-table representation enables matching text statements to table content — essential for consistency checking | arXiv:2005.08314 | ✅ verified (arxiv) |
| 3 | TAPAS: Weakly Supervised Table Parsing via Pre-training | ACL 2020 | 2020 | BERT extension with cell selection + aggregation operators | SOTA on SQA (55.1→67.2); competitive on WikiSQL, WikiTQ | **Core method**: Cell-level selection enables identifying which table cells a text statement refers to — key for cross-reference resolution | arXiv:2004.02349 | ✅ verified (arxiv) |
| 4 | LogicNLG: Logical Natural Language Generation from Open-Domain Tables | ACL 2020 | 2020 | Auto-regressive rationalization for faithful table-to-text | Introduces LogicNLG benchmark for logical table-to-text consistency | **Directly relevant**: Addresses faithfulness of text generated from tables — inverse of consistency checking (text→table vs. table→text) | Google Scholar (ACL Anthology) | ✅ verified (scholar) |
| 5 | HybridQA: A Dataset of Multi-hop Question Answering over Tabular and Textual Data | Findings of EMNLP 2020 | 2020 | Multi-hop reasoning linking table cells to hyperlinked text passages | 478 citations; new benchmark for text+table cross-referencing | **Highly relevant**: Requires linking text passages to specific table cells — core capability for text-table cross-reference resolution | Google Scholar (ACL Anthology) | ✅ verified (scholar) |
| 6 | TableFormer: Table Structure Understanding with Transformers | CVPR 2022 | 2022 | DETR-based transformer for table structure recognition | 188 citations; robust table structure extraction from document images | **Relevant**: Table extraction is the first step in any text-table consistency pipeline; enables parsing tables from PDF/DOCX documents | Google Scholar (CVF) | ✅ verified (scholar) |
| 7 | ReasTAP: Injecting Table Reasoning Skills During Pre-training | EMNLP 2022 | 2022 | Synthetic reasoning example pre-training with 7 reasoning skills | SOTA on WikiSQL, WTQ, TabFact, LogicNLG | **Relevant**: Pre-training with reasoning skills improves both fact verification and table-to-text generation | arXiv:2210.12374 | ✅ verified (arxiv) |
| 8 | TAT-QA: A Question Answering Benchmark on Hybrid Tabular and Textual Content in Finance | ACL 2021 | 2021 | Hybrid QA benchmark with tabular + textual financial content | 629 citations; covers span-in-text, cell-in-table, difference, average | **Highly relevant**: Financial domain SRS-like documents with tables; directly tests text-table cross-referencing in domain-specific context | Google Scholar (ACL Anthology) | ✅ verified (scholar) |
| 9 | TACR: A Table Alignment-Based Cell Selection Method for HybridQA | Findings of ACL 2023 | 2023 | Table alignment model for cell selection in hybrid QA | Improved cell selection accuracy over baselines | **Relevant**: Explicitly aligns questions to table cells — method adaptable for matching text statements to table rows/cells | Google Scholar (ACL Anthology) | ✅ verified (scholar) |
| 10 | UTP: Bridge the Gap between Language Models and Tabular Understanding | arXiv 2023 | 2023 | Universal pre-training supporting table-text, table-only, text-only inputs; Cross-Modal Contrastive Regularization | Superior on both uni-modal (table retrieval) and cross-modal (table QA) tasks | **Relevant**: Cross-modal contrastive learning aligns table and text representations — directly useful for consistency checking | arXiv:2302.09302 | ✅ verified (arxiv) |
| 11 | TabVer: Tabular Fact Verification with Natural Logic | TACL 2024 | 2024 | Natural logic-based verification without table-specific training | Competitive on TabFact without task-specific fine-tuning | **Relevant**: Rule-based verification approach offers interpretable reasoning for consistency checking | Google Scholar (MIT Press) | ✅ verified (scholar) |
| 12 | HIPPO: Enhancing Table Understanding via Hybrid-Modal Preference Optimization | arXiv 2025 | 2025 | Direct Preference Optimization with text+image table representations | 4% improvement on table QA and fact verification | **Relevant**: Multi-modal table understanding improves fact verification accuracy | arXiv:2502.17315 | ✅ verified (arxiv) |
| 13 | RePanda: Pandas-powered Tabular Verification and Reasoning | arXiv 2025 | 2025 | Translates claims into executable pandas queries for verification | 84.09% on TabFact; 84.72% OOD on WikiFact | **Relevant**: Executable query approach provides interpretable, verifiable reasoning — adaptable for checking SRS text against tables | arXiv:2503.11921 | ✅ verified (arxiv) |
| 14 | Thucy: LLM-based Multi-Agent System for Claim Verification across Relational Databases | AAAI 2026 Workshop | 2025 | Multi-agent LLM system with SQL evidence reporting | 94.3% on TabFact (vs. 88.7% SOTA); cross-database, cross-table | **Highly relevant**: Multi-agent approach with transparent SQL evidence; scales to complex tables typical in SRS documents | arXiv:2512.03278 | ✅ verified (arxiv) |
| 15 | ATF: Adaptive Table Filtering Framework | arXiv 2025 | 2025 | Question-aware filtering with column descriptions, clustering, sparse-dense alignment | 70% cell reduction; boosts OOD TableQA; integrates with TAPAS, TAPEX | **Relevant**: Pre-processing step to reduce table size before consistency checking — useful for large SRS tables | arXiv:2506.23463 | ✅ verified (arxiv) |
| 16 | Format as a Prior: Quantifying and Analyzing Bias in LLMs for Heterogeneous Data | AAAI 2026 | 2025 | Three-stage empirical analysis of format bias (text vs. table vs. infobox vs. KG) | Format bias is systematic across model families; driven by information richness and structure quality | **Relevant**: Reveals LLM biases when processing text vs. tables — critical for designing fair consistency checking pipelines | arXiv:2508.15793 | ✅ verified (arxiv) |
| 17 | QUEST: Quality-aware Semi-supervised Table Extraction for Business Documents | ICDAR 2025 | 2025 | Quality assessment model predicting F1 scores; SSL with diversity measures | F1: 64%→74% on business docs; 42%→50% on DocILE | **Relevant**: Table extraction from business documents (similar to SRS); quality-aware extraction ensures reliable downstream consistency checking | arXiv:2506.14568 | ✅ verified (arxiv) |
| 18 | PubTables-v2: Large-scale Dataset for Full-page and Multi-page Table Extraction | arXiv 2025 | 2025 | Multi-page table extraction benchmark; VLM vs. small model comparison | Frontier models +0.354 GriTS on complex tasks; small models competitive on narrow tasks | **Relevant**: Multi-page table extraction benchmark — SRS documents often contain tables spanning multiple pages | arXiv:2512.10888 | ✅ verified (arxiv) |
| 19 | Deep Learning for Table Detection and Structure Recognition: A Survey | ACM Computing Surveys 2024 | 2024 | Comprehensive survey of DL methods for table detection and structure recognition | 67 citations; covers CNN, GAN, transformer, DETR approaches | **Relevant**: Provides landscape of table extraction methods — essential for selecting extraction tools for SRS documents | Google Scholar (ACM) | ✅ verified (scholar) |
| 20 | CRAFT: Unified Counterfactual Reasoning for Tabular QA and Fact Verification | arXiv 2026 | 2026 | Bidirectional verification with declarative statements + counterfactual variants | Consistent improvements on WikiTQ and TabFact; mitigates LLM backbone gaps | **Relevant**: Counterfactual reasoning framework — bidirectional verification concept adaptable for text-table consistency | arXiv:2606.06842 | ✅ verified (arxiv) |

---

## 3. Thematic Analysis

### Theme 1: Table Fact Verification (Checking Claims Against Table Data)

**TabFact** (Chen et al., ICLR 2020) is the foundational work, introducing 118k human-annotated statements over 16k Wikipedia tables labeled as ENTAILED or REFUTED. The paper proposes two models: **Table-BERT** (encodes linearized tables and statements as vectors) and **LPA (Latent Program Algorithm)** (parses statements into executable programs). Both achieve ~65% accuracy, far below human performance (~92%), highlighting the difficulty of table-based reasoning.

**RePanda** (Chegini et al., 2025) modernizes this approach by translating claims into executable **pandas queries**, achieving 84.09% on TabFact and strong OOD generalization (84.72% on WikiFact). The executable approach provides interpretable evidence — directly applicable to SRS consistency checking where traceability is required.

**Thucy** (Theologitis & Suciu, 2025) pushes further with a **multi-agent LLM system** that operates across relational databases (not just single tables), achieving 94.3% on TabFact. Crucially, it reports **SQL queries as evidence**, offering full transparency — a property essential for SRS document verification where stakeholders need to understand why a contradiction was flagged.

**TabVer** (Aly & Vlachos, TACL 2024) takes a different approach using **natural logic** for verification without task-specific training, demonstrating that rule-based methods can complement neural approaches.

**Key insight for SRS**: Fact verification methods verify *external claims* against tables. For SRS consistency checking, the "claims" are the text descriptions *within the same document* as the tables — a setting not directly addressed by any of these works.

### Theme 2: Table-to-Text Faithfulness (Ensuring Generated Text Matches Table Content)

**LogicNLG** (Chen et al., ACL 2020) defines the task of generating *logically faithful* text from tables. The benchmark requires that generated descriptions be consistent with table content — the inverse problem of text-table consistency checking. This line of work establishes evaluation metrics for text-table faithfulness that can be adapted for consistency detection.

**LOFT** (Zhao et al., ACL 2023) enhances both faithfulness and diversity using logic form control, generating faithful statements covering different table regions and reasoning operations.

**Key insight for SRS**: Table-to-text faithfulness research has developed metrics for measuring whether text is consistent with table data. These metrics (e.g., logical consistency checks, entailment verification) can be repurposed for detecting inconsistencies in existing text-table pairs in SRS documents.

### Theme 3: Table Understanding Pre-trained Models (Joint Text-Table Representation)

**TaBERT** (Yin et al., ACL 2020) and **TAPAS** (Herzig et al., ACL 2020) are the two foundational pre-trained models for joint text-table understanding. TaBERT aligns natural language utterances with table columns, while TAPAS extends BERT to encode tables and select cells with aggregation operators.

**ReasTAP** (Zhao et al., EMNLP 2022) injects **7 table reasoning skills** (numerical operation, temporal comparison, conjunction, etc.) during pre-training, achieving SOTA on both fact verification (TabFact) and table-to-text generation (LogicNLG).

**UTP** (Chen et al., 2023) addresses the input gap between pre-training and fine-tuning with **Cross-Modal Contrastive Regularization (CMCR)**, explicitly encouraging consistency between table-text cross-modality representations.

**HIPPO** (Wang et al., 2025) uses **hybrid-modal preference optimization** with both text and image table representations, achieving 4% improvements on fact verification.

**Key insight for SRS**: These models provide the representational foundation for matching text statements to table content. TAPAS's cell selection capability is particularly relevant — it can identify which specific cells a text statement refers to, enabling cell-level consistency checking.

### Theme 4: Cross-Reference Resolution Between Text and Tables

**HybridQA** (Chen et al., Findings of EMNLP 2020) is the key benchmark for multi-hop reasoning that links text passages to table cells via hyperlinks. It requires models to find information that spans both tabular and textual content — a core capability for text-table cross-reference resolution.

**TAT-QA** (Zhu et al., ACL 2021) extends this to the **financial domain**, with answer types including span-in-text, cell-in-table, difference, and average — directly relevant to SRS documents where financial/technical tables coexist with prose descriptions.

**TACR** (Wu et al., Findings of ACL 2023) proposes explicit **table alignment-based cell selection**, aligning questions to table cells — a method adaptable for matching SRS text statements to table rows.

**Key insight for SRS**: Cross-reference resolution methods provide the linking mechanism between text and tables. For SRS consistency checking, we need to: (1) identify which text passages refer to which tables, (2) map text statements to specific table cells/rows, and (3) verify that the mapped text and cell content are consistent. HybridQA and TACR address steps (1) and (2); step (3) requires fact verification methods.

### Theme 5: Table Extraction from Documents

**TableFormer** (Nassar et al., CVPR 2022) uses a **DETR-based transformer** for table structure recognition, achieving robust extraction from document images. It avoids the Hungarian algorithm used in standard DETR, improving efficiency.

**QUEST** (Thomas et al., ICDAR 2025) introduces **quality-aware semi-supervised learning** for table extraction from business documents, improving F1 from 64% to 74%. The quality assessment model predicts extraction quality, enabling confidence-aware downstream processing.

**PubTables-v2** (Smock et al., 2025) provides the first benchmark for **multi-page table extraction**, evaluating both frontier VLMs and small models. SRS documents frequently contain tables spanning multiple pages, making this benchmark particularly relevant.

**Deep Learning Survey** (Salaheldin Kasem et al., ACM Computing Surveys 2024) comprehensively surveys CNN, GAN, transformer, and DETR approaches for table detection and structure recognition.

**Key insight for SRS**: Table extraction is the necessary first step in any text-table consistency pipeline. For SRS documents (typically PDF or DOCX), extraction quality directly impacts downstream consistency checking accuracy. The quality-aware approach of QUEST is particularly valuable — it can flag low-confidence extractions for human review before consistency checking.

---

## 4. Gap Analysis

### Gap 1: No Direct Text-Table Contradiction Detection in Documents
**Finding**: No paper directly addresses detecting contradictions between text descriptions and tables **within the same document**. Fact verification (TabFact, RePanda, Thucy) verifies *external claims* against tables. Table-to-text faithfulness (LogicNLG, LOFT) ensures *generated* text matches tables. Neither addresses the SRS scenario where pre-existing prose and tables may be inconsistent.

**Opportunity**: Develop a method that: (1) extracts tables from SRS documents, (2) identifies text passages that reference those tables, (3) maps text statements to specific table cells, and (4) detects contradictions using fact verification techniques.

### Gap 2: No Domain-Specific (SRS/Requirements) Benchmarks
**Finding**: All existing benchmarks (TabFact, HybridQA, TAT-QA) use Wikipedia tables or financial reports. No benchmark exists for **Software Requirements Specification** documents, which have unique characteristics: traceability matrices, requirement IDs, parameter specifications, and formal cross-references.

**Opportunity**: Create a labeled dataset of SRS documents with annotated text-table inconsistencies.

### Gap 3: Limited Work on Multi-Modal Table Understanding for Consistency
**Finding**: While HIPPO (2025) explores hybrid-modal (text+image) table understanding, no work applies multi-modal approaches to consistency checking. SRS tables often contain visual elements (merged cells, color coding, hierarchical headers) that affect interpretation.

**Opportunity**: Develop multi-modal consistency checking that considers both the textual content and visual structure of tables.

### Gap 4: Lack of Interpretable Evidence for Contradictions
**Finding**: Most neural fact verification models (Table-BERT, TAPAS) are black-box. Only RePanda (pandas queries) and Thucy (SQL queries) provide executable evidence. For SRS documents used in safety-critical systems, interpretable evidence is essential.

**Opportunity**: Develop consistency checking methods that produce human-readable evidence chains (e.g., "Text states X, but Table 3 Row 5 shows Y, because...").

### Gap 5: Format Bias in LLMs
**Finding**: The "Format as a Prior" paper (AAAI 2026) reveals systematic bias in LLMs when processing text vs. tables. This bias could cause consistency checking systems to incorrectly flag or miss contradictions depending on how information is formatted.

**Opportunity**: Design consistency checking pipelines that are robust to format bias, possibly by normalizing both text and table content to a common representation before comparison.

---

## 5. Recommended Methods for SRS Text-Table Consistency Checking

Based on the literature, a hybrid pipeline for SRS text-table consistency checking would combine:

1. **Table Extraction**: Use TableFormer or QUEST for extracting tables from PDF/DOCX SRS documents, with quality assessment to flag low-confidence extractions.

2. **Text-Table Linking**: Adapt HybridQA/TACR methods to identify which text passages reference which tables and map statements to specific cells.

3. **Fact Verification**: Apply executable approaches (RePanda's pandas queries or Thucy's SQL) for interpretable, verifiable consistency checking. Use counterfactual reasoning (CRAFT) for robust verification.

4. **Pre-trained Representations**: Use TAPAS or TaBERT for joint text-table encoding to capture semantic relationships between text and table content.

5. **Bias Mitigation**: Account for format bias (per the "Format as a Prior" findings) by normalizing representations before comparison.

---

## 6. Method Comparison Summary

| Method Category | Key Papers | Approach | Interpretability | SRS Applicability |
|----------------|-----------|----------|------------------|-------------------|
| **Program Synthesis** | TabFact-LPA, RePanda | Translate claims to executable queries | High (executable code) | High — provides audit trail |
| **Neural Verification** | Table-BERT, TAPAS, HIPPO | Encode text+table as vectors | Low (black-box) | Medium — accurate but not transparent |
| **Natural Logic** | TabVer | Rule-based logical reasoning | Medium (logic rules) | High — interpretable rules |
| **Multi-Agent LLM** | Thucy, CRAFT | LLM agents with SQL/code tools | High (SQL evidence) | High — transparent + scalable |
| **Counterfactual** | CRAFT | Bidirectional verification with counterfactuals | Medium | Medium — novel but complex |
| **Pre-trained Models** | TaBERT, TAPAS, ReasTAP | Joint text-table representation | Low | Foundation layer for other methods |
| **Table-to-Text** | LogicNLG, LOFT | Faithful text generation from tables | Medium | Inverse problem — metrics adaptable |

---

## 7. Citation Summary

### Foundational Papers (2020)
- Chen, W. et al. (2020). *TabFact: A Large-scale Dataset for Table-based Fact Verification*. ICLR 2020. arXiv:1909.02164.
- Yin, P. et al. (2020). *TaBERT: Pretraining for Joint Understanding of Textual and Tabular Data*. ACL 2020. arXiv:2005.08314.
- Herzig, J. et al. (2020). *TAPAS: Weakly Supervised Table Parsing via Pre-training*. ACL 2020. arXiv:2004.02349.
- Chen, W. et al. (2020). *LogicNLG: Logical Natural Language Generation from Open-Domain Tables*. ACL 2020.
- Chen, W. et al. (2020). *HybridQA: A Dataset of Multi-hop Question Answering over Tabular and Textual Data*. Findings of EMNLP 2020.

### Table Extraction (2022-2025)
- Nassar, A. et al. (2022). *TableFormer: Table Structure Understanding with Transformers*. CVPR 2022.
- Thomas, E. et al. (2025). *QUEST: Quality-aware Semi-supervised Table Extraction for Business Documents*. ICDAR 2025. arXiv:2506.14568.
- Smock, B. et al. (2025). *PubTables-v2: A new large-scale dataset for full-page and multi-page table extraction*. arXiv:2512.10888.
- Salaheldin Kasem, M. et al. (2024). *Deep Learning for Table Detection and Structure Recognition: A Survey*. ACM Computing Surveys.

### Fact Verification (2024-2026)
- Aly, R. & Vlachos, A. (2024). *TabVer: Tabular Fact Verification with Natural Logic*. TACL 2024.
- Chegini, A.M. et al. (2025). *RePanda: Pandas-powered Tabular Verification and Reasoning*. arXiv:2503.11921.
- Theologitis, M. & Suciu, D. (2025). *Thucy: An LLM-based Multi-Agent System for Claim Verification across Relational Databases*. AAAI 2026 Workshop. arXiv:2512.03278.
- Pan, C. et al. (2026). *CRAFT: A Unified Counterfactual Reasoning Framework for Tabular QA and Fact Verification*. arXiv:2606.06842.

### Cross-Reference & Text-Table Alignment (2021-2025)
- Zhu, F. et al. (2021). *TAT-QA: A Question Answering Benchmark on a Hybrid of Tabular and Textual Content in Finance*. ACL 2021.
- Wu, J. et al. (2023). *TACR: A Table Alignment-Based Cell Selection Method for HybridQA*. Findings of ACL 2023.
- Chen, N. et al. (2023). *UTP: Bridge the Gap between Language Models and Tabular Understanding*. arXiv:2302.09302.
- Zhao, Y. et al. (2022). *ReasTAP: Injecting Table Reasoning Skills During Pre-training*. EMNLP 2022. arXiv:2210.12374.

### Emerging Methods (2025-2026)
- Wang, H. et al. (2025). *HIPPO: Enhancing the Table Understanding Capability of LLMs through Hybrid-Modal Preference Optimization*. arXiv:2502.17315.
- Jang, W. (2025). *ATF: Adaptive Table Filtering Framework*. arXiv:2506.23463.
- Liu, J. et al. (2025). *Format as a Prior: Quantifying and Analyzing Bias in LLMs for Heterogeneous Data*. AAAI 2026. arXiv:2508.15793.

---

## 8. Conclusion

The literature reveals a mature ecosystem for **table fact verification** and **table-to-text faithfulness**, with strong foundational models (TaBERT, TAPAS) and benchmarks (TabFact, HybridQA). However, the specific task of **detecting contradictions between text and tables within the same document** — particularly in technical/requirements documents like SRS — remains unaddressed. The closest existing work (fact verification, table-to-text faithfulness) provides the building blocks but does not solve the end-to-end problem. This survey identifies a clear research opportunity to develop a text-table consistency checking system for SRS documents by combining table extraction, text-table linking, and executable fact verification methods.
