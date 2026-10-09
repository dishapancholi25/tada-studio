import { X } from "lucide-react";
import type { Node } from "reactflow";
import { getNodeColorRgb } from "./inputSourceTypes";

interface MultiSourceChipsProps {
	selectedNodeIds: string[];
	availableNodes: Node[];
	onRemove: (nodeId: string) => void;
}

export default function MultiSourceChips({
	selectedNodeIds,
	availableNodes,
	onRemove,
}: MultiSourceChipsProps) {
	if (selectedNodeIds.length === 0) {
		return (
			<div className="rounded-lg border border-dashed border-[color:var(--color-border)]/40 bg-[color:var(--color-surface)]/20 px-3 py-2 text-xs text-[color:var(--color-text-muted)]">
				No nodes selected
			</div>
		);
	}

	const orderedNodes = selectedNodeIds
		.map((id) => availableNodes.find((n) => n.id === id))
		.filter((n): n is Node => !!n);

	return (
		<div className="flex flex-wrap gap-2">
			{orderedNodes.map((node) => {
				const colorRgb = getNodeColorRgb(node.data.type);
				return (
					<div
						key={node.id}
						className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium text-slate-900"
						style={{
							borderColor: `rgba(${colorRgb}, 0.3)`,
							backgroundColor: `rgba(${colorRgb}, 0.1)`,
						}}
					>
						<span>{node.data.name}</span>
						<button
							type="button"
							onClick={(e) => {
								e.stopPropagation();
								onRemove(node.id);
							}}
							className="flex h-3.5 w-3.5 items-center justify-center rounded-full text-slate-600 transition-colors hover:bg-slate-200/60 hover:text-slate-900"
						>
							<X className="h-2.5 w-2.5" />
						</button>
					</div>
				);
			})}
		</div>
	);
}
