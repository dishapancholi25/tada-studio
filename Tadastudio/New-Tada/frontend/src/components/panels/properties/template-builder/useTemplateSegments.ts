import { useCallback, useEffect, useMemo, useState } from "react";
import type {
	TemplateSegment,
	TextSegment,
	VariableInfo,
	VariableSegment,
} from "./templateBuilderTypes";

/** Parse a flat template string into segments. */
export function parseTemplate(
	template: string,
	variables: VariableInfo[],
): TemplateSegment[] {
	if (!template) return [{ type: "text", value: "" }];

	const segments: TemplateSegment[] = [];
	const regex = /\{([^}]+)\}/g;
	let lastIndex = 0;
	let match: RegExpExecArray | null;

	while ((match = regex.exec(template)) !== null) {
		// Text before this variable
		if (match.index > lastIndex) {
			segments.push({ type: "text", value: template.slice(lastIndex, match.index) });
		}

		const key = match[1];
		const varInfo = variables.find((v) => v.key === key);

		segments.push({
			type: "variable",
			variableKey: key,
			displayLabel: varInfo?.displayLabel ?? key,
			nodeType: varInfo?.nodeType,
		} satisfies VariableSegment);

		lastIndex = regex.lastIndex;
	}

	// Trailing text
	if (lastIndex < template.length) {
		segments.push({ type: "text", value: template.slice(lastIndex) });
	}

	// Ensure there's at least one text segment for cursor placement
	if (segments.length === 0) {
		segments.push({ type: "text", value: "" });
	}

	return segments;
}

/** Serialize segments back to a flat template string. */
export function serializeSegments(segments: TemplateSegment[]): string {
	return segments
		.map((s) => (s.type === "text" ? s.value : `{${s.variableKey}}`))
		.join("");
}

/** Hook for managing template segments with insert/remove/update operations. */
export function useTemplateSegments(
	initialTemplate: string,
	variables: VariableInfo[],
) {
	const [segments, setSegments] = useState<TemplateSegment[]>(() =>
		parseTemplate(initialTemplate, variables),
	);

	// Re-parse when the external template prop changes (e.g., modal reopened after save)
	useEffect(() => {
		setSegments(parseTemplate(initialTemplate, variables));
	}, [initialTemplate, variables]);

	const templateString = useMemo(() => serializeSegments(segments), [segments]);

	/** Insert a variable at a given segment index. Splits the text segment if needed. */
	const insertVariableAtIndex = useCallback(
		(variable: VariableInfo, segmentIndex: number, charOffset?: number) => {
			setSegments((prev) => {
				const next = [...prev];
				const target = next[segmentIndex];

				const varSeg: VariableSegment = {
					type: "variable",
					variableKey: variable.key,
					displayLabel: variable.displayLabel,
					nodeType: variable.nodeType,
				};

				if (target && target.type === "text" && charOffset !== undefined) {
					// Split text segment at charOffset
					const before: TextSegment = {
						type: "text",
						value: target.value.slice(0, charOffset),
					};
					const after: TextSegment = {
						type: "text",
						value: target.value.slice(charOffset),
					};
					next.splice(segmentIndex, 1, before, varSeg, after);
				} else {
					// Insert after the segment
					next.splice(segmentIndex + 1, 0, varSeg);
				}

				return next;
			});
		},
		[],
	);

	/** Append a variable at the end of the template. */
	const appendVariable = useCallback((variable: VariableInfo) => {
		setSegments((prev) => {
			const varSeg: VariableSegment = {
				type: "variable",
				variableKey: variable.key,
				displayLabel: variable.displayLabel,
				nodeType: variable.nodeType,
			};
			return [...prev, varSeg];
		});
	}, []);

	/** Remove a segment by index. */
	const removeSegment = useCallback((index: number) => {
		setSegments((prev) => {
			const next = [...prev];
			next.splice(index, 1);
			// Merge adjacent text segments
			const merged: TemplateSegment[] = [];
			for (const seg of next) {
				const last = merged[merged.length - 1];
				if (seg.type === "text" && last?.type === "text") {
					(last as TextSegment).value += seg.value;
				} else {
					merged.push({ ...seg });
				}
			}
			if (merged.length === 0) {
				merged.push({ type: "text", value: "" });
			}
			return merged;
		});
	}, []);

	/** Update text segment at index. */
	const updateTextSegment = useCallback(
		(index: number, newValue: string) => {
			setSegments((prev) => {
				const next = [...prev];
				if (next[index]?.type === "text") {
					next[index] = { type: "text", value: newValue };
				}
				return next;
			});
		},
		[],
	);

	/** Replace all segments (e.g., after DOM-based parsing). */
	const replaceSegments = useCallback(
		(newSegments: TemplateSegment[]) => {
			setSegments(
				newSegments.length > 0
					? newSegments
					: [{ type: "text", value: "" }],
			);
		},
		[],
	);

	/** Re-parse from a raw string (e.g., when initial template changes externally). */
	const reparse = useCallback(
		(raw: string) => {
			setSegments(parseTemplate(raw, variables));
		},
		[variables],
	);

	return {
		segments,
		templateString,
		insertVariableAtIndex,
		appendVariable,
		removeSegment,
		updateTextSegment,
		replaceSegments,
		reparse,
	};
}
