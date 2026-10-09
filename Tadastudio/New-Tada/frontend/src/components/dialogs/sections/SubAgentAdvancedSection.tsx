"use client";

import { Cpu, Database as Memory, Settings, Zap } from "lucide-react";

export default function SubAgentAdvancedSection() {
	return (
		<div className="space-y-6">
			<div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
				<div className="flex items-start justify-between gap-4 border-b border-slate-200 pb-5">
					<div className="flex items-center gap-3">
						<div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-orange-200 bg-orange-100 text-orange-600">
							<Settings className="h-6 w-6" />
						</div>
						<div>
							<h3 className="text-xl font-semibold text-slate-900">
								Advanced Configuration
							</h3>
							<p className="text-sm text-slate-600">
								Future settings for LLM and memory
							</p>
						</div>
					</div>
				</div>

				<div className="mt-6">
					<div className="rounded-xl border border-slate-200 bg-slate-50 p-8 text-center">
						<div className="mb-4 flex justify-center gap-6">
							<Cpu className="h-8 w-8 text-blue-600" />
							<Memory className="h-8 w-8 text-emerald-600" />
							<Zap className="h-8 w-8 text-amber-600" />
						</div>
						<h4 className="mb-2 text-base font-semibold text-slate-900">
							Advanced Settings Coming Soon
						</h4>
						<p className="mx-auto max-w-md text-sm text-slate-600">
							Future releases will include model selection, temperature control,
							memory configuration, and other advanced agent settings.
						</p>
					</div>

					<div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
						<div className="rounded-lg border border-slate-200 border-dashed bg-white p-4 opacity-90 transition-colors hover:border-orange-200">
							<div className="mb-2 flex items-center gap-2">
								<Cpu className="h-4 w-4 text-blue-600" />
								<span className="text-sm font-medium text-slate-800">
									Model Selection
								</span>
							</div>
							<p className="text-xs text-slate-600">
								Choose LLM model and parameters
							</p>
						</div>

						<div className="rounded-lg border border-slate-200 border-dashed bg-white p-4 opacity-90 transition-colors hover:border-orange-200">
							<div className="mb-2 flex items-center gap-2">
								<Memory className="h-4 w-4 text-emerald-600" />
								<span className="text-sm font-medium text-slate-800">
									Memory Configuration
								</span>
							</div>
							<p className="text-xs text-slate-600">
								Enable and configure agent memory
							</p>
						</div>

						<div className="rounded-lg border border-slate-200 border-dashed bg-white p-4 opacity-90 transition-colors hover:border-orange-200">
							<div className="mb-2 flex items-center gap-2">
								<Zap className="h-4 w-4 text-amber-600" />
								<span className="text-sm font-medium text-slate-800">
									Performance Tuning
								</span>
							</div>
							<p className="text-xs text-slate-600">
								Timeout, max tokens, and more
							</p>
						</div>

						<div className="rounded-lg border border-slate-200 border-dashed bg-white p-4 opacity-90 transition-colors hover:border-orange-200">
							<div className="mb-2 flex items-center gap-2">
								<Settings className="h-4 w-4 text-slate-700" />
								<span className="text-sm font-medium text-slate-800">
									Behavior Options
								</span>
							</div>
							<p className="text-xs text-slate-600">
								Customize agent behavior patterns
							</p>
						</div>
					</div>
				</div>
			</div>
		</div>
	);
}
