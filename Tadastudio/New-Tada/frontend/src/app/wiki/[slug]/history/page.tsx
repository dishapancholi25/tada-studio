"use client";

import { Clock, GitCompare, RotateCcw } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import WikiDiffView from "@/components/wiki/WikiDiffView";
import WikiBreadcrumb from "@/components/wiki/WikiBreadcrumb";
import WikiSidebar from "@/components/wiki/WikiSidebar";
import { useAuth } from "@/contexts/AuthContext";
import { useNotification } from "@/contexts/NotificationContext";
import { wikiApi, WikiApiError, type WikiRevision } from "@/lib/wiki-api";

export default function WikiHistoryPage() {
	const params = useParams();
	const router = useRouter();
	const { user } = useAuth();
	const isAdmin = user?.is_admin === true;
	const { showSuccess, showError } = useNotification();
	const slug = params.slug as string;

	const [revisions, setRevisions] = useState<WikiRevision[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [restoring, setRestoring] = useState<number | null>(null);
	const [expandedDiffId, setExpandedDiffId] = useState<string | null>(null);

	useEffect(() => {
		if (!slug) return;
		(async () => {
			try {
				const data = await wikiApi.getRevisions(slug);
				setRevisions(data);
			} catch {
				setError("Failed to load revision history");
			} finally {
				setLoading(false);
			}
		})();
	}, [slug]);

	const handleRestore = async (version: number) => {
		setRestoring(version);
		try {
			await wikiApi.restoreRevision(slug, version);
			showSuccess(`Restored to version ${version}`);
			router.push(`/wiki/${slug}`);
		} catch (err: unknown) {
			showError(err instanceof WikiApiError ? err.detail : "Failed to restore version");
			setRestoring(null);
		}
	};

	return (
		<div className="flex h-full overflow-hidden">
			<WikiSidebar />

			<div className="custom-scrollbar flex-1 overflow-y-auto bg-white">
				<div className="mx-auto max-w-3xl px-8 py-8">
					<WikiBreadcrumb currentSlug={slug} />

					{/* Header — Workflow Management–style icon block */}
					<div className="mb-8 flex items-center gap-3">
						<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-orange-200 bg-orange-100">
							<Clock className="h-5 w-5 text-orange-600" />
						</div>
						<div>
							<h1 className="text-xl font-semibold tracking-tight text-slate-900">
								Version History
							</h1>
							<p className="mt-0.5 text-xs text-slate-500">
								{isAdmin ? "View and restore previous versions" : "View previous versions"}
							</p>
						</div>
					</div>

					{/* Loading */}
					{loading && (
						<div className="space-y-3">
							{[1, 2, 3].map((i) => (
								<div
									key={i}
									className="h-24 animate-pulse rounded-2xl border border-slate-200 bg-slate-50"
								/>
							))}
						</div>
					)}

					{/* Error */}
					{error && !loading && (
						<div className="py-12 text-center">
							<p className="mb-4 text-slate-600">{error}</p>
							<Link
								href={`/wiki/${slug}`}
								className="text-sm text-orange-700 transition-colors hover:text-slate-900 hover:underline"
							>
								← Back to page
							</Link>
						</div>
					)}

					{/* Empty */}
					{!loading && !error && revisions.length === 0 && (
						<div className="rounded-2xl border border-slate-200 bg-white p-12 text-center shadow-[0_8px_24px_rgba(15,23,42,0.06)]">
							<Clock className="mx-auto mb-3 h-10 w-10 text-slate-400" />
							<p className="text-sm text-slate-600">
								No revision history available
							</p>
						</div>
					)}

					{/* Revision list */}
					{!loading && !error && revisions.length > 0 && (
						<div className="space-y-3">
							{revisions.map((revision, index) => (
								<div
									key={revision.id}
									className="rounded-2xl border border-slate-200 bg-white p-5 shadow-[0_8px_24px_rgba(15,23,42,0.06)] transition-all hover:border-orange-400"
								>
									<div className="mb-3 flex items-start justify-between gap-4">
										<div>
											<div className="mb-1 flex items-center gap-2">
												<span className="text-sm font-semibold text-slate-900">
													Version {revision.version}
												</span>
												{index === 0 && (
													<span className="rounded-full border border-[#0DA931] bg-white px-2 py-0.5 text-[10px] font-medium text-[#0DA931]">
														Current
													</span>
												)}
											</div>
											<p className="text-xs text-slate-600">
												{new Date(revision.created_at).toLocaleString(undefined, {
													month: "short",
													day: "numeric",
													year: "numeric",
													hour: "2-digit",
													minute: "2-digit",
												})}
												{revision.created_by && (
													<span className="ml-1">· {revision.created_by}</span>
												)}
											</p>
											{revision.change_summary && (
												<p className="mt-1.5 text-xs italic text-slate-700">
													&ldquo;{revision.change_summary}&rdquo;
												</p>
											)}
										</div>

										<div className="flex flex-shrink-0 items-center gap-2">
											{index < revisions.length - 1 && (
												<button
													type="button"
													onClick={() =>
														setExpandedDiffId(
															expandedDiffId === revision.id
																? null
																: revision.id,
														)
													}
													className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-700 transition-all hover:border-orange-400 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
												>
													<GitCompare className="h-3.5 w-3.5" />
													{expandedDiffId === revision.id
														? "Hide changes"
														: "Show changes"}
												</button>
											)}
											{isAdmin && index !== 0 && (
												<button
													type="button"
													onClick={() => handleRestore(revision.version)}
													disabled={restoring === revision.version}
													className="flex flex-shrink-0 items-center gap-1.5 rounded-[4px] border border-orange-500 bg-orange-500 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:border-orange-600 hover:bg-orange-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25 disabled:opacity-50"
												>
													<RotateCcw className="h-3.5 w-3.5" />
													{restoring === revision.version
														? "Restoring…"
														: "Restore"}
												</button>
											)}
										</div>
									</div>

									{/* Content preview */}
									<div className="border-t border-slate-200 pt-3">
										<p className="mb-1.5 text-[0.6rem] uppercase text-slate-500">
											Content preview
										</p>
										<pre className="line-clamp-3 max-h-24 overflow-hidden whitespace-pre-wrap break-words rounded-lg border border-slate-200 bg-slate-50 p-3 font-mono text-xs text-slate-700">
											{revision.content.slice(0, 240)}
											{revision.content.length > 240 && "…"}
										</pre>
									</div>

									{/* Diff view */}
									{index < revisions.length - 1 && (
										<div
											className={`overflow-hidden transition-all duration-300 ${
												expandedDiffId === revision.id
													? "mt-3 max-h-[2000px] opacity-100"
													: "max-h-0 opacity-0"
											}`}
										>
											<div className="border-t border-slate-200 pt-3">
												<p className="mb-1.5 text-[0.6rem] uppercase text-slate-500">
													Changes from version{" "}
													{revisions[index + 1].version}
												</p>
												<WikiDiffView
													oldContent={
														revisions[index + 1].content
													}
													newContent={revision.content}
												/>
											</div>
										</div>
									)}
								</div>
							))}
						</div>
					)}
				</div>
			</div>
		</div>
	);
}
