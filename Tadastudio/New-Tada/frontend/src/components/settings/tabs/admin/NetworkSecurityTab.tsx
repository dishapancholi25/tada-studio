"use client";

import {
	AlertCircle,
	Globe,
	Info,
	Loader2,
	Plus,
	Power,
	PowerOff,
	Shield,
	Trash2,
	X,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { useEscapeKey, useFocusTrap } from "@/hooks/useAccessibility";
import Button from "@/components/ui/Button";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import { useToast } from "@/contexts/ToastContext";
import { ApiError, ssrfPolicyAPI, type SSRFPolicy } from "@/lib/admin-api";

// ─── Validation ───────────────────────────────────────────────────────────────

/**
 * Accepts an allow-list entry: a bare IP/hostname, host:port, host/path,
 * host:port/path, or a full URL. Matches the backend's parse_endpoint_entry.
 */
function isValidAllowListEntry(entry: string): boolean {
	const candidate = entry.trim();
	if (!candidate) return false;
	const withScheme = candidate.includes("://")
		? candidate
		: `http://${candidate}`;
	try {
		const url = new URL(withScheme);
		return !!url.hostname;
	} catch {
		return false;
	}
}

// ─── Types ────────────────────────────────────────────────────────────────────

interface CreatePolicyModalProps {
	open: boolean;
	onClose: () => void;
	onCreated: (policy: SSRFPolicy) => void;
	existingToolIds: string[];
}

interface AddIpModalProps {
	open: boolean;
	toolId: string;
	onClose: () => void;
	onAdded: (policy: SSRFPolicy) => void;
}

// ─── Create Policy Modal ──────────────────────────────────────────────────────

function CreatePolicyModal({
	open,
	onClose,
	onCreated,
	existingToolIds,
}: CreatePolicyModalProps) {
	const { showToast } = useToast();
	const [toolId, setToolId] = useState("");
	const [initialIps, setInitialIps] = useState("");
	const [saving, setSaving] = useState(false);
	const [errors, setErrors] = useState<{ toolId?: string; ips?: string }>({});
	const [mounted, setMounted] = useState(false);
	const dialogRef = useFocusTrap<HTMLDivElement>(open);

	useEffect(() => {
		setMounted(true);
		return () => setMounted(false);
	}, []);

	useEscapeKey(onClose, open);

	useEffect(() => {
		if (open) {
			document.body.style.overflow = "hidden";
			setToolId("");
			setInitialIps("");
			setErrors({});
		} else {
			document.body.style.overflow = "";
		}
		return () => {
			document.body.style.overflow = "";
		};
	}, [open]);

	const validate = (): boolean => {
		const newErrors: { toolId?: string; ips?: string } = {};
		const trimmedId = toolId.trim().toUpperCase();

		if (!trimmedId) {
			newErrors.toolId = "Tool ID is required";
		} else if (!/^[A-Z0-9_]+$/.test(trimmedId)) {
			newErrors.toolId =
				"Only uppercase letters, numbers, and underscores allowed";
		} else if (existingToolIds.includes(trimmedId)) {
			newErrors.toolId = `Policy for "${trimmedId}" already exists`;
		}

		// Validate IPs if provided
		const ipsText = initialIps.trim();
		if (ipsText) {
			const lines = ipsText
				.split(/[\n,]/)
				.map((l) => l.trim())
				.filter(Boolean);
			for (const line of lines) {
				if (!isValidAllowListEntry(line)) {
					newErrors.ips = `Invalid entry: "${line}"`;
					break;
				}
			}
		}

		setErrors(newErrors);
		return Object.keys(newErrors).length === 0;
	};

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		if (!validate()) return;

		const trimmedId = toolId.trim().toUpperCase();
		const ipsText = initialIps.trim();
		const ips = ipsText
			? ipsText
					.split(/[\n,]/)
					.map((l) => l.trim())
					.filter(Boolean)
			: [];

		try {
			setSaving(true);
			const created = await ssrfPolicyAPI.update(trimmedId, ips, true);
			onCreated(created);
			showToast("success", `Created network policy for ${trimmedId}`);
			onClose();
		} catch (err) {
			const msg =
				err instanceof ApiError
					? err.message
					: "Failed to create policy";
			showToast("error", msg);
		} finally {
			setSaving(false);
		}
	};

	if (!mounted || !open) return null;

	return createPortal(
		<div
			className="fixed inset-0 z-[9999] flex items-center justify-center p-4"
			onClick={onClose}
		>
			<div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
			<div
				ref={dialogRef}
				className="relative w-full max-w-lg animate-fadeIn rounded-[4px] border border-slate-200 bg-white shadow-[0_18px_50px_rgba(15,23,42,0.12)]"
				onClick={(e) => e.stopPropagation()}
			>
				{/* Header */}
				<div className="flex shrink-0 items-start justify-between border-b border-slate-200 px-6 pb-4 pt-5">
					<div className="flex items-center gap-3">
						<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[4px] border border-orange-200 bg-orange-100">
							<Shield className="h-5 w-5 text-orange-600" />
						</div>
						<div>
							<h2 className="text-lg font-semibold tracking-tight text-slate-900">
								Create Network Policy
							</h2>
							<p className="mt-0.5 text-sm text-slate-600">
								Allow outbound requests only to specific
								endpoints for a tool
							</p>
						</div>
					</div>
					<button
						type="button"
						onClick={onClose}
						className="rounded-[4px] p-2 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800"
					>
						<X className="h-5 w-5" />
					</button>
				</div>

				{/* Form */}
				<form onSubmit={handleSubmit}>
					<div className="space-y-4 px-6 py-5">
						{/* Tool ID */}
						<div>
							<label className="mb-1.5 block text-sm font-medium text-slate-900">
								Tool Identifier{" "}
								<span className="text-red-600">*</span>
							</label>
							<input
								type="text"
								value={toolId}
								onChange={(e) => {
									setToolId(e.target.value);
									if (errors.toolId)
										setErrors((prev) => ({
											...prev,
											toolId: undefined,
										}));
								}}
								placeholder="e.g. HTTP_REQUEST, MCP_SERVER"
								className={`w-full rounded-[4px] border bg-white px-3 py-2 text-sm text-slate-900 outline-none transition-colors placeholder:text-slate-400 hover:border-orange-400 focus:border-orange-500 focus:ring-2 focus:ring-orange-500/15 ${
									errors.toolId
										? "border-red-400 focus:border-red-500 focus:ring-red-500/20"
										: "border-slate-200"
								}`}
								autoFocus
							/>
							{errors.toolId && (
								<p className="mt-1 text-xs text-red-700">
									{errors.toolId}
								</p>
							)}
							<p className="mt-1 text-xs text-slate-500">
								Uppercase identifier for the tool (e.g.
								HTTP_REQUEST for the HTTP tool, or a custom MCP
								server name)
							</p>
						</div>

						{/* Initial IPs */}
						<div>
							<label className="mb-1.5 block text-sm font-medium text-slate-900">
								Allowed Endpoints
							</label>
							<textarea
								value={initialIps}
								onChange={(e) => {
									setInitialIps(e.target.value);
									if (errors.ips)
										setErrors((prev) => ({
											...prev,
											ips: undefined,
										}));
								}}
								placeholder="Enter endpoints, one per line or comma-separated&#10;e.g. 10.0.0.1, 10.0.0.1:5005/get, api.example.com"
								rows={4}
								className={`w-full rounded-[4px] border bg-white px-3 py-2 text-sm font-mono text-slate-900 outline-none transition-colors placeholder:text-slate-400 hover:border-orange-400 focus:border-orange-500 focus:ring-2 focus:ring-orange-500/15 ${
									errors.ips
										? "border-red-400 focus:border-red-500 focus:ring-red-500/20"
										: "border-slate-200"
								}`}
							/>
							{errors.ips && (
								<p className="mt-1 text-xs text-red-700">
									{errors.ips}
								</p>
							)}
							<p className="mt-1 text-xs text-slate-500">
								Optional — you can add entries later. Supports
								an IP, IP:port, IP/path, IP:port/path, a
								hostname, or a full URL.
							</p>
						</div>
					</div>

					{/* Footer */}
					<div className="flex items-center justify-end gap-3 border-t border-slate-200 px-6 py-4">
						<Button
							onClick={onClose}
							variant="secondary"
							className="!border-slate-200 !bg-white !text-slate-800 hover:!border-orange-500 hover:!text-orange-700"
						>
							Cancel
						</Button>
						<button
							type="submit"
							disabled={saving}
							className="inline-flex items-center gap-2 rounded-[4px] px-4 py-2 text-sm font-medium text-white transition-all disabled:opacity-50"
							style={{ background: "var(--color-primary)" }}
						>
							{saving && (
								<Loader2 className="h-4 w-4 animate-spin" />
							)}
							Create Policy
						</button>
					</div>
				</form>
			</div>
		</div>,
		document.body,
	);
}

