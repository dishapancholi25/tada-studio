"use client";

import { AlertCircle, CheckCircle2 } from "lucide-react";
import { useMemo } from "react";

interface RegexInputProps {
	value: string;
	onChange: (value: string) => void;
	placeholder?: string;
	disabled?: boolean;
	className?: string;
}

/**
 * Validate a regex pattern string. Returns null if valid, error message if invalid.
 * Patterns run on the Python backend which supports inline flags like (?i).
 * We strip Python inline flags before testing with JS RegExp.
 */
function validateRegex(pattern: string): string | null {
	if (!pattern) return null; // empty is not an error (just not filled yet)
	try {
		const stripped = pattern.replace(/^\(\?[imsx]+\)/, "");
		new RegExp(stripped);
		return null;
	} catch (e) {
		const msg = e instanceof SyntaxError ? e.message : "Invalid regex";
		// Strip the unhelpful "Invalid regular expression: /pattern/: " prefix
		return msg.replace(/^Invalid regular expression: \/.*\/: /, "");
	}
}

const baseClass =
	"w-full rounded-lg border bg-[color:var(--color-bg-secondary)] px-3 py-2 font-mono text-sm text-[color:var(--color-text-primary)] placeholder-[color:var(--color-text-muted)]/50 focus-visible:outline-none focus-visible:ring-2 transition-colors";

export default function RegexInput({
	value,
	onChange,
	placeholder = "Regex pattern...",
	disabled = false,
	className = "",
}: RegexInputProps) {
	const error = useMemo(() => validateRegex(value), [value]);
	const hasValue = value.length > 0;

	const borderClass = error
		? "border-red-500/60 focus:border-red-500/80 focus-visible:ring-red-500/30"
		: hasValue
			? "border-emerald-500/40 focus:border-emerald-500/60 focus-visible:ring-emerald-500/30"
			: "border-[color:var(--color-border)]/70 focus:border-[rgba(6,182,212,0.5)] focus-visible:ring-[rgba(6,182,212,0.45)]";

	return (
		<div className={className}>
			<div className="relative">
				<input
					type="text"
					value={value}
					onChange={(e) => onChange(e.target.value)}
					placeholder={placeholder}
					disabled={disabled}
					className={`${baseClass} ${borderClass} pr-8`}
				/>
				{hasValue && (
					<div className="absolute right-2.5 top-1/2 -translate-y-1/2">
						{error ? (
							<AlertCircle className="h-3.5 w-3.5 text-red-400" />
						) : (
							<CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
						)}
					</div>
				)}
			</div>
			{error && (
				<p className="mt-1 text-[11px] text-red-400">{error}</p>
			)}
		</div>
	);
}
