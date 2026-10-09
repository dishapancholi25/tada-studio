#!/usr/bin/env python3
"""
Script to find and fix orphaned workflows and graph definitions in the database.

An orphaned workflow is one that has no WorkflowMembership records.
An orphaned graph definition is one where workflow_id is NULL or the workflow doesn't exist.

By default, scans ALL workflows, graphs, and users in the database.

Usage:
    # Scan entire database and show what would be fixed (dry-run)
    python fix_orphaned_workflows.py

    # Scan entire database and actually fix all issues
    python fix_orphaned_workflows.py --fix

    # Diagnose a specific workflow only
    python fix_orphaned_workflows.py --workflow "Test MCP Servers" --workspace admin
"""

import sys
import os
from typing import List, Dict, Any

# Add the project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from sqlalchemy import or_
from backend.services.database import get_db
from backend.models import (
    GraphDefinition,
    Workflow,
    WorkflowMembership,
    WorkflowRole,
    User,
)
from backend.models.workflows.agent_template import AgentTemplate


def find_orphaned_workflows() -> List[Dict[str, Any]]:
    """Find all workflows that have no membership records."""
    orphaned = []

    with get_db() as db:
        # Get all workflows that are not deleted
        workflows = db.query(Workflow).filter(~Workflow.is_deleted).all()

        for workflow in workflows:
            # Check if there are any memberships
            membership_count = (
                db.query(WorkflowMembership)
                .filter(WorkflowMembership.workflow_id == workflow.id)
                .count()
            )

            if membership_count == 0:
                # Get graph definitions
                graph_defs = (
                    db.query(GraphDefinition)
                    .filter(GraphDefinition.workflow_id == workflow.id)
                    .all()
                )
                graph_def_count = len(graph_defs)

                # Get workspace IDs
                workspace_ids = list(set(gd.workspace_id for gd in graph_defs))

                # Count agent templates
                graph_def_ids = [gd.id for gd in graph_defs]
                agent_template_count = 0
                if graph_def_ids:
                    agent_template_count = (
                        db.query(AgentTemplate)
                        .filter(AgentTemplate.graph_definition_id.in_(graph_def_ids))
                        .count()
                    )

                orphaned.append(
                    {
                        "id": workflow.id,
                        "name": workflow.name,
                        "created_by_user_id": workflow.created_by_user_id,
                        "latest_version": workflow.latest_version,
                        "graph_def_count": graph_def_count,
                        "agent_template_count": agent_template_count,
                        "workspaces": workspace_ids,
                    }
                )

    return orphaned


def delete_orphaned_workflow(workflow_id: str, dry_run: bool = True) -> bool:
    """Delete an orphaned workflow and all its graph definitions."""
    with get_db() as db:
        workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not workflow:
            print(f"   ❌ Workflow {workflow_id} not found")
            return False

        # Double-check no memberships
        membership_count = (
            db.query(WorkflowMembership)
            .filter(WorkflowMembership.workflow_id == workflow_id)
            .count()
        )
        if membership_count > 0:
            print(f"   ⚠️  Workflow {workflow_id} has memberships, skipping")
            return False

        # Get graph definitions
        graph_defs = (
            db.query(GraphDefinition)
            .filter(GraphDefinition.workflow_id == workflow_id)
            .all()
        )

        # Get agent templates that reference these graph definitions
        graph_def_ids = [gd.id for gd in graph_defs]
        agent_templates = []
        if graph_def_ids:
            agent_templates = (
                db.query(AgentTemplate)
                .filter(AgentTemplate.graph_definition_id.in_(graph_def_ids))
                .all()
            )

        if not dry_run:
            # Delete agent templates first (they reference graph definitions)
            for at in agent_templates:
                db.delete(at)

            # Delete graph definitions
            for gd in graph_defs:
                db.delete(gd)

            # Delete workflow
            db.delete(workflow)
            db.commit()

        print(
            f"   {'[DRY-RUN]' if dry_run else '✓'} Deleted workflow '{workflow.name}' "
            f"({len(graph_defs)} graph definitions, {len(agent_templates)} agent templates)"
        )
        return True


