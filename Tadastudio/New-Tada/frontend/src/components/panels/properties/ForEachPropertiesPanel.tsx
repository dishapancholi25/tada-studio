import {
	AlertCircle,
	Info,
	Repeat,
	Save,
	Trash2,
	X,
	Zap,
} from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { Edge, Node } from "reactflow";
import FormInput from "@/components/ui/FormInput";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import type { ForEachConfig } from "@/types/nodes";

interface ForEachPropertiesPanelProps {
	node: Node;
	nodes?: Node[];
	edges?: Edge[];
	onUpdateNode: (nodeId: string, data: any) => void;
	onDeleteNode: (nodeId: string) => void;
	onClose: () => void;
}

/**
 * Default server ceiling on For Each items (FOR_EACH_MAX_ITEMS).
 * Used for guidance only — the server applies the authoritative limit, which
 * an administrator may raise or lower, so this does not hard-block input.
 */
const DEFAULT_SYSTEM_MAX_ITEMS = 5000;

const SOURCE_MODE_OPTIONS: Array<{
	value: NonNullable<ForEachConfig["source_mode"]>;
	label: string;
	badge?: string;
	description: string;
}> = [
	{
		value: "previous",
		label: "Previous Node",
		badge: "Recommended",
		description:
			"Auto-detect the node directly connected before this For Each node. Rewiring the graph (e.g. swapping in a Database Query node) updates the source automatically.",
	},
	{
		value: "specific",
		label: "Specific Node",
		description: "Choose a fixed node from the workflow as the source.",
	},
	{
		value: "start",
		label: "Workflow Input",
		description: "Use the initial data that triggered this workflow.",
	},
];

const inputBase =
	"rounded-[4px] border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 transition-colors focus:border-orange-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40";

