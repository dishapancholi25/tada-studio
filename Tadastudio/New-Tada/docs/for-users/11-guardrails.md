# Guardrails

Guardrails are safety policies that protect your AI workflows by scanning inputs and outputs for sensitive data, toxic language, prompt injection, and other risks. This guide covers creating policies, assigning them to agents, and testing them.

---

## Overview

Guardrails intercept workflow execution at six points:

| Checkpoint | What it does |
|------------|-------------|
| **Input validation** | Scans user input before it reaches the LLM (pattern rules + ML scanners) |
| **System prompt protection** | Detects attempts to override or extract system prompts |
| **Tool call validation** | Checks URLs, SQL, and file paths before tool execution |
| **Provider content filter** | Catches and logs provider-level content safety rejections (Azure/OpenAI) |
| **Token budget tracking** | Monitors token usage and enforces cost limits |
| **Output filtering** | Scans LLM responses before they reach the user (pattern rules + ML scanners) |

When a violation is detected, the system can **block** the request, **redact** the offending content, or **warn** without blocking (depending on the enforcement mode).

---

## 1. Navigate to Guardrails

Click **Guardrails** in the left sidebar to open the guardrails management page. From here you can:

- Browse and create policies
- View built-in templates
- Monitor violations
- Check compliance status (admin)

---

## 2. Create a Policy

Click **New Policy** to open the policy builder. A policy has a name, description, and a configuration that defines what to check for.

### Policy Settings

| Setting | Description |
|---------|-------------|
| **Name** | A short, descriptive name (e.g., "PII Protection") |
| **Description** | What this policy does and why |
| **Scope** | `User` (private), `Organization` (team-wide), or `Global` (platform-wide) |
| **Applies to** | Which target types: Agent, Workflow, Tool, or Model |
| **Tags** | Labels for filtering (e.g., "pii", "compliance", "security") |

### Enforcement Modes

| Mode | Behavior |
|------|----------|
| **Enforce** | Violations are blocked. Input/output checks halt execution; tool calls are rejected. |
| **Audit** | Violations are logged but execution continues. Use this to test a policy before enforcing it. |
| **Disabled** | All checks are skipped. The policy is inactive but preserved for later use. |

### Configuration Sections

A policy can include any combination of the following:

#### Pattern Rules (Regex-based DLP)

Detect and block sensitive patterns in text using regex. Each rule contains one or more labeled regex patterns that are evaluated together. Rules can be set to **Block**, **Warn**, or **Redact**, and applied to **Input**, **Output**, or **Both**.

The preset picker in the UI provides ready-made rules you can add with one click:

**Single-pattern presets (PII / secrets):**

| Preset | What it catches | Default action |
|--------|----------------|----------------|
| SSN (US) | `123-45-6789` format | Redact |
| Credit Card | 13--19 digit card numbers | Redact |
| Email Address | Standard email format | Warn |
| Phone (US) | US phone number patterns | Warn |
| API Key | Keys starting with `sk-`, `pk_`, `AKIA`, `ghp_`, etc. | Redact |
| AWS Access Key | `AKIA` followed by 16 alphanumeric characters | Block |
| Private Key | `-----BEGIN PRIVATE KEY-----` blocks | Block |

**Multi-pattern presets (security / compliance):**

| Preset | Patterns | Default action |
|--------|----------|----------------|
| SQL Injection | SQL keywords (`DROP`, `DELETE`, etc.) + SQL operators (`--`, `; ' OR '`) | Block |
| Prompt Injection | Ignore-instructions phrases, role override attempts, system prompt extraction | Block |
| Code Execution | Shell commands (`rm -rf`, `sudo`), script injection (`<script>`), OS command injection | Block |
| Confidential Data Leak | API key assignments, AWS credentials, database connection strings | Block |
| URL / Link Filtering | HTTP/HTTPS URLs, Base64 data URIs | Warn |

You can also create custom rules from scratch with your own regex patterns.

##### Regex syntax

Pattern rules use **Python regex** syntax (the `re` module on the backend). Standard regex features are supported: character classes, quantifiers, alternation, groups, lookaheads, word boundaries (`\b`), etc.

