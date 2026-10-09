"use client";

import {
	Activity,
	AlertTriangle,
	Calendar,
	CheckCircle,
	Copy,
	Eye,
	EyeOff,
	Key,
	Pencil,
	Plus,
	Shield,
	Trash2,
	X,
} from "lucide-react";
import { api } from "@/lib/api";
import { useCallback, useEffect, useState } from "react";
import Button from "@/components/ui/Button";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import { useToast } from "@/contexts/ToastContext";
import {
	type AvailableScopesResponse,
	type CreateTokenRequest,
	type ScopeDefinition,
	type UserAPIToken,
	userAPITokenService,
} from "@/lib/user-api-token";

export default function APITokensTab() {
	const [tokens, setTokens] = useState<UserAPIToken[]>([]);
	const [loading, setLoading] = useState(true);
	const [showCreateModal, setShowCreateModal] = useState(false);
	const [createdToken, setCreatedToken] = useState<string | null>(null);
	const [createdTokenData, setCreatedTokenData] = useState<any>(null);
	const [editScopesToken, setEditScopesToken] = useState<UserAPIToken | null>(null);
	const [pendingRevokeToken, setPendingRevokeToken] = useState<{
		id: string;
		name: string;
	} | null>(null);
	const { showToast } = useToast();

	// Load tokens on mount
	useEffect(() => {
		void loadTokens();
	}, []);

	const loadTokens = async () => {
		try {
			setLoading(true);
			const response = await userAPITokenService.listTokens();
			console.log("Tokens response:", response);

			if (response && Array.isArray(response.tokens)) {
				setTokens(response.tokens);
			} else {
				console.warn("Invalid response format:", response);
				setTokens([]);
			}
		} catch (error) {
			console.error("Failed to load tokens:", error);
			showToast(
				"error",
				`Failed to load API tokens: ${error instanceof Error ? error.message : "Unknown error"}`,
			);
			setTokens([]); // Set empty array on error
		} finally {
			setLoading(false);
		}
	};

	const handleCopyToken = async (token: string) => {
		try {
			await navigator.clipboard.writeText(token);
			showToast("success", "Token copied to clipboard");
		} catch (error) {
			console.error("Failed to copy token:", error);
			showToast("error", "Failed to copy token to clipboard");
		}
	};

	const handleRevokeToken = (tokenId: string, tokenName: string) => {
		setPendingRevokeToken({ id: tokenId, name: tokenName });
	};

	const handleConfirmRevokeToken = async () => {
		if (!pendingRevokeToken) return;
		const token = pendingRevokeToken;
		try {
			await userAPITokenService.revokeToken(token.id);
			showToast("success", `Token "${token.name}" revoked successfully`);
			await loadTokens();
		} catch (error) {
			console.error("Failed to revoke token:", error);
			showToast("error", "Failed to revoke token");
		} finally {
			setPendingRevokeToken(null);
		}
	};

	const formatDate = (dateString?: string) => {
		if (!dateString) return "Never";
		return new Date(dateString).toLocaleDateString("en-US", {
			year: "numeric",
			month: "short",
			day: "numeric",
			hour: "2-digit",
			minute: "2-digit",
		});
	};

	const isExpired = (expiresAt?: string) => {
		if (!expiresAt) return false;
		return new Date(expiresAt) < new Date();
	};

	const getExpiryStatus = (token: UserAPIToken) => {
		if (!token.expires_at) {
			return {
				text: "Never expires",
				color: "text-[#0DA931]",
				icon: CheckCircle,
			};
		}

		if (isExpired(token.expires_at)) {
			return { text: "Expired", color: "text-red-600", icon: AlertTriangle };
		}

		const daysUntilExpiry = Math.ceil(
			(new Date(token.expires_at).getTime() - new Date().getTime()) /
				(1000 * 60 * 60 * 24),
		);

		if (daysUntilExpiry <= 7) {
			return {
				text: `Expires in ${daysUntilExpiry} days`,
				color: "text-amber-700",
				icon: AlertTriangle,
			};
		}

		return {
			text: `Expires on ${formatDate(token.expires_at)}`,
			color: "text-slate-700",
			icon: Calendar,
		};
	};

	return (
		<div className="p-6">
			<div className="mx-auto max-w-screen-2xl">
				{/* Header */}
				<div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
					<div className="flex items-start gap-3">
						<div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[4px] border border-orange-200 bg-orange-100">
							<Key className="h-5 w-5 text-orange-600" />
						</div>
						<div>
							<h3 className="mb-1 text-xl font-semibold tracking-tight text-slate-900">
								Personal Access Tokens
							</h3>
							<p className="text-sm text-slate-600">
								Tokens you have generated to access workflows via HTTP execution API
							</p>
						</div>
					</div>
					<Button
						onClick={() => setShowCreateModal(true)}
						icon={<Plus className="h-4 w-4" />}
						className="shadow-[0_8px_20px_rgba(15,23,42,0.12)]"
					>
						Create New Token
					</Button>
				</div>

				{/* Info Banner */}
				<div className="mb-6 flex items-start gap-3 rounded-[4px] border border-slate-200 bg-white p-4 shadow-[0_18px_50px_rgba(15,23,42,0.06)] transition-colors hover:border-orange-400">
					<Shield className="mt-0.5 h-5 w-5 shrink-0 text-orange-600" />
					<div className="text-sm text-slate-700">
						<p className="mb-1 font-medium text-slate-900">About Personal Access Tokens</p>
						<p className="text-slate-600">
							Personal Access Tokens (PATs) allow you to authenticate HTTP execution requests with your
							own credentials. These tokens inherit your workflow permissions and can be scoped to
							specific workflows.
						</p>
					</div>
				</div>

				{/* Tokens List */}
				{loading ? (
					<div className="flex h-64 items-center justify-center">
						<div className="animate-pulse text-slate-600">Loading tokens...</div>
					</div>
				) : tokens.length === 0 ? (
					<div className="rounded-[4px] border border-slate-200 bg-white py-12 text-center shadow-[0_18px_50px_rgba(15,23,42,0.06)] transition-colors hover:border-orange-400">
						<Key className="mx-auto mb-4 h-12 w-12 text-slate-400" />
						<h4 className="mb-2 text-lg font-medium text-slate-900">No tokens yet</h4>
						<p className="mb-4 text-slate-600">Create your first token to start using the HTTP execution API</p>
						<Button
							onClick={() => setShowCreateModal(true)}
							className="shadow-[0_8px_20px_rgba(15,23,42,0.12)]"
						>
							Create Your First Token
						</Button>
					</div>
				) : (
					<div className="space-y-4">
						{tokens.map((token) => {
							const expiryStatus = getExpiryStatus(token);
							const ExpiryIcon = expiryStatus.icon;

							return (
								<div
									key={token.id}
									className={`rounded-[4px] border border-slate-200 bg-white p-5 shadow-[0_18px_50px_rgba(15,23,42,0.06)] transition-all hover:border-orange-400 ${
										token.is_active && !isExpired(token.expires_at) ? "" : "opacity-70"
									}`}
								>
									<div className="flex items-start justify-between">
										<div className="flex-1">
											{/* Token Name & Prefix */}
											<div className="mb-3 flex items-center gap-3">
												<div className="flex rounded-[4px] border border-orange-200 bg-orange-100 p-2">
													<Key className="h-5 w-5 text-orange-600" />
												</div>
												<div>
													<h4 className="text-lg font-semibold text-slate-900">{token.name}</h4>
													<code className="font-mono text-sm text-slate-500">
														{token.prefix}••••••••••••
													</code>
												</div>
											</div>

											{/* Description */}
											{token.description && (
												<p className="mb-3 text-sm text-slate-600">{token.description}</p>
											)}

											{/* Token Info Grid */}
											<div className="mb-3 grid grid-cols-2 gap-4 lg:grid-cols-4">
												{/* Created */}
												<div>
													<div className="mb-1 text-xs font-medium text-slate-500">Created</div>
													<div className="text-sm text-slate-900">{formatDate(token.created_at)}</div>
												</div>

												{/* Expiry */}
												<div>
													<div className="mb-1 text-xs font-medium text-slate-500">Expiry</div>
													<div
														className={`flex items-start gap-1 text-sm ${expiryStatus.color}`}
													>
														<ExpiryIcon className="mt-0.5 h-3.5 w-3.5 shrink-0" />
														{expiryStatus.text}
													</div>
												</div>

												{/* Last Used */}
												<div>
													<div className="mb-1 text-xs font-medium text-slate-500">Last Used</div>
													<div className="text-sm text-slate-900">{formatDate(token.last_used_at)}</div>
												</div>

												{/* Usage Count */}
												<div>
													<div className="mb-1 text-xs font-medium text-slate-500">Total Uses</div>
													<div className="flex items-center gap-1 text-sm text-slate-900">
														<Activity className="h-3.5 w-3.5 text-slate-500" />
														{token.usage_count.toLocaleString()}
													</div>
												</div>
											</div>

											{/* Scopes */}
											<div className="flex flex-wrap gap-2">
												{token.scopes.map((scope, idx) => (
													<span
														key={idx}
														className="rounded-[4px] border border-slate-200 bg-slate-50 px-2 py-1 text-xs font-medium text-slate-800"
													>
														{scope}
													</span>
												))}
											</div>
										</div>

										{/* Actions */}
										<div className="ml-4 flex items-center gap-1">
											<button
												onClick={() => setEditScopesToken(token)}
												className="rounded-[4px] p-2 text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-900 disabled:opacity-40"
												title="Edit scopes"
												type="button"
												disabled={!token.is_active || isExpired(token.expires_at)}
											>
												<Pencil className="h-4 w-4" />
											</button>
											<button
												onClick={() => handleRevokeToken(token.id, token.name)}
												className="rounded-[4px] p-2 text-red-600 transition-colors hover:bg-red-50 hover:text-red-700 disabled:opacity-40"
												title="Revoke token"
												type="button"
												disabled={!token.is_active}
											>
												<Trash2 className="h-4 w-4" />
											</button>
										</div>
									</div>

									{/* Status Badge */}
									{!token.is_active && (
										<div className="mt-3 border-t border-slate-200 pt-3">
											<span className="rounded-[4px] border border-red-200 bg-red-50 px-2 py-1 text-xs font-medium text-red-700">
												Revoked
											</span>
										</div>
									)}
								</div>
							);
						})}
					</div>
				)}

				{/* Create Token Modal */}
				{showCreateModal && (
					<CreateTokenModal
						onClose={() => {
							setShowCreateModal(false);
							setCreatedToken(null);
							setCreatedTokenData(null);
						}}
						onTokenCreated={(token, tokenData) => {
							setCreatedToken(token);
							setCreatedTokenData(tokenData);
							setShowCreateModal(false); // close create modal
							void loadTokens();
						}}
					/>
				)}

				{/* Token Created Success Modal */}
				{createdToken && (
					<TokenCreatedModal
						token={createdToken}
						tokenData={createdTokenData}
						onClose={() => {
							setCreatedToken(null);
							setCreatedTokenData(null);
							setShowCreateModal(false);
						}}
					/>
				)}

				{/* Edit Scopes Modal */}
				{editScopesToken && (
					<EditScopesModal
						token={editScopesToken}
						onClose={() => setEditScopesToken(null)}
						onSaved={() => {
							void loadTokens();
						}}
					/>
				)}
				<ConfirmDialog
					isOpen={pendingRevokeToken !== null}
					onClose={() => setPendingRevokeToken(null)}
					onConfirm={handleConfirmRevokeToken}
					title="Revoke Token"
					message={
						pendingRevokeToken
							? `Are you sure you want to revoke the token "${pendingRevokeToken.name}"? This action cannot be undone.`
							: ""
					}
					confirmText="Revoke"
					cancelText="Cancel"
					variant="danger"
					surface="light"
				/>
			</div>
		</div>
	);
}