def add_membership_to_orphaned_workflow(workflow_id: str, dry_run: bool = True) -> bool:
    """Add owner membership to an orphaned workflow."""
    with get_db() as db:
        workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not workflow:
            print(f"   ❌ Workflow {workflow_id} not found")
            return False

        # Double-check no memberships
        membership_count = (
            db.query(WorkflowMembership)
            .filter(WorkflowMembership.workflow_id == workflow_id)
            .count()
        )
        if membership_count > 0:
            print(f"   ⚠️  Workflow {workflow_id} already has memberships, skipping")
            return False

        # Try to find the user
        user_id = workflow.created_by_user_id
        if not user_id:
            print(f"   ❌ Workflow '{workflow.name}' has no created_by_user_id")
            return False

        # Check if user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            print(f"   ❌ User {user_id} not found for workflow '{workflow.name}'")
            return False

        if not dry_run:
            # Create membership
            membership = WorkflowMembership(
                workflow_id=workflow_id, user_id=user_id, role=WorkflowRole.OWNER
            )
            db.add(membership)
            db.commit()

        print(
            f"   {'[DRY-RUN]' if dry_run else '✓'} Added OWNER membership for "
            f"user '{user.email or user_id}' to workflow '{workflow.name}'"
        )
        return True


def find_orphaned_graph_definitions() -> List[Dict[str, Any]]:
    """Find all graph definitions that have no valid workflow."""
    orphaned = []

    with get_db() as db:
        # Find graph definitions where:
        # 1. workflow_id is NULL, or
        # 2. The workflow doesn't exist
        graph_defs = (
            db.query(GraphDefinition)
            .filter(
                or_(
                    GraphDefinition.workflow_id.is_(None),
                    ~db.query(Workflow)
                    .filter(Workflow.id == GraphDefinition.workflow_id)
                    .exists(),
                )
            )
            .all()
        )

        for gd in graph_defs:
            # Check if workflow exists
            workflow_exists = False
            workflow_name = None
            if gd.workflow_id:
                workflow = (
                    db.query(Workflow).filter(Workflow.id == gd.workflow_id).first()
                )
                if workflow:
                    workflow_exists = True
                    workflow_name = workflow.name

            orphaned.append(
                {
                    "id": gd.id,
                    "name": gd.name,
                    "workspace_id": gd.workspace_id,
                    "version": gd.version,
                    "is_latest": gd.is_latest,
                    "workflow_id": gd.workflow_id,
                    "workflow_exists": workflow_exists,
                    "workflow_name": workflow_name,
                    "created_at": gd.created_at,
                    "created_by": gd.created_by,
                }
            )

    return orphaned


def delete_orphaned_graph_definition(graph_def_id: str, dry_run: bool = True) -> bool:
    """Delete an orphaned graph definition."""
    with get_db() as db:
        graph_def = (
            db.query(GraphDefinition).filter(GraphDefinition.id == graph_def_id).first()
        )

        if not graph_def:
            print(f"   ❌ Graph definition {graph_def_id} not found")
            return False

        if not dry_run:
            db.delete(graph_def)
            db.commit()

        print(
            f"   {'[DRY-RUN]' if dry_run else '✓'} Deleted graph definition "
            f"'{graph_def.name}' v{graph_def.version} in workspace '{graph_def.workspace_id}' "
            f"(workflow_id: {graph_def.workflow_id or 'None'})"
        )
        return True


