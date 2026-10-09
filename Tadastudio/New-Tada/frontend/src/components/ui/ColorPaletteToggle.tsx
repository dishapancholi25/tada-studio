"use client";

import { Palette, Sparkles } from "lucide-react";
import { useCallback } from "react";
import { useColorTheme } from "@/contexts/ColorThemeContext";

const themeLabels: Record<
	"mashreq" | "expose",
	{ label: string; description: string }
> = {
	mashreq: { label: "Mashreq", description: "Mashreq orange brand palette" },
	expose: { label: "Plum", description: "Modern plum & indigo palette" },
};

export default function ColorPaletteToggle() {
	const { theme, toggleTheme, setTheme } = useColorTheme();

	const setMashreqTheme = useCallback(() => setTheme("mashreq"), [setTheme]);
	const setExposeTheme = useCallback(() => setTheme("expose"), [setTheme]);

	return (
		<div className="flex items-center gap-2 bg-[color:var(--color-surface)]/70 border border-[color:var(--color-border)]/50 rounded-xl px-3 py-2 backdrop-blur-sm shadow-[0_10px_30px_rgba(0,0,0,0.35)]">
			<div className="hidden sm:flex items-center gap-2 text-[color:var(--color-text-muted)] text-xs capitalize tracking-wide">
				<Palette className="w-4 h-4" />
				Palette
			</div>
			<button
				type="button"
				onClick={setMashreqTheme}
				className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-all duration-200 ${
					theme === "mashreq"
						? "bg-[var(--accent-alpha-18)] text-[color:var(--color-text-primary)] shadow-[0_6px_18px_var(--accent-alpha-35)]"
						: "hover:bg-[var(--accent-alpha-10)] text-[color:var(--color-text-secondary)]"
				}`}
			>
				<Sparkles
					className={`w-4 h-4 ${theme === "mashreq" ? "animate-pulse" : ""}`}
				/>
				<span>{themeLabels.mashreq.label}</span>
			</button>
			<button
				type="button"
				onClick={setExposeTheme}
				className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-all duration-200 ${
					theme === "expose"
						? "bg-[var(--accent-alpha-18)] text-[color:var(--color-text-primary)] shadow-[0_6px_18px_var(--accent-alpha-35)]"
						: "hover:bg-[var(--accent-alpha-10)] text-[color:var(--color-text-secondary)]"
				}`}
			>
				<Palette
					className={`w-4 h-4 ${theme === "expose" ? "animate-pulse" : ""}`}
				/>
				<span>{themeLabels.expose.label}</span>
			</button>
			<button
				type="button"
				onClick={toggleTheme}
				className="sm:hidden inline-flex items-center gap-1 px-2 py-1 text-xs text-[color:var(--color-text-secondary)] border border-[color:var(--color-border)] rounded-lg"
				aria-label="Toggle color palette"
			>
				{theme === "mashreq" ? "Mashreq" : "Plum"}
			</button>
		</div>
	);
}
