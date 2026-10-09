"use client";

import { X } from "lucide-react";
import { useState } from "react";
import Button from "@/components/ui/Button";
import FormInput from "@/components/ui/FormInput";

export interface SearchResult {
	content: string;
	score: number;
	metadata?: {
		source?: string;
		chunk_index?: number;
		total_chunks?: number;
		[key: string]: unknown;
	};
}

interface DocumentSearchModalProps {
	isOpen: boolean;
	onClose: () => void;
	onSearch: (query: string) => Promise<SearchResult[]>;
	documentName?: string;
}

export default function DocumentSearchModal({
	isOpen,
	onClose,
	onSearch,
	documentName,
}: DocumentSearchModalProps) {
	const [query, setQuery] = useState("");
	const [results, setResults] = useState<SearchResult[]>([]);
	const [searching, setSearching] = useState(false);

	if (!isOpen) return null;

	const handleSearch = async () => {
		if (!query.trim()) return;

		setSearching(true);
		try {
			const searchResults = await onSearch(query);
			setResults(searchResults);
		} catch (error) {
			console.error("Search failed:", error);
		} finally {
			setSearching(false);
		}
	};

	const handleClose = () => {
		setQuery("");
		setResults([]);
		onClose();
	};

	const handleKeyDown = (e: React.KeyboardEvent) => {
		if (e.key === "Enter") {
			handleSearch();
		}
	};

	return (
		<div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/45 p-4">
			<div
				className="flex max-h-[80vh] w-full max-w-4xl flex-col rounded-2xl border border-orange-300 bg-white shadow-2xl"
				style={{
					boxShadow: undefined,
				}}
			>
				{/* Header */}
				<div className="mb-4 flex items-center justify-between rounded-t-2xl border-b border-orange-300 bg-white px-6 py-4">
					<h3 className="text-lg font-semibold text-slate-900">
						{documentName ? `Test Retrieval: ${documentName}` : "Test Retrieval"}
					</h3>
					<button
						onClick={handleClose}
						className="rounded-lg border border-transparent p-2 text-slate-500 transition-colors hover:border-orange-300 hover:bg-white hover:text-slate-900"
					>
						<X className="h-5 w-5" />
					</button>
				</div>

				{/* Search Input */}
				<div className="mb-4 px-6">
					<div className="flex gap-3">
						<div className="flex-1">
							<FormInput
								value={query}
								onChange={(e) => setQuery(e.target.value)}
								onKeyDown={handleKeyDown}
								placeholder="Enter your search query..."
							/>
						</div>
						<Button
							onClick={handleSearch}
							disabled={!query.trim() || searching}
							loading={searching}
							className="border-orange-500 bg-orange-500 text-white hover:border-orange-600 hover:bg-orange-600"
						>
							{searching ? "Searching..." : "Search"}
						</Button>
					</div>
				</div>

				{/* Results */}
				<div className="flex-1 overflow-y-auto px-6 pb-6">
					{results.length > 0 ? (
						<div className="space-y-4">
							{results.map((result, index) => (
								<div
									key={`result-${result.score}-${result.content?.substring(0, 30) || index}`}
									className="rounded-xl border border-orange-300 bg-white p-4 shadow-sm"
								>
									<div className="flex justify-between items-start mb-2">
										<span className="text-sm font-semibold text-orange-700">
											Result {index + 1}
										</span>
										<span className="rounded-full border border-orange-300 bg-white px-2 py-0.5 font-mono text-xs text-orange-700">
											Score: {result.score.toFixed(3)}
										</span>
									</div>
									<p className="whitespace-pre-wrap text-sm text-slate-700">
										{result.content}
									</p>
									{result.metadata && Object.keys(result.metadata).length > 0 && (
										<div
											className="mt-3 pt-3 border-t"
											style={{ borderColor: "rgba(249,115,22,0.35)" }}
										>
											<p className="text-xs text-slate-500">
												Source: {result.metadata.source || "Unknown"} | Chunk:{" "}
												{(result.metadata.chunk_index ?? 0) + 1}/
												{result.metadata.total_chunks || "?"}
											</p>
										</div>
									)}
								</div>
							))}
						</div>
					) : searching ? (
						<div className="text-center py-8">
							<div className="mx-auto h-8 w-8 animate-spin rounded-full border-b-2 border-orange-500" />
							<p className="mt-2 text-slate-600">
								Searching...
							</p>
						</div>
					) : query && !searching ? (
						<div className="py-8 text-center text-slate-600">
							No results found for your query
						</div>
					) : (
						<div className="py-8 text-center text-slate-600">
							Enter a query to search through the document
						</div>
					)}
				</div>

			</div>
		</div>
	);
}
