"use client";

import type React from "react";
import { useCallback } from "react";

interface Tab {
	key: string;
	label: string;
	icon?: React.ReactNode;
}

interface ExecutionTabsProps {
	tabs: Tab[];
	active: string;
	onChange: (key: string) => void;
}

export default function ExecutionTabs({
	tabs,
	active,
	onChange,
}: ExecutionTabsProps) {
	const createTabHandler = useCallback(
		(tabKey: string) => () => onChange(tabKey),
		[onChange],
	);

	return (
		<div className="px-6 py-4 border-b border-slate-200">
			{/* Section Label */}
			<div className="text-[0.6rem] capitalize text-slate-500 font-semibold mb-3">
				View Mode
			</div>

			{/* Tab Pills */}
			<div className="flex gap-2 flex-wrap">
				{tabs.map((t) => (
					<button
						key={t.key}
						onClick={createTabHandler(t.key)}
						className={`
              px-4 py-2 rounded-xl text-sm font-medium transition-all
              flex items-center gap-2
              focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)]
              ${
								active === t.key
									? "border border-[color:var(--color-primary)] bg-[rgba(var(--color-primary-rgb),0.1)] text-[color:var(--color-primary)] shadow-sm"
									: "border border-slate-200 bg-white text-slate-600 hover:text-slate-900 hover:border-slate-300 hover:bg-slate-50"
							}
            `}
					>
						{t.icon && <span className="w-4 h-4 opacity-80">{t.icon}</span>}
						{t.label}
					</button>
				))}
			</div>
		</div>
	);
}
