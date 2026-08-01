# Industrial SRS Document Search Results

> Search date: 2026-07-28
> Sources: NASA NTRS, NASA GitHub, DoD/MIL-STD, GitHub, ECSS/ESA, FAA

## Summary

Found **40+ public SRS-related documents** from NASA, DoD, and open-source aerospace projects. The NASA Technical Reports Server (NTRS) alone yielded 25+ downloadable SRS PDFs. Key highlights:

- **NASA HDTN SRS** (2024, 164 pages) following NPR 7150.2D Class B — the highest-quality modern aerospace SRS found
- **Flight Guidance System SRS** written in RSML-e formal specification language
- **ICESat/GLAS Science Software SRS** for spacecraft instrument data processing
- **MIL-STD-498 SRS template** — the complete DoD SRS format specification
- **NASA CryptoLib/SBN/spacewasm** — formal "shall" requirements on GitHub

---

## 1. NASA NTRS Documents (Downloadable PDFs)

All documents are **public domain** (Work of the US Gov, Public Use Permitted) and freely downloadable via:
```
https://ntrs.nasa.gov/api/citations/{ID}/downloads/{filename}
```

### 1.1 High-Priority SRS Documents (Recommended for Analysis)

| # | Title | NTRS ID | Center | Date | Type | Pages | PDF | System Type | Standard |
|---|-------|---------|--------|------|------|-------|-----|-------------|----------|
| 1 | HDTN 7150.2D Class B Software Requirements Specification (SRS) | 20240011318 | Glenn Research Center | 2024-09-30 | TM | 164 | Yes | Space communications (Delay Tolerant Networking) | NASA NPR 7150.2D Class B |
| 2 | HDTN Test Framework Software Requirements Specification and Design Description | 20240014467 | Glenn Research Center | 2024-12-06 | TM | — | Yes | Space communications test framework | NASA NPR 7150.2D |
| 3 | Flight Guidance System Requirements Specification | 20030065162 | Langley Research Center | 2003 | CR | — | Yes | Avionics (regional jet FGS mode logic) | RSML-e formal spec |
| 4 | ICESat (GLAS) Science Software Requirements Document - Volume 3 | 20020061450 | Goddard Space Flight Center | 2002 | TM | — | Yes | Spacecraft instrument (laser altimeter) | NASA software engineering |
| 5 | HSCT4.0 Application: Software Requirements Specification | 20010055695 | Langley Research Center | 2001 | TM | — | Yes | High-speed civil transport (HSCT) | NASA HPC application |
| 6 | Master Software Requirements Specification | 20060022635 | Ames Research Center | 2006 | Other | — | Yes | Grid computing (NASA IPG / Globus GRAM) | — |
| 7 | Incubator Display Software Cost Reduction Toolset SRS | 20060053376 | Ames Research Center | 2006 | Other | — | Yes | ISS incubator display (Lockheed Martin) | NASA subcontract |
| 8 | Software requirements: Guidance and control software development specification | 19900017211 | Legacy CDMS | 1990 | — | — | Yes | Spacecraft guidance & control | DSN software standards |
| 9 | NSSC-2 operating system design requirements specification | 19800011579 | Legacy CDMS | 1980 | — | — | Yes | Operating system (NSSC-2) | — |
| 10 | HDTN Software Requirements Analysis | 20240004702 | Glenn Research Center | 2024-05-20 | TM | — | Yes | Space communications protocol analysis | IETF RFC, CCSDS |

**Download URLs (key documents):**
- HDTN SRS: `https://ntrs.nasa.gov/api/citations/20240011318/downloads/TM-20240011318.pdf`
- HDTN Test Framework SRS: `https://ntrs.nasa.gov/api/citations/20240014467/downloads/TM-20240014467.pdf`
- Flight Guidance System SRS: `https://ntrs.nasa.gov/api/citations/20030065162/downloads/20030065162.pdf`
- ICESat GLAS SRS: `https://ntrs.nasa.gov/api/citations/20020061450/downloads/20020061450.pdf`
- HSCT4.0 SRS: `https://ntrs.nasa.gov/api/citations/20010055695/downloads/20010055695.pdf`

### 1.2 Additional SRS-Related Documents (Formal Methods, Traceability)

