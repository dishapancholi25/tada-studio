"use client";

import React from "react";
import ToolTile, { type ToolOption } from "./ToolTile";

interface ToolTileGridProps {
	availableTools: ToolOption[];
	selectedTool: string;
	onToolSelect: (value: string) => void;
}

export default function ToolTileGrid({
	availableTools,
	selectedTool,
	onToolSelect,
}: ToolTileGridProps) {
	return (
		<div className="space-y-4">
			{/* Section Header */}
			<div className="flex items-center justify-between px-1">
				<div className="text-xs font-semibold capitalize text-slate-600">
					Available Tools
				</div>
				<span className="rounded-full border border-[#0DA931] bg-white px-2.5 py-1 text-[10px] font-medium text-[#0DA931]">
					{availableTools.length} Ready
				</span>
			</div>

			{/* Tool Tiles Grid */}
			<div className="grid grid-cols-2 xl:grid-cols-3 gap-3 p-2">
				{availableTools.map((tool) => (
					<ToolTile
						key={tool.value}
						tool={tool}
						isSelected={selectedTool === tool.value}
						onSelect={onToolSelect}
					/>
				))}
			</div>
		</div>
	);
}