export default function ForEachPropertiesPanel({
	node,
	nodes = [],
	edges = [],
	onUpdateNode,
	onDeleteNode,
	onClose,
}: ForEachPropertiesPanelProps) {
	const [config, setConfig] = useState<ForEachConfig>(
		node.data.for_each_config || {
			source_mode: "specific",
			source_node_id: "",
			field_path: "fields.rows",
			concurrency_limit: 5,
			rate_limit_per_second: null,
			item_limit: null,
			max_iterations: 1000,
			error_strategy: "continue_on_error",
			max_retries_per_item: 0,
		},
	);
	const [isDirty, setIsDirty] = useState(false);

	// Exclude this ForEach node itself from the selectable source list
	const availableSourceNodes = useMemo(
		() => nodes.filter((n) => n.id !== node.id),
		[nodes, node.id],
	);

	const sourceMode = config.source_mode || "specific";

	// The node directly wired into this For Each node via a workflow
	// connection (ignoring tool/delegation edges), used for "Previous Node"
	// mode. Mirrors the Agent Node Input "previous" resolution in
	// InputSourceSelector.tsx / backend PreviousInputSource.
	const previousNode = useMemo(() => {
		const incoming = edges.filter(
			(e) =>
				e.target === node.id &&
				e.data?.connection_type !== "tool" &&
				e.data?.connection_type !== "delegation",
		);
		if (incoming.length === 0) return null;
		const sourceId = incoming[incoming.length - 1].source;
		return nodes.find((n) => n.id === sourceId) || null;
	}, [edges, nodes, node.id]);

	const startNode = useMemo(
		() => nodes.find((n) => n.data?.type === "START" || n.type === "START"),
		[nodes],
	);

	// The node whose output the Field Path dropdown/resolution should use,
	// based on the currently selected source_mode - not always
	// config.source_node_id.
	const effectiveSourceNode = useMemo(() => {
		if (sourceMode === "previous") return previousNode;
		if (sourceMode === "start") return startNode || null;
		return (
			availableSourceNodes.find((n) => n.id === config.source_node_id) ||
			null
		);
	}, [sourceMode, previousNode, startNode, availableSourceNodes, config.source_node_id]);

	// Field-path options derived from the selected source node.
	// If the source is an Agent with a structured output schema, list all
	// array-typed fields so users can pick a real field name (e.g.
	// `fields.results`) instead of a hardcoded guess (`fields.items`).
	// Non-agent sources fall back to the generic presets.
	const fieldPathOptions = useMemo(() => {
		const generic = [
			{ value: "fields.rows", label: "CSV Rows (fields.rows)" },
			{ value: "fields.items", label: "JSON Items (fields.items)" },
			{ value: "structured.data", label: "Structured Data (structured.data)" },
		];

		if (!effectiveSourceNode) return generic;

		const schemaFields: Array<{
			name: string;
			type?: string;
			description?: string;
		}> =
			effectiveSourceNode?.data?.agent_config?.structured_outputs?.[0]
				?.fields || [];

		const listFields = schemaFields.filter((f) =>
			typeof f.type === "string" && f.type.startsWith("List["),
		);

		if (listFields.length === 0) return generic;

		return listFields.map((f) => ({
			value: `fields.${f.name}`,
			label: `${f.name} (${f.type})`,
		}));
	}, [effectiveSourceNode]);

	const presetValues = useMemo(
		() => fieldPathOptions.map((o) => o.value),
		[fieldPathOptions],
	);

	useEffect(() => {
		if (node.data.for_each_config) {
			setConfig(node.data.for_each_config);
		}
	}, [node.data.for_each_config]);

	const handleSave = () => {
		onUpdateNode(node.id, {
			...node.data,
			for_each_config: config,
		});
		setIsDirty(false);
		onClose();
	};

	const handleConfigChange = (field: keyof ForEachConfig, value: any) => {
		setConfig((prev) => ({
			...prev,
			[field]: value,
		}));
		setIsDirty(true);
	};

	const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

	const handleDelete = () => {
		setShowDeleteConfirm(true);
	};

	const handleConfirmDelete = () => {
		onDeleteNode(node.id);
		onClose();
	};

	const handleBackdropClick = useCallback(() => {
		onClose();
	}, [onClose]);

	const handleStopPropagation = useCallback((e: React.MouseEvent) => {
		e.stopPropagation();
	}, []);

	return (
		<div
			className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 backdrop-blur-sm"
			onClick={handleBackdropClick}
		>
			<div
				className="mx-4 flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-[4px] border border-gray-200 bg-white shadow-[0_24px_80px_rgba(15,23,42,0.12)]"
				onClick={handleStopPropagation}
			>
				<div className="flex items-center justify-between border-b border-gray-200 bg-white px-6 py-5">
					<div className="flex items-start gap-3">
						<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[4px] border border-gray-200 bg-white shadow-sm">
							<Repeat className="h-5 w-5 text-orange-600" />
						</div>
						<div>
							<p className="text-xs font-semibold capitalize tracking-wide text-gray-900">
								Tool configuration
							</p>
							<h2 className="text-lg font-semibold text-gray-900">
								For Each Configuration
							</h2>
							<p className="text-sm text-gray-600">
								Iterate over an array and process each item
							</p>
						</div>
					</div>
					<button
						type="button"
						onClick={onClose}
						className="rounded-[4px] border border-gray-200 bg-white p-2 text-gray-600 transition-colors hover:border-orange-300 hover:bg-slate-50 hover:text-slate-900"
					>
						<X className="h-5 w-5" />
					</button>
				</div>

				<div className="flex-1 space-y-6 overflow-y-auto bg-slate-50 p-6">
					<div className="rounded-[4px] border border-gray-200 bg-white p-5 shadow-sm">
						<h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-gray-900">
							<Repeat className="h-4 w-4 text-orange-600" />
							Source Configuration
						</h3>

						<div className="space-y-1.5">
							<label className="block text-sm font-medium text-gray-800">
								Where should this array come from?
							</label>
							<div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
								{SOURCE_MODE_OPTIONS.map((opt) => {
									const isActive = sourceMode === opt.value;
									return (
										<button
											key={opt.value}
											type="button"
											onClick={() =>
												handleConfigChange("source_mode", opt.value)
											}
											className={`rounded-[4px] border p-3 text-left transition-colors ${
												isActive
													? "border-orange-400 bg-orange-50"
													: "border-gray-200 bg-white hover:border-orange-300 hover:bg-slate-50"
											}`}
										>
											<div className="flex items-center gap-2">
												<span className="text-sm font-semibold text-gray-900">
													{opt.label}
												</span>
												{opt.badge && (
													<span className="rounded-[4px] bg-orange-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-orange-700">
														{opt.badge}
													</span>
												)}
											</div>
											<p className="mt-1 text-xs text-gray-600">
												{opt.description}
											</p>
										</button>
									);
								})}
							</div>
						</div>

						{sourceMode === "previous" && (
							<div className="mt-4 rounded-[4px] border border-gray-200 bg-slate-50 p-3 text-sm">
								{previousNode ? (
									<p className="text-gray-800">
										This For Each node will receive output from{" "}
										<span className="font-semibold">
											{previousNode.data?.name || previousNode.id}
										</span>
										. Reconnecting a different node before this one (e.g. a
										Database Query action node) will update the source
										automatically - no reconfiguration needed.
									</p>
								) : (
									<p className="text-amber-700">
										No node is currently connected directly before this For
										Each node. Connect one to use it as the source.
									</p>
								)}
							</div>
						)}

						{sourceMode === "start" && (
							<div className="mt-4 rounded-[4px] border border-gray-200 bg-slate-50 p-3 text-sm text-gray-800">
								This For Each node will iterate over the workflow&apos;s
								initial input{startNode ? ` ("${startNode.data?.name || startNode.id}")` : ""}.
							</div>
						)}

						{sourceMode === "specific" && (
							<div className="mt-4 space-y-1.5">
								<label className="block text-sm font-medium text-gray-800">
									Source Node
								</label>
								<select
									value={config.source_node_id || ""}
									onChange={(e) =>
										handleConfigChange("source_node_id", e.target.value)
									}
									className={`${inputBase} w-full`}
								>
									<option value="">Select a source node...</option>
									{availableSourceNodes.map((n) => (
										<option key={n.id} value={n.id}>
											{n.data?.name || n.id}
										</option>
									))}
									{config.source_node_id &&
										!availableSourceNodes.some(
											(n) => n.id === config.source_node_id,
										) && (
											<option value={config.source_node_id}>
												{config.source_node_id} (not found)
											</option>
										)}
								</select>
								<p className="text-xs text-gray-600">
									The node whose output contains the array to iterate over
								</p>
							</div>
						)}

						<div className="mt-4 space-y-1.5">
							<label className="block text-sm font-medium text-gray-800">
								Field Path
							</label>
							<div className="space-y-2">
								<select
									value={
										presetValues.includes(config.field_path || "")
											? config.field_path
											: "custom"
									}
									onChange={(e) => {
										if (e.target.value !== "custom") {
											handleConfigChange("field_path", e.target.value);
										}
									}}
									className={`${inputBase} w-full`}
								>
									{fieldPathOptions.map((opt) => (
										<option key={opt.value} value={opt.value}>
											{opt.label}
										</option>
									))}
									<option value="custom">Custom...</option>
								</select>
								<input
									type="text"
									value={config.field_path || ""}
									onChange={(e) =>
										handleConfigChange("field_path", e.target.value)
									}
									placeholder="e.g., fields.results"
									className={`${inputBase} w-full break-words`}
								/>
							</div>
							<p className="text-xs text-gray-600">
								Dot-path to the array in the source node&apos;s output. When
								the source is an Agent with a structured output schema, the
								dropdown lists its array-typed fields.
							</p>
						</div>
					</div>

					<div className="rounded-[4px] border border-gray-200 bg-white p-5 shadow-sm">
						<h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-gray-900">
							<Zap className="h-4 w-4 text-orange-600" />
							Execution Settings
						</h3>

						<div className="space-y-1.5">
							<label className="block text-sm font-medium text-gray-800">
								Concurrency Limit: {config.concurrency_limit || 5}
							</label>
							<input
								type="range"
								min={1}
								max={20}
								step={1}
								value={config.concurrency_limit || 5}
								onChange={(e) =>
									handleConfigChange(
										"concurrency_limit",
										parseInt(e.target.value),
									)
								}
								className="w-full accent-orange-600"
							/>
							<div className="flex justify-between text-xs text-gray-600">
								<span>1 (sequential)</span>
								<span>20 (parallel)</span>
							</div>
						</div>

						<div className="mt-4">
							<FormInput
								label="Rate Limit (requests/second)"
								type="number"
								value={
									config.rate_limit_per_second != null
										? String(config.rate_limit_per_second)
										: ""
								}
								onChange={(e) =>
									handleConfigChange(
										"rate_limit_per_second",
										e.target.value ? parseFloat(e.target.value) : null,
									)
								}
								placeholder="No limit"
								hint="Optional rate limit for iterations per second"
							/>
						</div>

						<div className="mt-4">
							<FormInput
								label="Process First N Items"
								type="number"
								min={1}
								value={
									config.item_limit != null ? String(config.item_limit) : ""
								}
								onChange={(e) =>
									handleConfigChange(
										"item_limit",
										e.target.value ? parseInt(e.target.value) : null,
									)
								}
								placeholder="All items"
								hint="Run the loop over only the first N items and skip the rest — useful for testing against a few rows. Leave empty to process everything."
							/>
							{config.item_limit != null && config.item_limit > 0 && (
								<p className="mt-1.5 text-xs text-amber-600">
									Partial run: only the first {config.item_limit} item
									{config.item_limit === 1 ? "" : "s"} will be processed.
									Remaining items are skipped and reported in the node output.
								</p>
							)}
						</div>

						<div className="mt-4">
							<FormInput
								label="Max Iterations"
								type="number"
								min={1}
								value={String(config.max_iterations || 1000)}
								onChange={(e) =>
									handleConfigChange(
										"max_iterations",
										parseInt(e.target.value) || 1000,
									)
								}
								hint={`Safety cap: the node fails if the source has more items than this — it never processes part of them. To run over a subset on purpose, use "Process First N Items" above. A system limit (default ${DEFAULT_SYSTEM_MAX_ITEMS.toLocaleString()}) also applies.`}
							/>
							{(config.max_iterations || 1000) > DEFAULT_SYSTEM_MAX_ITEMS && (
								<p className="mt-1.5 text-xs text-amber-600">
									Above the default system limit of{" "}
									{DEFAULT_SYSTEM_MAX_ITEMS.toLocaleString()} — runs will be
									capped at whatever the server allows, and a source array
									larger than that cap fails the node instead of processing
									part of it.
								</p>
							)}
						</div>
					</div>

					<div className="rounded-[4px] border border-gray-200 bg-white p-5 shadow-sm">
						<h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-gray-900">
							<Info className="h-4 w-4 text-orange-600" />
							Data Residency &amp; Limits
						</h3>

						<div className="space-y-1.5">
							<FormInput
								label="Allowed Fields"
								type="text"
								value={(config.allowed_fields || []).join(", ")}
								onChange={(e) => {
									const parsed = e.target.value
										.split(",")
										.map((s) => s.trim())
										.filter((s) => s.length > 0);
									handleConfigChange(
										"allowed_fields",
										parsed.length > 0 ? parsed : null,
									);
								}}
								placeholder="All fields (leave empty)"
								hint="Comma-separated column allow-list. When set, only these keys of each row are sent to body nodes/LLM. Leave empty to expose all fields."
							/>
						</div>

						<div className="mt-4">
							<FormInput
								label="Max Item Size (bytes)"
								type="number"
								value={
									config.max_item_bytes != null
										? String(config.max_item_bytes)
										: ""
								}
								onChange={(e) =>
									handleConfigChange(
										"max_item_bytes",
										e.target.value ? parseInt(e.target.value) || null : null,
									)
								}
								placeholder="No limit"
								hint="Optional cap on each item's serialized size. Oversized rows are truncated before reaching the LLM to protect the context window."
							/>
						</div>
					</div>

					<div className="rounded-[4px] border border-gray-200 bg-white p-5 shadow-sm">
						<h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-gray-900">
							<AlertCircle className="h-4 w-4 text-red-600" />
							Error Handling
						</h3>

						<div className="space-y-1.5">
							<label className="block text-sm font-medium text-gray-800">
								On Error
							</label>
							<select
								value={config.error_strategy || "continue_on_error"}
								onChange={(e) =>
									handleConfigChange("error_strategy", e.target.value)
								}
								className={`${inputBase} w-full`}
							>
								<option value="continue_on_error">
									Continue with other items
								</option>
								<option value="fail_fast">Stop immediately</option>
							</select>
						</div>

						<div className="mt-4">
							<FormInput
								label="Max Retries per Item"
								type="number"
								value={String(config.max_retries_per_item || 0)}
								onChange={(e) =>
									handleConfigChange(
										"max_retries_per_item",
										parseInt(e.target.value) || 0,
									)
								}
								hint="Number of retry attempts for each failed iteration"
							/>
						</div>
					</div>

					<div className="flex items-start gap-3 rounded-[4px] border border-orange-400 bg-white p-4 shadow-sm">
						<Info className="mt-0.5 h-4 w-4 flex-shrink-0 text-orange-600" />
						<div className="text-xs text-gray-800">
							<p className="mb-1 font-medium text-gray-900">How For Each works:</p>
							<p>
								Connect nodes after this For Each node to define the loop body.
								Each iteration receives the current item via the{" "}
								<code className="rounded-[4px] border border-gray-200 bg-slate-50 px-1 font-mono text-gray-900">
									__for_each_current
								</code>{" "}
								virtual node output.
							</p>
						</div>
					</div>
				</div>

				<div className="flex items-center justify-between border-t border-gray-200 bg-white p-4">
					<button
						type="button"
						onClick={handleDelete}
						className="flex items-center gap-2 rounded-[4px] border border-gray-200 bg-white px-3 py-2 text-sm text-red-700 transition-colors hover:border-red-300 hover:bg-red-50 hover:text-red-800"
					>
						<Trash2 className="h-4 w-4" />
						Delete Node
					</button>

					<div className="flex items-center gap-3">
						<button
							type="button"
							onClick={onClose}
							className="rounded-[4px] border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900"
						>
							Cancel
						</button>
						<button
							type="button"
							onClick={handleSave}
							disabled={!isDirty}
							className="inline-flex items-center gap-2 rounded-[4px] bg-orange-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-orange-700 disabled:cursor-not-allowed disabled:opacity-40"
						>
							<Save className="h-4 w-4" />
							Save
						</button>
					</div>
				</div>
			</div>

			{/* Delete Confirmation Dialog */}
			<ConfirmDialog
				isOpen={showDeleteConfirm}
				onClose={() => setShowDeleteConfirm(false)}
				onConfirm={handleConfirmDelete}
				title="Delete Node?"
				message={`Are you sure you want to delete "${node.data.name || "For Each"}"? This action cannot be undone.`}
				confirmText="Delete"
				cancelText="Cancel"
				variant="danger"
				surface="light"
			/>
		</div>
	);
}
