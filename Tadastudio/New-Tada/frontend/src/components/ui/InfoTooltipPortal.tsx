"use client";

import { HelpCircle } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

interface InfoTooltipPortalProps {
	text: string;
}

export default function InfoTooltipPortal({ text }: InfoTooltipPortalProps) {
	const [show, setShow] = useState(false);
	const [position, setPosition] = useState({ top: 0, left: 0 });
	const [showAbove, setShowAbove] = useState(true);
	const buttonRef = useRef<HTMLButtonElement>(null);
	const [mounted, setMounted] = useState(false);

	const showTooltip = useCallback(() => setShow(true), []);
	const hideTooltip = useCallback(() => setShow(false), []);

	useEffect(() => {
		setMounted(true);
		return () => setMounted(false);
	}, []);

	useEffect(() => {
		if (show && buttonRef.current) {
			const rect = buttonRef.current.getBoundingClientRect();
			const tooltipWidth = 320;
			const tooltipHeight = 50;

			let left = rect.left + rect.width / 2;
			let top = rect.top - tooltipHeight - 10;
			let above = true;

			const padding = 10;
			if (left - tooltipWidth / 2 < padding) {
				left = tooltipWidth / 2 + padding;
			} else if (left + tooltipWidth / 2 > window.innerWidth - padding) {
				left = window.innerWidth - tooltipWidth / 2 - padding;
			}

			if (top < padding) {
				top = rect.bottom + 10;
				above = false;
			}

			setPosition({ top, left });
			setShowAbove(above);
		}
	}, [show]);

	const tooltipContent = show && mounted && (
		<div
			className="fixed z-[9999] pointer-events-none"
			style={{
				top: `${position.top}px`,
				left: `${position.left}px`,
				transform: "translateX(-50%)",
				maxWidth: "320px",
				width: "max-content",
				animation: "tooltip-enter 0.2s ease-out",
			}}
		>
			<div className="relative overflow-visible rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 shadow-[0_10px_40px_rgba(0,0,0,0.3)]">
				{/* Top accent line */}
					<div className="absolute top-0 left-3 right-3 h-[1px] bg-gradient-to-r from-transparent via-orange-500 to-transparent" />
					<span className="text-[13px] leading-relaxed text-white">
					{text}
				</span>
			</div>
			{/* Arrow */}
			{showAbove ? (
				<div className="flex justify-center -mt-[1px]">
						<div className="h-2.5 w-2.5 rotate-45 rounded-[2px] border-b border-r border-slate-700 bg-slate-900" />
				</div>
			) : (
				<div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-0">
						<div className="h-2.5 w-2.5 rotate-45 rounded-[2px] border-t border-l border-slate-700 bg-slate-900" />
				</div>
			)}
		</div>
	);

	return (
		<>
			<button
				ref={buttonRef}
				onMouseEnter={showTooltip}
				onMouseLeave={hideTooltip}
				className="rounded-full p-0.5 text-slate-400 hover:text-orange-500 hover:bg-orange-50 transition-all duration-200 inline-flex"
				type="button"
			>
				<HelpCircle className="w-3.5 h-3.5" />
			</button>
			{mounted && createPortal(tooltipContent, document.body)}
			{mounted &&
				createPortal(
					<style>{`
						@keyframes tooltip-enter {
							from {
								opacity: 0;
								transform: translateX(-50%) scale(0.96) translateY(4px);
							}
							to {
								opacity: 1;
								transform: translateX(-50%) scale(1) translateY(0);
							}
						}
					`}</style>,
					document.head,
				)}
		</>
	);
}
