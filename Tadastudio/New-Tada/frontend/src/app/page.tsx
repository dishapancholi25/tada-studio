"use client";

import { lazy, Suspense, useEffect, useMemo, useRef, useState } from "react";
import AgentBuilder from "@/components/core/AgentBuilder";
import AppShell from "@/components/layout/AppShell";
import {
	Activity,
	BookOpen,
	Bot,
	Calendar,
	ChevronDown,
	Database,
	Download,
	FlaskConical,
	FolderOpen,
	History,
	Info,
	Link,
	Plus,
	Search,
	TrendingUp,
	Users,
	Workflow,
} from "lucide-react";
import { format } from "date-fns";
import { motion } from "framer-motion";
import { useRouter, useSearchParams } from "next/navigation";
import { useGraph } from "@/contexts/GraphContext";
import WelcomeDialog from "@/tutorial/WelcomeDialog";
import { api } from "@/lib/api";
import * as evalApi from "@/lib/evaluation-api";

const GraphManagementDialog = lazy(
	() => import("@/components/core/GraphManagementDialog"),
);

// ─── Types ────────────────────────────────────────────────────────────────────

interface Stats {
	workflows: number;
	libraryWorkflows: number;
	agentTemplates: number;
	executions: number;
	collections: number;
	databases: number;
	endpoints: number;
	evaluations: number;
}

interface RunRow {
	id: string;
	workflowId: string | null;
	graphName: string;
	status: string;
	startedAt: string | null;
	department: string;
}

type GraphExecutionListItem = {
	id?: string;           // database UUID (from execution-history API)
	workflow_id?: string;  // Workflow UUID (required by analytics endpoints)
	execution_id?: string; // websocket execution ID or legacy field
	graph_name?: string;
	status?: string;
	started_at?: string;
	start_time?: string;   // backend alias for started_at
	completed_at?: string;
	end_time?: string;     // backend alias for completed_at
	department?: string;
	metadata?: Record<string, unknown>;
};

function normalizeGraphExecutions(value: unknown): GraphExecutionListItem[] {
	if (!value || typeof value !== "object") return [];
	if (Array.isArray(value)) return value as GraphExecutionListItem[];
	const v = value as Record<string, unknown>;
	// Database-backed response: { executions: [...], total_count: N, has_more: bool }
	if (Array.isArray(v.executions)) return v.executions as GraphExecutionListItem[];
	// In-memory fallback response: { active_executions: [...], recent_executions: [...] }
	const active = Array.isArray(v.active_executions)
		? (v.active_executions as GraphExecutionListItem[])
		: [];
	const recent = Array.isArray(v.recent_executions)
		? (v.recent_executions as GraphExecutionListItem[])
		: [];
	return [...active, ...recent];
}

interface DashboardInsight {
	recentRuns: RunRow[];
	librarySectors: Array<{ name: string; total: number }>;
	activityByDay: Array<{ label: string; count: number }>;
	activeRuns: number;
	completedRuns: number;
	failedRuns: number;
	thisWeek: number;
}

// ─── Demo / fallback data ─────────────────────────────────────────────────────

const DEMO_RUNS: RunRow[] = [
	{ id: "d1", workflowId: null, graphName: "Invoice exception handling", status: "completed", startedAt: "2023-03-15T00:00:00Z", department: "BBG" },
	{ id: "d2", workflowId: null, graphName: "Invoice exception handling", status: "failed",    startedAt: "2022-07-08T00:00:00Z", department: "CXCG" },
	{ id: "d3", workflowId: null, graphName: "Sales outreach drafts",      status: "completed", startedAt: "2020-11-11T00:00:00Z", department: "Payments" },
	{ id: "d4", workflowId: null, graphName: "Invoice exception handling", status: "running",   startedAt: "2021-09-05T00:00:00Z", department: "Finance" },
	{ id: "d5", workflowId: null, graphName: "Invoice exception handling", status: "failed",    startedAt: "2023-06-01T00:00:00Z", department: "23456789012" },
	{ id: "d6", workflowId: null, graphName: "Sales outreach drafts",      status: "completed", startedAt: "2024-08-19T00:00:00Z", department: "3210987654" },
	{ id: "d7", workflowId: null, graphName: "Tanzi's Odyssey",            status: "completed", startedAt: "2024-02-29T00:00:00Z", department: "5432199876" },
];

const DEMO_SECTORS = [
	{ name: "Finance",           total: 5 },
	{ name: "Operations",        total: 4 },
	{ name: "Customer service",  total: 4 },
	{ name: "Technology",        total: 3 },
	{ name: "Risk & Compliance", total: 3 },
	{ name: "General",           total: 3 },
	{ name: "RBG",               total: 2 },
	{ name: "CXCG",              total: 2 },
	{ name: "Payments",          total: 1 },
	{ name: "RetailBanking",     total: 1 },
];

