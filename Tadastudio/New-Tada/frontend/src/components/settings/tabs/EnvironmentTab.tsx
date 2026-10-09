"use client";

import { Check, Copy, FileText, RefreshCw, Search } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import Button from "@/components/ui/Button";
import FormInput from "@/components/ui/FormInput";
import { useToast } from "@/contexts/ToastContext";
import { configAPI } from "@/lib/config-api";

export default function EnvironmentTab() {
	const [envContent, setEnvContent] = useState("");
	const [loading, setLoading] = useState(true);
	const [searchTerm, setSearchTerm] = useState("");
	const [copiedLine, setCopiedLine] = useState<number | null>(null);
	const { showToast } = useToast();

	useEffect(() => {
		loadEnvFile().catch((error) => {
			console.error("Failed to load environment file:", error);
		});
	}, []);

	const loadEnvFile = async () => {
		try {
			setLoading(true);
			const content = await configAPI.getEnvFileContent();
			setEnvContent(content);
		} catch (error) {
			console.error("Failed to load .env file:", error);
			showToast("error", "Failed to load environment file");
		} finally {
			setLoading(false);
		}
	};

	const copyToClipboard = (text: string, lineNumber: number) => {
		navigator.clipboard.writeText(text).catch((error) => {
			console.error("Failed to copy to clipboard:", error);
		});
		setCopiedLine(lineNumber);
		showToast("success", "Copied to clipboard");
		setTimeout(() => setCopiedLine(null), 2000);
	};

	const getFilteredLines = () => {
		const lines = envContent.split("\n");
		if (!searchTerm) return lines;

		return lines.filter((line) =>
			line.toLowerCase().includes(searchTerm.trim().toLowerCase()),
		);
	};

	const formatLine = (line: string) => {
		// Check if it's a comment
		if (line.trim().startsWith("#")) {
			return { type: "comment", content: line };
		}

		// Check if it's an environment variable
		const match = line.match(/^([A-Z_]+[A-Z0-9_]*)=(.*)$/);
		if (match) {
			const [, key, value] = match;
			return { type: "variable", key, value };
		}

		// Empty line or other
		return { type: "other", content: line };
	};

	const maskSensitiveValue = (key: string, value: string) => {
		const sensitiveKeys = ["KEY", "SECRET", "PASSWORD", "TOKEN", "API"];
		const isSensitive = sensitiveKeys.some((k) => key.includes(k));

		if (isSensitive && value.length > 4) {
			return `${value.substring(0, 4)}${"*".repeat(Math.min(value.length - 4, 20))}`;
		}
		return value;
	};

	// Change handler for search input
	const handleSearchChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setSearchTerm(e.target.value);
		},
		[],
	);

	// Factory function for copy handlers
	const createCopyHandler = useCallback(
		(text: string, lineNumber: number) => () => {
			copyToClipboard(text, lineNumber);
		},
		[],
	);

	return (
		<div className="p-6">
			{/* Header */}
			<div className="flex items-center justify-between mb-6">
				<div className="flex items-center gap-3">
					<div className="p-2 bg-gradient-to-br from-orange-500/20 to-red-500/20 rounded-lg">
						<FileText className="w-6 h-6 text-orange-400" />
					</div>
					<div>
						<h2 className="text-xl font-semibold text-slate-900">
							Environment Variables
						</h2>
						<p className="text-sm text-[color:var(--color-text-muted)] mt-1">
							View and search your .env configuration
						</p>
					</div>
				</div>
				<Button onClick={loadEnvFile} icon={<RefreshCw className="w-4 h-4" />}>
					Refresh
				</Button>
			</div>

			{/* Search Bar */}
			<div className="mb-6">
				<div className="relative">
					<Search
						className="absolute left-3 top-3 w-5 h-5"
						style={{ color: "var(--color-text-secondary)" }}
					/>
					<FormInput
						className="pl-10"
						value={searchTerm}
						onChange={handleSearchChange}
						placeholder="Search environment variables..."
					/>
				</div>
			</div>

			{/* Environment File Content */}
			{loading ? (
				<div className="flex items-center justify-center h-96">
					<div className="animate-pulse text-[color:var(--color-text-muted)]">
						Loading environment file...
					</div>
				</div>
			) : (
				<div className="bg-[color:var(--color-bg-secondary)]/60 backdrop-blur-sm border border-[color:var(--color-surface)] rounded-xl overflow-hidden">
					<div className="bg-[color:var(--color-surface)]/50 px-4 py-3 border-b border-[color:var(--color-border)]">
						<div className="flex items-center justify-between">
							<span className="text-sm text-[color:var(--color-text-muted)]">
								.env
							</span>
							<span className="text-xs text-[color:var(--color-text-muted)]">
								{envContent.split("\n").length} lines
							</span>
						</div>
					</div>

					<div className="overflow-x-auto">
						<div className="font-mono text-sm">
							{getFilteredLines().map((line, index) => {
								const formatted = formatLine(line);
								const lineNumber = envContent.split("\n").indexOf(line) + 1;

								return (
									<div
										key={`line-${lineNumber}-${line.substring(0, 30)}`}
										className="group flex hover:bg-[color:var(--color-surface)]/30 transition-colors duration-150"
									>
										{/* Line Number */}
										<div className="w-12 px-3 py-2 text-right text-[color:var(--color-text-muted)] select-none border-r border-[color:var(--color-surface)]">
											{lineNumber}
										</div>

										{/* Line Content */}
										<div className="flex-1 px-4 py-2 flex items-center justify-between">
											{formatted.type === "comment" ? (
												<span className="text-[color:var(--color-text-muted)]">
													{formatted.content}
												</span>
											) : formatted.type === "variable" ? (
												<div className="flex-1 flex items-center gap-2">
													<span className="text-[color:var(--color-accent)]">
														{formatted.key}
													</span>
													<span className="text-[color:var(--color-text-muted)]">
														=
													</span>
													<span className="text-[#0DA931]">
														{maskSensitiveValue(
															formatted.key!,
															formatted.value!,
														)}
													</span>
												</div>
											) : (
												<span className="text-[color:var(--color-text-muted)]">
													{formatted.content || "\u00A0"}
												</span>
											)}

											{/* Copy Button */}
											{formatted.type === "variable" && (
												<button
													onClick={createCopyHandler(
														`${formatted.key}=${formatted.value}`,
														lineNumber,
													)}
													className="ml-4 opacity-0 group-hover:opacity-100 transition-opacity duration-150"
												>
													{copiedLine === lineNumber ? (
														<Check className="w-4 h-4 text-[#0DA931]" />
													) : (
														<Copy className="w-4 h-4 text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text-secondary)]" />
													)}
												</button>
											)}
										</div>
									</div>
								);
							})}
						</div>
					</div>
				</div>
			)}

			{/* Info Box */}
			<div className="mt-6 p-4 bg-[color:var(--color-accent)]/15 border border-[color:var(--color-border)]/25 rounded-lg">
				<div className="flex items-start gap-3">
					<FileText className="w-5 h-5 text-[color:var(--color-accent)] mt-0.5" />
					<div>
						<p className="text-sm text-[color:var(--color-accent)] font-medium">
							Read-Only Mode
						</p>
						<p className="text-xs text-[color:var(--color-text-muted)] mt-1">
							Environment variables are displayed in read-only mode for
							security. To modify values, use the specific configuration tabs or
							edit the .env file directly.
						</p>
					</div>
				</div>
			</div>
		</div>
	);
}
