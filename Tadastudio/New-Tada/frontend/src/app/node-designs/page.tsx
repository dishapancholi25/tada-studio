"use client";

import React, { useState } from "react";

// Design 1: Modern Gradient with Animated Glow
const Design1Start = ({ data }: { data?: any }) => (
	<div className="relative group">
		<div className="absolute -inset-1 bg-gradient-to-r from-[#0DA931] to-emerald-600 rounded-xl blur opacity-75 group-hover:opacity-100 transition duration-200 animate-pulse"></div>
		<div className="relative bg-gradient-to-br from-[#0DA931] to-emerald-600 rounded-xl px-8 py-4 text-white shadow-xl">
			<div className="flex items-center gap-3">
				<div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center backdrop-blur">
					<svg
						className="w-6 h-6"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path
							strokeLinecap="round"
							strokeLinejoin="round"
							strokeWidth={2}
							d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
						/>
						<path
							strokeLinecap="round"
							strokeLinejoin="round"
							strokeWidth={2}
							d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
						/>
					</svg>
				</div>
				<div>
					<h3 className="text-lg font-bold">Start</h3>
					<p className="text-xs text-slate-700">Entry Point</p>
				</div>
			</div>
		</div>
		<div className="absolute -right-1.5 top-1/2 -translate-y-1/2 w-3 h-3 bg-white border-2 border-[#0DA931] rounded-full" />
	</div>
);

const Design1End = ({ data }: { data?: any }) => (
	<div className="relative group">
		<div className="absolute -inset-1 bg-gradient-to-r from-red-600 to-rose-600 rounded-xl blur opacity-75 group-hover:opacity-100 transition duration-200 animate-pulse"></div>
		<div className="relative bg-gradient-to-br from-red-500 to-rose-600 rounded-xl px-8 py-4 text-white shadow-xl">
			<div className="flex items-center gap-3">
				<div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center backdrop-blur">
					<svg
						className="w-6 h-6"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path
							strokeLinecap="round"
							strokeLinejoin="round"
							strokeWidth={2}
							d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
						/>
					</svg>
				</div>
				<div>
					<h3 className="text-lg font-bold">End</h3>
					<p className="text-xs text-slate-700">Exit Point</p>
				</div>
			</div>
		</div>
		<div className="absolute -left-1.5 top-1/2 -translate-y-1/2 w-3 h-3 bg-white border-2 border-red-400 rounded-full" />
	</div>
);

// Design 2: Glassmorphism
const Design2Start = ({ data }: { data?: any }) => (
	<div className="relative">
		<div className="absolute inset-0 bg-gradient-to-r from-[#0DA931] to-emerald-500 rounded-2xl blur-xl opacity-50"></div>
		<div className="relative bg-slate-100 backdrop-blur-md border border-slate-300 rounded-2xl px-6 py-4 shadow-2xl">
			<div className="flex items-center gap-3">
				<div className="w-12 h-12 bg-gradient-to-br from-[#0DA931] to-emerald-500 rounded-xl flex items-center justify-center shadow-lg">
					<svg
						className="w-7 h-7 text-white"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path
							strokeLinecap="round"
							strokeLinejoin="round"
							strokeWidth={2.5}
							d="M5 13l4 4L19 7"
						/>
					</svg>
				</div>
				<div>
					<h3 className="text-white font-bold text-lg">Start Node</h3>
					<p className="text-[#0DA931] text-sm">Workflow Entry</p>
				</div>
			</div>
		</div>
		<div className="absolute -right-2 top-1/2 -translate-y-1/2 w-4 h-4 bg-gradient-to-r from-[#0DA931] to-emerald-500 rounded-full" />
	</div>
);

