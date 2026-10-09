import { AlertCircle } from "lucide-react";
import type React from "react";

interface SchemaValidationErrorsProps {
	errors: string[];
}

const SchemaValidationErrors: React.FC<SchemaValidationErrorsProps> = ({
	errors,
}) => {
	if (errors.length === 0) return null;

	return (
		<div className="mb-6 p-4 bg-red-50 border border-red-200 rounded">
			<div className="flex items-center gap-3 mb-3">
				<AlertCircle className="w-5 h-5 text-red-600" />
				<span className="text-red-600 font-semibold">
					Schema Validation Errors
				</span>
			</div>
			<ul className="text-red-700 text-sm space-y-2">
				{errors.map((error, index) => (
					<li
						key={`validation-${error.substring(0, 50)}-${index}`}
						className="flex items-start gap-2"
					>
						<span className="text-red-500 mt-0.5">•</span>
						{error}
					</li>
				))}
			</ul>
		</div>
	);
};

export default SchemaValidationErrors;
