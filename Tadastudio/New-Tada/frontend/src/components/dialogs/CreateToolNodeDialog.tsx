import {
	Building2,
	Cloud,
	Code,
	Database,
	FileOutput,
	FileSearch,
	FileText,
	Globe,
	Mail,
	Search,
	Terminal,
	X,
} from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import Button from "@/components/ui/Button";
import { useEscapeKey, useFocusTrap } from "@/hooks/useAccessibility";
import { ARIA_LABELS } from "@/lib/accessibility";
import type { McpServerInfo } from "@/lib/user-settings-api";
import ComingSoonSection from "./ComingSoonSection";
import McpServerSelectionModal from "./McpServerSelectionModal";
import ToolConfigSidebar from "./ToolConfigSidebar";
import ToolTileGrid from "./ToolTileGrid";

interface CreateToolNodeDialogProps {
	isOpen: boolean;
	onClose: () => void;
	onConfirm: (
		toolType: string,
		toolName: string,
		metadata?: {
			provider?: string;
			customConfig?: McpServerInfo;
			shouldClone?: boolean;
		},
	) => void;
	parentAgentName: string;
}

const availableTools = [
	{
		value: "document_search",
		label: "Document Search",
		icon: FileSearch,
		description: "Search through uploaded documents and knowledge bases",
		color: "blue",
	},
	{
		value: "document_retrieve",
		label: "Document Retrieve",
		icon: FileText,
		description: "Retrieve full document content from collections",
		color: "teal",
	},
	{
		value: "database_query",
		label: "Database Query",
		icon: Database,
		description: "Execute SQL queries on connected databases",
		color: "green",
	},
	{
		value: "http_request",
		label: "HTTP Request",
		icon: Globe,
		description: "Make HTTP API calls to external services",
		color: "green",
	},
	{
		value: "web_search",
		label: "Web Search",
		icon: Search,
		description: "Search the web for information",
		color: "plum",
	},
	{
		value: "mcp_server",
		label: "MCP Server",
		icon: Terminal,
		description: "Connect to Model Context Protocol servers",
		color: "cyan",
	},
	{
		value: "file_write",
		label: "File Write",
		icon: FileOutput,
		description: "Write files to a sandboxed workspace directory",
		color: "amber",
	},
];

const comingSoonTools = [
	{
		value: "file_read",
		label: "File Read",
		icon: FileText,
		description: "Read and extract content from files",
		color: "emerald",
		logo: "",
		fallbackEmoji: "📄",
		note: "ISG security audit in progress",
	},
	{
		value: "email_send",
		label: "Email Send",
		icon: Mail,
		description: "Send emails with AI-generated content",
		color: "emerald",
		logo: "",
		fallbackEmoji: "✉️",
	},
	{
		value: "code_executor",
		label: "Code Executor",
		icon: Code,
		description: "Execute Python or JavaScript code dynamically",
		color: "violet",
		logo: "",
		fallbackEmoji: "💻",
	},
	{
		value: "sharepoint",
		label: "SharePoint",
		icon: Building2,
		description: "Access and manage SharePoint documents",
		color: "orange",
		logo: "https://cdn.jsdelivr.net/npm/simple-icons@v9/icons/microsoftsharepoint.svg",
		fallbackEmoji: "📊",
	},
	{
		value: "microsoft_graph",
		label: "Microsoft Graph",
		icon: Cloud,
		description: "Integrate with Microsoft 365 services",
		color: "gray",
		logo: "https://cdn.jsdelivr.net/npm/simple-icons@v9/icons/microsoft.svg",
		fallbackEmoji: "🔷",
	},
	{
		value: "salesforce",
		label: "Salesforce",
		icon: Cloud,
		description: "Connect to Salesforce CRM",
		color: "cyan",
		logo: "https://cdn.jsdelivr.net/npm/simple-icons@v9/icons/salesforce.svg",
		fallbackEmoji: "☁️",
	},
	{
		value: "pdf_generation",
		label: "PDF/Doc Generation",
		icon: FileText,
		description: "Generate PDF and Word documents",
		color: "red",
		logo: "https://cdn.jsdelivr.net/npm/simple-icons@v9/icons/adobeacrobatreader.svg",
		fallbackEmoji: "📄",
	},
];

