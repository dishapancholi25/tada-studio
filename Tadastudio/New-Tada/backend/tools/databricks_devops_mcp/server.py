"""Databricks Workspace & Azure DevOps MCP Server.

A custom MCP server that exposes Databricks workspace operations
and Azure DevOps git operations as tools for AI agents.

Architecture:
- READS: Use Databricks Workspace API (notebooks are rendered properly)
- WRITES: Use Azure DevOps REST API (solves commit/push gap)
- SYNC: Use Databricks Repos API (pull DevOps changes into workspace)

This gives full end-to-end automation:
  Agent generates code -> pushes to DevOps branch -> syncs Databricks repo

Runs as a stdio subprocess spawned by the MCP client manager.
"""

import base64
import json
import logging
import os
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

mcp = FastMCP(
    "Databricks DevOps MCP Server",
    instructions="""You have access to a Databricks workspace connected to an Azure DevOps
    Git repository. Use these tools to read, write, and manage notebooks in the workspace.

    Typical workflow for creating a new notebook:
    1. Use list_branches to see available branches
    2. Use create_feature_branch to create a new branch from main
    3. Use write_notebook to push notebook content to the branch
    4. Use sync_repo to pull the changes into the Databricks workspace
    5. Optionally use read_notebook to verify the content

    Notebook format: Databricks Python notebooks use '# Databricks notebook source'
    as the first line and '# COMMAND ----------' as cell separators.
    Use '# MAGIC %md' prefix for markdown cells and '# MAGIC %sql' for SQL cells.
    """,
)

# ---------------------------------------------------------------------------
# Configuration (loaded from environment variables)
# ---------------------------------------------------------------------------

_client: Optional[httpx.AsyncClient] = None


def _get_config():
    """Read configuration from environment variables."""
    return {
        "databricks_host": os.environ.get("DATABRICKS_HOST", "").rstrip("/"),
        "databricks_token": os.environ.get("DATABRICKS_TOKEN", ""),
        "devops_org": os.environ.get("DEVOPS_ORG", ""),
        "devops_project": os.environ.get("DEVOPS_PROJECT", ""),
        "devops_repo": os.environ.get("DEVOPS_REPO", ""),
        "devops_pat": os.environ.get("DEVOPS_PAT", ""),
        "git_folder_path": os.environ.get("DATABRICKS_GIT_FOLDER_PATH", ""),
    }


def _databricks_headers() -> dict:
    cfg = _get_config()
    return {
        "Authorization": f"Bearer {cfg['databricks_token']}",
        "Content-Type": "application/json",
    }


def _devops_headers() -> dict:
    cfg = _get_config()
    b64_pat = base64.b64encode(f":{cfg['devops_pat']}".encode()).decode()
    return {
        "Authorization": f"Basic {b64_pat}",
        "Content-Type": "application/json",
    }


def _devops_base_url() -> str:
    cfg = _get_config()
    return (
        f"https://dev.azure.com/{cfg['devops_org']}/{cfg['devops_project']}"
        f"/_apis/git/repositories/{cfg['devops_repo']}"
    )


# ===========================================================================
# TOOL: list_notebooks
# ===========================================================================


@mcp.tool()
async def list_notebooks(path: str = "/") -> str:
    """List notebooks and files in a Databricks workspace path.

    Args:
        path: Workspace path to list. Use "/" for the Git folder root.
              Paths are relative to the configured Git folder.
              Example: "/notebooks/bronze" to list bronze layer notebooks.

    Returns:
        JSON list of objects in the directory with their types and paths.
    """
    cfg = _get_config()
    git_folder = cfg["git_folder_path"]

    if path == "/":
        full_path = git_folder
    else:
        full_path = f"{git_folder}{path}"

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{cfg['databricks_host']}/api/2.0/workspace/list",
            headers=_databricks_headers(),
            params={"path": full_path},
        )

    if resp.status_code != 200:
        return f"Error listing path '{path}': {resp.text}"

    data = resp.json()
    objects = data.get("objects", [])

    results = []
    for obj in objects:
        relative_path = obj.get("path", "").replace(git_folder, "")
        results.append(
            {
                "path": relative_path or "/",
                "type": obj.get("object_type", "UNKNOWN"),
                "language": obj.get("language", None),
            }
        )

    return json.dumps(results, indent=2)


# ===========================================================================
# TOOL: read_notebook
# ===========================================================================


