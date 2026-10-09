"use client";

import { useEffect, useState } from "react";
import { Plus, RotateCcw, UserX } from "lucide-react";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import { useToast } from "@/contexts/ToastContext";

interface LocalUser {
	id: string;
	email: string;
	is_active: boolean;
	created_at: string | null;
}

async function apiRequest(path: string, options?: RequestInit) {
	const res = await fetch(path, {
		...options,
		credentials: "include",
		headers: {
			"Content-Type": "application/json",
			...(options?.headers ?? {}),
		},
	});
	if (!res.ok) {
		const data = await res.json().catch(() => ({}));
		throw new Error(data.detail ?? `Request failed (${res.status})`);
	}
	return res.json();
}

export default function LocalUsersTab() {
	const { showToast } = useToast();
	const [users, setUsers] = useState<LocalUser[]>([]);
	const [loading, setLoading] = useState(true);

	// Create form
	const [newEmail, setNewEmail] = useState("");
	const [newPassword, setNewPassword] = useState("");
	const [creating, setCreating] = useState(false);

	// Reset password form (keyed by user id)
	const [resetUserId, setResetUserId] = useState<string | null>(null);
	const [resetPassword, setResetPassword] = useState("");
	const [resetting, setResetting] = useState(false);
	const [pendingDeactivateUser, setPendingDeactivateUser] =
		useState<LocalUser | null>(null);

	const loadUsers = async () => {
		try {
			const data = await apiRequest("/api/auth/local/users");
			setUsers(data.users ?? []);
		} catch (err) {
			showToast("error", String(err));
		} finally {
			setLoading(false);
		}
	};

	useEffect(() => {
		void loadUsers();
	}, []); // eslint-disable-line react-hooks/exhaustive-deps

	const handleCreate = async (e: React.FormEvent) => {
		e.preventDefault();
		setCreating(true);
		try {
			await apiRequest("/api/auth/local/users", {
				method: "POST",
				body: JSON.stringify({ email: newEmail, password: newPassword }),
			});
			showToast("success", `User ${newEmail} created.`);
			setNewEmail("");
			setNewPassword("");
			await loadUsers();
		} catch (err) {
			showToast("error", String(err));
		} finally {
			setCreating(false);
		}
	};

	const handleDeactivate = (user: LocalUser) => {
		setPendingDeactivateUser(user);
	};

	const handleConfirmDeactivate = async () => {
		if (!pendingDeactivateUser) return;
		const user = pendingDeactivateUser;
		try {
			await apiRequest(`/api/auth/local/users/${user.id}`, {
				method: "DELETE",
			});
			showToast("success", `${user.email} deactivated.`);
			await loadUsers();
		} catch (err) {
			showToast("error", String(err));
		} finally {
			setPendingDeactivateUser(null);
		}
	};

	const handleResetPassword = async (e: React.FormEvent) => {
		e.preventDefault();
		if (!resetUserId) return;
		setResetting(true);
		try {
			await apiRequest(
				`/api/auth/local/users/${resetUserId}/reset-password`,
				{
					method: "PUT",
					body: JSON.stringify({ new_password: resetPassword }),
				},
			);
			showToast("success", "Password updated.");
			setResetUserId(null);
			setResetPassword("");
		} catch (err) {
			showToast("error", String(err));
		} finally {
			setResetting(false);
		}
	};

	if (loading) {
		return (
			<div className="flex items-center justify-center p-12">
				<div className="animate-pulse text-[color:var(--color-text-muted)]">
					Loading local users...
				</div>
			</div>
		);
	}

	return (
		<div className="max-w-2xl space-y-8 p-6">
			{/* Create user form */}
			<div>
				<h3
					className="mb-4 text-lg font-semibold"
					style={{ color: "var(--color-text-primary)" }}
				>
					Create Local User
				</h3>
				<form onSubmit={handleCreate} className="flex items-end gap-3">
					<div className="flex-1">
						<label
							htmlFor="new-email"
							className="mb-1 block text-xs"
							style={{ color: "var(--color-text-secondary)" }}
						>
							Email
						</label>
						<input
							id="new-email"
							type="email"
							required
							value={newEmail}
							onChange={(e) => setNewEmail(e.target.value)}
							className="w-full rounded-lg border px-3 py-2 text-sm outline-none"
							style={{
								background: "var(--color-bg-secondary)",
								borderColor: "var(--color-border)",
								color: "var(--color-text-primary)",
							}}
						/>
					</div>
					<div className="flex-1">
						<label
							htmlFor="new-password"
							className="mb-1 block text-xs"
							style={{ color: "var(--color-text-secondary)" }}
						>
							Password
						</label>
						<input
							id="new-password"
							type="password"
							required
							minLength={6}
							value={newPassword}
							onChange={(e) => setNewPassword(e.target.value)}
							className="w-full rounded-lg border px-3 py-2 text-sm outline-none"
							style={{
								background: "var(--color-bg-secondary)",
								borderColor: "var(--color-border)",
								color: "var(--color-text-primary)",
							}}
						/>
					</div>
					<button
						type="submit"
						disabled={creating}
						className="flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50"
						style={{
							background: "rgba(var(--color-primary-rgb), 0.15)",
							color: "var(--color-primary-light)",
							border: "1px solid rgba(var(--color-primary-rgb), 0.3)",
						}}
					>
						<Plus className="h-4 w-4" />
						{creating ? "Creating..." : "Create"}
					</button>
				</form>
			</div>

			{/* User list */}
			<div>
				<h3
					className="mb-4 text-lg font-semibold"
					style={{ color: "var(--color-text-primary)" }}
				>
					Local Users ({users.length})
				</h3>
				{users.length === 0 ? (
					<p
						className="text-sm"
						style={{ color: "var(--color-text-muted)" }}
					>
						No local users yet.
					</p>
				) : (
					<div className="space-y-2">
						{users.map((u) => (
							<div
								key={u.id}
								className="flex items-center justify-between rounded-lg border px-4 py-3"
								style={{
									background: "var(--color-bg-secondary)",
									borderColor: "var(--color-border)",
								}}
							>
								<div>
									<span
										className="text-sm font-medium"
										style={{
											color: u.is_active
												? "var(--color-text-primary)"
												: "var(--color-text-muted)",
										}}
									>
										{u.email}
									</span>
									{!u.is_active && (
										<span className="ml-2 rounded bg-red-500/20 px-2 py-0.5 text-xs text-red-400">
											Deactivated
										</span>
									)}
								</div>
								<div className="flex items-center gap-2">
									{/* Reset password toggle */}
									{u.is_active && (
										<button
											type="button"
											onClick={() =>
												setResetUserId(
													resetUserId === u.id ? null : u.id,
												)
											}
											className="rounded p-1.5 transition-colors hover:bg-slate-100"
											title="Reset password"
										>
											<RotateCcw
												className="h-4 w-4"
												style={{
													color: "var(--color-text-secondary)",
												}}
											/>
										</button>
									)}
									{u.is_active && (
										<button
											type="button"
											onClick={() => handleDeactivate(u)}
											className="rounded p-1.5 transition-colors hover:bg-red-500/20"
											title="Deactivate"
										>
											<UserX className="h-4 w-4 text-red-400" />
										</button>
									)}
								</div>
							</div>
						))}

						{/* Inline reset password form */}
						{resetUserId && (
							<form
								onSubmit={handleResetPassword}
								className="flex items-end gap-3 rounded-lg border px-4 py-3"
								style={{
									background:
										"rgba(var(--color-primary-rgb), 0.05)",
									borderColor:
										"rgba(var(--color-primary-rgb), 0.2)",
								}}
							>
								<div className="flex-1">
									<label
										htmlFor="reset-password"
										className="mb-1 block text-xs"
										style={{
											color: "var(--color-text-secondary)",
										}}
									>
										New password for{" "}
										{users.find((u) => u.id === resetUserId)
											?.email ?? "user"}
									</label>
									<input
										id="reset-password"
										type="password"
										required
										minLength={6}
										value={resetPassword}
										onChange={(e) =>
											setResetPassword(e.target.value)
										}
										className="w-full rounded-lg border px-3 py-2 text-sm outline-none"
										style={{
											background:
												"var(--color-bg-secondary)",
											borderColor: "var(--color-border)",
											color: "var(--color-text-primary)",
										}}
									/>
								</div>
								<button
									type="submit"
									disabled={resetting}
									className="rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50"
									style={{
										background:
											"rgba(var(--color-primary-rgb), 0.15)",
										color: "var(--color-primary-light)",
										border: "1px solid rgba(var(--color-primary-rgb), 0.3)",
									}}
								>
									{resetting ? "Saving..." : "Save"}
								</button>
								<button
									type="button"
									onClick={() => {
										setResetUserId(null);
										setResetPassword("");
									}}
									className="rounded-lg px-4 py-2 text-sm transition-colors"
									style={{
										color: "var(--color-text-secondary)",
										border: "1px solid var(--color-border)",
									}}
								>
									Cancel
								</button>
							</form>
						)}
					</div>
				)}
			</div>
			<ConfirmDialog
				isOpen={pendingDeactivateUser !== null}
				onClose={() => setPendingDeactivateUser(null)}
				onConfirm={handleConfirmDeactivate}
				title="Deactivate User"
				message={
					pendingDeactivateUser
						? `Deactivate ${pendingDeactivateUser.email}?`
						: ""
				}
				confirmText="Deactivate"
				cancelText="Cancel"
				variant="danger"
				surface="light"
			/>
		</div>
	);
}
