import { MessageSquare } from "lucide-react";
import type React from "react";
import { useCallback } from "react";
import type { ConversationMessage } from "@/types/api";

interface ExecutionTabNavigationProps {
	activeTab: "io" | "history";
	onTabChange: (tab: "io" | "history") => void;
	conversationHistory?: ConversationMessage[];
}

const ExecutionTabNavigation: React.FC<ExecutionTabNavigationProps> = ({
	activeTab,
	onTabChange,
	conversationHistory,
}) => {
	const handleIOTabClick = useCallback(() => {
		onTabChange("io");
	}, [onTabChange]);

	const handleHistoryTabClick = useCallback(() => {
		onTabChange("history");
	}, [onTabChange]);

	if (!conversationHistory || conversationHistory.length === 0) {
		return null;
	}

	const tabs = [
		{
			id: "io" as const,
			label: "Input / Output",
			description: "Raw payloads",
		},
		{
			id: "history" as const,
			label: "Conversation History",
			description: `${conversationHistory.length} message${conversationHistory.length === 1 ? "" : "s"}`,
			count: conversationHistory.length,
		},
	];

	return (
		<nav className="flex flex-col gap-2 rounded-2xl border border-gray-200 bg-white p-2 shadow-sm sm:flex-row">
			{tabs.map((tab) => {
				const isActive = activeTab === tab.id;
				const handleClick =
					tab.id === "io" ? handleIOTabClick : handleHistoryTabClick;
				return (
					<button
						key={tab.id}
						type="button"
						onClick={handleClick}
						className={`flex flex-1 items-center justify-between rounded-xl border px-4 py-3 text-left text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40 ${
							isActive
								? "border-orange-500 bg-white text-gray-900 shadow-sm"
								: "border-transparent text-gray-600 hover:border-gray-300 hover:bg-slate-50 hover:text-gray-900"
						}`}
					>
						<div>
							<p className="text-sm">{tab.label}</p>
							<p className="text-xs text-gray-500">{tab.description}</p>
						</div>
						{tab.id === "history" && (
							<span
								className={`inline-flex items-center gap-1 rounded-full border px-2 py-1 text-[11px] ${
									isActive
										? "border-orange-300 bg-white text-orange-800"
										: "border-gray-200 bg-white text-gray-600"
								}`}
							>
								<MessageSquare className="h-3.5 w-3.5" />
								{tab.count}
							</span>
						)}
					</button>
				);
			})}
		</nav>
	);
};

export default ExecutionTabNavigation;