@mcp.tool()
async def read_notebook(path: str) -> str:
    """Read/export a notebook from the Databricks workspace.

    Args:
        path: Path to the notebook relative to the Git folder root.
              Example: "/notebooks/bronze/ingest_raw_data"
              (omit the .py extension - Databricks handles this)

    Returns:
        The notebook source code content.
    """
    cfg = _get_config()
    full_path = f"{cfg['git_folder_path']}{path}"

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{cfg['databricks_host']}/api/2.0/workspace/export",
            headers=_databricks_headers(),
            params={"path": full_path, "format": "SOURCE"},
        )

    if resp.status_code != 200:
        return f"Error reading notebook '{path}': {resp.text}"

    data = resp.json()
    content_b64 = data.get("content", "")
    content = base64.b64decode(content_b64).decode("utf-8")

    return content


# ===========================================================================
# TOOL: list_branches
# ===========================================================================


@mcp.tool()
async def list_branches() -> str:
    """List all branches in the Azure DevOps Git repository.

    Returns:
        JSON list of branch names and their latest commit IDs.
    """
    url = f"{_devops_base_url()}/refs?filter=heads/&api-version=7.1"
    logger.info("list_branches URL: %s", url)

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=_devops_headers())

    if resp.status_code != 200:
        return f"Error listing branches (HTTP {resp.status_code}). URL attempted: {url}"

    data = resp.json()
    branches = []
    for ref in data.get("value", []):
        name = ref.get("name", "").replace("refs/heads/", "")
        branches.append(
            {
                "name": name,
                "commit_id": ref.get("objectId", ""),
            }
        )

    return json.dumps(branches, indent=2)


# ===========================================================================
# TOOL: create_feature_branch
# ===========================================================================


@mcp.tool()
async def create_feature_branch(
    branch_name: str,
    source_branch: str = "main",
) -> str:
    """Create a new feature branch in the Azure DevOps repository.

    Args:
        branch_name: Name for the new branch (e.g. 'feature/agent-etl-pipeline').
                     Do not include 'refs/heads/' prefix.
        source_branch: Branch to create from (default: 'main').

    Returns:
        Confirmation message with the new branch details.
    """
    refs_url = f"{_devops_base_url()}/refs?filter=heads/{source_branch}&api-version=7.1"

    async with httpx.AsyncClient() as client:
        resp = await client.get(refs_url, headers=_devops_headers())

    if resp.status_code != 200:
        return f"Error finding source branch '{source_branch}': {resp.text}"

    refs = resp.json().get("value", [])
    if not refs:
        return f"Source branch '{source_branch}' not found."

    source_commit = refs[0]["objectId"]

    create_url = f"{_devops_base_url()}/refs?api-version=7.1"
    payload = [
        {
            "name": f"refs/heads/{branch_name}",
            "oldObjectId": "0000000000000000000000000000000000000000",
            "newObjectId": source_commit,
        }
    ]

    async with httpx.AsyncClient() as client:
        resp = await client.post(create_url, headers=_devops_headers(), json=payload)

    if resp.status_code != 200:
        return f"Error creating branch: {resp.text}"

    result = resp.json()
    created = result.get("value", [{}])[0]

    if not created.get("success", False):
        custom_msg = created.get("customMessage", "Unknown error")
        return f"Failed to create branch: {custom_msg}"

    return json.dumps(
        {
            "status": "success",
            "branch": branch_name,
            "source_branch": source_branch,
            "commit_id": source_commit,
            "message": f"Branch '{branch_name}' created from '{source_branch}'.",
        },
        indent=2,
    )


# ===========================================================================
# TOOL: write_notebook
# ===========================================================================


