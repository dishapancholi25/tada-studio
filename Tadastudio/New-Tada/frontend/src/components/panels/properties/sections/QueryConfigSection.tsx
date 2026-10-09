"use client";

import type { ComponentProps } from "react";
import { Lock, Shield } from "lucide-react";
import Checkbox from "@/components/ui/Checkbox";
import InfoTooltip from "@/components/ui/InfoTooltipPortal";
import Toggle from "@/components/ui/Toggle";

interface QueryConfigSectionProps {
	enableReadOnly: boolean;
	onEnableReadOnlyChange: (enabled: boolean) => void;
	allowedOperations: string[];
	onAllowedOperationsChange: (operations: string[]) => void;
}

const DML_OPERATIONS = [
	{ name: "SELECT", variant: "green", description: "Read data from tables" },
	{ name: "INSERT", variant: "plum", description: "Add new records" },
	{ name: "UPDATE", variant: "purple", description: "Modify existing records" },
	{ name: "DELETE", variant: "default", description: "Remove records" },
] as const;

const DDL_OPERATIONS = [
	{ name: "CREATE", variant: "blue", description: "Create new tables or objects" },
	{ name: "ALTER", variant: "blue", description: "Modify table structure" },
	{ name: "DROP", variant: "amber", description: "Delete tables or objects" },
	{
		name: "TRUNCATE",
		variant: "amber",
		description: "Remove all rows from a table",
	},
] as const;

