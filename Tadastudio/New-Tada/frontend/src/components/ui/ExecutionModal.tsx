"use client";

import type React from "react";
import { useCallback } from "react";

interface ExecutionModalProps {
	children: React.ReactNode;
	onBackdropClick?: () => void;
	maxWidthClass?: string;
}

export default function ExecutionModal({
	children,
	onBackdropClick,
	maxWidthClass = "max-w-5xl",
}: ExecutionModalProps) {
	const stopPropagation = useCallback(
		(e: React.MouseEvent) => e.stopPropagation(),
		[],
	);

	return (
		<>
			{/* Backdrop - sits below the execution panel (z-40 < z-50) */}
			<div
				className="fixed inset-0 bg-black/40 z-40 animate-fadeIn"
				onClick={onBackdropClick}
			/>

			{/* Dialog - sits above the execution panel (z-[60] > z-50) */}
			<div className="fixed inset-0 flex items-center justify-center z-[60] pointer-events-none animate-fadeIn">
				{/* Outer gradient frame - creates the "glass halo" effect */}
				<div
					className={`${maxWidthClass} w-full mx-4 p-[1px] rounded-[30px] bg-gradient-to-br from-[rgba(var(--color-primary-rgb),0.3)] via-transparent to-[rgba(var(--color-primary-rgb),0.1)] animate-scaleIn pointer-events-auto`}
					onClick={stopPropagation}
				>
					{/* Inner modal shell - Light theme */}
					<div className="rounded-[30px] border border-slate-200 bg-white shadow-[0_35px_120px_rgba(0,0,0,0.15)] max-h-[90vh] overflow-hidden">
						{children}
					</div>
				</div>
			</div>
		</>
	);
}
