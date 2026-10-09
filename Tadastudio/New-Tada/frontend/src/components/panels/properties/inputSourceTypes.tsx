import clsx from "clsx";
import type { LucideIcon } from "lucide-react";
import {
	AlertCircle,
	Bot,
	CheckCircle,
	Code,
	Database,
	FileText,
	GitBranch,
	GitMerge,
	Globe,
	Layers,
	Mail,
	Play,
	Search,
	Sparkles,
	Zap,
} from "lucide-react";
import type { Node } from "reactflow";

export interface StructuredField {
	id: string;
	name: string;
	type: string;
	description?: string;
	required?: boolean;
}

export interface InputSourceConfig {
	source_mode: "previous" | "specific" | "start" | "custom";
	source_node_id?: string | null;
	source_node_ids?: string[];
	use_structured_field: boolean;
	selected_fields: string[];
	combine_fields_as_json: boolean;
	include_original_input: boolean;
	include_node_labels?: boolean;
	custom_template?: string | null;
}

export interface ModeOption {
	value: InputSourceConfig["source_mode"];
	title: string;
	description: string;
	Icon: LucideIcon;
	badge?: string;
	badgeVariant?: "recommended" | "advanced";
}

export const MODE_OPTIONS: ModeOption[] = [
	{
		value: "previous",
		title: "Previous Node",
		description: "Output from the node directly before this one.",
		Icon: GitBranch,
		badge: "Recommended",
		badgeVariant: "recommended",
	},
	{
		value: "specific",
		title: "Specific Node",
		description: "Choose which node(s) to pull data from.",
		Icon: GitMerge,
	},
	{
		value: "start",
		title: "Workflow Input",
		description: "The initial data that triggered this workflow.",
		Icon: FileText,
	},
	{
		value: "custom",
		title: "Custom Template",
		description: "Combine multiple sources with a custom format.",
		Icon: Code,
		badge: "Advanced",
		badgeVariant: "advanced",
	},
];

export const normalizeConfig = (
	incoming?: Partial<InputSourceConfig> | null,
): InputSourceConfig => {
	const mode = incoming?.source_mode ?? "previous";
	const rawIds = Array.isArray(incoming?.source_node_ids)
		? [...incoming.source_node_ids]
		: [];
	if (rawIds.length === 0 && incoming?.source_node_id) {
		rawIds.push(incoming.source_node_id);
	}

	const uniqueIds = Array.from(new Set(rawIds.filter(Boolean))) as string[];
	const selectedFields = Array.isArray(incoming?.selected_fields)
		? [...incoming.selected_fields]
		: [];

	const base: InputSourceConfig = {
		source_mode: mode,
		source_node_id:
			uniqueIds.length === 1
				? uniqueIds[0]
				: (incoming?.source_node_id ?? null),
		source_node_ids: uniqueIds,
		use_structured_field:
			incoming?.use_structured_field ?? selectedFields.length > 0,
		selected_fields: selectedFields,
		combine_fields_as_json: incoming?.combine_fields_as_json ?? true,
		include_original_input: incoming?.include_original_input ?? false,
		include_node_labels: incoming?.include_node_labels ?? true,
		custom_template: incoming?.custom_template ?? null,
	};

	return base;
};

export const configsEqual = (a: InputSourceConfig, b: InputSourceConfig) =>
	JSON.stringify(a) === JSON.stringify(b);

export const generateInputPreview = (
	config: InputSourceConfig,
	availableNodes: Node[],
): string => {
	if (config.source_mode === "previous") {
		return "This node will receive the output from the previous node in the workflow";
	}
	if (config.source_mode === "start") {
		return "This node will receive the original input that started the workflow (e.g., user's initial message)";
	}
	if (
		config.source_mode === "specific" &&
		config.source_node_ids &&
		config.source_node_ids.length > 0
	) {
		const sourceNodes = availableNodes.filter((n) =>
			config.source_node_ids!.includes(n.id),
		);

		if (sourceNodes.length === 0) return "Select source nodes to preview input";

		if (sourceNodes.length === 1) {
			const sourceNode = sourceNodes[0];
			if (config.use_structured_field && config.selected_fields.length > 0) {
				if (
					config.selected_fields.length === 1 &&
					!config.combine_fields_as_json
				) {
					const fieldName = config.selected_fields[0];
					return `Value of the "${fieldName}" field from ${sourceNode.data.name}`;
				}
				const exampleObj: Record<string, string> = {};
				for (const f of config.selected_fields) {
					exampleObj[f] = "...";
				}
				return `JSON object:\n${JSON.stringify(exampleObj, null, 2)}`;
			}
			return `Complete output from ${sourceNode.data.name} (full JSON if structured, raw text otherwise)`;
		}

		const orderedSourceNodes = config.source_node_ids
			.map((id) => availableNodes.find((n) => n.id === id))
			.filter((n): n is Node => !!n);

		const nodeNames = orderedSourceNodes.map((n) => n.data.name);
		if (config.include_node_labels) {
			return nodeNames
				.map((name) => `${name} Output:\n[output from ${name}]`)
				.join("\n\n---\n\n");
		}
		return nodeNames.map((name) => `[output from ${name}]`).join("\n\n");
	}
	if (config.source_mode === "custom") {
		if (!config.custom_template)
			return "Enter a custom template with variables...";
		let preview = config.custom_template;
		for (const n of availableNodes) {
			preview = preview.replace(`{${n.id}}`, `[output from ${n.data.name}]`);
		}
		preview = preview.replace("{original}", "[original workflow input]");
		preview = preview.replace("{previous}", "[previous node output]");
		return preview;
	}
	return "Default: output from previous node";
};

