"use client";

import {
	CheckCircle,
	ChevronDown,
	ChevronUp,
	Clock,
	Coins,
	File,
	FileCode,
	FileSpreadsheet,
	FileText,
	Trash2,
	XCircle,
} from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import LoadingSkeleton from "../shared/LoadingSkeleton";

export interface DocumentItem {
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

interface DocumentTableProps {
	documents: DocumentItem[];
	selectedDocument: DocumentItem | null;
	onSelectDocument: (doc: DocumentItem) => void;
	onDeleteDocument: (id: string) => void;
	loading?: boolean;
	showCollectionColumn?: boolean;
	isReadOnly?: boolean;
	emptyMessage?: string;
}

type SortColumn =
	| "name"
	| "type"
	| "size"
	| "chunk_count"
	| "status"
	| "upload_date"
	| "embedding_tokens"
	| "embedding_cost";
type SortDirection = "asc" | "desc";

const formatFileSize = (bytes: number): string => {
	if (bytes === 0) return "0 Bytes";
	const k = 1024;
	const sizes = ["Bytes", "KB", "MB", "GB"];
	const i = Math.floor(Math.log(bytes) / Math.log(k));
	return parseFloat((bytes / k ** i).toFixed(2)) + " " + sizes[i];
};

const formatUploadDate = (dateString: string): string => {
	if (!dateString) return "\u2014";
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
			return <CheckCircle className="h-4 w-4 text-[#0DA931]" />;
		case "processing":
			return <Clock className="h-4 w-4 text-orange-500 animate-pulse" />;
		case "failed":
			return <XCircle className="h-4 w-4 text-red-500" />;
		default:
			return <Clock className="h-4 w-4 text-slate-400" />;
	}
};

interface DocTypeStyle {
	icon: React.ReactNode;
	bg: string;
}

function getDocTypeStyle(type: string): DocTypeStyle {
	const t = type.toLowerCase();
	if (t === "pdf")
		return {
			icon: <FileText className="h-5 w-5 text-orange-600" />,
			bg: "linear-gradient(135deg, #ffffff, #ffffff)",
		};
	if (t === "docx" || t === "doc")
		return {
			icon: <FileText className="h-5 w-5 text-orange-600" />,
			bg: "linear-gradient(135deg, #ffffff, #ffffff)",
		};
	if (t === "xlsx" || t === "xls" || t === "csv")
		return {
			icon: <FileSpreadsheet className="h-5 w-5 text-amber-600" />,
			bg: "linear-gradient(135deg, #ffffff, #ffffff)",
		};
	if (t === "md" || t === "markdown")
		return {
			icon: <FileCode className="h-5 w-5 text-orange-600" />,
			bg: "linear-gradient(135deg, #ffffff, #ffffff)",
		};
	if (t === "txt" || t === "text")
		return {
			icon: <File className="h-5 w-5 text-slate-600" />,
			bg: "#ffffff",
		};
	if (t === "json" || t === "yaml" || t === "yml" || t === "xml")
		return {
			icon: <FileCode className="h-5 w-5 text-amber-600" />,
			bg: "linear-gradient(135deg, #ffffff, #ffffff)",
		};
	if (t === "html" || t === "htm")
		return {
			icon: <FileCode className="h-5 w-5 text-orange-600" />,
			bg: "#ffffff",
		};
	return {
		icon: <FileText className="h-5 w-5 text-orange-600" />,
		bg: "linear-gradient(135deg, #ffffff, #ffffff)",
	};
}

interface SortableHeaderProps {
	label: string;
	column: SortColumn;
	currentSort: SortColumn | null;
	direction: SortDirection;
	onSort: (column: SortColumn) => void;
	className?: string;
}

function SortableHeader({
	label,
	column,
	currentSort,
	direction,
	onSort,
	className = "",
}: SortableHeaderProps) {
	const isActive = currentSort === column;
	return (
		<th
			className={`cursor-pointer select-none px-4 py-3 text-left font-semibold transition-colors hover:text-slate-900 ${className}`}
			onClick={() => onSort(column)}
		>
			<span className="inline-flex items-center gap-1">
				{label}
				{isActive ? (
					direction === "asc" ? (
						<ChevronUp className="w-3 h-3" />
					) : (
						<ChevronDown className="w-3 h-3" />
					)
				) : (
					<ChevronDown className="w-3 h-3 opacity-0 group-hover:opacity-30" />
				)}
			</span>
		</th>
	);
}

