"use client";

import ColorPaletteToggle from "@/components/ui/ColorPaletteToggle";
import { useColorTheme } from "@/contexts/ColorThemeContext";

export default function ThemeTestPage() {
	const { theme } = useColorTheme();

	return (
		<div
			className="min-h-screen p-8 space-y-8"
			style={{ background: "var(--color-bg-primary)" }}
		>
			<div className="max-w-4xl mx-auto">
				<h1
					className="text-4xl font-bold mb-4"
					style={{ color: "var(--color-text-primary)" }}
				>
					Theme System Test
				</h1>
				<p
					className="text-lg mb-8"
					style={{ color: "var(--color-text-secondary)" }}
				>
					Current theme: <strong>{theme}</strong>
				</p>

				<div className="flex justify-center mb-8">
					<ColorPaletteToggle />
				</div>

				<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
					{/* Background Colors */}
					<div className="card p-6">
						<h2 className="text-xl font-semibold mb-4 text-primary">
							Background Colors
						</h2>
						<div className="space-y-3">
							<div
								className="p-3 rounded"
								style={{ background: "var(--color-bg-primary)" }}
							>
								<span className="text-primary">Primary Background</span>
							</div>
							<div
								className="p-3 rounded"
								style={{ background: "var(--color-bg-secondary)" }}
							>
								<span className="text-primary">Secondary Background</span>
							</div>
							<div className="p-3 rounded bg-surface">
								<span className="text-primary">Surface</span>
							</div>
						</div>
					</div>

					{/* Text Colors */}
					<div className="card p-6">
						<h2 className="text-xl font-semibold mb-4 text-primary">
							Text Colors
						</h2>
						<div className="space-y-2">
							<div className="text-primary">Primary Text</div>
							<div className="text-secondary">Secondary Text</div>
							<div className="text-muted">Muted Text</div>
						</div>
					</div>

					{/* Brand Colors */}
					<div className="card p-6">
						<h2 className="text-xl font-semibold mb-4 text-primary">
							Brand Colors
						</h2>
						<div className="space-y-3">
							<div
								className="p-3 rounded"
								style={{
									background: "var(--color-primary)",
									color: "var(--color-text-primary)",
								}}
							>
								Primary
							</div>
							<div
								className="p-3 rounded"
								style={{
									background: "var(--color-accent)",
									color: "var(--color-text-primary)",
								}}
							>
								Accent
							</div>
							<div className="p-3 rounded border-default">
								<span className="text-primary">Border</span>
							</div>
						</div>
					</div>

					{/* Buttons */}
					<div className="card p-6">
						<h2 className="text-xl font-semibold mb-4 text-primary">Buttons</h2>
						<div className="space-y-3">
							<button className="btn-primary w-full">Primary Button</button>
							<button className="btn-secondary w-full">Secondary Button</button>
							<button className="btn-ghost w-full">Ghost Button</button>
						</div>
					</div>

					{/* Form Elements */}
					<div className="card p-6">
						<h2 className="text-xl font-semibold mb-4 text-primary">
							Form Elements
						</h2>
						<div className="space-y-3">
							<input
								type="text"
								placeholder="Input field"
								className="form-input"
							/>
							<textarea
								placeholder="Textarea field"
								className="form-textarea"
								rows={3}
							/>
							<select className="form-select">
								<option>Select option</option>
								<option>Option 1</option>
								<option>Option 2</option>
							</select>
						</div>
					</div>

					{/* Glass Effects */}
					<div className="card p-6">
						<h2 className="text-xl font-semibold mb-4 text-primary">
							Glass Effects
						</h2>
						<div className="space-y-3">
							<div className="glass p-3 rounded">
								<span className="text-primary">Glass Effect</span>
							</div>
							<div className="glass-panel p-3 rounded">
								<span className="text-primary">Glass Panel</span>
							</div>
							<div className="glass-strong p-3 rounded">
								<span className="text-primary">Strong Glass</span>
							</div>
						</div>
					</div>
				</div>

				{/* Glow Effects */}
				<div className="mt-8">
					<h2 className="text-2xl font-semibold mb-6 text-primary">
						Glow Effects
					</h2>
					<div className="grid grid-cols-2 md:grid-cols-4 gap-4">
						<div className="p-4 rounded glow-primary text-center text-primary">
							Primary Glow
						</div>
						<div className="p-4 rounded glow-secondary text-center text-primary">
							Secondary Glow
						</div>
						<div className="p-4 rounded glow-success text-center text-primary">
							Success Glow
						</div>
						<div className="p-4 rounded glow-error text-center text-primary">
							Error Glow
						</div>
					</div>
				</div>

				{/* Status Colors */}
				<div className="mt-8">
					<h2 className="text-2xl font-semibold mb-6 text-primary">
						Status Colors
					</h2>
					<div className="grid grid-cols-2 md:grid-cols-4 gap-4">
						<div
							className="p-4 rounded text-center"
							style={{
								background: "var(--color-success)",
								color: "var(--color-text-primary)",
							}}
						>
							Success
						</div>
						<div
							className="p-4 rounded text-center"
							style={{
								background: "var(--color-error)",
								color: "var(--color-text-primary)",
							}}
						>
							Error
						</div>
						<div
							className="p-4 rounded text-center"
							style={{
								background: "var(--color-warning)",
								color: "var(--color-text-primary)",
							}}
						>
							Warning
						</div>
						<div
							className="p-4 rounded text-center"
							style={{
								background: "var(--color-info)",
								color: "var(--color-text-primary)",
							}}
						>
							Info
						</div>
					</div>
				</div>

				{/* Node Colors */}
				<div className="mt-8">
					<h2 className="text-2xl font-semibold mb-6 text-primary">
						Node Type Colors
					</h2>
					<div className="grid grid-cols-2 md:grid-cols-3 gap-4">
						<div
							className="p-4 rounded text-center"
							style={{
								background: "var(--color-node-agent)",
								color: "var(--color-text-primary)",
							}}
						>
							Agent
						</div>
						<div
							className="p-4 rounded text-center"
							style={{
								background: "var(--color-node-tool)",
								color: "var(--color-text-primary)",
							}}
						>
							Tool
						</div>
						<div
							className="p-4 rounded text-center"
							style={{
								background: "var(--color-node-condition)",
								color: "var(--color-text-primary)",
							}}
						>
							Condition
						</div>
						<div
							className="p-4 rounded text-center"
							style={{
								background: "var(--color-node-orchestrator)",
								color: "var(--color-text-primary)",
							}}
						>
							Orchestrator
						</div>
						<div
							className="p-4 rounded text-center"
							style={{
								background: "var(--color-node-end)",
								color: "var(--color-text-primary)",
							}}
						>
							End
						</div>
						<div
							className="p-4 rounded text-center"
							style={{
								background: "var(--color-node-trigger)",
								color: "var(--color-text-primary)",
							}}
						>
							Trigger
						</div>
					</div>
				</div>
			</div>
		</div>
	);
}
