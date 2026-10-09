"use client";

import { BookOpen, Rocket, Sparkles, X } from "lucide-react";
import { useEffect, useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { useTutorial } from "./TutorialContext";
import { getTutorialState } from "./persistence";

const WELCOME_DISMISSED_KEY = "as-welcome-dismissed";

function isFirstTimeUser(): boolean {
	if (typeof window === "undefined") return false;
	// Already dismissed the welcome dialog
	if (localStorage.getItem(WELCOME_DISMISSED_KEY)) return false;
	// If they've completed or started any tutorial, they're not new
	const state = getTutorialState();
	const hasCompleted = Object.keys(state.completedTutorials).length > 0;
	const hasProgress = Object.keys(state.lastStepReached).length > 0;
	return !hasCompleted && !hasProgress;
}

function dismissWelcome(): void {
	if (typeof window !== "undefined") {
		localStorage.setItem(WELCOME_DISMISSED_KEY, "true");
	}
}

export default function WelcomeDialog() {
	const [visible, setVisible] = useState(false);
	const { startTutorial, isRunning } = useTutorial();
	const { user, isAuthenticated } = useAuth();

	useEffect(() => {
		if (isAuthenticated && !isRunning && isFirstTimeUser()) {
			// Small delay so the page renders first
			const timer = setTimeout(() => setVisible(true), 800);
			return () => clearTimeout(timer);
		}
	}, [isAuthenticated, isRunning]);

	if (!visible) return null;

	const firstName = user?.first_name || user?.given_name || user?.name?.split(" ")[0] || "";

	const handleStartTutorial = () => {
		dismissWelcome();
		setVisible(false);
		startTutorial("home");
	};

	const handleDismiss = () => {
		dismissWelcome();
		setVisible(false);
	};

	return (
		<div
			className="fixed inset-0 z-[10001] flex items-center justify-center"
			style={{ background: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)" }}
		>
			<div
				className="relative w-full max-w-lg mx-4 rounded-2xl border overflow-hidden animate-fadeIn"
				style={{
					background: "linear-gradient(145deg, rgba(var(--color-primary-rgb), 0.12), var(--color-bg-secondary) 40%)",
					borderColor: "rgba(var(--color-primary-rgb), 0.3)",
					boxShadow: "0 0 40px rgba(var(--color-primary-rgb), 0.15), 0 20px 60px rgba(0,0,0,0.5)",
				}}
			>
				{/* Close button */}
				<button
					type="button"
					onClick={handleDismiss}
					className="absolute top-4 right-4 p-1.5 rounded-lg transition-colors"
					style={{ color: "var(--color-text-muted)" }}
					aria-label="Dismiss welcome"
				>
					<X size={18} />
				</button>

				{/* Header accent bar */}
				<div
					className="h-1 w-full"
					style={{
						background: "linear-gradient(90deg, var(--color-primary), var(--color-accent))",
					}}
				/>

				<div className="px-8 pt-8 pb-6">
					{/* Icon */}
					<div className="flex justify-center mb-5">
						<div
							className="flex items-center justify-center w-16 h-16 rounded-2xl"
							style={{
								background: "rgba(var(--color-primary-rgb), 0.15)",
								border: "1px solid rgba(var(--color-primary-rgb), 0.25)",
							}}
						>
							<Sparkles
								size={32}
								style={{ color: "var(--color-primary)" }}
							/>
						</div>
					</div>

					{/* Title */}
					<h2
						className="text-2xl font-bold text-center mb-2"
						style={{ color: "var(--color-text-primary)" }}
					>
						Welcome{firstName ? `, ${firstName}` : ""}!
					</h2>

					{/* Subtitle */}
					<p
						className="text-center text-sm mb-6"
						style={{ color: "var(--color-text-secondary)" }}
					>
						TADA Studio lets you design, orchestrate, and deploy AI agent
						workflows visually. Let us show you around.
					</p>

					{/* Feature highlights */}
					<div className="flex flex-col gap-3 mb-8">
						{[
							{
								icon: <Rocket size={16} />,
								text: "Build workflows with drag-and-drop nodes",
							},
							{
								icon: <BookOpen size={16} />,
								text: "Connect AI agents, tools, and data sources",
							},
							{
								icon: <Sparkles size={16} />,
								text: "Execute and evaluate your workflows in real time",
							},
						].map((item) => (
							<div
								key={item.text}
								className="flex items-center gap-3 px-4 py-2.5 rounded-xl"
								style={{
									background: "rgba(var(--color-primary-rgb), 0.06)",
									border: "1px solid rgba(var(--color-primary-rgb), 0.1)",
								}}
							>
								<span style={{ color: "var(--color-primary)" }}>
									{item.icon}
								</span>
								<span
									className="text-sm"
									style={{ color: "var(--color-text-primary)" }}
								>
									{item.text}
								</span>
							</div>
						))}
					</div>

					{/* Actions */}
					<div className="flex flex-col gap-3">
						<button
							type="button"
							onClick={handleStartTutorial}
							className="w-full py-3 px-6 rounded-xl font-semibold text-sm transition-all duration-200 hover:scale-[1.02]"
							style={{
								background: "linear-gradient(135deg, var(--color-primary), var(--color-accent))",
								color: "var(--button-primary-text)",
								boxShadow: "0 4px 20px rgba(var(--color-primary-rgb), 0.3)",
							}}
						>
							Start the Getting Started Tutorial
						</button>
						<button
							type="button"
							onClick={handleDismiss}
							className="w-full py-2.5 px-6 rounded-xl text-sm font-medium transition-colors"
							style={{
								background: "transparent",
								color: "var(--color-text-muted)",
								border: "1px solid var(--color-border)",
							}}
						>
							Skip for now &mdash; I&apos;ll explore on my own
						</button>
					</div>

					{/* Hint */}
					<p
						className="text-center text-xs mt-4"
						style={{ color: "var(--color-text-muted)" }}
					>
						You can always start the tutorial later from the{" "}
						<span
							className="font-medium"
							style={{ color: "var(--color-primary)" }}
						>
							?
						</span>{" "}
						button in the bottom-right corner.
					</p>
				</div>
			</div>
		</div>
	);
}
