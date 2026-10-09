# Dispute Management — Presales Demo

---

## Input

A queue of card dispute cases arrives in the platform. For this demo we use the first record:

> **Queue #001 — David Chen — Dispute vs. AUTHENTIC-SNEAKERS-PLUS ($250.00) — Item Not as Described**
>
> - **Case ID:** CDS8432112
> - **Disputed Transaction:** txn_K1L2M3N4P5Q6R7S8 — $250.00 USD — 2025-10-20
> - **Merchant:** AUTHENTIC-SNEAKERS-PLUS
> - **Channel:** Web Portal Self-Service
>
> Card Member: *"I purchased a pair of limited edition sneakers advertised as '100% authentic, new in box.' The item I received is clearly a cheap counterfeit. The seller is refusing to accept a return, claiming 'all sales final.'"*

This is pasted directly into the workflow input field. Everything from here is automated.

<img width="595" height="594" alt="image" src="https://github.com/user-attachments/assets/b81ba923-4190-4aff-ba1f-ca6185bf350d" />

---

## Workflow Overview

The workflow runs a team of five specialised agents, each with a distinct role:

| # | Agent | Role |
|---|-------|------|
| 1 | **Intake & Triage** | Classifies the dispute type, enriches the transaction, and scores initial fraud risk. |
| 2 | **Compliance Reasoning** | Calculates Reg E / Reg Z SLA deadlines and determines whether Provisional Credit is mandatory. |
| 3 | **Evidence Orchestration** | Executes parallel API calls across internal systems (Fraud Hub, CRM, Core Ledger) and external acquirers to assemble a structured evidence packet. |
| 4 | **Expert Investigation** | Synthesises evidence against Amex Operating Regulations to produce a final risk disposition and guided decision recommendation. |
| 5 | **Resolution** | Checks retention risk, issues any goodwill credit, and assembles the audit-ready final summary for human review. |

The human L2/L3 analyst only acts at the end — attesting to the decision and triggering final execution.

<img width="1273" height="781" alt="image" src="https://github.com/user-attachments/assets/6cc223ac-2bb9-4984-8d6d-5982a07d896d" />

---

## Demo

### Stop 1 — Triage & Classification Complete

The Intake & Triage Agent has ingested the case and classified it. It has identified the dispute category
as **Consumer — Item Not as Described**, assigned the Amex Risk Taxonomy tag, enriched the vague merchant
descriptor to a clear brand, and pulled David Chen's LTV score and fraud risk flags. The workflow now knows
which investigation path to follow.

<img width="1379" height="812" alt="image" src="https://github.com/user-attachments/assets/5d2a9cd7-67d6-46d0-a94b-33ba3571ebc5" />

---

### Stop 2 — Evidence Gathered & Compliance Checked

Running in parallel: the Compliance Reasoning Agent has confirmed the governing regulation (Reg Z), calculated
the SLA deadline, and determined whether Provisional Credit must be issued now. The Evidence Orchestration
Agent has called the Core Ledger, Fraud Hub, CRM, and the acquirer's API to retrieve compelling evidence —
authentication data, merchant communications, and delivery records. Everything is normalised into a structured
evidence packet.

<img width="1375" height="774" alt="image" src="https://github.com/user-attachments/assets/58efd5d9-2b27-47e1-a9a2-7df44f06589f" />

---

### Stop 3 — Case Summary for Human Review

The final output, assembled by the Resolution Agent, is ready for the L2/L3 analyst. It contains the
expert's final risk disposition (e.g. Confirmed Friendly Fraud or Policy-Mandated Write-Off), the full
policy citation and evidence rationale, the compliance verification status, any retention credit issued,
and the specific execution command for the analyst to attest and action.

<img width="1409" height="762" alt="image" src="https://github.com/user-attachments/assets/ccf90f3b-1896-474f-9e92-cedc2ade04ef" />
