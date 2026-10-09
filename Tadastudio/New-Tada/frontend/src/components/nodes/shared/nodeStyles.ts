/**
 * Shared Node Styling Constants
 *
 * Provides consistent styling across all agent builder nodes while
 * allowing node-specific customization through color parameters.
 */

// Shared shadow depths - creates visual hierarchy
export const nodeShadows = {
	default: "shadow-[0_6px_18px_rgba(0,0,0,0.12)]",
	hover: "shadow-[0_10px_26px_rgba(0,0,0,0.14)]",
	selected: "shadow-[0_0_0_2px_rgba(59,130,246,0.35)],shadow-[0_10px_26px_rgba(0,0,0,0.16)]",
};

// Shared border radius (standard and compact variants)
export const nodeRadius = {
	standard: "rounded-xl",
	compact: "rounded-lg", // For smaller nodes like MCP
};

export const nodeHeaderRadius = {
	standard: "rounded-t-xl",
	compact: "rounded-t-lg",
};

// Frame radius (slightly larger to account for 1px padding)
export const nodeFrameRadius = {
	standard: "rounded-[14px]",
	compact: "rounded-[12px]",
};

// Body background (flat, light — matches Figma-style node cards)
export const nodeBodyGradient = "bg-white";

// Gradient frame generator (for glass halo effect)
export const createGradientFrame = (colorRgb: string) => ({
	background: `linear-gradient(135deg, rgba(${colorRgb}, 0.18), transparent 60%, rgba(${colorRgb}, 0.06))`,
});

// Selection glow generator
export const createSelectionGlow = (colorRgb: string) => ({
	background: `linear-gradient(135deg, rgba(${colorRgb}, 0.24), transparent 70%)`,
});

// Common color RGB values for quick access
export const nodeColors = {
	// Theme colors (use CSS variables in components)
	primary: "var(--color-primary-rgb)",

	// Static colors
	green: "13, 169, 49",
	red: "239, 68, 68",
	rose: "244, 63, 94",
	orange: "249, 115, 22",
	amber: "245, 158, 11",
	purple: "168, 85, 247",
	violet: "139, 92, 246",
	blue: "59, 130, 246",
	indigo: "99, 102, 241",
	teal: "20, 184, 166",
	cyan: "6, 182, 212",
	emerald: "16, 185, 129",
	gray: "107, 114, 128",
};

// Icon capsule base styles
export const iconCapsuleBase =
	"flex items-center justify-center border transition-colors";
export const iconCapsuleSize = {
	standard: "h-8 w-8 rounded-xl",
	compact: "h-7 w-7 rounded-lg",
};

// Create icon capsule style with color
export const createIconCapsule = (colorRgb: string) => ({
	backgroundColor: `rgba(${colorRgb}, 0.12)`,
	borderColor: `rgba(${colorRgb}, 0.35)`,
	boxShadow: `0 0 20px rgba(${colorRgb}, 0.15)`,
});

// Typography styles
export const nodeTypography = {
	label: "text-xs font-semibold uppercase",
	title: "text-sm font-semibold text-slate-900",
	subtitle: "text-xs text-slate-500",
};

// Badge base styles
export const badgeBase =
	"flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium border";

// Create badge style with color
export const createBadge = (colorRgb: string) => ({
	backgroundColor: `rgba(${colorRgb}, 0.12)`,
	borderColor: `rgba(${colorRgb}, 0.35)`,
});

// Handle styles
export const handleStyles =
	"!w-2.5 !h-2.5 !bg-slate-900 !border-2 !border-white shadow-[0_1px_4px_rgba(0,0,0,0.18)] hover:!shadow-[0_0_0_4px_rgba(59,130,246,0.18)] transition-all";

// Delegation target handle style for regular agents — smaller, dashed, muted; reveals on hover/drag
export const delegationTargetHandleStyles =
	"!w-2.5 !h-2.5 !bg-transparent !border-2 !border-dashed !border-[color:var(--color-accent)]/35 hover:!border-[color:var(--color-accent)] hover:!bg-[color:var(--color-accent)]/15 hover:!shadow-[0_0_6px_rgba(var(--color-primary-rgb),0.4)] transition-all opacity-0 group-hover:opacity-100";

// Plus button styles
export const plusButtonBase =
	"p-3 w-12 h-12 flex items-center justify-center bg-white border-2 border-slate-200 hover:border-slate-300 rounded-full transition-all duration-300 hover:scale-110 hover:-translate-y-0.5";
export const plusButtonShadow =
	"shadow-[0_8px_25px_rgba(0,0,0,0.12)] hover:shadow-[0_12px_32px_rgba(0,0,0,0.14)]";
export const plusButtonPulse = "animate-plusPulse";

// Transition presets
export const nodeTransition = "transition-all duration-200";
export const nodeHoverLift = "hover:-translate-y-0.5";

// Selection ring generator (for accessibility fallback)
export const createSelectionRing = (colorRgb: string) => ({
	boxShadow: `0 0 0 2px rgba(${colorRgb}, 0.8)`,
});

// Header gradient generator
export const createHeaderGradient = (colorRgb: string) => ({
	background: `linear-gradient(to right, rgba(${colorRgb}, 0.25), rgba(${colorRgb}, 0.12), transparent)`,
});

// Execution status gradients
export const executionGradients = {
	completed: {
		from: "from-[#0DA931]/20",
		to: "to-emerald-500/20",
		border: "border-[#0DA931]/50",
		colorRgb: nodeColors.green,
	},
	failed: {
		from: "from-red-500/20",
		to: "to-rose-500/20",
		border: "border-red-500/50",
		colorRgb: nodeColors.red,
	},
	running: {
		from: "from-[color:var(--color-primary)]/35",
		to: "to-[color:var(--color-accent)]/35",
		border: "border-[color:var(--color-primary)]/60",
		colorRgb: "var(--color-primary-rgb)",
	},
	pending: {
		from: "from-amber-500/15",
		to: "to-amber-600/15",
		border: "border-amber-500/30",
		colorRgb: nodeColors.amber,
	},
};