function compareValues(
	a: DocumentItem,
	b: DocumentItem,
	column: SortColumn,
	direction: SortDirection,
): number {
	let aVal: string | number | null;
	let bVal: string | number | null;

	switch (column) {
		case "name":
			aVal = a.name.toLowerCase();
			bVal = b.name.toLowerCase();
			break;
		case "type":
			aVal = a.type.toLowerCase();
			bVal = b.type.toLowerCase();
			break;
		case "size":
			aVal = a.size;
			bVal = b.size;
			break;
		case "chunk_count":
			aVal = a.chunk_count;
			bVal = b.chunk_count;
			break;
		case "status":
			aVal = a.status;
			bVal = b.status;
			break;
		case "upload_date":
			aVal = a.upload_date ? new Date(a.upload_date).getTime() : 0;
			bVal = b.upload_date ? new Date(b.upload_date).getTime() : 0;
			break;
		case "embedding_tokens":
			aVal = a.embedding_tokens ?? 0;
			bVal = b.embedding_tokens ?? 0;
			break;
		case "embedding_cost":
			aVal = a.embedding_cost ?? 0;
			bVal = b.embedding_cost ?? 0;
			break;
		default:
			return 0;
	}

	if (aVal == null) aVal = "";
	if (bVal == null) bVal = "";

	let cmp: number;
	if (typeof aVal === "number" && typeof bVal === "number") {
		cmp = aVal - bVal;
	} else {
		cmp = String(aVal).localeCompare(String(bVal));
	}

	return direction === "desc" ? -cmp : cmp;
}