| # | Title | NTRS ID | Center | Date | Type | PDF | Relevance |
|---|-------|---------|--------|------|------|-----|-----------|
| 11 | Formalizing Space Shuttle Software Requirements | 20040110898 | Langley Research Center | 2004 | Preprint | Yes | Formal methods for Space Shuttle flight software requirements |
| 12 | Experience report: Using formal methods for requirements analysis of critical spacecraft software | 19950024826 | Legacy CDMS | 1995 | Conf. Paper | Yes | Formal specification and analysis of spacecraft requirements |
| 13 | Simplifying Requirements Formalization for Resource-Constrained Mission-Critical Software | 20230005275 | Ames Research Center | 2023 | Conf. Paper | Yes | Modern requirements formalization for mission-critical software |
| 14 | Preparation guide for class B software specification documents | 19800003556 | Legacy CDMS | 1980 | CR | Yes | Guide for Class B software spec preparation (DSN standards) |
| 15 | Flight software requirements and design support system | 19800021560 | Legacy CDMS | 1980 | — | Yes | Flight software requirements support tools |
| 16 | Compositional Specification of Software Architecture | 20020073030 | Ames Research Center | 2002 | TM | Yes | Software architecture specification |
| 17 | Autonomous Real Time Requirements Tracing | 20140008567 | — | 2014 | — | Yes | Requirements traceability automation |
| 18 | HDTN SRS Presentation to CCSDS | 20240013587 | Glenn Research Center | 2024 | Presentation | Yes | SRS overview presentation (CCSDS) |

### 1.3 System Specification Documents (Air Traffic Management)

| # | Title | NTRS ID | Center | Date | Type | PDF | System Type |
|---|-------|---------|--------|------|------|-----|-------------|
| 19 | ATD-2 IADS System Specification - Metroplex & TOS | 20210021679 | Ames Research Center | 2021 | System Spec | Yes | Air traffic management (FAA-related) |
| 20 | ATD-2 IADS System Specification - Core STBO | 20205005898 | Ames Research Center | 2020 | System Spec | Yes | Air traffic management (FAA-related) |
| 21 | Space Generic Open Avionics Architecture (SGOAA) standard specification | 19940017802 | Legacy CDMS | 1994 | CR | Yes | Space avionics architecture |

### 1.4 Requirements Specification Language (RSL) Documents

| # | Title | NTRS ID | Date | PDF |
|---|-------|---------|------|-----|
| 22 | Reference manual for a Requirements Specification Language (RSL), version 2.0 | 19940015566 | 1994 | Yes |
| 23 | Tools reference manual for a Requirements Specification Language (RSL), version 2.0 | 19940018652 | 1994 | Yes |
| 24 | Requirements Specification Language (RSL) and supporting tools | 19930003157 | 1993 | Yes |

### 1.5 NTRS Search API

The NTRS search API was reverse-engineered. It uses a **POST** endpoint:

```bash
curl -s -X POST "https://ntrs.nasa.gov/api/citations/search" \
  -H "Content-Type: application/json" \
  -d '{"q":"software requirements specification","page":{"size":25,"number":0}}'
```

Individual citation metadata:
```bash
curl -s "https://ntrs.nasa.gov/api/citations/{ID}"
```

Download files:
```bash
curl -sL -o document.pdf "https://ntrs.nasa.gov/api/citations/{ID}/downloads/{filename}"
```

---

## 2. NASA GitHub Repositories (Formal Requirements Documents)

These are **real NASA software projects** with formal "shall" requirements in version control.

### 2.1 nasa/CryptoLib — CCSDS SDLS Requirements

| Field | Value |
|-------|-------|
| URL | https://github.com/nasa/CryptoLib/blob/main/docs/requirements.md |
| Source | NASA Goddard Space Flight Center |
| Format | Markdown |
| Standard | CCSDS 355.0-B-2 (SDLS), CCSDS 355.1-B-1 (SDLS-EP) |
| System type | Space communications security (CCSDS Space Data Link Security) |
| Requirements | 70+ formal "shall" statements organized by PICS categories |
| Numerical constraints | Yes (bit lengths 0-15, field positions, MAC lengths, sequence numbers) |
| Tables/figures | No (structured list format with PICS IDs like A4/1, A6/1, A7.1.1/1) |
| Traceability | PICS IDs map to CCSDS standard sections |
| Freely downloadable | Yes (open source, Apache 2.0) |

