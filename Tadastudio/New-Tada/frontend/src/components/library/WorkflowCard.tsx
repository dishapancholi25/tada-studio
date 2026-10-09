"use client";

import { motion } from "framer-motion";
import {
	Bot,
	Check,
	Copy,
	Database,
	Globe,
	MessageSquare,
	Sparkles,
	Star,
	Stars,
	Trash2,
	TrendingUp,
	TrendingUp as UsageIcon,
	User,
	Zap,
} from "lucide-react";
import { useState } from "react";
import type { WorkflowTemplate } from "@/types/library";

interface WorkflowCardProps {
	workflow: WorkflowTemplate;
	onClone?: (workflowId: string) => void;
	onDelete?: (workflowId: string) => void;
	onSelect?: (workflowId: string) => void;
	currentUserEmail?: string;
	isCloning?: boolean;
	cloneLabel?: string;
	hideCloneAction?: boolean;
	dataTutorial?: string;
	dataTutorialClone?: string;
}

const getCategoryColorClasses = (color: string) => {
	const colorMap: Record<
		string,
		{ bg: string; text: string; border: string; iconBg: string }
	> = {
		blue: {
			bg: "from-blue-500/20 to-blue-500/5",
			text: "text-blue-400",
			border: "border-blue-500/20",
			iconBg: "bg-blue-500/20",
		},
		purple: {
			bg: "from-purple-500/20 to-purple-500/5",
			text: "text-purple-400",
			border: "border-purple-500/20",
			iconBg: "bg-purple-500/20",
		},
		green: {
			bg: "from-[#0DA931]/20 to-[#0DA931]/5",
			text: "text-[#0DA931]",
			border: "border-[#0DA931]/20",
			iconBg: "bg-[#0DA931]/20",
		},
		pink: {
			bg: "from-pink-500/20 to-pink-500/5",
			text: "text-pink-400",
			border: "border-pink-500/20",
			iconBg: "bg-pink-500/20",
		},
		cyan: {
			bg: "from-cyan-500/20 to-cyan-500/5",
			text: "text-cyan-400",
			border: "border-cyan-500/20",
			iconBg: "bg-cyan-500/20",
		},
		orange: {
			bg: "from-white to-white",
			text: "text-orange-600",
			border: "border-slate-200 group-hover:border-orange-400",
			iconBg: "bg-white",
		},
	};
	return colorMap[color] || colorMap.blue;
};

const getCategoryIcon = (category: string) => {
	const iconMap: Record<string, React.ElementType> = {
		Automation: Zap,
		"Data Processing": Database,
		Integration: Globe,
		AI: Bot,
		"Customer Service": MessageSquare,
		Marketing: TrendingUp,
		Sales: TrendingUp,
	};
	return iconMap[category] || Bot;
};

const getComplexityConfig = (complexity?: string) => {
	const normalized = complexity
		? complexity.charAt(0).toUpperCase() + complexity.slice(1)
		: "Beginner";
	const configMap: Record<
		string,
		{ icon: React.ElementType; color: string; bg: string }
	> = {
		Beginner: {
			icon: Star,
			color: "text-[#0DA931]",
			bg: "bg-[#0DA931]/20",
		},
		Intermediate: {
			icon: Stars,
			color: "text-blue-400",
			bg: "bg-blue-500/20",
		},
		Advanced: {
			icon: Sparkles,
			color: "text-purple-400",
			bg: "bg-purple-500/20",
		},
	};
	return configMap[normalized] || configMap.Beginner;
};

