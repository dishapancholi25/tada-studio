"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import WikiPageEditor, { type WikiSaveData } from "@/components/wiki/WikiPageEditor";
import { useAuth } from "@/contexts/AuthContext";
import { wikiApi, WikiApiError, type WikiPageResponse } from "@/lib/wiki-api";

export default function EditWikiPage() {
	const params = useParams();
	const router = useRouter();
	const { user, loading: authLoading } = useAuth();
	const isAdmin = user?.is_admin === true;
	const slug = params.slug as string;

	const [page, setPage] = useState<WikiPageResponse | null>(null);
	const [loading, setLoading] = useState(true);
	const [loadError, setLoadError] = useState<string | null>(null);
	const [saving, setSaving] = useState(false);
	const [saveError, setSaveError] = useState<string | null>(null);

	useEffect(() => {
		if (!slug) return;
		(async () => {
			try {
				const data = await wikiApi.getPage(slug);
				setPage(data);
			} catch {
				setLoadError("Failed to load page");
			} finally {
				setLoading(false);
			}
		})();
	}, [slug]);

	const handleSave = async (data: WikiSaveData) => {
		setSaving(true);
		setSaveError(null);
		try {
			await wikiApi.updatePage(slug, {
				title: data.title,
				content: data.content,
				tags: data.tags,
				change_summary: data.changeSummary,
				parent_id: data.parentId === null ? "" : data.parentId || undefined,
			});
			window.dispatchEvent(new Event("wiki:refresh"));
			router.push(`/wiki/${slug}`);
		} catch (err: unknown) {
			setSaveError(err instanceof WikiApiError ? err.detail : "Failed to save page");
			setSaving(false);
		}
	};

	if (loading || authLoading) {
		return (
			<div className="flex h-full items-center justify-center bg-white">
				<div className="animate-pulse text-sm text-slate-600">Loading page…</div>
			</div>
		);
	}

	// Only admins can edit wiki pages
	if (!isAdmin) {
		return (
			<div className="flex h-full items-center justify-center bg-white text-center">
				<div className="max-w-md px-6">
					<p className="mb-3 text-slate-800">
						Only administrators can edit wiki pages.
					</p>
					<button
						type="button"
						onClick={() => router.push(`/wiki/${slug}`)}
						className="text-sm text-orange-700 transition-colors hover:text-slate-900 hover:underline"
					>
						← Back to page
					</button>
				</div>
			</div>
		);
	}

	if (loadError || !page) {
		return (
			<div className="flex h-full items-center justify-center bg-white text-center">
				<div>
					<p className="mb-3 text-slate-800">{loadError ?? "Page not found"}</p>
					<button
						type="button"
						onClick={() => router.push("/wiki")}
						className="text-sm text-orange-700 transition-colors hover:text-slate-900 hover:underline"
					>
						← Back to Wiki
					</button>
				</div>
			</div>
		);
	}

	return (
		<div className="h-full bg-white">
			<WikiPageEditor
				mode="edit"
				initialTitle={page.title}
				initialContent={page.content}
				initialTags={page.tags ? page.tags.join(", ") : ""}
				initialParentId={page.parent_id}
				pageId={page.id}
				onSave={handleSave}
				onCancel={() => router.push(`/wiki/${slug}`)}
				saving={saving}
				error={saveError}
			/>
		</div>
	);
}