**Key features:** Requirements reference specific CCSDS standard clauses, include numerical parameters (bit positions, field lengths), and cover encryption, authentication, key management, and security associations.

### 2.2 nasa/SBN — Software Bus Networking Requirements

| Field | Value |
|-------|-------|
| URL | https://github.com/nasa/SBN/blob/master/doc/Requirements.md |
| Source | NASA (cFS ecosystem) |
| Format | Markdown |
| Standard | Core Flight System (cFS) application interface |
| System type | Spacecraft flight software (inter-process messaging) |
| Requirements | 30+ formal "shall" statements with unique IDs (SBN1000-SBN2009) |
| Numerical constraints | Yes (network-byte order, configurable max networks/peers) |
| Rationale | Each requirement includes a "Rationale:" explanation |
| Traceability | Requirement IDs (SBN1000, SBN1001.1, etc.) |
| Freely downloadable | Yes (open source, Apache 2.0) |

**Key features:** Requirements include rationale statements, hierarchical IDs (SBN1000, SBN1000.1, SBN1000.1.1), and cover network reliability, radiation-induced errors, resource constraints, and message filtering.

### 2.3 nasa/spacewasm — WebAssembly Interpreter Requirements

| Field | Value |
|-------|-------|
| URL | https://github.com/nasa/spacewasm/blob/main/docs/REQUIREMENTS.md |
| Source | NASA (adapted from DLR-FT) |
| Format | Markdown (table format: ID, Title, Statement, Rationale) |
| Standard | Wasm 1.0 Recommendation |
| System type | Flight software (WebAssembly interpreter for space) |
| Requirements | 17 formal requirements (REQ-1 through REQ-17) |
| Numerical constraints | Yes (fuel-bounded execution, fixed-size pages, libm 0.2.8) |
| Tables | Yes (4-column requirements table) |
| Freely downloadable | Yes (open source) |

**Key features:** Table format with rationale column, covers bare-metal execution, bounded memory/execution, serialization, instrumentation, and certification evidence.

### 2.4 Other NASA GitHub Repos with Requirements Documents

| Repository | Path | Description |
|-----------|------|-------------|
| nasa/icarous | apps/SBN/doc/Requirements.md | ICAROUS SBN requirements (similar to nasa/SBN) |
| nasa/fprime | */docs/sdd.md (multiple) | F' flight software framework — Software Design Descriptions for components (Drv/Udp, Svc/Version, Svc/FileWorker, etc.) |
| nasa/cFS | gh-pages/cfe-usersguide.pdf | cFE User's Guide (PDF) |
| nasa/cFS | gh-pages/osal-apiguide.pdf | OSAL API Guide (PDF) |

---

## 3. DoD / Military Standard Documents

### 3.1 MIL-STD-498 SRS Template (Complete)

| Field | Value |
|-------|-------|
| URL | https://github.com/bradfa/MIL-STD-498/blob/master/SRS.html.md |
| Source | DoD MIL-STD-498 (converted to Markdown) |
| Format | Markdown / HTML |
| Standard | MIL-STD-498 (Software Development and Documentation) |
| System type | Generic DoD software (defense) |
| Tables | Yes (interface data elements, qualification methods, traceability) |
| Freely downloadable | Yes |

**SRS structure (18 sections):**
1. Scope (Identification, System overview, Document overview)
2. Referenced documents
3. Requirements:
   - 3.1 Required states and modes
   - 3.2 CSCI capability requirements
   - 3.3 CSCI external interface requirements (detailed data element specs)
   - 3.4 CSCI internal interface requirements
   - 3.5 CSCI internal data requirements
   - 3.6 Adaptation requirements
   - 3.7 Safety requirements
   - 3.8 Security and privacy requirements
   - 3.9 CSCI environment requirements
   - 3.10 Computer resource requirements (hardware, utilization, software, communications)
   - 3.11 Software quality factors
   - 3.12 Design and implementation constraints
   - 3.13 Personnel-related requirements
   - 3.14 Training-related requirements
   - 3.15 Logistics-related requirements
   - 3.16 Other requirements
   - 3.17 Packaging requirements
   - 3.18 Precedence and criticality of requirements
4. Qualification provisions (Demonstration, Test, Analysis, Inspection, Special)
5. Requirements traceability (bidirectional: CSCI↔System)
6. Notes

