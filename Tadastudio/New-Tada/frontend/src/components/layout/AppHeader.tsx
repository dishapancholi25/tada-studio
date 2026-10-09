"use client";

import {
	ChevronLeft,
	LogOut,
	Menu,
	PanelRightOpen,
	Shield,
	User,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useAuth } from "@/contexts/AuthContext";

// ── Env flags ────────────────────────────────────────────────────────────────
// NEXT_PUBLIC_ vars are inlined at build time by Next.js.
// Add these to your .env to hide the icons:
//   NEXT_PUBLIC_HEADER_SHOW_BELL=false
//   NEXT_PUBLIC_HEADER_SHOW_PROFILE=false
const SHOW_BELL = process.env.NEXT_PUBLIC_HEADER_SHOW_BELL !== "false";
const SHOW_PROFILE = process.env.NEXT_PUBLIC_HEADER_SHOW_PROFILE !== "false";

const ORANGE = "#ff6b00";
const ORANGE_RGB = "255,107,0";

interface AppHeaderProps {
	sidebarWidth: number;
	collapsed: boolean;
	onToggle: () => void;
}

// ── Brand logo mark ───────────────────────────────────────────────────────────
function BrandLogoMark() {
	return (
		<div
			className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg"
		>
			{/* Replace the SVG below with <img src="/logo.png" … /> for a real logo */}
			<img src="/tada-icon-new.png" alt="Logo" className="h-10 w-10 object-contain object-center" />
		</div>
	);
}

