/**
 * Microsoft Fabric-specific result parsing utilities for MCP execution panel
 */

import {
	BarChart3,
	BookOpen,
	BrainCircuit,
	Database,
	FileCode,
	Layers,
	Library,
	Play,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

/** Known Fabric item types */
export type FabricItemType =
	| "Report"
	| "SemanticModel"
	| "SQLEndpoint"
	| "DataPipeline"
	| "Lakehouse"
	| "Notebook"
	| "SQLDatabase"
	| "VariableLibrary"
	| string;

export interface FabricWorkspaceItem {
	id: string;
	display_name: string;
	type: FabricItemType;
	description: string;
	folder_id: string;
	created_date: string | null;
	modified_date: string | null;
}

export interface FabricListItemsResult {
	status: string;
	workspace_name: string;
	item_type_filter: string | null;
	item_count: number;
	items: FabricWorkspaceItem[];
}

// Tool name detection predicates

export function isFabricListItemsTool(toolName: string): boolean {
	const lower = toolName.toLowerCase();
	return lower.includes("list_items") || lower === "listitems";
}

// Parsing functions

export function parseFabricListItems(
	result: any,
): FabricListItemsResult | null {
	if (!result || typeof result !== "object") return null;
	if (result.status !== "success") return null;

	const items: FabricWorkspaceItem[] = Array.isArray(result.items)
		? result.items
				.filter((item: any) => item && typeof item === "object")
				.map((item: any) => ({
					id: item.id || "",
					display_name: item.display_name || "Unnamed Item",
					type: item.type || "Unknown",
					description: item.description || "",
					folder_id: item.folder_id || "",
					created_date: item.created_date || null,
					modified_date: item.modified_date || null,
				}))
		: [];

	return {
		status: result.status,
		workspace_name: result.workspace_name || "Unknown Workspace",
		item_type_filter: result.item_type_filter || null,
		item_count: result.item_count ?? items.length,
		items,
	};
}

// Utility functions

export function groupFabricItemsByType(
	items: FabricWorkspaceItem[],
): Map<string, FabricWorkspaceItem[]> {
	const groups = new Map<string, FabricWorkspaceItem[]>();
	for (const item of items) {
		const existing = groups.get(item.type) || [];
		existing.push(item);
		groups.set(item.type, existing);
	}
	return groups;
}

/** Map Fabric item type strings to appropriate lucide-react icons */
export function getFabricItemTypeIcon(itemType: string): LucideIcon {
	switch (itemType) {
		case "Report":
			return BarChart3;
		case "SemanticModel":
			return BrainCircuit;
		case "SQLEndpoint":
		case "SQLDatabase":
			return Database;
		case "DataPipeline":
			return Play;
		case "Lakehouse":
			return Layers;
		case "Notebook":
			return BookOpen;
		case "VariableLibrary":
			return Library;
		default:
			return FileCode;
	}
}

/** Human-readable plural labels for Fabric item types */
export function pluralizeFabricType(typeName: string): string {
	const labels: Record<string, string> = {
		Report: "Reports",
		SemanticModel: "Semantic Models",
		SQLEndpoint: "SQL Endpoints",
		DataPipeline: "Data Pipelines",
		Lakehouse: "Lakehouses",
		Notebook: "Notebooks",
		SQLDatabase: "SQL Databases",
		VariableLibrary: "Variable Libraries",
	};
	return labels[typeName] || `${typeName}s`;
}
