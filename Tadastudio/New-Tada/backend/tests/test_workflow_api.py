"""Tests for core workflow API operations.

This module tests the fundamental workflow operations:
- Create workflow
- List workflows
- Add node to workflow
- Save workflow
- Get workflow
- Delete workflow
- Execute workflow (with real LLM)
"""

import pytest


class TestWorkflowCRUD:
    """Test suite for workflow CRUD operations."""

    def test_create_workflow(
        self, test_client, unique_workflow_name, cleanup_workflows
    ):
        """Test creating a new workflow."""
        cleanup_workflows.append(unique_workflow_name)

        response = test_client.post(
            "/api/graph/create",
            json={
                "name": unique_workflow_name,
                "description": "Test workflow created by pytest",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "graph" in data
        assert data["graph"]["name"] == unique_workflow_name

    def test_list_workflows(self, test_client, unique_workflow_name, cleanup_workflows):
        """Test listing workflows shows created workflow."""
        cleanup_workflows.append(unique_workflow_name)

        # Create a workflow first
        test_client.post(
            "/api/graph/create",
            json={"name": unique_workflow_name, "description": "Test"},
        )

        # List workflows
        response = test_client.get("/api/graph/list")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "graphs" in data

        # Find our workflow in the list
        workflow_names = [g["name"] for g in data["graphs"]]
        assert unique_workflow_name in workflow_names

    def test_get_workflow(self, test_client, unique_workflow_name, cleanup_workflows):
        """Test retrieving a specific workflow."""
        cleanup_workflows.append(unique_workflow_name)

        # Create a workflow first
        test_client.post(
            "/api/graph/create",
            json={"name": unique_workflow_name, "description": "Test"},
        )

        # Get the workflow
        response = test_client.get(f"/api/graph/{unique_workflow_name}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["graph"]["name"] == unique_workflow_name

    def test_save_workflow(self, test_client, unique_workflow_name, cleanup_workflows):
        """Test saving a workflow persists it."""
        cleanup_workflows.append(unique_workflow_name)

        # Create a workflow
        test_client.post(
            "/api/graph/create",
            json={"name": unique_workflow_name, "description": "Test"},
        )

        # Save it
        response = test_client.post(f"/api/graph/save/{unique_workflow_name}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_delete_workflow(self, test_client, unique_workflow_name):
        """Test deleting a workflow removes it."""
        # Create a workflow
        test_client.post(
            "/api/graph/create",
            json={"name": unique_workflow_name, "description": "Test"},
        )

        # Delete it
        response = test_client.delete(f"/api/graph/{unique_workflow_name}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify it's gone
        response = test_client.get(f"/api/graph/{unique_workflow_name}")
        assert response.status_code == 404


class TestNodeOperations:
    """Test suite for node operations within workflows."""

    def test_add_agent_node(self, test_client, unique_workflow_name, cleanup_workflows):
        """Test adding an AGENT node to a workflow."""
        cleanup_workflows.append(unique_workflow_name)

        # Create a workflow first
        test_client.post(
            "/api/graph/create",
            json={"name": unique_workflow_name, "description": "Test"},
        )

        # Add an agent node
        response = test_client.post(
            "/api/graph/node/create",
            json={
                "graph_name": unique_workflow_name,
                "node_type": "AGENT",
                "name": "Test Agent",
                "position": {"x": 100, "y": 100},
                "description": "A test agent node",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "node" in data
        assert data["node"]["name"] == "Test Agent"
        assert data["node"]["type"] == "AGENT"

    def test_add_end_node(self, test_client, unique_workflow_name, cleanup_workflows):
        """Test adding END node to complete a workflow (START is auto-created)."""
        cleanup_workflows.append(unique_workflow_name)

        # Create a workflow (START node is auto-created)
        create_resp = test_client.post(
            "/api/graph/create",
            json={"name": unique_workflow_name, "description": "Test"},
        )
        assert create_resp.status_code == 200
        # Verify START node was auto-created
        graph_data = create_resp.json()["graph"]
        start_nodes = [n for n in graph_data["nodes"] if n["type"] == "START"]
        assert len(start_nodes) == 1, "Expected exactly one auto-created START node"

        # Add END node
        end_response = test_client.post(
            "/api/graph/node/create",
            json={
                "graph_name": unique_workflow_name,
                "node_type": "END",
                "name": "End",
                "position": {"x": 400, "y": 100},
            },
        )
        assert end_response.status_code == 200
        end_data = end_response.json()
        assert end_data["success"] is True

    def test_agent_name_persistence(
        self, test_client, unique_workflow_name, cleanup_workflows
    ):
        """Test that agent name is persisted when set via configuration."""
        cleanup_workflows.append(unique_workflow_name)

        # Create a workflow
        test_client.post(
            "/api/graph/create",
            json={"name": unique_workflow_name, "description": "Test"},
        )

        # Add an agent node with a specific name
        agent_name = "Research Assistant"
        create_response = test_client.post(
            "/api/graph/node/create",
            json={
                "graph_name": unique_workflow_name,
                "node_type": "AGENT",
                "name": agent_name,
                "position": {"x": 100, "y": 100},
                "description": "Test agent for name persistence",
                "agent_config": {
                    "system_prompt": "You are a helpful research assistant.",
                },
            },
        )

        assert create_response.status_code == 200
        create_data = create_response.json()
        assert create_data["success"] is True
        node_id = create_data["node"]["uniq_id"]
        assert create_data["node"]["name"] == agent_name

        # Update the agent node with a new name via configuration
        updated_name = "Advanced Research Agent"
        update_response = test_client.put(
            "/api/graph/node/update",
            json={
                "graph_name": unique_workflow_name,
                "node_id": node_id,
                "updates": {
                    "name": updated_name,
                    "agent_config": {
                        "system_prompt": "You are an advanced research assistant.",
                    },
                },
            },
        )

        assert update_response.status_code == 200
        update_data = update_response.json()
        assert update_data["success"] is True

        # Retrieve the workflow and verify the name persisted
        get_response = test_client.get(f"/api/graph/{unique_workflow_name}")
        assert get_response.status_code == 200
        get_data = get_response.json()
        assert get_data["success"] is True

        # Find the agent node in the retrieved workflow
        nodes = get_data["graph"]["nodes"]
        agent_node = next((n for n in nodes if n["uniq_id"] == node_id), None)
        assert agent_node is not None
        assert agent_node["name"] == updated_name

        # Verify the agent_config is also preserved
        assert "agent_config" in agent_node
        assert (
            agent_node["agent_config"]["system_prompt"]
            == "You are an advanced research assistant."
        )


class TestWorkflowExecution:
    """Test suite for workflow execution with real LLM."""

    @pytest.mark.slow
    def test_execute_simple_workflow(
        self, test_client, unique_workflow_name, cleanup_workflows
    ):
        """Test executing a simple workflow with an agent.

        This test uses real LLM calls and requires Azure OpenAI credentials.
        It is marked as 'slow' and can be skipped with: pytest -m "not slow"
        """
        import os

        cleanup_workflows.append(unique_workflow_name)

        # Create workflow (automatically includes a START node)
        create_resp = test_client.post(
            "/api/graph/create",
            json={"name": unique_workflow_name, "description": "Execution test"},
        )
        # Get the auto-created START node ID from the graph
        graph_data = create_resp.json()["graph"]
        start_node_id = next(
            node["uniq_id"] for node in graph_data["nodes"] if node["type"] == "START"
        )

        # Add AGENT node with full configuration
        # Required: system_prompt, llm_config with provider, model_name, deployment_name, api_version, api_key_env_var
        agent_resp = test_client.post(
            "/api/graph/node/create",
            json={
                "graph_name": unique_workflow_name,
                "node_type": "AGENT",
                "name": "Test Agent",
                "position": {"x": 200, "y": 100},
                "description": "A simple test agent",
                "agent_config": {
                    "system_prompt": "You are a helpful assistant. Respond concisely.",
                    "llm_config": {
                        "provider": "azure_openai",
                        "model_name": os.getenv(
                            "AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4"
                        ),
                        "deployment_name": os.getenv(
                            "AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4"
                        ),
                        "api_version": os.getenv(
                            "AZURE_OPENAI_API_VERSION", "2024-10-21"
                        ),
                        "api_key_env_var": "AZURE_OPENAI_API_KEY",
                    },
                },
            },
        )
        agent_node_id = agent_resp.json()["node"]["uniq_id"]

        # Add END node
        end_resp = test_client.post(
            "/api/graph/node/create",
            json={
                "graph_name": unique_workflow_name,
                "node_type": "END",
                "name": "End",
                "position": {"x": 400, "y": 100},
            },
        )
        end_node_id = end_resp.json()["node"]["uniq_id"]

        # Create connections: START -> AGENT -> END
        test_client.post(
            "/api/graph/connection/create",
            json={
                "graph_name": unique_workflow_name,
                "source_id": start_node_id,
                "target_id": agent_node_id,
            },
        )

        test_client.post(
            "/api/graph/connection/create",
            json={
                "graph_name": unique_workflow_name,
                "source_id": agent_node_id,
                "target_id": end_node_id,
            },
        )

        # Save workflow
        test_client.post(f"/api/graph/save/{unique_workflow_name}")

        # Execute the workflow (async)
        response = test_client.post(
            "/api/graph/execute",
            json={
                "graph_name": unique_workflow_name,
                "initial_input": {"message": "Say hello in exactly 3 words."},
                "async_execution": True,
            },
        )

        # Print response for debugging if it fails
        if response.status_code != 200:
            print(f"Execution failed: {response.json()}")

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.json()}"
        )
        data = response.json()
        assert data["success"] is True
        assert "execution_id" in data
        execution_id = data["execution_id"]

        # Poll for completion (wait up to 30 seconds)
        import time

        max_wait = 30
        poll_interval = 1
        elapsed = 0
        final_status = None

        print(f"Waiting for execution {execution_id} to complete...")
        while elapsed < max_wait:
            status_resp = test_client.get(f"/api/graph/execution/{execution_id}/status")
            if status_resp.status_code == 200:
                status_data = status_resp.json()
                exec_status = status_data.get("execution_status", {})
                current_status = exec_status.get("status", "unknown")
                print(f"  [{elapsed}s] Status: {current_status}")

                if current_status in ("completed", "failed", "error", "cancelled"):
                    final_status = exec_status
                    break

            time.sleep(poll_interval)
            elapsed += poll_interval

        assert final_status is not None, (
            f"Execution did not complete within {max_wait}s"
        )

        # Verify execution completed successfully
        assert final_status.get("status") == "completed", (
            f"Expected 'completed', got: {final_status}"
        )

        # Extract output from node executions (check AGENT node for LLM response)
        node_executions = final_status.get("node_executions", {})
        agent_output = None
        end_node_output = None

        print("\n=== NODE EXECUTIONS ===")
        for node_id, node_data in node_executions.items():
            node_type = node_data.get("node_type")
            node_name = node_data.get("node_name")
            output_data = node_data.get("output_data") or {}
            print(f"Node: {node_name} ({node_type})")
            print(f"  Output: {output_data}")

            if node_type == "AGENT":
                fields = (
                    output_data.get("fields", {})
                    if isinstance(output_data, dict)
                    else {}
                )
                agent_output = (
                    fields.get("response") or output_data.get("response")
                    if isinstance(output_data, dict)
                    else None
                )
            elif node_type == "END":
                fields = (
                    output_data.get("fields", {})
                    if isinstance(output_data, dict)
                    else {}
                )
                end_node_output = (
                    fields.get("response") or output_data.get("response")
                    if isinstance(output_data, dict)
                    else None
                )

        final_output = agent_output or end_node_output
        print("\n=== WORKFLOW COMPLETED ===")
        print(f"Status: {final_status.get('status')}")
        print(f"Response: {final_output}")
        print("==========================\n")


class TestBatchUpdateOperations:
    """Test suite for batch update API operations.

    These tests verify that the batch-update endpoint correctly handles
    adding nodes, creating connections, and other graph mutations.
    """

    def test_batch_add_node_with_type_field(
        self, test_client, unique_workflow_name, cleanup_workflows
    ):
        """Test adding a node via batch update with 'type' field."""
        cleanup_workflows.append(unique_workflow_name)

        # Create a workflow
        test_client.post(
            "/api/graph/create",
            json={"name": unique_workflow_name, "description": "Batch test"},
        )

        # Batch update to add a node (using 'type' field)
        response = test_client.post(
            "/api/graph/batch-update",
            json={
                "graph_name": unique_workflow_name,
                "changes": [
                    {
                        "type": "ADD_NODE",
                        "data": {
                            "node": {
                                "uniq_id": "batch-node-1",
                                "name": "Batch Agent",
                                "type": "AGENT",
                                "position": {"x": 200, "y": 200},
                            }
                        },
                    }
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify the node was added
        nodes = data["graph"]["nodes"]
        added_node = next((n for n in nodes if n["uniq_id"] == "batch-node-1"), None)
        assert added_node is not None
        assert added_node["name"] == "Batch Agent"
        assert added_node["type"] == "AGENT"

    def test_batch_add_node_with_node_type_field(
        self, test_client, unique_workflow_name, cleanup_workflows
    ):
        """Test adding a node via batch update with 'node_type' field (frontend format)."""
        cleanup_workflows.append(unique_workflow_name)

        # Create a workflow
        test_client.post(
            "/api/graph/create",
            json={"name": unique_workflow_name, "description": "Batch test"},
        )

        # Batch update to add a node (using 'node_type' field - frontend format)
        response = test_client.post(
            "/api/graph/batch-update",
            json={
                "graph_name": unique_workflow_name,
                "changes": [
                    {
                        "type": "ADD_NODE",
                        "data": {
                            "node": {
                                "uniq_id": "batch-node-2",
                                "name": "Frontend Agent",
                                "node_type": "AGENT",
                                "position": {"x": 300, "y": 300},
                            }
                        },
                    }
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify the node was added
        nodes = data["graph"]["nodes"]
        added_node = next((n for n in nodes if n["uniq_id"] == "batch-node-2"), None)
        assert added_node is not None
        assert added_node["name"] == "Frontend Agent"
        assert added_node["type"] == "AGENT"

    def test_batch_add_connection(
        self, test_client, unique_workflow_name, cleanup_workflows
    ):
        """Test creating a connection via batch update."""
        cleanup_workflows.append(unique_workflow_name)

        # Create a workflow (START is auto-created)
        create_resp = test_client.post(
            "/api/graph/create",
            json={"name": unique_workflow_name, "description": "Connection test"},
        )
        graph_data = create_resp.json()["graph"]
        start_node_id = next(
            node["uniq_id"] for node in graph_data["nodes"] if node["type"] == "START"
        )

        # Add an END node via batch update
        test_client.post(
            "/api/graph/batch-update",
            json={
                "graph_name": unique_workflow_name,
                "changes": [
                    {
                        "type": "ADD_NODE",
                        "data": {
                            "node": {
                                "uniq_id": "end-node-1",
                                "name": "End",
                                "type": "END",
                                "position": {"x": 400, "y": 100},
                            }
                        },
                    }
                ],
            },
        )

        # Now add a connection via batch update
        response = test_client.post(
            "/api/graph/batch-update",
            json={
                "graph_name": unique_workflow_name,
                "changes": [
                    {
                        "type": "ADD_CONNECTION",
                        "data": {
                            "sourceId": start_node_id,
                            "targetId": "end-node-1",
                            "sourceHandle": "default",
                            "targetHandle": "default",
                            "connectionType": "workflow",
                        },
                    }
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify the connection was created
        connections = data["graph"]["connections"]
        conn = next(
            (
                c
                for c in connections
                if c["source_id"] == start_node_id and c["target_id"] == "end-node-1"
            ),
            None,
        )
        assert conn is not None

    def test_batch_delete_node(
        self, test_client, unique_workflow_name, cleanup_workflows
    ):
        """Test deleting a node via batch update."""
        cleanup_workflows.append(unique_workflow_name)

        # Create a workflow and add an agent node
        test_client.post(
            "/api/graph/create",
            json={"name": unique_workflow_name, "description": "Delete test"},
        )

        # Add a node first
        test_client.post(
            "/api/graph/batch-update",
            json={
                "graph_name": unique_workflow_name,
                "changes": [
                    {
                        "type": "ADD_NODE",
                        "data": {
                            "node": {
                                "uniq_id": "to-delete-node",
                                "name": "Node To Delete",
                                "type": "AGENT",
                                "position": {"x": 200, "y": 200},
                            }
                        },
                    }
                ],
            },
        )

        # Now delete it via batch update
        response = test_client.post(
            "/api/graph/batch-update",
            json={
                "graph_name": unique_workflow_name,
                "changes": [
                    {
                        "type": "DELETE_NODE",
                        "data": {"nodeId": "to-delete-node"},
                    }
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify the node was deleted
        nodes = data["graph"]["nodes"]
        deleted_node = next(
            (n for n in nodes if n["uniq_id"] == "to-delete-node"), None
        )
        assert deleted_node is None

    def test_batch_delete_connection(
        self, test_client, unique_workflow_name, cleanup_workflows
    ):
        """Test deleting a connection via batch update."""
        cleanup_workflows.append(unique_workflow_name)

        # Create workflow with START -> END connection
        create_resp = test_client.post(
            "/api/graph/create",
            json={"name": unique_workflow_name, "description": "Delete conn test"},
        )
        graph_data = create_resp.json()["graph"]
        start_node_id = next(
            node["uniq_id"] for node in graph_data["nodes"] if node["type"] == "START"
        )

        # Add END node and connection
        test_client.post(
            "/api/graph/batch-update",
            json={
                "graph_name": unique_workflow_name,
                "changes": [
                    {
                        "type": "ADD_NODE",
                        "data": {
                            "node": {
                                "uniq_id": "end-for-delete",
                                "name": "End",
                                "type": "END",
                                "position": {"x": 400, "y": 100},
                            }
                        },
                    },
                    {
                        "type": "ADD_CONNECTION",
                        "data": {
                            "sourceId": start_node_id,
                            "targetId": "end-for-delete",
                            "connectionType": "workflow",
                        },
                    },
                ],
            },
        )

        # Delete the connection
        response = test_client.post(
            "/api/graph/batch-update",
            json={
                "graph_name": unique_workflow_name,
                "changes": [
                    {
                        "type": "DELETE_CONNECTION",
                        "data": {
                            "sourceId": start_node_id,
                            "targetId": "end-for-delete",
                        },
                    }
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify the connection was deleted
        connections = data["graph"]["connections"]
        conn = next(
            (
                c
                for c in connections
                if c["source_id"] == start_node_id
                and c["target_id"] == "end-for-delete"
            ),
            None,
        )
        assert conn is None

    def test_batch_multiple_changes(
        self, test_client, unique_workflow_name, cleanup_workflows
    ):
        """Test applying multiple changes in a single batch update."""
        cleanup_workflows.append(unique_workflow_name)

        # Create a workflow
        create_resp = test_client.post(
            "/api/graph/create",
            json={"name": unique_workflow_name, "description": "Multi-change test"},
        )
        graph_data = create_resp.json()["graph"]
        start_node_id = next(
            node["uniq_id"] for node in graph_data["nodes"] if node["type"] == "START"
        )

        # Apply multiple changes at once: add agent, add end, add connections
        response = test_client.post(
            "/api/graph/batch-update",
            json={
                "graph_name": unique_workflow_name,
                "changes": [
                    {
                        "type": "ADD_NODE",
                        "data": {
                            "node": {
                                "uniq_id": "multi-agent",
                                "name": "Multi Agent",
                                "node_type": "AGENT",
                                "position": {"x": 200, "y": 100},
                            }
                        },
                    },
                    {
                        "type": "ADD_NODE",
                        "data": {
                            "node": {
                                "uniq_id": "multi-end",
                                "name": "End",
                                "type": "END",
                                "position": {"x": 400, "y": 100},
                            }
                        },
                    },
                    {
                        "type": "ADD_CONNECTION",
                        "data": {
                            "sourceId": start_node_id,
                            "targetId": "multi-agent",
                            "connectionType": "workflow",
                        },
                    },
                    {
                        "type": "ADD_CONNECTION",
                        "data": {
                            "sourceId": "multi-agent",
                            "targetId": "multi-end",
                            "connectionType": "workflow",
                        },
                    },
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify all changes were applied
        graph = data["graph"]

        # Check nodes
        agent_node = next(
            (n for n in graph["nodes"] if n["uniq_id"] == "multi-agent"), None
        )
        end_node = next(
            (n for n in graph["nodes"] if n["uniq_id"] == "multi-end"), None
        )
        assert agent_node is not None
        assert end_node is not None
        assert agent_node["type"] == "AGENT"
        assert end_node["type"] == "END"

        # Check connections
        conn1 = next(
            (
                c
                for c in graph["connections"]
                if c["source_id"] == start_node_id and c["target_id"] == "multi-agent"
            ),
            None,
        )
        conn2 = next(
            (
                c
                for c in graph["connections"]
                if c["source_id"] == "multi-agent" and c["target_id"] == "multi-end"
            ),
            None,
        )
        assert conn1 is not None
        assert conn2 is not None


class TestHealthCheck:
    """Test suite for API health endpoints."""

    def test_root_endpoint(self, test_client):
        """Test the root endpoint returns API info."""
        response = test_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "AgenticStudio" in data["message"]

    def test_health_endpoint(self, test_client):
        """Test the health check endpoint."""
        response = test_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_graph_health_endpoint(self, test_client):
        """Test the graph API health check endpoint."""
        response = test_client.get("/api/graph/health")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "healthy"