// ── Header ────────────────────────────────────────────────────────────────────
export default function AppHeader({ sidebarWidth, collapsed, onToggle }: AppHeaderProps) {
	const { user, logout } = useAuth();
	const [showUserMenu, setShowUserMenu] = useState(false);
	const [isLogoHovered, setIsLogoHovered] = useState(false);
	const userMenuRef = useRef<HTMLDivElement>(null);

	const handleSignOut = async () => {
		try { await logout(); } catch (e) { console.error("Logout failed:", e); }
	};

	// Close dropdown on outside click / Escape
	useEffect(() => {
		function onOutside(e: MouseEvent) {
			if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
				setShowUserMenu(false);
			}
		}
		function onEscape(e: KeyboardEvent) {
			if (e.key === "Escape") setShowUserMenu(false);
		}
		document.addEventListener("mousedown", onOutside);
		document.addEventListener("keydown", onEscape);
		return () => {
			document.removeEventListener("mousedown", onOutside);
			document.removeEventListener("keydown", onEscape);
		};
	}, []);

	const userInitials = useMemo(() => {
		if (!user) return "";
		if (user.name) {
			const parts = user.name.split(" ").filter(Boolean)
				.map((p: string) => p[0]?.toUpperCase()).filter(Boolean).slice(0, 2);
			if (parts.length) return parts.join("");
		}
		return user.email ? user.email.slice(0, 2).toUpperCase() : "";
	}, [user]);

	return (
		<header className="fixed left-0 right-0 top-0 z-[51] flex h-14 items-center border-b border-gray-100 bg-white shadow-sm">

			{/* ── Left: brand / logo section — mirrors sidebar width ── */}
			<div
				className="relative flex shrink-0 items-center border-r border-gray-100 transition-[width] duration-300 ease-in-out"
				style={{ width: sidebarWidth, height: 56 }}
			>
				{collapsed ? (
					/* Collapsed: Mashreq logo centred, changes to hamburger on hover */
					<button
						type="button"
						onClick={onToggle}
						onMouseEnter={() => setIsLogoHovered(true)}
						onMouseLeave={() => setIsLogoHovered(false)}
						className="flex h-full w-full items-center justify-center overflow-hidden bg-slate-50/70 transition-colors hover:bg-[rgba(255,94,0,0.05)] focus-visible:outline-none px-2"
						aria-label="Expand sidebar"
						aria-expanded={false}
					>
						{isLogoHovered ? (
							/* Hamburger menu icon on hover */
							<Menu className="h-6 w-6 text-[#FF5E00] transition-all" />
						) : (
							/* Mashreq logo when not hovering */
							<img src="/logo.png" alt="Mashreq" className="h-9 w-10 shrink-0 object-cover object-center transition-all" />
						)}
					</button>
				) : (
					/* Expanded: logo left, collapse button right */
					<div className="flex h-full w-full items-center justify-between bg-slate-50/70 px-4">
						{/* Primary logo */}
						<img src="/logo.png" alt="Mashreq" className="h-10 w-auto max-w-[168px] shrink-0 object-contain" />
						<button
							type="button"
							onClick={onToggle}
							className="flex h-8 w-8 items-center justify-center rounded-md border border-gray-200 bg-white text-gray-500 transition-all hover:border-[#FF5E00] hover:bg-[rgba(255,94,0,0.05)] hover:text-[#FF5E00] focus-visible:outline-none"
							aria-label="Collapse sidebar"
							aria-expanded={true}
							title="Collapse sidebar"
						>
							<PanelRightOpen className="h-5 w-5" />
						</button>
					</div>
				)}
			</div>

			{/* ── App name + logo ── */}
			<div className="flex items-center gap-3 pl-5">
				<BrandLogoMark />
				<span className="select-none text-lg font-bold tracking-tight text-[#0A0A0A]">
					TADA STUDIO
				</span>
			</div>

			{/* ── Spacer ── */}
			<div className="flex-1" />

			{/* ── Right: bell + profile ── */}
			<div className="flex items-center gap-1 pr-4">

				{/* Bell - placeholder, notifications are in workspace */}
				{SHOW_BELL && (
					<button
						type="button"
						className="flex h-9 w-9 items-center justify-center rounded-lg text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-900 focus-visible:outline-none"
						aria-label="Notifications"
					>
						<svg className="h-[18px] w-[18px]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
							<path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
						</svg>
					</button>
				)}

				{/* Profile avatar + dropdown */}
				{SHOW_PROFILE && user && (
					<div className="relative ml-1" ref={userMenuRef}>
						<button
							type="button"
							onClick={() => setShowUserMenu((prev) => !prev)}
							className="flex h-9 w-9 items-center justify-center rounded-full text-[11px] font-semibold transition-colors focus-visible:outline-none"
							style={{
								background: `rgba(${ORANGE_RGB},0.12)`,
								color: ORANGE,
								boxShadow: showUserMenu
									? `0 0 0 2px rgba(${ORANGE_RGB},0.35), 0 0 0 4px rgba(${ORANGE_RGB},0.08)`
									: undefined,
							}}
							aria-haspopup="menu"
							aria-expanded={showUserMenu}
							aria-label="User menu"
						>
							{userInitials || <User className="h-4 w-4" />}
						</button>

						{showUserMenu && (
							<div
								className="absolute right-0 top-full z-50 mt-2 w-56 overflow-hidden rounded-xl border border-gray-100 bg-white shadow-lg"
								role="menu"
							>
								<div className="border-b border-gray-100 px-4 py-3">
									<p className="text-sm font-semibold text-gray-900">
										{user.name || "User"}
									</p>
									{user.email && (
										<p className="mt-0.5 truncate text-xs text-gray-500">
											{user.email}
										</p>
									)}
								</div>
								{user?.is_admin && (
									<div
										className="border-b border-gray-100 px-4 py-2.5"
										style={{ background: `rgba(${ORANGE_RGB},0.06)` }}
									>
										<div className="flex items-center gap-2">
											<Shield className="h-4 w-4" style={{ color: ORANGE }} />
											<span className="text-sm font-medium" style={{ color: ORANGE }}>
												Administrator
											</span>
										</div>
									</div>
								)}
								<button
									type="button"
									onClick={handleSignOut}
									className="flex w-full items-center gap-3 px-4 py-3 text-sm text-gray-700 transition-colors duration-150 hover:bg-orange-50 hover:text-slate-900"
									role="menuitem"
								>
									<LogOut className="h-4 w-4" />
									<span>Sign Out</span>
								</button>
							</div>
						)}
					</div>
				)}
			</div>
		</header>
	);
}
