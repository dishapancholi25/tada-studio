import { Wrench, X } from "lucide-react";
import type React from "react";

interface McpServerConfigModalHeaderProps {
	isEditing: boolean;
	onClose: () => void;
}

const McpServerConfigModalHeader: React.FC<McpServerConfigModalHeaderProps> = ({
	isEditing,
	onClose,
}) => {
	return (
		<div className="shrink-0 border-b border-slate-200 px-6 pb-4 pt-5">
			<div className="flex items-start justify-between">
				<div className="flex items-center gap-3">
					<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[4px] border border-orange-200 bg-orange-100">
						<Wrench className="h-5 w-5 text-orange-600" />
					</div>
					<div>
						<h2 className="text-lg font-semibold tracking-tight text-slate-900">
							{isEditing ? "Edit MCP Server" : "Add MCP Server"}
						</h2>
						<p className="mt-0.5 text-sm text-slate-600">
							Configure connection details and authentication. Credentials are encrypted at rest.
						</p>
					</div>
				</div>
				<button
					type="button"
					onClick={onClose}
					className="ml-4 rounded-[4px] p-2 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800"
					aria-label="Close modal"
				>
					<X size={20} />
				</button>
			</div>
		</div>
	);
};

export default McpServerConfigModalHeader;
