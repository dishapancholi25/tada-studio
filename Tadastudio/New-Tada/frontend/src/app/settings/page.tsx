"use client";

import {
	BookOpen,
	Cpu,
	Database,
	FileText,
	Globe,
	Key,
	Lock,
	Palette,
	Settings,
	Shield,
	Users,
	Wrench,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import AppShell from "@/components/layout/AppShell";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import AdminSettingsContainer from "@/components/settings/tabs/AdminSettingsContainer";
import APITokensTab from "@/components/settings/tabs/APITokensTab";
import DatabaseTab from "@/components/settings/tabs/DatabaseTab";
import EnvironmentTab from "@/components/settings/tabs/EnvironmentTab";
import ExternalServicesTab from "@/components/settings/tabs/ExternalServicesTab";
import ExternalToolsTab from "@/components/settings/tabs/ExternalToolsTab";
import LLMProvidersTab from "@/components/settings/tabs/LLMProvidersTab";
import LocalUsersTab from "@/components/settings/tabs/LocalUsersTab";
import SecurityTab from "@/components/settings/tabs/SecurityTab";
import TutorialsTab from "@/components/settings/tabs/TutorialsTab";
import { useAuth } from "@/contexts/AuthContext";
import { useColorTheme } from "@/contexts/ColorThemeContext";
import { useFeatureAccess } from "@/contexts/FeatureAccessContext";

import { useToast } from "@/contexts/ToastContext";
import { configAPI, type EnvironmentConfig } from "@/lib/config-api";

interface Tab {
	id: string;
	label: string;
	icon: React.ElementType;
	description: string;
}

// Base tabs available to all users
const baseTabs: Tab[] = [
	{
		id: "appearance",
		label: "Appearance",
		icon: Palette,
		description: "Choose your preferred theme and branding",
	},
	{
		id: "api-tokens",
		label: "API Tokens",
		icon: Key,
		description: "Manage your Personal Access Tokens for HTTP execution API",
	},
	{
		id: "llm",
		label: "LLM Providers",
		icon: Cpu,
		description: "Configure AI language model providers and settings",
	},
	{
		id: "database",
		label: "Database",
		icon: Database,
		description: "Manage database connections and settings",
	},
	{
		id: "external",
		label: "External Services",
		icon: Globe,
		description: "Configure external integrations and APIs",
	},
	{
		id: "external-tools",
		label: "External Tools",
		icon: Wrench,
		description: "Configure custom MCP servers and external tool integrations",
	},
	{
		id: "tutorials",
		label: "Tutorials",
		icon: BookOpen,
		description: "Reset your tutorial progress to replay any tutorial from the beginning.",
	},
	/* Hidden tabs - uncomment to restore
  ,{
    id: 'environment',
    label: 'Environment Variables',
    icon: FileText,
    description: 'View and manage environment configuration'
  },
  {
    id: 'security',
    label: 'Security & Advanced',
    icon: Lock,
    description: 'Security settings and advanced configuration'
  }
  */
];

// Admin-only tabs
const adminTabs: Tab[] = [
	{
		id: "admin",
		label: "Admin",
		icon: Shield,
		description: "Manage users, groups, and access control",
	},
	{
		id: "local-users",
		label: "Local Users",
		icon: Users,
		description: "Manage local email/password user accounts",
	},
];

// Tab ID to Feature Name mapping
const TAB_FEATURE_MAP: Record<string, string> = {
	database: "settings.database",
	llm: "settings.llm_providers",
	"external-tools": "settings.external_tools",
	appearance: "settings.appearance",
	"api-tokens": "settings.api_tokens",
};

function SettingsPageContent() {
	const searchParams = useSearchParams();
	const initialTab = searchParams?.get("tab") || "appearance";
	const [activeTab, setActiveTab] = useState(initialTab);
	const [config, setConfig] = useState<EnvironmentConfig | null>(null);
	const [loading, setLoading] = useState(true);
	const [externalServicesDirty, setExternalServicesDirty] = useState(false);
	const [pendingTabId, setPendingTabId] = useState<string | null>(null);
	const { showToast } = useToast();

	const { theme, setTheme } = useColorTheme();
	const { user } = useAuth();
	const router = useRouter();
	const {
		canAccessFeature,
		isFeatureAdminOnly,
		loading: featureAccessLoading,
	} = useFeatureAccess();

	// Determine if user is admin
	const isAdmin = user?.is_admin ?? false;

	// Check if local auth is enabled (for showing local-users tab)
	const [localAuthEnabled, setLocalAuthEnabled] = useState(false);
	useEffect(() => {
		fetch("/api/auth/local/status", { credentials: "include" })
			.then((r) => r.json())
			.then((data) => setLocalAuthEnabled(data.enabled === true))
			.catch(() => {});
	}, []);

	// Build tabs list based on admin status and feature access
	// Filter baseTabs to only include tabs the user has access to
	const accessibleBaseTabs = baseTabs.filter((tab) => {
		const featureName = TAB_FEATURE_MAP[tab.id];
		// If tab has no feature mapping, allow access (e.g., appearance)
		if (!featureName) return true;
		// Check if user has access to this feature
		return canAccessFeature(featureName);
	});

	const visibleAdminTabs = adminTabs.filter(
		(tab) => tab.id !== "local-users" || localAuthEnabled,
	);
	const tabs = isAdmin
		? [...accessibleBaseTabs, ...visibleAdminTabs]
		: accessibleBaseTabs;

	// Ensure activeTab is always valid (part of accessible tabs)
	useEffect(() => {
		if (tabs.length > 0 && !tabs.some((tab) => tab.id === activeTab)) {
			// Current active tab is not accessible, switch to first available tab
			setActiveTab(tabs[0].id);
		}
	}, [tabs, activeTab]);

	// Warn on browser close/navigate-away when External Services has unsaved changes
	useEffect(() => {
		if (!externalServicesDirty) return;
		const handler = (e: BeforeUnloadEvent) => {
			e.preventDefault();
		};
		window.addEventListener("beforeunload", handler);
		return () => window.removeEventListener("beforeunload", handler);
	}, [externalServicesDirty]);

	// Load system config only for admins — the endpoint is admin-gated.
	// Wait until auth is resolved (user !== undefined/null) before deciding.
	useEffect(() => {
		if (!user) return;
		if (isAdmin) {
			void loadConfiguration(true);
		} else {
			// Non-admins don't need system config; provide an empty placeholder so
			// config-dependent tabs (database, external) still render.
			setConfig({ external_services: {} } as unknown as EnvironmentConfig);
			setLoading(false);
		}
	}, [user]); // eslint-disable-line react-hooks/exhaustive-deps

	const loadConfiguration = async (isInitialLoad = false) => {
		try {
			if (isInitialLoad) setLoading(true);
			const data = await configAPI.getEnvironmentConfig(true);
			setConfig(data);
		} catch (error) {
			console.error("Failed to load configuration:", error);
			showToast("error", "Failed to load configuration");
		} finally {
			if (isInitialLoad) setLoading(false);
		}
	};

	const handleConfigUpdate = async (
		section: string,
		key: string,
		value: any,
	) => {
		try {
			const updates = { [`${section}.${key}`]: value };
			await configAPI.updateEnvironmentConfig(updates);
			showToast("success", "Configuration updated successfully");
			await loadConfiguration();
		} catch (error) {
			console.error("Failed to update configuration:", error);
			showToast("error", "Failed to update configuration");
		}
	};

	const navigateToTab = (tabId: string) => {
		setActiveTab(tabId);
		// Update URL with tab parameter
		const params = new URLSearchParams(window.location.search);
		params.set("tab", tabId);
		if (tabId !== "admin") {
			params.delete("subtab");
		}
		router.push(`${window.location.pathname}?${params.toString()}`, { scroll: false });
	};

	const handleTabClick = (tabId: string, hasAccess: boolean) => {
		if (!hasAccess || featureAccessLoading) return;
		if (externalServicesDirty && activeTab === "external" && tabId !== "external") {
			setPendingTabId(tabId);
			return;
		}
		navigateToTab(tabId);
	};

	const handleConfirmLeaveExternalServices = () => {
		if (!pendingTabId) return;
		const tabId = pendingTabId;
		setExternalServicesDirty(false);
		setPendingTabId(null);
		navigateToTab(tabId);
	};

	const renderTabContent = () => {
		// Check feature access first
		const featureName = TAB_FEATURE_MAP[activeTab];
		if (featureName && !canAccessFeature(featureName)) {
			return (
				<div className="flex flex-col items-center justify-center h-96 gap-4">
					<div className="p-6 rounded-full bg-orange-50 border border-orange-100">
						<Lock className="w-12 h-12 text-orange-600" />
					</div>
					<h3 className="text-xl font-semibold text-slate-900">
						Admin Access Required
					</h3>
					<p className="text-slate-600 text-center max-w-md">
						This feature is restricted to administrators. Please contact your
						system administrator to request access.
					</p>
				</div>
			);
		}

		// Show loading state for feature access
		if (featureAccessLoading) {
			return (
				<div className="flex items-center justify-center h-96">
					<div className="animate-pulse text-[color:var(--color-text-muted)]">
						Loading permissions...
					</div>
				</div>
			);
		}

		// Appearance tab doesn't need config loading
		if (activeTab === "appearance") {
			return (
				<div className="p-6">
					<div className="max-w-2xl">
						<h3 className="text-xl font-semibold text-slate-900 mb-6">
							Theme Selection
						</h3>
						<div className="grid grid-cols-1 md:grid-cols-2 gap-6">
							{/* Mashreq Theme */}
							<div
								className={`p-6 rounded-xl border-2 cursor-pointer transition-all duration-200 ${
									theme === "mashreq"
										? "border-[color:var(--color-primary)] shadow-lg shadow-[color:var(--color-primary)]/20"
										: "border-[color:var(--color-border)] hover:border-[color:var(--color-border-hover)]"
								}`}
								style={{
									background:
										theme === "mashreq"
											? "rgba(var(--color-primary-rgb), 0.05)"
											: "white",
								}}
								onClick={() => setTheme("mashreq")}
							>
								<div className="flex items-center gap-4 mb-4">
									<div className="w-16 h-16 rounded-xl bg-gradient-to-br from-[#ff6b00] to-[#e55f00] flex items-center justify-center">
										<div className="w-8 h-8 bg-white rounded-md opacity-90"></div>
									</div>
									<div>
										<h4 className="text-lg font-semibold text-slate-900">
											Mashreq
										</h4>
										<p className="text-slate-600 text-sm">
											Orange accent theme
										</p>
									</div>
								</div>
								<div className="flex items-center gap-2 text-sm text-slate-700">
									<div className="w-3 h-3 rounded-full bg-[#ff6b00]"></div>
									<span>Mashreq brand orange</span>
								</div>
							</div>

							{/* Expose Theme */}
							{/* <div
								className={`p-6 rounded-xl border-2 cursor-pointer transition-all duration-200 ${
									theme === "expose"
										? "border-[color:var(--color-primary)] shadow-lg shadow-[color:var(--color-primary)]/20"
										: "border-[color:var(--color-border)] hover:border-[color:var(--color-border-hover)]"
								}`}
								style={{
									background:
										theme === "expose"
											? "rgba(var(--color-primary-rgb), 0.05)"
											: "white",
								}}
								onClick={() => setTheme("expose")}
							>
								<div className="flex items-center gap-4 mb-4">
									<div className="w-16 h-16 rounded-xl bg-gradient-to-br from-[#932A8F] to-[#7A2375] flex items-center justify-center">
										<div className="w-8 h-8 bg-black rounded-md opacity-80"></div>
									</div>
									<div>
										<h4 className="text-lg font-semibold text-slate-900">Expose</h4>
										<p className="text-slate-600 text-sm">
											Purple accent theme
										</p>
									</div>
								</div>
								<div className="flex items-center gap-2 text-sm text-slate-700">
									<div className="w-3 h-3 rounded-full bg-[#932A8F]"></div>
									<span>Modern purple branding</span>
								</div>
							</div> */}
						</div>

						<div
							className="mt-8 p-4 rounded-lg"
							style={{
								background: "white",
								border: "1px solid rgb(226,232,240)",
							}}
						>
							<div className="flex items-center gap-3">
								<div className="text-slate-700">
									Current theme:
								</div>
								<div
									className="font-semibold"
									style={{ color: "var(--color-primary)" }}
								>
									{theme === "mashreq" ? "Mashreq" : "Expose"}
								</div>
							</div>
						</div>
					</div>
				</div>
			);
		}

		// API Tokens tab doesn't need config loading
		if (activeTab === "api-tokens") {
			return <APITokensTab />;
		}

		// External Tools tab doesn't need config loading
		if (activeTab === "external-tools") {
			return <ExternalToolsTab />;
		}

		// Tutorials tab doesn't need config loading
		if (activeTab === "tutorials") {
			return <TutorialsTab />;
		}

		if (loading || !config) {
			return (
				<div className="flex items-center justify-center h-96">
					<div className="animate-pulse text-[color:var(--color-text-muted)]">
						Loading configuration...
					</div>
				</div>
			);
		}

		switch (activeTab) {
			case "llm":
				return <LLMProvidersTab />;
			case "database":
				return <DatabaseTab config={config} onUpdate={handleConfigUpdate} />;
			case "external":
				return (
					<ExternalServicesTab
						config={config}
						onUpdate={handleConfigUpdate}
						onSaved={loadConfiguration}
						onHasChanges={setExternalServicesDirty}
					/>
				);
			case "admin":
				return <AdminSettingsContainer />;
			case "local-users":
				return <LocalUsersTab />;
			/* Hidden tabs - uncomment to restore
      case 'environment':
        return <EnvironmentTab />;
      case 'security':
        return <SecurityTab config={config} onUpdate={handleConfigUpdate} />;
      */
			default:
				return null;
		}
	};

	return (
		<AppShell>
		<div className="h-screen flex flex-col bg-white overflow-hidden">
			<div className="flex-1 flex flex-col mx-auto w-full max-w-screen-2xl px-4 sm:px-6 lg:px-8 py-4 sm:py-6 overflow-hidden">
				{/* Page Header */}
				<div className="mb-4 sm:mb-6 shrink-0" data-tutorial="settings-header">
					<div className="flex items-center gap-3">
						<div className="p-2.5 sm:p-3 bg-orange-50 border border-orange-100 rounded-xl">
							<Settings className="w-6 h-6 sm:w-8 sm:h-8 text-orange-600" />
						</div>
						<div>
							<h1 className="text-xl sm:text-2xl lg:text-3xl font-bold text-slate-900">Settings</h1>
							<p className="text-slate-600 text-sm sm:text-base mt-0.5 sm:mt-1 hidden sm:block">
								Configure your environment and application settings
							</p>
						</div>
					</div>
				</div>

				{/* Main Content Card */}
				<div className="flex-1 flex flex-col rounded-2xl border border-slate-200 bg-white shadow-[0_18px_50px_rgba(15,23,42,0.08)] overflow-hidden min-h-0">
					{/* Tab Navigation */}
					<div className="shrink-0 border-b border-slate-200 bg-slate-50/50">
						<div className="flex flex-wrap gap-1 sm:gap-2 p-2">
							{tabs.map((tab) => {
								const Icon = tab.icon;
								const featureName = TAB_FEATURE_MAP[tab.id];
								const hasAccess = !featureName || canAccessFeature(featureName);
								const isLocked = featureName && !hasAccess;

								return (
									<button
										key={tab.id}
										data-tutorial={`${tab.id}-tab`}
										onClick={() => handleTabClick(tab.id, hasAccess)}
										disabled={isLocked || featureAccessLoading}
										className={`flex items-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-2 sm:py-2.5 rounded-xl text-sm font-medium transition-all duration-200 whitespace-nowrap ${
											isLocked ? "cursor-not-allowed opacity-50" : ""
										} ${
											activeTab === tab.id
												? "bg-orange-500 text-white border border-orange-500 shadow-sm"
												: "bg-white text-slate-600 border border-slate-200 hover:border-orange-300 hover:text-orange-600"
										}`}
									>
										<Icon className="w-4 h-4 sm:w-5 sm:h-5" />
										<span className="hidden sm:inline">{tab.label}</span>
										{isLocked && <Lock className="w-3.5 h-3.5 sm:w-4 sm:h-4" />}
									</button>
								);
							})}
						</div>
					</div>

					{/* Tab Description - visible only on larger screens */}
					<div className="shrink-0 px-4 sm:px-6 py-3 border-b border-slate-100 bg-white hidden sm:block">
						{(() => {
							const currentTab = tabs.find((t) => t.id === activeTab);
							const featureName = TAB_FEATURE_MAP[activeTab];
							const hasAccess = !featureName || canAccessFeature(featureName);

							if (!hasAccess) {
								return (
									<div className="flex items-center gap-2">
										<Lock className="w-4 h-4 text-amber-500" />
										<p className="text-slate-600 text-sm">
											This feature is restricted to administrators.
										</p>
									</div>
								);
							}

							return (
								<p className="text-slate-600 text-sm">
									{currentTab?.description}
								</p>
							);
						})()}
					</div>

					{/* Tab Content - scrollable */}
					<div className="flex-1 overflow-y-auto min-h-0">
						{renderTabContent()}
					</div>
				</div>
			</div>
		</div>
		<ConfirmDialog
			isOpen={pendingTabId !== null}
			onClose={() => setPendingTabId(null)}
			onConfirm={handleConfirmLeaveExternalServices}
			title="Leave External Services"
			message="You have unsaved changes in External Services. Leave anyway?"
			confirmText="Leave"
			cancelText="Cancel"
			variant="warning"
			surface="light"
		/>
		</AppShell>
	);
}

export default function SettingsPage() {
	return <SettingsPageContent />;
}