**Related MIL-STD-498 documents in same repo:** COM, CPM, DBDD, FSM, IDD, IRS, OCD, SCOM, SDD, SDP, SIOM, SIP, SPS, SSDD, SSS, STD, STP, STR, STRP, SUM, SVD

### 3.2 DI-IPSC-81433A — SRS Data Item Description

| Field | Value |
|-------|-------|
| URL | http://www.everyspec.com/DATA-ITEM-DESC-DIDs/DI-IPSC/DI-IPSC-81433A_3709/ |
| Source | DoD (MIL-STD-498 Data Item Description) |
| Format | PDF (604 KB) |
| Date | 15-DEC-1999 |
| Standard | MIL-STD-498 / DI-IPSC-81433A |
| Freely downloadable | Yes (everyspec.com — may require browser session for download) |

### 3.3 Other MIL-STD-498 Repositories

| Repository | URL | Contents |
|-----------|-----|----------|
| dapperfu/markdown_Requirements | https://github.com/dapperfu/markdown_Requirements | SRS.md, IRS.md, SVD.md, OCD.md (MIL-STD-498 templates) |
| viableindustries/MIL-STD-498 | https://github.com/viableindustries/MIL-STD-498 | MIL-STD-498 document set |

---

## 4. GitHub SRS Template Repositories (IEEE Standards)

| Repository | Stars | Standard | Format | URL |
|-----------|-------|----------|--------|-----|
| jam01/SRS-Template | 405 | IEEE 830 / ISO/IEC/IEEE 29148:2011 | Markdown | https://github.com/jam01/SRS-Template |
| jpeisenbarth/SRS-Tex | 157 | IEEE | LaTeX | https://github.com/jpeisenbarth/SRS-Tex |
| marcobuschini/Software-Requirements-Specification | 65 | Karl Wiegers template | Markdown | https://github.com/marcobuschini/Software-Requirements-Specification |
| bonellia/srs-ieee-latex | 20 | IEEE | LaTeX | https://github.com/bonellia/srs-ieee-latex |
| RafaelGorski/Problem-Based-SRS | 31 | Problem-Based SRS | — | https://github.com/RafaelGorski/Problem-Based-SRS |
| wxinix/IEEE-29148-SRS-LaTeX-Template | 7 | IEEE 29148:2018 | LaTeX | https://github.com/wxinix/IEEE-29148-SRS-LaTeX-Template |
| cemantix-org/ieee-srs | 6 | IEEE | — | https://github.com/cemantix-org/ieee-srs |

---

## 5. Standards Referenced by Found Documents

| Standard | Title | Domain | Found In |
|----------|-------|--------|----------|
| NASA NPR 7150.2D | NASA Software Engineering Requirements | Aerospace | HDTN SRS (NTRS 20240011318) |
| MIL-STD-498 | Software Development and Documentation | Defense | bradfa/MIL-STD-498 |
| DI-IPSC-81433A | SRS Data Item Description | Defense | everyspec.com |
| IEEE 830-1998 | Recommended Practice for SRS | Generic | Wikipedia, GitHub templates |
| ISO/IEC/IEEE 29148:2018 | Systems & Software Engineering — Requirements Engineering | Generic | Wikipedia, GitHub templates |
| CCSDS 355.0-B-2 | Space Data Link Security Protocol | Space comms | NASA CryptoLib |
| CCSDS 355.1-B-1 | SDLS Extended Procedures | Space comms | NASA CryptoLib |
| ECSS-E-ST-40C | ESA Software Engineering | Aerospace (ESA) | (website unavailable — ecss.nl returned 503) |
| DO-178C | Software Considerations in Airborne Systems | Avionics | (not found on NTRS; RTCA paid standard) |
| RSML-e | Requirements State Machine Language | Avionics | Flight Guidance System SRS (NTRS 20030065162) |

---

## 6. Documents NOT Found / Access Limited

| Source | Status | Notes |
|--------|--------|-------|
| FAA SRS documents | Not found | FAA website returned 404; NTRS has ATD-2 IADS (air traffic mgmt) specs |
| ESA ECSS-E-ST-40C | Unavailable | ecss.nl returned 503 (service unavailable) |
| DO-178C SRS examples | Not found | RTCA DO-178C is a paid standard; no public SRS examples found |
| IBM DOORS sample SRS | Not found | IBM requires login for sample documents |
| Automotive (ISO 26262) SRS | Not found | No public automotive SRS found on GitHub/NTRS |
| Medical (IEC 62304) SRS | Not found | kernel-medical/iec62304-embedded-drivers exists but is a template, not a filled SRS |

