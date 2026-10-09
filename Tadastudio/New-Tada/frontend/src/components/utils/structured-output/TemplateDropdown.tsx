import { LayoutTemplate } from "lucide-react";
import type React from "react";

interface TemplateDropdownProps {
	showTemplates: boolean;
	onToggle: () => void;
}

const TemplateDropdown: React.FC<TemplateDropdownProps> = ({
	showTemplates,
	onToggle,
}) => {
	return (
		<button
			type="button"
			onClick={onToggle}
			className={`flex items-center gap-2 rounded-[4px] border px-4 py-2 transition-all shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25 ${
				showTemplates
					? "border-orange-500 bg-white text-orange-900"
					: "border-slate-200 bg-white text-slate-900 hover:border-orange-400 hover:bg-slate-50"
			}`}
		>
			<LayoutTemplate
				className={`w-4 h-4 shrink-0 ${showTemplates ? "text-orange-600" : "text-slate-600"}`}
			/>
			<span className="text-sm font-medium">Use Template</span>
			<span className="text-[10px] rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-slate-700">
				{showTemplates ? "Hide" : "Browse"}
			</span>
		</button>
	);
};

export default TemplateDropdown;
