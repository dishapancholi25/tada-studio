"use client";

import type { ReactNode } from "react";
import AppShell from "@/components/layout/AppShell";

export default function WikiLayout({ children }: { children: ReactNode }) {
	return (
		<AppShell>
			<div className="flex h-screen flex-col overflow-hidden bg-white">
				<main className="flex-1 overflow-hidden">{children}</main>
			</div>
		</AppShell>
	);
}
