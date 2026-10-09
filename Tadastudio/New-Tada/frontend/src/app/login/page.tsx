"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Eye, EyeOff, LogIn } from "lucide-react";

// ─── Skip-auth helpers (temporary local credential mode) ─────────────────────

const SKIP_AUTH = process.env.NEXT_PUBLIC_SKIP_AUTH === "true";
const SESSION_KEY = "tada_skip_auth_session";

// Check email+password against a raw credential string (comma or pipe separated).
// Called inline inside the handler so process.env is read on the client, not at SSR.
function matchCredential(raw: string | undefined, email: string, password: string): boolean {
	if (!raw) return false;
	const cleaned = raw.replace(/^["'`]|["'`]$/g, "").trim();
	for (const chunk of cleaned.split(/[|,]/)) {
		const pair = chunk.trim();
		if (!pair) continue;
		const colonIdx = pair.indexOf(":");
		if (colonIdx < 1) continue;
		const e = pair.slice(0, colonIdx).trim().toLowerCase();
		const p = pair.slice(colonIdx + 1).trim();
		if (e === email && p === password) return true;
	}
	return false;
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function LoginPage() {
	const searchParams = useSearchParams();
	const rd = searchParams.get("rd") || "/";

	// ── Skip-auth state ──────────────────────────────────────────────────────
	const [skipEmail,    setSkipEmail]    = useState("");
	const [skipPassword, setSkipPassword] = useState("");
	const [showPw,       setShowPw]       = useState(false);
	const [skipError,    setSkipError]    = useState<string | null>(null);
	const [skipLoading,  setSkipLoading]  = useState(false);

	// ── Original local-auth state ────────────────────────────────────────────
	const [localAuthEnabled, setLocalAuthEnabled] = useState<boolean | null>(null);
	const [email,    setEmail]    = useState("");
	const [password, setPassword] = useState("");
	const [error,    setError]    = useState<string | null>(null);
	const [loading,  setLoading]  = useState(false);

	// ── Original: check whether local auth is enabled on mount ──────────────
	// (Only runs when SKIP_AUTH is off so we never hit the API in skip-auth mode)
	useEffect(() => {
		if (SKIP_AUTH) return;

		fetch("/api/auth/local/status", { credentials: "include" })
			.then((r) => r.json())
			.then((data) => {
				if (!data.enabled) {
					window.location.replace(
						`/oauth2/start?rd=${encodeURIComponent(rd)}`,
					);
				} else {
					setLocalAuthEnabled(true);
				}
			})
			.catch(() => {
				// If the status check fails, fall back to Microsoft auth
				window.location.replace(
					`/oauth2/start?rd=${encodeURIComponent(rd)}`,
				);
			});
	}, [rd]);

	// ── Original: Microsoft sign-in ──────────────────────────────────────────
	const handleMicrosoftSignIn = () => {
		window.location.href = `/oauth2/start?rd=${encodeURIComponent(rd)}`;
	};

	// ── Original: local API sign-in ──────────────────────────────────────────
	const handleLocalSignIn = async (e: React.FormEvent) => {
		e.preventDefault();
		setError(null);
		setLoading(true);
		try {
			const res = await fetch("/api/auth/local/login", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				credentials: "include",
				body: JSON.stringify({ email, password }),
			});
			if (!res.ok) {
				const data = await res.json().catch(() => ({}));
				setError(data.detail ?? "Invalid email or password.");
				return;
			}
			window.location.href = rd;
		} catch {
			setError("Network error -- please try again.");
		} finally {
			setLoading(false);
		}
	};

	// ── Skip-auth: env-credential sign-in ────────────────────────────────────
	const handleSkipAuthSignIn = (e: React.FormEvent) => {
		e.preventDefault();
		setSkipError(null);
		setSkipLoading(true);

		const key = skipEmail.trim().toLowerCase();
		let matched = false;
		let isAdmin = false;

		if (matchCredential(process.env.NEXT_PUBLIC_ADMIN_CREDENTIALS, key, skipPassword))      { matched = true; isAdmin = true; }
		else if (matchCredential(process.env.NEXT_PUBLIC_USER_CREDENTIALS, key, skipPassword))  { matched = true; }

		if (!matched) {
			setSkipError("Invalid email or password.");
			setSkipLoading(false);
			return;
		}

		const session = {
			email: key,
			name: key
				.split("@")[0]
				.replace(/[._]/g, " ")
				.replace(/\b\w/g, (c) => c.toUpperCase()),
			is_admin: isAdmin,
			role: isAdmin ? "ADMIN" : "USER",
			auth_source: "skip_auth",
		};

		try {
			localStorage.setItem(SESSION_KEY, JSON.stringify(session));
		} catch {
			// storage may be blocked in private mode — proceed anyway
		}

		// Full reload so AuthContext re-initialises and reads the new session.
		window.location.href = rd;
	};

	// ═════════════════════════════════════════════════════════════════════════
	// SKIP_AUTH = true  →  Temporary Mashreq-themed local login
	// ═════════════════════════════════════════════════════════════════════════
	if (SKIP_AUTH) {
		return (
			<div className="min-h-screen flex flex-col items-center justify-center bg-white px-4">
				<div className="w-full max-w-sm">

					{/* Logo + heading */}
					<div className="flex flex-col items-center mb-8">
						<img
							src="/logo.png"
							alt="Mashreq"
							className="h-10 w-auto object-contain mb-5"
						/>
						<h1 className="text-2xl font-bold text-gray-900 tracking-tight">
							Sign in to TADA Studio
						</h1>
						<p className="mt-1 text-sm text-gray-500">
							Enter your credentials to continue
						</p>
					</div>

					{/* Card */}
					<div className="rounded-2xl border border-gray-200 bg-white shadow-sm px-8 py-8">
						<form onSubmit={handleSkipAuthSignIn} className="space-y-5">

							{/* Email */}
							<div>
								<label
									htmlFor="skip-email"
									className="block text-xs font-semibold uppercase tracking-wider text-gray-500 mb-1.5"
								>
									Email
								</label>
								<input
									id="skip-email"
									type="email"
									autoComplete="email"
									required
									value={skipEmail}
									onChange={(e) => setSkipEmail(e.target.value)}
									placeholder="you@mashreq.com"
									className="w-full rounded-lg border border-gray-200 bg-gray-50 px-4 py-2.5 text-sm text-gray-900 placeholder-gray-400 outline-none transition-colors focus:border-[#ff6b00] focus:ring-2 focus:ring-[#ff6b00]/20"
								/>
							</div>

							{/* Password */}
							<div>
								<label
									htmlFor="skip-password"
									className="block text-xs font-semibold uppercase tracking-wider text-gray-500 mb-1.5"
								>
									Password
								</label>
								<div className="relative">
									<input
										id="skip-password"
										type={showPw ? "text" : "password"}
										autoComplete="current-password"
										required
										value={skipPassword}
										onChange={(e) => setSkipPassword(e.target.value)}
										placeholder="••••••••"
										className="w-full rounded-lg border border-gray-200 bg-gray-50 px-4 py-2.5 pr-10 text-sm text-gray-900 placeholder-gray-400 outline-none transition-colors focus:border-[#ff6b00] focus:ring-2 focus:ring-[#ff6b00]/20"
									/>
									<button
										type="button"
										onClick={() => setShowPw((v) => !v)}
										className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
										tabIndex={-1}
										aria-label={showPw ? "Hide password" : "Show password"}
									>
										{showPw
											? <EyeOff className="h-4 w-4" />
											: <Eye    className="h-4 w-4" />}
									</button>
								</div>
							</div>

							{/* Error */}
							{skipError && (
								<p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-600">
									{skipError}
								</p>
							)}

							{/* Submit */}
							<button
								type="submit"
								disabled={skipLoading}
								className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#ff6b00] px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-[#e55f00] active:scale-[0.98] disabled:opacity-60"
							>
								{skipLoading ? (
									<span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
								) : (
									<LogIn className="h-4 w-4" />
								)}
								{skipLoading ? "Signing in…" : "Sign in"}
							</button>
						</form>
					</div>

					{/* Footer */}
					<p className="mt-6 text-center text-xs text-gray-400">
						Powered by{" "}
						<span className="font-semibold text-[#ff6b00]">Mashreq</span>
					</p>
				</div>
			</div>
		);
	}

	// ═════════════════════════════════════════════════════════════════════════
	// SKIP_AUTH = false  →  Original OAuth / local-API login (unchanged)
	// ═════════════════════════════════════════════════════════════════════════

	// Show nothing while we determine whether local auth is on (avoids flash)
	if (localAuthEnabled === null) {
		return (
			<div
				className="flex min-h-screen items-center justify-center"
				style={{ background: "var(--color-bg-primary)" }}
			/>
		);
	}

	return (
		<div
			className="flex min-h-screen items-center justify-center p-4"
			style={{ background: "var(--color-bg-primary)" }}
		>
			<div
				className="w-full max-w-sm rounded-[24px] border-2 p-8 shadow-[0_35px_120px_rgba(0,0,0,0.65)]"
				style={{
					borderColor: "rgba(var(--color-primary-rgb),0.30)",
					background:
						"linear-gradient(135deg, rgba(26,26,26,0.96), rgba(16,16,16,0.98), rgba(6,6,6,1))",
				}}
			>
				{/* Header */}
				<div className="mb-8 text-center">
					<h1
						className="mb-1 text-2xl font-semibold"
						style={{ color: "var(--color-text-primary)" }}
					>
						Sign in
					</h1>
					<p
						className="text-sm"
						style={{ color: "var(--color-text-muted)" }}
					>
						Choose how you&apos;d like to continue
					</p>
				</div>

				{/* Microsoft sign-in */}
				<button
					type="button"
					onClick={handleMicrosoftSignIn}
					className="mb-6 flex w-full items-center justify-center gap-3 rounded-xl border px-4 py-3 text-sm font-medium transition-all duration-200 hover:brightness-110 active:scale-[0.98]"
					style={{
						borderColor: "rgba(var(--color-primary-rgb),0.40)",
						background: "rgba(var(--color-primary-rgb),0.10)",
						color: "var(--color-primary-light)",
					}}
				>
					<MicrosoftLogo />
					Sign in with Microsoft
				</button>

				{/* Divider */}
				<div className="mb-6 flex items-center gap-3">
					<div
						className="h-px flex-1"
						style={{ background: "var(--color-border)" }}
					/>
					<span
						className="text-xs uppercase"
						style={{ color: "var(--color-text-muted)" }}
					>
						or
					</span>
					<div
						className="h-px flex-1"
						style={{ background: "var(--color-border)" }}
					/>
				</div>

				{/* Local sign-in form */}
				<form onSubmit={handleLocalSignIn} className="space-y-4">
					<div>
						<label
							htmlFor="email"
							className="mb-1.5 block text-xs uppercase"
							style={{ color: "var(--color-text-secondary)" }}
						>
							Email
						</label>
						<input
							id="email"
							type="email"
							autoComplete="email"
							required
							value={email}
							onChange={(e) => setEmail(e.target.value)}
							className="w-full rounded-xl border px-4 py-2.5 text-sm outline-none transition-colors focus:border-[color:var(--color-primary)]"
							style={{
								background: "rgba(255,255,255,0.04)",
								borderColor: "var(--color-border)",
								color: "var(--color-text-primary)",
							}}
						/>
					</div>
					<div>
						<label
							htmlFor="password"
							className="mb-1.5 block text-xs uppercase"
							style={{ color: "var(--color-text-secondary)" }}
						>
							Password
						</label>
						<input
							id="password"
							type="password"
							autoComplete="current-password"
							required
							value={password}
							onChange={(e) => setPassword(e.target.value)}
							className="w-full rounded-xl border px-4 py-2.5 text-sm outline-none transition-colors focus:border-[color:var(--color-primary)]"
							style={{
								background: "rgba(255,255,255,0.04)",
								borderColor: "var(--color-border)",
								color: "var(--color-text-primary)",
							}}
						/>
					</div>

					{error && (
						<p className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-400">
							{error}
						</p>
					)}

					<button
						type="submit"
						disabled={loading}
						className="w-full rounded-xl px-4 py-2.5 text-sm font-medium transition-all duration-200 hover:brightness-110 active:scale-[0.98] disabled:opacity-50"
						style={{
							background:
								"linear-gradient(135deg, rgba(var(--color-primary-rgb),0.8), rgba(var(--color-primary-rgb),0.6))",
							color: "var(--button-primary-text, #fff)",
						}}
					>
						{loading ? "Signing in..." : "Sign in"}
					</button>
				</form>
			</div>
		</div>
	);
}

function MicrosoftLogo() {
	return (
		<svg width="18" height="18" viewBox="0 0 21 21" aria-hidden="true">
			<rect x="1"  y="1"  width="9" height="9" fill="#F25022" />
			<rect x="11" y="1"  width="9" height="9" fill="#7FBA00" />
			<rect x="1"  y="11" width="9" height="9" fill="#00A4EF" />
			<rect x="11" y="11" width="9" height="9" fill="#FFB900" />
		</svg>
	);
}
