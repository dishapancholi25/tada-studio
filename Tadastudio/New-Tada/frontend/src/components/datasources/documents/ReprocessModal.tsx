"use client";

import {
	BookOpen,
	Code,
	FileText,
	Hash,
	Loader2,
	RefreshCw,
	Scale,
	Target,
	Type,
	X,
	Zap,
} from "lucide-react";
import { useCallback, useState } from "react";

interface ReprocessConfig {
	strategy:
		| "recursive"
		| "character"
		| "token"
		| "semantic"
		| "whole_page";
	chunkSize: number | null;
	chunkOverlap: number;
	preset: "fast" | "balanced" | "precise" | "whole_page" | "custom";
}

interface ReprocessModalProps {
	isOpen: boolean;
	onClose: () => void;
	onReprocess: (config: ReprocessConfig) => Promise<void>;
	documentName: string;
	currentChunkCount: number;
}

const PRESET_CONFIGS = {
	fast: {
		strategy: "recursive" as const,
		chunkSize: 2000,
		chunkOverlap: 100,
		description: "Larger chunks for faster processing",
		icon: Zap,
		color: "text-orange-600",
		bgColor: "from-white to-white",
		borderColor: "border-orange-300",
	},
	balanced: {
		strategy: "recursive" as const,
		chunkSize: 1000,
		chunkOverlap: 200,
		description: "Optimal balance of speed and accuracy",
		icon: Scale,
		color: "text-orange-600",
		bgColor: "from-white to-white",
		borderColor: "border-orange-400",
	},
	precise: {
		strategy: "semantic" as const,
		chunkSize: 500,
		chunkOverlap: 100,
		description: "Smaller chunks for maximum precision",
		icon: Target,
		color: "text-amber-600",
		bgColor: "from-white to-white",
		borderColor: "border-amber-400",
	},
	whole_page: {
		strategy: "whole_page" as const,
		chunkSize: null,
		chunkOverlap: 0,
		description: "Keep PDF pages intact as single chunks",
		icon: FileText,
		color: "text-orange-700",
		bgColor: "from-white to-white",
		borderColor: "border-orange-300",
	},
};

const STRATEGY_INFO = {
	recursive: {
		name: "Recursive Character",
		icon: BookOpen,
		description: "Intelligently splits at natural boundaries",
	},
	character: {
		name: "Fixed Character",
		icon: Type,
		description: "Splits at fixed character intervals",
	},
	token: {
		name: "Token-based",
		icon: Hash,
		description: "Splits based on language model tokens",
	},
	semantic: {
		name: "Semantic",
		icon: Code,
		description: "Uses NLP to identify semantic boundaries",
	},
	whole_page: {
		name: "Whole Page",
		icon: FileText,
		description: "Keeps each PDF page as a single chunk",
	},
};

