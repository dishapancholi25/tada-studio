import type { DefaultEdgeOptions } from "reactflow";

/** Builder canvas edge color (workflow + agent tool/delegation/sub-workflow links). */
export const builderEdgeStroke = "#4a4a4a";

export const defaultSmoothEdgeOptions: DefaultEdgeOptions = {
	animated: false,
	type: "smoothstep",
	style: {
		stroke: builderEdgeStroke,
		strokeWidth: 3,
	},
};

export const CONDITION_TAKEN_STYLE = {
	stroke: "#0DA931",
	strokeWidth: 3,
	opacity: 1,
} as const;

export const CONDITION_SKIPPED_STYLE = {
	stroke: "#6b7280",
	strokeWidth: 1,
	opacity: 0.3,
} as const;
