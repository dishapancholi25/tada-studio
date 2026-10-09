"use client";

import { AlertCircle, AlertTriangle, CheckCircle, Info, X } from "lucide-react";
import type React from "react";
import { createContext, useCallback, useContext, useState } from "react";

type ToastType = "success" | "error" | "warning" | "info";

interface Toast {
	id: string;
	type: ToastType;
	title: string;
	message?: string;
	duration?: number;
}

interface ToastContextType {
	showToast: (
		type: ToastType,
		title: string,
		message?: string,
		duration?: number,
	) => void;
	showSuccess: (title: string, message?: string) => void;
	showError: (title: string, message?: string) => void;
	showWarning: (title: string, message?: string) => void;
	showInfo: (title: string, message?: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const useToast = () => {
	const context = useContext(ToastContext);
	if (!context) {
		throw new Error("useToast must be used within a ToastProvider");
	}
	return context;
};

const getToastIcon = (type: ToastType) => {
	switch (type) {
		case "success":
			return <CheckCircle className="w-5 h-5" />;
		case "error":
			return <AlertCircle className="w-5 h-5" />;
		case "warning":
			return <AlertTriangle className="w-5 h-5" />;
		case "info":
			return <Info className="w-5 h-5" />;
	}
};

const baseToastClass = "flex items-start gap-3 p-4 rounded-lg shadow-xl border transition-all duration-300";

const getToastInlineStyles = (type: ToastType): React.CSSProperties => {
	switch (type) {
		case "success":
			return {
				backgroundColor: "#0DA931",
				borderColor: "#0DA931",
				color: "#F1F8E9",
			};
		case "error":
			return {
				backgroundColor: "#dc2626",
				borderColor: "#ef4444",
				color: "white",
			};
		case "warning":
			return {
				backgroundColor: "var(--color-warning)",
				borderColor: "var(--color-warning)",
				color: "white",
			};
		case "info":
			return {
				backgroundColor: "var(--color-accent)",
				borderColor: "var(--color-accent)",
				color: "white",
			};
	}
};

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({
	children,
}) => {
	const [toasts, setToasts] = useState<Toast[]>([]);

	const removeToast = useCallback((id: string) => {
		setToasts((prev) => prev.filter((toast) => toast.id !== id));
	}, []);

	const createRemoveHandler = useCallback(
		(id: string) => () => removeToast(id),
		[removeToast],
	);

	const showToast = useCallback(
		(type: ToastType, title: string, message?: string, duration = 5000) => {
			const id = Date.now().toString();
			const toast: Toast = { id, type, title, message, duration };

			setToasts((prev) => [...prev, toast]);

			if (duration > 0) {
				setTimeout(() => removeToast(id), duration);
			}
		},
		[removeToast],
	);

	const showSuccess = useCallback(
		(title: string, message?: string) => {
			showToast("success", title, message);
		},
		[showToast],
	);

	const showError = useCallback(
		(title: string, message?: string) => {
			showToast("error", title, message, 5000);
		},
		[showToast],
	);

	const showWarning = useCallback(
		(title: string, message?: string) => {
			showToast("warning", title, message);
		},
		[showToast],
	);

	const showInfo = useCallback(
		(title: string, message?: string) => {
			showToast("info", title, message);
		},
		[showToast],
	);

	return (
		<ToastContext.Provider
			value={{ showToast, showSuccess, showError, showWarning, showInfo }}
		>
			{children}

			{/* Toast Container */}
			<div className="fixed top-4 right-4 z-[9999] space-y-2 max-w-md">
				{toasts.map((toast) => (
					<div
						key={toast.id}
						className={`${baseToastClass} toast-animation`}
						style={getToastInlineStyles(toast.type)}
					>
						<div className="flex-shrink-0 mt-0.5">
							{getToastIcon(toast.type)}
						</div>

						<div className="flex-1 min-w-0">
							<h3 className="font-semibold">{toast.title}</h3>
							{toast.message && (
								<p className="mt-1 text-sm opacity-90 whitespace-pre-wrap">{toast.message}</p>
							)}
						</div>

						<button
							onClick={createRemoveHandler(toast.id)}
							className="flex-shrink-0 ml-4 opacity-70 hover:opacity-100 transition-opacity"
						>
							<X className="w-4 h-4" />
						</button>
					</div>
				))}
			</div>
		</ToastContext.Provider>
	);
};