**Inline flags** are also supported. Prefix a pattern with an inline flag group to change matching behavior:

| Flag | Meaning | Example |
|------|---------|---------|
| `(?i)` | Case-insensitive matching | `(?i)\b(DROP\|DELETE\|INSERT)\b` matches `drop`, `DROP`, `Drop` |

The `(?i)` flag is used by several of the built-in presets (SQL Injection, Prompt Injection, Code Execution, Confidential Data Leak) to match keywords regardless of case. You can use it in your own custom patterns too.

> **Note:** The UI validates regex patterns as you type. Inline flags like `(?i)` are recognised and handled correctly by the validator.

#### Input Safety (LLM Guard Scanners)

ML-based detection for adversarial inputs and content safety. Each scanner can be set to **Off**, **Block**, or **Warn**, and many have configurable confidence thresholds.

**Adversarial Detection:**

- **Prompt injection detection** -- catches attempts to hijack the agent (threshold: 0.75)
- **Jailbreak detection** -- catches attempts to bypass safety guidelines (threshold: 0.75)

**PII Detection:**

- **PII anonymize** -- detect personally identifiable information with four actions:
  - **Off** -- no PII scanning
  - **Block** -- reject input containing PII
  - **Warn** -- log PII but allow through
  - **Anonymize** -- replace PII with placeholders (vault round-trip), restored in output via deanonymize
- **Use faker** -- when anonymizing, replace PII with realistic fake data instead of `[REDACTED_*]` placeholders
- **Entity type selector** -- choose which PII types to detect from 38+ Presidio entity types.
  The selector provides:
  - **Quick actions:** *Recommended* (8 common types), *All Types*, or *Clear All*
  - **Compliance presets:** One-click configurations for major regulations:

| Preset | Regulation | Types |
|--------|-----------|-------|
| **GDPR** | EU General Data Protection Regulation | 15 entity types (person, email, phone, IP, location, EU IDs) |
| **HIPAA** | US Health Insurance Portability and Accountability Act | 13 entity types (person, SSN, medical license, US IDs) |
| **PCI-DSS** | Payment Card Industry Data Security Standard | 11 entity types (credit card, bank numbers, crypto) |
| **CCPA** | California Consumer Privacy Act | 10 entity types (person, SSN, driver license, passport) |
| **PIPEDA** | Canadian Personal Information Protection Act | 9 entity types (person, email, phone, credit card) |

- **Search and browse:** Type to search all entity types, grouped by category
  (Financial, US Identifiers, International IDs, European IDs, Personal Data, Technical, Other)
- Leaving the selection empty scans for all types (default behavior)

**Input Content Safety:**

- **Toxicity detection** -- toxic, insulting, or hateful language (threshold: 0.5)
- **Gibberish detection** -- nonsensical or garbled input
- **Code detection** -- block code snippets in user input

**Input Policy Controls:**

- **Topic ban** -- block input about specific topics (list of topic strings)
- **Language filter** -- only allow input in specific languages (list of language codes)
- **Secrets detection** -- detect API keys, credentials, and secrets
- **Token limit** -- cap input token count

**General Safety:**

- **System prompt protection** -- anchors the system prompt against extraction
- **Input/output length limits** -- maximum character counts

**LLM Judge** (fallback):

- Configurable LLM-based adversarial content classification. Used as a fallback when ML scanners are not enabled.

#### Output Safety (LLM Guard Scanners)

ML-based scanners that check LLM responses before they reach the user:

| Scanner | What it checks |
|---------|---------------|
| **Toxicity** | Toxic or harmful language in responses |
| **No-Refusal** | Detects when the LLM refuses to answer |
| **Sensitive Data** | PII or sensitive data leaked in output |
| **Relevance** | Whether the response is relevant to the prompt |
| **Gibberish** | Nonsensical or garbled output |
| **Bias** | Biased or prejudiced content |
| **Factual Consistency** | Hallucinations or factual errors |
| **Ban Topics** | Specific topics to block in output |
| **Language** | Allowed languages for output |
| **Ban Competitors** | Competitor names to detect in output |

When PII anonymization was used on input, the output is automatically **deanonymized** to restore original values.

#### Tool Call Policy

Controls what tools are allowed to do:

