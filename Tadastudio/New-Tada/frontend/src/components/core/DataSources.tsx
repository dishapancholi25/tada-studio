"use client";

import { Database, Folder, Link } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import type React from "react";
import DatabasesTab from "../datasources/tabs/DatabasesTab";
import DocumentsTab from "../datasources/tabs/DocumentsTab";
import EndpointsTab from "../datasources/tabs/EndpointsTab";
import { api } from "@/lib/api";

interface DataSourceCounts {
	collections: number;
	databases: number;
	endpoints: number;
}

interface TabDef {
	id: string;
	label: string;
	icon: React.ReactNode;
	badge?: number;
}

export default function DataSources() {
	const [activeTab, setActiveTab] = useState("documents");
	const [counts, setCounts] = useState<DataSourceCounts>({
		collections: 0,
		databases: 0,
		endpoints: 0,
	});

	useEffect(() => {
		Promise.allSettled([
			api.getCollections(),
			api.getDatabaseConnections(true, 0, 100),
			api.getApiEndpoints(true, 0, 100),
		]).then(([colResult, dbResult, epResult]) => {
			setCounts({
				collections:
					colResult.status === "fulfilled" ? colResult.value.length : 0,
				databases:
					dbResult.status === "fulfilled" ? dbResult.value.length : 0,
				endpoints:
					epResult.status === "fulfilled" ? epResult.value.length : 0,
			});
		});
	}, []);

	const tabs: TabDef[] = [
		{
			id: "documents",
			label: "Documents",
			icon: <Folder className="w-4 h-4" />,
			badge: counts.collections > 0 ? counts.collections : undefined,
		},
		{
			id: "databases",
			label: "Databases",
			icon: <Database className="w-4 h-4" />,
			badge: counts.databases > 0 ? counts.databases : undefined,
		},
		{
			id: "endpoints",
			label: "API Endpoint",
			icon: <Link className="w-4 h-4" />,
			badge: counts.endpoints > 0 ? counts.endpoints : undefined,
		},
	];

	const handleTabChange = useCallback((tabId: string) => {
		setActiveTab(tabId);
	}, []);

	const renderTabContent = () => {
		switch (activeTab) {
			case "documents":
				return <DocumentsTab />;
			case "databases":
				return <DatabasesTab />;
			case "endpoints":
				return <EndpointsTab />;
			default:
				return null;
		}
	};

	return (
		<div className="flex-1 flex flex-col mx-auto w-full max-w-screen-2xl px-4 sm:px-6 lg:px-8 py-4 sm:py-6 overflow-hidden">
			{/* Page Header */}
			<div className="mb-4 flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 shrink-0" data-tutorial="datasources-header">
				<div>
					<h1 className="text-xl sm:text-2xl font-bold text-slate-900">Data Sources</h1>
					<p className="text-sm text-slate-500 mt-0.5 hidden sm:block">
						Manage documents, database connections, and API endpoints for your AI agents
					</p>
				</div>

				{/* Summary counts */}
				<div className="hidden md:flex items-center divide-x divide-slate-200 border border-slate-200 rounded-xl overflow-hidden bg-white text-sm shadow-sm">
					<span className="px-4 py-2 text-slate-500">
						Collections <strong className="text-slate-900 font-semibold ml-1">{counts.collections}</strong>
					</span>
					<span className="px-4 py-2 text-slate-500">
						Databases <strong className="text-slate-900 font-semibold ml-1">{counts.databases}</strong>
					</span>
					<span className="px-4 py-2 text-slate-500">
						Endpoints <strong className="text-slate-900 font-semibold ml-1">{counts.endpoints}</strong>
					</span>
				</div>
			</div>

			{/* Main Content Card */}
			<div className="flex-1 flex flex-col rounded-2xl border border-slate-200 bg-white shadow-[0_18px_50px_rgba(15,23,42,0.08)] overflow-hidden min-h-0">
				{/* Tab Navigation */}
				<div className="shrink-0 border-b border-slate-200 bg-slate-50/50">
					<div className="flex items-center gap-1 p-2 overflow-x-auto">
						{tabs.map((tab) => (
							<button
								key={tab.id}
								type="button"
								onClick={() => handleTabChange(tab.id)}
								className={`flex items-center gap-2 px-3 sm:px-4 py-2 sm:py-2.5 rounded-xl text-sm font-medium transition-all whitespace-nowrap ${
									activeTab === tab.id
										? "bg-orange-500 text-white border border-orange-500 shadow-sm"
										: "bg-white text-slate-600 border border-slate-200 hover:border-orange-300 hover:text-orange-600"
								}`}
							>
								{tab.icon}
								<span className="hidden sm:inline">{tab.label}</span>
								{tab.badge !== undefined && (
									<span className={`text-xs font-medium px-1.5 py-0.5 rounded-full ${
										activeTab === tab.id
											? "bg-white/20 text-white"
											: "bg-slate-100 text-slate-500"
									}`}>
										{tab.badge}
									</span>
								)}
							</button>
						))}
					</div>
				</div>

				{/* Tab Content - scrollable */}
				<div className="flex-1 overflow-y-auto min-h-0">
					<div key={activeTab} className="animate-fadeIn">
						{renderTabContent()}
					</div>

					{/* Quick-access DB and Endpoints cards — shown below when Documents tab is active */}
					{activeTab === "documents" && (
						<div className="grid grid-cols-1 sm:grid-cols-2 gap-4 p-4 sm:p-6">
							<div className="flex flex-col items-center justify-center gap-3 p-6 sm:p-8 bg-slate-50 border border-slate-200 rounded-xl text-center min-h-[180px] sm:min-h-[220px]">
								<div className="flex h-10 w-10 sm:h-12 sm:w-12 items-center justify-center rounded-xl bg-slate-100 text-slate-500">
									<Database className="w-5 h-5 sm:w-6 sm:h-6" />
								</div>
								<div className="flex-1 flex flex-col items-center justify-center">
									<h3 className="text-sm font-semibold text-slate-700">Database Connections</h3>
									<p className="text-xs text-slate-500 mt-1 max-w-[220px] mx-auto">
										Connect to databases to enable AI agents to query and retrieve data
									</p>
								</div>
								<button
									type="button"
									onClick={() => handleTabChange("databases")}
									className="px-4 py-2 text-sm font-medium bg-orange-500 rounded-xl text-white hover:bg-orange-600 transition-colors"
								>
									Add Database
								</button>
							</div>

							<div className="flex flex-col items-center justify-center gap-3 p-6 sm:p-8 bg-slate-50 border border-slate-200 rounded-xl text-center min-h-[180px] sm:min-h-[220px]">
								<div className="flex h-10 w-10 sm:h-12 sm:w-12 items-center justify-center rounded-xl bg-slate-100 text-slate-500">
									<Link className="w-5 h-5 sm:w-6 sm:h-6" />
								</div>
								<div className="flex-1 flex flex-col items-center justify-center">
									<h3 className="text-sm font-semibold text-slate-700">API Endpoints</h3>
									<p className="text-xs text-slate-500 mt-1 max-w-[220px] mx-auto">
										Configure API endpoints for external integrations
									</p>
								</div>
								<button
									type="button"
									onClick={() => handleTabChange("endpoints")}
									className="px-4 py-2 text-sm font-medium bg-orange-500 rounded-xl text-white hover:bg-orange-600 transition-colors"
								>
									Add Endpoint
								</button>
							</div>
						</div>
					)}
				</div>
			</div>
		</div>
	);
}
