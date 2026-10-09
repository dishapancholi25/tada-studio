# RAG for TADA Studio / TADA Chat — Sanctions & Compliance Corpus

Context derived from a transcribed meeting (Call with Sachin and 2 others). Sources: meeting transcript, meeting chat, and shared artifacts.

## Project Context

### Objective

The team is evaluating a collection of sanctions and compliance policy documents to build a RAG (Retrieval-Augmented Generation) solution for:

- TADA Chat
- TADA Studio

The current phase is document analysis and solution design. The goal is to understand the document corpus and determine:

- Appropriate ingestion strategy
- OCR requirements
- Parsing approach
- Chunking strategy
- Embedding strategy
- Retrieval strategy
- Dependencies and blockers
- High-level delivery estimate

This is not yet implementation. The team is conducting a discovery and assessment exercise.

### Participants

Meeting speakers:

- Sachin Karmakar
- Vishal Prakash Badole
- Ziye Wang
- Vipul Sharma

## Document Corpus

### Corpus Size

Shared analysis revealed:

- 114 files
- 281.5 MB total
- 5,220 PDF pages

File breakdown:

- 108 PDFs
- 5 DOCX documents
- 1 PPTX file

### Current Understanding

The team believes a single generalized ingestion strategy will not work.

Different document categories require different:

- Parsing methods
- OCR methods
- Chunking approaches
- Retrieval patterns

Documents contain combinations of:

- Text
- Tables
- Images
- Hyperlinks
- Multilingual content
- Complex layouts
- Referenced external content

## Major Technical Questions

### 1. Hyperlink Handling

Many documents contain hyperlinks pointing to external content.

Example: document sections contain references that redirect to SWIFT content, compliance references, or other policy locations.

**Option 1 — Store hyperlinks only.** At retrieval time: return document content, return hyperlink, user manually follows link.
Pros: simpler, faster, lower ingestion complexity.

**Option 2 — Crawl linked content.** Process: follow hyperlinks, extract linked content, convert linked content, index linked content within RAG.
Pros: better answer completeness.
Cons: complexity increases significantly; hyperlinks may themselves contain more hyperlinks; risk of recursive expansion; increased ingestion and maintenance cost.

Team sentiment leaned toward Option 1 initially.

### 2. Language Challenges

Documents include English and Arabic.

Observation: Arabic introduces additional challenges.

Sachin highlighted:
- UAE Arabic usage can differ from other Arabic-speaking regions.
- Intent and meaning can vary by region.
- Retrieval performance and semantic understanding may be impacted.

Therefore language handling cannot be treated as simple translation.

Potential concerns: dialect-specific meaning, intent recognition, embedding quality, retrieval accuracy.

### 3. OCR Requirements

OCR is required for some files.

Confirmed OCR-required files:
- `103pay.pdf`
- `CBUAE Guidance on Third party transactions.pdf`
- `CBUAE_EN_1853_VER1.pdf`
- `CBDDQ v1 4_Mashreq Bank_2023.pdf`

**Special notes:**

`CBUAE Guidance on Third party transactions.pdf` — contains zero extractable text, zero detected images. Problem: text appears as vector outlines. Traditional image-detection-based OCR fallback would miss it.

`CBDDQ` — contains scanned Wolfsberg due diligence questionnaire, dense 3-column table structure. Requires OCR + manual quality validation.

## Chunking Discussion

The team agreed that chunking should depend on document structure.

### Chunking Strategies Discussed

- **Fixed-Size Chunking** — basic chunk splitting. Useful for simple text documents.
- **Recursive Character Splitting** — used when structure is weak.
- **Semantic Chunking** — preferred for narrative text, natural language paragraphs. Mentioned by Ziye.
- **Document Structure-Aware Chunking** — preferred for tables, structured documents, policy frameworks. Mentioned by Ziye.
- **Hierarchical (Parent-Child) Chunking** — for preserving document hierarchy and context.
- **LLM-Driven / Agentic Chunking** — advanced strategy, potential future experimentation.

## Retrieval Design Discussion

Strategies identified:

- **Hybrid Search** — strong recommendation. Combination of semantic retrieval + keyword retrieval. Needed due to regulatory language, common terminology, exact policy references.
- **Reranking** — improve retrieval precision.
- **Context Expansion** — expand neighboring chunks. Useful when relevant information spans adjacent chunks.
- **Granularity-Retrieval Tradeoff** — balance between small chunk precision and large chunk context retention.

## Document Structure Concerns

### Tables

Significant number of tables.

Issues: multi-page tables; missing repeated headers in continuation pages; table extraction challenges.

Need: preserve continuity, convert properly. Potential output formats: Markdown, JSON.

### Images Mixed with Text

Important challenge: documents frequently contain text, diagrams, screenshots, images.

Question: should image context be linked with surrounding text? Team believes this relationship may affect retrieval quality.

## Markdown Conversion Discussion

Ziye proposed converting source documents into Markdown before ingestion.

Reason: PDF and Word documents contain formatting noise, presentation metadata, unnecessary structure.

Markdown would produce: cleaner content, more consistent chunking, easier indexing.

