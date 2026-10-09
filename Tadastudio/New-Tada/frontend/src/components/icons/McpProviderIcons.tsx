"use client";

import { FileSearch, Github, Terminal } from "lucide-react";
import type React from "react";

interface IconProps {
	className?: string;
	size?: number;
	style?: React.CSSProperties;
}

/**
 * Notion logo icon
 */
export const NotionIcon: React.FC<IconProps> = ({
	className = "",
	size = 24,
	style,
}) => {
	return (
		<svg
			width={size}
			height={size}
			viewBox="0 0 24 24"
			fill="currentColor"
			xmlns="http://www.w3.org/2000/svg"
			className={className}
			style={{ flexShrink: 0, ...style }}
		>
			<path d="M4.459 4.208c.746.606 1.026.56 2.428.466l13.215-.793c.28 0 .047-.28-.046-.326L17.86 1.968c-.42-.326-.98-.7-2.055-.607L3.01 2.295c-.466.046-.56.28-.374.466l1.823 1.447zm.793 3.08v13.904c0 .747.373 1.027 1.214.98l14.523-.84c.841-.046.934-.56.934-1.166V6.354c0-.606-.233-.933-.747-.886l-15.177.886c-.56.047-.747.327-.747.934zm14.337.745c.093.42 0 .84-.42.888l-.7.14v10.264c-.608.327-1.168.514-1.635.514-.747 0-.934-.234-1.495-.933l-4.577-7.186v6.952l1.448.327s0 .84-1.168.84l-3.22.187c-.094-.187 0-.653.327-.746l.84-.233V9.854L7.822 9.76c-.094-.42.14-1.026.793-1.073l3.454-.234 4.763 7.279v-6.44l-1.215-.14c-.093-.514.28-.886.747-.933l3.222-.186zM2.83.559L16.2 0c1.634-.14 2.054.047 2.754.56l3.594 2.52c.467.327.607.42.607.98v17.96c0 1.073-.374 1.727-1.681 1.82L5.93 24c-.98.047-1.448-.093-1.962-.747L1.195 19.93c-.56-.793-.794-1.387-.794-2.054V2.106C.401 1.26.775.606 2.83.56z" />
		</svg>
	);
};

/**
 * Atlassian logo icon
 */
export const AtlassianIcon: React.FC<IconProps> = ({
	className = "",
	size = 24,
	style,
}) => {
	return (
		<svg
			width={size}
			height={size}
			viewBox="0 0 24 24"
			fill="currentColor"
			xmlns="http://www.w3.org/2000/svg"
			className={className}
			style={{ flexShrink: 0, ...style }}
		>
			<path d="M6.427 9.239a.57.57 0 0 0-.972.096L.112 21.066a.574.574 0 0 0 .511.826h7.278a.58.58 0 0 0 .507-.326c1.644-3.456.806-8.662-1.981-12.327zm5.478-6.324a12.36 12.36 0 0 0-.073 12.063l3.46 6.758a.574.574 0 0 0 .511.31h7.278a.574.574 0 0 0 .511-.826L12.947 2.915a.573.573 0 0 0-1.042 0z" />
		</svg>
	);
};

/**
 * Canva logo icon (placeholder for coming soon)
 */
export const CanvaIcon: React.FC<IconProps> = ({
	className = "",
	size = 24,
	style,
}) => {
	return (
		<svg
			width={size}
			height={size}
			viewBox="0 0 24 24"
			fill="currentColor"
			xmlns="http://www.w3.org/2000/svg"
			className={className}
			style={{ flexShrink: 0, ...style }}
		>
			<path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm4.873 16.076c-.163.26-.398.39-.697.39-.196 0-.404-.072-.656-.208a8.376 8.376 0 0 1-.748-.494 12.666 12.666 0 0 1-1.436-1.222c-.6.91-1.323 1.625-2.17 2.144-.845.52-1.724.78-2.637.78-.976 0-1.764-.325-2.364-.975-.6-.65-.9-1.518-.9-2.601 0-.878.187-1.75.56-2.614.373-.865.895-1.633 1.566-2.3a7.555 7.555 0 0 1 2.384-1.6c.91-.396 1.878-.594 2.904-.594.52 0 .975.046 1.365.136.391.091.728.215 1.014.371.286.156.521.338.709.546.187.208.325.43.416.665.091.234.137.48.137.735 0 .443-.11.834-.33 1.17-.22.338-.498.507-.832.507-.3 0-.546-.117-.736-.351a2.097 2.097 0 0 1-.403-.845c-.052-.195-.105-.368-.156-.52a1.126 1.126 0 0 0-.26-.416c-.117-.117-.286-.176-.507-.176-.39 0-.761.123-1.117.371-.356.247-.676.573-.962.975-.286.403-.514.859-.683 1.37-.17.51-.254 1.027-.254 1.553 0 .482.084.897.253 1.248.17.35.417.52.741.52.443 0 .866-.183 1.27-.546.403-.364.78-.845 1.131-1.443.13-.228.286-.396.468-.507a1.07 1.07 0 0 1 .572-.166c.261 0 .468.091.624.273.156.182.234.403.234.664 0 .195-.046.397-.136.605z" />
		</svg>
	);
};

