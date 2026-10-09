// frontend/src/components/auth/AuthGuard.tsx
"use client";

import type React from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import PendingUserPanel from "@/components/auth/PendingUserPanel";

const PUBLIC_ROUTES = ["/login"];
const SKIP_AUTH = process.env.NEXT_PUBLIC_SKIP_AUTH === "true";

interface AuthGuardProps {
	children: React.ReactNode;
}

export const AuthGuard: React.FC<AuthGuardProps> = ({ children }) => {
	const { isAuthenticated, user, logout, apiReady, loading } = useAuth();
	const pathname = usePathname();
	const router = useRouter();

	// Public routes bypass authentication entirely
	if (PUBLIC_ROUTES.includes(pathname)) {
		return <>{children}</>;
	}

	// While auth context is initialising, always show spinner
	if (loading) {
		return (
			<div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-white to-[#ff6b00]">
				<div className="flex flex-col items-center gap-4">
					<div className="w-12 h-12 animate-spin rounded-full border-[3px] border-white/40 border-t-white" />
					<p className="text-white text-lg animate-pulse drop-shadow">Loading...</p>
				</div>
			</div>
		);
	}

	// Not authenticated after init
	if (!isAuthenticated) {
		if (SKIP_AUTH) {
			// In skip-auth mode redirect to local login page
			if (typeof window !== "undefined") {
				router.replace("/login");
			}
			return null;
		}
		// OAuth mode: proxy handles the redirect; show spinner while it does
		return (
			<div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-white to-[#ff6b00]">
				<div className="flex flex-col items-center gap-4">
					<div className="w-12 h-12 animate-spin rounded-full border-[3px] border-white/40 border-t-white" />
					<p className="text-white text-lg animate-pulse drop-shadow">
						Loading...
					</p>
				</div>
			</div>
		);
	}

	// Check if user is pending approval
	if (apiReady && user?.is_pending) {
		return (
			<PendingUserPanel
				userEmail={user.email}
				userName={user.name}
				onRetry={async () => {
					// Re-fetch user status by reloading the page
					window.location.reload();
				}}
				onSignOut={logout}
			/>
		);
	}

	return <>{children}</>;
};
