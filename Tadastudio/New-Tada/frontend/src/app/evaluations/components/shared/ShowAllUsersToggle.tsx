"use client";

import { useAuth } from "@/contexts/AuthContext";

export default function ShowAllUsersToggle({
	enabled,
	onToggle,
}: {
	enabled: boolean;
	onToggle: (value: boolean) => void;
}) {
	const { user } = useAuth();

	if (!user?.is_admin) return null;

	return (
		<label
			className="flex cursor-pointer items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-600 transition-all hover:border-orange-400 hover:bg-white hover:text-slate-900"
			title="Show datasets and runs from all users"
		>
			<div className="relative">
				<input
					type="checkbox"
					checked={enabled}
					onChange={(e) => onToggle(e.target.checked)}
					className="sr-only"
				/>
				<div
					className={`h-5 w-9 rounded-full transition-colors ${
						enabled
							? "bg-orange-500"
							: "bg-slate-200"
					}`}
				/>
				<div
					className={`absolute left-0.5 top-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform ${
						enabled ? "translate-x-4" : ""
					}`}
				/>
			</div>
			<span className="whitespace-nowrap">Show All Users</span>
		</label>
	);
}
