"use client";

import { useCallback } from "react";
import type { ToolCallPolicy } from "@/types/guardrails";
import NumberInput from "../../../../ui/NumberInput";
import StringListEditor from "./StringListEditor";

interface ToolPoliciesSectionProps {
	policy: ToolCallPolicy;
	onChange: (policy: ToolCallPolicy) => void;
}

export default function ToolPoliciesSection({
	policy,
	onChange,
}: ToolPoliciesSectionProps) {
	const handleListChange = useCallback(
		(field: keyof ToolCallPolicy, values: string[]) => {
			onChange({ ...policy, [field]: values });
		},
		[policy, onChange],
	);

	const handleNumberChange = useCallback(
		(field: keyof ToolCallPolicy, value: number) => {
			onChange({ ...policy, [field]: value });
		},
		[policy, onChange],
	);

	return (
		<div className="space-y-6">
			{/* Network Security */}
			<div className="space-y-3">
				<h4 className="text-xs font-semibold capitalize text-[color:var(--color-text-secondary)]">
					Network Security
				</h4>
				<StringListEditor
					label="Allowed URL Patterns"
					description="Glob patterns. Empty = allow all external URLs."
					values={policy.allowed_url_patterns}
					onChange={(v) => handleListChange("allowed_url_patterns", v)}
					placeholder="e.g. https://api.example.com/*"
					monospace
				/>
				<StringListEditor
					label="Blocked URL Patterns"
					values={policy.blocked_url_patterns}
					onChange={(v) => handleListChange("blocked_url_patterns", v)}
					placeholder="e.g. *.internal.corp"
					monospace
				/>
				<StringListEditor
					label="Blocked IP Ranges"
					description="CIDR ranges for SSRF protection. Defaults protect against internal network access."
					values={policy.blocked_ip_ranges}
					onChange={(v) => handleListChange("blocked_ip_ranges", v)}
					placeholder="e.g. 192.168.0.0/16"
					monospace
				/>
			</div>

			{/* Database Policies */}
			<div className="space-y-3">
				<h4 className="text-xs font-semibold capitalize text-[color:var(--color-text-secondary)]">
					Database
				</h4>
				<StringListEditor
					label="Allowed SQL Operations"
					description="Only these SQL operations will be permitted."
					values={policy.allowed_sql_operations}
					onChange={(v) =>
						handleListChange("allowed_sql_operations", v)
					}
					placeholder="e.g. SELECT"
				/>
				<StringListEditor
					label="Blocked Tables"
					values={policy.blocked_tables}
					onChange={(v) => handleListChange("blocked_tables", v)}
					placeholder="e.g. users"
				/>
				<NumberInput
					label="Max Query Rows"
					description="Maximum rows a query can return"
					value={policy.max_query_rows}
					onChange={(v) => handleNumberChange("max_query_rows", v)}
					min={1}
					max={100000}
					step={100}
				/>
			</div>

			{/* File System */}
			<div className="space-y-3">
				<h4 className="text-xs font-semibold capitalize text-[color:var(--color-text-secondary)]">
					File System
				</h4>
				<StringListEditor
					label="Allowed File Extensions"
					description="Empty = allow all. Include the dot (e.g. .txt)."
					values={policy.allowed_file_extensions}
					onChange={(v) =>
						handleListChange("allowed_file_extensions", v)
					}
					placeholder="e.g. .txt"
				/>
				<StringListEditor
					label="Blocked File Paths"
					values={policy.blocked_file_paths}
					onChange={(v) => handleListChange("blocked_file_paths", v)}
					placeholder="e.g. /etc/"
					monospace
				/>
				<NumberInput
					label="Max File Size (MB)"
					description="Maximum file size for writes"
					value={policy.max_file_size_mb}
					onChange={(v) => handleNumberChange("max_file_size_mb", v)}
					min={0.1}
					max={100}
					step={0.5}
				/>
			</div>

			{/* Execution Limits */}
			<div className="space-y-3">
				<h4 className="text-xs font-semibold capitalize text-[color:var(--color-text-secondary)]">
					Execution Limits
				</h4>
				<div className="grid gap-4 md:grid-cols-2">
					<NumberInput
						label="Max Tool Calls"
						description="Per execution"
						value={policy.max_tool_calls_per_execution}
						onChange={(v) =>
							handleNumberChange(
								"max_tool_calls_per_execution",
								v,
							)
						}
						min={1}
						max={500}
						step={5}
					/>
					<NumberInput
						label="Tool Timeout (s)"
						description="Per individual call"
						value={policy.tool_timeout_seconds}
						onChange={(v) =>
							handleNumberChange("tool_timeout_seconds", v)
						}
						min={5}
						max={600}
						step={5}
					/>
				</div>
			</div>
		</div>
	);
}
