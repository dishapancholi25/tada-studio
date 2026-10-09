"use client";

import { Users, User, ShieldCheck, Shield } from "lucide-react";
import { useState, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import AdminTab from "./AdminTab";
import GroupsTabContent from "./admin/GroupsTabContent";
import NetworkSecurityTab from "./admin/NetworkSecurityTab";
import UsersTabContent from "./admin/UsersTabContent";

type AdminSubTab = "users" | "groups" | "settings" | "network-security";

interface SubTab {
	id: AdminSubTab;
	label: string;
	icon: React.ElementType;
}

const subTabs: SubTab[] = [
	{
		id: "users",
		label: "Users",
		icon: User,
	},
	{
		id: "groups",
		label: "Groups",
		icon: Users,
	},
	{
		id: "settings",
		label: "Access",
		icon: ShieldCheck,
	},
	{
		id: "network-security",
		label: "Network Security",
		icon: Shield,
	},
];

export default function AdminSettingsContainer() {
	const searchParams = useSearchParams();
	const router = useRouter();
	const initialSubTab = (searchParams?.get("subtab") as AdminSubTab) || "users";
	const [activeSubTab, setActiveSubTab] = useState<AdminSubTab>(initialSubTab);

	// Update URL when subtab changes
	const handleSubTabChange = (subTab: AdminSubTab) => {
		setActiveSubTab(subTab);
		// Update URL with subtab parameter
		const params = new URLSearchParams(window.location.search);
		params.set("tab", "admin");
		params.set("subtab", subTab);
		router.push(`${window.location.pathname}?${params.toString()}`, {
			scroll: false,
		});
	};

	const renderSubTabContent = () => {
		switch (activeSubTab) {
			case "users":
				return <UsersTabContent />;
			case "groups":
				return <GroupsTabContent />;
			case "settings":
				return <AdminTab />;
			case "network-security":
				return <NetworkSecurityTab />;
			default:
				return null;
		}
	};

	return (
		<div className="space-y-6">
			{/* Sub-tab Navigation */}
			<div
				className="rounded-xl p-2 overflow-x-auto"
				style={{
					background: "var(--color-bg-secondary)",
					border: "1px solid var(--color-border)",
				}}
			>
				<div className="flex gap-2 md:flex-wrap">
					{subTabs.map((tab) => {
						const Icon = tab.icon;
						return (
							<button
								key={tab.id}
								onClick={() => handleSubTabChange(tab.id)}
								className={`flex items-center gap-2 px-4 py-2.5 rounded-lg font-medium transition-all duration-200 whitespace-nowrap flex-shrink-0`}
								style={{
									color:
										activeSubTab === tab.id
											? "var(--nav-link-active)"
											: "var(--color-text-primary)",
									background:
										activeSubTab === tab.id
											? "rgba(var(--color-primary-rgb), 0.18)"
											: "transparent",
									border:
										activeSubTab === tab.id
											? "1px solid var(--nav-link-active)"
											: "1px solid transparent",
								}}
							>
								<Icon className="w-4 h-4" />
								<span>{tab.label}</span>
							</button>
						);
					})}
				</div>
			</div>

			{/* Sub-tab Content */}
			<div
				className="rounded-xl"
				style={{
					background: "var(--color-surface)",
					border: "1px solid var(--color-border)",
				}}
			>
				{renderSubTabContent()}
			</div>
		</div>
	);
}