/**
 * Databricks logo icon
 */
export const DatabricksIcon: React.FC<IconProps> = ({
	className = "",
	size = 24,
	style,
}) => {
	return (
		<svg
			width={size}
			height={size}
			viewBox="0 0 18 18"
			fill="currentColor"
			xmlns="http://www.w3.org/2000/svg"
			className={className}
			style={{ flexShrink: 0, ...style }}
		>
			<path d="M1.155,4.93v.512L9,9.868l7.006-3.957,0,1.6L9,11.491,1.55,7.258l-.395.22V10.54L9,14.955l7.006-3.942,0,1.586L9,16.581,1.55,12.347l-.395.22v.519L9,17.5l7.845-4.414V10.021l-.4-.218L9,14.036,1.992,10.054V8.476L9,12.414,16.845,8V4.978l-.4-.219L9,8.993,2.352,5.215,9,1.46l5.476,3.094.479-.269V3.863L9,.5Z" />
		</svg>
	);
};

/**
 * Azure DevOps logo icon (for Databricks DevOps MCP server)
 */
export const AzureDevOpsIcon: React.FC<IconProps> = ({
	className = "",
	size = 24,
	style,
}) => {
	return (
		<svg
			width={size}
			height={size}
			viewBox="0 0 18 18"
			fill="currentColor"
			xmlns="http://www.w3.org/2000/svg"
			className={className}
			style={{ flexShrink: 0, ...style }}
		>
			<path d="M17 3.588v10.083l-4.763 4.33L6.738 15.5v2.5L2.476 13.204l10.524.81V4.263L17 3.588zm-3.238-.879L8.262 0v2.5l-5.238 1.7L0 7.225v5.063l2.476 1.263V6.163l11.286-3.454z" />
		</svg>
	);
};

/**
 * SharePoint logo icon
 */
export const SharePointIcon: React.FC<IconProps> = ({
	className = "",
	size = 24,
	style,
}) => {
	return (
		<img
			src="/logos/sharepoint-icon.svg"
			alt="SharePoint"
			width={size}
			height={size}
			className={className}
			style={{ flexShrink: 0, ...style }}
		/>
	);
};

/**
 * Salesforce logo icon
 */
export const SalesforceIcon: React.FC<IconProps> = ({
	className = "",
	size = 24,
	style,
}) => {
	return (
		<img
			src="/logos/salesforce-icon.svg"
			alt="Salesforce"
			width={size}
			height={size}
			className={className}
			style={{ flexShrink: 0, ...style }}
		/>
	);
};

/**
 * Microsoft Teams logo icon
 */
export const TeamsIcon: React.FC<IconProps> = ({
	className = "",
	size = 24,
	style,
}) => {
	return (
		<img
			src="/logos/teams-icon.svg"
			alt="Teams"
			width={size}
			height={size}
			className={className}
			style={{ flexShrink: 0, ...style }}
		/>
	);
};

/**
 * Azure Data Factory logo icon
 */
export const AdfIcon: React.FC<IconProps> = ({
	className = "",
	size = 24,
	style,
}) => {
	return (
		<img
			src="/logos/adf-icon.svg"
			alt="Azure Data Factory"
			width={size}
			height={size}
			className={className}
			style={{ flexShrink: 0, ...style }}
		/>
	);
};

/**
 * OneDrive logo icon
 */
export const OneDriveIcon: React.FC<IconProps> = ({
	className = "",
	size = 24,
	style,
}) => {
	return (
		<img
			src="/logos/onedrive-logo.svg"
			alt="OneDrive"
			width={size}
			height={size}
			className={className}
			style={{ flexShrink: 0, ...style }}
		/>
	);
};

/**
 * Microsoft Fabric logo icon
 */
export const FabricIcon: React.FC<IconProps> = ({
	className = "",
	size = 24,
	style,
}) => {
	return (
		<img
			src="/logos/fabric-icon.svg"
			alt="Microsoft Fabric"
			width={size}
			height={size}
			className={className}
			style={{ flexShrink: 0, ...style }}
		/>
	);
};

/**
 * GitHub icon wrapper with style support
 */
export const GithubIcon: React.FC<IconProps> = ({
	className = "",
	size = 24,
	style,
}) => {
	return <Github className={className} size={size} style={style} />;
};