export default function WorkflowCard({
	workflow,
	onClone,
	onDelete,
	onSelect,
	currentUserEmail,
	isCloning = false,
	cloneLabel = "Clone Workflow",
	hideCloneAction = false,
	dataTutorial,
	dataTutorialClone,
}: WorkflowCardProps) {
	const [justCloned, setJustCloned] = useState(false);
	const colorClasses = getCategoryColorClasses(workflow.icon_color || "blue");
	const CategoryIcon = getCategoryIcon(workflow.category[0] || "General");
	const complexityConfig = getComplexityConfig(workflow.complexity);
	const ComplexityIcon = complexityConfig.icon;

	const isCreator =
		currentUserEmail &&
		workflow.creator_email &&
		currentUserEmail.toLowerCase() === workflow.creator_email.toLowerCase();
	const canDelete = onDelete && isCreator;

	const handleClone = () => {
		if (!onClone || isCloning || justCloned) return;

		onClone(workflow.id);
		setJustCloned(true);
		setTimeout(() => setJustCloned(false), 2000);
	};

	const handleDelete = (e: React.MouseEvent) => {
		e.stopPropagation();
		if (onDelete) {
			onDelete(workflow.id);
		}
	};

	return (
		<motion.article
			layout
			initial={{ opacity: 0, scale: 0.95 }}
			animate={{
				opacity: isCloning ? 0.7 : 1,
				scale: isCloning ? 0.98 : 1,
			}}
			exit={{ opacity: 0, scale: 0.95 }}
			whileHover={{
				y: -5,
				scale: 1.025,
				rotate: [0, -0.45, 0.45, 0],
				transition: { duration: 0.42, ease: "easeInOut" },
			}}
			whileTap={{ scale: 0.99 }}
			transition={{ duration: 0.2 }}
			className="group relative overflow-hidden rounded-2xl border border-slate-200 bg-white p-6 min-h-[320px] shadow-[0_18px_50px_rgba(15,23,42,0.10)] transition-all duration-300 before:pointer-events-none before:absolute before:inset-x-0 before:top-0 before:h-1 before:bg-[linear-gradient(90deg,#f97316_0%,#fb923c_34%,#f59e0b_48%,#f97316_63%,#213C81_78%,#f97316_100%)] before:bg-[length:220%_100%] hover:before:animate-[library-flow-bar_5.5s_linear_infinite] after:pointer-events-none after:absolute after:bottom-0 after:right-0 after:h-24 after:w-24 after:translate-x-10 after:translate-y-10 after:rounded-full after:bg-amber-300/20 after:blur-2xl hover:border-orange-400 hover:shadow-[0_24px_65px_rgba(15,23,42,0.12)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
			role="button"
			tabIndex={0}
			data-tutorial={dataTutorial}
			onClick={() => onSelect?.(workflow.id)}
			onKeyDown={(event) => {
				if (event.key === "Enter" || event.key === " ") {
					event.preventDefault();
					onSelect?.(workflow.id);
				}
			}}
		>
			{/* Delete Button (only for creator, visible on hover) */}
			{canDelete && (
				<button
					onClick={handleDelete}
					className="absolute top-3 right-3 p-2 rounded-xl border border-red-500/40 bg-red-500/15 text-red-400 hover:bg-red-500/25 hover:text-red-300 opacity-0 group-hover:opacity-100 transition-all duration-200 z-10"
					title="Delete template"
					aria-label="Delete template"
				>
					<Trash2 className="w-4 h-4" />
				</button>
			)}

			{/* Header with Icon and Title */}
			<div className="relative z-[1] flex items-start gap-3 mb-3">
				<div
					className={`p-2.5 bg-gradient-to-br ${colorClasses.bg} border ${colorClasses.border} rounded-xl group-hover:scale-110 group-hover:-rotate-3 transition-transform duration-300 flex-shrink-0`}
				>
					<CategoryIcon className={`w-5 h-5 ${colorClasses.text}`} />
				</div>
				<div className="flex-1 min-w-0">
					<h3
						className="text-lg font-semibold text-[color:var(--color-text-primary)] truncate transition-colors group-hover:text-slate-900"
						title={workflow.name}
					>
						{workflow.name}
					</h3>
					<span
						className={`text-[0.6rem] capitalize font-medium ${colorClasses.text}`}
					>
						{workflow.category.join(", ")}
					</span>
				</div>
			</div>

			{/* Description */}
			<p className="relative z-[1] text-sm text-[color:var(--color-text-secondary)] line-clamp-3 mb-4 flex-grow">
				{workflow.description}
			</p>

			{/* Tags */}
			<div
				className="relative z-[1] flex flex-wrap gap-1.5 mb-4 overflow-hidden"
				style={{ maxHeight: "64px" }}
			>
				{workflow.tags.slice(0, 4).map((tag) => (
					<span
						key={tag}
						className="px-2.5 py-1 text-[11px] font-medium rounded-full border border-slate-200 bg-white text-orange-700 whitespace-nowrap"
					>
						{tag}
					</span>
				))}
				{workflow.tags.length > 4 && (
					<span className="px-2.5 py-1 text-[11px] font-medium rounded-full bg-[color:var(--color-border)]/20 text-[color:var(--color-text-muted)] border border-[color:var(--color-border)]/40 whitespace-nowrap">
						+{workflow.tags.length - 4}
					</span>
				)}
			</div>

			{/* Metadata Row */}
			<div className="relative z-[1] space-y-2 mb-4">
				<div className="flex items-center gap-3 text-sm flex-wrap">
					{workflow.complexity && (
						<div
							className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full ${complexityConfig.bg} ${complexityConfig.color}`}
						>
							<ComplexityIcon className="w-3.5 h-3.5" />
							<span className="text-[11px] font-medium">
								{workflow.complexity.charAt(0).toUpperCase() +
									workflow.complexity.slice(1)}
							</span>
						</div>
					)}
				</div>
				<div className="flex items-center justify-between text-[0.6rem] capitalize text-[color:var(--color-text-muted)] pt-2 border-t border-[color:var(--color-border)]/40">
					<div className="flex items-center gap-1.5">
						<User className="w-3 h-3" />
						<span title={workflow.creator_email || undefined}>
							{workflow.creator_name}
						</span>
					</div>
					<div className="flex items-center gap-1.5">
						<UsageIcon className="w-3 h-3" />
						<span>
							{workflow.usage_count}{" "}
							{workflow.usage_count === 1 ? "use" : "uses"}
						</span>
					</div>
				</div>
			</div>

			{/* Clone Button */}
			{!hideCloneAction && (
				<button
					onClick={(event) => {
						event.stopPropagation();
						handleClone();
					}}
					disabled={!onClone || isCloning || justCloned}
					className={`relative z-[1] w-full flex items-center justify-center gap-2 px-4 py-3 font-semibold rounded-xl transition-all disabled:cursor-not-allowed ${
						justCloned
							? "bg-[#0DA931] text-white border-2 border-[#0DA931] shadow-[0_15px_40px_rgba(15,23,42,0.12)]"
							: "bg-orange-500 border-2 border-orange-500 shadow-[0_15px_40px_rgba(15,23,42,0.12)] hover:bg-orange-600 hover:border-orange-600 hover:shadow-[0_20px_50px_rgba(15,23,42,0.14)] disabled:opacity-40"
					}`}
					style={{
						color: justCloned ? undefined : "var(--button-primary-text)",
					}}
					aria-label={`${cloneLabel} ${workflow.name}`}
					data-tutorial={dataTutorialClone}
				>
					{isCloning ? (
						<>
							<div
								className="w-4 h-4 border-2 border-slate-200 border-t-orange-500 rounded-full animate-spin"
								style={{
									borderColor: "var(--button-primary-text)",
									borderTopColor: "transparent",
								}}
							></div>
							<span>Cloning...</span>
						</>
					) : justCloned ? (
						<>
							<Check className="w-4 h-4" />
							<span>Cloned!</span>
						</>
					) : (
						<>
							<Copy className="w-4 h-4" />
							<span>{cloneLabel}</span>
						</>
					)}
				</button>
			)}
		</motion.article>
	);
}
