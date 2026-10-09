"use client";

import {
	Activity,
	AlertCircle,
	Check,
	Database,
	Eye,
	EyeOff,
	Loader2,
	Lock,
	Server,
	X,
} from "lucide-react";
import { useCallback, useState } from "react";
import Button from "@/components/ui/Button";
import FormInput from "@/components/ui/FormInput";
import { useAuth } from "@/contexts/AuthContext";
import { useFeatureAccess } from "@/contexts/FeatureAccessContext";
import { useToast } from "@/contexts/ToastContext";
import { configAPI, type EnvironmentConfig } from "@/lib/config-api";

interface DatabaseTabProps {
	config: EnvironmentConfig;
	onUpdate: (section: string, key: string, value: any) => void;
}

export default function DatabaseTab({ config, onUpdate }: DatabaseTabProps) {
	const [testing, setTesting] = useState(false);
	const [testResult, setTestResult] = useState<any>(null);
	const [showPassword, setShowPassword] = useState(false);
	const [localConfig, setLocalConfig] = useState(config.database.postgresql);
	const { showToast } = useToast();
	const { user } = useAuth();
	const { canAccessFeature } = useFeatureAccess();

	const handleTestConnection = async () => {
		setTesting(true);
		setTestResult(null);

		try {
			const result = await configAPI.testConnection("database");
			setTestResult(result);

			if (result.success) {
				showToast("success", "Database connection successful");
			} else {
				showToast("error", `Database connection failed: ${result.error}`);
			}
		} catch (error) {
			setTestResult({ success: false, error: String(error) });
			showToast("error", "Failed to test database connection");
		} finally {
			setTesting(false);
		}
	};

	const handleFieldChange = (field: string, value: string) => {
		setLocalConfig({ ...localConfig, [field]: value });
	};

	const handleFieldBlur = (field: string, value: string) => {
		onUpdate("database.postgresql", field, value);
	};

	const getConnectionString = () => {
		return `postgresql://${localConfig.username}:****@${localConfig.host}:${localConfig.port}/${localConfig.database}?sslmode=${localConfig.sslmode}`;
	};

	// Factory function for field change handlers
	const createFieldChangeHandler = useCallback(
		(field: string) => (e: React.ChangeEvent<HTMLInputElement>) => {
			handleFieldChange(field, e.target.value);
		},
		[],
	);

	// Factory function for field blur handlers
	const createFieldBlurHandler = useCallback(
		(field: string) => (e: React.ChangeEvent<HTMLInputElement>) => {
			handleFieldBlur(field, e.target.value);
		},
		[],
	);

	// Click handler for password visibility toggle
	const handleTogglePassword = useCallback(() => {
		setShowPassword(!showPassword);
	}, [showPassword]);

	// Change handler for SSL mode select
	const handleSSLModeChange = useCallback(
		(e: React.ChangeEvent<HTMLSelectElement>) => {
			handleFieldChange("sslmode", e.target.value);
			handleFieldBlur("sslmode", e.target.value);
		},
		[],
	);

	if (!canAccessFeature("settings.database")) {
		return (
			<div className="flex h-96 flex-col items-center justify-center gap-4 p-6">
				<div className="rounded-full border border-slate-200 bg-white p-6 shadow-sm">
					<Lock className="h-12 w-12 text-orange-600" />
				</div>
				<h3 className="text-xl font-semibold text-slate-900">Admin Access Required</h3>
				<p className="max-w-md text-center text-slate-600">
					This feature is restricted to administrators. Please contact your system administrator to request access.
				</p>
			</div>
		);
	}

	return (
		<div className="p-6">
			{/* Header */}
			<div className="mb-6 flex items-center gap-3">
				<div className="flex items-center justify-center rounded-[4px] border border-orange-200 bg-orange-100 p-2">
			<Database className="h-6 w-6 text-orange-600" />
				</div>
				<div>
					<h2 className="text-xl font-semibold tracking-tight text-slate-900">Database Configuration</h2>
					<p className="mt-1 text-sm text-slate-600">Configure PostgreSQL database connection and settings</p>
				</div>
			</div>

			{/* Connection Status */}
			{testResult && (
				<div
					className={`mb-6 rounded-[4px] border p-4 ${
						testResult.success
							? "border-[#0DA931] bg-white"
							: "border-red-200 bg-white"
					}`}
				>
					<div className="flex items-start gap-3">
						{testResult.success ? (
							<Check className="mt-0.5 h-5 w-5 text-emerald-600" />
						) : (
							<X className="mt-0.5 h-5 w-5 text-red-600" />
						)}
						<div className="flex-1">
							<p className={`font-medium ${testResult.success ? "text-emerald-800" : "text-red-800"}`}>
								{testResult.success ? "Connection Successful" : "Connection Failed"}
							</p>
							{testResult.success ? (
								<div className="mt-2 space-y-1 text-sm text-slate-700">
									<p>Response time: {testResult.response_time_ms}ms</p>
									<p>PostgreSQL Version: {testResult.version?.split(" ")[0]}</p>
									<p>
										pgvector:{" "}
										{testResult.pgvector_enabled
											? `Enabled (v${testResult.pgvector_version})`
											: "Not installed"}
									</p>
								</div>
							) : (
								<p className="mt-1 text-sm text-slate-700">{testResult.error}</p>
							)}
						</div>
					</div>
				</div>
			)}

			{/* PostgreSQL Configuration */}
			<div className="mb-6 rounded-[4px] border border-slate-200 bg-white p-6 shadow-[0_18px_50px_rgba(15,23,42,0.06)] transition-colors hover:border-orange-400">
				<div className="mb-6 flex items-center justify-between">
					<div className="flex items-center gap-3">
						<span className="text-2xl">🐘</span>
						<h3 className="text-lg font-semibold text-slate-900">PostgreSQL</h3>
					</div>
					<div className="flex items-center gap-2">
						<div
							className={`h-2 w-2 rounded-full ${
								localConfig.status === "connected" ? "animate-pulse bg-emerald-500" : "bg-slate-400"
							}`}
						/>
						<span className="text-sm text-slate-600">
							{localConfig.status === "connected" ? "Connected" : "Not Connected"}
						</span>
					</div>
				</div>

				<div className="grid gap-4 md:grid-cols-2">
					{/* Host */}
					<div>
						<label htmlFor="db-host" className="mb-2 block text-sm font-medium text-slate-900">
							Host
						</label>
						<FormInput
							id="db-host"
							value={localConfig.host}
							onChange={createFieldChangeHandler("host")}
							onBlur={createFieldBlurHandler("host")}
							placeholder="localhost"
							className="!rounded-[4px] !border-slate-200 !bg-white !text-slate-900 placeholder:!text-slate-400 hover:!border-orange-400 focus:!border-orange-500 focus:!ring-orange-500/15"
						/>
					</div>

					{/* Port */}
					<div>
						<label htmlFor="db-port" className="mb-2 block text-sm font-medium text-slate-900">
							Port
						</label>
						<FormInput
							id="db-port"
							type="number"
							value={String(localConfig.port || 5432)}
							onChange={createFieldChangeHandler("port")}
							onBlur={createFieldBlurHandler("port")}
							placeholder="5432"
							className="!rounded-[4px] !border-slate-200 !bg-white !text-slate-900 placeholder:!text-slate-400 hover:!border-orange-400 focus:!border-orange-500 focus:!ring-orange-500/15"
						/>
					</div>

					{/* Database */}
					<div>
						<label htmlFor="db-name" className="mb-2 block text-sm font-medium text-slate-900">
							Database
						</label>
						<FormInput
							id="db-name"
							value={localConfig.database}
							onChange={createFieldChangeHandler("database")}
							onBlur={createFieldBlurHandler("database")}
							placeholder="langgraph"
							className="!rounded-[4px] !border-slate-200 !bg-white !text-slate-900 placeholder:!text-slate-400 hover:!border-orange-400 focus:!border-orange-500 focus:!ring-orange-500/15"
						/>
					</div>

					{/* Username */}
					<div>
						<label htmlFor="db-username" className="mb-2 block text-sm font-medium text-slate-900">
							Username
						</label>
						<FormInput
							id="db-username"
							value={localConfig.username}
							onChange={createFieldChangeHandler("username")}
							onBlur={createFieldBlurHandler("username")}
							placeholder="postgres"
							className="!rounded-[4px] !border-slate-200 !bg-white !text-slate-900 placeholder:!text-slate-400 hover:!border-orange-400 focus:!border-orange-500 focus:!ring-orange-500/15"
						/>
					</div>

					{/* Password */}
					<div>
						<label htmlFor="db-password" className="mb-2 block text-sm font-medium text-slate-900">
							Password
						</label>
						<div className="relative">
							<FormInput
								id="db-password"
								type={showPassword ? "text" : "password"}
								value={localConfig.password || ""}
								onChange={createFieldChangeHandler("password")}
								onBlur={createFieldBlurHandler("password")}
								placeholder="Enter password"
								className="!rounded-[4px] !border-slate-200 !bg-white pr-10 !text-slate-900 placeholder:!text-slate-400 hover:!border-orange-400 focus:!border-orange-500 focus:!ring-orange-500/15"
							/>
							<button
								type="button"
								onClick={handleTogglePassword}
								className="absolute right-2 top-2.5 text-slate-500 transition-colors hover:text-slate-900"
								aria-label={showPassword ? "Hide password" : "Show password"}
							>
								{showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
							</button>
						</div>
					</div>

					{/* SSL Mode */}
					<div>
						<label htmlFor="db-sslmode" className="mb-2 block text-sm font-medium text-slate-700">
							SSL Mode
						</label>
						<select
							id="db-sslmode"
							value={localConfig.sslmode}
							onChange={handleSSLModeChange}
							className="w-full rounded-[4px] border border-slate-200 bg-white px-4 py-2 text-slate-900 transition-colors hover:border-orange-400 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/15"
						>
							<option value="disable">Disable</option>
							<option value="allow">Allow</option>
							<option value="prefer">Prefer</option>
							<option value="require">Require</option>
							<option value="verify-ca">Verify CA</option>
							<option value="verify-full">Verify Full</option>
						</select>
					</div>
				</div>

				{/* Connection String */}
				<div className="mt-6 rounded-[4px] border border-slate-200 bg-slate-50 p-3">
					<p className="text-xs text-slate-600">Connection String</p>
					<code className="text-xs text-slate-900">{getConnectionString()}</code>
				</div>

				{/* Test Connection Button */}
				<Button
					onClick={handleTestConnection}
					disabled={testing}
					loading={testing}
					icon={!testing ? <Activity className="h-4 w-4" /> : undefined}
					className="mt-6 w-full shadow-[0_8px_20px_rgba(15,23,42,0.12)]"
				>
					{testing ? "Testing Connection..." : "Test Connection"}
				</Button>
			</div>

			{/* Connection Pool Settings */}
			<div className="mb-6 rounded-[4px] border border-slate-200 bg-white p-6 shadow-[0_18px_50px_rgba(15,23,42,0.06)] transition-colors hover:border-orange-400">
				<h3 className="mb-4 text-lg font-semibold text-slate-900">Connection Pool</h3>
				<div className="grid gap-4 md:grid-cols-2">
					<div>
						<label htmlFor="db-pool-size" className="mb-2 block text-sm font-medium text-slate-900">
							Pool Size
						</label>
						<FormInput
							id="db-pool-size"
							type="number"
							value={String(localConfig.pool_size || 10)}
							onChange={createFieldChangeHandler("pool_size")}
							onBlur={createFieldBlurHandler("pool_size")}
							className="!rounded-[4px] !border-slate-200 !bg-white !text-slate-900 placeholder:!text-slate-400 hover:!border-orange-400 focus:!border-orange-500 focus:!ring-orange-500/15"
						/>
					</div>
					<div>
						<label htmlFor="db-max-overflow" className="mb-2 block text-sm font-medium text-slate-900">
							Max Overflow
						</label>
						<FormInput
							id="db-max-overflow"
							type="number"
							value={String(localConfig.max_overflow || 20)}
							onChange={createFieldChangeHandler("max_overflow")}
							onBlur={createFieldBlurHandler("max_overflow")}
							className="!rounded-[4px] !border-slate-200 !bg-white !text-slate-900 placeholder:!text-slate-400 hover:!border-orange-400 focus:!border-orange-500 focus:!ring-orange-500/15"
						/>
					</div>
				</div>
			</div>

			{/* pgvector Settings */}
			<div className="mb-6 rounded-[4px] border border-slate-200 bg-white p-6 shadow-[0_18px_50px_rgba(15,23,42,0.06)] transition-colors hover:border-orange-400">
				<div className="mb-4 flex items-center gap-3">
					<Server className="h-5 w-5 text-violet-600" />
					<h3 className="text-lg font-semibold text-slate-900">Vector Database (pgvector)</h3>
				</div>
				<div className="space-y-3">
					<div className="flex items-center justify-between rounded-[4px] border border-slate-200 bg-slate-50 p-3">
						<span className="text-sm text-slate-700">Status</span>
						<span
							className={`text-sm font-medium ${
								config.database.pgvector?.enabled ? "text-emerald-700" : "text-slate-500"
							}`}
						>
							{config.database.pgvector?.enabled ? "Enabled" : "Disabled"}
						</span>
					</div>
					<div className="flex items-center justify-between rounded-[4px] border border-slate-200 bg-slate-50 p-3">
						<span className="text-sm text-slate-700">Dimensions</span>
						<span className="text-sm font-medium text-slate-900">
							{config.database.pgvector?.dimensions || 1536}
						</span>
					</div>
					<div className="flex items-center justify-between rounded-[4px] border border-slate-200 bg-slate-50 p-3">
						<span className="text-sm text-slate-700">Index Type</span>
						<span className="text-sm font-medium text-slate-900">
							{config.database.pgvector?.index_type || "ivfflat"}
						</span>
					</div>
				</div>
			</div>

			{/* Future Databases */}
			<div className="rounded-[4px] border border-slate-200 bg-white p-6 shadow-[0_18px_50px_rgba(15,23,42,0.06)] transition-colors hover:border-orange-400">
				<h3 className="mb-4 text-lg font-semibold text-slate-900">Coming Soon</h3>
				<div className="grid gap-4 md:grid-cols-3">
					{Object.entries(config.database.future_databases || {}).map(
						([name, info]: [string, any]) => (
							<div
								key={name}
								className="rounded-[4px] border border-slate-200 bg-slate-50 p-4 opacity-70"
							>
								<div className="mb-2 flex items-center gap-2">
									<Lock className="h-4 w-4 text-slate-500" />
									<span className="text-sm font-medium capitalize text-slate-700">
										{name}
									</span>
								</div>
								<p className="text-xs text-slate-600">Available in future update</p>
							</div>
						),
					)}
				</div>
			</div>
		</div>
	);
}
