"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useGraph } from "@/contexts/GraphContext";
import { useLoadingOverlay } from "@/contexts/LoadingOverlayContext";
import { useToast } from "@/contexts/ToastContext";
import { api } from "@/lib/api";
import { useGraphStore } from "@/stores/graphStore";
import GraphManagementModalContainer from "./GraphManagementModalContainer";

interface GraphManagementDialogProps {
  isOpen: boolean;
  onClose: () => void;
  initialTab?: "create" | "load";
  mode?: "modal" | "page";
}

interface Graph {
  name: string;
  workflow_id?: string; // UUID for unique workflow identification
  description?: string;
  created_at: string;
  updated_at?: string;
  workflow_role?: string;
  owner_name?: string;
  is_shared?: boolean;
}

export default function GraphManagementDialog({
  isOpen,
  onClose,
  initialTab = "load",
  mode = "modal",
}: GraphManagementDialogProps) {
  const router = useRouter();
  const { createGraph, deleteGraph, currentGraph } = useGraph();
  const { showOverlay, hideOverlay } = useLoadingOverlay();
  const { showSuccess, showError } = useToast();
  const [graphs, setGraphs] = useState<Graph[]>([]);
  const [newGraphName, setNewGraphName] = useState("");
  const [newGraphDescription, setNewGraphDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [creatingWorkflow, setCreatingWorkflow] = useState(false);
  const [creationMessage, setCreationMessage] = useState("");
  const [activeTab, setActiveTab] = useState<"create" | "load">(initialTab);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortOption, setSortOption] = useState<
    "created" | "updated" | "alphabetical"
  >("created");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");
  const [deleteConfirmation, setDeleteConfirmation] = useState<{
    isOpen: boolean;
    graphName: string | null;
  }>({
    isOpen: false,
    graphName: null,
  });
  const [deletingGraph, setDeletingGraph] = useState<string | null>(null);
  const [editModal, setEditModal] = useState<{
    isOpen: boolean;
    graphName: string;
    graphDescription: string;
  }>({ isOpen: false, graphName: "", graphDescription: "" });
  const [editSaving, setEditSaving] = useState(false);

  // Handle escape key for delete confirmation modal
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape" && deleteConfirmation.isOpen) {
        setDeleteConfirmation({ isOpen: false, graphName: null });
      }
    };

    if (deleteConfirmation.isOpen) {
      document.addEventListener("keydown", handleEscape);
      return () => document.removeEventListener("keydown", handleEscape);
    }
  }, [deleteConfirmation.isOpen]);

  // Reset edit modal when main dialog closes, and sync tab when opening
  useEffect(() => {
    if (isOpen) {
      setActiveTab(initialTab);
    } else {
      setEditModal({ isOpen: false, graphName: "", graphDescription: "" });
      setEditSaving(false);
    }
  }, [isOpen, initialTab]);

  useEffect(() => {
    // console.log('[GraphManagementDialog] Dialog opened, loading graph list');
    if (isOpen) {
      loadGraphList().catch((error) => {
        console.error("Failed to load graph list:", error);
      });
    }
  }, [isOpen]);

  const loadGraphList = async () => {
    try {
      setLoading(true);
      const response = await api.listGraphs();
      if (response.success) {
        setGraphs(response.graphs);
      }
    } catch {
      // console.error('Failed to load graphs');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateGraph = async () => {
    if (!newGraphName.trim()) {
      alert("Please enter a graph name");
      return;
    }

    try {
      // Show a global overlay for 1s minimum to mask UI quirks while navigating
      showOverlay({ message: "Creating workflow...", minDurationMs: 1000 });
      setCreatingWorkflow(true);
      setCreationMessage("Creating workflow...");

      // Create the graph first (stores result in Zustand via loadGraphToStore)
      await createGraph(newGraphName, newGraphDescription);

      // Get workflow_id from the store (already loaded by createGraph)
      const workflowId = useGraphStore.getState().currentGraph?.workflow_id;

      if (!workflowId) {
        throw new Error("Failed to retrieve workflow ID for new workflow");
      }

      // Clear form
      setNewGraphName("");
      setNewGraphDescription("");

      // Mark that this is a new workflow so the workflow page uses 1s minimum load
      sessionStorage.setItem("newWorkflowCreation", "true");

      // Navigate using workflow ID
      router.push(`/workflow/${workflowId}`);
      onClose();

      // Let overlay auto-hide after its minDuration; also stop local spinner state
      setCreatingWorkflow(false);
      setCreationMessage("");
      // If navigation completes super fast, allow manual hide request; minDuration enforces timing
      hideOverlay();
    } catch (err) {
      alert("Failed to create graph: " + (err as Error).message);
      setCreatingWorkflow(false);
      setCreationMessage("");
      hideOverlay();
    }
  };

  const handleLoadGraph = async (graph: Graph) => {
    try {
      // Use workflow_id if available, fall back to name for legacy workflows
      const workflowIdentifier =
        graph.workflow_id || encodeURIComponent(graph.name);

      // Short global overlay when loading an existing workflow
      showOverlay({
        message: `Loading workflow: ${graph.name}...`,
        minDurationMs: 500,
      });
      setLoading(true);
      onClose();
      // Navigate to the selected workflow using workflow ID
      router.push(`/workflow/${workflowIdentifier}`);
      hideOverlay();
    } catch (err) {
      alert("Failed to load graph: " + (err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleEditGraph = (graph: Graph) => {
    setEditModal({
      isOpen: true,
      graphName: graph.name,
      graphDescription: graph.description || "",
    });
  };

  const handleEditSave = async (newName: string, newDescription: string) => {
    const originalName = editModal.graphName;
    const originalDescription = editModal.graphDescription;
    if (!originalName) return;

    try {
      setEditSaving(true);

      const nameChanged = newName !== originalName;
      const descriptionChanged = newDescription !== originalDescription;

      // Update name if changed
      if (nameChanged) {
        await api.updateWorkflowName(originalName, newName);
      }

      // Update description if changed
      if (descriptionChanged) {
        // Use the new name if it was changed, since the backend uses graph_name
        const graphNameForDesc = nameChanged ? newName : originalName;
        await api.updateWorkflowDescription(graphNameForDesc, newDescription);
      }

      // Update local state
      setGraphs((prev) =>
        prev.map((g) =>
          g.name === originalName
            ? { ...g, name: newName, description: newDescription }
            : g,
        ),
      );

      setEditModal({ isOpen: false, graphName: "", graphDescription: "" });
      showSuccess(
        "Workflow Updated",
        `"${newName}" has been updated successfully`,
      );
    } catch (err) {
      showError("Failed to update workflow", (err as Error).message);
    } finally {
      setEditSaving(false);
    }
  };

  const handleEditCancel = () => {
    if (!editSaving) {
      setEditModal({ isOpen: false, graphName: "", graphDescription: "" });
    }
  };

  const handleDeleteGraph = async (graphName: string) => {
    setDeleteConfirmation({ isOpen: true, graphName });
  };

  const confirmDelete = async () => {
    const graphName = deleteConfirmation.graphName;
    if (!graphName) return;

    try {
      setDeletingGraph(graphName);
      setDeleteConfirmation({ isOpen: false, graphName: null });

      // Check if we're deleting the currently active workflow
      const isDeletingCurrentWorkflow = currentGraph?.name === graphName;

      // Add a small delay for smooth animation
      await new Promise((resolve) => setTimeout(resolve, 200));

      await deleteGraph(graphName);

      // Smooth reload with fade effect - optimistic UI update
      setGraphs((prev) => prev.filter((g) => g.name !== graphName));

      // Show success notification with proper styling
      showSuccess(
        "Workflow Deleted",
        `"${graphName}" has been removed successfully`,
      );

      // Clear the deleting state after animation completes
      setTimeout(() => {
        setDeletingGraph(null);
      }, 300);

      // If we deleted the current workflow, navigate to home after closing modal
      if (isDeletingCurrentWorkflow) {
        // Close modal first to prevent flash
        onClose();
        // Navigate to home page
        router.push("/");
      }
    } catch (err) {
      showError("Failed to delete workflow", (err as Error).message);
      setDeletingGraph(null);
      // Reload to restore the correct state on error
      await loadGraphList();
    }
  };

  const handleImportGraph = async (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      showOverlay({ message: "Importing workflow...", minDurationMs: 1000 });
      setCreatingWorkflow(true);
      setCreationMessage("Parsing workflow file...");

      const text = await file.text();
      const data = JSON.parse(text);

      // Validate the imported data structure
      if (!data.name) {
        throw new Error("Invalid workflow file: missing name");
      }

      if (!data.nodes || !Array.isArray(data.nodes)) {
        throw new Error(
          "Invalid workflow file: missing or invalid nodes array",
        );
      }

      // Generate a unique name if a workflow with this name already exists
      let workflowName = data.name;
      const existingNames = graphs.map((g) => g.name);
      if (existingNames.includes(workflowName)) {
        let counter = 1;
        while (existingNames.includes(`${workflowName} (${counter})`)) {
          counter++;
        }
        workflowName = `${workflowName} (${counter})`;
      }

      setCreationMessage(`Importing workflow: ${workflowName}...`);

      // Import the raw workflow JSON directly without validation
      const response = await api.importRawWorkflow({
        name: workflowName,
        description: data.description || "Imported workflow",
        workflow_json: data,
      });

      if (!response.success || !response.workflow_id) {
        throw new Error("Failed to import workflow");
      }

      const workflowId = response.workflow_id;
      const warnings = response.warnings || [];

      // Success! Show the imported workflow
      if (warnings.length > 0) {
        // Show warning if there were model configuration issues
        const warningMessage =
          `"${workflowName}" has been imported, but some agent models need to be configured:\n\n` +
          warnings.join("\n");
        showSuccess("Workflow Imported with Warnings", warningMessage);
      } else {
        showSuccess(
          "Workflow Imported",
          `"${workflowName}" has been imported successfully`,
        );
      }

      // Navigate to the imported workflow
      sessionStorage.setItem("newWorkflowCreation", "true");
      router.push(`/workflow/${workflowId}`);
      onClose();

      setCreatingWorkflow(false);
      setCreationMessage("");
      hideOverlay();
    } catch (err) {
      showError("Import Failed", (err as Error).message);
      setCreatingWorkflow(false);
      setCreationMessage("");
      hideOverlay();
    }
  };

  return (
    <GraphManagementModalContainer
      isOpen={isOpen}
      mode={mode}
      creatingWorkflow={creatingWorkflow}
      activeTab={activeTab}
      onTabChange={setActiveTab}
      searchQuery={searchQuery}
      onSearchChange={setSearchQuery}
      sortOption={sortOption}
      onSortOptionChange={setSortOption}
      sortDirection={sortDirection}
      onSortDirectionToggle={() =>
        setSortDirection((d) => (d === "asc" ? "desc" : "asc"))
      }
      graphName={newGraphName}
      onGraphNameChange={setNewGraphName}
      graphDescription={newGraphDescription}
      onGraphDescriptionChange={setNewGraphDescription}
      loading={loading}
      creationMessage={creationMessage}
      onCreateGraph={handleCreateGraph}
      onImportGraph={handleImportGraph}
      graphs={graphs}
      currentGraph={currentGraph}
      deletingGraph={deletingGraph}
      onLoadGraph={handleLoadGraph}
      onEditGraph={handleEditGraph}
      onDeleteGraph={handleDeleteGraph}
      editModal={editModal}
      editSaving={editSaving}
      onEditSave={handleEditSave}
      onEditCancel={handleEditCancel}
      deleteConfirmation={deleteConfirmation}
      onConfirmDelete={confirmDelete}
      onCancelDelete={() =>
        setDeleteConfirmation({ isOpen: false, graphName: null })
      }
      onClose={onClose}
    />
  );
}
