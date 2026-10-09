"use client";

import {
	AlertCircle,
	BookOpen,
	Bot,
	Cpu,
	Database,
	FlaskConical,
	FolderOpen,
	Globe,
	History,
	Info,
	Key,
	Palette,
	Shield,
	ShieldCheck,
	Upload,
	Wrench,
} from "lucide-react";
import type React from "react";
import { useEffect, useState } from "react";
import { useToast } from "@/contexts/ToastContext";
import { ApiError, adminAPI, type FeatureAccess } from "@/lib/admin-api";

interface FeatureConfig {
	featureName: string;
	icon: React.ElementType;
	displayName: string;
	description: string;
	category: "settings" | "navigation";
}

const SETTINGS_FEATURES: FeatureConfig[] = [
	{
		featureName: "settings.database",
		icon: Database,
		displayName: "Database Settings",
		description: "Configure database connections and data sources",
		category: "settings",
	},
	{
		featureName: "settings.llm_providers",
		icon: Cpu,
		displayName: "LLM Providers",
		description: "Manage LLM deployment configurations",
		category: "settings",
	},
	{
		featureName: "settings.external_services",
		icon: Globe,
		displayName: "External Services",
		description: "Configure external service API keys",
		category: "settings",
	},
	{
		featureName: "settings.external_tools",
		icon: Wrench,
		displayName: "External Tools",
		description: "Configure external tools and MCP servers",
		category: "settings",
	},
	{
		featureName: "settings.appearance",
		icon: Palette,
		displayName: "Appearance",
		description: "Customize UI theme and appearance",
		category: "settings",
	},
	{
		featureName: "settings.api_tokens",
		icon: Key,
		displayName: "API Tokens",
		description: "Manage personal access tokens",
		category: "settings",
	},
];

const NAVIGATION_FEATURES: FeatureConfig[] = [
	{
		featureName: "nav.workflow",
		icon: Bot,
		displayName: "Workflow Editor",
		description: "Access to the workflow editor and canvas",
		category: "navigation",
	},
	{
		featureName: "nav.library",
		icon: BookOpen,
		displayName: "Library",
		description: "Access to workflow and agent template library",
		category: "navigation",
	},
	{
		featureName: "nav.publish",
		icon: Upload,
		displayName: "Publish",
		description: "Publish workflows and agents to the library",
		category: "navigation",
	},
	{
		featureName: "nav.datasources",
		icon: Database,
		displayName: "Data Sources",
		description: "Manage document uploads and data sources",
		category: "navigation",
	},
	{
		featureName: "nav.executions",
		icon: History,
		displayName: "Executions",
		description: "View workflow execution history and logs",
		category: "navigation",
	},
	{
		featureName: "nav.manage",
		icon: FolderOpen,
		displayName: "Manage Workflows",
		description: "Manage saved workflows",
		category: "navigation",
	},
	{
		featureName: "nav.evaluations",
		icon: FlaskConical,
		displayName: "Evaluations",
		description: "Access to workflow evaluation and testing tools",
		category: "navigation",
	},
	{
		featureName: "nav.guardrails",
		icon: ShieldCheck,
		displayName: "Guardrails",
		description: "Access to guardrail policies and violation monitoring",
		category: "navigation",
	},
];

