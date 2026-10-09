"use client";

import type React from "react";
import FormInput from "@/components/ui/FormInput";
import { cn } from "@/lib/utils";
import McpLogo from "../icons/McpLogo";
import ToolInfoPanel from "./ToolInfoPanel";
import type { ToolOption } from "./ToolTile";

const colorRgbMap: Record<string, string> = {
	blue: "59, 130, 246",
	green: "13, 169, 49",
	teal: "20, 184, 166",
	plum: "234, 88, 12",
	cyan: "6, 182, 212",
	purple: "168, 85, 247",
	emerald: "16, 185, 129",
	amber: "245, 158, 11",
};

interface ToolConfigSidebarProps {
	selectedToolOption: ToolOption | undefined;
	toolName: string;
	onToolNameChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

export default function ToolConfigSidebar({
	selectedToolOption,
	toolName,
	onToolNameChange,
}: ToolConfigSidebarProps) {
	const colorRgb = selectedToolOption
		? colorRgbMap[selectedToolOption.color] || "234, 88, 12"
		: "234, 88, 12";

	const Icon = selectedToolOption?.icon;

	return (
		<div
			className={cn(
				"custom-scrollbar flex w-full shrink-0 flex-col gap-5 overflow-y-auto rounded-2xl border border-slate-200 bg-white p-5 shadow-sm md:w-[340px]",
			)}
		>
			{/* Tool Preview */}
			{selectedToolOption && (
				<div className="flex items-center gap-4 border-b border-slate-200 pb-4">
					<div
						className="flex-shrink-0 rounded-2xl p-3.5 transition-colors"
						style={{
							backgroundColor: `rgba(${colorRgb}, 0.1)`,
							border: `1px solid rgba(${colorRgb}, 0.35)`,
						}}
					>
						{selectedToolOption.value === "mcp_server" ? (
							<McpLogo className="text-orange-600" size={28} />
						) : Icon ? (
							<Icon
								className="h-7 w-7"
								style={{ color: `rgb(${colorRgb})` }}
							/>
						) : null}
					</div>
					<div className="min-w-0 flex-1">
						<h3 className="truncate text-lg font-semibold text-slate-900">
							{selectedToolOption.label}
						</h3>
						<p className="mt-0.5 line-clamp-2 text-xs text-slate-600">
							{selectedToolOption.description}
						</p>
					</div>
				</div>
			)}

			<div className="text-xs font-semibold capitalize text-slate-600">
				Configuration
			</div>

			<FormInput
				label="Tool Name"
				value={toolName}
				onChange={onToolNameChange}
				placeholder="Enter a custom name for this tool"
				required
				className="!border-slate-200 !bg-white !text-slate-900 placeholder:!text-slate-400 hover:!border-slate-300 focus:!border-orange-500 focus:!ring-orange-500/20"
			/>

			<ToolInfoPanel selectedToolOption={selectedToolOption} />
		</div>
	);
}
