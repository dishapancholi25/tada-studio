import {
	AlertTriangle,
	ArrowDownCircle,
	Clock,
	Code,
	ExternalLink,
	File,
	FileText,
	Folder,
	Globe,
	HardDrive,
	Layers,
	List,
	Search,
	Table2,
	Terminal,
	Type,
	User,
	Zap,
} from "lucide-react";
import type React from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/cjs/styles/prism";
import { getProviderVisuals } from "../../../../icons/McpProviderIcons";
import JsonViewerEnhanced from "../../../../JsonViewerEnhanced";
import SimpleMarkdown from "../../../../utils/SimpleMarkdown";
import type {
	McpResultType,
	McpServerExecution,
} from "../types/execution.types";
import {
	type AtlassianResource,
	isAtlassianResourcesTool,
	isJiraIssueTool,
	parseAtlassianResources,
	parseJiraIssueResult,
} from "../utils/atlassianResultParser";
import {
	formatCellValue,
	parseDatabricksTableResult,
} from "../utils/databricksResultParser";
import { formatDuration, formatToolName } from "../utils/formatters";
import {
	getNotionResultType,
	type NotionSearchResult,
	parseNotionSearchResults,
} from "../utils/notionResultParser";
import {
	formatFileSize,
	formatSharePointDate,
	isSharePointDriveItemsTool,
	isSharePointFileContentTool,
	isSharePointListSitesTool,
	isSharePointSearchContentTool,
	isSharePointSearchFilesTool,
	isSharePointSiteInfoTool,
	looksLikeMarkdown,
	parseSearchSnippet,
	parseSharePointDriveItems,
	parseSharePointFileContent,
	parseSharePointSearchContent,
	parseSharePointSiteInfo,
	parseSharePointSites,
	type SharePointSearchResult,
} from "../utils/sharepointResultParser";
import {
	formatFileSize as formatOneDriveFileSize,
	formatSharePointDate as formatOneDriveDate,
	isOneDriveDriveListTool,
	isOneDriveFileContentTool,
	isOneDriveItemsListTool,
	isOneDriveMetadataTool,
	looksLikeMarkdown as oneDriveLooksLikeMarkdown,
	parseOneDriveDrives,
	parseOneDriveFileContent,
	parseOneDriveItemMetadata,
	parseOneDriveItems,
} from "../utils/oneDriveResultParser";
import {
	getFabricItemTypeIcon,
	groupFabricItemsByType,
	isFabricListItemsTool,
	parseFabricListItems,
	pluralizeFabricType,
} from "../utils/fabricResultParser";
import { BaseRenderer, BaseRendererProps } from "./BaseRenderer";

const SQL_PARAMETER_KEYS = new Set(["query", "statement"]);
const SQL_PROVIDERS = new Set(["databricks"]);

const MARKDOWN_PARAMETER_KEYS = new Set(["description"]);
const MARKDOWN_PROVIDERS = new Set(["atlassian"]);

const sqlHighlightStyle = {
	...vscDarkPlus,
	'pre[class*="language-"]': {
		...vscDarkPlus['pre[class*="language-"]'],
		background: "transparent",
		margin: 0,
		padding: 0,
		fontSize: "0.8125rem",
		lineHeight: "1.6",
	},
	'code[class*="language-"]': {
		...vscDarkPlus['code[class*="language-"]'],
		background: "transparent",
		fontSize: "0.8125rem",
	},
};

export class McpServerRenderer extends BaseRenderer<McpServerExecution> {
	state = {
		expandedResults: new Set<number>(),
	};

	getViewModes() {
		const { executions, selectedIndex } = this.props;
		const currentExecution = executions[selectedIndex];

		const modes = [
			{ key: "overview", label: "Overview", icon: <Zap className="w-4 h-4" /> },
		];

		// Add result-specific views based on detected result type
		const isSpSearch =
			currentExecution?.provider === "sharepoint" &&
			(isSharePointSearchContentTool(currentExecution.tool) ||
				isSharePointSearchFilesTool(currentExecution.tool));
		const spSearchItems =
			currentExecution?.result?.results ?? currentExecution?.result?.files;
		if (isSpSearch && Array.isArray(spSearchItems) && spSearchItems.length > 0) {
			const total = currentExecution.result.total ?? spSearchItems.length;
			modes.push({
				key: "results",
				label: `Results (${spSearchItems.length} of ${total.toLocaleString()})`,
				icon: <Search className="w-4 h-4" />,
			});
		} else if (
			currentExecution?.resultType === "search" &&
			currentExecution.result?.results?.length
		) {
			modes.push({
				key: "results",
				label: `Results (${currentExecution.result.results.length})`,
				icon: <Search className="w-4 h-4" />,
			});
		}

		// Add Table tab for table results with columns/rows (Unity Catalog or SQL MCP format)
		if (
			currentExecution?.resultType === "table" &&
			(
				(currentExecution?.result?.columns && currentExecution?.result?.rows) ||
				(currentExecution?.result?.manifest?.schema?.columns && currentExecution?.result?.result?.data_array)
			)
		) {
			const rowCount = currentExecution.result.rows?.length
				?? currentExecution.result.result?.data_array?.length
				?? 0;
			modes.push({
				key: "table",
				label: `Table (${rowCount} row${rowCount !== 1 ? "s" : ""})`,
				icon: <Table2 className="w-4 h-4" />,
			});
		}

		// Always include Input and Raw Data
		modes.push({
			key: "input",
			label: "Input",
			icon: <ArrowDownCircle className="w-4 h-4" />,
		});
		modes.push({
			key: "raw",
			label: "Raw Data",
			icon: <FileText className="w-4 h-4" />,
		});

		return modes;
	}

	renderViewMode(mode: string, execution: McpServerExecution) {
		switch (mode) {
			case "overview":
				return this.renderOverview(execution);
			case "results":
				return this.renderResults(execution);
			case "table":
				return this.renderTableView(execution);
			case "input":
				return this.renderInput(execution);
			default:
				return (
					<div className="rounded-2xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/40 p-5 shadow-[0_20px_55px_rgba(0,0,0,0.55)]">
						<JsonViewerEnhanced data={execution} />
					</div>
				);
		}
	}

	renderOverview(execution: McpServerExecution) {
		return (
			<div className="space-y-5">
				{/* Tool Info Card */}
				{this.renderToolInfoCard(execution)}

				{/* Result Warning */}
				{execution.resultWarning &&
					this.renderWarningCard(execution.resultWarning)}

				{/* Input Summary */}
				{this.renderInputSummary(execution)}

				{/* Results Preview */}
				{this.renderResultsPreview(execution)}
			</div>
		);
	}

	renderToolInfoCard(execution: McpServerExecution) {
		const providerVisuals = getProviderVisuals(execution.provider || "generic");
		const ProviderIcon = providerVisuals.icon;

		return (
			<div className="rounded-2xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/40 p-5 shadow-[0_20px_55px_rgba(0,0,0,0.55)]">
				{/* Section Label */}
				<div className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)] font-semibold mb-4">
					Tool Execution
				</div>