export default function AdminTab() {
	const { showToast } = useToast();
	const [features, setFeatures] = useState<FeatureAccess[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [updatingFeature, setUpdatingFeature] = useState<string | null>(null);

	useEffect(() => {
		loadFeatureAccess();
	}, []);

	const loadFeatureAccess = async () => {
		try {
			setLoading(true);
			setError(null);
			const data = await adminAPI.listFeatureAccess();
			setFeatures(data);
		} catch (err) {
			const errorMessage =
				err instanceof ApiError
					? err.message
					: "Failed to load feature access settings";
			setError(errorMessage);
			showToast("error", errorMessage);
		} finally {
			setLoading(false);
		}
	};

	const handleToggle = async (
		featureName: string,
		currentAdminOnly: boolean,
	) => {
		try {
			setUpdatingFeature(featureName);
			const newAdminOnly = !currentAdminOnly;

			await adminAPI.updateFeatureAccess(featureName, newAdminOnly);

			// Update local state
			setFeatures((prev) =>
				prev.map((f) =>
					f.feature_name === featureName
						? { ...f, admin_only: newAdminOnly }
						: f,
				),
			);

			showToast(
				"success",
				`${featureName} is now ${newAdminOnly ? "Admin Only" : "available to All Users"}`,
			);
		} catch (err) {
			const errorMessage =
				err instanceof ApiError
					? err.message
					: "Failed to update feature access";
			showToast("error", errorMessage);
		} finally {
			setUpdatingFeature(null);
		}
	};

	const getFeatureData = (featureName: string): FeatureAccess | undefined => {
		return features.find((f) => f.feature_name === featureName);
	};

	if (loading) {
		return (
			<div className="flex items-center justify-center h-64">
				<div className="text-center">
					<div
						className="animate-spin rounded-full h-12 w-12 border-b-2 mx-auto mb-4"
						style={{ borderColor: "var(--color-primary)" }}
					></div>
					<p className="text-sm" style={{ color: "var(--color-text-muted)" }}>
						Loading feature access settings...
					</p>
				</div>
			</div>
		);
	}

	if (error) {
		return (
			<div className="flex items-center justify-center h-64">
				<div className="text-center max-w-md">
					<AlertCircle
						className="h-12 w-12 mx-auto mb-4"
						style={{ color: "var(--color-error)" }}
					/>
					<h3
						className="text-lg font-semibold mb-2"
						style={{ color: "var(--color-text-primary)" }}
					>
						Failed to Load Settings
					</h3>
					<p
						className="text-sm mb-4"
						style={{ color: "var(--color-text-secondary)" }}
					>
						{error}
					</p>
					<button
						onClick={loadFeatureAccess}
						className="px-4 py-2 rounded-lg transition-colors"
						style={{
							background: "var(--color-primary)",
							color: "white",
						}}
						onMouseEnter={(e) => (e.currentTarget.style.opacity = "0.9")}
						onMouseLeave={(e) => (e.currentTarget.style.opacity = "1")}
					>
						Try Again
					</button>
				</div>
			</div>
		);
	}

	return (
		<div className="space-y-6 p-6">
			{/* Header */}
			<div
				className="flex items-start gap-4 pb-6 border-b"
				style={{ borderColor: "var(--color-border)" }}
			>
				<div
					className="p-3 rounded-lg"
					style={{ background: "rgba(var(--color-primary-rgb), 0.1)" }}
				>
					<Shield
						className="h-6 w-6"
						style={{ color: "var(--color-primary)" }}
					/>
				</div>
				<div className="flex-1">
					<h2
						className="text-xl font-semibold mb-2"
						style={{ color: "var(--color-text-primary)" }}
					>
						Admin Settings
					</h2>
					<p
						className="text-sm"
						style={{ color: "var(--color-text-secondary)" }}
					>
						Configure access control for settings tabs and navigation menu
						items. Determine which features require admin privileges and which
						are available to all authenticated users.
					</p>
				</div>
			</div>

			{/* Info Banner */}
			<div className="pb-6">
				<div className="flex items-start gap-3">
					<Info
						className="h-5 w-5 flex-shrink-0 mt-0.5"
						style={{ color: "var(--color-text-muted)" }}
					/>
					<div
						className="text-sm"
						style={{ color: "var(--color-text-primary)" }}
					>
						<p className="font-medium mb-1">Access Control Levels:</p>
						<ul
							className="space-y-1 ml-4 list-disc"
							style={{ color: "var(--color-text-secondary)" }}
						>
							<li>
								<strong>Admin Only:</strong> Only users with admin privileges
								can access this feature
							</li>
							<li>
								<strong>All Users:</strong> All authenticated users can access
								this feature
							</li>
						</ul>
					</div>
				</div>
			</div>

			{/* Settings Features Section */}
			<div className="space-y-4">
				<h3
					className="text-lg font-semibold"
					style={{ color: "var(--color-text-primary)" }}
				>
					Settings Tab Access Control
				</h3>

				<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
					{SETTINGS_FEATURES.map((config) => {
						const featureData = getFeatureData(config.featureName);
						const adminOnly = featureData?.admin_only ?? true;
						const isUpdating = updatingFeature === config.featureName;
						const Icon = config.icon;

						return (
							<div
								key={config.featureName}
								className={`
                  rounded-lg p-4 transition-all
                  ${isUpdating ? "opacity-50 cursor-not-allowed" : ""}
                `}
								style={{
									background: "var(--color-bg-secondary)",
									border: `1px solid var(--color-border)`,
								}}
							>
								<div className="flex items-start justify-between mb-3">
									<div className="flex items-center gap-3">
										<div
											className="p-2 rounded-lg"
											style={{
												background: adminOnly
													? "rgba(255, 152, 0, 0.1)"
													: "rgba(76, 175, 80, 0.1)",
											}}
										>
											<Icon
												className="h-5 w-5"
												style={{
													color: adminOnly ? "#FF9800" : "#4CAF50",
												}}
											/>
										</div>
										<div>
											<h4
												className="font-medium"
												style={{ color: "var(--color-text-primary)" }}
											>
												{config.displayName}
											</h4>
											<p
												className="text-xs mt-0.5"
												style={{ color: "var(--color-text-muted)" }}
											>
												{config.description}
											</p>
										</div>
									</div>
								</div>

								<div
									className="flex items-center justify-between pt-3 border-t"
									style={{ borderColor: "var(--color-border)" }}
								>
									<div className="flex items-center gap-2">
										<span
											className="text-sm font-medium"
											style={{
												color: adminOnly ? "#FF9800" : "#4CAF50",
											}}
										>
											{adminOnly ? "Admin Only" : "All Users"}
										</span>
									</div>

									<button
										onClick={() => handleToggle(config.featureName, adminOnly)}
										disabled={isUpdating}
										className={`
                      relative inline-flex h-6 w-11 items-center rounded-full transition-colors
                      ${
												isUpdating
													? "cursor-not-allowed opacity-50"
													: "hover:opacity-80 cursor-pointer"
											}
                    `}
										style={{
											background: adminOnly ? "#FF9800" : "#4CAF50",
										}}
										aria-label={`Toggle ${config.displayName} access`}
									>
										<span
											className={`
                        inline-block h-4 w-4 transform rounded-full bg-white transition-transform
                        ${adminOnly ? "translate-x-1" : "translate-x-6"}
                      `}
										/>
									</button>
								</div>
							</div>
						);
					})}
				</div>
			</div>

			{/* Navigation Menu Access Control Section */}
			<div className="space-y-4">
				<h3
					className="text-lg font-semibold"
					style={{ color: "var(--color-text-primary)" }}
				>
					Navigation Menu Access Control
				</h3>

				<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
					{NAVIGATION_FEATURES.map((config) => {
						const featureData = getFeatureData(config.featureName);
						const adminOnly = featureData?.admin_only ?? true;
						const isUpdating = updatingFeature === config.featureName;
						const Icon = config.icon;

						return (
							<div
								key={config.featureName}
								className={`
                  rounded-lg p-4 transition-all
                  ${isUpdating ? "opacity-50 cursor-not-allowed" : ""}
                `}
								style={{
									background: "var(--color-bg-secondary)",
									border: `1px solid var(--color-border)`,
								}}
							>
								<div className="flex items-start justify-between mb-3">
									<div className="flex items-center gap-3">
										<div
											className="p-2 rounded-lg"
											style={{
												background: adminOnly
													? "rgba(255, 152, 0, 0.1)"
													: "rgba(76, 175, 80, 0.1)",
											}}
										>
											<Icon
												className="h-5 w-5"
												style={{
													color: adminOnly ? "#FF9800" : "#4CAF50",
												}}
											/>
										</div>
										<div>
											<h4
												className="font-medium"
												style={{ color: "var(--color-text-primary)" }}
											>
												{config.displayName}
											</h4>
											<p
												className="text-xs mt-0.5"
												style={{ color: "var(--color-text-muted)" }}
											>
												{config.description}
											</p>
										</div>
									</div>
								</div>

								<div
									className="flex items-center justify-between pt-3 border-t"
									style={{ borderColor: "var(--color-border)" }}
								>
									<div className="flex items-center gap-2">
										<span
											className="text-sm font-medium"
											style={{
												color: adminOnly ? "#FF9800" : "#4CAF50",
											}}
										>
											{adminOnly ? "Admin Only" : "All Users"}
										</span>
									</div>

									<button
										onClick={() => handleToggle(config.featureName, adminOnly)}
										disabled={isUpdating}
										className={`
                      relative inline-flex h-6 w-11 items-center rounded-full transition-colors
                      ${
												isUpdating
													? "cursor-not-allowed opacity-50"
													: "hover:opacity-80 cursor-pointer"
											}
                    `}
										style={{
											background: adminOnly ? "#FF9800" : "#4CAF50",
										}}
										aria-label={`Toggle ${config.displayName} access`}
									>
										<span
											className={`
                        inline-block h-4 w-4 transform rounded-full bg-white transition-transform
                        ${adminOnly ? "translate-x-1" : "translate-x-6"}
                      `}
										/>
									</button>
								</div>
							</div>
						);
					})}
				</div>
			</div>
		</div>
	);
}