export default function CreateToolNodeDialog({
	isOpen,
	onClose,
	onConfirm,
	parentAgentName,
}: CreateToolNodeDialogProps) {
	const [selectedTool, setSelectedTool] = useState("document_search");
	const [toolName, setToolName] = useState("Document Search");
	const [showMcpProviderModal, setShowMcpProviderModal] = useState(false);
	const dialogRef = useFocusTrap<HTMLDivElement>(isOpen);
	const [mounted, setMounted] = useState(false);

	useEffect(() => {
		setMounted(true);
		return () => setMounted(false);
	}, []);

	// Handle escape key
	useEscapeKey(onClose, isOpen);

	const handleToolTypeChange = (value: string) => {
		setSelectedTool(value);
		// Update default name based on tool type
		const tool = availableTools.find((t) => t.value === value);
		if (tool) {
			setToolName(tool.label);
		}
	};

	const handleSubmit = (e: React.FormEvent) => {
		e.preventDefault();
		if (selectedTool && toolName.trim()) {
			// For MCP Server, show provider selection modal
			if (selectedTool === "mcp_server") {
				setShowMcpProviderModal(true);
				return;
			}
			onConfirm(selectedTool, toolName.trim());
			// Reset form
			setSelectedTool("document_search");
			setToolName("Document Search");
		}
	};

	// Handle MCP provider selection
	const handleMcpProviderSelect = useCallback(
		(
			provider: string,
			providerToolName: string,
			customConfig?: McpServerInfo,
			shouldClone?: boolean,
		) => {
			onConfirm("mcp_server", providerToolName, {
				provider,
				customConfig,
				shouldClone,
			});
			// Reset form and close modals
			setShowMcpProviderModal(false);
			setSelectedTool("document_search");
			setToolName("Document Search");
			onClose();
		},
		[onConfirm, onClose],
	);

	const handleCloseMcpProviderModal = useCallback(() => {
		setShowMcpProviderModal(false);
	}, []);

	const selectedToolOption = availableTools.find(
		(t) => t.value === selectedTool,
	);

	// Click handler for backdrop
	const handleBackdropClick = useCallback(() => {
		onClose();
	}, [onClose]);

	// Click handler to stop propagation
	const handleDialogClick = useCallback((e: React.MouseEvent) => {
		e.stopPropagation();
	}, []);

	// Change handler for tool name input
	const handleToolNameChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setToolName(e.target.value);
		},
		[],
	);

	if (!isOpen || !mounted) {
		return null;
	}

	return createPortal(
		<div
			className="fixed inset-0 z-[120] flex animate-fadeIn items-center justify-center bg-black/60 backdrop-blur-sm"
			onClick={handleBackdropClick}
			role="presentation"
			aria-hidden="true"
		>
			<div
				className="relative mx-4 flex max-h-[80vh] w-[92vw] max-w-6xl animate-scaleIn flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-[0_30px_80px_rgba(4,7,17,0.15)]"
				onClick={handleDialogClick}
			>
				<div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-orange-500/60" />
				<div
					ref={dialogRef}
					className="flex min-h-0 max-h-[80vh] flex-1 flex-col overflow-hidden"
					role="dialog"
					aria-modal="true"
					aria-labelledby="dialog-title"
					aria-describedby="dialog-description"
				>
					<form
						onSubmit={handleSubmit}
						className="flex h-full min-h-0 flex-col"
					>
						{/* Header — Workflow Management style */}
						<div className="flex shrink-0 items-center justify-between border-b border-slate-200 bg-white px-6 py-5">
							<div className="flex items-center gap-3">
								<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-orange-200 bg-orange-100">
									<FileSearch className="h-5 w-5 text-orange-600" aria-hidden />
								</div>
								<div>
									<h2
										id="dialog-title"
										className="text-lg font-semibold tracking-tight text-slate-900"
									>
										Add Tool
									</h2>
									<p
										id="dialog-description"
										className="mt-0.5 text-sm text-slate-500"
									>
										Extend capabilities of{" "}
										<span className="font-medium text-orange-800">
											{parentAgentName}
										</span>
									</p>
								</div>
							</div>
							<button
								type="button"
								onClick={onClose}
								className="rounded-xl border border-slate-200 bg-white p-2 text-slate-500 transition-colors hover:border-orange-400 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
								aria-label={ARIA_LABELS.CLOSE}
							>
								<X className="h-5 w-5" aria-hidden="true" />
							</button>
						</div>

						{/* Body - Two panel layout */}
						<div className="flex min-h-0 flex-1 flex-col gap-6 overflow-hidden px-6 py-5 md:flex-row">
							{/* Left panel: Tool selection */}
							<div className="flex-1 overflow-y-auto overflow-x-hidden custom-scrollbar space-y-5 min-h-0">
								<ToolTileGrid
									availableTools={availableTools}
									selectedTool={selectedTool}
									onToolSelect={handleToolTypeChange}
								/>

								<ComingSoonSection tools={comingSoonTools} />
							</div>

							{/* Right panel: Configuration sidebar */}
							<ToolConfigSidebar
								selectedToolOption={selectedToolOption}
								toolName={toolName}
								onToolNameChange={handleToolNameChange}
							/>
						</div>

						{/* Footer */}
						<div className="flex shrink-0 gap-3 border-t border-slate-200 bg-white px-6 py-4">
							<Button
								type="button"
								onClick={onClose}
								variant="ghost"
								className="flex-1 !rounded-xl !border !border-slate-200 !bg-white !text-slate-700 hover:!border-orange-400 hover:!text-orange-800"
							>
								Cancel
							</Button>
							<Button
								type="submit"
								className="flex-1 !rounded-[4px] !border !border-orange-500 !bg-orange-500 !text-white hover:!border-orange-600 hover:!bg-orange-600"
							>
								Add Tool
							</Button>
						</div>
					</form>
				</div>
			</div>

			{/* MCP Provider Selection Modal */}
			<McpServerSelectionModal
				isOpen={showMcpProviderModal}
				onClose={handleCloseMcpProviderModal}
				onSelectProvider={handleMcpProviderSelect}
			/>
		</div>,
		document.body,
	);
}
