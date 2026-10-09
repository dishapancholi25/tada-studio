"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface AuthResult {
	ok: boolean;
	has_refresh_token: boolean;
	me: {
		status: number;
		body: any;
	};
}

export default function AzureAuthDemo() {
	const [authResult, setAuthResult] = useState<AuthResult | null>(null);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		const urlParams = new URLSearchParams(window.location.search);
		const code = urlParams.get("code");
		const errorParam = urlParams.get("error");

		if (errorParam) {
			setError(
				`OAuth Error: ${errorParam} - ${urlParams.get("error_description")}`,
			);
		} else if (code) {
			handleAuthCallback();
		}
	}, []);

	const handleLogin = async () => {
		try {
			setLoading(true);
			setError(null);
			await api.startAzureLogin();
		} catch (err) {
			setError(`Login failed: ${err}`);
			setLoading(false);
		}
	};

	const handleAuthCallback = async () => {
		try {
			setLoading(true);
			setError(null);
			const result = await api.getAzureAuthCallback();
			setAuthResult(result);

			// Clean up URL
			window.history.replaceState({}, document.title, window.location.pathname);
		} catch (err: any) {
			setError(`Authentication failed: ${err.message || err}`);
		} finally {
			setLoading(false);
		}
	};

	const resetDemo = () => {
		setAuthResult(null);
		setError(null);
	};

	return (
		<div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
			<div className="max-w-md mx-auto bg-white rounded-lg shadow-md p-6">
				<div className="text-center">
					<h1 className="text-2xl font-bold text-gray-900 mb-6">
						Azure OAuth Demo
					</h1>

					{error && (
						<div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
							{error}
						</div>
					)}

					{loading && (
						<div className="mb-4 p-3 bg-blue-100 border border-blue-400 text-blue-700 rounded">
							Processing...
						</div>
					)}

					{!authResult && !loading && (
						<div className="space-y-4">
							<p className="text-gray-600 mb-4">
								Click the button below to start the Microsoft OAuth flow.
							</p>
							<button
								onClick={handleLogin}
								disabled={loading}
								className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
							>
								Login with Microsoft
							</button>
						</div>
					)}

					{authResult && (
						<div className="space-y-4">
							<div className="p-4 bg-[#F1F8E9] border border-[#0DA931] text-[#0DA931] rounded">
								<h3 className="font-bold mb-2">Authentication Successful!</h3>
								<div className="text-left text-sm">
									<p>
										<strong>Has Refresh Token:</strong>{" "}
										{authResult.has_refresh_token ? "Yes" : "No"}
									</p>
									<p>
										<strong>Graph API Status:</strong> {authResult.me?.status}
									</p>
								</div>
							</div>

							{authResult.me?.body && (
								<div className="p-4 bg-gray-100 border border-gray-300 rounded">
									<h4 className="font-bold mb-2">
										User Information (from Graph API):
									</h4>
									<div className="text-left text-sm space-y-1">
										<p>
											<strong>Name:</strong> {authResult.me.body.displayName}
										</p>
										<p>
											<strong>Email:</strong>{" "}
											{authResult.me.body.mail ||
												authResult.me.body.userPrincipalName}
										</p>
										<p>
											<strong>ID:</strong> {authResult.me.body.id}
										</p>
										<p>
											<strong>Job Title:</strong>{" "}
											{authResult.me.body.jobTitle || "N/A"}
										</p>
									</div>
								</div>
							)}

							<div className="p-4 bg-gray-50 border border-gray-200 rounded">
								<h4 className="font-bold mb-2">Raw Response:</h4>
								<pre className="text-xs text-left overflow-auto max-h-40 whitespace-pre-wrap">
									{JSON.stringify(authResult, null, 2)}
								</pre>
							</div>

							<button
								onClick={resetDemo}
								className="w-full bg-gray-600 text-white py-2 px-4 rounded-md hover:bg-gray-700 transition-colors"
							>
								Reset Demo
							</button>
						</div>
					)}
				</div>
			</div>
		</div>
	);
}
