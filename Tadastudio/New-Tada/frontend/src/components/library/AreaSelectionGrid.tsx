"use client";

import { motion } from "framer-motion";
import { LayoutGrid } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { TEMPLATE_CATEGORIES, type TemplateCategory } from "@/types/library";

interface AreaSelectionGridProps {
	onSelectArea: (area: TemplateCategory | null) => void;
}

interface CategoryCounts {
	agents: number;
	workflows: number;
}

const CATEGORY_DESCRIPTIONS: Record<string, string> = {
	Finance: "Automates key financial processes to improve efficiency in AI use cases.",
	Sales: "Uses AI to drive faster deal execution and revenue growth.",
	Recruitment: "Streamlines talent acquisition workflows using intelligent automation.",
	Marketing: "Accelerates campaign planning and content creation with AI agents.",
	"Customer Service": "Resolves customer queries faster with AI-driven support flows.",
	Education: "Enhances learning experiences through intelligent workflow automation.",
	Operations: "Optimises operational processes and reduces manual overhead.",
	Analytics: "Transforms raw data into actionable insights using AI pipelines.",
	Technology: "Accelerates development cycles with AI-assisted engineering flows.",
	"Risk & Compliance": "Monitors and enforces compliance policies with automated checks.",
	"Human Resources": "Streamlines HR processes from onboarding to performance reviews.",
	Cybersecurity: "Detects and responds to threats with AI-powered security workflows.",
	General: "General-purpose workflow templates for diverse automation needs.",
};

export function AreaSelectionGrid({ onSelectArea }: AreaSelectionGridProps) {
	const [categoryCounts, setCategoryCounts] = useState<Record<string, CategoryCounts>>({});
	const [loading, setLoading] = useState(true);

	useEffect(() => {
		let isMounted = true;
		const fetchCounts = async () => {
			try {
				setLoading(true);
				const response = await api.getCategoryCounts();
				if (isMounted && response.success) {
					const counts: Record<string, CategoryCounts> = {};
					TEMPLATE_CATEGORIES.forEach((cat) => {
						counts[cat] = response.category_counts[cat] || { agents: 0, workflows: 0 };
					});
					setCategoryCounts(counts);
				}
			} catch {
				// silent
			} finally {
				if (isMounted) setLoading(false);
			}
		};
		fetchCounts();
		return () => { isMounted = false; };
	}, []);

	return (
		<div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
			{TEMPLATE_CATEGORIES.map((category, index) => {
				const counts = categoryCounts[category];
				const total = (counts?.agents ?? 0) + (counts?.workflows ?? 0);
				const description =
					CATEGORY_DESCRIPTIONS[category] ??
					"Explore workflow templates to accelerate your AI automation journey.";

				return (
					<motion.button
						key={category}
						data-tutorial={index === 0 ? "library-category" : undefined}
						type="button"
						onClick={() => onSelectArea(category)}
						whileHover={{
							y: -5,
							scale: 1.015,
							rotate: [0, -0.35, 0.35, 0],
							transition: { duration: 0.42, ease: "easeInOut" },
						}}
						whileTap={{ scale: 0.99 }}
						className="group relative overflow-hidden flex flex-col gap-3 rounded-2xl border border-gray-200 bg-white p-5 text-left shadow-[0_18px_50px_rgba(15,23,42,0.08)] transition-all duration-300 before:pointer-events-none before:absolute before:inset-x-0 before:top-0 before:h-1 before:bg-[linear-gradient(90deg,#f97316_0%,#fb923c_34%,#f59e0b_48%,#f97316_63%,#213C81_78%,#f97316_100%)] before:bg-[length:220%_100%] hover:before:animate-[library-flow-bar_5.5s_linear_infinite] after:pointer-events-none after:absolute after:bottom-0 after:right-0 after:h-20 after:w-20 after:translate-x-8 after:translate-y-8 after:rounded-full after:bg-amber-300/20 after:blur-2xl hover:border-orange-400 hover:shadow-[0_22px_56px_rgba(15,23,42,0.10)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/30"
					>
						{/* Header row */}
						<div className="relative z-[1] flex items-start justify-between gap-2">
							<span className="text-sm font-bold text-[color:var(--color-text-primary)] leading-snug transition-colors group-hover:text-slate-900">
								{category}
							</span>
							<span
								className="shrink-0 text-xs font-medium text-orange-600 transition-colors group-hover:text-slate-900"
							>
								View all
							</span>
						</div>

						{/* Description */}
						<p className="relative z-[1] text-xs leading-relaxed text-[color:var(--color-text-muted)] line-clamp-2">
							{description}
						</p>

						{/* Footer: count */}
						<div className="relative z-[1] flex items-center justify-end gap-1.5 pt-1">
							<LayoutGrid className="h-3.5 w-3.5 text-[color:var(--color-text-muted)] transition-colors group-hover:text-slate-800" />
							<span className="text-xs font-medium text-[color:var(--color-text-muted)]">
								{loading ? "…" : total}
							</span>
						</div>
					</motion.button>
				);
			})}
		</div>
	);
}