def diagnose_workflow(workflow_name: str, workspace_id: str):
    """Diagnose the state of a specific workflow in the database."""
    from sqlalchemy import desc

    print(f"\n{'=' * 80}")
    print("Workflow Diagnostic (Single Workflow)")
    print(f"{'=' * 80}\n")
    print(f"Workflow: {workflow_name}")
    print(f"Workspace: {workspace_id}\n")

    with get_db() as db:
        # First, search for this workflow name in ALL workspaces
        all_graph_defs = (
            db.query(GraphDefinition)
            .filter(GraphDefinition.name == workflow_name)
            .order_by(GraphDefinition.workspace_id, desc(GraphDefinition.version))
            .all()
        )

        if all_graph_defs:
            workspaces = list(set(gd.workspace_id for gd in all_graph_defs))
            print(
                f"Found '{workflow_name}' in {len(workspaces)} workspace(s): {', '.join(workspaces)}\n"
            )

        # Query graph definitions for the specified workspace
        graph_defs = (
            db.query(GraphDefinition)
            .filter(
                GraphDefinition.name == workflow_name,
                GraphDefinition.workspace_id == workspace_id,
            )
            .order_by(desc(GraphDefinition.version))
            .all()
        )

        if not graph_defs:
            print(
                f"❌ No graph definitions found for '{workflow_name}' in workspace '{workspace_id}'"
            )
            if all_graph_defs:
                print(
                    f"\nBut found {len(all_graph_defs)} definition(s) in other workspaces. Re-run with the correct workspace.\n"
                )
            return

        print(f"Found {len(graph_defs)} graph definition(s):\n")

        # Track workflow IDs
        workflow_ids = set()

        for gd in graph_defs:
            workflow_ids.add(gd.workflow_id)
            status = "✅ LATEST" if gd.is_latest else "⚠️  OLD"
            print(f"{status}")
            print(f"  ID: {gd.id}")
            print(f"  Version: {gd.version}")
            print(f"  Workflow ID: {gd.workflow_id}")
            print(f"  Created: {gd.created_at}")
            print(f"  Updated: {gd.updated_at}")
            print(f"  Created By: {gd.created_by}")
            print(f"  Parent Version ID: {gd.parent_version_id}")
            print()

        # Check for multiple version 1 records (indicates orphaned data)
        version_ones = [gd for gd in graph_defs if gd.version == 1]
        if len(version_ones) > 1:
            print(
                f"🚨 PROBLEM: Found {len(version_ones)} version 1 records! Should only have one."
            )
            print("   This indicates orphaned data from incomplete deletion.\n")

        # Check workflows
        print(f"\nWorkflow records ({len(workflow_ids)} unique):\n")
        for wf_id in workflow_ids:
            if wf_id is None:
                print("⚠️  Workflow ID is None (orphaned graph definitions)\n")
                continue

            workflow = db.query(Workflow).filter(Workflow.id == wf_id).first()
            if workflow:
                status = "🗑️  DELETED" if workflow.is_deleted else "✅ ACTIVE"
                print(f"{status}")
                print(f"  ID: {workflow.id}")
                print(f"  Name: {workflow.name}")
                print(f"  Is Deleted: {workflow.is_deleted}")
                print(f"  Created By User ID: {workflow.created_by_user_id}")
                print(f"  Latest Version: {workflow.latest_version}")

                # Check memberships
                memberships = (
                    db.query(WorkflowMembership)
                    .filter(WorkflowMembership.workflow_id == wf_id)
                    .all()
                )
                print(f"  Memberships: {len(memberships)}")
                for m in memberships:
                    print(f"    - User ID: {m.user_id}, Role: {m.role}")
                print()
            else:
                print(f"⚠️  Workflow {wf_id} NOT FOUND (orphaned graph definitions)\n")

        # Summary
        print(f"\n{'=' * 80}")
        print("SUMMARY")
        print(f"{'=' * 80}")
        print(f"Total graph definitions: {len(graph_defs)}")
        print(f"Latest versions: {len([gd for gd in graph_defs if gd.is_latest])}")
        print(f"Unique workflows: {len(workflow_ids)}")
        print(f"Version 1 records: {len(version_ones)}")

        if len(version_ones) > 1 or len([gd for gd in graph_defs if gd.is_latest]) > 1:
            print("\n⚠️  ACTION NEEDED: Use --delete-graphs to fix orphaned records")
        else:
            print("\n✅ No obvious issues detected")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Find and fix orphaned workflows and graph definitions across ALL users, workspaces, and workflows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan entire database and show what would be fixed (dry-run)
  python fix_orphaned_workflows.py

  # Scan entire database and actually fix all issues
  python fix_orphaned_workflows.py --fix

  # Diagnose a specific workflow only (no fixing, just detailed info)
  python fix_orphaned_workflows.py --workflow "Test MCP Servers" --workspace admin

