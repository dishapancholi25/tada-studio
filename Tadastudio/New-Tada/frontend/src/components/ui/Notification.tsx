"use client";

import { AlertCircle, CheckCircle, Info, X, XCircle } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

export type NotificationType = "success" | "error" | "warning" | "info";

export interface NotificationProps {
	id: string;
	type: NotificationType;
	title: string;
	message?: string;
	duration?: number;
	onClose: (id: string) => void;
}

const notificationStyles = {
	success: {
		bg: "bg-white/90",
		border: "border-[color:var(--color-success)]",
		icon: CheckCircle,
		iconColor: "text-[color:var(--color-success)]",
		titleColor: "text-[#1E372D]",
	},
	error: {
		bg: "bg-white/90",
		border: "border-[color:var(--color-error)]",
		icon: XCircle,
		iconColor: "text-[color:var(--color-error)]",
		titleColor: "text-[#3B1A24]",
	},
	warning: {
		bg: "bg-white/90",
		border: "border-[color:var(--color-warning)]",
		icon: AlertCircle,
		iconColor: "text-[color:var(--color-warning)]",
		titleColor: "text-[#402417]",
	},
	info: {
		bg: "bg-white/90",
		border: "border-[#3D5A81]",
		icon: Info,
		iconColor: "text-[#3D5A81]",
		titleColor: "text-[#1B253D]",
	},
};

export function Notification({
	id,
	type,
	title,
	message,
	duration = 5000,
	onClose,
}: NotificationProps) {
	const [isLeaving, setIsLeaving] = useState(false);
	const [isEntering, setIsEntering] = useState(true);
	const [isHovered, setIsHovered] = useState(false);
	const style = notificationStyles[type];
	const Icon = style.icon;
	const closeTimerRef = useRef<NodeJS.Timeout | null>(null);
	const remainingRef = useRef(duration);
	const lastTickRef = useRef(Date.now());

	const handleClose = useCallback(() => {
		if (isLeaving) return;
		setIsLeaving(true);
		setTimeout(() => {
			onClose(id);
		}, 300);
	}, [id, onClose, isLeaving]);

	useEffect(() => {
		// Entry animation
		const entryTimer = setTimeout(() => {
			setIsEntering(false);
		}, 50);

		return () => clearTimeout(entryTimer);
	}, []);

	useEffect(() => {
		if (duration <= 0) return;

		// Clear any existing timer
		if (closeTimerRef.current) {
			clearTimeout(closeTimerRef.current);
			closeTimerRef.current = null;
		}

		if (isHovered) {
			// Pause: calculate remaining time
			const elapsed = Date.now() - lastTickRef.current;
			remainingRef.current = Math.max(0, remainingRef.current - elapsed);
		} else {
			// Resume: start timer with remaining time
			lastTickRef.current = Date.now();
			if (remainingRef.current > 0) {
				closeTimerRef.current = setTimeout(() => {
					handleClose();
				}, remainingRef.current);
			}
		}

		return () => {
			if (closeTimerRef.current) {
				clearTimeout(closeTimerRef.current);
			}
		};
	}, [isHovered, duration, handleClose]);

	return (
		<div
			onMouseEnter={() => setIsHovered(true)}
			onMouseLeave={() => setIsHovered(false)}
			className={`
        ${style.bg} ${style.border} 
        backdrop-blur-sm border rounded-lg shadow-2xl p-4 mb-3 
        min-w-[320px] max-w-md
        transform transition-all duration-300 ease-out
        ${isEntering ? "translate-x-full opacity-0 scale-95" : ""}
        ${isLeaving ? "translate-x-full opacity-0" : "translate-x-0 opacity-100 scale-100"}
      `}
		>
			<div className="flex items-start gap-3">
				<Icon className={`w-5 h-5 ${style.iconColor} flex-shrink-0 mt-0.5`} />
				<div className="flex-1 min-w-0">
					<h3 className={`font-semibold ${style.titleColor}`}>{title}</h3>
					{message && (
						<p className="text-sm text-[color:var(--color-text-secondary)] mt-1 whitespace-pre-wrap">
							{message}
						</p>
					)}
				</div>
				<button
					onClick={handleClose}
					className="text-[color:var(--color-text-muted)] hover:text-gray-200 transition-colors p-1 hover:bg-slate-100 rounded"
				>
					<X className="w-4 h-4" />
				</button>
			</div>
		</div>
	);
}

// Notification Container
export function NotificationContainer({
	children,
}: {
	children: React.ReactNode;
}) {
	return (
		<div className="fixed top-4 right-4 z-[10000] pointer-events-none">
			<div className="pointer-events-auto">{children}</div>
		</div>
	);
}
