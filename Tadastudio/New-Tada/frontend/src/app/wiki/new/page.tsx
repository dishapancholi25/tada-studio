"use client";

import { AlertTriangle } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import WikiPageEditor, { type WikiSaveData } from "@/components/wiki/WikiPageEditor";
import { useAuth } from "@/contexts/AuthContext";
import { wikiApi, WikiApiError } from "@/lib/wiki-api";

export default function NewWikiPage() {
	const router = useRouter();
	const { user, loading: authLoading } = useAuth();
	const isAdmin = user?.is_admin === true;
	const [saving, setSaving] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [featureDisabled, setFeatureDisabled] = useState(false);
	const [checkingAccess, setCheckingAccess] = useState(true);

	// Check if wiki feature is enabled by trying to list pages
	const checkAccess = useCallback(async () => {
		try {
			await wikiApi.listPages();
		} catch (err) {
			if (err instanceof WikiApiError && err.status === 404) {
				setFeatureDisabled(true);
			}
		} finally {
			setCheckingAccess(false);
		}
	}, []);

	useEffect(() => {
		checkAccess();
	}, [checkAccess]);

	const handleSave = async (data: WikiSaveData) => {
		if (!data.title.trim()) return;
		setSaving(true);
		setError(null);
		try {
			const page = await wikiApi.createPage({
				title: data.title,
				content: data.content,
				tags: data.tags,
				is_published: true,
				parent_id: data.parentId || undefined,
			});
			window.dispatchEvent(new Event("wiki:refresh"));
			router.push(`/wiki/${page.slug}`);
		} catch (err: unknown) {
			if (err instanceof WikiApiError && err.status === 404) {
				setFeatureDisabled(true);
			} else {
				setError(err instanceof WikiApiError ? err.detail : "Failed to create page");
			}
			setSaving(false);
		}
	};

	// Show loading state while checking access
	if (checkingAccess || authLoading) {
		return (
			<div className="flex h-full items-center justify-center bg-white">
				<div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-200 border-t-orange-500" />
			</div>
		);
	}

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

	// Only admins can create wiki pages
	if (!isAdmin) {
		return (
			<div className="flex h-full items-center justify-center bg-white">
				<div className="text-center max-w-md px-6">
					<div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-2xl border border-slate-200 bg-white shadow-[0_10px_28px_rgba(15,23,42,0.06)]">
						<AlertTriangle className="h-8 w-8 text-amber-500" />
					</div>
					<h1 className="text-xl font-semibold text-slate-900 mb-2">Admin Access Required</h1>
					<p className="text-sm text-slate-600 mb-6">
						Only administrators can create wiki pages. Please contact your administrator if you
						need to add content.
					</p>
					<button
						onClick={() => router.push("/wiki")}
						className="inline-flex items-center gap-2 rounded-[4px] border border-slate-300 bg-white px-5 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
					>
						Back to Wiki
					</button>
				</div>
			</div>
		);
	}

	return (
		<div className="h-full bg-white">
			<WikiPageEditor
				mode="create"
				onSave={handleSave}
				onCancel={() => router.push("/wiki")}
				saving={saving}
				error={error}
			/>
		</div>
	);
}
