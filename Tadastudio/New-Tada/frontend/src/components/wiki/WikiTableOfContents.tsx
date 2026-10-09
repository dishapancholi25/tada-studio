"use client";

import { useEffect, useRef, useState } from "react";
import { useRovingTabIndex } from "@/hooks/useAccessibility";

interface TocItem {
	id: string;
	level: number;
	text: string;
}

interface WikiTableOfContentsProps {
	content: string;
}

export default function WikiTableOfContents({
	content,
}: WikiTableOfContentsProps) {
	const [items, setItems] = useState<TocItem[]>([]);
	const [activeId, setActiveId] = useState<string>("");

	useEffect(() => {
		// Parse markdown headers
		const lines = content.split("\n");
		const tocItems: TocItem[] = [];

		lines.forEach((line) => {
			const match = line.match(/^(#{1,6})\s+(.+)$/);
			if (match) {
				const level = match[1].length;
				const text = match[2].trim();
				const id = text
					.toLowerCase()
					.replace(/[^\w\s-]/g, "")
					.replace(/\s+/g, "-");
				tocItems.push({ id, level, text });
			}
		});

		setItems(tocItems);
	}, [content]);

	useEffect(() => {
		if (items.length === 0) return;
		const observer = new IntersectionObserver(
			(entries) => {
				const visible = entries.filter((e) => e.isIntersecting);
				if (visible.length > 0) {
					setActiveId(visible[0].target.id);
				}
			},
			{ rootMargin: "-10% 0px -80% 0px", threshold: 0 },
		);
		const headings = document.querySelectorAll(
			"h1[id], h2[id], h3[id], h4[id], h5[id], h6[id]",
		);
		headings.forEach((h) => observer.observe(h));
		return () => observer.disconnect();
	}, [items]);

	const scrollToHeading = (id: string) => {
		const element = document.getElementById(id);
		if (element) {
			element.scrollIntoView({ behavior: "smooth", block: "start" });
		}
	};

	const {
		focusedIndex,
		handleKeyDown: handleRovingKeyDown,
		getRovingProps,
	} = useRovingTabIndex(items.length);
	const buttonRefs = useRef<(HTMLButtonElement | null)[]>([]);

	useEffect(() => {
		buttonRefs.current[focusedIndex]?.focus();
	}, [focusedIndex]);

	if (items.length === 0) {
		return null;
	}

	return (
		<div className="sticky top-8 w-full rounded-2xl border border-slate-200 bg-white p-4 shadow-[0_10px_28px_rgba(15,23,42,0.08)]">
			<p className="mb-3 text-[0.6rem] font-semibold capitalize text-slate-800">
				On this page
			</p>

			<div className="border-t border-slate-200 pt-3">
				<nav
					className="space-y-0.5"
					aria-label="Table of contents"
					onKeyDown={handleRovingKeyDown}
				>
					{items.map((item, index) => (
						<button
							key={item.id}
							ref={(el) => {
								buttonRefs.current[index] = el;
							}}
							onClick={() => scrollToHeading(item.id)}
							aria-current={
								activeId === item.id ? "location" : undefined
							}
							{...getRovingProps(index)}
							className={`relative block w-full rounded-lg px-3 py-1.5 text-left text-[13px] transition-all duration-200 ${
								activeId === item.id
									? "font-medium text-slate-900"
									: "text-slate-800 hover:bg-slate-50 hover:text-slate-900"
							}`}
							style={{
								paddingLeft: `${(item.level - 1) * 12 + 12}px`,
							}}
						>
							{activeId === item.id && (
								<span className="absolute bottom-1 left-0 top-1 w-0.5 rounded-full bg-orange-500" />
							)}
							{item.text}
						</button>
					))}
				</nav>
			</div>
		</div>
	);
}
