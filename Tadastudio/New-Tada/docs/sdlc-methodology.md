# SpecFlow Development Methodology

This document describes the piste-lane development model used by SpecFlow.
Use it to correctly label epics when creating tasks, whether you are an AI agent or a human.

---

## The Piste Model

SpecFlow categorises every epic into one of four **piste lanes** (named after ski-run difficulty markers). The lane determines **who does the work**, **which AI model is used**, and **how much oversight is required**.

| Lane | Icon | Hex | Who leads | AI model | Effort | Review required |
|---|---|---|---|---|---|---|
| **Green** | Circle | `#22c55e` | AI agent | Sonnet | Medium | No — auto-pickup |
| **Blue** | Square | `#3b82f6` | AI agent | Sonnet | High | Yes — human review |
| **Red** | Diamond | `#ef4444` | Human | Opus | Medium | N/A — human-led |
| **Black** | Double-diamond | `#3f3f46` | Human | Opus | Medium | N/A — manual only |

---

## How to Choose a Lane

### Green — "Agent auto-pickup, Specified"

Assign **Green** when **all** of the following are true:

- The requirement is fully specified (clear acceptance criteria, no ambiguity).
- The change is low-risk: a single feature, bug fix, or UI tweak.
- No architectural decisions, security-sensitive code, or database migrations.
- Automated tests can verify correctness.

**AI responsibilities:** branch, implement, write/run tests, lint, open PR, mark complete.
**Human responsibilities:** none required (PR is auto-raised with Copilot review).

### Blue — "Agent-assisted, Review required"

Assign **Blue** when:

- The requirement is mostly specified but involves moderate complexity.
- The change touches multiple files or areas of the codebase.
- There is some design judgement needed that benefits from human validation.
- Higher effort is expected (the agent runs with `effort: high`).

**AI responsibilities:** branch, implement, write/run tests, lint, open PR.
**Human responsibilities:** review the PR, request rework if needed, approve and merge.

### Red — "Human-led, Agent support"

Assign **Red** when:

- The work requires human judgement, creativity, or domain expertise.
- The scope is broad or the requirements are underspecified.
- The change involves architecture, security, data modelling, or cross-system integration.
- An AI agent can assist (research, draft code, run tests) but should not lead.

**AI responsibilities:** provide support when asked — research, generate drafts, run checks.
**Human responsibilities:** lead implementation, make design decisions, write and review code.

### Black — "Manual only, High complexity"

Assign **Black** when:

- The task is the highest complexity or highest risk.
- It involves infrastructure, compliance, breaking changes, or multi-team coordination.
- AI assistance is not appropriate or not reliable for this type of work.

**AI responsibilities:** none (Opus model is reserved but execution is manual).
**Human responsibilities:** full ownership of implementation, testing, and review.

---

## Task Lifecycle

Every epic moves through two independent status tracks:

### Feature Status (development progress)

| Status | Meaning |
|---|---|
| `not-started` | Work has not begun |
| `in-progress` | Actively being worked on |
| `done` | Implementation complete |
| `needs-rework` | Reviewed and sent back for changes |

### Factory Status (automation progress — Green and Blue lanes)

| Status | Meaning |
|---|---|
| `queued` | Waiting to be picked up by the factory scheduler |
| `waiting` | Blocked — depends on another epic that has not merged yet |
| `agent-running` | An AI agent is actively working on this epic |
| `completed` | Agent finished successfully and opened a PR |
| `failed` | Agent encountered an error |

### Priority

| Value | Label | Use when |
|---|---|---|
| 1 | Critical | Blocks other work or affects production |
| 2 | High | Important, should be done soon |
| 3 | Medium | Normal priority |
| 4 | Low | Nice to have, no urgency |

---

## Quick-Reference Decision Tree

```
Is the requirement fully specified and low-risk?
 ├─ Yes → GREEN
 └─ No
     Is it mostly specified, moderate complexity?
      ├─ Yes → BLUE
      └─ No
          Can a human lead with AI support?
           ├─ Yes → RED
           └─ No (highest complexity / risk) → BLACK
```

---

## For AI Agents Creating Tasks

When you create or label an epic:

1. Read the title and description carefully.
2. Walk through the decision tree above.
3. Set the `complexity` field to one of: `green`, `blue`, `red`, `black`.
4. Set `priority` (1–4) based on urgency and impact.
5. Set `featureStatus` to `not-started`.
6. If the epic depends on another epic, set `dependsOnId` and the factory will automatically set status to `waiting`.

## For Humans Creating Tasks

When you create or label an epic in the SpecFlow UI:

1. Choose the piste marker that matches the complexity and autonomy level.
2. If you are unsure, start with **Blue** — it ensures human review while still leveraging AI.
3. You can always re-classify a task later if the complexity turns out to be different.
4. Set priority based on business impact, not implementation difficulty (difficulty is captured by the lane).
