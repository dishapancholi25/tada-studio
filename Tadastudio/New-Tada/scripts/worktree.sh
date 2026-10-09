#!/usr/bin/env bash
set -euo pipefail

# Git Worktree Helper
# Creates worktrees for parallel development and merges them back when done.
#
# Usage:
#   ./scripts/worktree.sh [-y] create <branch-name> [base-branch]
#   ./scripts/worktree.sh [-y] merge [branch-name]
#   ./scripts/worktree.sh list
#   ./scripts/worktree.sh [-y] remove <branch-name>
#
# Options:
#   -y   Auto-confirm all prompts (non-interactive mode for CI/AI agents)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAIN_REPO="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKTREE_BASE="$(dirname "$MAIN_REPO")/worktrees"
DEFAULT_BASE="$(git -C "$MAIN_REPO" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")"
AUTO_YES=false

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

info()  { echo -e "${CYAN}[info]${NC} $*"; }
ok()    { echo -e "${GREEN}[ok]${NC} $*"; }
warn()  { echo -e "${YELLOW}[warn]${NC} $*"; }
err()   { echo -e "${RED}[error]${NC} $*" >&2; }

# Prompt for confirmation. Returns 0 (yes) or 1 (no).
# With -y flag, always returns 0 (yes).
confirm() {
    local prompt="$1"
    if [[ "$AUTO_YES" == true ]]; then
        info "$prompt [auto-yes]"
        return 0
    fi
    read -rp "$prompt " answer
    [[ "$answer" =~ ^[Yy]$ ]]
}

usage() {
    cat <<EOF
Git Worktree Helper

Commands:
  create <branch> [base]   Create a new worktree branching from base (default: $DEFAULT_BASE)
  merge  [branch]           Merge the current or named worktree branch back into its base
  list                      List all active worktrees
  remove <branch>           Remove a worktree and optionally delete the branch

Options:
  -y                        Auto-confirm all prompts (non-interactive mode)

Examples:
  $(basename "$0") create feat/new-feature
  $(basename "$0") create fix/bug-123 develop
  $(basename "$0") -y merge feat/new-feature
  $(basename "$0") -y remove feat/new-feature
EOF
    exit 1
}

# Resolve worktree path from branch name
worktree_path() {
    local branch="$1"
    # Replace / with - for directory name
    echo "$WORKTREE_BASE/${branch//\//-}"
}

cmd_create() {
    local branch="${1:-}"
    local base="${2:-$DEFAULT_BASE}"

    if [[ -z "$branch" ]]; then
        err "Branch name required."
        echo "  Usage: $(basename "$0") create <branch-name> [base-branch]"
        exit 1
    fi

    local wt_path
    wt_path="$(worktree_path "$branch")"

    if [[ -d "$wt_path" ]]; then
        err "Worktree already exists at $wt_path"
        exit 1
    fi

    # Ensure base branch is up to date
    info "Fetching latest from origin..."
    git -C "$MAIN_REPO" fetch origin "$base" --quiet 2>/dev/null || true

    # Create the worktree directory parent
    mkdir -p "$WORKTREE_BASE"

    # Check if the branch already exists
    if git -C "$MAIN_REPO" show-ref --verify --quiet "refs/heads/$branch" 2>/dev/null; then
        info "Branch '$branch' already exists, creating worktree from it..."
        git -C "$MAIN_REPO" worktree add "$wt_path" "$branch"
    else
        info "Creating worktree with new branch '$branch' from '$base'..."
        git -C "$MAIN_REPO" worktree add -b "$branch" "$wt_path" "origin/$base" 2>/dev/null \
            || git -C "$MAIN_REPO" worktree add -b "$branch" "$wt_path" "$base"
    fi

    # Store the base branch for later merge
    git -C "$wt_path" config --local "worktree.baseBranch" "$base"

    # Copy .env file if it exists in the main repo
    if [[ -f "$MAIN_REPO/.env" ]]; then
        cp "$MAIN_REPO/.env" "$wt_path/.env"
        info "Copied .env to worktree"
    fi

    ok "Worktree created!"
    echo ""
    echo "  Path:   $wt_path"
    echo "  Branch: $branch"
    echo "  Base:   $base"
    echo ""
    info "To start working:  cd $wt_path"
}

