"use client";

import React from "react";

// Loading spinner component for general use
export function LoadingSpinner({
	size = "md",
	className = "",
}: {
	size?: "sm" | "md" | "lg";
	className?: string;
}) {
	const sizeClasses = {
		sm: "w-4 h-4",
		md: "w-8 h-8",
		lg: "w-10 h-10",
	};

	return (
		<div className={`flex items-center justify-center ${className}`}>
			<div
				className={`${sizeClasses[size]} animate-spin rounded-full border-2 border-transparent border-t-orange-500`}
			/>
		</div>
	);
}

// Page loading component - used for sidebar page loading states
export function PageLoading({ message = "Loading..." }: { message?: string }) {
	return (
		<div className="h-full bg-white flex items-center justify-center p-6">
			<div className="flex flex-col items-center justify-center gap-4 rounded-2xl bg-white px-8 py-16 w-full max-w-md">
				<LoadingSpinner size="lg" />
				<p className="text-sm text-slate-600">
					{message}
				</p>
			</div>
		</div>
	);
}

// Workflow loading component
export function WorkflowLoading({
	message = "Loading workflow...",
}: {
	message?: string;
}) {
	return (
		<div className="h-screen flex flex-col items-center justify-center bg-gradient-to-br from-orange-50 to-orange-100 gap-6 animate-fadeIn">
			<div className="w-12 h-12 rounded-full border-[3px] border-orange-200 border-t-orange-500 animate-spin" />
			<p className="text-slate-700 text-lg animate-pulse">
				{message}
			</p>
		</div>
	);
}
