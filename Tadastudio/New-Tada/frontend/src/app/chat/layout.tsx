"use client";

import AppShell from "@/components/layout/AppShell";

export default function ChatLayout({ children }: { children: React.ReactNode }) {
	return (
		<AppShell>
			<div className="flex h-full min-h-0 flex-col bg-[color:var(--color-bg-primary)]">
				<div className="flex min-h-0 flex-1 overflow-hidden">
					{children}
				</div>
			</div>
		</AppShell>
	);
}
