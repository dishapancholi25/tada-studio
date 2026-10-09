# Account Unlock Investigation — Presales Demo

---

## Input

A queue of account unlock cases arrives in the platform. For this demo we use the first record:

> **Queue #001 — Account Disabled: Compliance Violation (CSPM-GOV-9001-A)**
>
> An automated governance remediation has disabled the account for **`p.sharma@bank.com`**.
> This action was triggered by a high-severity compliance finding (CSPM-GOV-9001-A: Separation of Duties Violation).
> The account is flagged for manual compliance review before reactivation.
>
> - **Affected User:** `p.sharma@bank.com`
> - **Source System:** CSPM (Cloud Security Posture Management)
> - **Reference ID:** CSPM-GOV-9001-A

This is pasted directly into the workflow input field. Everything from here is automated.

<img width="556" height="536" alt="image" src="https://github.com/user-attachments/assets/e51a3fa5-bca3-44f0-a087-71969cfdc6f1" />

---

## Workflow Overview

The workflow runs a team of four specialised agents in sequence, each with a distinct role:

| # | Agent | Role |
|---|-------|------|
| 1 | **Intake & Triage** | Queries IAM and HRIS to build a verified user profile. Identifies why the account was locked and selects the appropriate investigation playbook. |
| 2 | **Evidence Orchestration** | Executes only the data collection steps defined by that playbook — targeted retrieval from CSPM, Azure AD, SIEM, or HRIS depending on the scenario. |
| 3 | **Expert Investigation** | Correlates the raw evidence packet, pinpoints the root cause, and formally classifies the risk using the internal risk taxonomy. |
| 4 | **Resolution** | Translates the technical findings into plain-English and pulls pre-approved recommended actions from the Resolution Playbook for the human reviewer. |

The human agent only acts at the end — reviewing the briefing and making the final call.

<img width="1490" height="777" alt="image" src="https://github.com/user-attachments/assets/36297d08-572c-430f-80d7-b039c801876d" />

---

## Demo

### Stop 1 — Triage Complete

The Intake & Triage Agent has queried IAM and HRIS. It now knows who p.sharma is, their role and manager,
and the exact reason the account was locked. Based on the lock type (a Governance Violation), it selects
the **Governance_Violation** investigation playbook — meaning the Evidence agent will query CSPM and Azure AD, not the SIEM.

<img width="1366" height="651" alt="image" src="https://github.com/user-attachments/assets/ae2b1276-c6eb-4d0c-8213-c6aabbac0622" />

---

### Stop 2 — Evidence Gathered

The Evidence Orchestration Agent has executed the playbook. It queried the CSPM for the compliance finding
details and pulled the relevant Azure AD conditional access logs. The raw evidence packet is compiled and
passed forward — no interpretation yet, just the facts collected in one place.

<img width="1376" height="798" alt="image" src="https://github.com/user-attachments/assets/bfa5b8e1-1697-4b8e-be48-0da44a5d62e0" />

---

### Stop 3 — Case summary

The final output, assembled by the Case Summary Agent, is waiting for the human reviewer. It contains a
plain-English executive summary of what happened, a risk assessment, the key investigative details, and a
dynamic list of recommended actions drawn from the Resolution Playbook.

The human reviews, selects their action, and closes the case.

<img width="1408" height="792" alt="image" src="https://github.com/user-attachments/assets/1cb2774f-99f7-4c13-8cfa-8302164e8767" />
