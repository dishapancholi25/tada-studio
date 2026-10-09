"use client";

import React, { useState, useRef, useEffect } from "react";
import { useAccessRequests } from "@/contexts/AccessRequestContext";
import { useRouter } from "next/navigation";

export function GlobalNotificationBell() {
	const { pendingRequests, approveRequest, rejectRequest } = useAccessRequests();
	const [isOpen, setIsOpen] = useState(false);
	const [loadingId, setLoadingId] = useState<string | null>(null);
	const dropdownRef = useRef<HTMLDivElement>(null);
	const router = useRouter();

	const count = pendingRequests.length;

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

	const handleApprove = async (requestId: string, e: React.MouseEvent) => {
		e.stopPropagation();
		setLoadingId(requestId);
		try {
			await approveRequest(requestId);
		} catch (error) {
			console.error("Failed to approve:", error);
		} finally {
			setLoadingId(null);
		}
	};

	const handleReject = async (requestId: string, e: React.MouseEvent) => {
		e.stopPropagation();
		setLoadingId(requestId);
		try {
			await rejectRequest(requestId);
		} catch (error) {
			console.error("Failed to reject:", error);
		} finally {
			setLoadingId(null);
		}
	};

	const navigateToWorkflow = (workflowId: string) => {
		setIsOpen(false);
		router.push(`/workflow/${workflowId}`);
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
			{/* Bell Button */}
			<button
				type="button"
				onClick={() => setIsOpen(!isOpen)}
				className="relative flex h-9 w-9 items-center justify-center rounded-lg text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-900 focus-visible:outline-none"
				aria-label={count > 0 ? `${count} pending access requests` : "No notifications"}
			>
				<svg
					className="h-[18px] w-[18px]"
					fill="none"
					viewBox="0 0 24 24"
					stroke="currentColor"
					strokeWidth={2}
				>
					<path
						strokeLinecap="round"
						strokeLinejoin="round"
						d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
					/>
				</svg>

				{/* Badge with count */}
				{count > 0 && (
					<span className="absolute -right-0.5 -top-0.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white shadow-sm">
						{count > 99 ? "99+" : count}
					</span>
				)}
			</button>

			{/* Dropdown */}
			{isOpen && (
				<div
					className="absolute right-0 top-full z-50 mt-2 w-80 overflow-hidden rounded-xl border border-gray-100 bg-white shadow-lg"
					role="menu"
				>
					<div className="border-b border-gray-100 px-4 py-3">
						<h3 className="font-semibold text-gray-900">Access Requests</h3>
						<p className="text-xs text-gray-500">
							{count > 0 ? `${count} pending request${count !== 1 ? "s" : ""}` : "No pending requests"}
						</p>
					</div>

					{count === 0 ? (
						<div className="px-4 py-8 text-center text-sm text-gray-400">
							No pending access requests
						</div>
					) : (
						<div className="max-h-80 overflow-y-auto">
							{pendingRequests.map((request) => (
								<div
									key={request.id}
									className="border-b border-gray-50 px-4 py-3 last:border-b-0 hover:bg-gray-50 cursor-pointer transition-colors"
									onClick={() => navigateToWorkflow(request.workflow_id)}
								>
									<div className="flex items-start gap-3">
										{/* User avatar */}
										<div
											className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-semibold"
											style={{ backgroundColor: "#ff6b00", color: "white", opacity: 0.9 }}
										>
											{request.requester_email?.charAt(0).toUpperCase() || "?"}
										</div>

										<div className="flex-1 min-w-0">
											<p className="text-sm font-medium text-gray-900 truncate">
												{request.requester_email || request.requester_id}
											</p>
											<p className="text-xs text-gray-500">
												Wants to edit <span className="font-medium text-gray-700">{request.workflow_name || "workflow"}</span>
											</p>
											{request.message && (
												<p className="mt-1 text-xs text-gray-400 italic truncate">
													"{request.message}"
												</p>
											)}
											<p className="mt-1 text-xs text-gray-400">
												{formatTimeAgo(request.created_at)}
											</p>

											{/* Action buttons */}
											<div className="mt-2 flex gap-2">
												<button
													onClick={(e) => handleApprove(request.id, e)}
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
													onClick={(e) => handleReject(request.id, e)}
													disabled={loadingId === request.id}
													className="flex items-center gap-1 rounded bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600 hover:bg-gray-200 disabled:opacity-50 transition-colors"
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

export default GlobalNotificationBell;