export const getNodeColorRgb = (nodeType: string): string => {
	switch (nodeType) {
		case "START":
			return "13, 169, 49";
		case "END":
			return "239, 68, 68";
		case "AGENT":
			return "168, 85, 247";
		case "CONDITION":
			return "249, 115, 22";
		case "CHECKPOINT":
			return "168, 85, 247";
		case "HTTP_REQUEST":
		case "HTTP_REQUEST_ACTION":
			return "249, 115, 22";
		case "DATABASE_QUERY":
		case "DATABASE_INSERT":
		case "DATABASE_QUERY_ACTION":
			return "59, 130, 246";
		case "EMAIL_SEND":
			return "16, 185, 129";
		case "WEB_SEARCH":
			return "245, 158, 11";
		case "DOCUMENT_SEARCH":
			return "59, 130, 246";
		case "FILE_READ":
		case "FILE_WRITE":
			return "245, 158, 11";
		case "SUBWORKFLOW":
			return "20, 184, 166";
		case "MCP_SERVER":
			return "6, 182, 212";
		default:
			return "var(--color-primary-rgb)";
	}
};

export const getNodeIcon = (nodeType: string) => {
	const baseClass =
		"flex h-7 w-7 items-center justify-center rounded-lg border";
	const iconClass = "h-3.5 w-3.5";

	switch (nodeType) {
		case "START":
			return (
				<div
					className={clsx(
						baseClass,
						"border-[#0DA931]/30 bg-[#0DA931]/10 text-[#0DA931]",
					)}
				>
					<Play className={iconClass} />
				</div>
			);
		case "END":
			return (
				<div
					className={clsx(
						baseClass,
						"border-red-400/30 bg-red-500/10 text-red-300",
					)}
				>
					<CheckCircle className={iconClass} />
				</div>
			);
		case "AGENT":
			return (
				<div
					className={clsx(
						baseClass,
						"border-purple-400/30 bg-purple-500/10 text-purple-600",
					)}
				>
					<Bot className={iconClass} />
				</div>
			);
		case "CONDITION":
			return (
				<div
					className={clsx(
						baseClass,
						"border-orange-400/30 bg-orange-500/10 text-orange-300",
					)}
				>
					<GitBranch className={iconClass} />
				</div>
			);
		case "CHECKPOINT":
			return (
				<div
					className={clsx(
						baseClass,
						"border-purple-400/30 bg-purple-500/10 text-purple-600",
					)}
				>
					<AlertCircle className={iconClass} />
				</div>
			);
		case "HTTP_REQUEST":
		case "HTTP_REQUEST_ACTION":
			return (
				<div
					className={clsx(
						baseClass,
						"border-orange-400/30 bg-orange-500/10 text-orange-300",
					)}
				>
					<Globe className={iconClass} />
				</div>
			);
		case "DATABASE_QUERY":
		case "DATABASE_INSERT":
		case "DATABASE_QUERY_ACTION":
			return (
				<div
					className={clsx(
						baseClass,
						"border-blue-400/30 bg-blue-500/10 text-blue-600",
					)}
				>
					<Database className={iconClass} />
				</div>
			);
		case "EMAIL_SEND":
			return (
				<div
					className={clsx(
						baseClass,
						"border-emerald-400/30 bg-emerald-500/10 text-emerald-600",
					)}
				>
					<Mail className={iconClass} />
				</div>
			);
		case "WEB_SEARCH":
			return (
				<div
					className={clsx(
						baseClass,
						"border-amber-400/30 bg-amber-500/10 text-amber-300",
					)}
				>
					<Search className={iconClass} />
				</div>
			);
		case "DOCUMENT_SEARCH":
			return (
				<div
					className={clsx(
						baseClass,
						"border-blue-400/30 bg-blue-500/10 text-blue-600",
					)}
				>
					<FileText className={iconClass} />
				</div>
			);
		case "FILE_READ":
		case "FILE_WRITE":
			return (
				<div
					className={clsx(
						baseClass,
						"border-amber-400/30 bg-amber-500/10 text-amber-300",
					)}
				>
					<FileText className={iconClass} />
				</div>
			);
		case "SUBWORKFLOW":
			return (
				<div
					className={clsx(
						baseClass,
						"border-teal-400/30 bg-teal-500/10 text-teal-600",
					)}
				>
					<Layers className={iconClass} />
				</div>
			);
		case "MCP_SERVER":
			return (
				<div
					className={clsx(
						baseClass,
						"border-cyan-400/30 bg-cyan-500/10 text-cyan-600",
					)}
				>
					<Zap className={iconClass} />
				</div>
			);
		default:
			return (
				<div
					className={clsx(
						baseClass,
						"border-[rgba(var(--color-primary-rgb),0.3)] bg-[rgba(var(--color-primary-rgb),0.1)] text-[color:var(--color-primary-light)]",
					)}
				>
					<Code className={iconClass} />
				</div>
			);
	}
};
