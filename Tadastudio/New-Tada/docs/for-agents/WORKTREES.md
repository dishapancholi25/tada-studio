# Git Worktrees

The project includes a helper script at `scripts/worktree.sh` for managing git worktrees. Worktrees let you work on multiple branches simultaneously without stashing or switching branches in the main repo.

Worktrees are created under `../worktrees/` (sibling to the main repo directory), with `/` in branch names replaced by `-` for the directory name.

## Options

| Flag | Description |
|------|-------------|
| `-y` | Auto-confirm all prompts. Use for non-interactive mode (AI agents, CI). |

The `-y` flag goes **before** the command:

```bash
./scripts/worktree.sh -y merge feat/my-feature
./scripts/worktree.sh -y remove feat/my-feature
```

## Commands

### Create a worktree

```bash
./scripts/worktree.sh create <branch-name> [base-branch]
```

- Creates a new worktree with a new branch based on `base-branch`
- If `base-branch` is omitted, defaults to the current branch
- If the branch already exists, checks it out into the worktree
- Stores the base branch in git config for later merge
- Copies `.env` from the main repo into the worktree (if it exists)

**Example:**

```bash
./scripts/worktree.sh create feat/new-feature main
# Worktree at: ../worktrees/feat-new-feature
# Branch: feat/new-feature (based on main)
# .env copied if present
```

### List worktrees

```bash
./scripts/worktree.sh list
```

### Merge a worktree branch back

```bash
./scripts/worktree.sh [-y] merge [branch-name]
```

- If no branch name is given, detects the current branch
- Checks for uncommitted changes (fails if dirty)
- Switches the main repo to the base branch, pulls latest, and merges with `--no-ff`
- Prompts to push and clean up after merge (auto-confirmed with `-y`)
- On merge conflict, prints instructions for manual resolution

**Example:**

```bash
./scripts/worktree.sh merge feat/new-feature
# Merges feat/new-feature into its base branch in the main repo

# Non-interactive: merge, push, and clean up automatically
./scripts/worktree.sh -y merge feat/new-feature
```

### Remove a worktree

```bash
./scripts/worktree.sh [-y] remove <branch-name>
```

- Removes the worktree directory
- Prompts to delete the local branch (auto-confirmed with `-y`)
- Prunes stale worktree references

**Example:**

```bash
./scripts/worktree.sh remove feat/new-feature

# Non-interactive: remove worktree and delete branch automatically
./scripts/worktree.sh -y remove feat/new-feature
```

## Typical workflow

```bash
# 1. Create worktree from current branch
./scripts/worktree.sh create feat/my-feature

# 2. Work in the worktree
cd ../worktrees/feat-my-feature
# ... make changes, commit ...

# 3. Merge back (from anywhere)
./scripts/worktree.sh merge feat/my-feature

# 4. Or remove without merging
./scripts/worktree.sh remove feat/my-feature
```

## Non-interactive workflow (AI agents)

```bash
# Create, work, merge, and clean up without any prompts
./scripts/worktree.sh create feat/my-feature main
cd ../worktrees/feat-my-feature
# ... make changes, commit ...
./scripts/worktree.sh -y merge feat/my-feature
```