const DEMO_ACTIVITY = [
	{ label: "04-10", count: 3 },
	{ label: "04-15", count: 5 },
	{ label: "04-16", count: 4 },
	{ label: "04-17", count: 7 },
	{ label: "04-20", count: 2 },
	{ label: "04-22", count: 6 },
	{ label: "04-25", count: 4 },
];

const DEMO_STATS: Stats = {
	workflows: 12,
	libraryWorkflows: 28,
	agentTemplates: 8,
	executions: 7,
	collections: 5,
	databases: 3,
	endpoints: 6,
	evaluations: 4,
};
const DEMO_ACTIVE_RUNS = 1;
const DEMO_COMPLETED_RUNS = 4;
const DEMO_FAILED_RUNS = 2;
const DEMO_THIS_WEEK = 31;

const CARD_DESCRIPTION =
	"Shows participation levels across different departments to highlight engagement.";

const STATUS_STYLES: Record<string, { bg: string; text: string }> = {
	completed: { bg: "bg-[#F1F8E9]", text: "text-[#1B5E20]" },
	failed:    { bg: "bg-[#FFEBEE]", text: "text-[#B00020]" },
	running:   { bg: "bg-[#FFF1E8]", text: "text-[#FF5E00]" },
	paused:    { bg: "bg-[#FFF8E1]", text: "text-[#F57C00]" },
};

function SectionHeading({ title, tooltip }: { title: string; tooltip: string }) {
	return (
		<div className="flex items-center gap-2">
			<h2 className="text-[24px] font-semibold text-[#333333]">{title}</h2>
			<div className="group/section-tooltip relative flex h-4 w-4 items-center justify-center rounded-full border border-[#D7D7D7] bg-[#FBFBFB] text-[#4C4C4C]">
				<Info className="h-2.5 w-2.5" />
				<div className="pointer-events-none absolute left-1/2 top-full z-30 mt-2 w-56 -translate-x-1/2 rounded bg-[#252525] px-2.5 py-1.5 text-[11px] font-medium leading-snug text-white opacity-0 shadow-md transition-all duration-200 group-hover/section-tooltip:translate-y-1 group-hover/section-tooltip:opacity-100">
					{tooltip}
				</div>
			</div>
		</div>
	);
}

function formatDate(dateStr: string): string {
	try {
		return format(new Date(dateStr), "MMMM d, yyyy");
	} catch {
		return "—";
	}
}

// ─── Neural network background (unchanged) ────────────────────────────────────

