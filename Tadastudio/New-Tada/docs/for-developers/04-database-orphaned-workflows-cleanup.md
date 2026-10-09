# Orphaned Workflows Cleanup Guide

## Overview

Orphaned workflows are workflows that have no `WorkflowMembership` records. This prevents them from being deleted via the API and can cause sync issues when trying to import/delete/reimport workflows.

## Root Cause

The bug was in `import_raw_workflow()` which created workflows without creating the corresponding `WorkflowMembership` records. This has been fixed in PR #139, but existing orphaned workflows need to be cleaned up.

## The Fix Script

The `fix_orphaned_workflows.py` script can:

1. **Find** all orphaned workflows in the database
2. **Delete** orphaned workflows and their graph definitions
3. **Add memberships** to orphaned workflows (if you want to keep them)

## Running in Production

### Step 1: Copy the script to production

Copy `fix_orphaned_workflows.py` to your production environment where you can access the database.

### Step 2: Set database connection

The script uses the database configuration from the environment. Make sure your environment variables point to the production database:

```bash
# Check current database connection
python3 -c "
import sys
sys.path.insert(0, 'backend')
from backend.services.database.config import DatabaseConfig
config = DatabaseConfig.from_env()
print('Database:', config.connection_string)
"
```

If needed, set the production database environment variables:

```bash
export KEY_POSTGRES_HOST=<production-postgres-host>
export KEY_POSTGRES_DBNAME=<production-database-name>
export KEY_POSTGRES_USER=<production-user>
export KEY_POSTGRES_PASSWORD=<production-password>
export KEY_POSTGRES_PORT=5432
```

### Step 3: Check for orphaned workflows (dry-run)

```bash
python3 fix_orphaned_workflows.py
```

This will list all orphaned workflows without making any changes.

### Step 4: Choose your fix strategy

#### Option A: Delete orphaned workflows (recommended)

**Dry-run first:**

```bash
python3 fix_orphaned_workflows.py --delete
```

**Execute deletion:**

```bash
python3 fix_orphaned_workflows.py --delete --execute
```

This will permanently delete the orphaned workflows and all their graph definitions.

#### Option B: Add memberships (if you want to keep the workflows)

**Dry-run first:**

```bash
python3 fix_orphaned_workflows.py --add-membership
```

**Execute:**

```bash
python3 fix_orphaned_workflows.py --add-membership --execute
```

This will add `OWNER` memberships to the orphaned workflows for their `created_by_user_id`.

**Note:** This option will fail if the user doesn't exist in the database.

## Running via Kubernetes (if backend is in k8s)

If your backend is running in Kubernetes, you can exec into a pod:

```bash
# Find the backend pod
kubectl get pods -n <namespace> | grep backend

# Copy the script to the pod
kubectl cp fix_orphaned_workflows.py <namespace>/<pod-name>:/tmp/

# Exec into the pod
kubectl exec -it <pod-name> -n <namespace> -- /bin/bash

# Run the script
cd /tmp
python3 fix_orphaned_workflows.py
python3 fix_orphaned_workflows.py --delete --execute
```

## Running via Docker

If running via Docker Compose:

```bash
# Copy script to container
docker cp fix_orphaned_workflows.py <container-name>:/app/

# Exec into container
docker exec -it <container-name> /bin/bash

# Run the script
cd /app
python3 fix_orphaned_workflows.py
python3 fix_orphaned_workflows.py --delete --execute
```

## Safety Features

1. **Dry-run by default**: The script shows what it will do without actually making changes unless `--execute` is provided
2. **Double-check memberships**: Before deleting/modifying, the script verifies the workflow has no memberships
3. **Transaction safety**: All database operations are wrapped in transactions that rollback on error

## What Gets Deleted

When using `--delete --execute`, the script will:

- Delete all `GraphDefinition` records associated with the orphaned workflow
- Delete the `Workflow` record itself
- NOT delete any `WorkflowMembership` records (there are none for orphaned workflows)
- NOT delete the `Workflow` if it has any memberships (safety check)

## Expected Output

### Check only

```
Found 6 orphaned workflow(s):
1. Workflow: Test MCP Servers
   ID: e49a217a-c9c1-4670-83c0-0d11999200b9
   Created by: user
   Latest version: 1
   Graph definitions: 1
   Workspaces: library
...
```

### Delete (dry-run)

```
Deleting orphaned workflows...
[DRY-RUN] Deleted workflow 'Test MCP Servers' (1 graph definitions)
...
DRY RUN: Would have processed 6/6 workflow(s)
```

### Delete (execute)

```
Deleting orphaned workflows...
✓ Deleted workflow 'Test MCP Servers' (1 graph definitions)
...
Successfully processed 6/6 workflow(s)
```

## Verification After Cleanup

Run the check again to confirm no orphaned workflows remain:

```bash
python3 fix_orphaned_workflows.py
```

Expected output:

```
✅ No orphaned workflows found!
```

## Preventing Future Orphaned Workflows

The fix in PR #139 ensures that:

1. `import_raw_workflow()` now creates `WorkflowMembership` records
2. Race conditions in concurrent saves are handled gracefully

Deploy PR #139 to production to prevent new orphaned workflows from being created.