- **URL whitelist/blacklist** -- restrict which URLs tools can access
- **SSRF protection** -- block requests to internal IP ranges
- **SQL restrictions** -- limit allowed operations (e.g., SELECT only) and block specific tables
- **File restrictions** -- control allowed extensions, block specific paths, set max file size
- **Call limits** -- cap the number of tool calls per execution

#### Token Budget

Cost controls for LLM usage:

- Max input/output/total tokens per execution
- Max LLM calls per execution
- Warning threshold (e.g., warn at 80% of budget)

#### Provider Content Filter

Catches and logs content safety rejections from cloud LLM providers (Azure OpenAI, OpenAI). When the
provider's built-in filters block a request (e.g., for hate speech, violence, or jailbreak), the violation
is recorded and shown in the violations dashboard. You can optionally filter by specific categories.

#### Custom Filters

Three types of user-defined filters:

| Type | How it works |
|------|-------------|
| **Python code** | Write a Python function that runs in a sandbox to check or transform content |
| **LLM judge** | Provide a natural-language policy; an LLM evaluates whether content violates it |
| **Declarative template** | Choose from built-in templates: Topic Guard, Language Detector, Word Count Limit |

---

## 3. Use Built-in Templates

The guardrails page includes a **Templates** section with pre-built policies you can clone and customize. Click a template and select **Clone** to create your own editable copy.

You can also use **quick-start bundles** for one-click setup of common guardrail combinations:

| Bundle | What it includes |
|--------|-----------------|
| **LLM Safety** | Adversarial detection, input/output content safety, general safety, token budget |
| **Compliance Kit** | Full scanner suite (all input + output scanners), LLM judge, general safety, cost controls |
| **AI Safety Suite** | All LLM Guard input and output scanners |

---

## 4. Assign a Policy to an Agent

Policies take effect only when assigned to a target. To assign a policy to an agent node:

1. Open a workflow and double-click an **Agent** node to open its configuration panel
2. Switch to the **Guardrails** tab in the panel
3. Click **Assign** to open the policy picker
4. Select a policy from the list
5. Set the **Priority** (lower number = higher priority, range 0--9999, default 500)
6. Set the **Override Mode** (see below)
7. Click **Assign Policy**

The policy now appears in the assignment list. You can also assign policies at the **Workflow** level to cover all agents in that workflow.

### Override Modes

When multiple policies apply to the same agent, the override mode controls how they combine:

| Mode | Behavior |
|------|----------|
| **Merge** | Rules from all policies are combined. Allowed patterns union, blocked patterns union, strictest limits win. This is the default. |
| **Replace** | This policy's config replaces all prior rules entirely. |
| **Append** | This policy's rules are added after others in evaluation order. |

### Editing Priority and Override Mode

After assigning a policy, you can change its priority or override mode directly in the assignment list:

- Click the **Priority** value to edit it inline. Press **Enter** to save or **Escape** to cancel.
- Click the **Mode** value to switch between Merge, Replace, and Append.

Changing priority re-sorts the list automatically. Lower priority numbers are evaluated first.

---

## 5. Compulsory Policies (Admin)

Admins can mark a global policy as **Compulsory**. Compulsory policies:

- Apply automatically to **all** executions, regardless of individual assignments
- Cannot be removed or weakened by non-admin users
- Appear with a lock icon in the assignment list
- Are evaluated at the highest priority layer

To set a policy as compulsory, navigate to the **Compulsory** tab on the guardrails page (admin access required).

---

## 6. Policy Resolution

When an agent has multiple policies (from assignments, workflow-level, and compulsory), they are resolved in this priority order:

1. **Compulsory policies** (global, admin-enforced) -- highest priority
2. **Organization policies** (scope = organization)
3. **Workflow-level assignments** (target_type = workflow)
4. **Tool-specific assignments**
5. **Model-specific assignments**
6. **Agent-node assignments** -- lowest priority

Within each layer, assignments are ordered by their priority number (lower = first). The enforcement mode is always resolved to the **strictest** across all layers: `enforce > audit > disabled`.

You can preview the merged result by clicking **Effective Config** in the guardrails section of the agent panel.

---

## 7. Test a Policy in the Sandbox

