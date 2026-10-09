"use client";

import { CheckCircle, type LucideIcon } from "lucide-react";
import type React from "react";
import { useCallback } from "react";
import McpLogo from "../icons/McpLogo";

export interface ToolOption {
	value: string;
	label: string;
	icon: LucideIcon;
	description: string;
	color: string;
}

interface ToolTileProps {
	tool: ToolOption;
	isSelected: boolean;
	onSelect: (value: string) => void;
}

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

export default function ToolTile({
	tool,
	isSelected,
	onSelect,
}: ToolTileProps) {
	const Icon = tool.icon;
	const radioId = `tool-tile-${tool.value}`;
	const colorRgb = colorRgbMap[tool.color] || "234, 88, 12";

	const handleChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			onSelect(e.target.value);
		},
		[onSelect],
	);

	return (
		<div className="group relative">
			<label
				htmlFor={radioId}
				className={`
					relative flex h-[144px] cursor-pointer flex-col items-center gap-2.5 rounded-2xl border p-4 transition-all duration-200
					${
						isSelected
							? "border-orange-500 bg-white shadow-[0_8px_24px_rgba(15,23,42,0.08)]"
							: "border-slate-200 bg-white shadow-sm hover:border-orange-400 hover:shadow-md"
					}
				`}
			>
				<input
					id={radioId}
					type="radio"
					name="toolType"
					value={tool.value}
					checked={isSelected}
					onChange={handleChange}
					className="sr-only"
				/>

				{isSelected && (
					<div
						className="absolute -right-2 -top-2 z-10 flex h-6 w-6 items-center justify-center rounded-full bg-orange-500 shadow-md"
					>
						<CheckCircle className="h-4 w-4 text-white" />
					</div>
				)}

				<div
					className="flex-shrink-0 rounded-xl p-3 transition-colors"
					style={{
						backgroundColor: isSelected
							? `rgba(${colorRgb}, 0.1)`
							: "rgb(248 250 252)",
						border: isSelected
							? `1px solid rgba(${colorRgb}, 0.35)`
							: "1px solid rgb(226 232 240)",
					}}
				>
					{tool.value === "mcp_server" ? (
						<McpLogo
							className={
								isSelected ? "text-orange-600" : "text-slate-500"
							}
							size={22}
						/>
					) : (
						<Icon
							className="h-[22px] w-[22px]"
							style={{
								color: isSelected
									? `rgb(${colorRgb})`
									: "rgb(100 116 139)",
							}}
						/>
					)}
				</div>

				<div className="w-full truncate text-center text-sm font-semibold text-slate-900 transition-colors group-hover:text-slate-900">
					{tool.label}
				</div>

				<div className="line-clamp-2 px-1 text-center text-[11px] leading-tight text-slate-600">
					{tool.description}
				</div>
			</label>
		</div>
	);
}
