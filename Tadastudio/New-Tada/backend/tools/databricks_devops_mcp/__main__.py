"""Databricks DevOps MCP Server entry point.

Usage: python -m backend.tools.databricks_devops_mcp

Environment variables required:
  DATABRICKS_HOST           - Databricks workspace URL (e.g. https://adb-xxxx.azuredatabricks.net)
  DATABRICKS_TOKEN          - Databricks personal access token
  DEVOPS_ORG                - Azure DevOps organization name
  DEVOPS_PROJECT            - Azure DevOps project name
  DEVOPS_REPO               - Azure DevOps repository name
  DEVOPS_PAT                - Azure DevOps personal access token
  DATABRICKS_GIT_FOLDER_PATH - Workspace path to the Git folder (e.g. /Repos/user@company.com/repo)
"""

from .server import mcp

if __name__ == "__main__":
    mcp.run()