export default function QueryConfigSection({
	enableReadOnly,
	onEnableReadOnlyChange,
	allowedOperations,
	onAllowedOperationsChange,
}: QueryConfigSectionProps) {
	const handleToggleOperation = (operation: string, checked: boolean) => {
		if (checked) {
			if (!allowedOperations.includes(operation)) {
				onAllowedOperationsChange([...allowedOperations, operation]);
			}
		} else {
			onAllowedOperationsChange(
				allowedOperations.filter((op) => op !== operation),
			);
		}
	};

	const handleReadOnlyToggle = (checked: boolean) => {
		onEnableReadOnlyChange(checked);
		if (checked) {
			onAllowedOperationsChange(["SELECT"]);
		}
	};

	return (
		<div className="space-y-6">
			<div className="rounded-[4px] border border-gray-200 bg-white p-6 shadow-sm">
				<div className="flex flex-wrap items-start justify-between gap-4 border-b border-gray-200 pb-5">
					<div className="flex min-w-0 items-start gap-3">
						<div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[4px] border border-gray-200 bg-white shadow-sm">
							<Shield className="h-5 w-5 text-orange-600" aria-hidden />
						</div>
						<div className="min-w-0">
							<h3 className="text-lg font-semibold text-gray-900">
								Query Configuration
							</h3>
							<p className="text-sm text-gray-600">
								Control allowed database operations
							</p>
						</div>
					</div>
				</div>

				<div className="mt-6 space-y-6">
					<div className="rounded-[4px] border border-gray-200 bg-slate-50 p-5">
						<div className="flex flex-wrap items-center justify-between gap-4">
							<div className="flex min-w-0 flex-1 items-start gap-3">
								<div className="rounded-[4px] border border-gray-200 bg-white p-2.5 shadow-sm">
									<Lock className="h-5 w-5 text-blue-700" />
								</div>
								<div className="min-w-0 flex-1">
									<div className="flex items-center gap-2">
										<h4 className="text-base font-semibold text-gray-900">
											Read-only Mode
										</h4>
										<InfoTooltip text="When enabled, only SELECT queries are allowed. All other operations will be locked." />
									</div>
									<p className="mt-1 text-sm text-gray-600">
										Restrict to SELECT queries only for safe, read-only database
										access
									</p>
								</div>
							</div>
							<Toggle
								checked={enableReadOnly}
								onChange={handleReadOnlyToggle}
								size="md"
							/>
						</div>
					</div>

					<div>
						<div className="mb-4 flex items-center gap-2">
							<label className="text-sm font-semibold text-gray-900">
								Allowed Operations
							</label>
							<InfoTooltip text="Select which SQL operations agents can perform on the database" />
						</div>

						<div className="mb-2">
							<span className="mb-2 block text-xs font-medium capitalize tracking-wider text-gray-600">
								Data Manipulation (DML)
							</span>
							<div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
								{DML_OPERATIONS.map((op) => {
									const isSelected = allowedOperations.includes(op.name);
									const isDisabled = enableReadOnly && op.name !== "SELECT";

									return (
										<Checkbox
											key={op.name}
											checked={isSelected}
											onChange={(checked) =>
												handleToggleOperation(op.name, checked)
											}
											disabled={isDisabled}
											variant={
												op.variant as ComponentProps<
													typeof Checkbox
												>["variant"]
											}
											size="lg"
											className={`h-full min-h-[5rem] !items-start rounded-[4px] border px-4 py-4 transition-colors duration-200 ${
												isSelected
													? "border-orange-500 bg-white shadow-sm"
													: "border-transparent bg-white hover:border-orange-400 hover:bg-slate-50"
											} ${isDisabled ? "cursor-not-allowed opacity-50" : ""}`}
											label={
												<div className="flex w-full flex-col gap-1.5">
													<div className="flex items-center justify-between gap-2">
														<span className="text-base font-bold tracking-wide text-gray-900">
															{op.name}
														</span>
														{isDisabled && (
															<div className="flex items-center gap-1.5 rounded-full border border-gray-200 bg-slate-100 px-2 py-0.5">
																<Lock className="h-3 w-3 text-gray-600" />
																<span className="text-xs font-semibold capitalize text-gray-700">
																	Locked
																</span>
															</div>
														)}
													</div>
													<p className="text-xs text-gray-600">{op.description}</p>
												</div>
											}
										/>
									);
								})}
							</div>
						</div>

						<div className="mt-5">
							<div className="mb-2 flex items-center gap-2">
								<span className="block text-xs font-medium capitalize tracking-wider text-gray-600">
									Schema Changes (DDL)
								</span>
								<InfoTooltip text="DDL operations modify database structure. Use with caution as these changes can be irreversible." />
							</div>
							<div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
								{DDL_OPERATIONS.map((op) => {
									const isSelected = allowedOperations.includes(op.name);
									const isDisabled = enableReadOnly;

									return (
										<Checkbox
											key={op.name}
											checked={isSelected}
											onChange={(checked) =>
												handleToggleOperation(op.name, checked)
											}
											disabled={isDisabled}
											variant={
												op.variant as ComponentProps<
													typeof Checkbox
												>["variant"]
											}
											size="lg"
											className={`h-full min-h-[5rem] !items-start rounded-[4px] border px-4 py-4 transition-colors duration-200 ${
												isSelected
													? "border-amber-500 bg-white shadow-sm"
													: "border-transparent bg-white hover:border-amber-400 hover:bg-slate-50"
											} ${isDisabled ? "cursor-not-allowed opacity-50" : ""}`}
											label={
												<div className="flex w-full flex-col gap-1.5">
													<div className="flex items-center justify-between gap-2">
														<span className="text-base font-bold tracking-wide text-gray-900">
															{op.name}
														</span>
														{isDisabled && (
															<div className="flex items-center gap-1.5 rounded-full border border-gray-200 bg-slate-100 px-2 py-0.5">
																<Lock className="h-3 w-3 text-gray-600" />
																<span className="text-xs font-semibold capitalize text-gray-700">
																	Locked
																</span>
															</div>
														)}
													</div>
													<p className="text-xs text-gray-600">{op.description}</p>
												</div>
											}
										/>
									);
								})}
							</div>
						</div>

						{allowedOperations.length === 0 && (
							<div className="mt-3 rounded-[4px] border border-amber-300 bg-white p-3 shadow-sm">
								<p className="text-sm text-amber-950">
									At least one operation must be selected for the database query to
									function.
								</p>
							</div>
						)}

						{enableReadOnly && (
							<div className="mt-3 rounded-[4px] border border-orange-400 bg-white p-3 shadow-sm">
								<div className="flex items-start gap-2">
									<Shield className="mt-0.5 h-4 w-4 shrink-0 text-orange-600" />
									<p className="text-sm text-gray-800">
										Read-only mode is active. Only SELECT queries are permitted for
										maximum safety.
									</p>
								</div>
							</div>
						)}
					</div>
				</div>
			</div>
		</div>
	);
}