export default function DocumentTable({
	documents,
	selectedDocument,
	onSelectDocument,
	onDeleteDocument,
	loading,
	showCollectionColumn,
	isReadOnly,
	emptyMessage,
}: DocumentTableProps) {
	const [sortColumn, setSortColumn] = useState<SortColumn | null>(null);
	const [sortDirection, setSortDirection] = useState<SortDirection>("asc");

	const handleSort = useCallback(
		(column: SortColumn) => {
			if (sortColumn === column) {
				setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
			} else {
				setSortColumn(column);
				setSortDirection("asc");
			}
		},
		[sortColumn],
	);

	const sortedDocuments = useMemo(() => {
		if (!sortColumn) return documents;
		return [...documents].sort((a, b) =>
			compareValues(a, b, sortColumn, sortDirection),
		);
	}, [documents, sortColumn, sortDirection]);

	if (loading) {
		return <LoadingSkeleton variant="table" rows={5} />;
	}

	if (documents.length === 0) {
		return (
			<div className="rounded-xl bg-white py-16 text-center text-sm text-slate-600">
				<FileText className="mx-auto mb-3 h-10 w-10 text-orange-400" />
				{emptyMessage || "Upload documents to populate this collection."}
			</div>
		);
	}

	return (
		<table className="min-w-full divide-y divide-orange-100">
			<thead className="sticky top-0 z-10 border-b border-orange-300 bg-white">
				<tr className="group text-xs capitalize tracking-wide text-slate-600">
					<SortableHeader
						label="Document"
						column="name"
						currentSort={sortColumn}
						direction={sortDirection}
						onSort={handleSort}
						className="px-5"
					/>
					{showCollectionColumn && (
						<th className="px-4 py-3 text-left font-medium">Collection</th>
					)}
					<SortableHeader
						label="Type"
						column="type"
						currentSort={sortColumn}
						direction={sortDirection}
						onSort={handleSort}
					/>
					<SortableHeader
						label="Size"
						column="size"
						currentSort={sortColumn}
						direction={sortDirection}
						onSort={handleSort}
					/>
					<SortableHeader
						label="Chunks"
						column="chunk_count"
						currentSort={sortColumn}
						direction={sortDirection}
						onSort={handleSort}
					/>
					<SortableHeader
						label="Tokens"
						column="embedding_tokens"
						currentSort={sortColumn}
						direction={sortDirection}
						onSort={handleSort}
					/>
					<SortableHeader
						label="Cost"
						column="embedding_cost"
						currentSort={sortColumn}
						direction={sortDirection}
						onSort={handleSort}
					/>
					<SortableHeader
						label="Status"
						column="status"
						currentSort={sortColumn}
						direction={sortDirection}
						onSort={handleSort}
					/>
					<SortableHeader
						label="Uploaded"
						column="upload_date"
						currentSort={sortColumn}
						direction={sortDirection}
						onSort={handleSort}
					/>
					{!isReadOnly && <th className="px-4 py-3" aria-label="Actions" />}
				</tr>
			</thead>
			<tbody className="divide-y divide-orange-100 text-sm">
				{sortedDocuments.map((doc) => {
					const typeStyle = getDocTypeStyle(doc.type);
					return (
						<tr
							key={doc.id}
							className="cursor-pointer transition-colors duration-150 hover:bg-white"
							style={{
								background:
									selectedDocument?.id === doc.id
										? "#ffffff"
										: undefined,
								borderLeft:
									selectedDocument?.id === doc.id
										? "3px solid #f97316"
										: undefined,
							}}
							onClick={() => onSelectDocument(doc)}
						>
							<td className="px-5 py-3 align-middle">
								<div className="flex items-center gap-3">
									<div
										className="rounded-md border border-orange-200 p-2"
										style={{ background: typeStyle.bg }}
									>
										{typeStyle.icon}
									</div>
									<div className="min-w-0">
										<p className="max-w-[200px] truncate text-sm font-semibold text-slate-900">
											{doc.name}
										</p>
										{doc.error_message && (
											<p className="truncate text-xs text-red-600">
												Processing error
											</p>
										)}
									</div>
								</div>
							</td>
							{showCollectionColumn && (
								<td className="px-4 py-3 align-middle">
									<div className="min-w-0">
										<p className="max-w-[160px] truncate text-sm text-slate-800">
											{doc.collection_name || "\u2014"}
										</p>
										{(doc.owner_name || doc.owner_email) && (
											<p className="truncate text-xs text-slate-500">
												{doc.owner_name || doc.owner_email}
											</p>
										)}
									</div>
								</td>
							)}
							<td className="px-4 py-3 align-middle">
								<span className="rounded border border-orange-300 bg-white px-1.5 py-0.5 font-mono text-xs text-orange-700">
									{doc.type.toUpperCase()}
								</span>
							</td>
							<td className="px-4 py-3 align-middle text-slate-600">
								{formatFileSize(doc.size)}
							</td>
							<td className="px-4 py-3 align-middle text-slate-600">
								{doc.chunk_count > 0 ? doc.chunk_count : "\u2014"}
							</td>
							<td className="px-4 py-3 align-middle font-mono text-xs text-slate-600">
								{doc.embedding_tokens
									? doc.embedding_tokens.toLocaleString()
									: "\u2014"}
							</td>
							<td className="px-4 py-3 align-middle font-mono text-xs text-slate-600">
								{doc.embedding_cost != null && doc.embedding_cost > 0 ? (
									<span className="inline-flex items-center gap-1">
										<Coins className="h-3 w-3 text-amber-500" />$
										{doc.embedding_cost.toFixed(4)}
									</span>
								) : (
									"\u2014"
								)}
							</td>
							<td className="px-4 py-3 align-middle">
								<div className="flex items-center gap-2">
									{getStatusIcon(doc.status)}
									<span className="text-sm capitalize text-slate-700">
										{doc.status}
									</span>
								</div>
							</td>
							<td className="px-4 py-3 align-middle text-slate-600">
								{formatUploadDate(doc.upload_date)}
							</td>
							{!isReadOnly && (
								<td className="px-4 py-3 align-middle text-right">
									{!doc.is_read_only && (
										<button
											type="button"
											onClick={(e) => {
												e.stopPropagation();
												onDeleteDocument(doc.id);
											}}
											className="inline-flex items-center justify-center rounded-md p-2 text-red-500 transition-colors hover:bg-red-50 hover:text-red-600"
											aria-label={`Delete ${doc.name}`}
											title="Delete document"
										>
											<Trash2 className="w-4 h-4" />
										</button>
									)}
								</td>
							)}
						</tr>
					);
				})}
			</tbody>
		</table>
	);
}
