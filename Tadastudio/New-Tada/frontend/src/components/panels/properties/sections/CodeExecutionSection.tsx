"use client";

import { AlertTriangle, HardDrive, Network, Play, Settings, Terminal } from "lucide-react";
import InfoTooltip from "@/components/ui/InfoTooltipPortal";
import NumberInput from "@/components/ui/NumberInput";

interface CodeExecutionSectionProps {
	outputVariable: string;
	onOutputVariableChange: (value: string) => void;
	timeoutSeconds: number;
	onTimeoutSecondsChange: (value: number) => void;
	memoryLimitMb: number;
	onMemoryLimitMbChange: (value: number) => void;
	workingDirectory: string;
	onWorkingDirectoryChange: (value: string) => void;
	allowNetwork: boolean;
	onAllowNetworkChange: (value: boolean) => void;
	allowFilesystem: boolean;
	onAllowFilesystemChange: (value: boolean) => void;
	allowSubprocess: boolean;
	onAllowSubprocessChange: (value: boolean) => void;
	captureStdout: boolean;
	onCaptureStdoutChange: (value: boolean) => void;
	captureStderr: boolean;
	onCaptureStderrChange: (value: boolean) => void;
}

export default function CodeExecutionSection({
	outputVariable,
	onOutputVariableChange,
	timeoutSeconds,
	onTimeoutSecondsChange,
	memoryLimitMb,
	onMemoryLimitMbChange,
	workingDirectory,
	onWorkingDirectoryChange,
	allowNetwork,
	onAllowNetworkChange,
	allowFilesystem,
	onAllowFilesystemChange,
	allowSubprocess,
	onAllowSubprocessChange,
	captureStdout,
	onCaptureStdoutChange,
	captureStderr,
	onCaptureStderrChange,
}: CodeExecutionSectionProps) {
	return (
		<div className="space-y-6">
			{/* Execution Settings */}
			<div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
				<div className="flex items-start justify-between gap-4 border-b border-slate-200 pb-5">
					<div className="flex items-center gap-3">
						<div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-emerald-200 bg-emerald-100 text-emerald-600">
							<Play className="h-6 w-6" />
						</div>
						<div>
							<h3 className="text-xl font-semibold text-slate-900">
								Execution Settings
							</h3>
							<p className="text-sm text-slate-600">
								Configure how your code runs
							</p>
						</div>
					</div>
				</div>

				<div className="mt-6 space-y-6">
					<div className="grid grid-cols-1 gap-6 md:grid-cols-2">
						<div>
							<div className="mb-2 flex items-center gap-2">
								<label className="text-sm font-semibold text-slate-800">
									Output Variable
								</label>
								<InfoTooltip text="The variable name whose value will be captured as the node output" />
							</div>
							<input
								type="text"
								value={outputVariable}
								onChange={(e) => onOutputVariableChange(e.target.value)}
								placeholder="result"
								className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-900 transition-colors focus:border-emerald-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400/40"
							/>
							<p className="mt-1.5 text-xs text-slate-500">
								Set this variable in your code to return a value
							</p>
						</div>

						<div>
							<div className="mb-2 flex items-center gap-2">
								<label className="text-sm font-semibold text-slate-800">
									Timeout
								</label>
								<InfoTooltip text="Maximum execution time before the code is terminated" />
							</div>
							<NumberInput
								value={timeoutSeconds}
								onChange={onTimeoutSecondsChange}
								min={5}
								max={300}
								step={5}
								label=""
								description=""
							/>
							<p className="mt-1.5 text-xs text-slate-500">
								{timeoutSeconds} seconds (5-300s range)
							</p>
						</div>
					</div>

					<div className="grid grid-cols-1 gap-6 md:grid-cols-2">
						<div>
							<div className="mb-2 flex items-center gap-2">
								<label className="text-sm font-semibold text-slate-800">
									Memory Limit
								</label>
								<InfoTooltip text="Maximum memory the code can use" />
							</div>
							<NumberInput
								value={memoryLimitMb}
								onChange={onMemoryLimitMbChange}
								min={64}
								max={1024}
								step={64}
								label=""
								description=""
							/>
							<p className="mt-1.5 text-xs text-slate-500">
								{memoryLimitMb} MB (64-1024 MB range)
							</p>
						</div>

						<div>
							<div className="mb-2 flex items-center gap-2">
								<label className="text-sm font-semibold text-slate-800">
									Working Directory
								</label>
								<InfoTooltip text="Directory where the code will run. Leave empty for system temp." />
							</div>
							<input
								type="text"
								value={workingDirectory}
								onChange={(e) => onWorkingDirectoryChange(e.target.value)}
								placeholder="(System temp directory)"
								className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-900 transition-colors focus:border-emerald-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400/40"
							/>
						</div>
					</div>
				</div>
			</div>

			{/* Permissions & Advanced */}
			<div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
				<div className="flex items-start justify-between gap-4 border-b border-slate-200 pb-5">
					<div className="flex items-center gap-3">
						<div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-emerald-200 bg-emerald-100 text-emerald-600">
							<Settings className="h-6 w-6" />
						</div>
						<div>
							<h3 className="text-xl font-semibold text-slate-900">
								Permissions & Capture
							</h3>
							<p className="text-sm text-slate-600">
								Control what the code can access
							</p>
						</div>
					</div>
				</div>

				<div className="mt-6 space-y-6">
					<div>
						<label className="mb-3 block text-sm font-semibold text-slate-800">
							Sandbox Permissions
						</label>
						<div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
							<label className="flex cursor-pointer items-center gap-3 rounded-xl border border-slate-200 bg-white p-4 transition-all hover:border-emerald-300 hover:bg-emerald-50/50">
								<input
									type="checkbox"
									checked={allowNetwork}
									onChange={(e) => onAllowNetworkChange(e.target.checked)}
									className="h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
								/>
								<div className="flex items-center gap-2">
									<Network className="h-4 w-4 text-slate-600" />
									<span className="text-sm font-medium text-slate-700">Network</span>
								</div>
							</label>

							<label className="flex cursor-pointer items-center gap-3 rounded-xl border border-slate-200 bg-white p-4 transition-all hover:border-emerald-300 hover:bg-emerald-50/50">
								<input
									type="checkbox"
									checked={allowFilesystem}
									onChange={(e) => onAllowFilesystemChange(e.target.checked)}
									className="h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
								/>
								<div className="flex items-center gap-2">
									<HardDrive className="h-4 w-4 text-slate-600" />
									<span className="text-sm font-medium text-slate-700">Filesystem</span>
								</div>
							</label>

							<label className="flex cursor-pointer items-center gap-3 rounded-xl border border-slate-200 bg-white p-4 transition-all hover:border-emerald-300 hover:bg-emerald-50/50">
								<input
									type="checkbox"
									checked={allowSubprocess}
									onChange={(e) => onAllowSubprocessChange(e.target.checked)}
									className="h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
								/>
								<div className="flex items-center gap-2">
									<Terminal className="h-4 w-4 text-slate-600" />
									<span className="text-sm font-medium text-slate-700">Subprocess</span>
								</div>
							</label>
						</div>
					</div>

					<div>
						<label className="mb-3 block text-sm font-semibold text-slate-800">
							Output Capture
						</label>
						<div className="flex flex-wrap gap-4">
							<label className="flex cursor-pointer items-center gap-2.5 text-sm text-slate-700">
								<input
									type="checkbox"
									checked={captureStdout}
									onChange={(e) => onCaptureStdoutChange(e.target.checked)}
									className="h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
								/>
								<span className="font-medium">Capture stdout</span>
							</label>

							<label className="flex cursor-pointer items-center gap-2.5 text-sm text-slate-700">
								<input
									type="checkbox"
									checked={captureStderr}
									onChange={(e) => onCaptureStderrChange(e.target.checked)}
									className="h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
								/>
								<span className="font-medium">Capture stderr</span>
							</label>
						</div>
					</div>
				</div>
			</div>

			{/* Security Warning */}
			<div className="flex items-start gap-3 rounded-2xl border border-amber-300 bg-amber-50 p-5">
				<AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0 text-amber-600" />
				<div className="text-sm text-amber-900">
					<p className="font-semibold">Security Note</p>
					<p className="mt-1 text-amber-800">
						Code runs in a subprocess with configurable permissions. Be cautious with
						untrusted code. The execution environment has access to the system
						Python/Node.js installation.
					</p>
				</div>
			</div>
		</div>
	);
}