/**
 * Terminal icon wrapper with style support
 */
export const TerminalIcon: React.FC<IconProps> = ({
	className = "",
	size = 24,
	style,
}) => {
	return <Terminal className={className} size={size} style={style} />;
};

/**
 * Provider visual configuration for MCP nodes
 */
export interface McpProviderVisual {
	icon: React.ComponentType<IconProps>;
	color: string;
	colorRgb: string;
	label: string;
	description: string;
}

export const MCP_PROVIDER_VISUALS: Record<string, McpProviderVisual> = {
	github: {
		icon: GithubIcon,
		color: "#f0883e",
		colorRgb: "240, 136, 62",
		label: "GitHub",
		description: "Access repositories, issues, PRs, and GitHub Actions",
	},
	notion: {
		icon: NotionIcon,
		color: "#00a3bf",
		colorRgb: "0, 163, 191",
		label: "Notion",
		description: "Access databases, pages, and workspace content",
	},
	atlassian: {
		icon: AtlassianIcon,
		color: "#0052cc",
		colorRgb: "0, 82, 204",
		label: "Atlassian",
		description: "Jira issues, Confluence pages, and Bitbucket repos",
	},
	databricks: {
		icon: DatabricksIcon,
		color: "#FF3621",
		colorRgb: "255, 54, 33",
		label: "Databricks Catalog",
		description: "Access Unity Catalog functions and data via MCP",
	},
	databricks_devops: {
		icon: AzureDevOpsIcon,
		color: "#0078D4",
		colorRgb: "0, 120, 212",
		label: "DevOps",
		description:
			"Databricks workspace & Azure DevOps notebook management",
	},
	sharepoint: {
		icon: SharePointIcon,
		color: "#0078D4",
		colorRgb: "0, 120, 212",
		label: "SharePoint",
		description: "Access SharePoint sites, document libraries, and files",
	},
	onedrive: {
		icon: OneDriveIcon,
		color: "#0078D4",
		colorRgb: "0, 120, 212",
		label: "OneDrive",
		description: "Access personal and shared files from OneDrive",
	},
	fabric: {
		icon: FabricIcon,
		color: "#2AAC94",
		colorRgb: "42, 172, 148",
		label: "Microsoft Fabric",
		description: "Access Fabric workspaces, lakehouses, notebooks, and pipelines",
	},
	canva: {
		icon: CanvaIcon,
		color: "#00c4cc",
		colorRgb: "0, 196, 204",
		label: "Canva",
		description: "Create and manage designs, templates, and assets",
	},
	salesforce: {
		icon: SalesforceIcon,
		color: "#00A1E0",
		colorRgb: "0, 161, 224",
		label: "Salesforce",
		description: "Access Salesforce CRM data, objects, and automation",
	},
	teams: {
		icon: TeamsIcon,
		color: "#6264A7",
		colorRgb: "98, 100, 167",
		label: "Teams",
		description: "Access Microsoft Teams channels, messages, and meetings",
	},
	adf: {
		icon: AdfIcon,
		color: "#0078D4",
		colorRgb: "0, 120, 212",
		label: "Azure Data Factory",
		description: "Manage data pipelines, datasets, and data flows",
	},
	// Default fallback for generic MCP servers
	default: {
		icon: TerminalIcon,
		color: "var(--color-primary)",
		colorRgb: "var(--color-primary-rgb)",
		label: "MCP Server",
		description: "Connect to Model Context Protocol servers",
	},
};

/**
 * Get provider visuals with fallback to default
 */
export function getProviderVisuals(provider: string): McpProviderVisual {
	return MCP_PROVIDER_VISUALS[provider] || MCP_PROVIDER_VISUALS.default;
}

/**
 * Detect MCP provider key from a node name string.
 * Returns a key into MCP_PROVIDER_VISUALS or null if no match.
 */
export function detectProviderFromNodeName(
	nodeName: string,
): string | null {
	const lower = nodeName.toLowerCase();

	if (lower.includes("devops")) return "databricks_devops";
	if (lower.includes("databricks")) return "databricks";
	if (lower.includes("onedrive")) return "onedrive";
	if (lower.includes("sharepoint")) return "sharepoint";
	if (lower.includes("notion")) return "notion";
	if (lower.includes("github")) return "github";
	if (
		lower.includes("atlassian") ||
		lower.includes("jira") ||
		lower.includes("confluence")
	)
		return "atlassian";
	if (lower.includes("fabric")) return "fabric";
	if (lower.includes("canva")) return "canva";
	if (lower.includes("salesforce")) return "salesforce";
	if (lower.includes("teams")) return "teams";
	if (lower.includes("data factory") || lower.includes("adf"))
		return "adf";

	return null;
}
