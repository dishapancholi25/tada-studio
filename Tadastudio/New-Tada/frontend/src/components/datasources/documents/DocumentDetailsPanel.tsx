"use client";

import { CheckCircle, Clock, Coins, Cpu, RefreshCw, Search, Trash2, X, XCircle } from "lucide-react";
import Button from "@/components/ui/Button";

export interface DocumentDetails {
	id: string;
	name: string;
	type: string;
	size: number;
	status: "pending" | "processing" | "processed" | "failed";
	chunk_count: number;
	upload_date: string;
	error_message?: string;
	embedding_tokens?: number | null;
	embedding_cost?: number | null;
	embedding_model?: string | null;
	collection_id: string;
	collection_name?: string;
	owner_name?: string;
	owner_email?: string;
	is_read_only?: boolean;
}

interface DocumentDetailsPanelProps {
	document: DocumentDetails;
	onClose: () => void;
	onDelete: () => void;
	onReprocess: () => void;
	onSearchWithin: () => void;
	isReadOnly?: boolean;
	className?: string;
}

const formatFileSize = (bytes: number): string => {
	if (bytes === 0) return "0 Bytes";
	const k = 1024;
	const sizes = ["Bytes", "KB", "MB", "GB"];
	const i = Math.floor(Math.log(bytes) / Math.log(k));
	return parseFloat((bytes / k ** i).toFixed(2)) + " " + sizes[i];
};

const formatUploadDate = (dateString: string): string => {
	if (!dateString) return "—";
	const date = new Date(dateString);
	if (Number.isNaN(date.getTime())) return dateString;
	return date.toLocaleString(undefined, {
		dateStyle: "medium",
		timeStyle: "short",
	});
};

const getStatusIcon = (status: string) => {
	switch (status) {
		case "processed":
			return <CheckCircle className="h-4 w-4 text-orange-600" />;
		case "processing":
			return <Clock className="h-4 w-4 text-amber-500" />;
		case "failed":
			return <XCircle className="h-4 w-4 text-red-500" />;
		default:
			return null;
	}
};