// ─── Add IP Modal ─────────────────────────────────────────────────────────────

function AddIpModal({ open, toolId, onClose, onAdded }: AddIpModalProps) {
	const { showToast } = useToast();
	const [ip, setIp] = useState("");
	const [saving, setSaving] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [mounted, setMounted] = useState(false);
	const dialogRef = useFocusTrap<HTMLDivElement>(open);

	useEffect(() => {
		setMounted(true);
		return () => setMounted(false);
	}, []);

	useEscapeKey(onClose, open);

	useEffect(() => {
		if (open) {
			document.body.style.overflow = "hidden";
			setIp("");
			setError(null);
		} else {
			document.body.style.overflow = "";
		}
		return () => {
			document.body.style.overflow = "";
		};
	}, [open]);

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		const trimmed = ip.trim();
		if (!trimmed) {
			setError("IP or CIDR is required");
			return;
		}

		// Basic validation
		if (!isValidAllowListEntry(trimmed)) {
			setError("Invalid endpoint format");
			return;
		}

		try {
			setSaving(true);
			const updated = await ssrfPolicyAPI.addIp(toolId, trimmed);
			onAdded(updated);
			showToast("success", `Added ${trimmed} to ${toolId} allow list`);
			onClose();
		} catch (err) {
			const msg =
				err instanceof ApiError ? err.message : "Failed to add IP";
			setError(msg);
		} finally {
			setSaving(false);
		}
	};

	if (!mounted || !open) return null;

	return createPortal(
		<div
			className="fixed inset-0 z-[9999] flex items-center justify-center p-4"
			onClick={onClose}
		>
			<div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
			<div
				ref={dialogRef}
				className="relative w-full max-w-md animate-fadeIn rounded-[4px] border border-slate-200 bg-white shadow-[0_18px_50px_rgba(15,23,42,0.12)]"
				onClick={(e) => e.stopPropagation()}
			>
				{/* Header */}
				<div className="flex shrink-0 items-start justify-between border-b border-slate-200 px-6 pb-4 pt-5">
					<div className="flex items-center gap-3">
						<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[4px] border border-orange-200 bg-orange-100">
							<Plus className="h-5 w-5 text-orange-600" />
						</div>
						<div>
							<h2 className="text-lg font-semibold tracking-tight text-slate-900">
								Add Allowed Endpoint
							</h2>
							<p className="mt-0.5 text-sm text-slate-600">
								Add an allowed endpoint to{" "}
								<span className="font-mono font-medium">
									{toolId}
								</span>
							</p>
						</div>
					</div>
					<button
						type="button"
						onClick={onClose}
						className="rounded-[4px] p-2 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800"
					>
						<X className="h-5 w-5" />
					</button>
				</div>

				{/* Form */}
				<form onSubmit={handleSubmit}>
					<div className="px-6 py-5">
						{error && (
							<div className="mb-3 rounded-[4px] border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
								{error}
							</div>
						)}
						<label className="mb-1.5 block text-sm font-medium text-slate-900">
							Endpoint <span className="text-red-600">*</span>
						</label>
						<input
							type="text"
							value={ip}
							onChange={(e) => {
								setIp(e.target.value);
								if (error) setError(null);
							}}
							placeholder="e.g. 10.0.0.1, 10.0.0.1:5005/get, or www.example.com"
							className="w-full rounded-[4px] border border-slate-200 bg-white px-3 py-2 text-sm font-mono text-slate-900 outline-none transition-colors placeholder:text-slate-400 hover:border-orange-400 focus:border-orange-500 focus:ring-2 focus:ring-orange-500/15"
							autoFocus
						/>
						<p className="mt-1.5 text-xs text-slate-500">
							Supports an IP, IP:port, IP/path, IP:port/path, a
							hostname, or a full URL
						</p>
					</div>

					{/* Footer */}
					<div className="flex items-center justify-end gap-3 border-t border-slate-200 px-6 py-4">
						<Button
							onClick={onClose}
							variant="secondary"
							className="!border-slate-200 !bg-white !text-slate-800 hover:!border-orange-500 hover:!text-orange-700"
						>
							Cancel
						</Button>
						<button
							type="submit"
							disabled={saving}
							className="inline-flex items-center gap-2 rounded-[4px] px-4 py-2 text-sm font-medium text-white transition-all disabled:opacity-50"
							style={{ background: "var(--color-primary)" }}
						>
							{saving && (
								<Loader2 className="h-4 w-4 animate-spin" />
							)}
							Add IP
						</button>
					</div>
				</form>
			</div>
		</div>,
		document.body,
	);
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function NetworkSecurityTab() {
	const { showToast } = useToast();
	const [policies, setPolicies] = useState<SSRFPolicy[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	// Modal states
	const [showCreateModal, setShowCreateModal] = useState(false);
	const [addIpTarget, setAddIpTarget] = useState<string | null>(null);

	// Confirm dialog states
	const [confirmDelete, setConfirmDelete] = useState<{
		open: boolean;
		toolId: string;
		type: "policy" | "ip";
		ip?: string;
	}>({ open: false, toolId: "", type: "policy" });

	// Toggle in-progress
	const [togglingPolicy, setTogglingPolicy] = useState<string | null>(null);
	const [removingIp, setRemovingIp] = useState<string | null>(null);

	const loadPolicies = useCallback(async () => {
		try {
			setLoading(true);
			setError(null);
			const data = await ssrfPolicyAPI.list();
			setPolicies(data);
		} catch (err) {
			const msg =
				err instanceof ApiError
					? err.message
					: "Failed to load network security policies";
			setError(msg);
		} finally {
			setLoading(false);
		}
	}, []);

	useEffect(() => {
		loadPolicies();
	}, [loadPolicies]);

	const handlePolicyCreated = (policy: SSRFPolicy) => {
		setPolicies((prev) => [...prev, policy]);
	};

	const handleIpAdded = (updatedPolicy: SSRFPolicy) => {
		setPolicies((prev) =>
			prev.map((p) =>
				p.tool_id === updatedPolicy.tool_id ? updatedPolicy : p,
			),
		);
	};

	const handleTogglePolicy = async (policy: SSRFPolicy) => {
		try {
			setTogglingPolicy(policy.tool_id);
			const updated = await ssrfPolicyAPI.update(
				policy.tool_id,
				policy.allowed_ip_ranges,
				!policy.enabled,
			);
			setPolicies((prev) =>
				prev.map((p) =>
					p.tool_id === policy.tool_id ? updated : p,
				),
			);
			showToast(
				"success",
				`${policy.tool_id} policy ${updated.enabled ? "enabled" : "disabled"}`,
			);
		} catch (err) {
			const msg =
				err instanceof ApiError
					? err.message
					: "Failed to toggle policy";
			showToast("error", msg);
		} finally {
			setTogglingPolicy(null);
		}
	};

	const handleConfirmAction = async () => {
		const { toolId, type, ip } = confirmDelete;

		if (type === "policy") {
			try {
				await ssrfPolicyAPI.delete(toolId);
				setPolicies((prev) =>
					prev.filter((p) => p.tool_id !== toolId),
				);
				showToast("success", `Deleted policy for ${toolId}`);
			} catch (err) {
				const msg =
					err instanceof ApiError
						? err.message
						: "Failed to delete policy";
				showToast("error", msg);
			}
		} else if (type === "ip" && ip) {
			try {
				setRemovingIp(`${toolId}:${ip}`);
				const updated = await ssrfPolicyAPI.removeIp(toolId, ip);
				setPolicies((prev) =>
					prev.map((p) =>
						p.tool_id === toolId ? updated : p,
					),
				);
				showToast("success", `Removed ${ip} from ${toolId}`);
			} catch (err) {
				const msg =
					err instanceof ApiError
						? err.message
						: "Failed to remove IP";
				showToast("error", msg);
			} finally {
				setRemovingIp(null);
			}
		}
	};

	// ─── Loading State ────────────────────────────────────────────────────────

	if (loading) {
		return (
			<div className="flex items-center justify-center h-64">
				<div className="text-center">
					<Loader2
						className="animate-spin h-10 w-10 mx-auto mb-3"
						style={{ color: "var(--color-primary)" }}
					/>
					<p
						className="text-sm"
						style={{ color: "var(--color-text-muted)" }}
					>
						Loading network security policies...
					</p>
				</div>
			</div>
		);
	}

	// ─── Error State ──────────────────────────────────────────────────────────

	if (error) {
		return (
			<div className="flex items-center justify-center h-64">
				<div className="text-center max-w-md">
					<AlertCircle
						className="h-12 w-12 mx-auto mb-4"
						style={{ color: "var(--color-error)" }}
					/>
					<h3
						className="text-lg font-semibold mb-2"
						style={{ color: "var(--color-text-primary)" }}
					>
						Failed to Load Policies
					</h3>
					<p
						className="text-sm mb-4"
						style={{ color: "var(--color-text-secondary)" }}
					>
						{error}
					</p>
					<button
						onClick={loadPolicies}
						className="px-4 py-2 rounded-lg transition-colors"
						style={{
							background: "var(--color-primary)",
							color: "white",
						}}
					>
						Try Again
					</button>
				</div>
			</div>
		);
	}

	// ─── Main Render ──────────────────────────────────────────────────────────

	return (
		<div className="space-y-6 p-6">
			{/* Header */}
			<div
				className="flex items-start gap-4 pb-6 border-b"
				style={{ borderColor: "var(--color-border)" }}
			>
				<div
					className="p-3 rounded-lg"
					style={{
						background: "rgba(var(--color-primary-rgb), 0.1)",
					}}
				>
					<Shield
						className="h-6 w-6"
						style={{ color: "var(--color-primary)" }}
					/>
				</div>
				<div className="flex-1">
					<h2
						className="text-xl font-semibold mb-2"
						style={{ color: "var(--color-text-primary)" }}
					>
						Network Security
					</h2>
					<p
						className="text-sm"
						style={{ color: "var(--color-text-secondary)" }}
					>
					Manage allowed endpoints per tool. Outbound requests to
					addresses not explicitly allowed are denied to prevent SSRF
					attacks.
					</p>
				</div>
				{/* <button
					onClick={() => setShowCreateModal(true)}
					className="flex items-center gap-2 px-4 py-2 rounded-[4px] text-sm font-medium transition-colors hover:opacity-90"
					style={{
						background: "var(--color-primary)",
						color: "white",
					}}
				>
					<Plus className="h-4 w-4" />
					Add Policy
				</button> */}
			</div>

			{/* Info Banner */}
			<div
				className="flex items-start gap-3 rounded-lg px-4 py-3"
				style={{
					background: "rgba(var(--color-primary-rgb), 0.05)",
					border: "1px solid var(--color-border)",
				}}
			>
				<Info
					className="h-4 w-4 flex-shrink-0 mt-0.5"
					style={{ color: "var(--color-primary)" }}
				/>
				<div
					className="text-xs leading-relaxed"
					style={{ color: "var(--color-text-secondary)" }}
				>
					Each policy defines allowed endpoints for a specific tool.
					When a tool makes an outbound request, the destination is
					checked against its allow-list. Policies can be toggled
					on/off without deleting configured entries.
				</div>
			</div>

			{/* Policies List */}
			{policies.length === 0 ? (
				<div
					className="text-center py-16 rounded-lg"
					style={{
						background: "var(--color-bg-secondary)",
						border: "1px solid var(--color-border)",
					}}
				>
					<Globe
						className="h-12 w-12 mx-auto mb-3"
						style={{ color: "var(--color-text-muted)" }}
					/>
					<p
						className="text-sm font-medium"
						style={{ color: "var(--color-text-secondary)" }}
					>
						No network security policies configured
					</p>
					<p
						className="text-xs mt-1 mb-4"
						style={{ color: "var(--color-text-muted)" }}
					>
						Create a policy to restrict outbound tool requests to
						specific IP ranges.
					</p>
					<button
						onClick={() => setShowCreateModal(true)}
						className="inline-flex items-center gap-2 px-4 py-2 rounded-[4px] text-sm font-medium transition-colors"
						style={{
							background: "var(--color-primary)",
							color: "white",
						}}
					>
						<Plus className="h-4 w-4" />
						Create First Policy
					</button>
				</div>
			) : (
				<div className="space-y-4">
					{policies.map((policy) => (
						<div
							key={policy.tool_id}
							className="rounded-lg overflow-hidden transition-opacity"
							style={{
								background: "var(--color-bg-secondary)",
								border: `1px solid ${policy.enabled ? "var(--color-border)" : "var(--color-border)"}`,
								opacity: policy.enabled ? 1 : 0.6,
							}}
						>
							{/* Policy Header */}
							<div
								className="flex items-center justify-between px-5 py-4"
								style={{
									borderBottom:
										policy.allowed_ip_ranges.length > 0
											? "1px solid var(--color-border)"
											: "none",
								}}
							>
								<div className="flex items-center gap-3">
									<div
										className="p-2 rounded-lg"
										style={{
											background: policy.enabled
												? "rgba(76, 175, 80, 0.1)"
												: "rgba(158, 158, 158, 0.1)",
										}}
									>
										<Shield
											className="h-5 w-5"
											style={{
												color: policy.enabled
													? "#4CAF50"
													: "#9E9E9E",
											}}
										/>
									</div>
									<div>
										<h4
											className="font-semibold text-sm"
											style={{
												color: "var(--color-text-primary)",
											}}
										>
											{policy.tool_id}
										</h4>
										<div className="flex items-center gap-2 mt-0.5">
											<span
												className="text-xs"
												style={{
													color: "var(--color-text-muted)",
												}}
											>
												{
													policy.allowed_ip_ranges
														.length
												}{" "}
												allowed endpoint
												{policy.allowed_ip_ranges
													.length !== 1
													? "s"
													: ""}
											</span>
											<span
												className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium uppercase tracking-wide ${
													policy.enabled
														? "text-green-700 bg-green-100"
														: "text-slate-500 bg-slate-100"
												}`}
											>
												{policy.enabled
													? "Active"
													: "Disabled"}
											</span>
										</div>
									</div>
								</div>
								<div className="flex items-center gap-1">
									{/* <button
										onClick={() =>
											handleTogglePolicy(policy)
										}
										disabled={
											togglingPolicy === policy.tool_id
										}
										className="p-2 rounded-lg transition-colors hover:bg-black/5 disabled:opacity-50"
										title={
											policy.enabled
												? "Disable policy"
												: "Enable policy"
										}
									>
										{togglingPolicy === policy.tool_id ? (
											<Loader2 className="h-4 w-4 animate-spin text-slate-400" />
										) : policy.enabled ? (
											<Power
												className="h-4 w-4"
												style={{ color: "#4CAF50" }}
											/>
										) : (
											<PowerOff
												className="h-4 w-4"
												style={{ color: "#9E9E9E" }}
											/>
										)}
									</button> */}
									<button
										onClick={() =>
											setAddIpTarget(policy.tool_id)
										}
										className="p-2 rounded-lg transition-colors hover:bg-black/5"
										title="Add allowed endpoint"
									>
										<Plus
											className="h-4 w-4"
											style={{
												color: "var(--color-primary)",
											}}
										/>
									</button>
									{/* <button
										onClick={() =>
											setConfirmDelete({
												open: true,
												toolId: policy.tool_id,
												type: "policy",
											})
										}
										className="p-2 rounded-lg transition-colors hover:bg-red-50"
										title="Delete policy"
									>
										<Trash2 className="h-4 w-4 text-red-500" />
									</button> */}
								</div>
							</div>

							{/* IP Ranges */}
							{policy.allowed_ip_ranges.length > 0 && (
								<div className="px-5 py-3">
									<div className="flex flex-wrap gap-2">
										{policy.allowed_ip_ranges.map((ip) => (
											<span
												key={ip}
												className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-[4px] text-xs font-mono transition-opacity ${
													removingIp ===
													`${policy.tool_id}:${ip}`
														? "opacity-40"
														: ""
												}`}
												style={{
													background:
														"var(--color-bg-primary)",
													color: "var(--color-text-primary)",
													border: "1px solid var(--color-border)",
												}}
											>
												{ip}
												{!policy.fixed_ips.includes(ip) && (
													<button
														type="button"
														onClick={() =>
															setConfirmDelete({
																open: true,
																toolId: policy.tool_id,
																type: "ip",
																ip,
															})
														}
														className="-mr-1 ml-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded text-slate-400 transition-colors hover:bg-red-100 hover:text-red-600"
														title={`Remove ${ip}`}
														aria-label={`Remove ${ip}`}
													>
														<Trash2 className="pointer-events-none h-3.5 w-3.5" />
													</button>
												)}
											</span>
										))}
									</div>
								</div>
							)}
						</div>
					))}
				</div>
			)}

			{/* ─── Modals ──────────────────────────────────────────────────── */}

			<CreatePolicyModal
				open={showCreateModal}
				onClose={() => setShowCreateModal(false)}
				onCreated={handlePolicyCreated}
				existingToolIds={policies.map((p) => p.tool_id)}
			/>

			<AddIpModal
				open={!!addIpTarget}
				toolId={addIpTarget || ""}
				onClose={() => setAddIpTarget(null)}
				onAdded={handleIpAdded}
			/>

			<ConfirmDialog
				isOpen={confirmDelete.open}
				onClose={() =>
					setConfirmDelete((prev) => ({ ...prev, open: false }))
				}
				onConfirm={handleConfirmAction}
				title={
					confirmDelete.type === "policy"
						? "Delete Network Policy"
						: "Remove Allowed Endpoint"
				}
				message={
					confirmDelete.type === "policy"
						? `Are you sure you want to delete the network security policy for "${confirmDelete.toolId}"? This will remove all allowed endpoints and disable SSRF protection for this tool.`
						: `Are you sure you want to remove "${confirmDelete.ip}" from the ${confirmDelete.toolId} allow list? Requests to this endpoint will no longer be permitted.`
				}
				confirmText={
					confirmDelete.type === "policy"
						? "Delete Policy"
						: "Remove IP"
				}
				variant="danger"
				surface="light"
			/>
		</div>
	);
}
