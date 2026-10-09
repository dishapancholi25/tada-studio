import { AlertCircle, Clock } from "lucide-react";
import React, { useState } from "react";
import JsonViewerEnhanced from "../../../../JsonViewerEnhanced";
import ExecutionTabs from "../../../../ui/ExecutionTabs";
import type {
	CombinedNodeExecution,
	ToolExecution,
} from "../types/execution.types";
import { formatDuration, formatTimestamp } from "../utils/formatters";

export interface BaseRendererProps<T extends ToolExecution = ToolExecution> {
	executions: T[];
	selectedIndex: number;
	onSelectIndex: (index: number) => void;
	nodeExecution: CombinedNodeExecution | null;
}

/**
 * Base renderer interface for tool renderers
 */
export interface IRenderer<T extends ToolExecution = ToolExecution> {
	getViewModes(): Array<{ key: string; label: string; icon?: React.ReactNode }>;
	renderViewMode(mode: string, execution: T): React.ReactNode;
	renderEmptyState?(): React.ReactNode;
	getDefaultViewMode?(): string;
}

/**
 * Base functional component for renderers
 */
export function BaseRendererComponent<T extends ToolExecution = ToolExecution>({
	renderer,
	executions,
	selectedIndex,
	onSelectIndex,
	nodeExecution,
}: BaseRendererProps<T> & { renderer: IRenderer<T> }) {
	const defaultMode = renderer.getDefaultViewMode
		? renderer.getDefaultViewMode()
		: renderer.getViewModes()[0]?.key || "raw";
	const [viewMode, setViewMode] = useState(defaultMode);

	const renderExecutionSelector = () => {
		if (executions.length <= 1) return null;

		// Check if we have multiple review iterations
		const uniqueIterations = new Set(
			executions.map((e) => e.review_iteration).filter((r) => r != null)
		);
		const hasMultipleIterations = uniqueIterations.size > 1;

		// Build execution number within each run (for multi-iteration display)
		const executionNumberInRun: number[] = [];
		if (hasMultipleIterations) {
			const countPerIteration: Record<number, number> = {};
			executions.forEach((exec) => {
				const iteration = exec.review_iteration ?? 0;
				countPerIteration[iteration] = (countPerIteration[iteration] ?? 0) + 1;
				executionNumberInRun.push(countPerIteration[iteration]);
			});
		}

		return (
			<div className="px-6 py-4 border-b border-slate-200">
				{/* Section Label */}
				<div className="text-[0.6rem] capitalize text-slate-500 font-semibold mb-3">
					Execution Instance
				</div>

				{/* Selector Pills */}
				<div className="flex gap-2 flex-wrap">
					{executions.map((exec, idx) => {
						// Build label based on whether we have multiple iterations
						let label: string;
						if (hasMultipleIterations && exec.review_iteration) {
							// Multiple iterations: "Execution #1 (Run 1)", "Execution #1 (Run 2)"
							label = `Execution #${executionNumberInRun[idx]} (Run ${exec.review_iteration})`;
						} else {
							// Single iteration or no iteration: "Execution #1", "Execution #2"
							label = `Execution #${idx + 1}`;
						}

						return (
							<button
								key={exec.call_id || `exec-${idx}`}
								onClick={() => onSelectIndex(idx)}
								className={`
                  px-4 py-2 rounded-xl text-sm font-medium transition-all
                  focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)]
                  ${
										selectedIndex === idx
											? "border border-[color:var(--color-primary)] bg-[rgba(var(--color-primary-rgb),0.1)] text-[color:var(--color-primary)] shadow-sm"
											: "border border-slate-200 bg-white text-slate-600 hover:text-slate-900 hover:border-slate-300 hover:bg-slate-50"
									}
                `}
							>
								{label}
							</button>
						);
					})}
				</div>
			</div>
		);
	};

	const renderRawView = (execution: T) => {
		return (
			<div className="rounded-2xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/40 p-5 shadow-[0_20px_55px_rgba(0,0,0,0.55)]">
				<JsonViewerEnhanced data={execution} />
			</div>
		);
	};

	const renderEmptyState = () => {
		if (renderer.renderEmptyState) {
			return renderer.renderEmptyState();
		}
		return (
			<div className="flex-1 flex items-center justify-center py-16">
				<div className="text-center max-w-sm">
					{/* Icon Container */}
					<div className="p-5 rounded-2xl bg-[color:var(--color-surface)]/30 border border-[color:var(--color-border)]/40 inline-block mb-5 shadow-[0_20px_55px_rgba(0,0,0,0.35)]">
						<AlertCircle className="w-10 h-10 text-[color:var(--color-text-muted)]" />
					</div>

					{/* Title */}
					<h3 className="text-lg font-semibold text-slate-900 mb-2">
						No Executions
					</h3>

					{/* Description */}
					<p className="text-sm text-[color:var(--color-text-muted)] leading-relaxed">
						This tool hasn&apos;t been executed yet
					</p>
				</div>
			</div>
		);
	};

	if (executions.length === 0) {
		return renderEmptyState();
	}

	const currentExecution = executions[selectedIndex];

	return (
		<>
			{renderExecutionSelector()}

			{currentExecution && (
				<>
					<ExecutionTabs
						tabs={renderer.getViewModes()}
						active={viewMode}
						onChange={setViewMode}
					/>

					<div className="flex-1 overflow-y-auto p-6 custom-scrollbar">
						{viewMode === "raw"
							? renderRawView(currentExecution)
							: renderer.renderViewMode(viewMode, currentExecution)}
					</div>
				</>
			)}
		</>
	);
}

/**
 * Helper for maintaining backward compatibility with class components
 */
export abstract class BaseRenderer<T extends ToolExecution = ToolExecution>
	extends React.Component<BaseRendererProps<T>>
	implements IRenderer<T>
{
	abstract getViewModes(): Array<{
		key: string;
		label: string;
		icon?: React.ReactNode;
	}>;
	abstract renderViewMode(mode: string, execution: T): React.ReactNode;

	getDefaultViewMode() {
		const modes = this.getViewModes();
		return modes[0]?.key || "raw";
	}

	renderEmptyState(): React.ReactNode {
		return (
			<div className="flex-1 flex items-center justify-center py-16">
				<div className="text-center max-w-sm">
					{/* Icon Container */}
					<div className="p-5 rounded-2xl bg-[color:var(--color-surface)]/30 border border-[color:var(--color-border)]/40 inline-block mb-5 shadow-[0_20px_55px_rgba(0,0,0,0.35)]">
						<AlertCircle className="w-10 h-10 text-[color:var(--color-text-muted)]" />
					</div>

					{/* Title */}
					<h3 className="text-lg font-semibold text-slate-900 mb-2">
						No Executions
					</h3>

					{/* Description */}
					<p className="text-sm text-[color:var(--color-text-muted)] leading-relaxed">
						This tool hasn&apos;t been executed yet
					</p>
				</div>
			</div>
		);
	}

	render() {
		return <BaseRendererComponent {...this.props} renderer={this} />;
	}
}
