"use client";

import { lazy, Suspense, useEffect, useRef, useState } from "react";
import {
	ArrowUpDown,
	Download,
	FolderOpen,
	Pencil,
	Plus,
	Search,
	Share2,
	Trash2,
	Upload,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { useRouter } from "next/navigation";
import AppShell from "@/components/layout/AppShell";
import DeleteWorkflowModal from "@/components/core/DeleteWorkflowModal";
import Dropdown from "@/components/ui/Dropdown";
import EditWorkflowModal from "@/components/core/EditWorkflowModal";
import { useGraph } from "@/contexts/GraphContext";
import { useLoadingOverlay } from "@/contexts/LoadingOverlayContext";
import { useToast } from "@/contexts/ToastContext";
import { api } from "@/lib/api";

const GraphManagementDialog = lazy(
	() => import("@/components/core/GraphManagementDialog"),
);

interface Graph {
	name: string;
	workflow_id?: string;
	description?: string;
	created_at: string;
	updated_at?: string;
	workflow_role?: string;
	owner_name?: string;
	is_shared?: boolean;
}

// ── Mini workflow SVG thumbnails ────────────────────────────────────────────

function ThumbnailLinear() {
	return (
		<svg viewBox="0 0 220 100" className="w-full h-full" aria-hidden="true">
			<line x1="44" y1="50" x2="86" y2="50" stroke="white" strokeOpacity="0.45" strokeWidth="1.5" />
			<line x1="134" y1="50" x2="176" y2="50" stroke="white" strokeOpacity="0.45" strokeWidth="1.5" />
			<circle cx="30" cy="50" r="13" fill="white" fillOpacity="0.18" stroke="white" strokeOpacity="0.75" strokeWidth="1.5" />
			<text x="30" y="54" textAnchor="middle" fontSize="9" fill="white" fontWeight="700">S</text>
			<rect x="86" y="37" width="48" height="26" rx="8" fill="white" fillOpacity="0.18" stroke="white" strokeOpacity="0.75" strokeWidth="1.5" />
			<text x="110" y="54" textAnchor="middle" fontSize="9" fill="white" fontWeight="700">AI</text>
			<circle cx="190" cy="50" r="13" fill="white" fillOpacity="0.18" stroke="white" strokeOpacity="0.75" strokeWidth="1.5" />
			<text x="190" y="54" textAnchor="middle" fontSize="9" fill="white" fontWeight="700">E</text>
		</svg>
	);
}

function ThumbnailBranch() {
	return (
		<svg viewBox="0 0 220 120" className="w-full h-full" aria-hidden="true">
			<line x1="44" y1="60" x2="76" y2="60" stroke="white" strokeOpacity="0.45" strokeWidth="1.5" />
			<line x1="104" y1="52" x2="126" y2="36" stroke="white" strokeOpacity="0.45" strokeWidth="1.5" />
			<line x1="104" y1="68" x2="126" y2="84" stroke="white" strokeOpacity="0.45" strokeWidth="1.5" />
			<line x1="166" y1="36" x2="186" y2="60" stroke="white" strokeOpacity="0.45" strokeWidth="1.5" />
			<line x1="166" y1="84" x2="186" y2="60" stroke="white" strokeOpacity="0.45" strokeWidth="1.5" />
			<circle cx="30" cy="60" r="13" fill="white" fillOpacity="0.18" stroke="white" strokeOpacity="0.75" strokeWidth="1.5" />
			<text x="30" y="64" textAnchor="middle" fontSize="9" fill="white" fontWeight="700">S</text>
			<polygon points="90,48 104,60 90,72 76,60" fill="white" fillOpacity="0.18" stroke="white" strokeOpacity="0.75" strokeWidth="1.5" />
			<rect x="126" y="24" width="40" height="24" rx="6" fill="white" fillOpacity="0.18" stroke="white" strokeOpacity="0.75" strokeWidth="1.5" />
			<text x="146" y="40" textAnchor="middle" fontSize="9" fill="white" fontWeight="700">A</text>
			<rect x="126" y="72" width="40" height="24" rx="6" fill="white" fillOpacity="0.18" stroke="white" strokeOpacity="0.75" strokeWidth="1.5" />
			<text x="146" y="88" textAnchor="middle" fontSize="9" fill="white" fontWeight="700">B</text>
			<circle cx="200" cy="60" r="13" fill="white" fillOpacity="0.18" stroke="white" strokeOpacity="0.75" strokeWidth="1.5" />
			<text x="200" y="64" textAnchor="middle" fontSize="9" fill="white" fontWeight="700">E</text>
		</svg>
	);
}

function ThumbnailMulti() {
	return (
		<svg viewBox="0 0 240 100" className="w-full h-full" aria-hidden="true">
			<line x1="38" y1="50" x2="68" y2="50" stroke="white" strokeOpacity="0.45" strokeWidth="1.5" />
			<line x1="108" y1="50" x2="126" y2="50" stroke="white" strokeOpacity="0.45" strokeWidth="1.5" />
			<line x1="166" y1="50" x2="200" y2="50" stroke="white" strokeOpacity="0.45" strokeWidth="1.5" />
			<circle cx="24" cy="50" r="13" fill="white" fillOpacity="0.18" stroke="white" strokeOpacity="0.75" strokeWidth="1.5" />
			<text x="24" y="54" textAnchor="middle" fontSize="9" fill="white" fontWeight="700">S</text>
			<rect x="68" y="37" width="40" height="26" rx="8" fill="white" fillOpacity="0.18" stroke="white" strokeOpacity="0.75" strokeWidth="1.5" />
			<text x="88" y="54" textAnchor="middle" fontSize="8" fill="white" fontWeight="700">AI1</text>
			<rect x="126" y="37" width="40" height="26" rx="8" fill="white" fillOpacity="0.18" stroke="white" strokeOpacity="0.75" strokeWidth="1.5" />
			<text x="146" y="54" textAnchor="middle" fontSize="8" fill="white" fontWeight="700">AI2</text>
			<circle cx="214" cy="50" r="13" fill="white" fillOpacity="0.18" stroke="white" strokeOpacity="0.75" strokeWidth="1.5" />
			<text x="214" y="54" textAnchor="middle" fontSize="9" fill="white" fontWeight="700">E</text>
		</svg>
	);
}

function ThumbnailParallel() {
	return (
		<svg viewBox="0 0 240 120" className="w-full h-full" aria-hidden="true">
			<line x1="38" y1="60" x2="70" y2="60" stroke="white" strokeOpacity="0.45" strokeWidth="1.5" />
			<line x1="80" y1="54" x2="104" y2="36" stroke="white" strokeOpacity="0.45" strokeWidth="1.5" />
			<line x1="80" y1="66" x2="104" y2="84" stroke="white" strokeOpacity="0.45" strokeWidth="1.5" />
			<line x1="144" y1="36" x2="166" y2="60" stroke="white" strokeOpacity="0.45" strokeWidth="1.5" />
			<line x1="144" y1="84" x2="166" y2="60" stroke="white" strokeOpacity="0.45" strokeWidth="1.5" />
			<line x1="176" y1="60" x2="204" y2="60" stroke="white" strokeOpacity="0.45" strokeWidth="1.5" />
			<circle cx="24" cy="60" r="13" fill="white" fillOpacity="0.18" stroke="white" strokeOpacity="0.75" strokeWidth="1.5" />
			<text x="24" y="64" textAnchor="middle" fontSize="9" fill="white" fontWeight="700">S</text>
			<circle cx="76" cy="60" r="8" fill="white" fillOpacity="0.28" stroke="white" strokeOpacity="0.75" strokeWidth="1.5" />
			<rect x="104" y="24" width="40" height="24" rx="6" fill="white" fillOpacity="0.18" stroke="white" strokeOpacity="0.75" strokeWidth="1.5" />
			<text x="124" y="40" textAnchor="middle" fontSize="8" fill="white" fontWeight="700">AI1</text>
			<rect x="104" y="72" width="40" height="24" rx="6" fill="white" fillOpacity="0.18" stroke="white" strokeOpacity="0.75" strokeWidth="1.5" />
			<text x="124" y="88" textAnchor="middle" fontSize="8" fill="white" fontWeight="700">AI2</text>
			<circle cx="170" cy="60" r="8" fill="white" fillOpacity="0.28" stroke="white" strokeOpacity="0.75" strokeWidth="1.5" />
			<circle cx="218" cy="60" r="13" fill="white" fillOpacity="0.18" stroke="white" strokeOpacity="0.75" strokeWidth="1.5" />
			<text x="218" y="64" textAnchor="middle" fontSize="9" fill="white" fontWeight="700">E</text>
		</svg>
	);
}

const THUMBNAILS = [ThumbnailLinear, ThumbnailBranch, ThumbnailMulti, ThumbnailParallel];

// ── Workflow Card ────────────────────────────────────────────────────────────

interface CardProps {
	graph: Graph;
	index: number;
	isActive: boolean;
	isDeleting: boolean;
	onLoad: () => void;
	onEdit: () => void;
	onDelete: () => void;
	onExport: () => void;
}

function WorkflowCard({ graph, index, isActive, isDeleting, onLoad, onEdit, onDelete, onExport }: CardProps) {
	const ThumbnailSVG = THUMBNAILS[index % 4];
	const isSharedByOther = graph.workflow_role && graph.workflow_role !== "owner";
	const isSharedWithOthers = graph.is_shared && (!graph.workflow_role || graph.workflow_role === "owner");

	const updatedAt = graph.updated_at
		? formatDistanceToNow(new Date(graph.updated_at), { addSuffix: true })
		: formatDistanceToNow(new Date(graph.created_at), { addSuffix: true });

	return (
		<div
			className={`group relative flex flex-col overflow-hidden rounded-2xl border bg-white transition-all duration-200 ${
				isDeleting ? "pointer-events-none opacity-40 scale-[0.97]" : ""
			} ${
				isActive
					? "border-[#ff6b00] ring-2 ring-[#ff6b00]/30 shadow-[0_8px_32px_rgba(255,107,0,0.2)]"
					: "border-gray-200 hover:border-gray-300 hover:shadow-[0_8px_32px_rgba(0,0,0,0.12)] hover:-translate-y-0.5"
			}`}
		>
			{/* ── Thumbnail ── */}
			<div
				className="relative flex-none overflow-hidden"
				style={{ height: 152 }}
			>
				{/* Orange gradient background */}
				<div
					className="absolute inset-0"
					style={{
						background: isActive
							? "linear-gradient(135deg, #e85d00 0%, #ff6b00 40%, #ff9a3c 100%)"
							: "linear-gradient(135deg, #ff5500 0%, #ff6b00 45%, #ffb347 100%)",
					}}
				/>

				{/* Subtle dot grid pattern */}
				<div
					className="absolute inset-0 opacity-20"
					style={{
						backgroundImage: "radial-gradient(circle, white 1px, transparent 1px)",
						backgroundSize: "18px 18px",
					}}
				/>

				{/* SVG mini workflow */}
				<div className="absolute inset-0 flex items-center justify-center px-4 py-3">
					<ThumbnailSVG />
				</div>

				{/* Hover overlay (revealed on hover, keyboard focus, and touch/no-hover devices) */}
				<div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-black/50 opacity-0 transition-opacity duration-200 group-hover:opacity-100 group-focus-within:opacity-100 [@media(hover:none)]:opacity-100">
					{/* Primary load button */}
					<button
						type="button"
						onClick={onLoad}
						disabled={isActive}
						className="rounded-xl border border-white/30 bg-white px-5 py-2 text-sm font-semibold text-[#ff6b00] shadow-lg transition-transform duration-150 hover:scale-105 disabled:cursor-default disabled:opacity-60"
					>
						{isActive ? "Active" : "Open"}
					</button>
					{/* Secondary actions */}
					<div className="flex items-center gap-2">
						<button
							type="button"
							onClick={onEdit}
							title="Edit"
							className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/30 bg-white/90 text-slate-700 backdrop-blur-sm transition-colors hover:bg-white"
						>
							<Pencil className="h-3.5 w-3.5" />
						</button>
						<button
							type="button"
							onClick={onExport}
							title="Export"
							className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/30 bg-white/90 text-slate-700 backdrop-blur-sm transition-colors hover:bg-white"
						>
							<Download className="h-3.5 w-3.5" />
						</button>
						<button
							type="button"
							onClick={onDelete}
							title="Delete"
							className="flex h-8 w-8 items-center justify-center rounded-lg border border-red-400/40 bg-red-500/80 text-white backdrop-blur-sm transition-colors hover:bg-red-500"
						>
							<Trash2 className="h-3.5 w-3.5" />
						</button>
					</div>
				</div>

				{/* Active badge */}
				{isActive && (
					<span className="absolute left-3 top-3 flex items-center gap-1.5 rounded-full bg-white/20 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-white backdrop-blur-sm">
						<span className="h-1.5 w-1.5 animate-pulse rounded-full bg-white" />
						Active
					</span>
				)}

				{/* Shared badges */}
				{isSharedByOther && (
					<span className="absolute right-3 top-3 flex items-center gap-1 rounded-full bg-white/20 px-2 py-0.5 text-[10px] font-medium text-white backdrop-blur-sm">
						<Share2 className="h-3 w-3" />
						Shared by {graph.owner_name || "Unknown"}
					</span>
				)}
				{isSharedWithOthers && !isSharedByOther && (
					<span className="absolute right-3 top-3 flex items-center gap-1 rounded-full bg-white/20 px-2 py-0.5 text-[10px] font-medium text-white backdrop-blur-sm">
						<Share2 className="h-3 w-3" />
						Shared
					</span>
				)}
			</div>

			{/* ── Card footer ── */}
			<div className="flex min-w-0 flex-col gap-0.5 px-4 py-3">
				<p className="truncate text-sm font-semibold text-gray-900" title={graph.name}>
					{graph.name}
				</p>
				{graph.description && (
					<p className="line-clamp-1 text-xs text-gray-500">{graph.description}</p>
				)}
				<p className="mt-0.5 text-[11px] text-gray-400">Edited {updatedAt}</p>
			</div>
		</div>
	);
}

// ── New workflow placeholder card ────────────────────────────────────────────

function NewWorkflowCard({ onClick }: { onClick: () => void }) {
	return (
		<button
			type="button"
			onClick={onClick}
			className="group flex flex-col overflow-hidden rounded-2xl border-2 border-dashed border-gray-200 bg-white transition-all duration-200 hover:border-[#ff6b00]/50 hover:shadow-[0_8px_32px_rgba(255,107,0,0.1)] hover:-translate-y-0.5"
		>
			<div className="flex flex-1 flex-col items-center justify-center gap-3 p-8" style={{ minHeight: 152 }}>
				<span className="flex h-12 w-12 items-center justify-center rounded-2xl border-2 border-dashed border-gray-300 text-gray-400 transition-colors group-hover:border-[#ff6b00]/50 group-hover:text-slate-900">
					<Plus className="h-6 w-6" />
				</span>
				<span className="text-sm font-medium text-gray-500 group-hover:text-slate-900">
					New workflow
				</span>
			</div>
		</button>
	);
}

// ── Loading skeleton ──────────────────────────────────────────────────────────

function SkeletonCard() {
	return (
		<div className="flex flex-col overflow-hidden rounded-2xl border border-gray-100 bg-white">
			<div className="animate-pulse bg-gray-100" style={{ height: 152 }} />
			<div className="flex flex-col gap-2 px-4 py-3">
				<div className="h-3.5 w-3/4 animate-pulse rounded-full bg-gray-200" />
				<div className="h-3 w-1/2 animate-pulse rounded-full bg-gray-100" />
			</div>
		</div>
	);
}

// ── Main page ────────────────────────────────────────────────────────────────

export default function ManagePage() {
	const router = useRouter();
	const { deleteGraph, currentGraph } = useGraph();
	const { showOverlay, hideOverlay } = useLoadingOverlay();
	const { showSuccess, showError } = useToast();
	const importRef = useRef<HTMLInputElement>(null);

	const [graphs, setGraphs] = useState<Graph[]>([]);
	const [loading, setLoading] = useState(true);
	const [searchQuery, setSearchQuery] = useState("");
	const [sortOption, setSortOption] = useState<"created" | "updated" | "alphabetical">("updated");
	const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");

	const [deletingGraph, setDeletingGraph] = useState<string | null>(null);
	const [deleteConfirmation, setDeleteConfirmation] = useState<{ isOpen: boolean; graphName: string | null }>({
		isOpen: false,
		graphName: null,
	});
	const [editModal, setEditModal] = useState<{ isOpen: boolean; graphName: string; graphDescription: string }>({
		isOpen: false,
		graphName: "",
		graphDescription: "",
	});
	const [editSaving, setEditSaving] = useState(false);
	const [showCreateDialog, setShowCreateDialog] = useState(false);

	const loadGraphList = async () => {
		try {
			setLoading(true);
			const response = await api.listGraphs();
			if (response.success) setGraphs(response.graphs);
		} catch {
			// silent
		} finally {
			setLoading(false);
		}
	};

	useEffect(() => {
		loadGraphList();
	}, []);

	// ── Filtering & sorting ──────────────────────────────────────────────────

	const displayedGraphs = (() => {
		const q = searchQuery.trim().toLowerCase();
		const filtered = q
			? graphs.filter((g) => g.name?.toLowerCase().includes(q) || g.description?.toLowerCase().includes(q))
			: graphs;

		const dir = sortDirection === "asc" ? 1 : -1;
		return [...filtered].sort((a, b) => {
			if (currentGraph?.name === a.name) return -1;
			if (currentGraph?.name === b.name) return 1;
			switch (sortOption) {
				case "created":
					return dir * (new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
				case "updated":
					return dir * (new Date(a.updated_at || 0).getTime() - new Date(b.updated_at || 0).getTime());
				case "alphabetical":
					return dir * a.name.localeCompare(b.name);
				default:
					return 0;
			}
		});
	})();

	// ── Handlers ────────────────────────────────────────────────────────────

	const handleLoad = async (graph: Graph) => {
		const id = graph.workflow_id || encodeURIComponent(graph.name);
		showOverlay({ message: `Loading ${graph.name}…`, minDurationMs: 500 });
		router.push(`/workflow/${id}`);
		hideOverlay();
	};

	const handleExport = async (graphName: string) => {
		try {
			const response = await api.exportGraph(graphName, "full");
			const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: "application/json" });
			const url = URL.createObjectURL(blob);
			const a = document.createElement("a");
			a.href = url;
			a.download = `${graphName}.json`;
			a.click();
			URL.revokeObjectURL(url);
		} catch (err) {
			showError("Export failed", (err as Error).message);
		}
	};

	const handleEditSave = async (newName: string, newDescription: string) => {
		const originalName = editModal.graphName;
		if (!originalName) return;
		try {
			setEditSaving(true);
			if (newName !== originalName) await api.updateWorkflowName(originalName, newName);
			if (newDescription !== editModal.graphDescription)
				await api.updateWorkflowDescription(newName !== originalName ? newName : originalName, newDescription);
			setGraphs((prev) => prev.map((g) => g.name === originalName ? { ...g, name: newName, description: newDescription } : g));
			setEditModal({ isOpen: false, graphName: "", graphDescription: "" });
			showSuccess("Workflow updated", `"${newName}" saved successfully`);
		} catch (err) {
			showError("Update failed", (err as Error).message);
		} finally {
			setEditSaving(false);
		}
	};

	const handleDeleteGraph = (graphName: string) => {
		setDeleteConfirmation({ isOpen: true, graphName });
	};

	const confirmDelete = async () => {
		const graphName = deleteConfirmation.graphName;
		if (!graphName) return;
		const isDeletingCurrent = currentGraph?.name === graphName;
		try {
			setDeletingGraph(graphName);
			setDeleteConfirmation({ isOpen: false, graphName: null });
			await new Promise((r) => setTimeout(r, 200));
			await deleteGraph(graphName);
			setGraphs((prev) => prev.filter((g) => g.name !== graphName));
			showSuccess("Workflow deleted", `"${graphName}" removed`);
			setTimeout(() => setDeletingGraph(null), 300);
			if (isDeletingCurrent) router.push("/");
		} catch (err) {
			showError("Delete failed", (err as Error).message);
			setDeletingGraph(null);
			loadGraphList();
		}
	};

	const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
		const file = e.target.files?.[0];
		if (!file) return;
		try {
			showOverlay({ message: "Importing workflow…", minDurationMs: 1000 });
			const text = await file.text();
			const data = JSON.parse(text);
			if (!data.name || !Array.isArray(data.nodes)) throw new Error("Invalid workflow file");
			let workflowName = data.name;
			const existingNames = graphs.map((g) => g.name);
			if (existingNames.includes(workflowName)) {
				let i = 1;
				while (existingNames.includes(`${workflowName} (${i})`)) i++;
				workflowName = `${workflowName} (${i})`;
			}
			const response = await api.importRawWorkflow({ name: workflowName, description: data.description || "Imported workflow", workflow_json: data });
			if (!response.success || !response.workflow_id) throw new Error("Import failed");
			showSuccess("Workflow imported", `"${workflowName}" imported successfully`);
			sessionStorage.setItem("newWorkflowCreation", "true");
			router.push(`/workflow/${response.workflow_id}`);
			hideOverlay();
		} catch (err) {
			showError("Import failed", (err as Error).message);
			hideOverlay();
		} finally {
			if (importRef.current) importRef.current.value = "";
		}
	};

	// ── Render ───────────────────────────────────────────────────────────────

	return (
		<AppShell>
			<div className="flex h-full flex-col overflow-y-auto bg-white">

				{/* ── Sticky page header ── */}
				<header className="sticky top-0 z-30 border-b border-gray-200 bg-white/95 backdrop-blur-sm">
					<div className="mx-auto max-w-screen-2xl px-4 sm:px-6 lg:px-8 py-4 sm:py-6">
						{/* Top row */}
						<div className="flex items-center justify-between gap-4">
							<div>
								<h1 className="text-xl font-bold text-gray-900">My Workflows</h1>
								<p className="mt-0.5 text-sm text-gray-500">
									{loading ? "Loading…" : `${graphs.length} workflow${graphs.length !== 1 ? "s" : ""}`}
								</p>
							</div>
						</div>

						{/* Controls row */}
						<div className="mt-3 flex flex-wrap items-center gap-3">
							{/* Search */}
							<div className="relative flex-1 min-w-[180px] max-w-xs">
								<Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400 pointer-events-none" />
								<input
									type="text"
									placeholder="Search workflows…"
									value={searchQuery}
									onChange={(e) => setSearchQuery(e.target.value)}
									className="w-full rounded-xl border border-gray-200 bg-white py-2 pl-9 pr-3 text-sm text-gray-900 placeholder:text-gray-400 focus:border-[#ff6b00] focus:outline-none focus:ring-2 focus:ring-[#ff6b00]/20"
								/>
							</div>

							{/* Sort select */}
							<Dropdown
								value={sortOption}
								onChange={(v) => setSortOption(v as typeof sortOption)}
								options={[
									{ value: "updated", label: "Last edited" },
									{ value: "created", label: "Date created" },
									{ value: "alphabetical", label: "Name" },
								]}
								menuAppearance="light"
								width="trigger"
								className="w-[150px]"
								triggerClassName="!rounded-xl !py-2"
							/>
							{/* Sort direction */}
							<button
								type="button"
								onClick={() => setSortDirection((d) => (d === "asc" ? "desc" : "asc"))}
								title={sortDirection === "asc" ? "Ascending" : "Descending"}
								className="flex h-9 w-9 items-center justify-center rounded-xl border border-gray-200 bg-white text-gray-600 transition-colors hover:border-gray-300 hover:bg-gray-50"
							>
								<ArrowUpDown className={`h-4 w-4 transition-transform duration-200 ${sortDirection === "asc" ? "" : "rotate-180"}`} />
							</button>
						</div>
					</div>
				</header>

				{/* ── Card grid ── */}
					<main className="mx-auto w-full max-w-screen-2xl flex-1 px-4 sm:px-6 lg:px-8 py-4 sm:py-6">
					{loading ? (
						<div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
							{Array.from({ length: 8 }).map((_, i) => <SkeletonCard key={i} />)}
						</div>
					) : graphs.length === 0 ? (
						<div className="flex flex-col items-center justify-center rounded-3xl border border-dashed border-gray-200 bg-white py-24">
							<div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-orange-50 border border-orange-100 mb-4">
								<FolderOpen className="h-8 w-8 text-orange-500" />
							</div>
							<h3 className="text-lg font-semibold text-gray-900 mb-2">No workflows yet</h3>
							<p className="text-sm text-gray-500 mb-6 max-w-xs text-center">
								Create your first workflow to start building AI-powered automation
							</p>
							<button
								type="button"
								onClick={() => setShowCreateDialog(true)}
								className="flex items-center gap-2 rounded-xl bg-[#ff6b00] px-5 py-2.5 text-sm font-semibold text-white shadow-[0_4px_14px_rgba(255,107,0,0.35)] transition-all hover:bg-[#e55f00]"
							>
								<Plus className="h-4 w-4" />
								Create your first workflow
							</button>
						</div>
					) : (
						<>
							{/* Search empty state */}
							{displayedGraphs.length === 0 && searchQuery && (
								<div className="flex flex-col items-center justify-center rounded-3xl border border-dashed border-gray-200 bg-white py-16">
									<Search className="h-10 w-10 text-gray-300 mb-3" />
									<p className="text-sm font-medium text-gray-600">No workflows match &ldquo;{searchQuery}&rdquo;</p>
								</div>
							)}

							{displayedGraphs.length > 0 && (
								<div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
									{/* New workflow card first */}
									<NewWorkflowCard onClick={() => setShowCreateDialog(true)} />

									{displayedGraphs.map((graph, i) => (
										<WorkflowCard
											key={graph.workflow_id || graph.name}
											graph={graph}
											index={i}
											isActive={currentGraph?.name === graph.name}
											isDeleting={deletingGraph === graph.name}
											onLoad={() => handleLoad(graph)}
											onEdit={() => setEditModal({ isOpen: true, graphName: graph.name, graphDescription: graph.description || "" })}
											onDelete={() => handleDeleteGraph(graph.name)}
											onExport={() => handleExport(graph.name)}
										/>
									))}
								</div>
							)}
						</>
					)}
				</main>
			</div>

			{/* ── Modals ── */}
			<Suspense fallback={null}>
				{showCreateDialog && (
					<GraphManagementDialog
						isOpen={showCreateDialog}
						onClose={() => { setShowCreateDialog(false); loadGraphList(); }}
						initialTab="create"
						mode="modal"
					/>
				)}
			</Suspense>

			<EditWorkflowModal
				isOpen={editModal.isOpen}
				workflowName={editModal.graphName}
				workflowDescription={editModal.graphDescription}
				saving={editSaving}
				onSave={handleEditSave}
				onCancel={() => { if (!editSaving) setEditModal({ isOpen: false, graphName: "", graphDescription: "" }); }}
			/>

			<DeleteWorkflowModal
				isOpen={deleteConfirmation.isOpen}
				workflowName={deleteConfirmation.graphName}
				onConfirm={confirmDelete}
				onCancel={() => setDeleteConfirmation({ isOpen: false, graphName: null })}
			/>
		</AppShell>
	);
}
