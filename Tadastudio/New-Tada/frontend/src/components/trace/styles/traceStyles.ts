// Shared design system styles for trace viewer — orange / white, dark text, no pale-orange fills

export const traceStyles = {
	// ============ SURFACES ============

	shell:
		"rounded-[4px] border border-slate-200 bg-white shadow-[0_30px_80px_rgba(15,23,42,0.12)]",

	primaryCard:
		"rounded-[4px] border border-slate-200 bg-white shadow-sm",

	secondaryCard:
		"rounded-[4px] border border-slate-200 bg-white shadow-sm",

	tertiaryCard: "rounded-[4px] border border-slate-200 bg-white shadow-sm",

	headerGradient: "border-b border-slate-200 bg-white",

	panelGradient: "bg-white",

	statsBarGradient: "bg-white",

	// ============ GLOW EFFECTS ============
	glowWrapper: "hidden",
	glowWrapperLeft: "hidden",
	glowWrapperRight: "hidden",

	// ============ TYPOGRAPHY ============

	sectionHeader:
		"text-xs capitalize text-slate-900 font-semibold",

	inlineLabel: "text-[0.6rem] capitalize text-slate-600",

	inlineLabelLg:
		"text-[0.7rem] capitalize text-slate-600 font-semibold",

	// ============ BADGES ============

	badgePrimary:
		"rounded-full border border-orange-500/50 bg-white px-3 py-1 text-[11px] font-medium text-orange-800",

	badgeNeutral:
		"rounded-[4px] border border-slate-200 bg-white px-2 py-1 text-xs text-slate-700",

	badgeSmall:
		"rounded-[4px] border border-slate-200 bg-white px-2 py-1 text-[10px] font-medium text-slate-800",

	iconCapsule:
		"w-8 h-8 rounded-[4px] border border-orange-200 bg-orange-100 flex items-center justify-center text-orange-600",

	iconCapsuleSm:
		"w-6 h-6 rounded-[4px] border border-orange-200 bg-orange-100 flex items-center justify-center text-orange-600",

	iconButton:
		"p-2 rounded-[4px] border border-transparent text-slate-600 transition-all duration-200 hover:border-orange-400 hover:bg-slate-50 hover:text-orange-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/30",

	sectionToggle:
		"w-full rounded-[4px] px-5 py-4 flex items-center justify-between text-left text-slate-900 transition-colors hover:bg-slate-50",

	tabActive:
		"border-b-2 border-orange-500 bg-white text-slate-900",

	tabInactive:
		"border-b-2 border-transparent text-slate-600 hover:text-orange-800 hover:border-orange-400",

	searchInput:
		"rounded-[4px] border border-slate-200 bg-white text-slate-900 placeholder:text-slate-400 focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20 transition-all duration-200",

	statPill:
		"flex items-center gap-2.5 rounded-[4px] border border-slate-200 bg-white px-3 py-1.5",

	divider: "border-slate-200",

	shadowModal: "shadow-[0_30px_80px_rgba(15,23,42,0.12)]",
	shadowPrimary: "shadow-sm",
	shadowSecondary: "shadow-sm",
	shadowCard: "shadow-sm",
	shadowFocus: "shadow-sm",

	selectedNode:
		"border-l-2 border-l-orange-500 bg-slate-50 border-y-0 border-r-0 border-slate-200",

	highlightRow:
		"rounded-[4px] border border-slate-200 bg-slate-50 py-2.5 px-3 text-slate-900",
};

export const statusColors = {
	completed: {
		bg: "bg-[#F1F8E9]",
		border: "border-[#0DA931]",
		text: "text-[#0DA931]",
		combined:
			"border border-[#0DA931] bg-[#F1F8E9] text-[#0DA931]",
	},
	failed: {
		bg: "bg-red-50",
		border: "border-red-400",
		text: "text-red-600",
		combined: "border border-red-400 bg-red-50 text-red-600",
	},
	running: {
		bg: "bg-orange-50",
		border: "border-orange-400",
		text: "text-orange-600",
		combined: "border border-orange-400 bg-orange-50 text-orange-600",
	},
	pending: {
		bg: "bg-slate-50",
		border: "border-slate-300",
		text: "text-slate-600",
		combined: "border border-slate-300 bg-slate-50 text-slate-600",
	},
};

export const nodeTypeColors = {
	agent: "text-blue-700",
	tool: "text-amber-800",
	llm: "text-pink-700",
	condition: "text-violet-700",
	orchestrator: "text-purple-700",
	subgraph: "text-violet-700",
	human: "text-teal-700",
	start: "text-[#0DA931]",
	end: "text-red-700",
	checkpoint: "text-cyan-700",
	unknown: "text-slate-600",
};