				{/* Tool Identity */}
				<div className="flex items-center gap-4">
					<div
						className="h-14 w-14 rounded-2xl border flex items-center justify-center flex-shrink-0"
						style={{
							backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.12)`,
							borderColor: `rgba(${providerVisuals.colorRgb}, 0.35)`,
							boxShadow: `0 0 30px rgba(${providerVisuals.colorRgb}, 0.25)`,
						}}
					>
						<ProviderIcon
							className="w-7 h-7"
							style={{ color: providerVisuals.color }}
						/>
					</div>

					<div className="flex-1 min-w-0">
						<h3 className="text-xl font-semibold text-slate-900 truncate">
							{formatToolName(execution.tool)}
						</h3>
						<div className="flex items-center gap-2 mt-0.5 flex-wrap">
							<span className="text-xs font-mono text-[color:var(--color-text-muted)]">
								({execution.tool})
							</span>
							<span className="text-xs text-[color:var(--color-text-muted)]">
								•
							</span>
							<span className="text-xs text-[color:var(--color-text-muted)]">
								{providerVisuals.label} MCP
							</span>
						</div>
					</div>

					{/* Duration Badge */}
					{execution.duration && (
						<div
							className="px-3 py-1.5 rounded-full text-xs font-medium border flex-shrink-0"
							style={{
								backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.1)`,
								borderColor: `rgba(${providerVisuals.colorRgb}, 0.3)`,
								color: providerVisuals.color,
							}}
						>
							<div className="flex items-center gap-1.5">
								<Clock className="w-3.5 h-3.5" />
								{formatDuration(execution.duration)}
							</div>
						</div>
					)}
				</div>

				{/* Result Type Badge */}
				{execution.resultType && execution.resultType !== "raw" && (
					<div className="mt-4 pt-4 border-t border-[color:var(--color-border)]/40">
						<div className="flex items-center gap-2">
							<span className="text-xs text-[color:var(--color-text-muted)]">
								Result type:
							</span>
							<span
								className="px-2 py-0.5 rounded text-xs font-medium border"
								style={{
									backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.1)`,
									borderColor: `rgba(${providerVisuals.colorRgb}, 0.25)`,
									color: providerVisuals.color,
								}}
							>
								{this.getResultTypeIcon(execution.resultType)}
								<span className="ml-1.5">{execution.resultType}</span>
							</span>
						</div>
					</div>
				)}
			</div>
		);
	}

	getResultTypeIcon(resultType: McpResultType): React.ReactNode {
		switch (resultType) {
			case "search":
				return <Search className="w-3 h-3 inline" />;
			case "content":
				return <FileText className="w-3 h-3 inline" />;
			case "table":
				return <Table2 className="w-3 h-3 inline" />;
			case "list":
				return <List className="w-3 h-3 inline" />;
			case "text":
				return <Type className="w-3 h-3 inline" />;
			case "object":
				return <Code className="w-3 h-3 inline" />;
			default:
				return null;
		}
	}

	renderWarningCard(warning: string) {
		return (
			<div className="rounded-2xl border border-amber-500/30 bg-amber-500/5 p-4 shadow-[0_20px_55px_rgba(0,0,0,0.55)]">
				<div className="flex items-center gap-3">
					<div className="p-2 rounded-xl bg-amber-500/10 border border-amber-500/20">
						<AlertTriangle className="w-4 h-4 text-amber-400" />
					</div>
					<div>
						<p className="text-sm text-amber-300">{warning}</p>
					</div>
				</div>
			</div>
		);
	}

	renderInputSummary(execution: McpServerExecution) {
		if (!execution.arguments || Object.keys(execution.arguments).length === 0)
			return null;

		const providerVisuals = getProviderVisuals(execution.provider || "generic");
		const isSqlProvider = SQL_PROVIDERS.has(execution.provider || "");
		const isMarkdownProvider = MARKDOWN_PROVIDERS.has(execution.provider || "");

		return (
			<div className="rounded-2xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/40 p-5 shadow-[0_20px_55px_rgba(0,0,0,0.55)]">
				<div className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)] font-semibold mb-4">
					Input Parameters
				</div>

				<div className="grid gap-3">
					{Object.entries(execution.arguments).map(([key, value]) => {
						const stringValue = typeof value === "string" ? value : JSON.stringify(value);
						const isSql = isSqlProvider && SQL_PARAMETER_KEYS.has(key);
						const isMarkdown = isMarkdownProvider && MARKDOWN_PARAMETER_KEYS.has(key) && typeof value === "string" && value.length > 100;

						if (isSql) {
							return (
								<div
									key={key}
									className="rounded-xl bg-[color:var(--color-bg-secondary)] overflow-hidden"
								>
									<div className="flex items-center gap-2 px-3 pt-3 pb-1">
										<span className="text-xs font-mono text-[color:var(--color-text-muted)]">
											{key}
										</span>
										<span
											className="px-1.5 py-0.5 rounded text-[10px] font-medium border"
											style={{
												backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.1)`,
												borderColor: `rgba(${providerVisuals.colorRgb}, 0.25)`,
												color: providerVisuals.color,
											}}
										>
											SQL
										</span>
									</div>
									<div className="px-3 pb-3">
										<SyntaxHighlighter
											language="sql"
											style={sqlHighlightStyle}
											wrapLines
											wrapLongLines
											customStyle={{
												margin: 0,
												background: "transparent",
											}}
										>
											{stringValue}
										</SyntaxHighlighter>
									</div>
								</div>
							);
						}

						if (isMarkdown) {
							return (
								<div
									key={key}
									className="rounded-xl bg-[color:var(--color-bg-secondary)] overflow-hidden"
								>
									<div className="px-3 pt-3 pb-1">
										<span className="text-xs font-mono text-[color:var(--color-text-muted)]">
											{key}
										</span>
									</div>
									<div className="px-3 pb-3 max-h-80 overflow-y-auto custom-scrollbar">
										<SimpleMarkdown
											content={stringValue}
											className="text-sm text-[color:var(--color-text-secondary)] leading-relaxed"
											variant="light"
										/>
									</div>
								</div>
							);
						}

						return (
							<div
								key={key}
								className="flex items-start gap-3 p-3 rounded-xl bg-[color:var(--color-bg-secondary)]"
							>
								<span className="text-xs font-mono text-[color:var(--color-text-muted)] min-w-[100px] flex-shrink-0">
									{key}
								</span>
								<span className="text-sm text-slate-700 font-medium flex-1 break-all">
									{stringValue}
								</span>
							</div>
						);
					})}
				</div>
			</div>
		);
	}

	renderInput(execution: McpServerExecution) {
		return (
			<div className="space-y-5">
				{/* Arguments */}
				{this.renderInputSummary(execution)}

				{/* Action/Target Details */}
				<div className="rounded-2xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/40 p-5 shadow-[0_20px_55px_rgba(0,0,0,0.55)]">
					<div className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)] font-semibold mb-4">
						Execution Details
					</div>

					<div className="space-y-3">
						<div className="flex items-center gap-3 p-3 rounded-xl bg-[color:var(--color-bg-secondary)]">
							<span className="text-xs font-mono text-[color:var(--color-text-muted)] min-w-[100px]">
								action
							</span>
							<span className="text-sm text-slate-700 font-medium">
								{execution.action}
							</span>
						</div>
						<div className="flex items-center gap-3 p-3 rounded-xl bg-[color:var(--color-bg-secondary)]">
							<span className="text-xs font-mono text-[color:var(--color-text-muted)] min-w-[100px]">
								target
							</span>
							<span className="text-sm text-slate-700 font-medium">
								{execution.target}
							</span>
						</div>
						{execution.server && (
							<div className="flex items-center gap-3 p-3 rounded-xl bg-[color:var(--color-bg-secondary)]">
								<span className="text-xs font-mono text-[color:var(--color-text-muted)] min-w-[100px]">
									server
								</span>
								<span className="text-sm text-slate-700 font-medium truncate">
									{execution.server}
								</span>
							</div>
						)}
						{execution.connection_type && (
							<div className="flex items-center gap-3 p-3 rounded-xl bg-[color:var(--color-bg-secondary)]">
								<span className="text-xs font-mono text-[color:var(--color-text-muted)] min-w-[100px]">
									connection
								</span>
								<span className="text-sm text-slate-700 font-medium">
									{execution.connection_type}
								</span>
							</div>
						)}
					</div>
				</div>

				{/* Full Arguments as JSON */}
				{execution.arguments && Object.keys(execution.arguments).length > 0 && (
					<div className="rounded-2xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/40 p-5 shadow-[0_20px_55px_rgba(0,0,0,0.55)]">
						<div className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)] font-semibold mb-4">
							Raw Arguments
						</div>
						<div className="rounded-xl bg-[color:var(--color-bg-secondary)] p-4">
							<JsonViewerEnhanced data={execution.arguments} />
						</div>
					</div>
				)}
			</div>
		);
	}

	renderResultsPreview(execution: McpServerExecution) {
		if (!execution.result) return null;

		const providerVisuals = getProviderVisuals(execution.provider || "generic");

		// Atlassian-specific rendering
		if (execution.provider === "atlassian") {
			if (isAtlassianResourcesTool(execution.tool) && execution.resultType === "list") {
				return this.renderAtlassianResourcesList(execution, providerVisuals);
			}
			if (isJiraIssueTool(execution.tool) && execution.resultType === "object") {
				return this.renderJiraIssueResult(execution, providerVisuals);
			}
		}

		// SharePoint-specific rendering
		if (execution.provider === "sharepoint") {
			if (isSharePointListSitesTool(execution.tool)) {
				return this.renderSharePointSitesList(execution, providerVisuals);
			}
			if (isSharePointSiteInfoTool(execution.tool)) {
				return this.renderSharePointSiteInfo(execution, providerVisuals);
			}
			if (isSharePointDriveItemsTool(execution.tool)) {
				return this.renderSharePointDriveItems(execution, providerVisuals);
			}
			if (isSharePointFileContentTool(execution.tool)) {
				return this.renderSharePointFileContent(execution, providerVisuals);
			}
			if (
				isSharePointSearchContentTool(execution.tool) ||
				isSharePointSearchFilesTool(execution.tool)
			) {
				return this.renderSharePointSearchPreview(execution, providerVisuals);
			}
		}

		// OneDrive-specific rendering
		if (execution.provider === "onedrive") {
			if (isOneDriveItemsListTool(execution.tool)) {
				return this.renderOneDriveItemsList(execution, providerVisuals);
			}
			if (isOneDriveDriveListTool(execution.tool)) {
				return this.renderOneDriveDrivesList(execution, providerVisuals);
			}
			if (isOneDriveFileContentTool(execution.tool)) {
				return this.renderOneDriveFileContent(execution, providerVisuals);
			}
			if (isOneDriveMetadataTool(execution.tool)) {
				return this.renderOneDriveItemMetadata(execution, providerVisuals);
			}
		}

		// Fabric-specific rendering
		if (execution.provider === "fabric") {
			if (isFabricListItemsTool(execution.tool)) {
				return this.renderFabricItemsList(execution, providerVisuals);
			}
		}

		// Smart rendering based on result type
		switch (execution.resultType) {
			case "search":
				return this.renderSearchResultsPreview(execution, providerVisuals);
			case "content":
				return this.renderContentResult(execution, providerVisuals);
			case "text":
				return this.renderTextResult(execution, providerVisuals);
			case "list":
				return this.renderListResult(execution, providerVisuals);
			case "table":
				return this.renderTableResultPreview(execution, providerVisuals);
			case "object":
			default:
				return this.renderGenericResult(execution, providerVisuals);
		}
	}

	renderTableResultPreview(
		execution: McpServerExecution,
		providerVisuals: any,
	) {
		const tableData = parseDatabricksTableResult(execution.result);
		if (!tableData) {
			return this.renderGenericResult(execution, providerVisuals);
		}

		const previewRows = tableData.rows.slice(0, 5);

		return (
			<div className="rounded-2xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/40 overflow-hidden shadow-[0_20px_55px_rgba(0,0,0,0.55)]">
				<div className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)] font-semibold px-5 pt-5 pb-3">
					Result Preview
				</div>

				<div className="overflow-x-auto custom-scrollbar">
					<table className="w-full text-sm">
						<thead>
							<tr
								style={{
									backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.08)`,
								}}
							>
								{tableData.columns.map((col) => (
									<th
										key={col}
										className="px-4 py-2.5 text-left text-xs font-semibold capitalize tracking-wider whitespace-nowrap"
										style={{
											color: providerVisuals.color,
											borderBottom: `1px solid rgba(${providerVisuals.colorRgb}, 0.2)`,
										}}
									>
										{col}
									</th>
								))}
							</tr>
						</thead>
						<tbody>
							{previewRows.map((row, rowIdx) => (
								<tr
									key={rowIdx}
									className={
										rowIdx % 2 === 0
											? "bg-transparent"
											: "bg-[color:var(--color-surface)]/20"
									}
								>
									{row.map((cell: any, cellIdx: number) => (
										<td
											key={cellIdx}
											className="px-4 py-2.5 text-[color:var(--color-text-secondary)] whitespace-nowrap font-mono text-xs"
										>
											{formatCellValue(cell)}
										</td>
									))}
								</tr>
							))}
						</tbody>
					</table>
				</div>

				{tableData.row_count > 5 && (
					<div className="px-5 py-3 border-t border-[color:var(--color-border)]/40 text-xs text-[color:var(--color-text-muted)]">
						Showing 5 of {tableData.row_count} rows — view Table
						tab for full data
					</div>
				)}

				{tableData.is_truncated && (
					<div className="px-5 py-2 border-t border-amber-500/20 bg-amber-500/5 text-xs text-amber-300">
						Results were truncated by the server
					</div>
				)}
			</div>
		);
	}

	renderTableView(execution: McpServerExecution) {
		const tableData = parseDatabricksTableResult(execution.result);
		if (!tableData) {
			return this.renderGenericResult(
				execution,
				getProviderVisuals(execution.provider || "generic"),
			);
		}

		const providerVisuals = getProviderVisuals(
			execution.provider || "databricks",
		);

		return (
			<div className="space-y-4">
				{/* Table Stats Bar */}
				<div
					className="rounded-2xl border p-4"
					style={{
						borderColor: `rgba(${providerVisuals.colorRgb}, 0.3)`,
						backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.05)`,
					}}
				>
					<div className="flex items-center justify-between">
						<div className="flex items-center gap-3">
							<div
								className="p-2 rounded-xl border"
								style={{
									backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.1)`,
									borderColor: `rgba(${providerVisuals.colorRgb}, 0.2)`,
								}}
							>
								<Table2
									className="w-5 h-5"
									style={{ color: providerVisuals.color }}
								/>
							</div>
							<div
								className="font-medium"
								style={{ color: providerVisuals.color }}
							>
								{tableData.row_count} row
								{tableData.row_count !== 1 ? "s" : ""} ×{" "}
								{tableData.columns.length} column
								{tableData.columns.length !== 1 ? "s" : ""}
							</div>
						</div>
						{tableData.is_truncated && (
							<span className="px-3 py-1 text-[11px] font-medium rounded-full text-amber-700 border border-amber-400/40 bg-amber-500/10">
								Truncated
							</span>
						)}
					</div>
				</div>

				{/* Table */}
				<div className="rounded-2xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/40 overflow-hidden shadow-[0_20px_55px_rgba(0,0,0,0.55)]">
					<div className="overflow-x-auto custom-scrollbar">
						<table className="w-full text-sm">
							<thead>
								<tr
									style={{
										backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.08)`,
									}}
								>
									{tableData.columns.map((col) => (
										<th
											key={col}
											className="px-4 py-3 text-left text-xs font-semibold capitalize tracking-wider whitespace-nowrap"
											style={{
												color: providerVisuals.color,
												borderBottom: `1px solid rgba(${providerVisuals.colorRgb}, 0.2)`,
											}}
										>
											{col}
										</th>
									))}
								</tr>
							</thead>
							<tbody>
								{tableData.rows.map((row, rowIdx) => (
									<tr
										key={rowIdx}
										className={
											rowIdx % 2 === 0
												? "bg-transparent"
												: "bg-[color:var(--color-surface)]/20"
										}
									>
										{row.map((cell: any, cellIdx: number) => (
											<td
												key={cellIdx}
												className="px-4 py-3 text-[color:var(--color-text-secondary)] whitespace-nowrap font-mono text-xs"
											>
												{formatCellValue(cell)}
											</td>
										))}
									</tr>
								))}
							</tbody>
						</table>
					</div>
				</div>
			</div>
		);
	}

	renderResults(execution: McpServerExecution) {
		if (!execution.result) {
			return (
				<div className="flex-1 flex items-center justify-center py-12">
					<div className="text-center">
						<Search className="w-10 h-10 text-[color:var(--color-text-muted)] mx-auto mb-3" />
						<p className="text-[color:var(--color-text-muted)]">
							No results available
						</p>
					</div>
				</div>
			);
		}

		const providerVisuals = getProviderVisuals(execution.provider || "generic");

		if (
			execution.provider === "sharepoint" &&
			(isSharePointSearchContentTool(execution.tool) ||
				isSharePointSearchFilesTool(execution.tool))
		) {
			return this.renderSharePointSearchResults(execution, providerVisuals);
		}

		if (execution.resultType === "search" && execution.provider === "notion") {
			return this.renderNotionSearchResults(execution, providerVisuals);
		}

		// Generic search results
		if (execution.resultType === "search") {
			return this.renderGenericSearchResults(execution, providerVisuals);
		}

		// Fallback to generic result display
		return this.renderGenericResult(execution, providerVisuals);
	}

	renderNotionSearchResults(
		execution: McpServerExecution,
		providerVisuals: any,
	) {
		const results = parseNotionSearchResults(execution.result);

		return (
			<div className="space-y-4">
				{/* Results Count Header */}
				<div
					className="rounded-2xl border p-4"
					style={{
						borderColor: `rgba(${providerVisuals.colorRgb}, 0.3)`,
						backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.05)`,
					}}
				>
					<div className="flex items-center gap-3">
						<div
							className="p-2 rounded-xl border"
							style={{
								backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.1)`,
								borderColor: `rgba(${providerVisuals.colorRgb}, 0.2)`,
							}}
						>
							<Search
								className="w-5 h-5"
								style={{ color: providerVisuals.color }}
							/>
						</div>
						<div>
							<div
								className="font-medium"
								style={{ color: providerVisuals.color }}
							>
								{results.length} page{results.length !== 1 ? "s" : ""} found
							</div>
							{execution.arguments?.query && (
								<div className="text-xs text-[color:var(--color-text-muted)]">
									for &quot;{execution.arguments.query}&quot;
								</div>
							)}
						</div>
					</div>
				</div>

				{/* Result Cards */}
				<div className="space-y-3">
					{results.map((result, idx) =>
						this.renderNotionResultCard(result, idx, providerVisuals),
					)}
				</div>
			</div>
		);
	}

	renderNotionResultCard(
		result: NotionSearchResult,
		idx: number,
		providerVisuals: any,
	) {
		return (
			<div
				key={result.id || idx}
				className="rounded-2xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/40 p-5 hover:border-opacity-100 transition-all group shadow-[0_20px_55px_rgba(0,0,0,0.55)]"
				style={
					{
						"--hover-border-color": providerVisuals.color,
					} as React.CSSProperties
				}
				onMouseEnter={(e) => {
					e.currentTarget.style.borderColor = `rgba(${providerVisuals.colorRgb}, 0.4)`;
				}}
				onMouseLeave={(e) => {
					e.currentTarget.style.borderColor = "";
				}}
			>
				{/* Title & Link */}
				<div className="flex items-start justify-between gap-4 mb-3">
					<div className="flex items-center gap-3 min-w-0">
						<div
							className="p-2 rounded-lg flex-shrink-0"
							style={{
								backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.1)`,
							}}
						>
							<FileText
								className="w-4 h-4"
								style={{ color: providerVisuals.color }}
							/>
						</div>
						<div className="min-w-0">
							<h4
								className="text-base font-medium text-slate-900 group-hover:transition-colors truncate"
								style={
									{
										"--hover-color": providerVisuals.color,
									} as React.CSSProperties
								}
							>
								{result.title}
							</h4>
							<span className="text-xs text-[color:var(--color-text-muted)]">
								{result.type}
							</span>
						</div>
					</div>

					{result.url && (
						<a
							href={result.url}
							target="_blank"
							rel="noopener noreferrer"
							className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors flex-shrink-0"
							style={{
								color: providerVisuals.color,
								backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.1)`,
							}}
							onMouseEnter={(e) => {
								e.currentTarget.style.backgroundColor = `rgba(${providerVisuals.colorRgb}, 0.2)`;
							}}
							onMouseLeave={(e) => {
								e.currentTarget.style.backgroundColor = `rgba(${providerVisuals.colorRgb}, 0.1)`;
							}}
						>
							<ExternalLink className="w-3.5 h-3.5" />
							Open in Notion
						</a>
					)}
				</div>

				{/* Highlight/Snippet */}
				{result.highlight && (
					<p className="text-sm text-[color:var(--color-text-secondary)] leading-relaxed mb-3 line-clamp-2">
						{result.highlight}
					</p>
				)}

				{/* Timestamp */}
				{result.timestamp && (
					<div className="flex items-center gap-2 text-xs text-[color:var(--color-text-muted)]">
						<Clock className="w-3.5 h-3.5" />
						{result.timestamp}
					</div>
				)}
			</div>
		);
	}

	renderGenericSearchResults(
		execution: McpServerExecution,
		providerVisuals: any,
	) {
		const results = execution.result?.results || [];

		return (
			<div className="space-y-4">
				{/* Results Count Header */}
				<div
					className="rounded-2xl border p-4"
					style={{
						borderColor: `rgba(${providerVisuals.colorRgb}, 0.3)`,
						backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.05)`,
					}}
				>
					<div className="flex items-center gap-3">
						<div
							className="p-2 rounded-xl border"
							style={{
								backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.1)`,
								borderColor: `rgba(${providerVisuals.colorRgb}, 0.2)`,
							}}
						>
							<Search
								className="w-5 h-5"
								style={{ color: providerVisuals.color }}
							/>
						</div>
						<div
							className="font-medium"
							style={{ color: providerVisuals.color }}
						>
							{results.length} result{results.length !== 1 ? "s" : ""} found
						</div>
					</div>
				</div>

				{/* Result Cards */}
				<div className="space-y-3">
					{results.map((result: any, idx: number) => (
						<div
							key={result.id || idx}
							className="rounded-2xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/40 p-5 shadow-[0_20px_55px_rgba(0,0,0,0.55)]"
						>
							{result.title && (
								<h4 className="text-base font-medium text-slate-900 mb-2">
									{result.title}
								</h4>
							)}
							{result.url && (
								<a
									href={result.url}
									target="_blank"
									rel="noopener noreferrer"
									className="text-xs flex items-center gap-1 mb-2"
									style={{ color: providerVisuals.color }}
								>
									<ExternalLink className="w-3 h-3" />
									{result.url}
								</a>
							)}
							{(result.snippet || result.highlight || result.content) && (
								<p className="text-sm text-[color:var(--color-text-secondary)] leading-relaxed">
									{result.snippet || result.highlight || result.content}
								</p>
							)}
						</div>
					))}
				</div>
			</div>
		);
	}

	renderSearchResultsPreview(
		execution: McpServerExecution,
		providerVisuals: any,
	) {
		const resultCount = execution.result?.results?.length || 0;

		return (
			<div className="rounded-2xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/40 p-5 shadow-[0_20px_55px_rgba(0,0,0,0.55)]">
				<div className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)] font-semibold mb-4">
					Results Preview
				</div>

				<div
					className="rounded-xl p-4 border"
					style={{
						backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.05)`,
						borderColor: `rgba(${providerVisuals.colorRgb}, 0.2)`,
					}}
				>
					<div className="flex items-center gap-3">
						<Search
							className="w-5 h-5"
							style={{ color: providerVisuals.color }}
						/>
						<div>
							<div className="font-medium text-slate-900">
								{resultCount} result{resultCount !== 1 ? "s" : ""} found
							</div>
							<div className="text-xs text-[color:var(--color-text-muted)]">
								View the Results tab for details
							</div>
						</div>
					</div>
				</div>
			</div>
		);
	}

	renderContentResult(execution: McpServerExecution, providerVisuals: any) {
		const content =
			execution.result?.content ||
			execution.result?.body ||
			execution.result?.text ||
			"";

		return (
			<div className="rounded-2xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/40 p-5 shadow-[0_20px_55px_rgba(0,0,0,0.55)]">
				<div className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)] font-semibold mb-4">
					Content
				</div>
				<div className="rounded-xl bg-[color:var(--color-bg-secondary)] p-4">
					<pre className="text-sm text-[color:var(--color-text-secondary)] whitespace-pre-wrap font-sans leading-relaxed">
						{typeof content === "string"
							? content
							: JSON.stringify(content, null, 2)}
					</pre>
				</div>
			</div>
		);
	}

	renderTextResult(execution: McpServerExecution, providerVisuals: any) {
		return (
			<div className="rounded-2xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/40 p-5 shadow-[0_20px_55px_rgba(0,0,0,0.55)]">
				<div className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)] font-semibold mb-4">
					Result
				</div>
				<div className="rounded-xl bg-[color:var(--color-bg-secondary)] p-4">
					<pre className="text-sm text-[color:var(--color-text-secondary)] whitespace-pre-wrap font-sans leading-relaxed">
						{execution.result}
					</pre>
				</div>
			</div>
		);
	}

	renderListResult(execution: McpServerExecution, providerVisuals: any) {
		const items = Array.isArray(execution.result) ? execution.result : [];

		return (
			<div className="rounded-2xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/40 p-5 shadow-[0_20px_55px_rgba(0,0,0,0.55)]">
				<div className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)] font-semibold mb-4">
					Results ({items.length} items)
				</div>
				<div className="space-y-2 max-h-96 overflow-y-auto custom-scrollbar">
					{items.slice(0, 20).map((item: any, idx: number) => (
						<div
							key={idx}
							className="rounded-xl bg-[color:var(--color-bg-secondary)] p-3"
						>
							{typeof item === "object" ? (
								<JsonViewerEnhanced data={item} />
							) : (
								<span className="text-sm text-[color:var(--color-text-secondary)]">
									{String(item)}
								</span>
							)}
						</div>
					))}
					{items.length > 20 && (
						<div className="text-center text-xs text-[color:var(--color-text-muted)] py-2">
							+{items.length - 20} more items
						</div>
					)}
				</div>
			</div>
		);
	}

	renderGenericResult(execution: McpServerExecution, providerVisuals: any) {
		return (
			<div className="rounded-2xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/40 p-5 shadow-[0_20px_55px_rgba(0,0,0,0.55)]">
				<div className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)] font-semibold mb-4">
					Result
				</div>
				<div className="rounded-xl bg-[color:var(--color-bg-secondary)] p-4">
					<JsonViewerEnhanced data={execution.result} />
				</div>
			</div>
		);
	}

	renderAtlassianResourcesList(
		execution: McpServerExecution,
		providerVisuals: any,
	) {
		const resources = parseAtlassianResources(execution.result);

		if (resources.length === 0) {
			return this.renderGenericResult(execution, providerVisuals);
		}

		return (
			<div className="space-y-4">
				{/* Resources Count Header */}
				<div
					className="rounded-2xl border p-4"
					style={{
						borderColor: `rgba(${providerVisuals.colorRgb}, 0.3)`,
						backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.05)`,
					}}
				>
					<div className="flex items-center gap-3">
						<div
							className="p-2 rounded-xl border"
							style={{
								backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.1)`,
								borderColor: `rgba(${providerVisuals.colorRgb}, 0.2)`,
							}}
						>
							<ExternalLink
								className="w-5 h-5"
								style={{ color: providerVisuals.color }}
							/>
						</div>
						<div
							className="font-medium"
							style={{ color: providerVisuals.color }}
						>
							{resources.length} accessible resource{resources.length !== 1 ? "s" : ""}
						</div>
					</div>
				</div>

				{/* Resource Cards */}
				<div className="space-y-3">
					{resources.map((resource, idx) =>
						this.renderAtlassianResourceCard(resource, idx, providerVisuals),
					)}
				</div>
			</div>
		);
	}

	renderAtlassianResourceCard(
		resource: AtlassianResource,
		idx: number,
		providerVisuals: any,
	) {
		return (
			<div
				key={resource.id || idx}
				className="rounded-2xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/40 p-5 shadow-[0_20px_55px_rgba(0,0,0,0.55)]"
			>
				{/* Name & URL */}
				<div className="flex items-center gap-3 mb-3">
					{resource.avatarUrl && (
						<img
							src={resource.avatarUrl}
							alt=""
							className="w-8 h-8 rounded-lg flex-shrink-0"
						/>
					)}
					<div className="min-w-0 flex-1">
						<h4 className="text-base font-medium text-slate-900 truncate">
							{resource.name}
						</h4>
						{resource.url && (
							<a
								href={resource.url}
								target="_blank"
								rel="noopener noreferrer"
								className="text-xs flex items-center gap-1 mt-0.5"
								style={{ color: providerVisuals.color }}
							>
								<ExternalLink className="w-3 h-3" />
								{resource.url}
							</a>
						)}
					</div>
				</div>

				{/* Scopes */}
				{resource.scopes.length > 0 && (
					<div className="flex flex-wrap gap-1.5">
						{resource.scopes.map((scope) => (
							<span
								key={scope}
								className="px-2 py-0.5 rounded-md text-[11px] font-mono border"
								style={{
									backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.08)`,
									borderColor: `rgba(${providerVisuals.colorRgb}, 0.2)`,
									color: `rgba(${providerVisuals.colorRgb}, 0.85)`,
								}}
							>
								{scope}
							</span>
						))}
					</div>
				)}
			</div>
		);
	}

	renderJiraIssueResult(
		execution: McpServerExecution,
		providerVisuals: any,
	) {
		const issue = parseJiraIssueResult(execution.result);
		if (!issue) {
			return this.renderGenericResult(execution, providerVisuals);
		}

		return (
			<div className="rounded-2xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/40 p-5 shadow-[0_20px_55px_rgba(0,0,0,0.55)]">
				<div className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)] font-semibold mb-4">
					Jira Issue Created
				</div>

				<div className="flex items-center gap-4">
					{/* Issue Key Badge */}
					<div
						className="px-4 py-2.5 rounded-xl border text-lg font-bold"
						style={{
							backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.12)`,
							borderColor: `rgba(${providerVisuals.colorRgb}, 0.35)`,
							color: providerVisuals.color,
							boxShadow: `0 0 20px rgba(${providerVisuals.colorRgb}, 0.15)`,
						}}
					>
						{issue.key}
					</div>

					<div className="flex-1 min-w-0">
						{/* Summary from arguments */}
						{execution.arguments?.summary && (
							<p className="text-sm text-slate-700 font-medium line-clamp-2">
								{execution.arguments.summary}
							</p>
						)}
						<div className="flex items-center gap-3 mt-1.5">
							{issue.id && (
								<span className="text-xs text-[color:var(--color-text-muted)] font-mono">
									ID: {issue.id}
								</span>
							)}
							{execution.arguments?.issueTypeName && (
								<span
									className="px-2 py-0.5 rounded text-[11px] font-medium border"
									style={{
										backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.1)`,
										borderColor: `rgba(${providerVisuals.colorRgb}, 0.25)`,
										color: providerVisuals.color,
									}}
								>
									{execution.arguments.issueTypeName}
								</span>
							)}
							{execution.arguments?.projectKey && (
								<span className="text-xs text-[color:var(--color-text-muted)]">
									Project: {execution.arguments.projectKey}
								</span>
							)}
						</div>
					</div>
				</div>
			</div>
		);
	}

	renderEmptyState() {
		const providerVisuals = getProviderVisuals("generic");

		return (
			<div className="flex-1 flex items-center justify-center py-12">
				<div className="text-center">
					<div className="p-5 rounded-2xl bg-[color:var(--color-surface)]/30 border border-[color:var(--color-border)]/40 inline-block mb-5">
						<Terminal className="w-10 h-10 text-[color:var(--color-text-muted)]" />
					</div>
					<h3 className="text-lg font-medium text-slate-900 mb-2">
						No Execution Data
					</h3>
					<p className="text-sm text-[color:var(--color-text-muted)] max-w-sm">
						This MCP tool hasn&apos;t been executed yet
					</p>
				</div>
			</div>
		);
	}

	// ─── SharePoint-specific renderers ───────────────────────────────────

	renderSharePointSitesList(
		execution: McpServerExecution,
		providerVisuals: any,
	) {
		const sites = parseSharePointSites(execution.result);

		if (sites.length === 0) {
			return this.renderGenericResult(execution, providerVisuals);
		}

		return (
			<div className="space-y-4">
				{/* Count Header */}
				<div
					className="rounded-2xl border p-4"
					style={{
						borderColor: `rgba(${providerVisuals.colorRgb}, 0.3)`,
						backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.05)`,
					}}
				>
					<div className="flex items-center gap-3">
						<div
							className="p-2 rounded-xl border"
							style={{
								backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.1)`,
								borderColor: `rgba(${providerVisuals.colorRgb}, 0.2)`,
							}}
						>
							<Globe
								className="w-5 h-5"
								style={{ color: providerVisuals.color }}
							/>
						</div>
						<div
							className="font-medium"
							style={{ color: providerVisuals.color }}
						>
							{sites.length} site{sites.length !== 1 ? "s" : ""} found
						</div>
					</div>
				</div>

				{/* Site Cards */}
				<div className="space-y-3">
					{sites.map((site, idx) => (
						<div
							key={site.id || idx}
							className="rounded-2xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/40 p-5 shadow-[0_20px_55px_rgba(0,0,0,0.55)]"
						>
							<div className="min-w-0">
								<h4 className="text-base font-medium text-slate-900 truncate">
									{site.name}
								</h4>
								{site.url && (
									<a
										href={site.url}
										target="_blank"
										rel="noopener noreferrer"
										className="text-xs flex items-center gap-1 mt-1"
										style={{ color: providerVisuals.color }}
									>
										<ExternalLink className="w-3 h-3 flex-shrink-0" />
										{site.url}
									</a>
								)}
							</div>
							{site.description && (
								<p className="text-sm text-[color:var(--color-text-secondary)] mt-2">
									{site.description}
								</p>
							)}
							{(site.created || site.last_modified) && (
								<div className="flex items-center gap-4 mt-3 text-xs text-[color:var(--color-text-muted)]">
									{site.created && (
										<span className="flex items-center gap-1">
											<Clock className="w-3 h-3" />
											Created {formatSharePointDate(site.created)}
										</span>
									)}
									{site.last_modified && (
										<span className="flex items-center gap-1">
											<Clock className="w-3 h-3" />
											Modified {formatSharePointDate(site.last_modified)}
										</span>
									)}
								</div>
							)}
						</div>
					))}
				</div>
			</div>
		);
	}

	renderSharePointSiteInfo(
		execution: McpServerExecution,
		providerVisuals: any,
	) {
		const siteInfo = parseSharePointSiteInfo(execution.result);

		if (!siteInfo) {
			return this.renderGenericResult(execution, providerVisuals);
		}

		return (
			<div className="space-y-4">
				{/* Site Header */}
				<div
					className="rounded-2xl border p-5"
					style={{
						borderColor: `rgba(${providerVisuals.colorRgb}, 0.3)`,
						backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.05)`,
					}}
				>
					<div className="flex items-center gap-3 mb-2">
						<div
							className="p-2 rounded-xl border"
							style={{
								backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.1)`,
								borderColor: `rgba(${providerVisuals.colorRgb}, 0.2)`,
							}}
						>
							<Globe
								className="w-5 h-5"
								style={{ color: providerVisuals.color }}
							/>
						</div>
						<div>
							<h4 className="text-base font-medium text-slate-900">
								{siteInfo.name}
							</h4>
							{siteInfo.url && (
								<a
									href={siteInfo.url}
									target="_blank"
									rel="noopener noreferrer"
									className="text-xs flex items-center gap-1 mt-0.5"
									style={{ color: providerVisuals.color }}
								>
									<ExternalLink className="w-3 h-3" />
									{siteInfo.url}
								</a>
							)}
						</div>
					</div>
					{siteInfo.description && (
						<p className="text-sm text-[color:var(--color-text-secondary)] mt-2 ml-12">
							{siteInfo.description}
						</p>
					)}
					{(siteInfo.created || siteInfo.last_modified) && (
						<div className="flex items-center gap-4 mt-2 ml-12 text-xs text-[color:var(--color-text-muted)]">
							{siteInfo.created && (
								<span>Created {formatSharePointDate(siteInfo.created)}</span>
							)}
							{siteInfo.last_modified && (
								<span>
									Modified {formatSharePointDate(siteInfo.last_modified)}
								</span>
							)}
						</div>
					)}
				</div>

				{/* Document Libraries */}
				{siteInfo.drives.length > 0 && (
					<div className="rounded-2xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/40 p-5 shadow-[0_20px_55px_rgba(0,0,0,0.55)]">
						<div className="flex items-center gap-2 mb-4">
							<HardDrive className="w-4 h-4 text-[color:var(--color-text-muted)]" />
							<span className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)] font-semibold">
								Document Libraries
							</span>
							<span
								className="px-2 py-0.5 rounded-md text-[11px] font-medium border"
								style={{
									backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.08)`,
									borderColor: `rgba(${providerVisuals.colorRgb}, 0.2)`,
									color: providerVisuals.color,
								}}
							>
								{siteInfo.drive_count}
							</span>
						</div>
						<div className="space-y-2 max-h-64 overflow-y-auto custom-scrollbar">
							{siteInfo.drives.map((drive, idx) => (
								<div
									key={drive.id || idx}
									className="rounded-xl bg-[color:var(--color-bg-secondary)] p-3"
								>
									<div className="flex items-center justify-between">
										<div className="min-w-0 flex-1">
											<span className="text-sm font-medium text-slate-900">
												{drive.name}
											</span>
											{drive.description && (
												<p className="text-xs text-[color:var(--color-text-muted)] mt-0.5 truncate">
													{drive.description}
												</p>
											)}
										</div>
										{drive.url && (
											<a
												href={drive.url}
												target="_blank"
												rel="noopener noreferrer"
												className="ml-2 flex-shrink-0"
												style={{ color: providerVisuals.color }}
											>
												<ExternalLink className="w-3.5 h-3.5" />
											</a>
										)}
									</div>
								</div>
							))}
						</div>
					</div>
				)}

				{/* Lists */}
				{siteInfo.lists.length > 0 && (
					<div className="rounded-2xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/40 p-5 shadow-[0_20px_55px_rgba(0,0,0,0.55)]">
						<div className="flex items-center gap-2 mb-4">
							<List className="w-4 h-4 text-[color:var(--color-text-muted)]" />
							<span className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)] font-semibold">
								Lists
							</span>
							<span
								className="px-2 py-0.5 rounded-md text-[11px] font-medium border"
								style={{
									backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.08)`,
									borderColor: `rgba(${providerVisuals.colorRgb}, 0.2)`,
									color: providerVisuals.color,
								}}
							>
								{siteInfo.list_count}
							</span>
						</div>
						<div className="space-y-2 max-h-72 overflow-y-auto custom-scrollbar">
							{siteInfo.lists.map((list, idx) => (
								<div
									key={list.id || idx}
									className="rounded-xl bg-[color:var(--color-bg-secondary)] p-3"
								>
									<div className="flex items-center justify-between">
										<div className="min-w-0 flex-1">
											<span className="text-sm font-medium text-slate-900">
												{list.name}
											</span>
											{list.description && (
												<p className="text-xs text-[color:var(--color-text-muted)] mt-0.5 truncate">
													{list.description}
												</p>
											)}
										</div>
										{list.url && (
											<a
												href={list.url}
												target="_blank"
												rel="noopener noreferrer"
												className="ml-2 flex-shrink-0"
												style={{ color: providerVisuals.color }}
											>
												<ExternalLink className="w-3.5 h-3.5" />
											</a>
										)}
									</div>
								</div>
							))}
						</div>
					</div>
				)}
			</div>
		);
	}

	renderSharePointDriveItems(
		execution: McpServerExecution,
		providerVisuals: any,
	) {
		const items = parseSharePointDriveItems(execution.result);

		if (items.length === 0) {
			return this.renderGenericResult(execution, providerVisuals);
		}

		return (
			<div className="space-y-4">
				{/* Count Header */}
				<div
					className="rounded-2xl border p-4"
					style={{
						borderColor: `rgba(${providerVisuals.colorRgb}, 0.3)`,
						backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.05)`,
					}}
				>
					<div className="flex items-center gap-3">
						<div
							className="p-2 rounded-xl border"
							style={{
								backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.1)`,
								borderColor: `rgba(${providerVisuals.colorRgb}, 0.2)`,
							}}
						>
							<HardDrive
								className="w-5 h-5"
								style={{ color: providerVisuals.color }}
							/>
						</div>
						<div
							className="font-medium"
							style={{ color: providerVisuals.color }}
						>
							{items.length} item{items.length !== 1 ? "s" : ""}
						</div>
					</div>
				</div>

				{/* Items List */}
				<div className="rounded-2xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/40 p-5 shadow-[0_20px_55px_rgba(0,0,0,0.55)]">
					<div className="space-y-2 max-h-96 overflow-y-auto custom-scrollbar">
						{items.map((item, idx) => (
							<div
								key={item.id || idx}
								className="rounded-xl bg-[color:var(--color-bg-secondary)] p-3"
							>
								<div className="flex items-center gap-3">
									{/* File/Folder Icon */}
									<div
										className="p-1.5 rounded-lg flex-shrink-0"
										style={{
											backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.1)`,
										}}
									>
										{item.type === "folder" ? (
											<Folder
												className="w-4 h-4"
												style={{ color: providerVisuals.color }}
											/>
										) : (
											<File
												className="w-4 h-4"
												style={{ color: providerVisuals.color }}
											/>
										)}
									</div>

									{/* Name & Details */}
									<div className="min-w-0 flex-1">
										<div className="flex items-center gap-2">
											<span className="text-sm font-medium text-slate-900 truncate">
												{item.name}
											</span>
										</div>
										<div className="flex items-center gap-3 mt-1 text-xs text-[color:var(--color-text-muted)]">
											{item.type === "file" && item.size > 0 && (
												<span>{formatFileSize(item.size)}</span>
											)}
											{item.type === "folder" &&
												item.child_count !== undefined && (
													<span>
														{item.child_count} item
														{item.child_count !== 1 ? "s" : ""}
													</span>
												)}
											{item.mime_type && (
												<span
													className="px-1.5 py-0.5 rounded text-[10px] font-mono border"
													style={{
														backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.08)`,
														borderColor: `rgba(${providerVisuals.colorRgb}, 0.15)`,
														color: `rgba(${providerVisuals.colorRgb}, 0.85)`,
													}}
												>
													{item.mime_type.split("/").pop()}
												</span>
											)}
											{item.last_modified && (
												<span>
													{formatSharePointDate(item.last_modified)}
												</span>
											)}
										</div>
									</div>

									{/* Link */}
									{item.url && (
										<a
											href={item.url}
											target="_blank"
											rel="noopener noreferrer"
											className="flex-shrink-0"
											style={{ color: providerVisuals.color }}
										>
											<ExternalLink className="w-3.5 h-3.5" />
										</a>
									)}
								</div>
							</div>
						))}
					</div>
				</div>
			</div>
		);
	}

	renderSharePointFileContent(
		execution: McpServerExecution,
		providerVisuals: any,
	) {
		const fileContent = parseSharePointFileContent(execution.result);

		if (!fileContent) {
			return this.renderGenericResult(execution, providerVisuals);
		}

		return (
			<div className="space-y-4">
				{/* File Metadata Card */}
				<div
					className="rounded-2xl border p-5"
					style={{
						borderColor: `rgba(${providerVisuals.colorRgb}, 0.3)`,
						backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.05)`,
					}}
				>
					<div className="flex items-center gap-3 mb-3">
						<div
							className="p-2 rounded-xl border"
							style={{
								backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.1)`,
								borderColor: `rgba(${providerVisuals.colorRgb}, 0.2)`,
							}}
						>
							<FileText
								className="w-5 h-5"
								style={{ color: providerVisuals.color }}
							/>
						</div>
						<div className="min-w-0 flex-1">
							<h4 className="text-base font-medium text-slate-900 truncate">
								{fileContent.name}
							</h4>
							{fileContent.url && (
								<a
									href={fileContent.url}
									target="_blank"
									rel="noopener noreferrer"
									className="text-xs flex items-center gap-1 mt-0.5"
									style={{ color: providerVisuals.color }}
								>
									<ExternalLink className="w-3 h-3" />
									Open in SharePoint
								</a>
							)}
						</div>
					</div>

					{/* Metadata Badges */}
					<div className="flex flex-wrap gap-2 ml-12">
						{fileContent.size > 0 && (
							<span
								className="px-2 py-0.5 rounded-md text-[11px] font-medium border"
								style={{
									backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.08)`,
									borderColor: `rgba(${providerVisuals.colorRgb}, 0.2)`,
									color: `rgba(${providerVisuals.colorRgb}, 0.85)`,
								}}
							>
								{formatFileSize(fileContent.size)}
							</span>
						)}
						{fileContent.mime_type && (
							<span
								className="px-2 py-0.5 rounded-md text-[11px] font-mono border"
								style={{
									backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.08)`,
									borderColor: `rgba(${providerVisuals.colorRgb}, 0.2)`,
									color: `rgba(${providerVisuals.colorRgb}, 0.85)`,
								}}
							>
								{fileContent.mime_type}
							</span>
						)}
						{fileContent.created_by && (
							<span className="px-2 py-0.5 rounded-md text-[11px] border border-[color:var(--color-border)]/50 text-[color:var(--color-text-secondary)] flex items-center gap-1">
								<User className="w-3 h-3" />
								{fileContent.created_by}
							</span>
						)}
						{fileContent.extraction_method && (
							<span className="px-2 py-0.5 rounded-md text-[11px] border border-[color:var(--color-border)]/50 text-[color:var(--color-text-muted)]">
								via {fileContent.extraction_method}
							</span>
						)}
						{fileContent.sheet_count != null && (
							<span className="px-2 py-0.5 rounded-md text-[11px] border border-[color:var(--color-border)]/50 text-[color:var(--color-text-muted)]">
								{fileContent.sheet_count} sheet
								{fileContent.sheet_count !== 1 ? "s" : ""}
							</span>
						)}
						{fileContent.page_count != null && (
							<span className="px-2 py-0.5 rounded-md text-[11px] border border-[color:var(--color-border)]/50 text-[color:var(--color-text-muted)]">
								{fileContent.page_count} page
								{fileContent.page_count !== 1 ? "s" : ""}
							</span>
						)}
						{fileContent.last_modified && (
							<span className="px-2 py-0.5 rounded-md text-[11px] border border-[color:var(--color-border)]/50 text-[color:var(--color-text-muted)] flex items-center gap-1">
								<Clock className="w-3 h-3" />
								{formatSharePointDate(fileContent.last_modified)}
							</span>
						)}
					</div>
				</div>

				{/* Content Section */}
				{fileContent.content && (
					<div className="rounded-2xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/40 p-5 shadow-[0_20px_55px_rgba(0,0,0,0.55)]">
						<div className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)] font-semibold mb-4">
							Content
						</div>
						<div className="rounded-xl bg-[color:var(--color-bg-secondary)] p-4 max-h-96 overflow-y-auto custom-scrollbar">
							{looksLikeMarkdown(fileContent.content) ? (
								<SimpleMarkdown content={fileContent.content} variant="light" />
							) : (
								<pre className="text-sm text-[color:var(--color-text-secondary)] whitespace-pre-wrap font-sans leading-relaxed">
									{fileContent.content}
								</pre>
							)}
						</div>
					</div>
				)}

				{/* Binary file message */}
				{!fileContent.content && fileContent.message && (
					<div className="rounded-2xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/40 p-5 shadow-[0_20px_55px_rgba(0,0,0,0.55)]">
						<p className="text-sm text-[color:var(--color-text-secondary)]">
							{fileContent.message}
						</p>
					</div>
				)}
			</div>
		);
	}

	// ─── SharePoint search_content renderers ─────────────────────────────

	renderSharePointSearchPreview(
		execution: McpServerExecution,
		providerVisuals: any,
	) {
		const searchResult = parseSharePointSearchContent(execution.result);
		if (!searchResult) {
			return this.renderGenericResult(execution, providerVisuals);
		}

		const { results, total, query, facets, more_results_available } = searchResult;
		const driveItemCount = results.filter((r) => r.entity_type === "driveItem").length;
		const listItemCount = results.filter((r) => r.entity_type === "listItem").length;
		const fileTypeFacets = facets?.fileType?.slice(0, 5) || [];

		return (
			<div className="space-y-4">
				{/* Prominent Search Query Banner */}
				<div
					className="rounded-2xl border p-5"
					style={{
						borderColor: `rgba(${providerVisuals.colorRgb}, 0.4)`,
						backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.08)`,
					}}
				>
					<div className="flex items-center gap-3 mb-3">
						<div
							className="p-2.5 rounded-xl border"
							style={{
								backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.15)`,
								borderColor: `rgba(${providerVisuals.colorRgb}, 0.3)`,
							}}
						>
							<Search
								className="w-6 h-6"
								style={{ color: providerVisuals.color }}
							/>
						</div>
						<div>
							<div className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)] font-semibold">
								Search Query
							</div>
							<div className="text-lg font-semibold text-slate-900 mt-0.5">
								&ldquo;{query}&rdquo;
							</div>
						</div>
					</div>

					{/* Result count summary */}
					<div className="flex items-center gap-3 ml-[52px] flex-wrap">
						<span
							className="font-medium"
							style={{ color: providerVisuals.color }}
						>
							{results.length} of {total.toLocaleString()} results
						</span>
						{more_results_available && (
							<span
								className="px-2 py-0.5 rounded-md text-[11px] font-medium border"
								style={{
									backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.1)`,
									borderColor: `rgba(${providerVisuals.colorRgb}, 0.25)`,
									color: providerVisuals.color,
								}}
							>
								More available
							</span>
						)}
					</div>
				</div>

				{/* Entity Type Breakdown */}
				{(driveItemCount > 0 || listItemCount > 0) && (
					<div className="flex gap-3">
						{driveItemCount > 0 && (
							<div
								className="flex items-center gap-2 px-3 py-2 rounded-xl border"
								style={{
									backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.05)`,
									borderColor: `rgba(${providerVisuals.colorRgb}, 0.2)`,
								}}
							>
								<File
									className="w-4 h-4"
									style={{ color: providerVisuals.color }}
								/>
								<span className="text-sm text-[color:var(--color-text-secondary)]">
									{driveItemCount} document{driveItemCount !== 1 ? "s" : ""}
								</span>
							</div>
						)}
						{listItemCount > 0 && (
							<div
								className="flex items-center gap-2 px-3 py-2 rounded-xl border"
								style={{
									backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.05)`,
									borderColor: `rgba(${providerVisuals.colorRgb}, 0.2)`,
								}}
							>
								<List
									className="w-4 h-4"
									style={{ color: providerVisuals.color }}
								/>
								<span className="text-sm text-[color:var(--color-text-secondary)]">
									{listItemCount} list item{listItemCount !== 1 ? "s" : ""}
								</span>
							</div>
						)}
					</div>
				)}

				{/* Facets Preview */}
				{fileTypeFacets.length > 0 && (
					<div className="rounded-2xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/40 p-5 shadow-[0_20px_55px_rgba(0,0,0,0.55)]">
						<div className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)] font-semibold mb-3">
							File Types
						</div>
						<div className="flex flex-wrap gap-2">
							{fileTypeFacets.map((f) => (
								<span
									key={f.value}
									className="px-2.5 py-1 rounded-lg text-xs font-medium border"
									style={{
										backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.08)`,
										borderColor: `rgba(${providerVisuals.colorRgb}, 0.2)`,
										color: `rgba(${providerVisuals.colorRgb}, 0.85)`,
									}}
								>
									.{f.value}{" "}
									<span className="text-[color:var(--color-text-muted)]">
										({f.count.toLocaleString()})
									</span>
								</span>
							))}
						</div>
					</div>
				)}
			</div>
		);
	}

	renderSharePointSearchResults(
		execution: McpServerExecution,
		providerVisuals: any,
	) {
		const searchResult = parseSharePointSearchContent(execution.result);
		if (!searchResult) {
			return this.renderGenericResult(execution, providerVisuals);
		}

		const { results, total, query } = searchResult;

		return (
			<div className="space-y-4">
				{/* Results Count Header */}
				<div
					className="rounded-2xl border p-4"
					style={{
						borderColor: `rgba(${providerVisuals.colorRgb}, 0.3)`,
						backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.05)`,
					}}
				>
					<div className="flex items-center gap-3">
						<div
							className="p-2 rounded-xl border"
							style={{
								backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.1)`,
								borderColor: `rgba(${providerVisuals.colorRgb}, 0.2)`,
							}}
						>
							<Search
								className="w-5 h-5"
								style={{ color: providerVisuals.color }}
							/>
						</div>
						<div>
							<div
								className="font-medium"
								style={{ color: providerVisuals.color }}
							>
								{results.length} of {total.toLocaleString()} results
							</div>
							{query && (
								<div className="text-xs text-[color:var(--color-text-muted)]">
									for &quot;{query}&quot;
								</div>
							)}
						</div>
					</div>
				</div>

				{/* Result Cards */}
				<div className="space-y-3">
					{results.map((result, idx) =>
						this.renderSharePointSearchResultCard(result, idx, providerVisuals),
					)}
				</div>
			</div>
		);
	}

	renderSharePointSearchResultCard(
		result: SharePointSearchResult,
		idx: number,
		providerVisuals: any,
	) {
		const snippetSegments = parseSearchSnippet(result.snippet);
		const displayName =
			result.name ||
			(result.entity_type === "listItem" ? "List Item" : "Document");
		const EntityIcon = result.entity_type === "listItem" ? List : File;

		return (
			<div
				key={result.id || idx}
				className="rounded-2xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/40 p-5 hover:border-opacity-100 transition-all group shadow-[0_20px_55px_rgba(0,0,0,0.55)]"
				onMouseEnter={(e) => {
					e.currentTarget.style.borderColor = `rgba(${providerVisuals.colorRgb}, 0.4)`;
				}}
				onMouseLeave={(e) => {
					e.currentTarget.style.borderColor = "";
				}}
			>
				{/* Title row with entity icon */}
				<div className="flex items-start justify-between gap-4 mb-3">
					<div className="flex items-center gap-3 min-w-0">
						<div
							className="p-2 rounded-lg flex-shrink-0"
							style={{
								backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.1)`,
							}}
						>
							<EntityIcon
								className="w-4 h-4"
								style={{ color: providerVisuals.color }}
							/>
						</div>
						<div className="min-w-0">
							<h4 className="text-base font-medium text-slate-900 truncate">
								{displayName}
							</h4>
							<span className="text-xs text-[color:var(--color-text-muted)]">
								{result.entity_type === "listItem"
									? "List Item"
									: "Document"}
							</span>
						</div>
					</div>

					{result.url && (
						<a
							href={result.url}
							target="_blank"
							rel="noopener noreferrer"
							className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors flex-shrink-0"
							style={{
								color: providerVisuals.color,
								backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.1)`,
							}}
							onMouseEnter={(e) => {
								e.currentTarget.style.backgroundColor = `rgba(${providerVisuals.colorRgb}, 0.2)`;
							}}
							onMouseLeave={(e) => {
								e.currentTarget.style.backgroundColor = `rgba(${providerVisuals.colorRgb}, 0.1)`;
							}}
						>
							<ExternalLink className="w-3.5 h-3.5" />
							Open in SharePoint
						</a>
					)}
				</div>

				{/* Snippet with highlights */}
				{snippetSegments.length > 0 && (
					<p className="text-sm text-[color:var(--color-text-secondary)] leading-relaxed mb-3">
						{snippetSegments.map((seg, i) =>
							seg.highlighted ? (
								<span
									key={i}
									className="font-semibold px-0.5 rounded"
									style={{
										color: providerVisuals.color,
										backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.15)`,
									}}
								>
									{seg.text}
								</span>
							) : (
								<span key={i}>{seg.text}</span>
							),
						)}
					</p>
				)}

				{/* Metadata row */}
				<div className="flex items-center gap-3 flex-wrap text-xs text-[color:var(--color-text-muted)]">
					{result.last_modified && (
						<span className="flex items-center gap-1">
							<Clock className="w-3 h-3" />
							{formatSharePointDate(result.last_modified)}
						</span>
					)}
					{result.created_by && (
						<span className="flex items-center gap-1">
							<User className="w-3 h-3" />
							{result.created_by}
						</span>
					)}
					{result.entity_type === "driveItem" &&
						result.size != null &&
						result.size > 0 && (
							<span className="flex items-center gap-1">
								<HardDrive className="w-3 h-3" />
								{formatFileSize(result.size)}
							</span>
						)}
				</div>
			</div>
		);
	}

	// ─── OneDrive-specific renderers ─────────────────────────────────────

	renderOneDriveItemsList(
		execution: McpServerExecution,
		providerVisuals: any,
	) {
		const { items, query } = parseOneDriveItems(execution.result);

		if (items.length === 0) {
			return this.renderGenericResult(execution, providerVisuals);
		}

		return (
			<div className="space-y-4">
				{/* Count Header */}
				<div
					className="rounded-2xl border p-4"
					style={{
						borderColor: `rgba(${providerVisuals.colorRgb}, 0.3)`,
						backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.05)`,
					}}
				>
					<div className="flex items-center gap-3">
						<div
							className="p-2 rounded-xl border"
							style={{
								backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.1)`,
								borderColor: `rgba(${providerVisuals.colorRgb}, 0.2)`,
							}}
						>
							<Search
								className="w-5 h-5"
								style={{ color: providerVisuals.color }}
							/>
						</div>
						<div>
							<div
								className="font-medium"
								style={{ color: providerVisuals.color }}
							>
								{items.length} result{items.length !== 1 ? "s" : ""}
								{query ? ` for "${query}"` : ""}
							</div>
							<div className="text-xs text-[color:var(--color-text-muted)] mt-0.5">
								OneDrive files &amp; folders
							</div>
						</div>
					</div>
				</div>

				{/* Items List */}
				<div className="rounded-2xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/40 p-5 shadow-[0_20px_55px_rgba(0,0,0,0.55)]">
					<div className="space-y-2 max-h-96 overflow-y-auto custom-scrollbar">
						{items.map((item, idx) => (
							<div
								key={item.id || idx}
								className="rounded-xl bg-[color:var(--color-bg-secondary)] p-3"
							>
								<div className="flex items-center gap-3">
									<div
										className="p-1.5 rounded-lg flex-shrink-0"
										style={{
											backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.1)`,
										}}
									>
										{item.type === "folder" ? (
											<Folder
												className="w-4 h-4"
												style={{ color: providerVisuals.color }}
											/>
										) : (
											<File
												className="w-4 h-4"
												style={{ color: providerVisuals.color }}
											/>
										)}
									</div>

									<div className="min-w-0 flex-1">
										<span className="text-sm font-medium text-slate-900 truncate block">
											{item.name}
										</span>
										<div className="flex items-center gap-3 mt-1 text-xs text-[color:var(--color-text-muted)]">
											{item.type === "file" && item.size > 0 && (
												<span>{formatOneDriveFileSize(item.size)}</span>
											)}
											{item.type === "folder" &&
												item.child_count !== undefined && (
													<span>
														{item.child_count} item
														{item.child_count !== 1 ? "s" : ""}
													</span>
												)}
											{item.mime_type && (
												<span
													className="px-1.5 py-0.5 rounded text-[10px] font-mono border"
													style={{
														backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.08)`,
														borderColor: `rgba(${providerVisuals.colorRgb}, 0.15)`,
														color: `rgba(${providerVisuals.colorRgb}, 0.85)`,
													}}
												>
													{item.mime_type.split("/").pop()}
												</span>
											)}
											{item.last_modified && (
												<span>{formatOneDriveDate(item.last_modified)}</span>
											)}
										</div>
									</div>

									{item.url && (
										<a
											href={item.url}
											target="_blank"
											rel="noopener noreferrer"
											className="flex-shrink-0"
											style={{ color: providerVisuals.color }}
										>
											<ExternalLink className="w-3.5 h-3.5" />
										</a>
									)}
								</div>
							</div>
						))}
					</div>
				</div>
			</div>
		);
	}

	renderOneDriveDrivesList(
		execution: McpServerExecution,
		providerVisuals: any,
	) {
		const drives = parseOneDriveDrives(execution.result);

		if (drives.length === 0) {
			return this.renderGenericResult(execution, providerVisuals);
		}

		return (
			<div className="space-y-4">
				<div
					className="rounded-2xl border p-4"
					style={{
						borderColor: `rgba(${providerVisuals.colorRgb}, 0.3)`,
						backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.05)`,
					}}
				>
					<div className="flex items-center gap-3">
						<div
							className="p-2 rounded-xl border"
							style={{
								backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.1)`,
								borderColor: `rgba(${providerVisuals.colorRgb}, 0.2)`,
							}}
						>
							<HardDrive
								className="w-5 h-5"
								style={{ color: providerVisuals.color }}
							/>
						</div>
						<div
							className="font-medium"
							style={{ color: providerVisuals.color }}
						>
							{drives.length} drive{drives.length !== 1 ? "s" : ""}
						</div>
					</div>
				</div>

				<div className="rounded-2xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/40 p-5 shadow-[0_20px_55px_rgba(0,0,0,0.55)]">
					<div className="space-y-2 max-h-96 overflow-y-auto custom-scrollbar">
						{drives.map((drive, idx) => (
							<div
								key={drive.id || idx}
								className="rounded-xl bg-[color:var(--color-bg-secondary)] p-3"
							>
								<div className="flex items-center gap-3">
									<div
										className="p-1.5 rounded-lg flex-shrink-0"
										style={{
											backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.1)`,
										}}
									>
										<HardDrive
											className="w-4 h-4"
											style={{ color: providerVisuals.color }}
										/>
									</div>
									<div className="min-w-0 flex-1">
										<span className="text-sm font-medium text-slate-900">
											{drive.name}
										</span>
										<div className="flex items-center gap-3 mt-1 text-xs text-[color:var(--color-text-muted)]">
											{drive.drive_type && (
												<span
													className="px-1.5 py-0.5 rounded text-[10px] font-mono border"
													style={{
														backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.08)`,
														borderColor: `rgba(${providerVisuals.colorRgb}, 0.15)`,
														color: `rgba(${providerVisuals.colorRgb}, 0.85)`,
													}}
												>
													{drive.drive_type}
												</span>
											)}
											{drive.used > 0 && drive.total > 0 && (
												<span>
													{formatOneDriveFileSize(drive.used)} /{" "}
													{formatOneDriveFileSize(drive.total)}
												</span>
											)}
										</div>
									</div>
									{drive.url && (
										<a
											href={drive.url}
											target="_blank"
											rel="noopener noreferrer"
											className="flex-shrink-0"
											style={{ color: providerVisuals.color }}
										>
											<ExternalLink className="w-3.5 h-3.5" />
										</a>
									)}
								</div>
							</div>
						))}
					</div>
				</div>
			</div>
		);
	}

	renderOneDriveFileContent(
		execution: McpServerExecution,
		providerVisuals: any,
	) {
		const fileContent = parseOneDriveFileContent(execution.result);

		if (!fileContent) {
			return this.renderGenericResult(execution, providerVisuals);
		}

		return (
			<div className="space-y-4">
				<div
					className="rounded-2xl border p-4"
					style={{
						borderColor: `rgba(${providerVisuals.colorRgb}, 0.3)`,
						backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.05)`,
					}}
				>
					<div className="flex items-start gap-3">
						<div
							className="p-2 rounded-xl border flex-shrink-0"
							style={{
								backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.1)`,
								borderColor: `rgba(${providerVisuals.colorRgb}, 0.2)`,
							}}
						>
							<FileText
								className="w-5 h-5"
								style={{ color: providerVisuals.color }}
							/>
						</div>
						<div className="min-w-0 flex-1">
							<div className="flex items-center gap-2 mb-2">
								<span
									className="text-sm font-semibold truncate"
									style={{ color: providerVisuals.color }}
								>
									{fileContent.name}
								</span>
								{fileContent.url && (
									<a
										href={fileContent.url}
										target="_blank"
										rel="noopener noreferrer"
										style={{ color: providerVisuals.color }}
									>
										<ExternalLink className="w-3 h-3" />
									</a>
								)}
							</div>
							<div className="flex flex-wrap items-center gap-2 text-xs">
								{fileContent.size > 0 && (
									<span className="px-2 py-0.5 rounded-md text-[11px] border border-[color:var(--color-border)]/50 text-[color:var(--color-text-muted)]">
										{formatOneDriveFileSize(fileContent.size)}
									</span>
								)}
								{fileContent.mime_type && (
									<span
										className="px-2 py-0.5 rounded-md text-[11px] border font-mono"
										style={{
											backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.08)`,
											borderColor: `rgba(${providerVisuals.colorRgb}, 0.2)`,
											color: providerVisuals.color,
										}}
									>
										{fileContent.mime_type.split("/").pop()}
									</span>
								)}
								{fileContent.page_count !== undefined && (
									<span className="px-2 py-0.5 rounded-md text-[11px] border border-[color:var(--color-border)]/50 text-[color:var(--color-text-muted)]">
										{fileContent.page_count} page
										{fileContent.page_count !== 1 ? "s" : ""}
									</span>
								)}
								{fileContent.sheet_count !== undefined && (
									<span className="px-2 py-0.5 rounded-md text-[11px] border border-[color:var(--color-border)]/50 text-[color:var(--color-text-muted)]">
										{fileContent.sheet_count} sheet
										{fileContent.sheet_count !== 1 ? "s" : ""}
									</span>
								)}
								{fileContent.last_modified && (
									<span className="px-2 py-0.5 rounded-md text-[11px] border border-[color:var(--color-border)]/50 text-[color:var(--color-text-muted)] flex items-center gap-1">
										<Clock className="w-3 h-3" />
										{formatOneDriveDate(fileContent.last_modified)}
									</span>
								)}
							</div>
						</div>
					</div>
				</div>

				{fileContent.content && (
					<div className="rounded-2xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/40 p-5 shadow-[0_20px_55px_rgba(0,0,0,0.55)]">
						<div className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)] font-semibold mb-4">
							Content
						</div>
						<div className="rounded-xl bg-[color:var(--color-bg-secondary)] p-4 max-h-96 overflow-y-auto custom-scrollbar">
							{oneDriveLooksLikeMarkdown(fileContent.content) ? (
								<SimpleMarkdown content={fileContent.content} variant="light" />
							) : (
								<pre className="text-sm text-[color:var(--color-text-secondary)] whitespace-pre-wrap font-sans leading-relaxed">
									{fileContent.content}
								</pre>
							)}
						</div>
					</div>
				)}

				{!fileContent.content && fileContent.message && (
					<div className="rounded-2xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/40 p-5 shadow-[0_20px_55px_rgba(0,0,0,0.55)]">
						<p className="text-sm text-[color:var(--color-text-secondary)]">
							{fileContent.message}
						</p>
					</div>
				)}
			</div>
		);
	}

	renderOneDriveItemMetadata(
		execution: McpServerExecution,
		providerVisuals: any,
	) {
		const item = parseOneDriveItemMetadata(execution.result);

		if (!item) {
			return this.renderGenericResult(execution, providerVisuals);
		}

		return (
			<div className="space-y-4">
				<div
					className="rounded-2xl border p-4"
					style={{
						borderColor: `rgba(${providerVisuals.colorRgb}, 0.3)`,
						backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.05)`,
					}}
				>
					<div className="flex items-start gap-3">
						<div
							className="p-2 rounded-xl border flex-shrink-0"
							style={{
								backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.1)`,
								borderColor: `rgba(${providerVisuals.colorRgb}, 0.2)`,
							}}
						>
							{item.type === "folder" ? (
								<Folder
									className="w-5 h-5"
									style={{ color: providerVisuals.color }}
								/>
							) : (
								<FileText
									className="w-5 h-5"
									style={{ color: providerVisuals.color }}
								/>
							)}
						</div>
						<div className="min-w-0 flex-1">
							<div className="flex items-center gap-2 mb-2">
								<span
									className="text-sm font-semibold truncate"
									style={{ color: providerVisuals.color }}
								>
									{item.name}
								</span>
								{item.url && (
									<a
										href={item.url}
										target="_blank"
										rel="noopener noreferrer"
										style={{ color: providerVisuals.color }}
									>
										<ExternalLink className="w-3 h-3" />
									</a>
								)}
							</div>
							<div className="flex flex-wrap items-center gap-2 text-xs">
								<span
									className="px-2 py-0.5 rounded-md text-[11px] border font-mono"
									style={{
										backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.08)`,
										borderColor: `rgba(${providerVisuals.colorRgb}, 0.2)`,
										color: providerVisuals.color,
									}}
								>
									{item.type}
								</span>
								{item.type === "file" && item.size > 0 && (
									<span className="px-2 py-0.5 rounded-md text-[11px] border border-[color:var(--color-border)]/50 text-[color:var(--color-text-muted)]">
										{formatOneDriveFileSize(item.size)}
									</span>
								)}
								{item.type === "folder" && item.child_count !== undefined && (
									<span className="px-2 py-0.5 rounded-md text-[11px] border border-[color:var(--color-border)]/50 text-[color:var(--color-text-muted)]">
										{item.child_count} item
										{item.child_count !== 1 ? "s" : ""}
									</span>
								)}
								{item.mime_type && (
									<span className="px-2 py-0.5 rounded-md text-[11px] border border-[color:var(--color-border)]/50 text-[color:var(--color-text-muted)] font-mono">
										{item.mime_type.split("/").pop()}
									</span>
								)}
								{item.created && (
									<span className="px-2 py-0.5 rounded-md text-[11px] border border-[color:var(--color-border)]/50 text-[color:var(--color-text-muted)] flex items-center gap-1">
										<Clock className="w-3 h-3" />
										Created {formatOneDriveDate(item.created)}
									</span>
								)}
								{item.last_modified && (
									<span className="px-2 py-0.5 rounded-md text-[11px] border border-[color:var(--color-border)]/50 text-[color:var(--color-text-muted)] flex items-center gap-1">
										<Clock className="w-3 h-3" />
										Modified {formatOneDriveDate(item.last_modified)}
									</span>
								)}
							</div>
						</div>
					</div>
				</div>
			</div>
		);
	}

	// ─── Fabric-specific renderers ───────────────────────────────────────

	renderFabricItemsList(
		execution: McpServerExecution,
		providerVisuals: any,
	) {
		const parsed = parseFabricListItems(execution.result);

		if (!parsed || parsed.items.length === 0) {
			return this.renderGenericResult(execution, providerVisuals);
		}

		const grouped = groupFabricItemsByType(parsed.items);

		return (
			<div className="space-y-4">
				{/* Workspace Header */}
				<div
					className="rounded-2xl border p-4"
					style={{
						borderColor: `rgba(${providerVisuals.colorRgb}, 0.3)`,
						backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.05)`,
					}}
				>
					<div className="flex items-center gap-3">
						<div
							className="p-2 rounded-xl border"
							style={{
								backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.1)`,
								borderColor: `rgba(${providerVisuals.colorRgb}, 0.2)`,
							}}
						>
							<Layers
								className="w-5 h-5"
								style={{ color: providerVisuals.color }}
							/>
						</div>
						<div>
							<div
								className="font-medium"
								style={{ color: providerVisuals.color }}
							>
								{parsed.item_count} item{parsed.item_count !== 1 ? "s" : ""}
							</div>
							<div className="text-xs text-[color:var(--color-text-muted)] mt-0.5">
								Workspace: {parsed.workspace_name}
								{parsed.item_type_filter
									? ` (filtered: ${parsed.item_type_filter})`
									: ""}
							</div>
						</div>
					</div>
				</div>

				{/* Grouped Item Cards */}
				{Array.from(grouped.entries()).map(([typeName, items]) => {
					const TypeIcon = getFabricItemTypeIcon(typeName);
					return (
						<div
							key={typeName}
							className="rounded-2xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/40 p-5 shadow-[0_20px_55px_rgba(0,0,0,0.55)]"
						>
							{/* Type Group Header */}
							<div className="flex items-center gap-2 mb-4">
								<TypeIcon
									className="w-4 h-4"
									style={{ color: providerVisuals.color }}
								/>
								<span className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)] font-semibold">
									{pluralizeFabricType(typeName)}
								</span>
								<span
									className="px-2 py-0.5 rounded-md text-[11px] font-medium border"
									style={{
										backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.08)`,
										borderColor: `rgba(${providerVisuals.colorRgb}, 0.2)`,
										color: providerVisuals.color,
									}}
								>
									{items.length}
								</span>
							</div>

							{/* Items within group */}
							<div className="space-y-2 max-h-64 overflow-y-auto custom-scrollbar">
								{items.map((item, idx) => (
									<div
										key={item.id || idx}
										className="rounded-xl bg-[color:var(--color-bg-secondary)] p-3"
									>
										<div className="flex items-center gap-3">
											<div
												className="p-1.5 rounded-lg flex-shrink-0"
												style={{
													backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.1)`,
												}}
											>
												<TypeIcon
													className="w-4 h-4"
													style={{ color: providerVisuals.color }}
												/>
											</div>
											<div className="min-w-0 flex-1">
												<span className="text-sm font-medium text-slate-900 truncate block">
													{item.display_name}
												</span>
												{item.description && (
													<p className="text-xs text-[color:var(--color-text-muted)] mt-0.5 truncate">
														{item.description}
													</p>
												)}
											</div>
											<span
												className="px-2 py-0.5 rounded text-[11px] font-medium border flex-shrink-0"
												style={{
													backgroundColor: `rgba(${providerVisuals.colorRgb}, 0.1)`,
													borderColor: `rgba(${providerVisuals.colorRgb}, 0.25)`,
													color: providerVisuals.color,
												}}
											>
												{item.type}
											</span>
										</div>
									</div>
								))}
							</div>
						</div>
					);
				})}
			</div>
		);
	}
}
