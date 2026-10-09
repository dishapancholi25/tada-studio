# Horizon Scanning — Presales Demo

---

## Input

The input is a regulatory directive document — in this case a 200-300 page EU regulation. For demo purposes we use an extract rather than the full document, but the workflow is built to handle the full text.

> **Capital Requirements Directive VI (CRD VI)**
>
> Directive (EU) 2024/1619 of the European Parliament and of the Council of 31 May 2024 amending Directive 2013/36/EU as regards supervisory powers, sanctions, third-country branches, and environmental, social and governance risks.

The PDF is uploaded directly into the workflow input. Everything from here is automated.

<img width="636" height="528" alt="image" src="https://github.com/user-attachments/assets/3bd89f8e-9176-4db5-9865-0ec7c52ee3d1" />

---

## Workflow Overview

The workflow processes a large regulatory document through three specialised agents before handing off to a human for review. For this demo, we stop when the Action Plan is produced.

| # | Agent | Role |
|---|-------|------|
| 1 | **Intelligence** | Ingests the directive, generates an executive summary, categorises it against internal taxonomies, and performs a preliminary materiality and relevance assessment. |
| 2 | **Assignment** | Analyses the summary and extracted topics to identify and route the alert to the correct Risk Domain Owners and secondary stakeholders using the internal expertise matrix. |
| 3 | **Analysis & Drafting** | Cross-references every obligation and deadline in the directive against internal policies, procedures, and systems — then produces a detailed Impact Assessment and preliminary Action Plan. |

The human Risk Steward reviews and approves the Action Plan. Workflow closure and task tracking run separately.

<img width="1488" height="664" alt="image" src="https://github.com/user-attachments/assets/58be3de9-fe3e-48e0-a0a4-4bcb1ac0b20e" />

---

## Demo

### Stop 1 — Intelligence Summary Complete

The Intelligence Agent has processed the directive. It has produced a structured executive summary covering
the key objectives and most significant changes (new supervisory powers, ESG risk mandates, third-country
branch rules), assigned primary and secondary categorisation tags, and flagged preliminary materiality —
in this case high, due to impacts on capital requirements across EU banking subsidiaries.

<img width="1380" height="620" alt="image" src="https://github.com/user-attachments/assets/ba366708-7d56-419d-9ca9-206d114fd00b" />

---

### Stop 2 — Assigned to Risk Domain Owners

The Assignment Agent has matched the directive's topics against the internal expertise matrix and identified
the primary owners — for example, Head of Regulatory Compliance for general interpretation, Head of ERM for
ESG aspects, and Head of International Banking for third-country branch rules. Automated notifications have
been triggered to all assigned parties.

<img width="1392" height="799" alt="image" src="https://github.com/user-attachments/assets/90774255-e51d-4e2b-8f24-e75c4f348a7a" />

---

### Stop 3 — Action Plan Ready for Human Review

The Analysis & Drafting Agent has completed the deep impact assessment. It has extracted every specific
obligation, deadline, and change from the directive and cross-referenced them against the bank's internal
policies, procedures, and IT systems. The output is a near-complete Impact Assessment document and a
preliminary Action Plan — including specific tasks, suggested accountable executives, proposed timelines,
and resource considerations.

This is where the automated workflow ends. The human reviews, adjusts, and approves.

<img width="1404" height="801" alt="image" src="https://github.com/user-attachments/assets/57b5570b-17e0-4d30-b8b1-d069e6636d69" />