Note: Default mode scans ALL workflows, graphs, and users in the database.
      Use --workflow and --workspace to limit diagnosis to a specific workflow.
        """,
    )
    parser.add_argument(
        "--workflow",
        type=str,
        help="Filter to a specific workflow by name (diagnostic only, no fixing)",
    )
    parser.add_argument(
        "--workspace",
        type=str,
        help="Workspace ID for specific workflow (required with --workflow)",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Actually perform fixes on found issues (default is dry-run)",
    )

    args = parser.parse_args()

    # Handle specific workflow diagnosis
    if args.workflow:
        if not args.workspace:
            print("Error: --workspace required when using --workflow")
            sys.exit(1)
        diagnose_workflow(args.workflow, args.workspace)
        return

    # Default mode always runs autofix in dry-run or execute mode
    dry_run = not args.fix

    print(f"\n{'=' * 70}")
    print("Database Health Check - Full Scan")
    print(f"{'=' * 70}\n")
    print("Scanning: ALL workflows, graphs, and users in the database")
    print(
        f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (will make changes)'}\n"
    )

    # Find all issues across the entire database
    print("Scanning for orphaned records...")
    orphaned_graphs = find_orphaned_graph_definitions()
    orphaned_workflows = find_orphaned_workflows()

    total_issues = len(orphaned_graphs) + len(orphaned_workflows)
    print("Scan complete.\n")

    # Display orphaned graph definitions
    if orphaned_graphs:
        print(f"🚨 Found {len(orphaned_graphs)} orphaned graph definition(s):\n")
        for i, gd in enumerate(orphaned_graphs, 1):
            workflow_status = "EXISTS" if gd["workflow_exists"] else "MISSING"
            workflow_display = gd["workflow_name"] or gd["workflow_id"] or "None"
            latest_marker = " [LATEST]" if gd["is_latest"] else ""

            print(f"{i}. Graph: {gd['name']} v{gd['version']}{latest_marker}")
            print(f"   ID: {gd['id'][:8]}...")
            print(f"   Workspace: {gd['workspace_id']}")
            print(f"   Workflow: {workflow_display} ({workflow_status})")
            print()
    else:
        print("✅ No orphaned graph definitions found\n")

    # Display orphaned workflows
    if orphaned_workflows:
        print(f"🚨 Found {len(orphaned_workflows)} orphaned workflow(s):\n")
        for i, workflow in enumerate(orphaned_workflows, 1):
            print(f"{i}. Workflow: {workflow['name']}")
            print(f"   ID: {workflow['id'][:8]}...")
            print(f"   Created by: {workflow['created_by_user_id']}")
            print(f"   Graph definitions: {workflow['graph_def_count']}")
            print(f"   Agent templates: {workflow['agent_template_count']}")
            print()
    else:
        print("✅ No orphaned workflows found\n")

    # Summary
    print(f"{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")
    print(f"Total issues found: {total_issues}")
    print(f"  - Orphaned graph definitions: {len(orphaned_graphs)}")
    print(f"  - Orphaned workflows: {len(orphaned_workflows)}")
    print()

    if total_issues == 0:
        print("✅ Database is healthy!\n")
        return

    # Always show what would be fixed (or actually fix if --fix is used)
    print(f"{'=' * 70}")
    print(f"{'[DRY-RUN] Would fix' if dry_run else 'Fixing'} all issues...")
    print(f"{'=' * 70}\n")

    fixed_count = 0

    # Fix orphaned graph definitions
    if orphaned_graphs:
        print("Fixing orphaned graph definitions...")
        for gd in orphaned_graphs:
            if delete_orphaned_graph_definition(gd["id"], dry_run=dry_run):
                fixed_count += 1

    # Fix orphaned workflows by adding memberships
    if orphaned_workflows:
        print("\nFixing orphaned workflows...")
        for workflow in orphaned_workflows:
            if add_membership_to_orphaned_workflow(workflow["id"], dry_run=dry_run):
                fixed_count += 1

    print(f"\n{'=' * 70}")
    if dry_run:
        print(f"DRY RUN: Would have fixed {fixed_count}/{total_issues} issue(s)")
        print("Run with --fix to actually perform these fixes")
    else:
        print(f"✅ Successfully fixed {fixed_count}/{total_issues} issue(s)")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    main()
