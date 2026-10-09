import type { ExecutionStatusType, GraphExecution } from "@/types/api";
import { processContentForRendering } from "@/lib/markdown-utils";

export interface NodeOutput {
	nodeName: string;
	response: string;
}

export interface ResultDrawerData {
	status: ExecutionStatusType;
	input: string | null;
	outputs: NodeOutput[];
	rawJson: string | null;
	errorMessage: string | null;
	endNodeName: string | null;
	metrics: {
		durationSeconds: number | null;
		totalTokens: number;
		estimatedCost: number | null;
		nodeCount: number;
	};
	dbExecutionId: string | null;
	timestamp: string | null;
}

export function extractResultDrawerData(
	execution: GraphExecution,
): ResultDrawerData {
	const nodeExecs = execution.node_executions ?? [];

	// Input: START node's output_data.raw
	const startNode = nodeExecs.find((ne) => ne.node_type === "START");
	const input = startNode?.output_data?.raw ?? null;

	// Output: last completed END node's output_data
	const endNodes = nodeExecs.filter(
		(ne) => ne.node_type === "END" && ne.status === "completed",
	);
	const endNode = endNodes.length > 0 ? endNodes[endNodes.length - 1] : null;

	const outputs: NodeOutput[] = [];
	if (endNode?.output_data) {
		const od = endNode.output_data;

		// 1. Full format: { nodes: [{ node, node_id, response, ... }] }
		if (od.nodes && Array.isArray(od.nodes)) {
			for (const n of od.nodes) {
				if (n.node === "Start" || !n.response) continue;
				const text =
					processContentForRendering(n.response) ?? n.response;
				outputs.push({ nodeName: n.node ?? "Unknown", response: text });
			}
		}

		// 2. Summary format: top-level array [{ node, response }]
		if (outputs.length === 0 && Array.isArray(od)) {
			for (const n of od) {
				if (n.node === "Start" || !n.response) continue;
				const text =
					processContentForRendering(n.response) ?? n.response;
				outputs.push({ nodeName: n.node ?? "Unknown", response: text });
			}
		}

		// 3. Direct raw/response fields or compact format
		if (
			outputs.length === 0 &&
			typeof od === "object" &&
			!Array.isArray(od) &&
			!od.nodes
		) {
			const raw = od.raw ?? od.response ?? null;
			if (raw) {
				const processed = processContentForRendering(raw);
				const text = processed ?? (typeof raw === "string" ? raw : null);
				if (text) {
					outputs.push({ nodeName: "Output", response: text });
				}
			}

			// Compact format: { "NodeName": "response text" }
			if (outputs.length === 0) {
				for (const [key, val] of Object.entries(od)) {
					if (key.startsWith("_") || typeof val !== "string") continue;
					const text = processContentForRendering(val) ?? val;
					outputs.push({ nodeName: key, response: text });
				}
			}
		}

		// 4. Final fallback: stringify
		if (outputs.length === 0 && od && typeof od === "object") {
			outputs.push({
				nodeName: "Output",
				response: JSON.stringify(od, null, 2),
			});
		}
	}

	// Error
	const errorMessage =
		execution.error_message ??
		nodeExecs.find((ne) => ne.status === "failed")?.error_message ??
		null;

	// Metrics
	const totalTokens = nodeExecs.reduce(
		(sum, ne) => sum + (ne.total_tokens ?? 0),
		0,
	);

	// Raw JSON: the full output_data as it would be returned via HTTP
	const rawJson = endNode?.output_data
		? JSON.stringify(endNode.output_data, null, 2)
		: null;

	return {
		status: execution.status,
		input,
		outputs,
		rawJson,
		errorMessage,
		endNodeName: endNode?.node_name ?? null,
		metrics: {
			durationSeconds: execution.duration_seconds ?? null,
			totalTokens,
			estimatedCost: (() => {
			const backendCost = nodeExecs.reduce(
				(sum, ne) => sum + (ne.total_cost ?? 0),
				0,
			);
			if (backendCost > 0) return backendCost;
			// Fallback to legacy estimate for older executions without backend costs
			return totalTokens > 0 ? totalTokens * 0.000014 : null;
		})(),
			nodeCount: nodeExecs.length,
		},
		dbExecutionId:
			((execution as unknown as Record<string, unknown>).db_execution_id as string) ??
			null,
		timestamp: execution.end_time ?? execution.created_at ?? null,
	};
}

export function formatDuration(seconds: number | null): string {
	if (seconds === null || seconds === undefined) return "\u2014";
	if (seconds < 1) return `${(seconds * 1000).toFixed(0)}ms`;
	if (seconds < 60) return `${seconds.toFixed(1)}s`;
	const mins = Math.floor(seconds / 60);
	const secs = seconds % 60;
	return `${mins}m ${secs.toFixed(0)}s`;
}

export function formatTokens(count: number): string {
	if (count === 0) return "\u2014";
	return count.toLocaleString();
}

export function formatCost(cost: number | null): string {
	if (cost === null) return "\u2014";
	if (cost < 0.01) return `$${cost.toFixed(4)}`;
	return `$${cost.toFixed(2)}`;
}
