"use client";

import { useEffect, useState } from "react";
import AppHeader from "./AppHeader";
import AppSidebar from "./AppSidebar";
import TutorialHelpButton from "@/tutorial/TutorialHelpButton";

interface AppShellProps {
	children: React.ReactNode;
}

const SIDEBAR_EXPANDED  = 240;
const SIDEBAR_COLLAPSED = 56;

export default function AppShell({ children }: AppShellProps) {
	const [collapsed, setCollapsed] = useState(() => {
		if (typeof window === "undefined") return true;
		return localStorage.getItem("sidebar_collapsed") !== "false";
	});

	const toggle = () => {
		const next = !collapsed;
		setCollapsed(next);
		localStorage.setItem("sidebar_collapsed", String(next));
	};

	useEffect(() => {
		const handler = () => {
			setCollapsed(true);
			localStorage.setItem("sidebar_collapsed", "true");
		};
		window.addEventListener("collapseSidebar", handler);
		return () => window.removeEventListener("collapseSidebar", handler);
	}, []);

	const sidebarWidth = collapsed ? SIDEBAR_COLLAPSED : SIDEBAR_EXPANDED;

	return (
		<>
			{/* Fixed top header — full width */}
			<AppHeader
				sidebarWidth={sidebarWidth}
				collapsed={collapsed}
				onToggle={toggle}
			/>

			{/* Fixed sidebar — starts below the header */}
			<AppSidebar collapsed={collapsed} />

			{/* Scrollable main content — offset right of sidebar and below header */}
			<div
				className="flex min-w-0 flex-1 flex-col overflow-hidden transition-[margin-left] duration-300 ease-in-out"
				style={{
					marginLeft: sidebarWidth,
					marginTop: 56,
					height: "calc(100vh - 56px)",
				}}
			>
				{children}
			</div>

			{/* Edge-mounted help button */}
			<TutorialHelpButton mode="edge" />
		</>
	);
}
