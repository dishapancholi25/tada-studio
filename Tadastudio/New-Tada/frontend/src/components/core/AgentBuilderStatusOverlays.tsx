"use client";

import React from "react";

interface AgentBuilderStatusOverlaysProps {
	error: string | null;
	loading: boolean;
}

const AgentBuilderStatusOverlays = React.memo(
	function AgentBuilderStatusOverlays({
		error,
		loading,
	}: AgentBuilderStatusOverlaysProps) {
		return (
			<>
				{/* Error Display */}
				{error && (
					<div className="absolute top-4 left-1/2 transform -translate-x-1/2 bg-red-600 text-white px-4 py-2 rounded-lg shadow-lg animate-fadeIn">
						{error}
					</div>
				)}

				{/* Loading Indicator - Show for operations */}
				{loading && (
					<div className="absolute top-4 right-4 bg-[color:var(--color-surface)] text-[color:var(--color-text-primary)] px-4 py-2 rounded-lg shadow-lg animate-fadeIn flex items-center gap-2 z-50">
						<div className="w-4 h-4 border-2 border-[color:var(--color-border)] border-t-[color:var(--color-accent)] rounded-full animate-spin"></div>
						Saving...
					</div>
				)}
			</>
		);
	},
);

export default AgentBuilderStatusOverlays;
