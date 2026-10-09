"use client";

import { Code2, FileCode } from "lucide-react";
import { useRef, useState, useEffect } from "react";
import InfoTooltip from "@/components/ui/InfoTooltipPortal";

interface CodeEditorSectionProps {
	language: "python" | "javascript";
	onLanguageChange: (language: "python" | "javascript") => void;
	code: string;
	onCodeChange: (code: string) => void;
	outputVariable: string;
}

const DEFAULT_PYTHON_CODE = `# Your Python code here
# Set the 'result' variable with your return value

result = "Hello, World!"
`;

const DEFAULT_JAVASCRIPT_CODE = `// Your JavaScript code here
// Set the 'result' variable with your return value

let result = "Hello, World!";
`;

export default function CodeEditorSection({
	language,
	onLanguageChange,
	code,
	onCodeChange,
	outputVariable,
}: CodeEditorSectionProps) {
	const textareaRef = useRef<HTMLTextAreaElement>(null);
	const lineNumbersRef = useRef<HTMLDivElement>(null);
	const [lineCount, setLineCount] = useState(1);

	useEffect(() => {
		const lines = (code || "").split("\n").length;
		setLineCount(Math.max(lines, 1));
	}, [code]);

	const handleScroll = () => {
		if (textareaRef.current && lineNumbersRef.current) {
			lineNumbersRef.current.scrollTop = textareaRef.current.scrollTop;
		}
	};

	const handleLanguageChange = (newLanguage: "python" | "javascript") => {
		const currentCode = code || "";
		const isPythonDefault = currentCode.trim() === DEFAULT_PYTHON_CODE.trim();
		const isJsDefault = currentCode.trim() === DEFAULT_JAVASCRIPT_CODE.trim();
		const isEmpty = !currentCode.trim();

		let newCode = currentCode;
		if (isEmpty || isPythonDefault || isJsDefault) {
			newCode = newLanguage === "python" ? DEFAULT_PYTHON_CODE : DEFAULT_JAVASCRIPT_CODE;
		}

		onLanguageChange(newLanguage);
		if (newCode !== currentCode) {
			onCodeChange(newCode);
		}
	};

	const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
		e.stopPropagation();

		if (e.key === "Tab") {
			e.preventDefault();
			const textarea = e.currentTarget;
			const start = textarea.selectionStart;
			const end = textarea.selectionEnd;
			const value = textarea.value;
			const newValue = value.substring(0, start) + "    " + value.substring(end);
			onCodeChange(newValue);
			setTimeout(() => {
				textarea.selectionStart = textarea.selectionEnd = start + 4;
			}, 0);
		}
	};

	const lineNumbers = Array.from({ length: lineCount }, (_, i) => i + 1);

	return (
		<div className="space-y-6">
			<div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
				<div className="flex items-start justify-between gap-4 border-b border-slate-200 pb-5">
					<div className="flex items-center gap-3">
						<div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-orange-200 bg-orange-100 text-orange-600">
							<Code2 className="h-6 w-6" />
						</div>
						<div>
							<h3 className="text-xl font-semibold text-slate-900">
								Code Editor
							</h3>
							<p className="text-sm text-slate-600">
								Write Python or JavaScript code to execute
							</p>
						</div>
					</div>
				</div>

				<div className="mt-6 space-y-6">
					<div>
						<div className="mb-3 flex items-center gap-2">
							<label className="text-sm font-semibold text-slate-800">
								Language
							</label>
							<InfoTooltip text="Select the programming language for your code" />
						</div>
						<div className="flex gap-3">
							<button
								type="button"
								onClick={() => handleLanguageChange("python")}
								className={`flex items-center gap-2.5 rounded-xl border px-5 py-3 text-sm font-medium transition-all ${
									language === "python"
										? "border-orange-500 bg-orange-50 text-orange-700 shadow-sm"
										: "border-slate-200 bg-white text-slate-700 hover:border-orange-300 hover:text-orange-700"
								}`}
							>
								<FileCode className="h-5 w-5" />
								Python
							</button>
							<button
								type="button"
								onClick={() => handleLanguageChange("javascript")}
								className={`flex items-center gap-2.5 rounded-xl border px-5 py-3 text-sm font-medium transition-all ${
									language === "javascript"
										? "border-orange-500 bg-orange-50 text-orange-700 shadow-sm"
										: "border-slate-200 bg-white text-slate-700 hover:border-orange-300 hover:text-orange-700"
								}`}
							>
								<FileCode className="h-5 w-5" />
								JavaScript
							</button>
						</div>
					</div>

					<div>
						<div className="mb-3 flex items-center gap-2">
							<label className="text-sm font-semibold text-slate-800">
								Code
							</label>
							<InfoTooltip text="Input variables are injected into the namespace. Set the output variable to return a value." />
						</div>

						{/* Mashreq Theme Editor */}
						<div className="flex h-80 overflow-hidden rounded-xl border border-orange-200 bg-white shadow-sm">
							{/* Line Numbers */}
							<div
								ref={lineNumbersRef}
								className="w-12 select-none overflow-hidden border-r border-orange-100 bg-orange-50 py-3 text-right"
							>
								{lineNumbers.map((num) => (
									<div
										key={num}
										className="px-2 font-mono text-xs leading-6 text-orange-400"
									>
										{num}
									</div>
								))}
							</div>

							{/* Code Area */}
							<textarea
								ref={textareaRef}
								value={code || ""}
								onChange={(e) => onCodeChange(e.target.value)}
								onKeyDown={handleKeyDown}
								onKeyUp={(e) => e.stopPropagation()}
								onKeyPress={(e) => e.stopPropagation()}
								onScroll={handleScroll}
								placeholder={
									language === "python"
										? "# Enter Python code..."
										: "// Enter JavaScript code..."
								}
								className="flex-1 resize-none bg-white px-4 py-3 font-mono text-sm leading-6 text-slate-800 placeholder-slate-400 focus:outline-none"
								style={{
									caretColor: "#f97316",
								}}
								spellCheck={false}
								autoComplete="off"
								autoCorrect="off"
								autoCapitalize="off"
							/>
						</div>

						<div className="mt-3 rounded-lg border border-orange-200 bg-orange-50 p-3">
							<p className="text-xs text-slate-700">
								Set{" "}
								<code className="rounded bg-orange-100 px-1.5 py-0.5 font-mono text-orange-700">
									{outputVariable || "result"}
								</code>{" "}
								with your return value. Previous node output is available as{" "}
								<code className="rounded bg-orange-100 px-1.5 py-0.5 font-mono text-orange-700">
									input
								</code>.
							</p>
						</div>
					</div>
				</div>
			</div>
		</div>
	);
}
