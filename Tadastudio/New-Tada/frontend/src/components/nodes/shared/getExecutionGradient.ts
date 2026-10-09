/**
 * Shared Execution Gradient Utility
 *
 * Provides consistent gradient colors for node execution status across all node types.
 * Each node type has a theme color (emerald, purple, amber, etc.) that's used for
 * default and running states, while completed/failed states use shared colors.
 */

export interface GradientColors {
	from: string;
	to: string;
	border: string;
}

export interface ThemeGradient {
	default: GradientColors;
	running: GradientColors;
}

// Pre-defined theme gradients for each node type
export const themeGradients: Record<string, ThemeGradient> = {
	emerald: {
		default: {
			from: "from-emerald-500/20",
			to: "to-[#0DA931]/20",
			border: "border-emerald-500/50",
		},
		running: {
			from: "from-emerald-500/30",
			to: "to-[#0DA931]/30",
			border: "border-emerald-500/70",
		},
	},
	purple: {
		default: {
			from: "from-purple-500/20",
			to: "to-violet-500/20",
			border: "border-purple-500/50",
		},
		running: {
			from: "from-purple-500/30",
			to: "to-violet-500/30",
			border: "border-purple-500/70",
		},
	},
	amber: {
		default: {
			from: "from-amber-500/20",
			to: "to-yellow-500/20",
			border: "border-amber-500/50",
		},
		running: {
			from: "from-amber-500/30",
			to: "to-yellow-500/30",
			border: "border-amber-500/70",
		},
	},
	blue: {
		default: {
			from: "from-blue-500/20",
			to: "to-cyan-500/20",
			border: "border-blue-500/50",
		},
		running: {
			from: "from-blue-500/30",
			to: "to-cyan-500/30",
			border: "border-blue-500/70",
		},
	},
	orange: {
		default: {
			from: "from-orange-500/20",
			to: "to-amber-500/20",
			border: "border-orange-500/50",
		},
		running: {
			from: "from-orange-500/30",
			to: "to-amber-500/30",
			border: "border-orange-500/70",
		},
	},
	teal: {
		default: {
			from: "from-teal-500/20",
			to: "to-cyan-500/20",
			border: "border-teal-500/50",
		},
		running: {
			from: "from-teal-500/30",
			to: "to-cyan-500/30",
			border: "border-teal-500/70",
		},
	},
};

// Standard execution status colors (shared across all nodes)
const statusGradients = {
	completed: {
		from: "from-[#0DA931]/20",
		to: "to-emerald-500/20",
		border: "border-[#0DA931]/50",
	},
	failed: {
		from: "from-red-500/20",
		to: "to-rose-500/20",
		border: "border-red-500/50",
	},
	error: {
		from: "from-red-500/20",
		to: "to-rose-500/20",
		border: "border-red-500/60",
	}, // for config errors (slightly higher opacity border)
};

/**
 * Get gradient colors based on execution status and node theme.
 *
 * @param status - Execution status ('completed', 'failed', 'running', 'pending', 'skipped', or undefined)
 * @param theme - Node theme color key (must exist in themeGradients)
 * @param hasValidConfig - Whether the node has valid configuration (false shows error state)
 * @returns Gradient colors object with from, to, and border Tailwind classes
 */
export function getExecutionGradient(
	status: string | undefined,
	theme: keyof typeof themeGradients,
	hasValidConfig: boolean = true,
): GradientColors {
	// Show error state if no valid config and not currently executing
	if (!status && !hasValidConfig) {
		return statusGradients.error;
	}

	// Map execution status to gradient
	switch (status) {
		case "completed":
			return statusGradients.completed;
		case "failed":
			return statusGradients.failed;
		case "running":
			return themeGradients[theme].running;
		default:
			return themeGradients[theme].default;
	}
}
