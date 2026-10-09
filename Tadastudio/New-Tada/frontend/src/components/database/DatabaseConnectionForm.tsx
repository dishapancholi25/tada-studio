"use client";

import {
	AlertCircle,
	CheckCircle,
	Database,
	Eye,
	EyeOff,
	Loader,
	TestTube,
	X,
} from "lucide-react";
import { useEffect, useState } from "react";
import Button from "@/components/ui/Button";
import FormInput from "@/components/ui/FormInput";
import FormTextarea from "@/components/ui/FormTextarea";
import { api } from "@/lib/api";

export type DatabaseType =
	| "postgres"
	| "mysql"
	| "mongodb"
	| "sqlite"
	| "mssql"
	| "oracle";

interface DatabaseConnectionFormProps {
	isOpen: boolean;
	onClose: () => void;
	onSubmit: (data: DatabaseConnectionData) => Promise<void>;
	initialData?: DatabaseConnectionData;
	mode: "create" | "edit";
}

export interface DatabaseConnectionData {
	id?: string;
	name: string;
	description?: string;
	database_type: DatabaseType;
	connection_string?: string;
	host?: string;
	port?: number;
	database_name?: string;
	username?: string;
	password?: string;
	use_ssl: boolean;
	ssl_config?: Record<string, any>;
	connection_options?: Record<string, any>;
	read_only?: boolean;
}

const DATABASE_DEFAULTS: Record<DatabaseType, { port: number; icon: string }> =
	{
		postgres: { port: 5432, icon: "🐘" },
		mysql: { port: 3306, icon: "🐬" },
		mongodb: { port: 27017, icon: "🍃" },
		sqlite: { port: 0, icon: "📁" },
		mssql: { port: 1433, icon: "🏢" },
		oracle: { port: 1521, icon: "🔶" },
	};

