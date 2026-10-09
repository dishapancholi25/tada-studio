"use client";

import { BookOpen, Clock, FileText, Plus, Search, AlertTriangle } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import WikiSidebar from "@/components/wiki/WikiSidebar";
import { useAuth } from "@/contexts/AuthContext";
import { wikiApi, WikiApiError, type WikiPageListItem } from "@/lib/wiki-api";

export default function WikiHomePage() {
	const [pages, setPages] = useState<WikiPageListItem[]>([]);
	const [loading, setLoading] = useState(true);
	const [featureDisabled, setFeatureDisabled] = useState(false);
	const router = useRouter();
	const { user } = useAuth();
	const isAdmin = user?.is_admin === true;

	const fetchPages = useCallback(async () => {
		try {
			const data = await wikiApi.listPages();
			setPages(data);
		} catch (error) {
			// Check if wiki feature is disabled (404 response)
			if (error instanceof WikiApiError && error.status === 404) {
				setFeatureDisabled(true);
			}
			// silent for other errors
		} finally {
			setLoading(false);
		}
	}, []);

	useEffect(() => {
		fetchPages();
	}, [fetchPages]);

	// Show feature disabled state
	if (featureDisabled) {
		return (
			<div className="flex h-full items-center justify-center bg-white">
				<div className="text-center max-w-md px-6">
					<div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-2xl border border-slate-200 bg-white shadow-[0_10px_28px_rgba(15,23,42,0.06)]">
						<AlertTriangle className="h-8 w-8 text-amber-500" />
					</div>
					<h1 className="text-xl font-semibold text-slate-900 mb-2">Wiki Not Available</h1>
					<p className="text-sm text-slate-600 mb-6">
						The wiki feature is currently disabled. Please contact your administrator if you need access.
					</p>
					<button
						onClick={() => router.push("/")}
						className="inline-flex items-center gap-2 rounded-[4px] border border-slate-300 bg-white px-5 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
					>
						Go to Home
					</button>
				</div>
			</div>
		);
	}

	const recentPages = [...pages]
		.sort((a, b) => {
			const da = new Date(a.updated_at ?? a.created_at).getTime();
			const db = new Date(b.updated_at ?? b.created_at).getTime();
			return db - da;
		})
		.slice(0, 6);

	const isEmpty = !loading && pages.length === 0;

	return (
		<div className="flex h-full overflow-hidden bg-white">
			<WikiSidebar />

			{/* Main content */}
			<div className="custom-scrollbar flex-1 overflow-y-auto">
				<div className="mx-auto max-w-screen-2xl px-4 sm:px-6 lg:px-8 py-4 sm:py-6">
					{/* Header */}
					<div className="flex items-start justify-between mb-8">
						<div className="flex items-center gap-4">
							<div className="rounded-2xl border border-slate-200 bg-white p-3 shadow-[0_10px_28px_rgba(15,23,42,0.06)]">
								<BookOpen className="h-7 w-7 text-orange-600" />
							</div>
							<div>
								<h1 className="text-2xl font-semibold text-slate-900">Wiki</h1>
								<p className="text-sm text-slate-600 mt-0.5">
									{loading ? "Loading…" : `${pages.length} page${pages.length !== 1 ? "s" : ""}`}
								</p>
							</div>
						</div>

						{isAdmin && (
							<Link
								href="/wiki/new"
								className="flex items-center gap-2 rounded-[4px] border border-orange-500 bg-orange-500 px-4 py-2 text-xs font-medium text-white transition-colors hover:border-orange-600 hover:bg-orange-600"
							>
								<Plus className="w-3.5 h-3.5" />
								New page
							</Link>
						)}
					</div>

					{/* Empty state */}
					{isEmpty && (
						<div className="rounded-2xl border border-slate-200 bg-white p-16 text-center shadow-[0_10px_28px_rgba(15,23,42,0.06)]">
							<div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-2xl border border-slate-200 bg-white shadow-[0_10px_28px_rgba(15,23,42,0.06)]">
								<BookOpen className="h-8 w-8 text-orange-600" />
							</div>
							<h2 className="text-lg font-semibold text-slate-900 mb-2">No pages yet</h2>
							<p className="text-sm text-slate-600 mb-8 max-w-sm mx-auto">
								{isAdmin
									? "Create your first wiki page to get started."
									: "No wiki pages have been published yet."}
							</p>
							{isAdmin && (
								<Link
									href="/wiki/new"
									className="inline-flex items-center gap-2 rounded-[4px] border border-orange-500 bg-orange-500 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:border-orange-600 hover:bg-orange-600"
								>
									<Plus className="w-4 h-4" />
									Create a page
								</Link>
							)}
						</div>
					)}

					{/* Content when pages exist */}
					{!isEmpty && !loading && (
						<div className="space-y-8">
							{/* Quick search */}
							<div className="relative">
								<Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
								<input
									type="text"
									placeholder="Search pages… (use the sidebar for full search)"
									className="w-full rounded-2xl border border-slate-200 bg-white py-3 pl-11 pr-4 text-sm text-slate-900 shadow-[0_4px_16px_rgba(15,23,42,0.06)] transition-colors placeholder:text-slate-400 hover:border-orange-400 focus:border-orange-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/20"
									onKeyDown={(e) => {
										if (e.key === "Enter" && e.currentTarget.value.trim()) {
											window.location.href = `/wiki?q=${encodeURIComponent(e.currentTarget.value)}`;
										}
									}}
								/>
							</div>

							{/* Recently updated */}
							<div>
								<div className="mb-4 flex items-center gap-2">
									<Clock className="h-4 w-4 text-slate-600" />
									<h2 className="text-xs font-semibold uppercase text-slate-800">
										Recently Updated
									</h2>
								</div>
								<div className="grid gap-3 sm:grid-cols-2">
									{recentPages.map((page) => (
										<Link
											key={page.id}
											href={`/wiki/${page.slug}`}
											className="group block rounded-2xl border border-slate-200 bg-white p-4 shadow-[0_8px_24px_rgba(15,23,42,0.06)] transition-all duration-200 hover:-translate-y-0.5 hover:border-orange-400 hover:shadow-[0_12px_32px_rgba(15,23,42,0.08)]"
										>
											<div className="flex items-start gap-3">
												<div className="mt-0.5 flex-shrink-0 rounded-lg border border-slate-200 bg-white p-1.5">
													<FileText className="h-3.5 w-3.5 text-orange-600" />
												</div>
												<div className="min-w-0">
													<h3 className="text-sm font-medium text-slate-900 truncate group-hover:text-slate-900 transition-colors">
														{page.title}
													</h3>
													<p className="mt-0.5 text-xs text-slate-600">
														{new Date(page.updated_at ?? page.created_at).toLocaleDateString(undefined, {
															month: "short",
															day: "numeric",
															year: "numeric",
														})}
													</p>
												</div>
											</div>
											{page.tags && page.tags.length > 0 && (
												<div className="flex gap-1.5 mt-3 flex-wrap">
													{page.tags.slice(0, 3).map((tag) => (
														<span
															key={tag}
															className="rounded-full border border-slate-200 bg-white px-2 py-0.5 text-[10px] font-medium text-slate-800 transition-colors group-hover:border-orange-400 group-hover:text-slate-900"
														>
															{tag}
														</span>
													))}
												</div>
											)}
										</Link>
									))}
								</div>
							</div>

							{/* All pages */}
							{pages.length > 6 && (
								<div>
									<div className="mb-4 flex items-center gap-2">
										<FileText className="h-4 w-4 text-slate-600" />
										<h2 className="text-xs font-semibold uppercase text-slate-800">
											All Pages ({pages.length})
										</h2>
									</div>
									<div className="divide-y divide-slate-200 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[0_8px_24px_rgba(15,23,42,0.06)]">
										{pages.map((page) => (
											<Link
												key={page.id}
												href={`/wiki/${page.slug}`}
												className="group flex items-center gap-3 border-l-4 border-transparent px-4 py-3 transition-colors first:rounded-t-2xl last:rounded-b-2xl hover:border-orange-500 hover:bg-slate-50"
											>
												<FileText className="h-3.5 w-3.5 flex-shrink-0 text-slate-400 group-hover:text-slate-900" />
												<span className="flex-1 truncate text-sm text-slate-800 transition-colors group-hover:text-slate-900">
													{page.title}
												</span>
												<span className="flex-shrink-0 text-xs text-slate-600">
													{new Date(page.updated_at ?? page.created_at).toLocaleDateString(undefined, {
														month: "short",
														day: "numeric",
													})}
												</span>
											</Link>
										))}
									</div>
								</div>
							)}
						</div>
					)}

					{loading && (
						<div className="space-y-3">
							{[1, 2, 3].map((i) => (
								<div
									key={i}
									className="h-20 rounded-2xl bg-slate-50 border border-slate-200 animate-pulse"
								/>
							))}
						</div>
					)}
				</div>
			</div>
		</div>
	);
}