// Create Token Modal Component
function CreateTokenModal({
	onClose,
	onTokenCreated,
}: {
	onClose: () => void;
	onTokenCreated: (token: string, tokenData: any) => void;
}) {
	const [tokenName, setTokenName] = useState("");
	const [description, setDescription] = useState("");
	const [selectedScopes, setSelectedScopes] = useState<string[]>(["workflow:*:execute"]);
	const [availableScopes, setAvailableScopes] = useState<AvailableScopesResponse | null>(null);
	const [loadingScopes, setLoadingScopes] = useState(true);
	const [selectedWorkflows, setSelectedWorkflows] = useState<string[]>([]);
	const [workflows, setWorkflows] = useState<{ graph_name: string }[]>([]);
	const [loadingWorkflows, setLoadingWorkflows] = useState(false);
	const [showNamedWorkflows, setShowNamedWorkflows] = useState(false);
	const [expiresInDays, setExpiresInDays] = useState<number | null>(90);
	const [creating, setCreating] = useState(false);
	const { showToast } = useToast();

	useEffect(() => {
		const load = async () => {
			try {
				const resp = await userAPITokenService.getAvailableScopes();
				setAvailableScopes(resp);
			} catch (err) {
				console.error("Failed to load available scopes:", err);
			} finally {
				setLoadingScopes(false);
			}
		};
		void load();
	}, []);

	const loadWorkflows = useCallback(async () => {
		setLoadingWorkflows(true);
		try {
			const response = await api.getPublishedWorkflows();
			setWorkflows(response.published_workflows || []);
		} catch (error) {
			console.error("Failed to load workflows:", error);
			showToast("error", "Failed to load published workflows");
		} finally {
			setLoadingWorkflows(false);
		}
	}, [showToast]);

	const toggleScope = (scope: string) => {
		setSelectedScopes((prev) =>
			prev.includes(scope) ? prev.filter((s) => s !== scope) : [...prev, scope],
		);
	};

	const buildFinalScopes = (): string[] => {
		const scopes = [...selectedScopes];
		if (showNamedWorkflows && selectedWorkflows.length > 0) {
			const namedActions = availableScopes?.named_workflow_actions ?? ["read", "execute"];
			for (const wf of selectedWorkflows) {
				for (const action of namedActions) {
					const named = `workflow:${wf}:${action}`;
					if (!scopes.includes(named)) scopes.push(named);
				}
			}
		}
		return scopes;
	};

	const handleCreate = async () => {
		if (!tokenName.trim()) {
			showToast("error", "Please enter a token name");
			return;
		}

		const scopes = buildFinalScopes();
		if (scopes.length === 0) {
			showToast("error", "Please select at least one scope");
			return;
		}

		try {
			setCreating(true);

			const request: CreateTokenRequest = {
				name: tokenName.trim(),
				scopes,
				description: description.trim() || undefined,
				expires_in_days: expiresInDays || undefined,
			};

			const response = await userAPITokenService.createToken(request);

			showToast("success", "Token created successfully!");
			onTokenCreated(response.token, response);
		} catch (error) {
			console.error("Failed to create token:", error);
			showToast(
				"error",
				`Failed to create token: ${error instanceof Error ? error.message : "Unknown error"}`,
			);
		} finally {
			setCreating(false);
		}
	};

	return (
		<div className="fixed inset-0 z-50 flex items-start justify-center bg-black/50 p-4 pt-12">
			<div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-[4px] border border-slate-200 bg-white shadow-[0_18px_50px_rgba(15,23,42,0.12)]">
				{/* Header — Workflow Management style */}
				<div className="flex-none border-b border-slate-200 bg-white px-6 pb-4 pt-5">
					<div className="flex items-start justify-between gap-3">
						<div className="flex min-w-0 items-center gap-3">
							<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[4px] border border-orange-200 bg-orange-100">
								<Key className="h-5 w-5 text-orange-600" />
							</div>
							<div>
								<h3 className="text-lg font-semibold tracking-tight text-slate-900">Create New API Token</h3>
								<p className="mt-0.5 text-sm text-slate-600">Configure name, scopes, and expiration.</p>
							</div>
						</div>
						<button
							onClick={onClose}
							type="button"
							className="shrink-0 rounded-[4px] p-1.5 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800"
						>
							<X className="h-5 w-5" />
						</button>
					</div>
				</div>

				{/* Body */}
				<div className="space-y-6 p-6">
					{/* Token Name */}
					<div>
						<label className="mb-2 block text-sm font-medium text-slate-900">
							Token Name <span className="text-red-600">*</span>
						</label>
						<input
							type="text"
							value={tokenName}
							onChange={(e) => setTokenName(e.target.value)}
							placeholder="e.g., CI/CD Pipeline Token"
							className="w-full rounded-[4px] border border-slate-200 bg-white px-4 py-2 text-slate-900 placeholder:text-slate-400 transition-all hover:border-orange-400 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/15"
							maxLength={100}
						/>
						<p className="mt-1 text-xs text-slate-500">A descriptive name to help you identify this token</p>
					</div>

					{/* Description */}
					<div>
						<label className="mb-2 block text-sm font-medium text-slate-900">Description (Optional)</label>
						<textarea
							value={description}
							onChange={(e) => setDescription(e.target.value)}
							placeholder="e.g., Token for GitHub Actions workflow automation"
							rows={3}
							className="w-full resize-none rounded-[4px] border border-slate-200 bg-white px-4 py-2 text-slate-900 placeholder:text-slate-400 transition-all hover:border-orange-400 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/15"
							maxLength={500}
						/>
					</div>

					{/* Scopes */}
					<div>
						<label className="mb-2 block text-sm font-medium text-slate-900">Scopes</label>
						{loadingScopes ? (
							<div className="py-2 text-xs text-slate-600">Loading available scopes...</div>
						) : (
							<ScopePicker
								availableScopes={availableScopes}
								selectedScopes={selectedScopes}
								onToggle={toggleScope}
								showNamedWorkflows={showNamedWorkflows}
								onToggleNamedWorkflows={(val) => {
									setShowNamedWorkflows(val);
									if (val && workflows.length === 0) void loadWorkflows();
								}}
								selectedWorkflows={selectedWorkflows}
								workflows={workflows}
								loadingWorkflows={loadingWorkflows}
								onToggleWorkflow={(wf) => {
									setSelectedWorkflows((prev) =>
										prev.includes(wf) ? prev.filter((w) => w !== wf) : [...prev, wf],
									);
								}}
							/>
						)}
					</div>

					{/* Expiration */}
					<div>
						<label className="mb-2 block text-sm font-medium text-slate-900">Expiration</label>
						<div className="grid grid-cols-2 gap-2 md:grid-cols-4">
							{[30, 60, 90, 365].map((days) => (
								<button
									key={days}
									type="button"
									onClick={() => setExpiresInDays(days)}
									className={`rounded-[4px] border px-4 py-2 text-sm font-medium transition-all ${
										expiresInDays === days
											? "border-orange-500 bg-orange-500 text-white"
											: "border-slate-200 bg-white text-slate-700 hover:border-orange-400 hover:text-slate-900"
									}`}
								>
									{days} days
								</button>
							))}
						</div>
						<label className="mt-2 flex cursor-pointer items-center gap-2 rounded-[4px] border border-slate-200 bg-white p-3 transition-colors hover:border-orange-400">
							<input
								type="checkbox"
								checked={expiresInDays === null}
								onChange={(e) => setExpiresInDays(e.target.checked ? null : 90)}
								className="accent-orange-500"
							/>
							<span className="text-sm text-slate-800">No expiration</span>
						</label>
					</div>

					{/* Warning */}
					<div className="flex items-start gap-3 rounded-[4px] border border-amber-300 bg-white p-4 shadow-sm">
						<AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
						<div className="text-sm text-amber-950">
							<p className="mb-1 font-medium text-amber-900">Important: Save your token immediately!</p>
							<p className="text-slate-800">
								For security reasons, the token will only be shown once. Make sure to copy it to a secure
								location before closing this window.
							</p>
						</div>
					</div>
				</div>

				{/* Footer */}
				<div className="flex items-center justify-end gap-3 border-t border-slate-200 p-6">
					<Button
						onClick={onClose}
						variant="secondary"
						disabled={creating}
						className="!border-slate-200 !bg-white !text-slate-800 hover:!border-orange-500 hover:!text-orange-700"
					>
						Cancel
					</Button>
					<Button
						onClick={handleCreate}
						disabled={creating || !tokenName.trim()}
						className="shadow-[0_8px_20px_rgba(15,23,42,0.12)]"
					>
						{creating ? "Creating..." : "Create Token"}
					</Button>
				</div>
			</div>
		</div>
	);
}