Before enforcing a policy in production, test it against sample inputs:

1. Open a policy and click **Test**
2. Enter sample input text (and optionally output text)
3. Click **Run Test**
4. Review the results: which rules triggered, what action was taken, and the sanitized content

The sandbox does **not** persist violations -- it is a safe environment for experimentation.

### Example Test Inputs

**Combined PII + Toxicity test:**

```
You're an absolute idiot, John. Send the payment to john.smith@gmail.com,
his SSN is 123-45-6789 and his credit card is 4111-1111-1111-1111. What a
stupid moron.
```

This input triggers:

| Detection Engine | What it catches |
|-----------------|-----------------|
| **LLM Guard PII Scanner** | Person name (`John`, `john.smith`), Email (`john.smith@gmail.com`), SSN (`123-45-6789`), Credit card (`4111-1111-1111-1111`) |
| **LLM Guard Toxicity Scanner** | Insults (`absolute idiot`, `stupid moron`) |
| **Pattern Rules** (if configured) | SSN and credit card patterns via regex |

**PII detection only:**

```
Please contact Sarah Johnson at sarah.johnson@company.com, phone
555-123-4567, SSN 987-65-4321
```

This triggers the PII scanner for: person name, email, phone number, and SSN. With action set to **Anonymize**, the content is replaced with placeholders (or realistic fake data if **Use faker** is enabled) and restored in the output via deanonymization.

**Toxicity detection only:**

```
You're a complete idiot and the worst person I've ever dealt with
```

This triggers the toxicity scanner for toxic/insulting language.

---

## 8. Monitor Violations

Navigate to **Guardrails > Violations** to view a live feed of guardrail violations across all workflows.

Each violation record shows:

| Field | Description |
|-------|-------------|
| **Rule name** | Which rule was triggered (e.g., "US Social Security Number") |
| **Category** | Where it was caught: input, output, tool call, token budget, behavioral, or custom filter |
| **Severity** | `Block` (red), `Warn` (yellow), or `Info` (blue) |
| **Action taken** | What happened: blocked, redacted, warned, or transformed |
| **Workflow / Agent** | Which workflow and agent node triggered the violation |
| **Execution** | Link to the execution that triggered it |

### Violation Feedback

You can provide feedback on violations to help refine policies:

- **Positive** -- the violation was correctly identified
- **Negative** -- this was a false positive

Feedback is tracked per violation and aggregated in the policy metrics dashboard.

---

## 9. Compliance Dashboard (Admin)

Navigate to **Guardrails > Compliance** to see an overview of guardrail coverage across the platform.

The dashboard shows:

- **Enforcement breakdown** -- how many policies are in Enforce, Audit, or Disabled mode
- **Unprotected workflows** -- workflows with no guardrail coverage, ranked by criticality
- **Unprotected agent nodes** -- individual agents with no policy assignment

Criticality levels:

| Level | Meaning |
|-------|---------|
| **Critical** | No coverage at all -- no assignments and no compulsory fallback |
| **High** | All assigned policies are disabled; no compulsory fallback |
| **Medium** | Only compulsory coverage (no specific assignment) |
| **Low** | Fully covered by an active assignment |

---

## 10. Policy Versioning

Every time a policy is updated, a new version is automatically created. You can:

- **View version history** -- see what changed in each version with change summaries
- **Compare versions** -- review the config diff between versions
- **Rollback** -- restore a previous version's configuration (creates a new version with the old config)

To access version history, open a policy and click **Version History**.

---

## Quick Reference

| Task | How to do it |
|------|-------------|
| Create a policy | Guardrails page > **New Policy** |
| Assign to an agent | Agent config > Guardrails tab > **Assign** |
| Assign to a workflow | Workflow settings > Guardrails section > **Assign** |
| Change priority | Click the priority value in the assignment list |
| Change override mode | Click the mode value in the assignment list |
| Test a policy | Open policy > **Test** > enter sample text > **Run Test** |
| View violations | Guardrails > **Violations** |
| Check compliance | Guardrails > **Compliance** (admin) |
| Make compulsory | Guardrails > **Compulsory** tab (admin) |
| Rollback a policy | Open policy > **Version History** > select version > **Rollback** |