@mcp.tool()
async def write_notebook(
    path: str,
    content: str,
    branch: str,
    commit_message: str = "Add notebook via Agentic Studio agent",
) -> str:
    """Write a notebook to the Azure DevOps repository on a specific branch.

    This pushes the file directly to DevOps (not to the Databricks workspace).
    After writing, use sync_repo to pull the changes into Databricks.

    Args:
        path: File path in the repo (e.g. 'notebooks/bronze/ingest_raw.py').
              Do NOT include a leading slash.
        content: The full notebook source code. For Databricks Python notebooks,
                 start with '# Databricks notebook source' and use
                 '# COMMAND ----------' as cell separators.
        branch: The branch to push to (e.g. 'feature/agent-etl-pipeline').
        commit_message: Git commit message describing the change.

    Returns:
        Confirmation with the commit ID of the push.
    """
    refs_url = f"{_devops_base_url()}/refs?filter=heads/{branch}&api-version=7.1"

    async with httpx.AsyncClient() as client:
        resp = await client.get(refs_url, headers=_devops_headers())

    if resp.status_code != 200:
        return f"Error finding branch '{branch}': {resp.text}"

    refs = resp.json().get("value", [])
    if not refs:
        return (
            f"Branch '{branch}' not found. Create it first with create_feature_branch."
        )

    old_commit = refs[0]["objectId"]

    item_url = (
        f"{_devops_base_url()}/items"
        f"?path=/{path}&versionDescriptor.version={branch}"
        f"&api-version=7.1"
    )

    async with httpx.AsyncClient() as client:
        item_resp = await client.get(item_url, headers=_devops_headers())

    change_type = "edit" if item_resp.status_code == 200 else "add"

    push_url = f"{_devops_base_url()}/pushes?api-version=7.1"
    payload = {
        "refUpdates": [
            {
                "name": f"refs/heads/{branch}",
                "oldObjectId": old_commit,
            }
        ],
        "commits": [
            {
                "comment": commit_message,
                "changes": [
                    {
                        "changeType": change_type,
                        "item": {"path": f"/{path}"},
                        "newContent": {
                            "content": content,
                            "contentType": "rawtext",
                        },
                    }
                ],
            }
        ],
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(push_url, headers=_devops_headers(), json=payload)

    if resp.status_code not in (200, 201):
        return f"Error pushing notebook: {resp.text}"

    result = resp.json()
    new_commit = result.get("commits", [{}])[0].get("commitId", "unknown")

    return json.dumps(
        {
            "status": "success",
            "action": change_type,
            "path": path,
            "branch": branch,
            "commit_id": new_commit,
            "commit_message": commit_message,
            "message": f"Notebook '{path}' {'updated' if change_type == 'edit' else 'created'} on branch '{branch}'.",
        },
        indent=2,
    )


# ===========================================================================
# TOOL: write_multiple_notebooks
# ===========================================================================


@mcp.tool()
async def write_multiple_notebooks(
    files: list[dict[str, str]],
    branch: str,
    commit_message: str = "Add notebooks via Agentic Studio agent",
) -> str:
    """Write multiple notebooks/files in a single commit to Azure DevOps.

    This is more efficient than calling write_notebook multiple times,
    and keeps all changes in one atomic commit.

    Args:
        files: List of dicts, each with 'path' and 'content' keys.
               Example: [
                   {"path": "notebooks/bronze/ingest.py", "content": "# Databricks notebook source\\n..."},
                   {"path": "notebooks/silver/transform.py", "content": "# Databricks notebook source\\n..."}
               ]
        branch: The branch to push to.
        commit_message: Git commit message.

    Returns:
        Confirmation with the commit ID.
    """
    refs_url = f"{_devops_base_url()}/refs?filter=heads/{branch}&api-version=7.1"

    async with httpx.AsyncClient() as client:
        resp = await client.get(refs_url, headers=_devops_headers())

    if resp.status_code != 200:
        return f"Error finding branch '{branch}': {resp.text}"

    refs = resp.json().get("value", [])
    if not refs:
        return f"Branch '{branch}' not found."

    old_commit = refs[0]["objectId"]

    changes = []
    async with httpx.AsyncClient() as client:
        for file_info in files:
            file_path = file_info["path"]
            item_url = (
                f"{_devops_base_url()}/items"
                f"?path=/{file_path}&versionDescriptor.version={branch}"
                f"&api-version=7.1"
            )
            item_resp = await client.get(item_url, headers=_devops_headers())
            change_type = "edit" if item_resp.status_code == 200 else "add"

            changes.append(
                {
                    "changeType": change_type,
                    "item": {"path": f"/{file_path}"},
                    "newContent": {
                        "content": file_info["content"],
                        "contentType": "rawtext",
                    },
                }
            )

    push_url = f"{_devops_base_url()}/pushes?api-version=7.1"
    payload = {
        "refUpdates": [
            {
                "name": f"refs/heads/{branch}",
                "oldObjectId": old_commit,
            }
        ],
        "commits": [
            {
                "comment": commit_message,
                "changes": changes,
            }
        ],
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(push_url, headers=_devops_headers(), json=payload)

    if resp.status_code not in (200, 201):
        return f"Error pushing notebooks: {resp.text}"

    result = resp.json()
    new_commit = result.get("commits", [{}])[0].get("commitId", "unknown")

    paths = [f["path"] for f in files]
    return json.dumps(
        {
            "status": "success",
            "files_written": paths,
            "branch": branch,
            "commit_id": new_commit,
            "message": f"Pushed {len(files)} file(s) to branch '{branch}'.",
        },
        indent=2,
    )


# ===========================================================================
# TOOL: delete_file
# ===========================================================================


@mcp.tool()
async def delete_file(
    path: str,
    branch: str,
    commit_message: str = "Delete file via Agentic Studio agent",
) -> str:
    """Delete a file from the Azure DevOps repository on a specific branch.

    After deleting, use sync_repo to reflect the changes in the Databricks workspace.

    Args:
        path: File path in the repo (e.g. 'notebooks/bronze/old_ingest.py').
              Do NOT include a leading slash.
        branch: The branch to delete the file from.
        commit_message: Git commit message describing the deletion.

    Returns:
        Confirmation with the commit ID.
    """
    refs_url = f"{_devops_base_url()}/refs?filter=heads/{branch}&api-version=7.1"

    async with httpx.AsyncClient() as client:
        resp = await client.get(refs_url, headers=_devops_headers())

    if resp.status_code != 200:
        return f"Error finding branch '{branch}': {resp.text}"

    refs = resp.json().get("value", [])
    if not refs:
        return f"Branch '{branch}' not found."

    old_commit = refs[0]["objectId"]

    push_url = f"{_devops_base_url()}/pushes?api-version=7.1"
    payload = {
        "refUpdates": [
            {
                "name": f"refs/heads/{branch}",
                "oldObjectId": old_commit,
            }
        ],
        "commits": [
            {
                "comment": commit_message,
                "changes": [
                    {
                        "changeType": "delete",
                        "item": {"path": f"/{path}"},
                    }
                ],
            }
        ],
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(push_url, headers=_devops_headers(), json=payload)

    if resp.status_code not in (200, 201):
        return f"Error deleting file: {resp.text}"

    result = resp.json()
    new_commit = result.get("commits", [{}])[0].get("commitId", "unknown")

    return json.dumps(
        {
            "status": "success",
            "action": "delete",
            "path": path,
            "branch": branch,
            "commit_id": new_commit,
            "message": f"File '{path}' deleted from branch '{branch}'.",
        },
        indent=2,
    )


# ===========================================================================
# TOOL: get_file_from_devops
# ===========================================================================


@mcp.tool()
async def get_file_from_devops(
    path: str,
    branch: str = "main",
) -> str:
    """Read a file directly from the Azure DevOps repository.

    Useful when the Databricks workspace hasn't been synced yet,
    or to check the DevOps version of a file.

    Args:
        path: File path in the repo (e.g. 'notebooks/bronze/ingest_raw.py').
              Do NOT include a leading slash.
        branch: Branch to read from (default: 'main').

    Returns:
        The file content as a string.
    """
    item_url = (
        f"{_devops_base_url()}/items"
        f"?path=/{path}&versionDescriptor.version={branch}"
        f"&includeContent=true&api-version=7.1"
    )

    async with httpx.AsyncClient() as client:
        resp = await client.get(item_url, headers=_devops_headers())

    if resp.status_code != 200:
        return f"Error reading file '{path}' from branch '{branch}': {resp.text}"

    data = resp.json()
    content = data.get("content", "")

    if not content:
        # Try downloading content directly (binary endpoint)
        download_url = (
            f"{_devops_base_url()}/items"
            f"?path=/{path}&versionDescriptor.version={branch}"
            f"&$format=text&api-version=7.1"
        )
        async with httpx.AsyncClient() as client:
            resp = await client.get(download_url, headers=_devops_headers())

        if resp.status_code != 200:
            return f"Error downloading file '{path}': {resp.text}"

        content = resp.text

    return content


# ===========================================================================
# TOOL: sync_repo
# ===========================================================================


@mcp.tool()
async def sync_repo(branch: str) -> str:
    """Sync the Databricks Git folder to a specific branch, pulling latest changes.

    Call this after writing notebooks via write_notebook or write_multiple_notebooks
    to make the changes visible in the Databricks workspace.

    Args:
        branch: Branch name to sync to (e.g. 'feature/agent-etl-pipeline').

    Returns:
        Confirmation that the repo was synced.
    """
    cfg = _get_config()
    git_folder = cfg["git_folder_path"]

    async with httpx.AsyncClient() as client:
        status_resp = await client.get(
            f"{cfg['databricks_host']}/api/2.0/workspace/get-status",
            headers=_databricks_headers(),
            params={"path": git_folder},
        )

    if status_resp.status_code != 200:
        return f"Error finding Git folder at '{git_folder}': {status_resp.text}"

    object_id = status_resp.json().get("object_id")
    if not object_id:
        return "Could not determine repo ID from Git folder path."

    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{cfg['databricks_host']}/api/2.0/repos/{object_id}",
            headers=_databricks_headers(),
            json={"branch": branch},
        )

    if resp.status_code != 200:
        return f"Error syncing repo to branch '{branch}': {resp.text}"

    result = resp.json()
    return json.dumps(
        {
            "status": "success",
            "branch": result.get("branch", branch),
            "head_commit_id": result.get("head_commit_id", "unknown"),
            "path": git_folder,
            "message": f"Databricks Git folder synced to branch '{branch}'.",
        },
        indent=2,
    )


# ===========================================================================
# TOOL: get_repo_status
# ===========================================================================


@mcp.tool()
async def get_repo_status() -> str:
    """Get the current status of the Databricks Git folder (current branch, commit, etc).

    Returns:
        JSON with the current branch, head commit, and repo URL.
    """
    cfg = _get_config()
    git_folder = cfg["git_folder_path"]

    async with httpx.AsyncClient() as client:
        status_resp = await client.get(
            f"{cfg['databricks_host']}/api/2.0/workspace/get-status",
            headers=_databricks_headers(),
            params={"path": git_folder},
        )

    if status_resp.status_code != 200:
        return f"Error getting repo status: {status_resp.text}"

    object_id = status_resp.json().get("object_id")

    async with httpx.AsyncClient() as client:
        repo_resp = await client.get(
            f"{cfg['databricks_host']}/api/2.0/repos/{object_id}",
            headers=_databricks_headers(),
        )

    if repo_resp.status_code != 200:
        return f"Error getting repo details: {repo_resp.text}"

    data = repo_resp.json()
    return json.dumps(
        {
            "path": data.get("path", ""),
            "branch": data.get("branch", ""),
            "head_commit_id": data.get("head_commit_id", ""),
            "url": data.get("url", ""),
            "provider": data.get("provider", ""),
        },
        indent=2,
    )


# ===========================================================================
# TOOL: create_pull_request
# ===========================================================================


@mcp.tool()
async def create_pull_request(
    source_branch: str,
    target_branch: str = "main",
    title: str = "Agent-generated notebook",
    description: str = "",
) -> str:
    """Create a pull request in Azure DevOps to merge a feature branch.

    Args:
        source_branch: Branch with the changes (e.g. 'feature/agent-etl-pipeline').
        target_branch: Branch to merge into (default: 'main').
        title: Title for the pull request.
        description: Optional description/body for the PR.

    Returns:
        JSON with the PR ID, URL, and status.
    """
    cfg = _get_config()
    pr_url = f"{_devops_base_url()}/pullrequests?api-version=7.1"

    payload = {
        "sourceRefName": f"refs/heads/{source_branch}",
        "targetRefName": f"refs/heads/{target_branch}",
        "title": title,
        "description": description
        or f"Notebooks generated by Agentic Studio agent on branch '{source_branch}'.",
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(pr_url, headers=_devops_headers(), json=payload)

    if resp.status_code not in (200, 201):
        return f"Error creating pull request: {resp.text}"

    data = resp.json()
    pr_id = data.get("pullRequestId", "")
    web_url = (
        f"https://dev.azure.com/{cfg['devops_org']}/{cfg['devops_project']}/_git/"
        f"{cfg['devops_repo']}/pullrequest/{pr_id}"
    )

    return json.dumps(
        {
            "status": "success",
            "pr_id": pr_id,
            "title": data.get("title", ""),
            "source_branch": source_branch,
            "target_branch": target_branch,
            "url": web_url,
            "message": f"Pull request #{pr_id} created: {title}",
        },
        indent=2,
    )
