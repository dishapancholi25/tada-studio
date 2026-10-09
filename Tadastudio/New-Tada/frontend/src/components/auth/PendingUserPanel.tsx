"use client";

import { Clock, RefreshCw, LogOut } from "lucide-react";

interface PendingUserPanelProps {
	userEmail?: string;
	userName?: string;
	onRetry: () => void;
	onSignOut: () => void;
}

export default function PendingUserPanel({
	userEmail,
	userName,
	onRetry,
	onSignOut,
}: PendingUserPanelProps) {
	return (
		<div
			className="fixed inset-0 z-50 flex items-center justify-center p-4"
			style={{
				background: "var(--color-bg-primary)",
			}}
		>
			<div
				className="max-w-md w-full rounded-xl p-8 shadow-xl"
				style={{
					background: "var(--color-bg-secondary)",
					border: "1px solid var(--color-border)",
				}}
			>
				{/* Icon */}
				<div className="flex justify-center mb-6">
					<div
						className="p-4 rounded-full"
						style={{
							background: "rgba(251, 191, 36, 0.1)",
						}}
					>
						<Clock
							className="w-12 h-12"
							style={{ color: "rgb(251, 191, 36)" }}
						/>
					</div>
				</div>

				{/* Title */}
				<h1
					className="text-2xl font-bold text-center mb-3"
					style={{ color: "var(--color-text-primary)" }}
				>
					Account Pending Approval
				</h1>

				{/* Description */}
				<p
					className="text-center mb-6"
					style={{ color: "var(--color-text-secondary)" }}
				>
					Your account has been created, but access is pending approval from an
					administrator. You will be able to use the system once your account is
					activated.
				</p>

				{/* User Info */}
				{(userName || userEmail) && (
					<div
						className="mb-6 p-4 rounded-lg"
						style={{
							background: "var(--color-bg-tertiary)",
							border: "1px solid var(--color-border)",
						}}
					>
						{userName && (
							<p
								className="font-medium mb-1"
								style={{ color: "var(--color-text-primary)" }}
							>
								{userName}
							</p>
						)}
						{userEmail && (
							<p
								className="text-sm"
								style={{ color: "var(--color-text-secondary)" }}
							>
								{userEmail}
							</p>
						)}
					</div>
				)}

				{/* Actions */}
				<div className="flex flex-col gap-3">
					<button
						type="button"
						onClick={onRetry}
						className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg font-medium transition-colors"
						style={{
							background: "var(--color-primary)",
							color: "white",
						}}
						onMouseEnter={(e) => {
							e.currentTarget.style.opacity = "0.9";
						}}
						onMouseLeave={(e) => {
							e.currentTarget.style.opacity = "1";
						}}
					>
						<RefreshCw className="w-4 h-4" />
						Retry Connection
					</button>

					<button
						type="button"
						onClick={onSignOut}
						className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg font-medium transition-colors"
						style={{
							background: "transparent",
							color: "var(--color-text-secondary)",
							border: "1px solid var(--color-border)",
						}}
						onMouseEnter={(e) => {
							e.currentTarget.style.background = "var(--color-bg-tertiary)";
							e.currentTarget.style.color = "var(--color-text-primary)";
						}}
						onMouseLeave={(e) => {
							e.currentTarget.style.background = "transparent";
							e.currentTarget.style.color = "var(--color-text-secondary)";
						}}
					>
						<LogOut className="w-4 h-4" />
						Sign Out
					</button>
				</div>

				{/* Footer note */}
				<p
					className="text-xs text-center mt-6"
					style={{ color: "var(--color-text-muted)" }}
				>
					Need help? Contact your system administrator.
				</p>
			</div>
		</div>
	);
}
