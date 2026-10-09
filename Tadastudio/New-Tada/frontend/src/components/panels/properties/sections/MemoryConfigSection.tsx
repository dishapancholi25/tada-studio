"use client";

import { Brain, GitBranch, Loader2, MessageSquare, Trash2 } from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import Dropdown from "../../../ui/Dropdown";

interface MemoryConfigSectionProps {
	memoryEnabled: boolean;
	onMemoryEnabledChange: (enabled: boolean) => void;
	memoryWindowSize: number;
	onMemoryWindowSizeChange: (size: number) => void;
	memoryStrategy: string;
	onMemoryStrategyChange: (strategy: string) => void;
	onClearMemory: () => void;
	clearingMemory: boolean;
	agentName: string;
	/** Dropdown list styling: light menus keep text dark on hover (e.g. agent panel on light surface). */
	dropdownMenuAppearance?: "default" | "light";
}

export default function MemoryConfigSection({
	memoryEnabled,
	onMemoryEnabledChange,
	memoryWindowSize,
	onMemoryWindowSizeChange,
	memoryStrategy,
	onMemoryStrategyChange,
	onClearMemory,
	clearingMemory,
	agentName,
	dropdownMenuAppearance = "light",
}: MemoryConfigSectionProps) {
	const [isEditingSize, setIsEditingSize] = useState(false);
	const [editSize, setEditSize] = useState(memoryWindowSize.toString());
	const inputRef = useRef<HTMLInputElement>(null);
	const sliderProgress = ((memoryWindowSize - 5) / 45) * 100;

	useEffect(() => {
		setEditSize(memoryWindowSize.toString());
	}, [memoryWindowSize]);

	useEffect(() => {
		if (isEditingSize && inputRef.current) {
			inputRef.current.focus();
			inputRef.current.select();
		}
	}, [isEditingSize]);

	const handleSizeClick = useCallback(() => {
		setIsEditingSize(true);
	}, []);

	const handleSizeBlur = useCallback(() => {
		const newSize = parseInt(editSize);
		if (!isNaN(newSize) && newSize >= 5 && newSize <= 50) {
			onMemoryWindowSizeChange(newSize);
		} else {
			setEditSize(memoryWindowSize.toString());
		}
		setIsEditingSize(false);
	}, [editSize, memoryWindowSize, onMemoryWindowSizeChange]);

	const handleSizeKeyDown = useCallback(
		(e: React.KeyboardEvent<HTMLInputElement>) => {
			if (e.key === "Enter") {
				handleSizeBlur();
			} else if (e.key === "Escape") {
				setEditSize(memoryWindowSize.toString());
				setIsEditingSize(false);
			}
		},
		[handleSizeBlur, memoryWindowSize],
	);

	const handleMemoryEnabledChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			onMemoryEnabledChange(e.target.checked);
		},
		[onMemoryEnabledChange],
	);

	const handleRangeChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			onMemoryWindowSizeChange(parseInt(e.target.value));
		},
		[onMemoryWindowSizeChange],
	);

	const handleEditSizeChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setEditSize(e.target.value);
		},
		[],
	);

	return (
		<div className="space-y-6">
			<div className="rounded-[4px] border border-slate-200 bg-white p-6 shadow-sm">
				<div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 pb-5">
					<div className="flex items-center gap-3">
						<div className="flex h-12 w-12 items-center justify-center rounded-[4px] border border-orange-200 bg-orange-100 text-orange-600">
							<Brain className="h-6 w-6" />
						</div>
						<div>
							<h3 className="text-xl font-semibold text-slate-900">Memory</h3>
							<p className="text-sm text-slate-600">
								Control how much of the conversation {agentName} remembers.
							</p>
						</div>
					</div>
					<label className="relative inline-flex items-center cursor-pointer">
						<input
							type="checkbox"
							checked={memoryEnabled}
							onChange={handleMemoryEnabledChange}
							className="peer sr-only"
						/>
						<div className="h-7 w-12 rounded-full border border-slate-300 bg-slate-200 transition-colors duration-200 peer-checked:bg-orange-500 peer-checked:border-orange-500 peer-focus-visible:ring-2 peer-focus-visible:ring-orange-500/30" />
						<span className="absolute left-1 top-1 h-5 w-5 rounded-full bg-white shadow-sm transition-transform duration-200 peer-checked:translate-x-5" />
					</label>
				</div>
				<p className="mt-4 text-sm text-slate-600">
					When enabled, the agent will recall the latest message pairs to keep
					conversations coherent and contextual.
				</p>
			</div>

			{memoryEnabled && (
				<div className="space-y-6 rounded-[4px] border border-slate-200 bg-white p-6 shadow-sm">
					<div className="grid gap-6 md:grid-cols-2">
						<div>
							<label
								htmlFor="memory-window-size"
								className="mb-3 block text-sm font-medium text-slate-800"
							>
								Memory Window Size
							</label>
							<div className="flex items-center gap-4">
								<input
									id="memory-window-size"
									type="range"
									min="5"
									max="50"
									value={memoryWindowSize}
									onChange={handleRangeChange}
									className="flex-1 transition-all duration-200"
									style={{
										background: `linear-gradient(to right, rgb(234 88 12) 0%, rgb(234 88 12) ${sliderProgress}%, rgb(226 232 240) ${sliderProgress}%, rgb(226 232 240) 100%)`,
										accentColor: "rgb(234 88 12)",
									}}
								/>
								{isEditingSize ? (
									<input
										ref={inputRef}
										type="number"
										min="5"
										max="50"
										value={editSize}
										onChange={handleEditSizeChange}
										onBlur={handleSizeBlur}
										onKeyDown={handleSizeKeyDown}
										className="w-16 rounded-[4px] border border-slate-200 bg-white px-2 py-1 text-center text-base font-semibold text-slate-900 focus:border-orange-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/20"
									/>
								) : (
									<button
										onClick={handleSizeClick}
										className="w-14 rounded-[4px] border border-slate-200 bg-white px-2 py-1 text-center text-base font-semibold text-slate-900 transition-colors hover:border-orange-400"
										title="Click to edit"
									>
										{memoryWindowSize}
									</button>
								)}
							</div>
							<p className="mt-2 text-xs text-slate-600">
								Number of user/assistant message pairs to keep in rolling
								context.
							</p>
						</div>

						<div>
							<label className="mb-3 block text-sm font-medium text-slate-800">
								Memory Strategy
							</label>
							<Dropdown
								value={memoryStrategy}
								onChange={onMemoryStrategyChange}
								menuAppearance={dropdownMenuAppearance}
								triggerClassName="!rounded-[4px] !border-slate-200 !bg-white hover:!border-orange-400 hover:!bg-slate-50"
								dropdownClassName="!border-slate-200 !bg-white"
								optionClassName="!text-slate-900 hover:!bg-slate-100 hover:!text-orange-800"
								options={[
									{
										value: "thread_scoped",
										label: "Thread scoped",
										description:
											"Only remember conversations within this workflow run",
										icon: <MessageSquare className="h-4 w-4" />,
									},
									{
										value: "cross_thread",
										label: "Cross-thread",
										description: "Share memory across different workflow runs",
										icon: <GitBranch className="h-4 w-4" />,
									},
								]}
							/>
							<p className="mt-2 text-xs text-slate-600">
								Choose whether memory is unique to this execution or shared
								broadly.
							</p>
						</div>
					</div>

					<div className="rounded-[4px] border border-slate-200 bg-slate-50 p-4">
						<div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
							<div>
								<h4 className="text-sm font-semibold text-slate-900">
									Clear Memory
								</h4>
								<p className="text-xs text-slate-600">
									Remove all stored interactions for {agentName}. Useful when
									retraining instructions.
								</p>
							</div>
							<button
								onClick={onClearMemory}
								disabled={clearingMemory}
								className="inline-flex items-center gap-2 rounded-[4px] border border-red-200 bg-white px-4 py-2 text-sm font-medium text-red-700 transition-all hover:border-red-300 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
							>
								{clearingMemory ? (
									<>
										<Loader2 className="h-4 w-4 animate-spin text-orange-500" />
										Clearing...
									</>
								) : (
									<>
										<Trash2 className="h-4 w-4" />
										Clear history
									</>
								)}
							</button>
						</div>
					</div>
				</div>
			)}
		</div>
	);
}
