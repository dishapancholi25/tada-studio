import { Loader2 } from "lucide-react";
import type React from "react";
import Button from "@/components/ui/Button";

interface McpServerConfigModalFooterProps {
	isEditing: boolean;
	isSaving: boolean;
	onClose: () => void;
	onSubmit: () => void;
}

const McpServerConfigModalFooter: React.FC<McpServerConfigModalFooterProps> = ({
	isEditing,
	isSaving,
	onClose,
	onSubmit,
}) => {
	return (
		<div className="flex items-center justify-end gap-3 border-t border-slate-200 bg-white px-6 py-4">
			<div className="flex items-center justify-end gap-3">
				<Button
					variant="secondary"
					onClick={onClose}
					disabled={isSaving}
					className="!border-slate-200 !bg-white !text-slate-800 hover:!border-orange-500 hover:!text-orange-700"
				>
					Cancel
				</Button>
				<Button
					variant="primary"
					onClick={onSubmit}
					disabled={isSaving}
					loading={isSaving}
					className="shadow-[0_8px_20px_rgba(15,23,42,0.12)]"
				>
					{isSaving ? (
						<>
							<Loader2 className="animate-spin" size={16} />
							Saving...
						</>
					) : isEditing ? (
						"Save Changes"
					) : (
						"Create Server"
					)}
				</Button>
			</div>
		</div>
	);
};

export default McpServerConfigModalFooter;
