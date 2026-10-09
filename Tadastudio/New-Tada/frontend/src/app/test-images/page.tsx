"use client";

import React, { useState } from "react";
import JsonViewerEnhanced from "@/components/JsonViewerEnhanced";
import SimpleMarkdown from "@/components/utils/SimpleMarkdown";

export default function TestImagesPage() {
	// Sample base64 image (1x1 red pixel PNG)
	const sampleBase64 =
		"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg==";
	const fullDataUri = `data:image/png;base64,${sampleBase64}`;

	// Different test cases
	const [activeTest, setActiveTest] = useState<string>("markdown");

	const testCases = {
		markdown: {
			title: "Markdown Image Syntax",
			content: `# Test Image Rendering

Here's an image using markdown syntax:

![Test Image](${fullDataUri})

This should render as a small red pixel.`,
		},
		markdownEscaped: {
			title: "Escaped Markdown (simulating backend response)",
			content: `# Test Image Rendering\\n\\nHere's an image using markdown syntax:\\n\\n![Test Image](${fullDataUri})\\n\\nThis should render as a small red pixel.`,
		},
		htmlImg: {
			title: "HTML Image Tag",
			content: `# Test Image with HTML

<img src="${fullDataUri}" alt="Test Image" />

This uses HTML img tag instead of markdown.`,
		},
		jsonWithImage: {
			title: "JSON Viewer with Base64",
			data: {
				message: "This is a test response",
				image: fullDataUri,
				description: "The image field contains a base64 data URI",
			},
		},
		jsonWithMarkdown: {
			title: "JSON Viewer with Markdown containing image",
			data: {
				response: `Here's a response with an image:\\n\\n![Generated Image](${fullDataUri})\\n\\nThis is after the image.`,
			},
		},
		rawBase64String: {
			title: "Raw Base64 String in JSON Viewer",
			data: sampleBase64,
		},
		complexMarkdown: {
			title: "Complex Markdown with Multiple Images",
			content: `# Expense Report Card

## Generated Visualization

Here's your expense card:

![Expense Card](${fullDataUri})

### Additional Information

- Total Expenses: $1,234.56
- Categories: 5
- Time Period: Last 30 days

![Summary Chart](${fullDataUri})

All images should render properly.`,
		},
	};

	return (
		<div className="min-h-screen bg-[color:var(--color-bg-secondary)] text-slate-900 p-8">
			<div className="max-w-6xl mx-auto">
				<h1 className="text-3xl font-bold mb-8">
					Base64 Image Rendering Test Page
				</h1>

				{/* Test selector */}
				<div className="mb-6">
					<label
						htmlFor="test-case-select"
						className="block text-sm font-medium mb-2"
					>
						Select Test Case:
					</label>
					<select
						id="test-case-select"
						value={activeTest}
						onChange={(e) => setActiveTest(e.target.value)}
						className="bg-[color:var(--color-surface)] border border-[color:var(--color-border)] rounded px-4 py-2 text-slate-900"
					>
						{Object.keys(testCases).map((key) => (
							<option key={key} value={key}>
								{testCases[key as keyof typeof testCases].title}
							</option>
						))}
					</select>
				</div>

				{/* Test display area */}
				<div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
					{/* Input/Source */}
					<div className="bg-[color:var(--color-surface)] rounded-lg p-6">
						<h2 className="text-xl font-semibold mb-4">Input/Source</h2>
						<pre className="bg-[color:var(--color-bg-secondary)] p-4 rounded overflow-x-auto text-xs">
							{activeTest.includes("json")
								? JSON.stringify(
										(testCases[activeTest as keyof typeof testCases] as any)
											.data,
										null,
										2,
									)
								: (testCases[activeTest as keyof typeof testCases] as any)
										.content}
						</pre>
					</div>

					{/* Rendered Output */}
					<div className="bg-[color:var(--color-surface)] rounded-lg p-6">
						<h2 className="text-xl font-semibold mb-4">Rendered Output</h2>
						<div className="bg-[color:var(--color-bg-secondary)] p-4 rounded">
							{activeTest.includes("json") ? (
								<JsonViewerEnhanced
									data={
										(testCases[activeTest as keyof typeof testCases] as any)
											.data
									}
									className="w-full"
								/>
							) : (
								<SimpleMarkdown
									content={
										activeTest === "markdownEscaped"
											? (testCases[activeTest] as any).content.replace(
													/\\n/g,
													"\n",
												)
											: (testCases[activeTest as keyof typeof testCases] as any)
													.content
									}
									className="w-full"
								/>
							)}
						</div>
					</div>
				</div>

				{/* Debug Information */}
				<div className="mt-8 bg-[color:var(--color-surface)] rounded-lg p-6">
					<h2 className="text-xl font-semibold mb-4">Debug Information</h2>
					<p className="text-sm text-[color:var(--color-text-muted)] mb-2">
						Open browser console to see debug logs from SimpleMarkdown and
						JsonViewerEnhanced components.
					</p>
					<div className="bg-[color:var(--color-bg-secondary)] p-4 rounded">
						<p className="text-xs font-mono">
							<span className="text-[#0DA931]">Sample Base64 Length:</span>{" "}
							{sampleBase64.length} chars
							<br />
							<span className="text-[#0DA931]">Full Data URI Length:</span>{" "}
							{fullDataUri.length} chars
							<br />
							<span className="text-[#0DA931]">Active Test:</span> {activeTest}
						</p>
					</div>
				</div>

				{/* Instructions */}
				<div className="mt-8 bg-[color:var(--color-accent)]/10 border border-[color:var(--color-border)]/30 rounded-lg p-6">
					<h2 className="text-xl font-semibold mb-4 text-[color:var(--color-accent)]">
						Testing Instructions
					</h2>
					<ol className="list-decimal list-inside space-y-2 text-sm text-[color:var(--color-text-secondary)]">
						<li>Try each test case using the dropdown selector</li>
						<li>Check if images render properly in the output panel</li>
						<li>Open browser console (F12) to see debug logs</li>
						<li>The red pixel should be visible if rendering works</li>
						<li>Click on rendered images to open them in a new tab</li>
					</ol>
				</div>
			</div>
		</div>
	);
}