cmd_list() {
    info "Active worktrees:"
    echo ""
    git -C "$MAIN_REPO" worktree list
    echo ""
}

cmd_merge() {
    local branch="${1:-}"

    # If no branch given, detect from current directory
    if [[ -z "$branch" ]]; then
        branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
        if [[ -z "$branch" || "$branch" == "HEAD" ]]; then
            err "Could not detect current branch. Pass the branch name explicitly."
            exit 1
        fi
    fi

    local wt_path
    wt_path="$(worktree_path "$branch")"

    # Determine the base branch
    local base
    if [[ -d "$wt_path" ]]; then
        base="$(git -C "$wt_path" config --get worktree.baseBranch 2>/dev/null || echo "$DEFAULT_BASE")"
    else
        base="$DEFAULT_BASE"
    fi

    info "Merging '$branch' into '$base'..."

    # Check for uncommitted changes in the worktree
    if [[ -d "$wt_path" ]]; then
        if ! git -C "$wt_path" diff --quiet || ! git -C "$wt_path" diff --cached --quiet; then
            err "Worktree at $wt_path has uncommitted changes. Commit or stash them first."
            exit 1
        fi
    fi

    # Switch main repo to base branch
    info "Switching main repo to '$base'..."
    git -C "$MAIN_REPO" checkout "$base"

    info "Pulling latest '$base'..."
    git -C "$MAIN_REPO" pull origin "$base" --ff-only 2>/dev/null || true

    # Merge the feature branch
    info "Merging '$branch'..."
    if git -C "$MAIN_REPO" merge "$branch" --no-ff -m "Merge branch '$branch' into $base"; then
        ok "Merge successful!"
        echo ""

        if confirm "Push '$base' to origin? [y/N]"; then
            git -C "$MAIN_REPO" push origin "$base"
            ok "Pushed to origin/$base"
        fi

        if confirm "Remove worktree and delete branch '$branch'? [y/N]"; then
            cmd_remove "$branch"
        fi
    else
        err "Merge conflict! Resolve conflicts in: $MAIN_REPO"
        echo ""
        echo "  After resolving:"
        echo "    cd $MAIN_REPO"
        echo "    git add ."
        echo "    git commit"
        echo "    $(basename "$0") remove $branch   # to clean up the worktree"
    fi
}

cmd_remove() {
    local branch="${1:-}"

    if [[ -z "$branch" ]]; then
        err "Branch name required."
        echo "  Usage: $(basename "$0") remove <branch-name>"
        exit 1
    fi

    local wt_path
    wt_path="$(worktree_path "$branch")"

    if [[ -d "$wt_path" ]]; then
        info "Removing worktree at $wt_path..."
        git -C "$MAIN_REPO" worktree remove "$wt_path" --force
        ok "Worktree removed."
    else
        warn "No worktree found at $wt_path, skipping worktree removal."
    fi

    # Optionally delete the branch
    if git -C "$MAIN_REPO" show-ref --verify --quiet "refs/heads/$branch" 2>/dev/null; then
        if confirm "Delete local branch '$branch'? [y/N]"; then
            git -C "$MAIN_REPO" branch -D "$branch"
            ok "Branch '$branch' deleted."
        fi
    fi

    # Clean up pruned worktrees
    git -C "$MAIN_REPO" worktree prune
}

# --- Main ---

# Parse global options
while [[ "${1:-}" == -* ]]; do
    case "$1" in
        -y) AUTO_YES=true; shift ;;
        *)  err "Unknown option: $1"; usage ;;
    esac
done

command="${1:-}"
shift || true

case "$command" in
    create) cmd_create "$@" ;;
    merge)  cmd_merge "$@" ;;
    list)   cmd_list "$@" ;;
    remove) cmd_remove "$@" ;;
    *)      usage ;;
esac
