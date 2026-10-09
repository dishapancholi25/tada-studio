import type { Node } from "reactflow";

export interface ConditionBranchDetails {
	branchIndex: number | null;
	label: string;
	branchLabel: string;
	branchColor: string;
}

export interface ConditionConfig {
	branch_mode?: string;
	branch_labels?: string[];
	branch_count?: number;
	branches?: Array<{
		label?: string;
		color?: string;
	}>;
}

const DEFAULT_TRUE_LABEL = "True";
const DEFAULT_FALSE_LABEL = "False";

function normalizeType(value?: string | null): string {
	return (value || "").toLowerCase();
}

function deriveBranchCount(config?: ConditionConfig): number {
	if (!config) return 2;
	const fromBranches = Array.isArray(config.branches)
		? config.branches.length
		: 0;
	const fromLabels = Array.isArray(config.branch_labels)
		? config.branch_labels.length
		: 0;

	if (fromBranches > 0) return fromBranches;
	if (fromLabels > 0) return fromLabels;
	if (typeof config.branch_count === "number")
		return Math.max(1, config.branch_count);
	if (config.branch_mode === "multi") return 3;
	return 2;
}

function deriveBranchLabels(
	config: ConditionConfig | undefined,
	branchCount: number,
): string[] {
	if (config) {
		if (Array.isArray(config.branches) && config.branches.length > 0) {
			return config.branches.map((branch, index) => {
				if (branch?.label) return branch.label;
				if (
					Array.isArray(config.branch_labels) &&
					config.branch_labels[index]
				) {
					return config.branch_labels[index]!;
				}
				return `Branch ${index + 1}`;
			});
		}

		if (
			Array.isArray(config.branch_labels) &&
			config.branch_labels.length > 0
		) {
			return [...config.branch_labels];
		}
	}

	if (config?.branch_mode === "multi") {
		return Array.from(
			{ length: branchCount },
			(_, index) => `Branch ${index + 1}`,
		);
	}

	if (branchCount > 1) {
		const labels = [DEFAULT_TRUE_LABEL, DEFAULT_FALSE_LABEL];
		while (labels.length < branchCount) {
			labels.push(`Branch ${labels.length + 1}`);
		}
		return labels;
	}

	return [DEFAULT_TRUE_LABEL];
}

function ensureLabel(labels: string[], index: number): string {
	if (labels[index]) return labels[index]!;

	if (index === 0) return DEFAULT_TRUE_LABEL;
	if (index === 1) return DEFAULT_FALSE_LABEL;
	return `Branch ${index + 1}`;
}

function getBranchColorFromLabel(
	label?: string,
	branchIndex: number | null = null,
): string {
	const normalized = (label || "").toLowerCase();

	if (
		normalized.includes("true") ||
		normalized.includes("success") ||
		normalized.includes("yes")
	) {
		return "#0DA931";
	}
	if (
		normalized.includes("false") ||
		normalized.includes("fail") ||
		normalized.includes("reject") ||
		normalized.includes("no")
	) {
		return "#ef4444";
	}
	if (normalized.includes("default") || normalized.includes("else")) {
		return "#6b7280";
	}
	if (
		normalized.includes("partial") ||
		normalized.includes("maybe") ||
		normalized.includes("pending")
	) {
		return "#f97316";
	}
	if (normalized.includes("review") || normalized.includes("wait")) {
		return "#695DA8";
	}
	if (normalized.includes("over") || normalized.includes("payment")) {
		return "#8b5cf6";
	}
	if (normalized.includes("full") || normalized.includes("match")) {
		return "#0DA931";
	}

	switch (branchIndex) {
		case 0:
			return "#0DA931";
		case 1:
			return "#ef4444";
		case 2:
			return "#f97316";
		case 3:
			return "#8b5cf6";
		default:
			return "#8b5cf6";
	}
}

function parseBranchIndexFromHandle(handle?: string | null): number | null {
	if (!handle) return null;
	if (handle.startsWith("branch-")) {
		const parsed = Number(handle.replace("branch-", ""));
		return Number.isNaN(parsed) ? null : parsed;
	}
	return null;
}

export function resolveConditionEdgeData(
	conditionConfig: ConditionConfig | undefined,
	sourceHandle?: string | null,
): ConditionBranchDetails | null {
	const branchMode = conditionConfig?.branch_mode || "binary";
	const branchCount = Math.max(1, deriveBranchCount(conditionConfig));
	const branchLabels = deriveBranchLabels(conditionConfig, branchCount);

	const normalizedHandle = normalizeType(sourceHandle);

	let branchIndex: number | null = null;
	let label: string | undefined;
	let colorFromConfig: string | undefined;

	if (branchMode === "multi" && Array.isArray(conditionConfig?.branches)) {
		const parsedIndex = parseBranchIndexFromHandle(sourceHandle);
		if (parsedIndex !== null && conditionConfig?.branches?.[parsedIndex]) {
			branchIndex = parsedIndex;
			const branch = conditionConfig.branches[parsedIndex];
			label = branch?.label || ensureLabel(branchLabels, parsedIndex);
			colorFromConfig = branch?.color;
		}
	}

	if (branchIndex === null) {
		if (normalizedHandle === "true") {
			branchIndex = 0;
			label = branchLabels[0] || DEFAULT_TRUE_LABEL;
		} else if (normalizedHandle === "false") {
			branchIndex = branchLabels.length > 1 ? 1 : 0;
			label =
				branchLabels[branchIndex] ||
				(branchIndex === 0 ? DEFAULT_TRUE_LABEL : DEFAULT_FALSE_LABEL);
		} else if (normalizedHandle === "default") {
			branchIndex = branchLabels.length - 1;
			label = branchLabels[branchIndex] || "Default";
		} else {
			const parsedIndex = parseBranchIndexFromHandle(sourceHandle);
			if (parsedIndex !== null) {
				branchIndex = parsedIndex;
				label = ensureLabel(branchLabels, parsedIndex);

				if (
					Array.isArray(conditionConfig?.branches) &&
					conditionConfig.branches[parsedIndex]
				) {
					colorFromConfig = conditionConfig.branches[parsedIndex]?.color;
				}
			}
		}
	}

	if (branchIndex === null && branchCount === 1) {
		branchIndex = 0;
		label = branchLabels[0] || DEFAULT_TRUE_LABEL;
	}

	if (label === undefined && branchIndex !== null) {
		label = ensureLabel(branchLabels, branchIndex);
	}

	if (label === undefined) {
		label = DEFAULT_TRUE_LABEL;
	}

	const branchColor =
		colorFromConfig || getBranchColorFromLabel(label, branchIndex);

	return {
		branchIndex,
		label,
		branchLabel: label,
		branchColor,
	};
}

export function isConditionNodeType(type?: string | null): boolean {
	const normalized = normalizeType(type);
	return normalized === "condition" || normalized === "conditionnode";
}

export function isConditionNode(
	node: Pick<Node, "type" | "data"> | Record<string, any> | undefined,
): boolean {
	if (!node) return false;
	if (isConditionNodeType((node as any)?.type)) return true;
	if (isConditionNodeType((node as any)?.data?.type)) return true;
	if (isConditionNodeType((node as any)?.node_type)) return true;
	return false;
}