export default function DocumentDetailsPanel({
	document,
	onClose,
	onDelete,
	onReprocess,
	onSearchWithin,
	isReadOnly: isReadOnlyProp,
	className,
}: DocumentDetailsPanelProps) {
	const isReadOnly = isReadOnlyProp ?? document.is_read_only ?? false;
	return (
		<div
			className={`space-y-4 rounded-2xl border border-orange-300 bg-white p-5 text-slate-900 shadow-md ${className || ""}`}
			style={{
				boxShadow: undefined,
			}}
		>
			{/* Header: Name + Status + Close */}
			<div className="flex items-start justify-between gap-3">
				<div className="flex-1 min-w-0">
					<div className="flex items-center gap-2.5">
						<h4 className="truncate text-sm font-semibold text-slate-900">{document.name}</h4>
						<div
							className="inline-flex flex-shrink-0 items-center gap-1.5 rounded-full border border-orange-200 bg-white px-2 py-0.5 text-xs"
						>
							{getStatusIcon(document.status)}
							<span className="capitalize text-slate-700">{document.status}</span>
						</div>
					</div>
					{/* Collection + Owner subtitle */}
					<div className="mt-1 flex items-center gap-1.5 text-xs text-slate-500">
						{document.collection_name && <span>{document.collection_name}</span>}
						{document.collection_name && (document.owner_name || document.owner_email) && <span>&middot;</span>}
						{(document.owner_name || document.owner_email) && (
							<span>
								{document.owner_name
									? <>{document.owner_name}{document.owner_email && <> &middot; <a href={`mailto:${document.owner_email}`} className="text-orange-700 hover:text-slate-900 hover:underline">{document.owner_email}</a></>}</>
									: document.owner_email && <a href={`mailto:${document.owner_email}`} className="text-orange-700 hover:text-slate-900 hover:underline">{document.owner_email}</a>
								}
							</span>
						)}
					</div>
				</div>
				<Button
					onClick={onClose}
					variant="ghost"
					size="sm"
					icon={<X className="w-4 h-4" />}
					className="text-slate-700 hover:bg-white hover:text-slate-900"
				>
					Clear
				</Button>
			</div>

			{/* Metadata grid */}
			<div className="grid grid-cols-4 gap-3 text-sm">
				<div>
					<span className="text-[0.6rem] capitalize text-orange-700/70">
						Type
					</span>
					<p className="font-mono text-slate-700">{document.type}</p>
				</div>
				<div>
					<span className="text-[0.6rem] capitalize text-orange-700/70">
						Size
					</span>
					<p className="font-mono text-slate-700">{formatFileSize(document.size)}</p>
				</div>
				<div>
					<span className="text-[0.6rem] capitalize text-orange-700/70">
						Chunks
					</span>
					<p className="font-mono text-slate-700">{document.chunk_count > 0 ? document.chunk_count : "—"}</p>
				</div>
				<div>
					<span className="text-[0.6rem] capitalize text-orange-700/70">
						Uploaded
					</span>
					<p className="font-mono text-xs text-slate-700">{formatUploadDate(document.upload_date)}</p>
				</div>
			</div>

			{/* Embedding info */}
			{(document.embedding_tokens || document.embedding_model) && (
				<div className="rounded-xl border border-orange-200/70 border-slate-2000 p-3 shadow-sm">
					<div className="flex items-center gap-1.5 mb-2">
						<Cpu className="h-3.5 w-3.5 text-orange-600" />
						<span className="text-[0.6rem] font-semibold capitalize text-orange-700/80">
							Embedding
						</span>
					</div>
					<div className="grid grid-cols-3 gap-3 text-sm">
						{document.embedding_model && (
							<div>
								<span className="text-[0.6rem] capitalize text-slate-500">
									Model
								</span>
								<p className="truncate font-mono text-xs text-slate-700" title={document.embedding_model}>
									{document.embedding_model}
								</p>
							</div>
						)}
						<div>
							<span className="text-[0.6rem] capitalize text-slate-500">
								Tokens
							</span>
							<p className="font-mono text-slate-700">
								{document.embedding_tokens ? document.embedding_tokens.toLocaleString() : "—"}
							</p>
						</div>
						<div>
							<span className="text-[0.6rem] capitalize text-slate-500">
								Cost
							</span>
							<p className="font-mono text-slate-700">
								{document.embedding_cost != null && document.embedding_cost > 0 ? (
									<span className="inline-flex items-center gap-1">
										<Coins className="h-3 w-3 text-amber-500" />
										${document.embedding_cost.toFixed(4)}
									</span>
								) : "—"}
							</p>
						</div>
					</div>
				</div>
			)}

			{/* Error Message */}
			{document.error_message && (
				<div className="rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700">
					{document.error_message}
				</div>
			)}

			{/* Actions */}
			<div className="flex flex-wrap justify-end gap-2 border-t border-orange-200/70 pt-2">
				<Button
					onClick={onSearchWithin}
					variant="secondary"
					size="sm"
					icon={<Search className="w-4 h-4" />}
					className="border-orange-200 bg-white text-slate-800 hover:border-orange-400 hover:bg-white hover:text-slate-900"
				>
					Search within
				</Button>
				{!isReadOnly && document.status === "processed" && (
					<Button
						onClick={onReprocess}
						variant="secondary"
						size="sm"
						icon={<RefreshCw className="w-4 h-4" />}
						className="border-orange-200 bg-white text-slate-800 hover:border-orange-400 hover:bg-white hover:text-slate-900"
					>
						Reprocess
					</Button>
				)}
				{!isReadOnly && (
					<Button
						onClick={onDelete}
						variant="danger"
						size="sm"
						icon={<Trash2 className="w-4 h-4" />}
					>
						Remove
					</Button>
				)}
			</div>
		</div>
	);
}
