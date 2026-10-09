"use client";

import DataSources from "@/components/core/DataSources";
import AppShell from "@/components/layout/AppShell";

export default function DataSourcesPage() {
	return (
		<AppShell>
			<div className="h-screen flex flex-col bg-white overflow-hidden">
				<DataSources />
			</div>
		</AppShell>
	);
}
