"use client";

import { Clock, Database, FileText, Hash, Sliders } from "lucide-react";
import Dropdown from "@/components/ui/Dropdown";
import InfoTooltip from "@/components/ui/InfoTooltipPortal";
import NumberInput from "@/components/ui/NumberInput";
import Toggle from "@/components/ui/Toggle";

interface DatabaseAdvancedSectionProps {
	maxRows: number;
	onMaxRowsChange: (maxRows: number) => void;
	timeoutSeconds: number;
	onTimeoutSecondsChange: (timeout: number) => void;
	returnFormat: string;
	onReturnFormatChange: (format: string) => void;
	includeSchema: boolean;
	onIncludeSchemaChange: (include: boolean) => void;
}

export default function DatabaseAdvancedSection({
	maxRows,
	onMaxRowsChange,
	timeoutSeconds,
	onTimeoutSecondsChange,
	returnFormat,
	onReturnFormatChange,
	includeSchema,
	onIncludeSchemaChange,
}: DatabaseAdvancedSectionProps) {
	return (
		<div className="space-y-6">
			<div className="rounded-[4px] border border-gray-200 bg-white p-6 shadow-sm">
				<div className="flex flex-wrap items-start justify-between gap-4 border-b border-gray-200 pb-5">
					<div className="flex min-w-0 items-start gap-3">
						<div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[4px] border border-gray-200 bg-white shadow-sm">
							<Sliders className="h-5 w-5 text-orange-600" aria-hidden />
						</div>
						<div className="min-w-0">
							<h3 className="text-lg font-semibold text-gray-900">
								Advanced Settings
							</h3>
							<p className="text-sm text-gray-600">
								Performance limits and output formatting
							</p>
						</div>
					</div>
				</div>

				<div className="mt-6 space-y-6">
					<div className="space-y-5">
						<div className="mb-1 flex items-center gap-2">
							<h4 className="text-sm font-semibold capitalize tracking-wide text-gray-900">
								Performance Limits
							</h4>
						</div>

						<div className="rounded-[4px] border border-gray-200 bg-slate-50 p-5">
							<div className="mb-4 flex items-start gap-3">
								<div className="rounded-[4px] border border-gray-200 bg-white p-2 shadow-sm">
									<Hash className="h-4 w-4 text-orange-600" />
								</div>
								<div className="flex-1">
									<div className="flex items-center gap-2">
										<h5 className="text-sm font-semibold text-gray-900">
											Maximum Rows
										</h5>
										<InfoTooltip text="Limits the number of rows returned by SELECT queries to prevent overwhelming results" />
									</div>
									<p className="mt-1 text-xs text-gray-600">
										Applies to SELECT queries only
									</p>
								</div>
							</div>
							<NumberInput
								value={maxRows}
								onChange={onMaxRowsChange}
								min={10}
								max={1000}
								step={10}
								label=""
								description=""
							/>
							<div className="mt-2 flex items-center justify-between text-xs text-gray-600">
								<span>Min: 10 rows</span>
								<span>Max: 1000 rows</span>
							</div>
						</div>

						<div className="rounded-[4px] border border-gray-200 bg-slate-50 p-5">
							<div className="mb-4 flex items-start gap-3">
								<div className="rounded-[4px] border border-gray-200 bg-white p-2 shadow-sm">
									<Clock className="h-4 w-4 text-orange-600" />
								</div>
								<div className="flex-1">
									<div className="flex items-center gap-2">
										<h5 className="text-sm font-semibold text-gray-900">
											Query Timeout
										</h5>
										<InfoTooltip text="Maximum time to wait for query execution before canceling the operation" />
									</div>
									<p className="mt-1 text-xs text-gray-600">In seconds</p>
								</div>
							</div>
							<NumberInput
								value={timeoutSeconds}
								onChange={onTimeoutSecondsChange}
								min={5}
								max={300}
								step={5}
								label=""
								description=""
							/>
							<div className="mt-2 flex items-center justify-between text-xs text-gray-600">
								<span>Min: 5 seconds</span>
								<span>Max: 300 seconds</span>
							</div>
						</div>
					</div>

					<div className="space-y-5">
						<div className="mb-1 flex items-center gap-2">
							<h4 className="text-sm font-semibold capitalize tracking-wide text-gray-900">
								Output Formatting
							</h4>
						</div>

						<div className="rounded-[4px] border border-gray-200 bg-slate-50 p-5">
							<div className="mb-4 flex items-start gap-3">
								<div className="rounded-[4px] border border-gray-200 bg-white p-2 shadow-sm">
									<FileText className="h-4 w-4 text-orange-600" />
								</div>
								<div className="flex-1">
									<div className="flex items-center gap-2">
										<h5 className="text-sm font-semibold text-gray-900">
											Return Format
										</h5>
										<InfoTooltip text="Choose how query results are formatted for the agent" />
									</div>
									<p className="mt-1 text-xs text-gray-600">
										Format for query results
									</p>
								</div>
							</div>
							<Dropdown
								value={returnFormat}
								onChange={onReturnFormatChange}
								menuAppearance="light"
								options={[
									{
										value: "json",
										label: "JSON",
										description:
											"Structured data format - best for programmatic access",
									},
									{
										value: "csv",
										label: "CSV",
										description: "Comma-separated values - portable format",
									},
									{
										value: "markdown",
										label: "Markdown",
										description: "Formatted table - human-readable",
									},
								]}
							/>
						</div>

						<div className="rounded-[4px] border border-gray-200 bg-slate-50 p-5">
							<div className="flex flex-wrap items-center justify-between gap-4">
								<div className="flex min-w-0 flex-1 items-start gap-3">
									<div className="rounded-[4px] border border-gray-200 bg-white p-2 shadow-sm">
										<Database className="h-4 w-4 text-orange-600" />
									</div>
									<div className="flex-1">
										<div className="flex items-center gap-2">
											<h5 className="text-sm font-semibold text-gray-900">
												Include Schema Information
											</h5>
											<InfoTooltip text="Include column types, constraints, and other metadata in query results" />
										</div>
										<p className="mt-1 text-xs text-gray-600">
											Add column types and metadata to results
										</p>
									</div>
								</div>
								<Toggle
									checked={includeSchema}
									onChange={onIncludeSchemaChange}
									size="md"
								/>
							</div>
						</div>
					</div>

					<div className="rounded-[4px] border border-orange-400 bg-white p-4 shadow-sm">
						<div className="mb-2 flex items-center gap-2">
							<Sliders className="h-4 w-4 text-orange-600" />
							<span className="text-xs font-semibold capitalize tracking-wide text-gray-900">
								Current Settings
							</span>
						</div>
						<div className="flex flex-wrap gap-2">
							<span className="rounded-full border border-gray-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-gray-800">
								Max Rows: {maxRows}
							</span>
							<span className="rounded-full border border-gray-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-gray-800">
								Timeout: {timeoutSeconds}s
							</span>
							<span className="rounded-full border border-gray-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-gray-800">
								Format: {returnFormat.charAt(0).toUpperCase() + returnFormat.slice(1)}
							</span>
							<span className="rounded-full border border-gray-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-gray-800">
								Schema: {includeSchema ? "Included" : "Excluded"}
							</span>
						</div>
					</div>
				</div>
			</div>
		</div>
	);
}
