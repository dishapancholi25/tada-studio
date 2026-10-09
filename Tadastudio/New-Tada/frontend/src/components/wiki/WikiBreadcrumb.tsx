"use client";

import { ChevronRight } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { wikiApi, type WikiTreeNode } from "@/lib/wiki-api";

interface WikiBreadcrumbProps {
	currentSlug: string;
}

interface BreadcrumbSegment {
	slug: string;
	title: string;
}

function findAncestorPath(
	tree: WikiTreeNode[],
	targetSlug: string,
	path: BreadcrumbSegment[] = [],
): BreadcrumbSegment[] | null {
	for (const node of tree) {
		const currentPath = [...path, { slug: node.slug, title: node.title }];
		if (node.slug === targetSlug) return currentPath;
		if (node.children.length > 0) {
			const found = findAncestorPath(node.children, targetSlug, currentPath);
			if (found) return found;
		}
	}
	return null;
}

export default function WikiBreadcrumb({ currentSlug }: WikiBreadcrumbProps) {
	const [breadcrumbPath, setBreadcrumbPath] = useState<BreadcrumbSegment[] | null>(null);

	useEffect(() => {
		let cancelled = false;

		async function fetchPath() {
			try {
				const tree = await wikiApi.getTree();
				if (cancelled) return;
				setBreadcrumbPath(findAncestorPath(tree, currentSlug));
			} catch {
				if (!cancelled) setBreadcrumbPath(null);
			}
		}

		fetchPath();

		const handleRefresh = () => fetchPath();
		window.addEventListener("wiki:refresh", handleRefresh);

		return () => {
			cancelled = true;
			window.removeEventListener("wiki:refresh", handleRefresh);
		};
	}, [currentSlug]);

	if (!breadcrumbPath || breadcrumbPath.length === 0) return null;

	return (
		<nav className="mb-4" aria-label="Breadcrumb">
			<ol className="flex items-center gap-1 text-xs">
				<li>
					<Link
						href="/wiki"
						className="text-slate-500 transition-colors hover:text-slate-900"
					>
						Wiki
					</Link>
				</li>
				{breadcrumbPath.map((segment, index) => {
					const isLast = index === breadcrumbPath.length - 1;
					return (
						<li key={segment.slug} className="flex items-center gap-1">
							<ChevronRight className="h-3 w-3 flex-shrink-0 text-slate-400" />
							{isLast ? (
								<span className="max-w-[200px] truncate font-medium text-slate-800">
									{segment.title}
								</span>
							) : (
								<Link
									href={`/wiki/${segment.slug}`}
									className="max-w-[200px] truncate text-slate-500 transition-colors hover:text-slate-900"
								>
									{segment.title}
								</Link>
							)}
						</li>
					);
				})}
			</ol>
		</nav>
	);
}