const Design2End = ({ data }: { data?: any }) => (
	<div className="relative">
		<div className="absolute inset-0 bg-gradient-to-r from-red-400 to-rose-500 rounded-2xl blur-xl opacity-50"></div>
		<div className="relative bg-slate-100 backdrop-blur-md border border-slate-300 rounded-2xl px-6 py-4 shadow-2xl">
			<div className="flex items-center gap-3">
				<div className="w-12 h-12 bg-gradient-to-br from-red-400 to-rose-500 rounded-xl flex items-center justify-center shadow-lg">
					<svg
						className="w-7 h-7 text-white"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path
							strokeLinecap="round"
							strokeLinejoin="round"
							strokeWidth={2.5}
							d="M6 18L18 6M6 6l12 12"
						/>
					</svg>
				</div>
				<div>
					<h3 className="text-white font-bold text-lg">End Node</h3>
					<p className="text-red-200 text-sm">Workflow Exit</p>
				</div>
			</div>
		</div>
		<div className="absolute -left-2 top-1/2 -translate-y-1/2 w-4 h-4 bg-gradient-to-r from-red-400 to-rose-500 rounded-full" />
	</div>
);

// Design 3: Minimalist with Hover Effects
const Design3Start = ({ data }: { data?: any }) => (
	<div className="group">
		<div className="bg-[color:var(--color-bg-secondary)] border-2 border-[#0DA931] rounded-lg px-6 py-3 transition-all duration-300 group-hover:border-[#0DA931] group-hover:shadow-[0_0_20px_rgba(13,169,49,0.5)]">
			<div className="flex items-center gap-2">
				<div className="w-2 h-2 bg-[#F1F8E9]0 rounded-full animate-pulse"></div>
				<span className="text-white font-medium">Start</span>
				<svg
					className="w-4 h-4 text-[#0DA931] group-hover:translate-x-1 transition-transform"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
				>
					<path
						strokeLinecap="round"
						strokeLinejoin="round"
						strokeWidth={2}
						d="M13 7l5 5m0 0l-5 5m5-5H6"
					/>
				</svg>
			</div>
		</div>
		<div className="absolute -right-1 top-1/2 -translate-y-1/2 w-2 h-2 bg-[#F1F8E9]0 border border-[color:var(--color-bg-secondary)] rounded-full" />
	</div>
);

const Design3End = ({ data }: { data?: any }) => (
	<div className="group">
		<div className="bg-[color:var(--color-bg-secondary)] border-2 border-red-500 rounded-lg px-6 py-3 transition-all duration-300 group-hover:border-red-400 group-hover:shadow-[0_0_20px_rgba(239,68,68,0.5)]">
			<div className="flex items-center gap-2">
				<svg
					className="w-4 h-4 text-red-400 group-hover:-translate-x-1 transition-transform"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
				>
					<path
						strokeLinecap="round"
						strokeLinejoin="round"
						strokeWidth={2}
						d="M11 17l-5-5m0 0l5-5m-5 5h12"
					/>
				</svg>
				<span className="text-white font-medium">End</span>
				<div className="w-2 h-2 bg-red-500 rounded-full"></div>
			</div>
		</div>
		<div className="absolute -left-1 top-1/2 -translate-y-1/2 w-2 h-2 bg-red-500 border border-[color:var(--color-bg-secondary)] rounded-full" />
	</div>
);

// Design 4: Futuristic/Tech Style
const Design4Start = ({ data }: { data?: any }) => (
	<div className="relative">
		<div className="absolute -inset-px bg-gradient-to-r from-[color:var(--color-primary)] via-[color:var(--color-border)] to-[color:var(--color-accent)] rounded-lg opacity-75 blur animate-pulse"></div>
		<div className="relative bg-[#0d0d0d] rounded-lg p-1">
			<div className="bg-gradient-to-r from-[color:var(--color-bg-secondary)] to-[color:var(--color-surface)] rounded-md px-6 py-3">
				<div className="flex items-center gap-3">
					<div className="relative">
						<div className="absolute inset-0 bg-[#F1F8E9]0 blur-md"></div>
						<div className="relative w-8 h-8 bg-gradient-to-br from-[#0DA931] to-emerald-600 rounded-md flex items-center justify-center">
							<span className="text-white font-bold text-sm">▶</span>
						</div>
					</div>
					<div className="flex flex-col">
						<span className="text-[#0DA931] text-xs font-mono">NODE_START</span>
						<span className="text-white font-semibold">Initialize</span>
					</div>
				</div>
			</div>
		</div>
		<div className="absolute -right-1.5 top-1/2 -translate-y-1/2 w-3 h-3 bg-[#0DA931] rounded-full" />
	</div>
);