---

## 7. Recommended Documents for SRS Consistency Research

Based on the project goal (GJB 438C SRS consistency checking with numerical constraints, tables, and traceability):

### Tier 1: Best Candidates (Download and Analyze First)

1. **HDTN 7150.2D Class B SRS** (NTRS 20240011318) — 164 pages, 2024, NASA NPR 7150.2D Class B
   - Modern aerospace SRS with full requirements, traceability, and qualification methods
   - Download: `https://ntrs.nasa.gov/api/citations/20240011318/downloads/TM-20240011318.pdf`

2. **Flight Guidance System SRS** (NTRS 20030065162) — Avionics, RSML-e formal specification
   - Formal requirements specification for flight guidance mode logic
   - Download: `https://ntrs.nasa.gov/api/citations/20030065162/downloads/20030065162.pdf`

3. **ICESat GLAS Science Software SRS** (NTRS 20020061450) — Spacecraft instrument
   - Software requirements for laser altimeter data processing
   - Download: `https://ntrs.nasa.gov/api/citations/20020061450/downloads/20020061450.pdf`

4. **NASA CryptoLib Requirements** (GitHub) — CCSDS SDLS security requirements
   - 70+ "shall" requirements with numerical constraints (bit lengths, field positions)
   - URL: https://raw.githubusercontent.com/nasa/CryptoLib/main/docs/requirements.md

5. **NASA SBN Requirements** (GitHub) — Flight software networking requirements
   - 30+ "shall" requirements with rationale and hierarchical IDs
   - URL: https://raw.githubusercontent.com/nasa/SBN/master/doc/Requirements.md

### Tier 2: Good Candidates (For Comparison)

6. **HDTN Test Framework SRS** (NTRS 20240014467) — SRS + Design Description
7. **HSCT4.0 SRS** (NTRS 20010055695) — High-speed civil transport
8. **MIL-STD-498 SRS Template** (GitHub bradfa/MIL-STD-498) — Complete DoD SRS format
9. **ATD-2 IADS System Specification** (NTRS 20210021679) — Air traffic management
10. **NASA spacewasm Requirements** (GitHub) — Table format with rationale

### Tier 3: Reference Documents

11. **Formalizing Space Shuttle Software Requirements** (NTRS 20040110898)
12. **Master SRS** (NTRS 20060022635) — Grid computing
13. **Incubator Display SRS** (NTRS 20060053376) — ISS display
14. **Preparation guide for class B software spec documents** (NTRS 19800003556)
15. **Autonomous Real Time Requirements Tracing** (NTRS 20140008567)

---

## 8. Key Observations for GJB 438C Comparison

1. **NASA NPR 7150.2D** is the NASA equivalent of GJB 438C — both are government software engineering standards that mandate SRS documents with specific structure and requirements.

2. **MIL-STD-498** (DoD) is the predecessor to IEEE 12207 and is structurally similar to GJB 438C — both define SRS with:
   - Capability requirements
   - Interface requirements (detailed data element specifications)
   - Safety/security requirements
   - Computer resource requirements
   - Qualification methods (test/analysis/inspection/demonstration)
   - Requirements traceability (bidirectional)

3. **NASA CryptoLib** requirements use PICS (Protocol Implementation Conformance Statements) format, which maps individual requirements to standard clauses — similar to GJB compliance checking.

4. **Numerical constraints** are present in:
   - CryptoLib (bit lengths, field positions, MAC lengths)
   - spacewasm (fuel bounds, page sizes, memory limits)
   - SBN (max networks, max peers, byte ordering)
   - HDTN SRS (data rates, protocol parameters — in 164-page document)

5. **Tables** are expected in:
   - HDTN SRS (164 pages, likely contains requirements tables and traceability matrices)
   - MIL-STD-498 SRS template (interface data elements, qualification methods, traceability)
   - spacewasm (requirements table with ID/Title/Statement/Rationale columns)

6. **Traceability matrices** are explicitly required by:
   - MIL-STD-498 SRS (Section 5: Requirements traceability)
   - NASA NPR 7150.2D (requirements traceability is a key process area)
   - ATD-2 IADS System Specification (includes requirements verification matrix)