// Token Created Success Modal
function TokenCreatedModal({
	token,
	tokenData,
	onClose,
}: {
	token: string;
	tokenData: any;
	onClose: () => void;
}) {
	const [copied, setCopied] = useState(false);
	const [showToken, setShowToken] = useState(true);
	const { showToast } = useToast();

	const handleCopy = async () => {
		try {
			await navigator.clipboard.writeText(token);
			setCopied(true);
			showToast("success", "Token copied to clipboard");
			setTimeout(() => setCopied(false), 2000);
		} catch (error) {
			console.error("Failed to copy token:", error);
			showToast("error", "Failed to copy token to clipboard");
		}
	};

	return (
		<div className="fixed inset-0 z-50 flex items-start justify-center bg-black/50 p-4 pt-16">
			<div className="flex max-h-[90vh] w-full max-w-2xl flex-col rounded-[4px] border border-slate-200 bg-white shadow-[0_18px_50px_rgba(15,23,42,0.12)]">
				{/* Header */}
				<div className="border-b border-slate-200 bg-white px-6 pb-4 pt-5">
					<div className="flex items-start gap-3">
						<div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[4px] border border-[#0DA931] bg-[#F1F8E9]">
							<CheckCircle className="h-6 w-6 text-[#0DA931]" />
						</div>
						<div className="min-w-0 flex-1">
							<h3 className="text-lg font-semibold tracking-tight text-slate-900">Token Created Successfully!</h3>
							<p className="mt-1 text-sm text-slate-600">
								Make sure to copy your token now. You won&apos;t be able to see it again!
							</p>
						</div>
					</div>
				</div>

				{/* Body */}
				<div className="min-h-0 flex-1 overflow-y-auto p-6">
					<div className="space-y-4">
						{/* Token Display */}
						<div>
							<label className="mb-2 block text-sm font-medium text-slate-900">Your Personal Access Token</label>
							<div className="relative">
								<div className="flex items-center gap-2 rounded-[4px] border border-slate-200 bg-slate-50 p-4 font-mono text-sm break-all">
									<code className="flex-1 text-orange-700">{showToken ? token : "•".repeat(token.length)}</code>
									<button
										onClick={() => setShowToken(!showToken)}
										className="shrink-0 rounded-[4px] p-2 text-slate-600 transition-colors hover:bg-white hover:text-slate-900"
										title={showToken ? "Hide token" : "Show token"}
										type="button"
									>
										{showToken ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
									</button>
									<button
										onClick={handleCopy}
										className="shrink-0 rounded-[4px] p-2 text-slate-600 transition-colors hover:bg-white hover:text-slate-900"
										title="Copy token"
										type="button"
									>
										{copied ? <CheckCircle className="h-4 w-4 text-[#0DA931]" /> : <Copy className="h-4 w-4" />}
									</button>
								</div>
							</div>
						</div>

						{/* Token Info */}
						<div className="grid grid-cols-2 gap-4 rounded-[4px] border border-slate-200 bg-white p-4 shadow-sm">
							<div>
								<div className="mb-1 text-xs font-medium text-slate-500">Token Name</div>
								<div className="text-sm font-medium text-slate-900">{tokenData.token_name}</div>
							</div>
							<div>
								<div className="mb-1 text-xs font-medium text-slate-500">Token Prefix</div>
								<div className="font-mono text-sm text-slate-900">
									{tokenData.token_prefix}•••
								</div>
							</div>
							<div>
								<div className="mb-1 text-xs font-medium text-slate-500">Scopes</div>
								<div className="text-sm text-slate-900">{tokenData.scopes.join(", ")}</div>
							</div>
							<div>
								<div className="mb-1 text-xs font-medium text-slate-500">Expires</div>
								<div className="text-sm text-slate-900">
									{tokenData.expires_at ? new Date(tokenData.expires_at).toLocaleDateString() : "Never"}
								</div>
							</div>
						</div>

						{/* Usage Example */}
						<div>
							<label className="mb-2 block text-sm font-medium text-slate-900">Usage Example</label>
							<div className="rounded-[4px] border border-slate-200 bg-slate-50 p-4 font-mono text-xs">
								<pre className="whitespace-pre-wrap text-slate-800">{`# Execute a workflow via HTTP API
	curl -X POST "https://your-api.com/api/http-execution/trigger/my-workflow?token=${tokenData.token_prefix}..." \\
	-H "Content-Type: application/json" \\
	-d '{"input": "your data"}'`}</pre>
							</div>
						</div>

						{/* Warning */}
						<div className="flex items-start gap-3 rounded-[4px] border border-red-200 bg-white p-4 shadow-sm">
							<AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-red-600" />
							<div className="text-sm">
								<p className="mb-1 font-medium text-red-800">This is your only chance to copy this token!</p>
								<p className="text-slate-800">
									For security reasons, this token will never be shown again. If you lose it, you&apos;ll need to
									generate a new one.
								</p>
							</div>
						</div>
					</div>
				</div>
				
				{/* Footer */}
				<div className="flex items-center justify-end gap-3 border-t border-slate-200 px-6 py-4">
					<Button onClick={onClose} className="shadow-[0_8px_20px_rgba(15,23,42,0.12)]">
						I&apos;ve Saved My Token
					</Button>
				</div>
			</div>
		</div>
	);
}

// Shared Scope Picker Component
function ScopePicker({
	availableScopes,
	selectedScopes,
	onToggle,
	showNamedWorkflows,
	onToggleNamedWorkflows,
	selectedWorkflows,
	workflows,
	loadingWorkflows,
	onToggleWorkflow,
}: {
	availableScopes: AvailableScopesResponse | null;
	selectedScopes: string[];
	onToggle: (scope: string) => void;
	showNamedWorkflows: boolean;
	onToggleNamedWorkflows: (val: boolean) => void;
	selectedWorkflows: string[];
	workflows: { graph_name: string }[];
	loadingWorkflows: boolean;
	onToggleWorkflow: (wf: string) => void;
}) {
	if (!availableScopes) {
		return (
			<div className="rounded-[4px] border border-slate-200 bg-white p-3 shadow-sm">
				<p className="text-xs text-slate-600">
					Could not load available scopes. Default scopes will be applied.
				</p>
			</div>
		);
	}

	// Group scopes by resource
	const byResource = availableScopes.scopes.reduce<Record<string, ScopeDefinition[]>>(
		(acc, def) => {
			if (!acc[def.resource]) acc[def.resource] = [];
			acc[def.resource].push(def);
			return acc;
		},
		{},
	);

	return (
		<div className="space-y-4">
			{Object.entries(byResource).map(([resource, defs]) => (
				<div key={resource}>
					<div className="mb-2 text-xs font-semibold capitalize tracking-wide text-slate-500">{resource}</div>
					<div className="space-y-1">
						{defs.map((def) => (
							<label
								key={def.scope}
								className="flex cursor-pointer items-start gap-2 rounded-[4px] p-2 transition-colors hover:bg-slate-50"
							>
								<input
									type="checkbox"
									checked={selectedScopes.includes(def.scope)}
									onChange={() => onToggle(def.scope)}
									className="mt-0.5 accent-orange-500"
								/>
								<div>
									<div className="font-mono text-sm text-slate-900">{def.scope}</div>
									<div className="text-xs text-slate-600">{def.description}</div>
								</div>
							</label>
						))}
					</div>
				</div>
			))}

			{/* Named workflow scope option */}
			{availableScopes.named_workflow_actions.length > 0 && (
				<div>
					<label className="flex cursor-pointer items-start gap-2 rounded-[4px] p-2 transition-colors hover:bg-slate-50">
						<input
							type="checkbox"
							checked={showNamedWorkflows}
							onChange={(e) => onToggleNamedWorkflows(e.target.checked)}
							className="mt-0.5 accent-orange-500"
						/>
						<div>
							<div className="font-mono text-sm text-slate-900">
								{"workflow:<name>:" + availableScopes.named_workflow_actions.join("|")}
							</div>
							<div className="text-xs text-slate-600">Restrict to specific named workflows only</div>
						</div>
					</label>
					{showNamedWorkflows && (
						<div className="mt-2 max-h-48 space-y-2 overflow-y-auto rounded-[4px] border border-slate-200 bg-slate-50 p-3">
							{loadingWorkflows ? (
								<div className="py-2 text-center text-xs text-slate-600">Loading workflows...</div>
							) : workflows.length === 0 ? (
								<div className="py-2 text-center text-xs text-slate-600">No published workflows found</div>
							) : (
								workflows.map((wf) => (
									<label key={wf.graph_name} className="flex cursor-pointer items-center gap-2">
										<input
											type="checkbox"
											checked={selectedWorkflows.includes(wf.graph_name)}
											onChange={() => onToggleWorkflow(wf.graph_name)}
											className="accent-orange-500"
										/>
										<span className="font-mono text-sm text-slate-900">{wf.graph_name}</span>
									</label>
								))
							)}
						</div>
					)}
				</div>
			)}
		</div>
	);
}

// Edit Scopes Modal Component
function EditScopesModal({
	token,
	onClose,
	onSaved,
}: {
	token: UserAPIToken;
	onClose: () => void;
	onSaved: () => void;
}) {
	// Initialise selected scopes from the token's current scopes
	const [selectedScopes, setSelectedScopes] = useState<string[]>(token.scopes);
	const [availableScopes, setAvailableScopes] = useState<AvailableScopesResponse | null>(null);
	const [loadingScopes, setLoadingScopes] = useState(true);
	// Detect any existing named-workflow scopes (workflow:<name>:action where name != *)
	const hasExistingNamed = token.scopes.some((s) => {
		const parts = s.split(":");
		return parts[0] === "workflow" && parts[1] !== "*" && parts.length === 3;
	});
	const [showNamedWorkflows, setShowNamedWorkflows] = useState(hasExistingNamed);
	const initialNamedWorkflows = Array.from(
		new Set(
			token.scopes
				.filter((s) => {
					const parts = s.split(":");
					return parts[0] === "workflow" && parts[1] !== "*" && parts.length === 3;
				})
				.map((s) => s.split(":")[1]),
		),
	);
	const [selectedWorkflows, setSelectedWorkflows] = useState<string[]>(initialNamedWorkflows);
	const [workflows, setWorkflows] = useState<{ graph_name: string }[]>([]);
	const [loadingWorkflows, setLoadingWorkflows] = useState(false);
	const [saving, setSaving] = useState(false);
	const { showToast } = useToast();

	useEffect(() => {
		const load = async () => {
			try {
				const resp = await userAPITokenService.getAvailableScopes();
				setAvailableScopes(resp);
			} catch (err) {
				console.error("Failed to load available scopes:", err);
			} finally {
				setLoadingScopes(false);
			}
		};
		void load();
	}, []);

	const loadWorkflows = useCallback(async () => {
		setLoadingWorkflows(true);
		try {
			const response = await api.getPublishedWorkflows();
			setWorkflows(response.published_workflows || []);
		} catch (error) {
			console.error("Failed to load workflows:", error);
			showToast("error", "Failed to load published workflows");
		} finally {
			setLoadingWorkflows(false);
		}
	}, [showToast]);

	useEffect(() => {
		if (hasExistingNamed) void loadWorkflows();
	}, [hasExistingNamed, loadWorkflows]);

	const buildFinalScopes = (): string[] => {
		const scopes = [...selectedScopes];
		if (showNamedWorkflows && selectedWorkflows.length > 0) {
			const namedActions = availableScopes?.named_workflow_actions ?? ["read", "execute"];
			for (const wf of selectedWorkflows) {
				for (const action of namedActions) {
					const named = `workflow:${wf}:${action}`;
					if (!scopes.includes(named)) scopes.push(named);
				}
			}
		}
		return scopes;
	};

	const handleSave = async () => {
		const newScopes = buildFinalScopes();
		if (newScopes.length === 0) {
			showToast("error", "Please select at least one scope");
			return;
		}

		try {
			setSaving(true);
			await userAPITokenService.updateTokenScopes(token.id, newScopes);
			showToast("success", "Token scopes updated successfully");
			onSaved();
			onClose();
		} catch (error) {
			console.error("Failed to update scopes:", error);
			showToast("error", "Failed to update token scopes");
		} finally {
			setSaving(false);
		}
	};

	return (
		<div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
			<div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-[4px] border border-slate-200 bg-white shadow-[0_18px_50px_rgba(15,23,42,0.12)]">
				{/* Header */}
				<div className="border-b border-slate-200 bg-white px-6 pb-4 pt-5">
					<div className="flex items-start justify-between gap-3">
						<div className="flex min-w-0 items-center gap-3">
							<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[4px] border border-orange-200 bg-orange-100">
								<Pencil className="h-5 w-5 text-orange-600" />
							</div>
							<div className="min-w-0">
								<h3 className="text-lg font-semibold tracking-tight text-slate-900">Edit Scopes</h3>
								<p className="mt-1 truncate text-sm text-slate-600">{token.name}</p>
							</div>
						</div>
						<button
							onClick={onClose}
							type="button"
							className="shrink-0 rounded-[4px] p-1.5 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800"
						>
							<X className="h-5 w-5" />
						</button>
					</div>
				</div>

				{/* Body */}
				<div className="p-6">
					{loadingScopes ? (
						<div className="py-2 text-xs text-slate-600">Loading available scopes...</div>
					) : (
						<ScopePicker
							availableScopes={availableScopes}
							selectedScopes={selectedScopes}
							onToggle={(scope) =>
								setSelectedScopes((prev) =>
									prev.includes(scope) ? prev.filter((s) => s !== scope) : [...prev, scope],
								)
							}
							showNamedWorkflows={showNamedWorkflows}
							onToggleNamedWorkflows={(val) => {
								setShowNamedWorkflows(val);
								if (val && workflows.length === 0) void loadWorkflows();
							}}
							selectedWorkflows={selectedWorkflows}
							workflows={workflows}
							loadingWorkflows={loadingWorkflows}
							onToggleWorkflow={(wf) => {
								setSelectedWorkflows((prev) =>
									prev.includes(wf) ? prev.filter((w) => w !== wf) : [...prev, wf],
								);
							}}
						/>
					)}
				</div>

				{/* Footer */}
				<div className="flex items-center justify-end gap-3 border-t border-slate-200 p-6">
					<Button
						onClick={onClose}
						variant="secondary"
						disabled={saving}
						className="!border-slate-200 !bg-white !text-slate-800 hover:!border-orange-500 hover:!text-orange-700"
					>
						Cancel
					</Button>
					<Button
						onClick={handleSave}
						disabled={saving}
						className="shadow-[0_8px_20px_rgba(15,23,42,0.12)]"
					>
						{saving ? "Saving..." : "Save Scopes"}
					</Button>
				</div>
			</div>
		</div>
	);
}