const Design4End = ({ data }: { data?: any }) => (
	<div className="relative">
		<div className="absolute -inset-px bg-gradient-to-r from-red-500 via-rose-500 to-pink-500 rounded-lg opacity-75 blur animate-pulse"></div>
		<div className="relative bg-[#0d0d0d] rounded-lg p-1">
			<div className="bg-gradient-to-r from-[color:var(--color-bg-secondary)] to-[color:var(--color-surface)] rounded-md px-6 py-3">
				<div className="flex items-center gap-3">
					<div className="relative">
						<div className="absolute inset-0 bg-red-500 blur-md"></div>
						<div className="relative w-8 h-8 bg-gradient-to-br from-red-400 to-rose-600 rounded-md flex items-center justify-center">
							<span className="text-white font-bold text-sm">■</span>
						</div>
					</div>
					<div className="flex flex-col">
						<span className="text-red-400 text-xs font-mono">NODE_END</span>
						<span className="text-white font-semibold">Terminate</span>
					</div>
				</div>
			</div>
		</div>
		<div className="absolute -left-1.5 top-1/2 -translate-y-1/2 w-3 h-3 bg-red-400 rounded-full" />
	</div>
);

// Main component to showcase all designs
export default function NodeDesignShowcase() {
	const [selectedDesign, setSelectedDesign] = useState(1);

	const designs = [
		{ id: 1, name: "Modern Gradient", start: Design1Start, end: Design1End },
		{ id: 2, name: "Glassmorphism", start: Design2Start, end: Design2End },
		{ id: 3, name: "Minimalist", start: Design3Start, end: Design3End },
		{ id: 4, name: "Futuristic", start: Design4Start, end: Design4End },
	];

	const CurrentDesign = designs.find((d) => d.id === selectedDesign);

	return (
		<div className="min-h-screen bg-[color:var(--color-bg-secondary)] p-8">
			<div className="max-w-6xl mx-auto">
				<h1 className="text-3xl font-bold text-slate-900 mb-8">
					Workflow Node Designs
				</h1>

				{/* Design selector */}
				<div className="flex gap-4 mb-12">
					{designs.map((design) => (
						<button
							key={design.id}
							onClick={() => setSelectedDesign(design.id)}
							className={`px-4 py-2 rounded-lg font-medium transition-all ${
								selectedDesign === design.id
									? "bg-[color:var(--color-primary)] btn-primary-text"
									: "bg-[color:var(--color-surface)] text-[color:var(--color-text-muted)] hover:bg-[color:var(--color-border)]"
							}`}
						>
							{design.name}
						</button>
					))}
				</div>

				{/* Current design preview */}
				<div className="bg-[color:var(--color-surface)] rounded-2xl p-12 mb-12">
					<div className="flex justify-between items-center">
						{CurrentDesign && (
							<>
								<CurrentDesign.start />
								<div className="flex-1 border-t-2 border-dashed border-[color:var(--color-surface-hover)] mx-8"></div>
								<CurrentDesign.end />
							</>
						)}
					</div>
				</div>

				{/* All designs grid */}
				<h2 className="text-xl font-semibold text-slate-900 mb-6">All Designs</h2>
				<div className="grid grid-cols-1 md:grid-cols-2 gap-8">
					{designs.map((design) => (
						<div
							key={design.id}
							className="bg-[color:var(--color-surface)] rounded-xl p-8"
						>
							<h3 className="text-slate-900 font-medium mb-4">{design.name}</h3>
							<div className="flex justify-between items-center">
								<design.start />
								<div className="flex-1 border-t border-[color:var(--color-border)] mx-4"></div>
								<design.end />
							</div>
						</div>
					))}
				</div>
			</div>
		</div>
	);
}
