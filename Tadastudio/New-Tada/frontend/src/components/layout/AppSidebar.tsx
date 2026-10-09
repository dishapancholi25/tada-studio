"use client";

import type { LucideIcon } from "lucide-react";
import {
	BookOpen,
	Database,
	FlaskConical,
	FolderOpen,
	History,
	MessageCircle,
	ScrollText,
	Settings,
	Shield,
	Upload,
	Workflow,
} from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import Tooltip from "@/components/ui/Tooltip";
import { useFeatureAccess } from "@/contexts/FeatureAccessContext";
import * as evalApi from "@/lib/evaluation-api";

interface NavItem {
	id: string;
	label: string;
	icon: LucideIcon;
}

const NAV_ITEMS: NavItem[] = [
	{ id: "workflow",    label: "Dashboard",    icon: Workflow      },
	{ id: "library",     label: "Library",      icon: BookOpen      },
	{ id: "manage",      label: "My Workflows", icon: FolderOpen    },
	{ id: "chat",        label: "Playground",         icon: MessageCircle },
	{ id: "publish",     label: "Publish",      icon: Upload        },
	{ id: "history",     label: "Executions",   icon: History       },
	{ id: "evaluations", label: "Evaluations",  icon: FlaskConical  },
	{ id: "guardrails",  label: "Guardrails",   icon: Shield        },
	{ id: "datasources", label: "Data Sources", icon: Database      },
	{ id: "wiki",        label: "Wiki",         icon: ScrollText    },
];

const FEATURE_MAP: Record<string, string> = {
	workflow:    "nav.workflow",
	library:     "nav.library",
	publish:     "nav.publish",
	datasources: "nav.datasources",
	history:     "nav.executions",
	manage:      "nav.manage",
	evaluations: "nav.evaluations",
	chat:        "nav.chat",
	wiki:        "nav.wiki",
};

interface AppSidebarProps {
	collapsed: boolean;
}

const ORANGE = "#FF5E00";

export default function AppSidebar({ collapsed }: AppSidebarProps) {
	const router   = useRouter();
	const pathname = usePathname();
	const { canAccessFeature } = useFeatureAccess();
	const [evalBadgeCount, setEvalBadgeCount] = useState(0);

	const activeTab = useMemo(() => {
		if (pathname === "/executions")                                      return "history";
		if (pathname?.startsWith("/library"))                               return "library";
		if (pathname === "/publish")                                         return "publish";
		if (pathname === "/settings" || pathname?.startsWith("/settings/")) return "settings";
		if (pathname === "/datasources")                                     return "datasources";
		if (pathname === "/evaluations")                                     return "evaluations";
		if (pathname?.startsWith("/chat"))                                   return "chat";
		if (pathname?.startsWith("/guardrails"))                             return "guardrails";
		if (pathname === "/manage")                                          return "manage";
		if (pathname?.startsWith("/wiki"))                                   return "wiki";
		return "workflow";
	}, [pathname]);

	const visibleItems = useMemo(
		() =>
			NAV_ITEMS.filter((item) => {
				const feat = FEATURE_MAP[item.id];
				return feat ? canAccessFeature(feat) : true;
			}),
		// eslint-disable-next-line react-hooks/exhaustive-deps
		[canAccessFeature],
	);

	const navigate = (tabId: string) => {
		if (tabId === "workflow") {
			router.push("/");
			return;
		}
		if (tabId === "manage") { router.push("/manage"); return; }
		const routes: Record<string, string> = {
			history:     "/executions",
			library:     "/library",
			publish:     "/publish",
			settings:    "/settings",
			datasources: "/datasources",
			evaluations: "/evaluations",
			guardrails:  "/guardrails",
			chat:        "/chat",
			wiki:        "/wiki",
		};
		if (routes[tabId]) router.push(routes[tabId]);
	};

	// Eval badge polling
	useEffect(() => {
		const poll = async () => {
			try {
				const runs = await evalApi.listRuns({ status: "completed", limit: 20 });
				const lastSeen = localStorage.getItem("eval_last_seen_at") ?? "1970-01-01T00:00:00.000Z";
				setEvalBadgeCount(runs.filter((r) => r.completed_at && r.completed_at > lastSeen).length);
			} catch { /* silent */ }
		};
		poll();
		const id = setInterval(poll, 60_000);
		return () => clearInterval(id);
	}, []);

	useEffect(() => {
		if (pathname === "/evaluations") {
			localStorage.setItem("eval_last_seen_at", new Date().toISOString());
			setEvalBadgeCount(0);
		}
	}, [pathname]);

	// ─── single nav row ──────────────────────────────────────────────────────
	const renderItem = (item: NavItem) => {
		const isActive = activeTab === item.id;
		const Icon = item.icon;

		const button = (
			<button
				type="button"
				data-tutorial={`nav-${item.id}`}
				onClick={() => navigate(item.id)}
				className="group relative flex w-full cursor-pointer items-center focus-visible:outline-none"
				style={{ height: 44 }}
				aria-current={isActive ? "page" : undefined}
				aria-label={item.label}
			>
				{/* orange right accent bar */}
				{isActive && (
					<span
						className="absolute right-0 top-1/2 -translate-y-1/2 rounded-l-full"
						style={{ width: 3, height: 28, background: ORANGE }}
					/>
				)}

				{/* icon container — always centred in 56 px */}
				<span
					className="relative flex shrink-0 items-center justify-center transition-colors duration-150"
					style={{ width: 56, height: 44, color: isActive ? ORANGE : "#9ca3af" }}
				>
					<Icon className="h-[20px] w-[20px]" />

					{/* eval badge */}
					{item.id === "evaluations" && evalBadgeCount > 0 && (
						<span className="absolute top-2 right-2 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[9px] font-bold text-white">
							{evalBadgeCount > 9 ? "9+" : evalBadgeCount}
						</span>
					)}
				</span>

				{/* label — only when expanded */}
				{!collapsed && (
					<span
						className="truncate text-sm"
						style={{ color: isActive ? ORANGE : "#374151", fontWeight: isActive ? 600 : 400 }}
					>
						{item.label}
					</span>
				)}
			</button>
		);

		return (
			<Tooltip 
				key={item.id} 
				content={item.label} 
				position="right" 
				disabled={!collapsed}
			>
				{button}
			</Tooltip>
		);
	};

	// ─── sidebar ─────────────────────────────────────────────────────────────
	return (
		<aside
			data-tutorial="nav-bar"
			role="navigation"
			aria-label="Main navigation"
			className="fixed left-0 top-14 z-50 flex flex-col overflow-hidden border-r border-gray-100 bg-white shadow-sm transition-[width] duration-300 ease-in-out"
			style={{ width: collapsed ? 56 : 240, height: "calc(100vh - 56px)" }}
		>
			{/* ── Nav items ── */}
			<nav className="flex flex-1 flex-col overflow-y-auto overflow-x-hidden py-1">
				{visibleItems.map(renderItem)}
			</nav>

			{/* ── Footer: Settings ── */}
			<div className="shrink-0 border-t border-gray-100 py-1">
				{renderItem({ id: "settings", label: "Settings", icon: Settings })}
			</div>
		</aside>
	);
}
