"use client";

import {
	Brain,
	GitBranch,
	Loader2,
	MessageSquare,
	Trash2,
	X,
} from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import Dropdown from "../../../ui/Dropdown";

interface MemoryConfigOverlayProps {
	isOpen: boolean;
	onClose: () => void;
	memoryEnabled: boolean;
	onMemoryEnabledChange: (enabled: boolean) => void;
	memoryWindowSize: number;
	onMemoryWindowSizeChange: (size: number) => void;
	memoryStrategy: string;
	onMemoryStrategyChange: (strategy: string) => void;
	onClearMemory: () => void;
	clearingMemory: boolean;
	agentName: string;
}

export default function MemoryConfigOverlay({
	isOpen,
	onClose,
	memoryEnabled,
	onMemoryEnabledChange,
	memoryWindowSize,
	onMemoryWindowSizeChange,
	memoryStrategy,
	onMemoryStrategyChange,
	onClearMemory,
	clearingMemory,
	agentName,
}: MemoryConfigOverlayProps) {
	const [isEditingSize, setIsEditingSize] = useState(false);
	const [editSize, setEditSize] = useState(memoryWindowSize.toString());
	const inputRef = useRef<HTMLInputElement>(null);

	// Update editSize when memoryWindowSize changes externally
	useEffect(() => {
		setEditSize(memoryWindowSize.toString());
	}, [memoryWindowSize]);

	// Focus input when editing starts
	useEffect(() => {
		if (isEditingSize && inputRef.current) {
			inputRef.current.focus();
			inputRef.current.select();
		}
	}, [isEditingSize]);

	const handleSizeClick = () => {
		setIsEditingSize(true);
	};

	const handleSizeBlur = () => {
		const newSize = parseInt(editSize);
		if (!isNaN(newSize) && newSize >= 5 && newSize <= 50) {
			onMemoryWindowSizeChange(newSize);
		} else {
			setEditSize(memoryWindowSize.toString());
		}
		setIsEditingSize(false);
	};

	const handleSizeKeyDown = (e: React.KeyboardEvent) => {
		if (e.key === "Enter") {
			handleSizeBlur();
		} else if (e.key === "Escape") {
			setEditSize(memoryWindowSize.toString());
			setIsEditingSize(false);
		}
	};

	// useCallback handlers for event handling optimization
	const handleStopPropagation = useCallback((e: React.MouseEvent) => {
		e.stopPropagation();
	}, []);

	const handleMemoryEnabledChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			onMemoryEnabledChange(e.target.checked);
		},
		[onMemoryEnabledChange],
	);

	const handleMemoryWindowSizeChange = useCallback(
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

	if (!isOpen) return null;

	return (
		<div
			className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-start justify-center z-[110] p-4 pt-8 sm:pt-16 lg:pt-20 animate-fadeIn overflow-y-auto"
			onClick={handleStopPropagation}
		>
			<div
				className="bg-gradient-to-b from-[color:var(--color-surface)] to-[color:var(--color-bg-secondary)] border border-purple-400/50 rounded-xl shadow-2xl w-full max-w-4xl max-h-[calc(100vh-4rem)] sm:max-h-[calc(100vh-8rem)] lg:max-h-[calc(100vh-10rem)] mb-8 sm:mb-16 lg:mb-20 flex flex-col animate-scaleIn overflow-hidden"
				onClick={handleStopPropagation}
			>
				{/* Header */}
				<div className="flex items-center justify-between p-5 sm:p-6 bg-[color:var(--color-surface)]/50 border-b border-purple-400/30">
					<div className="flex items-center gap-3">
						<div className="p-3 bg-purple-400/10 rounded-xl">
							<Brain className="w-6 h-6 text-purple-400" />
						</div>
						<div>
							<h2 className="text-lg sm:text-xl font-bold text-slate-900 flex items-center gap-2">
								Memory
								{memoryEnabled && (
									<span className="text-xs px-2 py-0.5 bg-purple-400/20 text-purple-600 rounded-full">
										Enabled
									</span>
								)}
							</h2>
							<p className="text-sm text-[color:var(--color-text-muted)] mt-0.5">
								Enable conversation history and context retention
							</p>
						</div>
					</div>
					<button
						onClick={onClose}
						className="p-2 hover:bg-[color:var(--color-border)]/50 rounded-lg transition-all hover:rotate-90 duration-200"
					>
						<X className="w-5 h-5 text-[color:var(--color-text-muted)]" />
					</button>
				</div>

				{/* Content */}
				<div className="flex-1 overflow-y-auto p-5 sm:p-6 space-y-8 min-h-0">
					{/* Enable Memory Toggle */}
					<div className="flex items-center justify-between p-5 bg-[color:var(--color-surface)]/50 rounded-lg border border-purple-400/20 hover:border-purple-400/30 transition-colors duration-200">
						<div className="flex-1">
							<h4 className="text-base font-medium text-slate-900">
								Enable Memory
							</h4>
							<p className="text-sm text-[color:var(--color-text-muted)] mt-1 leading-relaxed">
								Agent will remember previous messages in the conversation
							</p>
						</div>
						<label className="relative inline-flex items-center cursor-pointer ml-4">
							<input
								type="checkbox"
								checked={memoryEnabled}
								onChange={handleMemoryEnabledChange}
								className="sr-only peer"
								aria-label="Enable memory for this agent"
							/>
							<div className="w-12 h-6 bg-[color:var(--color-border)] peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-purple-400/50 rounded-full peer peer-checked:after:translate-x-6 peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all after:duration-200 peer-checked:bg-purple-600 hover:scale-105 transition-transform"></div>
						</label>
					</div>

					{memoryEnabled && (
						<div className="space-y-8 animate-fadeIn bg-[color:var(--color-bg-secondary)]/30 rounded-lg p-6 border border-purple-400/10">
							{/* Memory Configuration - Side by side */}
							<div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
								{/* Memory Window Size */}
								<div>
									<label
										htmlFor="memory-window-size"
										className="block text-sm font-medium text-[color:var(--color-text-secondary)] mb-3"
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
											onChange={handleMemoryWindowSizeChange}
											className="flex-1 accent-purple-500 transition-all duration-200 hover:scale-105"
											style={{
												background: `linear-gradient(to right, rgb(168, 85, 247) 0%, rgb(168, 85, 247) ${((memoryWindowSize - 5) / 45) * 100}%, rgb(55, 65, 81) ${((memoryWindowSize - 5) / 45) * 100}%, rgb(55, 65, 81) 100%)`,
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
												className="text-base text-purple-400 font-bold w-16 text-center bg-purple-900/40 border border-purple-500/50 rounded-lg px-2 py-1 focus:outline-none focus:ring-2 focus:ring-purple-400/50"
											/>
										) : (
											<button
												onClick={handleSizeClick}
												className="text-base text-purple-400 font-bold w-12 text-center bg-purple-900/20 rounded-lg px-2 py-1 hover:bg-purple-900/30 transition-colors cursor-pointer"
												title="Click to edit"
											>
												{memoryWindowSize}
											</button>
										)}
									</div>
									<p className="text-sm text-[color:var(--color-text-muted)] mt-2">
										Number of conversation pairs (user + assistant messages) to
										remember
									</p>
								</div>

								{/* Memory Strategy */}
								<div>
									<label
										htmlFor="memory-strategy-select"
										className="block text-sm font-medium text-[color:var(--color-text-secondary)] mb-3"
									>
										Memory Strategy
									</label>
									<Dropdown
										value={memoryStrategy}
										onChange={onMemoryStrategyChange}
										options={[
											{
												value: "thread_scoped",
												label: "Thread Scoped",
												description: "Separate memory per conversation",
												icon: <MessageSquare className="w-4 h-4" />,
											},
											{
												value: "cross_thread",
												label: "Cross Thread",
												description: "Shared memory across conversations",
												icon: <GitBranch className="w-4 h-4" />,
											},
										]}
									/>
								</div>
							</div>

							{/* Clear Memory Button */}
							<div className="pt-6 border-t border-[color:var(--color-border)]">
								<label className="block text-sm font-medium text-[color:var(--color-text-secondary)] mb-3">
									Memory Management
								</label>
								<button
									onClick={onClearMemory}
									disabled={clearingMemory}
									className="px-4 py-2.5 bg-purple-900/20 hover:bg-purple-800/30 disabled:bg-[color:var(--color-surface)] disabled:cursor-not-allowed text-purple-400 hover:text-purple-600 text-sm font-medium rounded-lg transition-all duration-200 flex items-center gap-2 border border-purple-800/30 hover:border-purple-700/50 hover:scale-105 active:scale-95"
								>
									{clearingMemory ? (
										<>
											<Loader2 className="w-4 h-4 animate-spin" />
											Clearing...
										</>
									) : (
										<>
											<Trash2 className="w-4 h-4" />
											Clear Memory
										</>
									)}
								</button>
								<p className="mt-3 text-sm text-[color:var(--color-text-muted)]">
									Clear all stored memory for{" "}
									<span className="font-medium text-purple-600">
										{agentName}
									</span>{" "}
									across all conversations
								</p>
							</div>
						</div>
					)}
				</div>

				{/* Footer */}
				<div className="p-6 border-t border-purple-400/30 bg-[color:var(--color-surface)]/50">
					<div className="flex justify-end">
						<button
							onClick={onClose}
							className="px-6 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-all border border-[color:var(--color-surface-hover)]"
						>
							Done
						</button>
					</div>
				</div>
			</div>
		</div>
	);
}
