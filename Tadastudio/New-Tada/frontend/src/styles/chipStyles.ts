/**
 * Mashreq Design System - Chip/Badge/Label Styles
 * Based on UI component reference designs
 */

// ============ COLOR TOKENS ============
export const CHIP_COLORS = {
  orange: {
    primary: "#ff6b00",
    light: "#fff7ed",
    border: "#fb923c",
  },
  green: {
    primary: "#0DA931",
    light: "#F1F8E9",
    border: "#0DA931",
  },
  red: {
    primary: "#ef4444",
    light: "#fef2f2",
    border: "#f87171",
  },
  amber: {
    primary: "#f59e0b",
    light: "#fffbeb",
    border: "#fbbf24",
  },
  slate: {
    primary: "#64748b",
    light: "#f8fafc",
    border: "#cbd5e1",
  },
} as const;

// ============ CHIP VARIANTS ============

/**
 * Filled chips - solid background with white text
 */
export const CHIP_FILLED = {
  orange: "bg-orange-500 text-white border-transparent",
  green: "bg-[#0DA931] text-white border-transparent",
  red: "bg-red-500 text-white border-transparent",
  amber: "bg-amber-500 text-white border-transparent",
  slate: "bg-slate-500 text-white border-transparent",
  disabled: "bg-slate-200 text-slate-400 border-transparent cursor-not-allowed",
} as const;

/**
 * Outlined chips - white background with colored border and text
 */
export const CHIP_OUTLINED = {
  orange: "bg-white border-orange-400 text-orange-600",
  green: "bg-white border-[#0DA931] text-[#0DA931]",
  red: "bg-white border-red-400 text-red-600",
  amber: "bg-white border-amber-400 text-amber-600",
  slate: "bg-white border-slate-300 text-slate-600",
  disabled: "bg-white border-slate-200 text-slate-400 cursor-not-allowed",
} as const;

/**
 * Light/Tinted chips - light tinted background with colored text
 */
export const CHIP_LIGHT = {
  orange: "bg-orange-50 border-orange-200 text-orange-700",
  green: "bg-[#F1F8E9] border-[#0DA931]/30 text-[#0DA931]",
  red: "bg-red-50 border-red-200 text-red-700",
  amber: "bg-amber-50 border-amber-200 text-amber-700",
  slate: "bg-slate-50 border-slate-200 text-slate-600",
  disabled: "bg-slate-50 border-slate-100 text-slate-400 cursor-not-allowed",
} as const;

// ============ STATUS MAPPING ============

/**
 * Status-to-color mapping for badges (outlined style)
 */
export const STATUS_CHIP_STYLES = {
  // Success states
  completed: CHIP_OUTLINED.green,
  success: CHIP_OUTLINED.green,
  processed: CHIP_OUTLINED.green,
  active: CHIP_OUTLINED.green,
  enabled: CHIP_OUTLINED.green,
  connected: CHIP_OUTLINED.green,
  configured: CHIP_OUTLINED.green,

  // Error states
  failed: CHIP_OUTLINED.red,
  error: CHIP_OUTLINED.red,
  stopped: CHIP_OUTLINED.red,

  // Warning/Progress states
  running: CHIP_OUTLINED.orange,
  processing: CHIP_OUTLINED.orange,
  pending: CHIP_OUTLINED.slate,
  paused: CHIP_OUTLINED.amber,
  warning: CHIP_OUTLINED.amber,

  // Neutral states
  default: CHIP_OUTLINED.slate,
  inactive: CHIP_OUTLINED.slate,
  disabled: CHIP_OUTLINED.disabled,
  draft: CHIP_OUTLINED.slate,
  queued: CHIP_OUTLINED.slate,
} as const;

/**
 * Status-to-color mapping with light backgrounds
 */
export const STATUS_CHIP_LIGHT_STYLES = {
  completed: CHIP_LIGHT.green,
  success: CHIP_LIGHT.green,
  processed: CHIP_LIGHT.green,
  active: CHIP_LIGHT.green,

  failed: CHIP_LIGHT.red,
  error: CHIP_LIGHT.red,
  stopped: CHIP_LIGHT.red,

  running: CHIP_LIGHT.orange,
  processing: CHIP_LIGHT.orange,
  pending: CHIP_LIGHT.slate,
  paused: CHIP_LIGHT.amber,
  warning: CHIP_LIGHT.amber,

  default: CHIP_LIGHT.slate,
  inactive: CHIP_LIGHT.slate,
  disabled: CHIP_LIGHT.disabled,
} as const;

// ============ BASE CHIP CLASSES ============

/**
 * Base classes for all chips (includes border)
 */
export const CHIP_BASE = {
  sm: "inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium border",
  md: "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium border",
  lg: "inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium border",
  pill: "inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border",
} as const;

/**
 * Filter chip base (dismissible)
 */
export const FILTER_CHIP_BASE = "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border";

// ============ HELPER FUNCTIONS ============

export function getStatusChipClass(status: string, variant: 'outlined' | 'light' | 'filled' = 'outlined'): string {
  const normalizedStatus = status.toLowerCase();

  if (variant === 'light') {
    return STATUS_CHIP_LIGHT_STYLES[normalizedStatus as keyof typeof STATUS_CHIP_LIGHT_STYLES] || CHIP_LIGHT.slate;
  }

  if (variant === 'filled') {
    if (['completed', 'success', 'processed', 'active'].includes(normalizedStatus)) return CHIP_FILLED.green;
    if (['failed', 'error', 'stopped'].includes(normalizedStatus)) return CHIP_FILLED.red;
    if (['running', 'processing'].includes(normalizedStatus)) return CHIP_FILLED.orange;
    if (['paused', 'warning'].includes(normalizedStatus)) return CHIP_FILLED.amber;
    return CHIP_FILLED.slate;
  }

  return STATUS_CHIP_STYLES[normalizedStatus as keyof typeof STATUS_CHIP_STYLES] || CHIP_OUTLINED.slate;
}

export function getChipClass(color: keyof typeof CHIP_OUTLINED, variant: 'outlined' | 'light' | 'filled' = 'outlined'): string {
  switch (variant) {
    case 'filled':
      return CHIP_FILLED[color];
    case 'light':
      return CHIP_LIGHT[color];
    default:
      return CHIP_OUTLINED[color];
  }
}
