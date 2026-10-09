"use client";

import { Plus, X } from "lucide-react";
import type React from "react";
import CreateWorkflowTab from "./CreateWorkflowTab";
import DeleteWorkflowModal from "./DeleteWorkflowModal";
import EditWorkflowModal from "./EditWorkflowModal";
import LoadWorkflowTab from "./LoadWorkflowTab";

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

interface GraphManagementModalContainerProps {
  isOpen: boolean;
  creatingWorkflow: boolean;

  // Tab state
  activeTab: "create" | "load";
  onTabChange: (tab: "create" | "load") => void;

  // Header state (load tab)
  searchQuery: string;
  onSearchChange: (query: string) => void;
  sortOption: "created" | "updated" | "alphabetical";
  onSortOptionChange: (option: "created" | "updated" | "alphabetical") => void;
  sortDirection: "asc" | "desc";
  onSortDirectionToggle: () => void;

  // Create tab state
  graphName: string;
  onGraphNameChange: (name: string) => void;
  graphDescription: string;
  onGraphDescriptionChange: (description: string) => void;
  loading: boolean;
  creationMessage: string;
  onCreateGraph: () => void;
  onImportGraph: (event: React.ChangeEvent<HTMLInputElement>) => void;

  // Load tab state
  graphs: Graph[];
  currentGraph: { name: string } | null;
  deletingGraph: string | null;
  onLoadGraph: (graph: Graph) => void;
  onEditGraph: (graph: Graph) => void;
  onDeleteGraph: (name: string) => void;

  // Edit modal state
  editModal: {
    isOpen: boolean;
    graphName: string;
    graphDescription: string;
  };
  editSaving: boolean;
  onEditSave: (name: string, description: string) => void;
  onEditCancel: () => void;

  // Delete modal state
  deleteConfirmation: { isOpen: boolean; graphName: string | null };
  onConfirmDelete: () => void;
  onCancelDelete: () => void;

  // General
  onClose: () => void;
  mode?: "modal" | "page";
}

export default function GraphManagementModalContainer({
  isOpen,
  creatingWorkflow,
  activeTab,
  onTabChange,
  searchQuery,
  onSearchChange,
  sortOption,
  onSortOptionChange,
  sortDirection,
  onSortDirectionToggle,
  graphName,
  onGraphNameChange,
  graphDescription,
  onGraphDescriptionChange,
  loading,
  creationMessage,
  onCreateGraph,
  onImportGraph,
  graphs,
  currentGraph,
  deletingGraph,
  onLoadGraph,
  onEditGraph,
  onDeleteGraph,
  editModal,
  editSaving,
  onEditSave,
  onEditCancel,
  deleteConfirmation,
  onConfirmDelete,
  onCancelDelete,
  onClose,
  mode = "modal",
}: GraphManagementModalContainerProps) {
  // Don't unmount immediately to allow animations to complete
  if (!isOpen && !creatingWorkflow && mode === "modal") return null;

  const isCreateMode = activeTab === "create";

  const content = (
    <div
      data-tutorial="workflow-dialog"
      className={
        mode === "page"
          ? "relative w-full max-w-2xl mx-auto"
          : "relative w-full max-w-2xl max-h-[calc(100vh-120px)] rounded-[8px] border border-[#D7D7D7] bg-white animate-scaleIn flex flex-col overflow-hidden"
      }
      style={{ boxShadow: "0px 16px 42px rgba(0,0,0,0.06)" }}
    >
      {/* Header: Title + Close button */}
      {mode === "modal" && isCreateMode && (
        <div className="flex items-center justify-between border-b border-[#D7D7D7] px-4 py-3 sm:px-6 sm:py-4">
          <h2 className="text-[18px] font-semibold text-[#333333] sm:text-[20px]">New Workflow</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-[#333333] transition-colors hover:text-[#4C4C4C]"
            aria-label="Close"
          >
            <X className="h-5 w-5 sm:h-6 sm:w-6" strokeWidth={1.5} />
          </button>
        </div>
      )}

      {/* Close button for load mode */}
      {mode === "modal" && !isCreateMode && (
        <button
          type="button"
          onClick={onClose}
          className="absolute right-5 top-5 z-10 text-[#333333] transition-colors hover:text-[#4C4C4C]"
          aria-label="Close"
        >
          <X className="h-6 w-6" strokeWidth={1.5} />
        </button>
      )}

      <div className="flex-1 min-h-0 overflow-hidden flex flex-col">
        <div className="flex-1 overflow-y-auto p-4 sm:p-6">
          {isCreateMode ? (
            <CreateWorkflowTab
              graphName={graphName}
              onGraphNameChange={onGraphNameChange}
              graphDescription={graphDescription}
              onGraphDescriptionChange={onGraphDescriptionChange}
              loading={loading}
              creatingWorkflow={creatingWorkflow}
              creationMessage={creationMessage}
              onCreateGraph={onCreateGraph}
              onImportGraph={onImportGraph}
              onGoToWorkflows={() => onTabChange("load")}
            />
          ) : (
            <div className="space-y-6">
              {mode === "modal" && (
              <div className="flex items-center justify-between">
                <h2 className="text-[20px] font-semibold text-[#333333]">
                  Manage Workflows
                </h2>
                <button
                  onClick={() => onTabChange("create")}
                  className="flex items-center gap-2 rounded border border-[#FF5E00] bg-[#FF5E00] px-4 py-2 text-[14px] font-semibold text-white transition-colors hover:bg-[#E05500] hover:border-[#E05500]"
                >
                  <Plus className="h-4 w-4" />
                  <span>Create New</span>
                </button>
              </div>
              )}
              <LoadWorkflowTab
                graphs={graphs}
                loading={loading}
                searchQuery={searchQuery}
                sortOption={sortOption}
                sortDirection={sortDirection}
                currentGraph={currentGraph}
                deletingGraph={deletingGraph}
                onLoadGraph={onLoadGraph}
                onEditGraph={onEditGraph}
                onDeleteGraph={onDeleteGraph}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );

  if (mode === "page") {
    return (
      <>
        {content}
        <EditWorkflowModal
          isOpen={editModal.isOpen}
          workflowName={editModal.graphName}
          workflowDescription={editModal.graphDescription}
          saving={editSaving}
          onSave={onEditSave}
          onCancel={onEditCancel}
        />
        <DeleteWorkflowModal
          isOpen={deleteConfirmation.isOpen}
          workflowName={deleteConfirmation.graphName}
          onConfirm={onConfirmDelete}
          onCancel={onCancelDelete}
        />
      </>
    );
  }

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 backdrop-blur-[2px] p-4 animate-fadeIn">
      {content}
      <EditWorkflowModal
        isOpen={editModal.isOpen}
        workflowName={editModal.graphName}
        workflowDescription={editModal.graphDescription}
        saving={editSaving}
        onSave={onEditSave}
        onCancel={onEditCancel}
      />
      <DeleteWorkflowModal
        isOpen={deleteConfirmation.isOpen}
        workflowName={deleteConfirmation.graphName}
        onConfirm={onConfirmDelete}
        onCancel={onCancelDelete}
      />
    </div>
  );
}
