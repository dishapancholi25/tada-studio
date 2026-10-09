"use client";

import { Plus, Trash2, Variable } from "lucide-react";
import InfoTooltip from "@/components/ui/InfoTooltipPortal";
import type { InputVariableMapping } from "@/types/nodes";

interface CodeVariablesSectionProps {
	variables: InputVariableMapping[];
	onVariablesChange: (variables: InputVariableMapping[]) => void;
}

export default function CodeVariablesSection({
	variables,
	onVariablesChange,
}: CodeVariablesSectionProps) {
	const handleAddVariable = () => {
		const newVar: InputVariableMapping = {
			variable_name: `var_${(variables?.length || 0) + 1}`,
			source_mode: "previous",
			source_node_id: "",
			source_field_path: "",
			static_value: "",
			default_value: "",
		};
		onVariablesChange([...(variables || []), newVar]);
	};

	const handleUpdateVariable = (
		index: number,
		field: keyof InputVariableMapping,
		value: any
	) => {
		const updated = variables.map((v, i) =>
			i === index ? { ...v, [field]: value } : v
		);
		onVariablesChange(updated);
	};

	const handleRemoveVariable = (index: number) => {
		onVariablesChange(variables.filter((_, i) => i !== index));
	};

	return (
		<div className="space-y-6">
			<div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
				<div className="flex items-start justify-between gap-4 border-b border-slate-200 pb-5">
					<div className="flex items-center gap-3">
						<div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-emerald-200 bg-emerald-100 text-emerald-600">
							<Variable className="h-6 w-6" />
						</div>
						<div>
							<h3 className="text-xl font-semibold text-slate-900">
								Input Variables
							</h3>
							<p className="text-sm text-slate-600">
								Map data from other nodes into your code
							</p>
						</div>
					</div>
					<button
						type="button"
						onClick={handleAddVariable}
						className="flex items-center gap-2 rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-700 transition-colors hover:border-emerald-400 hover:bg-emerald-100"
					>
						<Plus className="h-4 w-4" />
						Add Variable
					</button>
				</div>

				<div className="mt-6 space-y-4">
					{(!variables || variables.length === 0) ? (
						<div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center">
							<Variable className="mx-auto h-10 w-10 text-slate-400" />
							<p className="mt-3 text-sm font-medium text-slate-700">
								No input variables configured
							</p>
							<p className="mt-1 text-xs text-slate-500">
								Add variables to pass data from other nodes into your code
							</p>
							<button
								type="button"
								onClick={handleAddVariable}
								className="mt-4 inline-flex items-center gap-2 rounded-lg border border-emerald-300 bg-white px-4 py-2 text-sm font-medium text-emerald-700 transition-colors hover:bg-emerald-50"
							>
								<Plus className="h-4 w-4" />
								Add First Variable
							</button>
						</div>
					) : (
						variables.map((variable, index) => (
							<div
								key={index}
								className="rounded-xl border border-slate-200 bg-slate-50 p-4 transition-colors hover:border-emerald-200"
							>
								<div className="flex items-center justify-between mb-4">
									<span className="flex items-center gap-2 text-sm font-semibold text-slate-800">
										<span className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-100 text-xs font-bold text-emerald-700">
											{index + 1}
										</span>
										Variable
									</span>
									<button
										type="button"
										onClick={() => handleRemoveVariable(index)}
										className="rounded-lg p-2 text-red-600 transition-colors hover:bg-red-50"
									>
										<Trash2 className="h-4 w-4" />
									</button>
								</div>

								<div className="grid grid-cols-1 gap-4 md:grid-cols-2">
									<div>
										<div className="mb-2 flex items-center gap-2">
											<label className="text-sm font-medium text-slate-700">
												Variable Name
											</label>
											<InfoTooltip text="Name used to access this variable in your code" />
										</div>
										<input
											type="text"
											value={variable.variable_name || ""}
											onChange={(e) =>
												handleUpdateVariable(index, "variable_name", e.target.value)
											}
											placeholder="my_var"
											className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 transition-colors focus:border-emerald-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400/40"
										/>
									</div>

									<div>
										<div className="mb-2 flex items-center gap-2">
											<label className="text-sm font-medium text-slate-700">
												Source
											</label>
											<InfoTooltip text="Where to get the value from" />
										</div>
										<select
											value={variable.source_mode || "previous"}
											onChange={(e) =>
												handleUpdateVariable(index, "source_mode", e.target.value)
											}
											className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 transition-colors focus:border-emerald-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400/40"
										>
											<option value="previous">Previous Node Output</option>
											<option value="specific">Specific Node</option>
											<option value="static">Static Value</option>
											<option value="current_item">Current Item (For Each)</option>
										</select>
									</div>
								</div>

								{variable.source_mode === "specific" && (
									<div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
										<div>
											<label className="mb-2 block text-sm font-medium text-slate-700">
												Source Node ID
											</label>
											<input
												type="text"
												value={variable.source_node_id || ""}
												onChange={(e) =>
													handleUpdateVariable(index, "source_node_id", e.target.value)
												}
												placeholder="node_id"
												className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 transition-colors focus:border-emerald-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400/40"
											/>
										</div>
										<div>
											<label className="mb-2 block text-sm font-medium text-slate-700">
												Field Path
											</label>
											<input
												type="text"
												value={variable.source_field_path || ""}
												onChange={(e) =>
													handleUpdateVariable(index, "source_field_path", e.target.value)
												}
												placeholder="fields.data"
												className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 transition-colors focus:border-emerald-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400/40"
											/>
										</div>
									</div>
								)}

								{variable.source_mode === "static" && (
									<div className="mt-4">
										<label className="mb-2 block text-sm font-medium text-slate-700">
											Static Value
										</label>
										<input
											type="text"
											value={
												typeof variable.static_value === "string"
													? variable.static_value
													: JSON.stringify(variable.static_value || "")
											}
											onChange={(e) =>
												handleUpdateVariable(index, "static_value", e.target.value)
											}
											placeholder="Value or JSON"
											className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 transition-colors focus:border-emerald-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400/40"
										/>
									</div>
								)}

								<div className="mt-4">
									<div className="mb-2 flex items-center gap-2">
										<label className="text-sm font-medium text-slate-700">
											Default Value
										</label>
										<InfoTooltip text="Used if the source value is empty or undefined" />
									</div>
									<input
										type="text"
										value={
											typeof variable.default_value === "string"
												? variable.default_value
												: JSON.stringify(variable.default_value || "")
										}
										onChange={(e) =>
											handleUpdateVariable(index, "default_value", e.target.value)
										}
										placeholder="Fallback if source is empty"
										className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 transition-colors focus:border-emerald-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400/40"
									/>
								</div>
							</div>
						))
					)}
				</div>
			</div>
		</div>
	);
}