export default function ReprocessModal({
	isOpen,
	onClose,
	onReprocess,
	documentName,
	currentChunkCount,
}: ReprocessModalProps) {
	const [config, setConfig] = useState<ReprocessConfig>({
		strategy: "recursive",
		chunkSize: 1000,
		chunkOverlap: 200,
		preset: "balanced",
	});
	const [processing, setProcessing] = useState(false);

	const isWholePageMode = config.strategy === "whole_page";

	const handlePresetSelect = useCallback(
		(preset: "fast" | "balanced" | "precise" | "whole_page") => {
			const presetConfig = PRESET_CONFIGS[preset];
			setConfig({
				strategy: presetConfig.strategy,
				chunkSize: presetConfig.chunkSize,
				chunkOverlap: presetConfig.chunkOverlap,
				preset,
			});
		},
		[],
	);

	const handleReprocess = async () => {
		setProcessing(true);
		try {
			await onReprocess(config);
			onClose();
		} catch (error) {
			console.error("Reprocess failed:", error);
		} finally {
			setProcessing(false);
		}
	};

	if (!isOpen) return null;

	return (
		<div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/45 p-4">
			<div className="max-h-[90vh] w-full max-w-2xl overflow-hidden rounded-2xl border border-orange-200 bg-white shadow-[0_24px_70px_rgba(15,23,42,0.22)]">
				{/* Header */}
				<div className="border-b border-orange-300 bg-white p-6">
					<div className="flex items-center justify-between">
						<div className="flex items-center gap-3">
							<div className="rounded-lg bg-orange-500 p-2 shadow-md">
								<RefreshCw className="h-6 w-6 text-white" />
							</div>
							<div>
								<h2 className="text-xl font-bold text-slate-900">
									Reprocess Document
								</h2>
								<p className="mt-1 text-sm text-slate-600">
									Re-chunk &quot;{documentName}&quot; with new settings
								</p>
							</div>
						</div>
						<button
							onClick={onClose}
							disabled={processing}
							className="rounded-lg border border-transparent p-2 text-slate-500 transition-colors hover:border-orange-300 hover:bg-white hover:text-slate-900 disabled:opacity-50"
						>
							<X className="h-5 w-5" />
						</button>
					</div>
				</div>

				{/* Content */}
				<div className="max-h-[calc(90vh-200px)] overflow-y-auto p-6">
					{/* Current Status */}
					<div className="mb-6 rounded-xl border border-orange-300 bg-white p-4">
						<p className="text-sm text-slate-700">
							Current chunk count:{" "}
							<span className="font-mono font-semibold text-orange-700">
								{currentChunkCount}
							</span>
						</p>
					</div>

					{/* Presets */}
					<div className="mb-6">
						<h3 className="mb-3 text-xs font-semibold capitalize text-orange-700">
							Quick Presets
						</h3>
						<div className="grid grid-cols-2 gap-3">
							{Object.entries(PRESET_CONFIGS).map(([key, preset]) => {
								const Icon = preset.icon;
								const isSelected = config.preset === key;

								return (
									<button
										key={key}
										type="button"
										onClick={() =>
											handlePresetSelect(
												key as "fast" | "balanced" | "precise" | "whole_page",
											)
										}
										disabled={processing}
										className={`relative p-4 rounded-xl border transition-all duration-200 text-left ${
											isSelected
												? `bg-gradient-to-br ${preset.bgColor} ${preset.borderColor} shadow-md`
												: "border-orange-200 bg-white hover:border-orange-400 hover:bg-white"
										} disabled:opacity-50 disabled:cursor-not-allowed`}
									>
										{isSelected && (
											<div className="absolute right-2 top-2 h-2 w-2 rounded-full bg-orange-500" />
										)}
										<Icon className={`w-5 h-5 ${preset.color} mb-2`} />
										<h4
											className={`text-sm font-semibold ${isSelected ? "text-slate-900" : "text-slate-700"}`}
										>
											{key === "whole_page"
												? "Whole Page"
												: key.charAt(0).toUpperCase() + key.slice(1)}
										</h4>
										<p className="mt-1 text-xs text-slate-500">
											{preset.description}
										</p>
									</button>
								);
							})}
						</div>
					</div>

					{/* Strategy Selection */}
					<div className="mb-6">
						<h3 className="mb-3 text-xs font-semibold capitalize text-orange-700">
							Chunking Strategy
						</h3>
						<div className="grid grid-cols-2 gap-2">
							{Object.entries(STRATEGY_INFO).map(([key, strategy]) => {
								const Icon = strategy.icon;
								const isSelected = config.strategy === key;

								return (
									<button
										key={key}
										type="button"
										onClick={() =>
											setConfig({
												...config,
												strategy: key as ReprocessConfig["strategy"],
												preset: "custom",
												// Reset chunk size for whole_page
												chunkSize: key === "whole_page" ? null : 1000,
												chunkOverlap: key === "whole_page" ? 0 : config.chunkOverlap,
											})
										}
										disabled={processing}
										className={`p-3 rounded-xl border text-left transition-all ${
											isSelected
												? "border-orange-400 bg-white shadow-sm"
												: "border-orange-200 bg-white hover:border-orange-400 hover:bg-white"
										} disabled:opacity-50`}
									>
										<div className="flex items-center gap-2">
											<Icon
												className={`h-4 w-4 ${isSelected ? "text-orange-700" : "text-slate-500"}`}
											/>
											<span
												className={`text-sm ${isSelected ? "font-semibold text-slate-900" : "text-slate-700"}`}
											>
												{strategy.name}
											</span>
										</div>
									</button>
								);
							})}
						</div>
					</div>

					{/* Parameters */}
					<div className="mb-6 rounded-xl border border-orange-300 bg-white p-4">
						<h3 className="mb-4 text-xs font-semibold capitalize text-orange-700">
							Parameters
						</h3>

						{isWholePageMode && (
							<div className="mb-4 rounded-lg border border-orange-300 bg-white p-3">
								<p className="text-xs text-orange-800">
									Whole Page mode keeps each PDF page as a single chunk. Size
									and overlap settings are not applicable.
								</p>
							</div>
						)}

						<div className="space-y-4">
							<div className={isWholePageMode ? "opacity-50" : ""}>
								<div className="flex items-center justify-between mb-2">
									<label className="text-sm text-slate-700">
										Chunk Size
									</label>
									<span className="font-mono text-sm text-orange-700">
										{isWholePageMode ? "N/A" : `${config.chunkSize} chars`}
									</span>
								</div>
								<input
									type="range"
									min="200"
									max="4000"
									step="100"
									value={config.chunkSize ?? 1000}
									onChange={(e) =>
										setConfig({
											...config,
											chunkSize: Number.parseInt(e.target.value),
											preset: "custom",
										})
									}
									disabled={isWholePageMode || processing}
									className="w-full accent-orange-500 disabled:cursor-not-allowed"
								/>
							</div>

							<div className={isWholePageMode ? "opacity-50" : ""}>
								<div className="flex items-center justify-between mb-2">
									<label className="text-sm text-slate-700">
										Chunk Overlap
									</label>
									<span className="font-mono text-sm text-orange-700">
										{isWholePageMode ? "N/A" : `${config.chunkOverlap} chars`}
									</span>
								</div>
								<input
									type="range"
									min="0"
									max="500"
									step="50"
									value={config.chunkOverlap}
									onChange={(e) =>
										setConfig({
											...config,
											chunkOverlap: Number.parseInt(e.target.value),
											preset: "custom",
										})
									}
									disabled={isWholePageMode || processing}
									className="w-full accent-orange-500 disabled:cursor-not-allowed"
								/>
							</div>
						</div>
					</div>

					{/* Warning */}
					<div className="rounded-xl border border-amber-300 bg-white p-4">
						<p className="text-xs text-amber-800">
							<strong>Note:</strong> Reprocessing will delete existing chunks
							and create new ones. This may affect existing search results and
							agent workflows using this document.
						</p>
					</div>
				</div>

				{/* Footer */}
				<div className="border-t border-orange-300 bg-white p-6">
					<div className="flex items-center justify-between">
						<div className="text-xs text-slate-600">
							Strategy: {config.strategy}
							{config.chunkSize !== null && ` • ${config.chunkSize} chars`}
							{config.chunkOverlap > 0 && ` • ${config.chunkOverlap} overlap`}
						</div>
						<div className="flex gap-3">
							<button
								type="button"
								onClick={onClose}
								disabled={processing}
								className="px-4 py-2 text-slate-600 transition-colors hover:text-slate-900 disabled:opacity-50"
							>
								Cancel
							</button>
							<button
								type="button"
								onClick={handleReprocess}
								disabled={processing}
								className="flex items-center gap-2 rounded-lg bg-orange-500 px-6 py-2 font-semibold text-white shadow-md transition-all duration-200 hover:scale-105 hover:bg-orange-600 disabled:opacity-50 disabled:hover:scale-100"
							>
								{processing ? (
									<>
										<Loader2 className="w-4 h-4 animate-spin text-orange-500" />
										Reprocessing...
									</>
								) : (
									<>
										<RefreshCw className="w-4 h-4" />
										Reprocess Document
									</>
								)}
							</button>
						</div>
					</div>
				</div>
			</div>
		</div>
	);
}