export default function DatabaseConnectionForm({
	isOpen,
	onClose,
	onSubmit,
	initialData,
	mode,
}: DatabaseConnectionFormProps) {
	const [formData, setFormData] = useState<DatabaseConnectionData>({
		name: "",
		description: "",
		database_type: "postgres",
		host: "localhost",
		port: 5432,
		database_name: "",
		username: "",
		password: "",
		use_ssl: false,
		read_only: true,
		connection_string: "",
	});

	const [useConnectionString, setUseConnectionString] = useState(false);
	const [showPassword, setShowPassword] = useState(false);
	const [submitting, setSubmitting] = useState(false);
	const [testing, setTesting] = useState(false);
	const [testResult, setTestResult] = useState<{
		success: boolean;
		message: string;
	} | null>(null);

	useEffect(() => {
		if (initialData) {
			setFormData(initialData);
			setUseConnectionString(!!initialData.connection_string);
		}
	}, [initialData]);

	const handleDatabaseTypeChange = (type: DatabaseType) => {
		setFormData({
			...formData,
			database_type: type,
			port: DATABASE_DEFAULTS[type].port,
		});
	};

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		setSubmitting(true);

		try {
			// Prepare data for submission
			const dataToSubmit = { ...formData };

			// Clear unused fields based on connection method
			if (useConnectionString) {
				delete dataToSubmit.host;
				delete dataToSubmit.port;
				delete dataToSubmit.database_name;
				delete dataToSubmit.username;
				delete dataToSubmit.password;
			} else {
				delete dataToSubmit.connection_string;
			}

			await onSubmit(dataToSubmit);
			onClose();
		} catch (error) {
			// console.error('Failed to save connection:', error);
		} finally {
			setSubmitting(false);
		}
	};

	const handleTestConnection = async () => {
		setTesting(true);
		setTestResult(null);

		try {
			// Prepare test data
			const testData = { ...formData };
			if (useConnectionString) {
				delete testData.host;
				delete testData.port;
				delete testData.database_name;
				delete testData.username;
				delete testData.password;
			} else {
				delete testData.connection_string;
			}

			// Test the connection configuration without saving
			const result = await api.testDatabaseConnectionConfig(testData);
			setTestResult({
				success: result.success,
				message: result.success
					? "Connection successful!"
					: result.error_message || "Connection failed",
			});
		} catch (error) {
			setTestResult({
				success: false,
				message: "Failed to test connection",
			});
		} finally {
			setTesting(false);
		}
	};

	if (!isOpen) return null;

	return (
		<div
			className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
			onClick={onClose}
		>
			<div
				data-tutorial="db-connection-modal"
				className="relative w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto overflow-hidden rounded-3xl border border-slate-200 bg-[color:var(--color-surface)] shadow-[0_30px_80px_rgba(4,7,17,0.18)]"
				onClick={(e) => e.stopPropagation()}
			>
				<div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-orange-500/60" />
				<div className="flex items-center justify-between gap-4 border-b border-slate-200 bg-white px-6 py-5">
					<div className="flex items-center gap-3">
						<div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-slate-200 bg-white text-orange-600 shadow-[0_10px_28px_rgba(15,23,42,0.08)]">
							<Database className="h-6 w-6" />
						</div>
						<div>
							<h3 className="text-lg font-semibold text-slate-900">
								{mode === "create"
									? "Add Database Connection"
									: "Edit Database Connection"}
							</h3>
							<p className="mt-1 text-sm text-slate-500">
								Configure database access for workflows.
							</p>
						</div>
					</div>
					<button
						type="button"
						onClick={onClose}
						className="rounded-xl border border-slate-200 bg-white p-2 text-slate-500 transition-colors hover:border-orange-400 hover:text-slate-900"
						aria-label="Close modal"
					>
						<X className="h-5 w-5" />
					</button>
				</div>

				<form onSubmit={handleSubmit} className="space-y-6 p-6">
					{/* Basic Information */}
					<div className="space-y-4">
						<div>
							<FormInput
								label="Connection Name *"
								value={formData.name}
								onChange={(e) =>
									setFormData({ ...formData, name: e.target.value })
								}
								placeholder="e.g., Production Database"
								required
							/>
						</div>

						<div>
							<FormTextarea
								label="Description"
								value={formData.description}
								onChange={(e) =>
									setFormData({ ...formData, description: e.target.value })
								}
								rows={2}
								placeholder="Brief description of this connection..."
							/>
						</div>

						<div data-tutorial="db-type-selector">
							<label
								id="database-type-label"
								className="block text-sm font-medium text-[color:var(--color-text-secondary)] mb-2"
							>
								Database Type *
							</label>
							<div
								className="grid grid-cols-3 gap-3"
								role="radiogroup"
								aria-labelledby="database-type-label"
							>
								{Object.entries(DATABASE_DEFAULTS).map(([type, config]) => (
									<button
										key={type}
										type="button"
										onClick={() =>
											handleDatabaseTypeChange(type as DatabaseType)
										}
										className={`px-4 py-3 rounded-lg border transition-all duration-200 ${
											formData.database_type === type
												? "bg-[color:var(--color-accent)]/20 border-[color:var(--color-border)] text-[color:var(--color-accent)]"
												: "bg-[color:var(--color-bg-secondary)] border-[color:var(--color-surface-hover)] text-[color:var(--color-text-secondary)] hover:border-[color:var(--color-text-muted)]"
										}`}
									>
										<div className="flex items-center gap-2">
											<span className="text-xl">{config.icon}</span>
											<span className="capitalize">{type}</span>
										</div>
									</button>
								))}
							</div>
						</div>
					</div>

					{/* Connection Method Toggle */}
					<div
						data-tutorial="db-connection-method"
						className="flex items-center gap-4 p-4 rounded-lg"
						style={{ background: "var(--color-bg-secondary)" }}
					>
						<label
							htmlFor="individual-fields-radio"
							className="flex items-center gap-2 cursor-pointer"
						>
							<input
								id="individual-fields-radio"
								type="radio"
								checked={!useConnectionString}
								onChange={() => setUseConnectionString(false)}
								className="text-[color:var(--color-accent)] focus:ring-[color:var(--color-accent)]"
							/>
							<span
								className="text-sm"
								style={{ color: "var(--color-text-primary)" }}
							>
								Individual Fields
							</span>
						</label>
						<label
							htmlFor="connection-string-radio"
							className="flex items-center gap-2 cursor-pointer"
						>
							<input
								id="connection-string-radio"
								type="radio"
								checked={useConnectionString}
								onChange={() => setUseConnectionString(true)}
								className="text-[color:var(--color-accent)] focus:ring-[color:var(--color-accent)]"
							/>
							<span
								className="text-sm"
								style={{ color: "var(--color-text-primary)" }}
							>
								Connection String
							</span>
						</label>
					</div>

					{/* Connection Details */}
					{useConnectionString ? (
						<div>
							<FormTextarea
								label="Connection String *"
								value={formData.connection_string}
								onChange={(e) =>
									setFormData({
										...formData,
										connection_string: e.target.value,
									})
								}
								className="font-mono text-sm"
								rows={3}
								placeholder={`e.g., postgresql://user:password@host:port/database`}
								required
							/>
							<p
								className="text-xs"
								style={{ color: "var(--color-text-secondary)" }}
							>
								The full connection string including credentials
							</p>
						</div>
					) : (
						<div className="space-y-4">
							{formData.database_type !== "sqlite" && (
								<>
									<div className="grid grid-cols-2 gap-4">
										<div>
											<FormInput
												label="Host *"
												value={formData.host}
												onChange={(e) =>
													setFormData({ ...formData, host: e.target.value })
												}
												placeholder="localhost"
												required
											/>
										</div>
										<div>
											<FormInput
												label="Port *"
												type="number"
												value={String(formData.port ?? "")}
												onChange={(e) =>
													setFormData({
														...formData,
														port: parseInt(e.target.value) || 0,
													})
												}
												required
											/>
										</div>
									</div>

									<div>
										<FormInput
											label="Database Name *"
											value={formData.database_name}
											onChange={(e) =>
												setFormData({
													...formData,
													database_name: e.target.value,
												})
											}
											placeholder="my_database"
											required
										/>
									</div>

									<div className="grid grid-cols-2 gap-4">
										<div>
											<FormInput
												label="Username *"
												value={formData.username}
												onChange={(e) =>
													setFormData({ ...formData, username: e.target.value })
												}
												placeholder="dbuser"
												required
											/>
										</div>
										<div>
											<label
												htmlFor="password-field"
												className="block text-sm font-medium text-[color:var(--color-text-secondary)] mb-2"
											>
												Password *
											</label>
											<div className="relative">
												<input
													id="password-field"
													type={showPassword ? "text" : "password"}
													value={formData.password}
													onChange={(e) =>
														setFormData({
															...formData,
															password: e.target.value,
														})
													}
													className="w-full px-3 py-2 pr-10 bg-[color:var(--color-bg-secondary)] border border-[color:var(--color-surface-hover)] rounded-lg text-slate-900 focus:ring-2 focus:ring-[color:var(--color-accent)] focus:border-[color:var(--color-border)]"
													placeholder="••••••••"
													required
												/>
												<button
													type="button"
													onClick={() => setShowPassword(!showPassword)}
													className="absolute right-2 top-1/2 -translate-y-1/2 text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text-secondary)]"
												>
													{showPassword ? (
														<EyeOff className="w-4 h-4" />
													) : (
														<Eye className="w-4 h-4" />
													)}
												</button>
											</div>
										</div>
									</div>
								</>
							)}

							{formData.database_type === "sqlite" && (
								<div>
									<FormInput
										label="Database File Path *"
										value={formData.database_name}
										onChange={(e) =>
											setFormData({
												...formData,
												database_name: e.target.value,
											})
										}
										placeholder="/path/to/database.db"
										required
									/>
								</div>
							)}
						</div>
					)}

					{/* Read-only Mode */}
					<div className="flex items-center gap-3">
						<input
							type="checkbox"
							id="read_only"
							checked={formData.read_only ?? true}
							onChange={(e) =>
								setFormData({ ...formData, read_only: e.target.checked })
							}
							className="rounded border-[color:var(--color-surface-hover)] text-[color:var(--color-accent)] focus:ring-[color:var(--color-accent)]"
						/>
						<label
							htmlFor="read_only"
							className="text-sm text-[color:var(--color-text-secondary)]"
						>
							Read-only Connection
						</label>
						<span className="text-xs text-[color:var(--color-text-muted)]">
							(Prevents INSERT, UPDATE, DELETE, and DDL operations)
						</span>
					</div>

					{/* SSL Configuration */}
					{formData.database_type !== "sqlite" && (
						<div className="space-y-4">
							<div className="flex items-center gap-3">
								<input
									type="checkbox"
									id="use_ssl"
									checked={formData.use_ssl}
									onChange={(e) =>
										setFormData({ ...formData, use_ssl: e.target.checked })
									}
									className="rounded border-[color:var(--color-surface-hover)] text-[color:var(--color-accent)] focus:ring-[color:var(--color-accent)]"
								/>
								<label
									htmlFor="use_ssl"
									className="text-sm text-[color:var(--color-text-secondary)]"
								>
									Use SSL/TLS Connection
								</label>
							</div>

							{/* Database-specific SSL Configuration */}
							{formData.use_ssl && (
								<div
									className="ml-6 space-y-3 p-4 rounded-lg"
									style={{
										background: "var(--color-bg-secondary)",
										border: "1px solid var(--color-border)",
									}}
								>
									<h4 className="text-sm font-medium text-white mb-2">
										SSL Configuration
									</h4>

									{/* PostgreSQL SSL Options */}
									{formData.database_type === "postgres" && (
										<div>
											<label
												htmlFor="pg_sslmode"
												className="block text-xs font-medium text-[color:var(--color-text-secondary)] mb-1"
											>
												SSL Mode
											</label>
											<select
												id="pg_sslmode"
												value={formData.ssl_config?.sslmode || "require"}
												onChange={(e) =>
													setFormData({
														...formData,
														ssl_config: {
															...formData.ssl_config,
															sslmode: e.target.value,
														},
													})
												}
												className="w-full px-3 py-2 bg-[color:var(--color-surface)] border border-[color:var(--color-surface-hover)] rounded-lg text-slate-900 text-sm focus:ring-2 focus:ring-[color:var(--color-accent)] focus:border-[color:var(--color-border)]"
											>
												<option value="disable">Disable</option>
												<option value="allow">Allow</option>
												<option value="prefer">Prefer</option>
												<option value="require">Require</option>
												<option value="verify-ca">Verify CA</option>
												<option value="verify-full">Verify Full</option>
											</select>
											<p className="text-xs text-[color:var(--color-text-muted)] mt-1">
												<strong>require</strong>: Encrypt connection
												(recommended for most cases)
											</p>
										</div>
									)}

									{/* MySQL SSL Options */}
									{formData.database_type === "mysql" && (
										<div className="space-y-2">
											<div
												className="p-3 rounded"
												style={{
													background: "rgba(59, 130, 246, 0.1)",
													border: "1px solid rgba(59, 130, 246, 0.3)",
												}}
											>
												<p className="text-xs text-blue-600">
													ℹ️ For remote MySQL servers (like db4free.net), SSL is
													negotiated automatically when enabled. Certificate
													paths are only needed for custom SSL setups.
												</p>
											</div>
										</div>
									)}

									{/* MSSQL SSL Options */}
									{formData.database_type === "mssql" && (
										<div className="space-y-3">
											<div>
												<label
													htmlFor="mssql_driver"
													className="block text-xs font-medium text-[color:var(--color-text-secondary)] mb-1"
												>
													ODBC Driver
												</label>
												<select
													id="mssql_driver"
													value={
														formData.ssl_config?.driver ||
														"{ODBC Driver 17 for SQL Server}"
													}
													onChange={(e) =>
														setFormData({
															...formData,
															ssl_config: {
																...formData.ssl_config,
																driver: e.target.value,
															},
														})
													}
													className="w-full px-3 py-2 bg-[color:var(--color-surface)] border border-[color:var(--color-surface-hover)] rounded-lg text-slate-900 text-sm focus:ring-2 focus:ring-[color:var(--color-accent)] focus:border-[color:var(--color-border)]"
												>
													<option value="{ODBC Driver 17 for SQL Server}">
														ODBC Driver 17 for SQL Server
													</option>
													<option value="{ODBC Driver 18 for SQL Server}">
														ODBC Driver 18 for SQL Server
													</option>
													<option value="{SQL Server}">
														SQL Server (Legacy)
													</option>
												</select>
											</div>
											<div className="flex items-center gap-3">
												<input
													type="checkbox"
													id="mssql_trust_cert"
													checked={
														formData.ssl_config?.trustServerCertificate ===
														"yes"
													}
													onChange={(e) =>
														setFormData({
															...formData,
															ssl_config: {
																...formData.ssl_config,
																trustServerCertificate: e.target.checked
																	? "yes"
																	: "no",
															},
														})
													}
													className="rounded border-[color:var(--color-surface-hover)] text-[color:var(--color-accent)] focus:ring-[color:var(--color-accent)]"
												/>
												<label
													htmlFor="mssql_trust_cert"
													className="text-xs text-[color:var(--color-text-secondary)]"
												>
													Trust Server Certificate (use for self-signed
													certificates)
												</label>
											</div>
										</div>
									)}

									{/* Oracle SSL Options */}
									{formData.database_type === "oracle" && (
										<div>
											<FormInput
												label="Service Name"
												value={formData.ssl_config?.service_name || ""}
												onChange={(e) =>
													setFormData({
														...formData,
														ssl_config: {
															...formData.ssl_config,
															service_name: e.target.value,
														},
													})
												}
												placeholder="ORCL"
											/>
											<p className="text-xs text-[color:var(--color-text-muted)] mt-1">
												Oracle service name (defaults to database name if not
												specified)
											</p>
										</div>
									)}
								</div>
							)}
						</div>
					)}

					{/* Test Result */}
					{testResult && (
						<div
							className={`p-4 rounded-lg flex items-start gap-3 ${
								testResult.success
									? "bg-[#0DA931]/30 border border-[#0DA931]"
									: "bg-red-900/30 border border-red-700"
							}`}
						>
							{testResult.success ? (
								<CheckCircle className="w-5 h-5 text-[#0DA931] flex-shrink-0 mt-0.5" />
							) : (
								<AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
							)}
							<div className="flex-1">
								<p
									className={`text-sm ${testResult.success ? "text-[#0DA931]" : "text-red-400"}`}
								>
									{testResult.message}
								</p>
							</div>
						</div>
					)}

					{/* Actions */}
					<div
						className="flex justify-between pt-4"
						style={{ borderTop: "1px solid var(--color-border)" }}
					>
						<Button
							type="button"
							onClick={handleTestConnection}
							disabled={testing || submitting}
							loading={testing}
							icon={!testing ? <TestTube className="w-4 h-4" /> : undefined}
							variant="secondary"
						>
							{testing ? "Testing..." : "Test Connection"}
						</Button>

						<div className="flex gap-3">
							<Button
								type="button"
								onClick={onClose}
								disabled={submitting}
								variant="ghost"
								data-tutorial="db-cancel-btn"
							>
								Cancel
							</Button>
							<Button
								type="submit"
								disabled={submitting || !formData.name}
								loading={submitting}
							>
								{mode === "create" ? "Add Connection" : "Save Changes"}
							</Button>
						</div>
					</div>
				</form>
			</div>
		</div>
	);
}
