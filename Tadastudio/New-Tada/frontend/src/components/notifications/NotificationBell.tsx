"use client";

import React, { useState, useRef, useEffect } from "react";
import { useAccessRequests, type AccessRequest } from "@/contexts/AccessRequestContext";
import { useToast } from "@/contexts/ToastContext";

interface NotificationBellProps {
	workflowId?: string;
}

export function NotificationBell({ workflowId }: NotificationBellProps) {
	const { pendingRequests, approveRequest, rejectRequest } = useAccessRequests();
	const { showSuccess, showInfo, showError } = useToast();
	const [isOpen, setIsOpen] = useState(false);
	const [loadingId, setLoadingId] = useState<string | null>(null);
	const dropdownRef = useRef<HTMLDivElement>(null);

	// Filter requests to only show ones for the current workflow (if workflowId provided)
	const filteredRequests = workflowId
		? pendingRequests.filter((req) => req.workflow_id === workflowId)
		: pendingRequests;

	const count = filteredRequests.length;

	// Close dropdown when clicking outside
	useEffect(() => {
		function handleClickOutside(event: MouseEvent) {
			if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
				setIsOpen(false);
			}
		}
		document.addEventListener("mousedown", handleClickOutside);
		return () => document.removeEventListener("mousedown", handleClickOutside);
	}, []);

	const handleApprove = async (requestId: string, request: AccessRequest, e: React.MouseEvent) => {
		e.stopPropagation();
		setLoadingId(requestId);
		try {
			await approveRequest(requestId);
			const requesterName = request.requester_email?.split("@")[0] || "User";
			showSuccess(
				"Access Granted",
				`${requesterName} now has editor access`
			);
		} catch (error) {
			console.error("Failed to approve:", error);
			showError("Failed", "Could not approve the request");
		} finally {
			setLoadingId(null);
		}
	};

	const handleReject = async (requestId: string, request: AccessRequest, e: React.MouseEvent) => {
		e.stopPropagation();
		setLoadingId(requestId);
		try {
			await rejectRequest(requestId);
			const requesterName = request.requester_email?.split("@")[0] || "User";
			showInfo(
				"Request Declined",
				`Access request from ${requesterName} was declined`
			);
		} catch (error) {
			console.error("Failed to reject:", error);
			showError("Failed", "Could not decline the request");
		} finally {
			setLoadingId(null);
		}
	};

	const formatTimeAgo = (dateString: string) => {
		const date = new Date(dateString);
		const now = new Date();
		const diffMs = now.getTime() - date.getTime();
		const diffMins = Math.floor(diffMs / 60000);
		const diffHours = Math.floor(diffMins / 60);
		const diffDays = Math.floor(diffHours / 24);

		if (diffMins < 1) return "just now";
		if (diffMins < 60) return `${diffMins}m ago`;
		if (diffHours < 24) return `${diffHours}h ago`;
		return `${diffDays}d ago`;
	};

	return (
		<div className="relative" ref={dropdownRef}>
			{/* Bell Button - always visible */}
			<button
				type="button"
				onClick={() => setIsOpen(!isOpen)}
				className="relative flex h-8 w-8 items-center justify-center rounded-lg text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-700 focus-visible:outline-none"
				aria-label={count > 0 ? `${count} pending access requests` : "No access requests"}
				title={count > 0 ? `${count} pending access request${count !== 1 ? "s" : ""}` : "Access requests"}
			>
				<svg
					className="h-5 w-5"
					fill="none"
					viewBox="0 0 24 24"
					stroke="currentColor"
					strokeWidth={1.5}
				>
					<path
						strokeLinecap="round"
						strokeLinejoin="round"
						d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0"
					/>
				</svg>

				{/* Red badge with count */}
				{count > 0 && (
					<span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
						{count > 9 ? "9+" : count}
					</span>
				)}
			</button>

			{/* Dropdown */}
			{isOpen && (
				<div
					className="absolute right-0 top-full z-50 mt-2 w-80 overflow-hidden rounded-lg border shadow-lg"
					style={{
						backgroundColor: "var(--color-bg-primary)",
						borderColor: "var(--color-border)",
					}}
				>
					<div
						className="px-4 py-3 border-b"
						style={{ borderColor: "var(--color-border)" }}
					>
						<h3
							className="font-semibold text-sm"
							style={{ color: "var(--color-text-primary)" }}
						>
							Access Requests
						</h3>
						<p
							className="text-xs mt-0.5"
							style={{ color: "var(--color-text-muted)" }}
						>
							{count > 0
								? `${count} pending for this workflow`
								: "No pending requests"}
						</p>
					</div>

					{count === 0 ? (
						<div
							className="px-4 py-6 text-center text-sm"
							style={{ color: "var(--color-text-muted)" }}
						>
							No pending access requests
						</div>
					) : (
						<div className="max-h-64 overflow-y-auto">
							{filteredRequests.map((request) => (
								<div
									key={request.id}
									className="px-4 py-3 border-b last:border-b-0"
									style={{ borderColor: "var(--color-border)" }}
								>
									<div className="flex items-start gap-3">
										{/* User avatar */}
										<div
											className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-semibold"
											style={{
												backgroundColor: "var(--color-accent)",
												color: "white",
											}}
										>
											{request.requester_email?.charAt(0).toUpperCase() || "?"}
										</div>

										<div className="flex-1 min-w-0">
											<p
												className="text-sm font-medium truncate"
												style={{ color: "var(--color-text-primary)" }}
											>
												{request.requester_email || request.requester_id}
											</p>
											<p
												className="text-xs"
												style={{ color: "var(--color-text-muted)" }}
											>
												Wants editor access
											</p>
											{request.message && (
												<p
													className="mt-1 text-xs italic truncate"
													style={{ color: "var(--color-text-secondary)" }}
												>
													"{request.message}"
												</p>
											)}
											<p
												className="mt-1 text-xs"
												style={{ color: "var(--color-text-muted)" }}
											>
												{formatTimeAgo(request.created_at)}
											</p>

											{/* Action buttons */}
											<div className="mt-2 flex gap-2">
												<button
													onClick={(e) => handleApprove(request.id, request, e)}
													disabled={loadingId === request.id}
													className="flex items-center gap-1 rounded bg-green-500 px-2.5 py-1 text-xs font-medium text-white hover:bg-green-600 disabled:opacity-50 transition-colors"
												>
													{loadingId === request.id ? (
														<span className="h-3 w-3 animate-spin rounded-full border-2 border-white border-t-transparent" />
													) : (
														<svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
															<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
														</svg>
													)}
													Approve
												</button>
												<button
													onClick={(e) => handleReject(request.id, request, e)}
													disabled={loadingId === request.id}
													className="flex items-center gap-1 rounded px-2.5 py-1 text-xs font-medium transition-colors disabled:opacity-50"
													style={{
														backgroundColor: "var(--color-surface)",
														color: "var(--color-text-secondary)",
													}}
												>
													<svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
														<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
													</svg>
													Reject
												</button>
											</div>
										</div>
									</div>
								</div>
							))}
						</div>
					)}
				</div>
			)}
		</div>
	);
}

export default NotificationBell;
