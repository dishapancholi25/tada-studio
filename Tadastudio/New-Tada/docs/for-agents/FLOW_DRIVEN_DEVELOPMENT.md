# Flow Driven Development

Flow Driven Development (FDD) is a label-based workflow for triaging GitHub issues by complexity and
automating the appropriate level of AI agent involvement. Issues are assigned a colour label that
determines how Claude Code responds — from fully autonomous implementation to advisory-only analysis.

The workflow is defined in `.github/workflows/claude.yml`.

---

## Complexity Labels

| Label | Complexity | Agent Behaviour |
|-------|-----------|-----------------|
| `green` | Trivial | Implement, create PR, and merge automatically |
| `blue` | Non-trivial | Implement, create PR, leave open for human review |
| `red` | Complex | Analyse codebase, create PR with implementation plan only |
| `black` | Very complex | Comment on the issue with analysis and questions only |

### Green — Trivial

Use for straightforward, low-risk changes where the requirements are unambiguous (e.g. renaming a
variable, updating a config value, fixing a typo, adding a simple utility).

Agent behaviour:

1. Reads the issue and understands the requirements
2. Creates a branch `claude/issue-<number>` from `main`
3. Implements the changes
4. Runs linting and type checks
5. Creates a PR with a description of changes
6. Merges the PR automatically

The agent makes reasonable assumptions if any detail is ambiguous. No human review is required.

### Blue — Non-trivial

Use for tasks that are well-defined but benefit from human review before merging (e.g. adding a new
API endpoint, implementing a UI component, fixing a non-trivial bug).

Agent behaviour:

1. Reads the issue and understands the requirements
2. Creates a branch `claude/issue-<number>` from `main`
3. Implements the changes
4. Runs linting and type checks
5. Creates a PR with a detailed description (what changed, design decisions, testing)
6. Leaves the PR open for human review — does **not** merge

If requirements are ambiguous, the agent adds a comment to the issue asking for clarification rather
than guessing.

### Red — Complex

Use for tasks that involve significant architectural decisions, multiple subsystems, or where the
implementation approach is not obvious (e.g. introducing a new service layer, refactoring a core
module, adding a complex feature).

Agent behaviour:

1. Reads the issue and analyses the existing codebase
2. Creates a branch `claude/issue-<number>` from `main`
3. Creates a PR containing **only an implementation plan** as the PR description — no code changes
4. The plan includes:
   - Summary of proposed changes
   - Files to be created or modified
   - Architectural decisions and trade-offs
   - Step-by-step implementation approach
   - Risks and concerns
   - Estimated scope
5. Waits for human approval before implementing

If requirements need clarification before planning, the agent comments on the issue first.

### Black — Very Complex

Use for tasks that need significant human input before any work begins (e.g. cross-cutting
architectural changes, tasks with unclear requirements, features that need stakeholder input).

Agent behaviour:

1. Reads the issue and analyses the codebase in depth
2. Adds a detailed comment to the issue with:
   - Its understanding of the requirements (for confirmation)
   - Clarification questions on ambiguous aspects
   - Potential approaches with pros and cons
   - Risks, edge cases, and complications
   - Suggestions for breaking the task into smaller pieces
   - Relevant existing patterns in the codebase
3. Does **not** create a branch or PR
4. Does **not** implement any code

---

## How to Use

### Prerequisites

Create four GitHub labels in the repository:

- `green`
- `blue`
- `red`
- `black`

The `CLAUDE_CODE_OAUTH_TOKEN` secret must be configured in the repository settings.

### Assigning Complexity

1. Create an issue with a clear description of the task
2. Apply one of the four colour labels to the issue
3. The Claude Code workflow triggers automatically on the `labeled` event
4. Claude performs the behaviour defined for that label

### Changing Complexity

If you apply a label and decide the complexity was wrong, remove the label and apply the correct one.
Note that re-labelling will trigger a new run — you may need to close any PR or branch created by the
previous run.

### Combining with @claude Mentions

The label-based workflow is independent of the existing `@claude` mention trigger. You can still
`@claude` in issue comments or PR reviews for ad-hoc requests. The `@claude` trigger does **not**
activate on label events, so there is no conflict.

---

## Permissions

Each job requests only the permissions it needs:

| Label | `contents` | `pull-requests` | `issues` |
|-------|-----------|-----------------|----------|
| `green` | write | write | write |
| `blue` | write | write | write |
| `red` | write | write | write |
| `black` | read | read | write |

All jobs require `id-token: write` for OAuth and `actions: read` for CI result access.

---

## Guidelines for Choosing a Label

Ask these questions when triaging an issue:

1. **Can this be done without any review?** — Use `green`
2. **Is the implementation clear but the change is significant enough to review?** — Use `blue`
3. **Does the approach need to be agreed before writing code?** — Use `red`
4. **Are the requirements unclear or is the scope very large?** — Use `black`

When in doubt, choose the higher complexity label. It is easier to move from `red` to `blue` than to
undo a merged `green` change that was more complex than expected.