## Tools Mentioned

- **Docling** — strongly recommended. Used for document extraction, conversion pipelines. Team viewed it positively.
- **Marker** — mentioned as especially useful for complex PDF-to-Markdown conversion. Potential candidate for testing.
- **NVIDIA RAG Pipeline** — mentioned but considered secondary. Team agreed not to make it the immediate focus.

## Future Architecture Ideas

Sachin proposed a more advanced future-state architecture.

### AI Decision Layer

A routing layer that decides: which model to use, which extraction strategy to apply, which embedding path to use.

### Specialized Small Models

Instead of relying purely on OCR: use multimodal embedding models, use task-specific models, use specialized extractors.

Expected benefits: improved extraction, lower cost, better flexibility.

### Infrastructure Discussion

The team discussed availability of GPU resources. Mentioned: OICM platform, vLLM-based infrastructure, on-prem GPU cluster, NVIDIA H100 environment.

Sachin indicated that internal GPU resources are available and future experimentation could potentially use them after coordination with platform teams.

## Document Analysis Results Shared in Meeting Chat

### Duplicates Removed

**Pair 1**
- `FATF Recommendations 2012.pdf.coredownload.inline.pdf`
- `FATF Recommendations_.pdf`
148 pages. Duplicate.

**Pair 2**
- `KYC Standards 2024_v1.0.pdf`
- `Group KYC Standards 2024_v10.pdf`
119 pages. Duplicate.

**Pair 3**
- `CBUAE_EN_4473_VER1.pdf`
- `Guidance for LFIs on Digital Identification.pdf`
26 pages. Duplicate.

**Additional duplicate**
- `review of sanctions implementation and enforcement.pdf`
- `review of sanctions implementation and enforcement_w.pdf`
Use version with extractable text.

**Major Duplicate Removed**

`OFAC FAQs.pdf` — 177 MB, 876 pages, no extractable text. Duplicate of `OFAC Consolidated Frequently Asked Questions.pdf`. Reason removed: would consume significant OCR effort without additional value. Estimated OCR savings: 1 to 1.5 hours.

### Files Flagged For Manual Review

Potentially problematic:

- `Notice No_1399_2020 re Dormant Accounts.pdf` — 34 pages, low text density
- `Training webinar on TFS.pdf` — 70 pages, training slide deck, diagram-heavy
- `SPGMI-2828 Whitepaper.pdf` — 18 pages, infographic-heavy, chart-heavy

Recommended: visual validation after ingestion.

## Work Allocation

### Ziye
Responsible for: categorizing documents, complexity classification, table-heavy identification, classification automation using Copilot.

Proposed categories include: table-heavy, OCR-heavy, easy, difficult.

### Vipul
Responsible for: language identification.

Languages to classify: English, Arabic. Task completed by end of meeting.

Additional outcome: identified 8 Q&A documents. Highlighted in tracker using yellow markers.

## Deliverables Being Created

**Spreadsheet** tracking: document name, category, language, OCR requirement, complexity, chunking strategy.

Referenced files:
- `Sanctions Doc Tracker - updated.xlsx`
- `Sanctions RAG.xlsx`

## Key Decisions

### Agreed
- Analyze document categories before implementation.
- Different document categories require different chunking approaches.
- Markdown conversion should be investigated.
- Classify all documents first.
- Language should be tracked explicitly.
- Hyperlink content handling requires separate consideration.
- Hybrid retrieval should be part of architecture.

### Not Yet Decided
- Crawl hyperlinks or not. **Research completed 2026-10-09** — see `reports/RAG hyperlink handling compliance docs.md`: recommends neither naive option; a reference-node/metadata-graph middle ground (capture link+anchor+context at ingestion, never auto-fetch by default, govern a short SWIFT/CBUAE/FATF allowlist with OWASP-grade SSRF controls for anything actually fetched).
- Final chunking strategy per category.
- Final OCR pipeline.
- Final embedding approach.
- Final retrieval architecture.
- Whether multimodal/local models will be adopted.

## Immediate Next Actions

1. Complete document categorization.
2. Complete language tagging.
3. Review OCR-required files.
4. Identify document categories and complexity levels.
5. Map document categories to chunking strategies.
6. Estimate effort and dependencies.
7. Decide hyperlink ingestion strategy.
8. Validate Docling and Marker approaches.
9. Divide documents among team members based on category rather than simple file count.
10. Prepare recommendation for stakeholders regarding final RAG architecture.

## Concise Summary

The team is designing a RAG solution for ~114 sanctions/compliance documents (108 PDFs, 5 DOCX, 1 PPTX, ~5,220 pages). Major challenges include OCR, multilingual content (English/Arabic), tables, images, hyperlinks, scanned documents, and policy references. Current focus is corpus analysis, classification, chunking strategy selection, OCR assessment, retrieval design, and effort estimation. Proposed techniques include semantic chunking, document-structure-aware chunking, hybrid retrieval, reranking, context expansion, Markdown conversion using Docling/Marker, and category-specific ingestion strategies. The team believes a single chunking/retrieval approach will not work across the entire corpus and is building a classification-driven ingestion framework before implementation.