function NeuralNetworkBackground() {
	const canvasRef = useRef<HTMLCanvasElement | null>(null);
	const rafRef = useRef<number | null>(null);

	useEffect(() => {
		const canvas = canvasRef.current;
		if (!canvas) return;

		const ctx = canvas.getContext("2d");
		if (!ctx) return;

		const prefersReducedMotion =
			typeof window !== "undefined" &&
			window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;
		if (prefersReducedMotion) return;

		let width = 0;
		let height = 0;
		let dpr = 1;

		const resize = () => {
			dpr = window.devicePixelRatio || 1;
			width = Math.max(1, window.innerWidth);
			height = Math.max(1, window.innerHeight);
			canvas.width = Math.floor(width * dpr);
			canvas.height = Math.floor(height * dpr);
			canvas.style.width = `${width}px`;
			canvas.style.height = `${height}px`;
			ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
		};

		resize();
		window.addEventListener("resize", resize);

		const points = Array.from({ length: 70 }, () => ({
			x: Math.random() * width,
			y: Math.random() * height,
			vx: (Math.random() - 0.5) * 0.35,
			vy: (Math.random() - 0.5) * 0.35,
			r: 1.6 + Math.random() * 1.6,
		}));

		const ORANGE = "249,115,22";
		const lineDist = 140;

		const tick = () => {
			ctx.clearRect(0, 0, width, height);

			for (const p of points) {
				p.x += p.vx;
				p.y += p.vy;
				if (p.x < 0 || p.x > width) p.vx *= -1;
				if (p.y < 0 || p.y > height) p.vy *= -1;
			}

			for (let i = 0; i < points.length; i++) {
				const p = points[i];
				ctx.beginPath();
				ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
				ctx.fillStyle = `rgba(${ORANGE},0.46)`;
				ctx.fill();

				for (let j = i + 1; j < points.length; j++) {
					const q = points[j];
					const dx = p.x - q.x;
					const dy = p.y - q.y;
					const dist = Math.hypot(dx, dy);
					if (dist < lineDist) {
						const a = (1 - dist / lineDist) * 0.34;
						ctx.strokeStyle = `rgba(${ORANGE},${a})`;
						ctx.lineWidth = 1;
						ctx.beginPath();
						ctx.moveTo(p.x, p.y);
						ctx.lineTo(q.x, q.y);
						ctx.stroke();
					}
				}
			}

			rafRef.current = requestAnimationFrame(tick);
		};

		rafRef.current = requestAnimationFrame(tick);

		return () => {
			window.removeEventListener("resize", resize);
			if (rafRef.current) cancelAnimationFrame(rafRef.current);
		};
	}, []);

	return (
		<canvas
			ref={canvasRef}
			aria-hidden="true"
			className="pointer-events-none absolute inset-0"
		/>
	);
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function Home() {
	const [showGraphDialog, setShowGraphDialog] = useState(false);
	const [graphDialogTab, setGraphDialogTab] = useState<"create" | "load">("load");
	const [tableFilter, setTableFilter] = useState<"all" | "completed" | "failed" | "paused">("all");
	const [tableSearch, setTableSearch] = useState("");

	const [stats, setStats] = useState<Stats>({
		workflows: 0,
		libraryWorkflows: 0,
		agentTemplates: 0,
		executions: 0,
		collections: 0,
		databases: 0,
		endpoints: 0,
		evaluations: 0,
	});

	const [insight, setInsight] = useState<DashboardInsight>({
		recentRuns: [],
		librarySectors: [],
		activityByDay: [],
		activeRuns: 0,
		completedRuns: 0,
		failedRuns: 0,
		thisWeek: 0,
	});

	const { currentGraph } = useGraph();
	const router = useRouter();
	const searchParams = useSearchParams();

	useEffect(() => {
		import("@/components/core/GraphManagementDialog");
		if (currentGraph) {
			import("@/stores/graphStore").then(({ useGraphStore }) => {
				useGraphStore.getState().clearGraph();
			});
		}
	}, []); // eslint-disable-line react-hooks/exhaustive-deps

	useEffect(() => {
		if (searchParams.get("manage") === "1") {
			setShowGraphDialog(true);
			const next = new URLSearchParams(searchParams.toString());
			next.delete("manage");
			const qs = next.toString();
			router.replace(`${window.location.pathname}${qs ? `?${qs}` : ""}`, { scroll: false });
		}
	}, [searchParams, router]);

	useEffect(() => {
		Promise.allSettled([
			api.listGraphs(),
			api.getGraphExecutions(undefined, 1000),
			api.getCollections(),
			api.getDatabaseConnections(true, 0, 100),
			api.getApiEndpoints(true, 0, 100),
			evalApi.listRuns({ limit: 100 }),
			api.listLibraryItems({ count_only: true }),
			api.getToolTemplates(),
			api.getPublishedWorkflows(),
			api.getCategoryCounts(),
			api.getLLMProviders(),
		]).then(([wf, ex, col, db, ep, ev, lib, _tools, _pub, cats, _llm]) => {
			const libCounts = lib.status === "fulfilled" ? lib.value?.counts : undefined;
			const execRows = ex.status === "fulfilled" ? normalizeGraphExecutions(ex.value) : [];

			const statusBuckets = { completed: 0, failed: 0, running: 0 };
			for (const row of execRows) {
				const s = String(row.status || "").toLowerCase();
				if (s === "completed") statusBuckets.completed++;
				else if (s === "failed") statusBuckets.failed++;
				else if (s === "running") statusBuckets.running++;
			}

			const sortedRuns = [...execRows].sort((a, b) => {
				const ta = new Date(a.started_at ?? a.start_time ?? "").getTime() || 0;
				const tb = new Date(b.started_at ?? b.start_time ?? "").getTime() || 0;
				return tb - ta;
			});

			const recentRuns: RunRow[] = sortedRuns.slice(0, 10).map((row, idx) => ({
				id: String(row.id || row.execution_id || row.graph_name || idx),
				workflowId: row.workflow_id ?? null,
				graphName: String(row.graph_name || "—"),
				status: String(row.status || "unknown"),
				startedAt: row.started_at ?? row.start_time ?? null,
				department: row.department ?? (row.metadata?.department as string) ?? "—",
			}));

			// Use local date to avoid UTC-offset shifting the day boundary.
			const localDateKey = (d: Date) => {
				const y = d.getFullYear();
				const m = String(d.getMonth() + 1).padStart(2, "0");
				const day = String(d.getDate()).padStart(2, "0");
				return `${y}-${m}-${day}`;
			};
			const dayKeys: string[] = [];
			for (let i = 6; i >= 0; i--) {
				const d = new Date();
				d.setDate(d.getDate() - i);
				dayKeys.push(localDateKey(d));
			}
			const dayCounts = new Map<string, number>(dayKeys.map((k) => [k, 0]));
			for (const row of execRows) {
				const ts = row.started_at ?? row.start_time;
				if (!ts) continue;
				const key = localDateKey(new Date(ts));
				if (dayCounts.has(key)) dayCounts.set(key, (dayCounts.get(key) || 0) + 1);
			}
			const activityByDay = dayKeys.map((k) => ({
				label: k.slice(5),
				count: dayCounts.get(k) || 0,
			}));

			const thisWeek = activityByDay.reduce((s, d) => s + d.count, 0);

			let librarySectors: Array<{ name: string; total: number }> = [];
			if (cats.status === "fulfilled" && cats.value?.category_counts) {
				const cc = cats.value.category_counts as Record<string, { agents?: number; workflows?: number }>;
				librarySectors = Object.entries(cc)
					.map(([name, c]) => ({ name, total: (c.agents ?? 0) + (c.workflows ?? 0) }))
					.filter((s) => s.total > 0)
					.sort((a, b) => b.total - a.total)
					.slice(0, 10);
			}

			setStats({
				workflows: wf.status === "fulfilled" ? (wf.value?.graphs?.length ?? 0) : 0,
				libraryWorkflows: libCounts && typeof libCounts.workflows === "number" ? libCounts.workflows : 0,
				agentTemplates: libCounts && typeof libCounts.agents === "number" ? libCounts.agents : 0,
				executions: execRows.length,
				collections: col.status === "fulfilled" ? (col.value?.length ?? 0) : 0,
				databases: db.status === "fulfilled" ? (Array.isArray(db.value) ? db.value.length : 0) : 0,
				endpoints: ep.status === "fulfilled" ? (Array.isArray(ep.value) ? ep.value.length : 0) : 0,
				evaluations: ev.status === "fulfilled" ? (Array.isArray(ev.value) ? ev.value.length : 0) : 0,
			});

			setInsight({
				recentRuns,
				librarySectors,
				activityByDay,
				activeRuns: statusBuckets.running,
				completedRuns: statusBuckets.completed,
				failedRuns: statusBuckets.failed,
				thisWeek,
			});
		});
	}, []);

	// ─── Derived values ───────────────────────────────────────────────────────

	// Single gate: no executions at all → show demo data everywhere.
	// Once the user runs anything, every section switches to real data only.
	const isDemo = stats.executions === 0;

	const statsForDisplay = useMemo(
		() => (isDemo ? DEMO_STATS : stats),
		[isDemo, stats],
	);

	const sectorsForChart = useMemo(
		() => (isDemo ? DEMO_SECTORS : insight.librarySectors),
		[isDemo, insight.librarySectors],
	);

	const maxSectorTotal = useMemo(
		() => Math.max(1, ...sectorsForChart.map((s) => s.total)),
		[sectorsForChart],
	);

	const activityForChart = useMemo(
		() => (isDemo ? DEMO_ACTIVITY : insight.activityByDay),
		[isDemo, insight.activityByDay],
	);

	const runsForTable = useMemo(
		() => (isDemo ? DEMO_RUNS : insight.recentRuns),
		[isDemo, insight.recentRuns],
	);

	const filteredRuns = useMemo(() => {
		let rows = runsForTable;
		if (tableFilter !== "all")
			rows = rows.filter((r) => r.status.toLowerCase() === tableFilter);
		if (tableSearch.trim()) {
			const q = tableSearch.toLowerCase();
			rows = rows.filter(
				(r) =>
					r.graphName.toLowerCase().includes(q) ||
					r.department.toLowerCase().includes(q),
			);
		}
		return rows;
	}, [runsForTable, tableFilter, tableSearch]);

	const successRate = useMemo(() => {
		const completed = isDemo ? DEMO_COMPLETED_RUNS : insight.completedRuns;
		const failed    = isDemo ? DEMO_FAILED_RUNS    : insight.failedRuns;
		const total = completed + failed;
		return total > 0 ? Math.round((completed / total) * 100) : 0;
	}, [isDemo, insight.completedRuns, insight.failedRuns]);

	const metricCards = useMemo(
		() => [
			{ label: "Evaluations",     value: statsForDisplay.evaluations,     icon: <FlaskConical className="h-4 w-4" />, route: "/evaluations" },
			{ label: "Executions",      value: statsForDisplay.executions,      icon: <History className="h-4 w-4" />,     route: "/executions" },
			{ label: "Workflow Library",value: statsForDisplay.libraryWorkflows, icon: <BookOpen className="h-4 w-4" />,   route: "/library" },
			{ label: "Databases",       value: statsForDisplay.databases,       icon: <Database className="h-4 w-4" />,    route: "/datasources" },
			{ label: "Workflows",       value: statsForDisplay.workflows,       icon: <Workflow className="h-4 w-4" />,    route: "/" },
			{ label: "API Endpoints",   value: statsForDisplay.endpoints,       icon: <Link className="h-4 w-4" />,        route: "/datasources" },
			{ label: "Agent Templates", value: statsForDisplay.agentTemplates,  icon: <Bot className="h-4 w-4" />,         route: "/library?mode=agent-template" },
			{ label: "Collections",     value: statsForDisplay.collections,     icon: <FolderOpen className="h-4 w-4" />,  route: "/datasources" },
		],
		[statsForDisplay],
	);

	// ─── Render ───────────────────────────────────────────────────────────────

	return (
		<AppShell>
			<main
				className="h-screen flex flex-col"
				style={{ background: "#F5F5F9", color: "#333333" }}
			>
				<div className="flex-1 overflow-hidden">
					{currentGraph ? (
						<AgentBuilder />
					) : (
						<div className="relative h-full">
							{/* Neural network background — preserved */}
							<div className="absolute inset-0">
								<div className="absolute inset-0 bg-white" />
								{/* NeuralNetworkBackground deactivated — component kept for re-enable */}
								</div>

							<motion.div
								initial={{ opacity: 0, y: 16 }}
								animate={{ opacity: 1, y: 0 }}
								transition={{ duration: 0.45, ease: "easeOut" }}
								className="relative z-10 flex h-full min-h-0 flex-col overflow-y-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-6"
							>
								<div className="mx-auto w-full max-w-screen-2xl space-y-6 pb-8">

									{/* ── Header ── */}
									<div className="flex items-center justify-start">
										<motion.button
									data-tutorial="new-workflow-btn"
											type="button"
									onClick={() => { setGraphDialogTab("create"); setShowGraphDialog(true); }}
											whileHover={{ y: -2, scale: 1.02 }}
											whileTap={{ scale: 0.98 }}
											transition={{ type: "spring", stiffness: 300, damping: 20 }}
											className="flex items-center gap-2 rounded bg-[#FF5E00] px-4 py-2 text-[12px] font-semibold text-white transition-colors hover:bg-[#E05500]"
											style={{ boxShadow: "0px 16px 42px rgba(0,0,0,0.06)" }}
								>
									<Plus className="h-4 w-4" />
											Create New Workflow
										</motion.button>
									</div>

									{/* ── Charts row ── */}
									<SectionHeading
										title="Summary"
										tooltip="Visual summary of library coverage and run activity."
									/>
									<div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
										{/* Library by Sector — horizontal bars */}
										<div
											className="rounded border border-[#D7D7D7] bg-white p-5"
											style={{ boxShadow: "0px 8px 6px rgba(0,0,0,0.1)", borderRadius: "8px" }}
										>
											<div className="mb-1 flex items-center justify-between">
												<h2 className="text-[16px] font-semibold text-[#333333]">Library by sector</h2>
												<span className="flex h-5 w-5 items-center justify-center rounded-[6px] bg-[#FF5E00] text-[10px] font-bold text-white">
													{sectorsForChart.length}
												</span>
											</div>
											<p className="mb-4 text-[12px] text-[#4C4C4C]">
												Classification of the AI solution based on its purpose, domain, or risk profile.
											</p>
											<div className="space-y-2">
												{[...sectorsForChart].sort((a, b) => b.total - a.total).map((sector) => (
													<div key={sector.name} className="group/bar flex items-center gap-2">
														<span className="w-28 shrink-0 truncate text-right text-[12px] text-[#4C4C4C]">
															{sector.name}
														</span>
														<div className="relative flex-1 overflow-visible rounded-sm bg-[#FBFBFB]">
															<motion.div
																initial={false}
																whileHover={{ scaleY: 1.35 }}
																transition={{ type: "spring", stiffness: 320, damping: 20 }}
																className="h-3.5 origin-center rounded-sm bg-gradient-to-r from-[#E05500] to-[#FF5E00] transition-all duration-500"
																style={{ width: `${(sector.total / maxSectorTotal) * 100}%` }}
															/>
															<div className="pointer-events-none absolute -top-8 left-1/2 z-20 -translate-x-1/2 whitespace-nowrap rounded border border-[#D7D7D7] bg-white px-2 py-1 text-[10px] font-semibold text-[#333333] opacity-0 shadow-md transition-all duration-200 group-hover/bar:-translate-y-1 group-hover/bar:opacity-100">
																{sector.name}: {sector.total}
															</div>
														</div>
														<span className="w-4 shrink-0 text-right text-[12px] font-semibold text-[#333333]">
															{sector.total}
														</span>
													</div>
												))}
											</div>
											<p className="mt-3 text-center text-[10px] font-normal text-[#7C7C7C] tracking-wide">Number of Workflows</p>
										</div>

										{/* Run Volume — vertical bars with axes */}
										<div
											className="rounded border border-[#D7D7D7] bg-white p-5"
											style={{ boxShadow: "0px 8px 6px rgba(0,0,0,0.1)", borderRadius: "8px" }}
										>
											<h2 className="mb-1 text-[16px] font-semibold text-[#333333]">Run Volume</h2>
											<p className="mb-4 text-[12px] text-[#4C4C4C]">
												Classification of the AI solution based on its purpose, domain, or risk profile.
											</p>
											{(() => {
												const sorted = [...activityForChart].sort((a, b) => b.count - a.count);
												const maxCount = Math.max(1, ...sorted.map((d) => d.count));
												const chartH = 160;
												const yTicks = 4;
												return (
													<div className="flex gap-2">
														{/* Y-axis labels */}
														<div className="flex flex-col justify-between pr-1 shrink-0" style={{ height: chartH + 20 }}>
															{Array.from({ length: yTicks + 1 }, (_, i) => {
																const val = Math.round((maxCount / yTicks) * (yTicks - i));
																return (
																	<span key={i} className="text-[10px] leading-none text-[#7C7C7C]">
																		{val}
																	</span>
																);
															})}
														</div>

														{/* Plot area */}
														<div className="flex flex-1 flex-col">
															{/* Bars + grid */}
															<div className="relative flex items-end gap-3" style={{ height: chartH }}>
																{Array.from({ length: yTicks + 1 }, (_, i) => (
																	<div
																		key={i}
																		className="pointer-events-none absolute left-0 right-0 border-t border-[#D7D7D7]"
																		style={{ bottom: `${(i / yTicks) * 100}%`, opacity: 0.5 }}
																	/>
																))}
																{sorted.map((d) => (
																	<div key={d.label} className="group/bar relative flex flex-1 items-end justify-center">
																		<motion.div
																			initial={false}
																			whileHover={{ scaleX: 1.35, y: -4 }}
																			transition={{ type: "spring", stiffness: 320, damping: 20 }}
																			className="w-5 origin-bottom rounded-t bg-gradient-to-t from-[#E05500] to-[#FF5E00] transition-all duration-500"
																			style={{ height: `${Math.max(4, (d.count / maxCount) * chartH)}px` }}
																		/>
																		<div className="pointer-events-none absolute bottom-full left-1/2 z-20 mb-2 -translate-x-1/2 whitespace-nowrap rounded border border-[#D7D7D7] bg-white px-2 py-1 text-[10px] font-semibold text-[#333333] opacity-0 shadow-md transition-all duration-200 group-hover/bar:-translate-y-1 group-hover/bar:opacity-100">
																			{d.label}: {d.count} runs
																		</div>
																	</div>
																))}
															</div>
															{/* X-axis line */}
															<div className="border-t border-[#D7D7D7]" />
															{/* X-axis labels */}
															<div className="flex justify-between pt-1">
																{sorted.map((d) => (
																	<span key={d.label} className="text-[10px] text-[#4C4C4C] text-center" style={{ flex: "1 1 0", minWidth: 0 }}>
																		{d.label}
																	</span>
																))}
															</div>
														</div>
													</div>
												);
											})()}
											<div className="mt-3 flex items-start justify-between gap-4">
												<p className="text-center text-[10px] font-normal text-[#7C7C7C] tracking-wide flex-1">
													Date <span className="font-normal">(MM-DD — e.g. 04-17 = April 17)</span>
												</p>
											</div>
											<div className="mt-2 flex items-center gap-3 rounded bg-[#FBFBFB] px-3 py-2">
												<span className="text-[10px] text-[#4C4C4C] leading-snug">
													<span className="font-semibold text-[#333333]">Y-axis:</span> Number of workflow executions (runs) on that date.
												</span>
												<span className="mx-1 text-[#CCCCCC]">·</span>
												<span className="text-[10px] text-[#4C4C4C] leading-snug">
													<span className="font-semibold text-[#333333]">X-axis:</span> Date in MM-DD format — the first two digits are the month.
												</span>
											</div>
										</div>
							</div>

									{/* ── Metric cards 4 × 2 ── */}
									<SectionHeading
										title="Workspace metrics"
										tooltip="Quick counts across workflows, executions, library, data sources, and evaluations."
									/>
									<div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
										{metricCards.map((card) => (
											<motion.button
										key={card.label}
										type="button"
										onClick={() => router.push(card.route)}
												whileHover={{ y: -4, scale: 1.015 }}
												whileTap={{ scale: 0.985 }}
												transition={{ type: "spring", stiffness: 280, damping: 20 }}
												className="group relative overflow-hidden rounded border border-[#D7D7D7] bg-white p-4 text-left transition-shadow before:pointer-events-none before:absolute before:inset-x-0 before:top-0 before:h-1 before:bg-[linear-gradient(90deg,#FF5E00_0%,#EF7413_34%,#FF5E00_48%,#EF7413_63%,#FF5E00_78%,#EF7413_100%)] before:bg-[length:220%_100%] hover:before:animate-[library-flow-bar_5.5s_linear_infinite] hover:shadow-lg"
												style={{ boxShadow: "0px 16px 42px rgba(0,0,0,0.06)" }}
											>
												<div className="mb-3 flex items-start justify-between">
													<div className="flex h-8 w-8 items-center justify-center rounded bg-[#FF5E00] text-white">
														{card.icon}
													</div>
													<span className="flex min-w-[24px] items-center justify-center rounded-[6px] bg-[#FFF1E8] px-1.5 py-0.5 text-[12px] font-bold text-[#FF5E00]">
														{card.value}
													</span>
												</div>
												<h3 className="mb-1 text-[16px] font-semibold text-[#333333]">{card.label}</h3>
												<p className="text-[12px] font-normal leading-relaxed text-[#7C7C7C]">{CARD_DESCRIPTION}</p>
											</motion.button>
										))}
									</div>

									{/* ── Stats strip ── */}
									<SectionHeading
										title="Run summary"
										tooltip="At-a-glance activity, weekly run volume, and success rate."
									/>
									<motion.div
										initial={{ opacity: 0, y: 10 }}
										animate={{ opacity: 1, y: 0 }}
										transition={{ delay: 0.12, duration: 0.35, ease: "easeOut" }}
										className="grid grid-cols-2 lg:grid-cols-4 divide-x divide-[#D7D7D7] overflow-hidden rounded border border-[#D7D7D7] bg-white"
										style={{ boxShadow: "0px 16px 42px rgba(0,0,0,0.06)" }}
									>
										<div
											className="flex items-center gap-3 p-4"
										>
											<div
												className="flex h-9 w-9 shrink-0 items-center justify-center rounded bg-[rgba(255,94,0,0.05)] text-[#FF5E00]"
											>
												<Users className="h-5 w-5" />
											</div>
											<div>
												<p className="text-[12px] text-[#4C4C4C]">Total Workflow</p>
												<p className="text-[24px] font-semibold text-[#333333]">{statsForDisplay.workflows}</p>
											</div>
										</div>
										<div
											className="flex items-center gap-3 p-4"
										>
											<div
												className="flex h-9 w-9 shrink-0 items-center justify-center rounded bg-[rgba(255,94,0,0.05)] text-[#FF5E00]"
											>
												<Activity className="h-5 w-5" />
											</div>
											<div>
												<p className="text-[12px] text-[#4C4C4C]">Active Runs</p>
												<p className="text-[24px] font-semibold text-[#333333]">{isDemo ? DEMO_ACTIVE_RUNS : insight.activeRuns}</p>
											</div>
										</div>
										<div
											className="flex items-center gap-3 p-4"
										>
											<div
												className="flex h-9 w-9 shrink-0 items-center justify-center rounded bg-[rgba(255,94,0,0.05)] text-[#FF5E00]"
											>
												<Calendar className="h-5 w-5" />
											</div>
											<div>
												<p className="text-[12px] text-[#4C4C4C]">This week</p>
												<p className="text-[24px] font-semibold text-[#333333]">
													{isDemo ? DEMO_THIS_WEEK : insight.thisWeek}
												</p>
											</div>
										</div>
										<div
											className="flex items-center gap-3 p-4"
										>
											<div
												className="flex h-9 w-9 shrink-0 items-center justify-center rounded bg-[rgba(255,94,0,0.05)] text-[#FF5E00]"
											>
												<TrendingUp className="h-5 w-5" />
											</div>
											<div>
												<p className="text-[12px] text-[#4C4C4C]">Success Rate</p>
												<p className="text-[24px] font-semibold text-[#333333]">{successRate}%</p>
											</div>
										</div>
									</motion.div>

									{/* ── Runs table ── */}
									<SectionHeading
										title="Recent runs"
										tooltip="Latest workflow runs filtered by status and search."
									/>
									<motion.div
										initial={{ opacity: 0, y: 10 }}
										animate={{ opacity: 1, y: 0 }}
										transition={{ delay: 0.18, duration: 0.35, ease: "easeOut" }}
										className="overflow-hidden rounded border border-[#D7D7D7] bg-white"
										style={{ boxShadow: "0px 16px 42px rgba(0,0,0,0.06)" }}
									>
										{/* Tabs + search */}
										<div className="flex items-center justify-between border-b border-[#D7D7D7] px-4">
											<div className="flex items-center">
												{(["all", "completed", "failed", "paused"] as const).map((tab) => (
													<button
														key={tab}
														type="button"
														onClick={() => setTableFilter(tab)}
														className={`relative px-3 py-3 text-[14px] font-semibold transition-colors ${
															tableFilter === tab
																? "text-[#FF5E00]"
																: "text-[#4C4C4C] hover:text-[#333333]"
														}`}
													>
														{tab === "all" ? "All" : tab.charAt(0).toUpperCase() + tab.slice(1)}
														{tableFilter === tab && (
															<span
																className="absolute bottom-0 left-0 right-0 h-1 bg-[#FF5E00]"
															/>
														)}
													</button>
												))}
											</div>
											<div className="flex items-center gap-3">
												<div className="flex items-center gap-2 rounded-[6px] border border-[#D7D7D7] bg-[#FAFAF9] px-3 py-1.5">
													<Search className="h-3.5 w-3.5 text-[#7C7C7C]" />
													<input
														type="text"
														placeholder="Search"
														value={tableSearch}
														onChange={(e) => setTableSearch(e.target.value)}
														className="input-inline w-40 text-[12px] text-[#333333] placeholder:text-[#7C7C7C]"
													/>
												</div>
												<motion.button
													type="button"
													className="text-[#FF5E00] hover:text-[#E05500]"
													title="Export"
													onClick={() => {
															const header = ["Workflow", "Department", "Started", "Status"];
															const rows = filteredRuns.map((r) => [
																`"${r.graphName.replace(/"/g, '""')}"`,
																`"${r.department.replace(/"/g, '""')}"`,
																r.startedAt ? formatDate(r.startedAt) : "—",
																r.status,
															]);
															const csv = [header, ...rows].map((r) => r.join(",")).join("\n");
															const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
															const url = URL.createObjectURL(blob);
															const a = document.createElement("a");
															a.href = url;
															a.download = "recent-runs.csv";
															a.click();
															URL.revokeObjectURL(url);
														}}
													whileHover={{ y: -1, scale: 1.08 }}
													whileTap={{ scale: 0.94 }}
													transition={{ type: "spring", stiffness: 320, damping: 20 }}
												>
													<Download className="h-4 w-4" />
												</motion.button>
											</div>
										</div>

										{/* Table */}
										<table className="min-w-full text-[14px]">
											<thead>
												<tr className="border-b border-[#D7D7D7] bg-[#FBFBFB]">
													{["Workflow", "Department", "Started", "Status"].map((col) => (
														<th key={col} className="px-4 py-3 text-left text-[12px] font-semibold text-[#4C4C4C]">
															{col}
														</th>
													))}
												</tr>
											</thead>
											<tbody className="divide-y divide-[#D7D7D7]">
												{filteredRuns.map((row) => {
													const style = STATUS_STYLES[row.status.toLowerCase()] ?? {
														bg: "bg-[#FBFBFB]",
														text: "text-[#4C4C4C]",
													};
													const workflowId = row.workflowId;
													return (
														<motion.tr
															key={row.id}
															onClick={
																workflowId
																	? () =>
																			router.push(
																				`/dashboard/workflow/${encodeURIComponent(workflowId)}`,
																			)
																	: undefined
															}
															initial={{ opacity: 0, y: 6 }}
															animate={{ opacity: 1, y: 0 }}
															whileHover={workflowId ? { x: 4 } : undefined}
															transition={{ type: "spring", stiffness: 260, damping: 24 }}
															className={`transition-colors ${
																workflowId
																	? "cursor-pointer hover:bg-[#FFF1E8]"
																	: "cursor-default"
															}`}
														>
															<td className="px-4 py-3 font-semibold text-[#333333]">{row.graphName}</td>
															<td className="px-4 py-3 text-[#4C4C4C]">{row.department}</td>
															<td className="px-4 py-3 text-[#7C7C7C]">
																{row.startedAt ? formatDate(row.startedAt) : "—"}
															</td>
															<td className="px-4 py-3">
																<span
																	className={`inline-flex rounded-[6px] px-2.5 py-1 text-[12px] font-semibold capitalize ${style.bg} ${style.text}`}
																>
																	{row.status}
																</span>
															</td>
														</motion.tr>
													);
												})}
												{filteredRuns.length === 0 && (
													<tr>
														<td colSpan={4} className="px-4 py-8 text-center text-[14px] text-[#7C7C7C]">
															No runs found.
														</td>
													</tr>
												)}
											</tbody>
										</table>
									</motion.div>

							</div>
							</motion.div>
						</div>
					)}
				</div>

				<Suspense fallback={<div />}>
					<GraphManagementDialog
						isOpen={showGraphDialog}
						onClose={() => setShowGraphDialog(false)}
						initialTab={graphDialogTab}
					/>
				</Suspense>

				{false && !currentGraph && <WelcomeDialog />}
			</main>
		</AppShell>
	);
}
