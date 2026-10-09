"use client";

import { Clock, Edit, Tag, Trash2 } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import StyledMarkdown from "@/components/utils/StyledMarkdown";
import WikiBreadcrumb from "@/components/wiki/WikiBreadcrumb";
import WikiSidebar from "@/components/wiki/WikiSidebar";
import WikiTableOfContents from "@/components/wiki/WikiTableOfContents";
import { useAuth } from "@/contexts/AuthContext";
import { useNotification } from "@/contexts/NotificationContext";
import { wikiApi, WikiApiError, type WikiPageResponse } from "@/lib/wiki-api";

export default function WikiPageView() {
	const params = useParams();
	const router = useRouter();
	const { user } = useAuth();
	const isAdmin = user?.is_admin === true;
	const { showError } = useNotification();
	const slug = params.slug as string;

	const [page, setPage] = useState<WikiPageResponse | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [deleting, setDeleting] = useState(false);
	const [confirmDelete, setConfirmDelete] = useState(false);

	useEffect(() => {
		if (slug) fetchPage();
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [slug]);

	const fetchPage = async () => {
		setLoading(true);
		setError(null);
		try {
			const data = await wikiApi.getPage(slug);
			setPage(data);
		} catch (err) {
			if (err instanceof WikiApiError && err.status === 404) {
				setError("Page not found");
			} else {
				setError("Failed to load page");
			}
		} finally {
			setLoading(false);
		}
	};

	const handleDelete = async () => {
		if (!confirmDelete) {
			setConfirmDelete(true);
			return;
		}
		setDeleting(true);
		try {
			await wikiApi.deletePage(slug);
			window.dispatchEvent(new Event("wiki:refresh"));
			router.push("/wiki");
		} catch (err: unknown) {
			showError(err instanceof WikiApiError ? err.detail : "Failed to delete page");
			setDeleting(false);
			setConfirmDelete(false);
		}
	};

	return (
		<div className="flex h-full overflow-hidden">
			<WikiSidebar />

			{/* Main content area */}
			<div className="flex-1 flex overflow-hidden">
				{/* Article */}
				<div className="custom-scrollbar flex-1 overflow-y-auto bg-white">
					{loading && (
						<div className="mx-auto max-w-3xl space-y-4 px-8 py-8">
							<div className="h-10 w-2/3 animate-pulse rounded-xl bg-slate-200" />
							<div className="h-4 w-1/3 animate-pulse rounded-lg bg-slate-100" />
							<div className="mt-6 h-64 animate-pulse rounded-2xl bg-slate-100" />
						</div>
					)}

					{error && (
						<div className="mx-auto max-w-3xl px-8 py-16 text-center">
							<div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-slate-200 bg-white">
								<Clock className="h-7 w-7 text-slate-400" />
							</div>
							<h1 className="mb-2 text-xl font-semibold text-slate-900">{error}</h1>
							<Link
								href="/wiki"
								className="text-sm text-orange-700 transition-colors hover:text-slate-900 hover:underline"
							>
								← Back to Wiki
							</Link>
						</div>
					)}

					{page && !loading && (
						<article className="mx-auto max-w-3xl px-8 py-8">
							<WikiBreadcrumb currentSlug={slug} />
							{/* Page header */}
							<div className="mb-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-[0_10px_28px_rgba(15,23,42,0.08)]">
								<div className="mb-3 flex items-start justify-between gap-4">
									<h1 className="text-3xl font-semibold leading-tight text-slate-900">
										{page.title}
									</h1>

									{/* Action buttons */}
									<div className="mt-1 flex flex-shrink-0 items-center gap-2">
										<Link
											href={`/wiki/${slug}/history`}
											title="Version history"
											className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-700 transition-all hover:border-orange-400 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
										>
											<Clock className="h-3.5 w-3.5" />
											v{page.version}
										</Link>
										{isAdmin && (
											<>
												<Link
													href={`/wiki/${slug}/edit`}
													title="Edit page"
													className="flex items-center gap-1.5 rounded-lg border border-orange-500 bg-orange-500 px-3 py-1.5 text-xs font-medium text-white transition-all hover:border-orange-600 hover:bg-orange-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
												>
													<Edit className="h-3.5 w-3.5" />
													Edit
												</Link>
												<button
													type="button"
													onClick={handleDelete}
													disabled={deleting}
													title={confirmDelete ? "Click again to confirm deletion" : "Delete page"}
													className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500/25 disabled:opacity-50 ${
														confirmDelete
															? "border-red-500 bg-red-50 text-red-700 shadow-[0_4px_16px_rgba(15,23,42,0.08)]"
															: "border-slate-200 bg-white text-slate-700 hover:border-red-400 hover:bg-red-50/80 hover:text-red-800"
													}`}
												>
													<Trash2 className="w-3.5 h-3.5" />
													{confirmDelete ? "Confirm?" : "Delete"}
												</button>
											</>
										)}
									</div>
								</div>

								{/* Metadata row */}
								<div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-600">
									<span>
										Updated{" "}
										{new Date(page.updated_at ?? page.created_at).toLocaleDateString(undefined, {
											month: "long",
											day: "numeric",
											year: "numeric",
										})}
									</span>
									{page.tags && page.tags.length > 0 && (
										<div className="flex items-center gap-1.5">
											<Tag className="h-3 w-3 text-slate-500" />
											{page.tags.map((tag) => (
												<span
													key={tag}
													className="rounded-full border border-slate-200 bg-white px-2 py-0.5 text-[10px] font-medium text-slate-800"
												>
													{tag}
												</span>
											))}
										</div>
									)}
								</div>

								<div className="mt-5 h-px bg-slate-200" />
							</div>

							{/* Content */}
							<div className="prose prose-slate max-w-none text-slate-800">
								<StyledMarkdown content={page.content} variant="light" />
							</div>
						</article>
					)}
				</div>

				{/* Right TOC — only on xl+ */}
				{page && (
					<div className="hidden xl:block w-64 flex-shrink-0 overflow-y-auto custom-scrollbar py-8 px-4">
						<WikiTableOfContents content={page.content} />
					</div>
				)}
			</div>
		</div>
	);
}
