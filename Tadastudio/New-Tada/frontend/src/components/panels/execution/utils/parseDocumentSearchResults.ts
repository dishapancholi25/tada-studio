import type { DocumentSearchExecution } from "../unified/types/execution.types";

export interface DocumentSearchParsedResult {
	content: string;
	source?: string;
	metadata?: {
		page?: number;
		relevance?: number;
		confidence?: number;
		source?: string;
	};
	isStructured?: boolean;
	raw?: Record<string, any>;
}

type RawDocumentSearchInput =
	| string
	| Record<string, any>
	| Array<Record<string, any>>
	| null
	| undefined;

/**
 * Parse document search results coming from different backends.
 * Handles JSON payloads, markdown formatted responses and legacy text blobs.
 */
export function parseDocumentSearchResults(
	rawResults: RawDocumentSearchInput,
): DocumentSearchParsedResult[] {
	if (!rawResults) {
		return [];
	}

	const { arrayCandidate, textCandidate } = extractResultPayload(rawResults);

	// Prefer structured array data when available
	if (arrayCandidate && arrayCandidate.length > 0) {
		return normaliseArrayResults(arrayCandidate);
	}

	if (!textCandidate) {
		return [];
	}

	const structured = parseStructuredMarkdown(textCandidate);
	if (structured.length > 0) {
		return structured;
	}

	const legacy = parseLegacyTextFormat(textCandidate);
	if (legacy.length > 0) {
		return legacy;
	}

	return [
		{
			content: textCandidate,
			isStructured: false,
		},
	];
}

function extractResultPayload(value: RawDocumentSearchInput) {
	const stack: RawDocumentSearchInput[] = [value];
	const seen = new Set<RawDocumentSearchInput>();
	let textCandidate: string | undefined;

	while (stack.length > 0) {
		const current = stack.pop();
		if (current == null || seen.has(current)) continue;
		seen.add(current);

		if (Array.isArray(current)) {
			return {
				arrayCandidate: current as Record<string, any>[],
				textCandidate,
			};
		}

		if (typeof current === "string") {
			if (!textCandidate) {
				textCandidate = current;
			}
			try {
				const parsed = JSON.parse(current);
				stack.push(parsed);
				continue;
			} catch {
				continue;
			}
		}

		if (typeof current === "object") {
			const record = current as Record<string, any>;
			const possibleKeys = ["results", "result", "documents", "items", "data"];
			for (const key of possibleKeys) {
				if (key in record) {
					stack.push(record[key]);
				}
			}

			if (typeof record.output === "string") {
				stack.push(record.output);
			}
			if (typeof record.content === "string") {
				stack.push(record.content);
			}

			if (!textCandidate) {
				try {
					textCandidate = JSON.stringify(record, null, 2);
				} catch {
					// Ignore stringify failures (cyclic references)
				}
			}
		}
	}

	return { arrayCandidate: undefined, textCandidate };
}

function normaliseArrayResults(
	items: Record<string, any>[],
): DocumentSearchParsedResult[] {
	return items
		.map((item) => {
			const metadata = item.metadata ?? {};
			const page =
				normaliseNumber(
					item.page ??
						metadata.page ??
						metadata.Page ??
						metadata.pages ??
						metadata.Pages,
				) ?? undefined;

			const relevance = normaliseScore(
				item.relevance ??
					metadata.relevance ??
					metadata.Relevance ??
					metadata.score ??
					metadata.Score,
			);

			const confidence = normaliseScore(
				item.confidence ?? metadata.confidence ?? metadata.Confidence,
			);

			const source =
				item.source ??
				metadata.source ??
				metadata.Source ??
				item.document_title ??
				metadata.document_title;

			const content = (item.content ?? item.text ?? "").toString().trim();
			if (!content) return null;

			const parsed: DocumentSearchParsedResult = {
				content,
				source,
				metadata: {
					page,
					relevance,
					confidence,
					source,
				},
				isStructured: true,
				raw: item,
			};

			return parsed;
		})
		.filter((item): item is DocumentSearchParsedResult => Boolean(item));
}

function parseStructuredMarkdown(text: string): DocumentSearchParsedResult[] {
	if (
		!text.includes("## Document Search Results") &&
		!text.includes("## Retrieved Context")
	) {
		return [];
	}

	const contextMatch = text.match(
		/## Retrieved Context\n+([\s\S]*?)(?=\n## References|\n## Search Quality|$)/,
	);
	if (!contextMatch) {
		return [];
	}

	const referencesMatch = text.match(/## References\n+([\s\S]*?)(?=\n## |$)/);
	const references = new Map<
		string,
		{ source?: string; page?: number; score?: number }
	>();

	if (referencesMatch) {
		const refLines = referencesMatch[1]
			.split("\n")
			.map((line) => line.trim())
			.filter(Boolean);

		refLines.forEach((line) => {
			const match = line.match(
				/\[(\d+)\]\s+([^,]+)(?:,\s*Pages?\s+([\d-]+))?(?:,\s*Chunk\s+[\d-]+)?(?:,\s*Score:\s*([\d.]+))?/i,
			);
			if (!match) return;

			const [, refNum, source, pageRaw, scoreRaw] = match;
			const page = pageRaw ? normalisePage(pageRaw) : undefined;
			const score = scoreRaw ? parseFloat(scoreRaw) : undefined;

			references.set(refNum, {
				source: source?.trim(),
				page,
				score,
			});
		});
	}

	const contextSection = contextMatch[1];
	const chunkRegex = /(^|\n)\s*\[(\d+)(?:\.(\d+))?\]\s*/g;
	const matches = Array.from(contextSection.matchAll(chunkRegex));
	const results: DocumentSearchParsedResult[] = [];

	matches.forEach((match, index) => {
		const markerLength = match[0].length;
		const contentStart = (match.index ?? 0) + markerLength;
		const contentEnd =
			index + 1 < matches.length
				? (matches[index + 1].index ?? contextSection.length)
				: contextSection.length;

		const rawContent = contextSection
			.slice(contentStart, contentEnd)
			.trim()
			// Remove dangling reference-only markers like [1] that may appear at the end
			.replace(/^\s*\[(\d+)\]\s*$/, "")
			.trim();

		if (!rawContent) {
			return;
		}

		const refNum = match[2];
		let content = rawContent;
		let confidence: number | undefined;

		const confidenceMatch = content.match(/\*Confidence:\s*(\d+)%\*/i);
		if (confidenceMatch) {
			confidence = parseInt(confidenceMatch[1], 10) / 100;
			content = content.replace(confidenceMatch[0], "").trim();
		}

		const ref = references.get(refNum);

		results.push({
			content,
			source: ref?.source,
			metadata: {
				page: ref?.page,
				relevance: ref?.score,
				confidence,
				source: ref?.source,
			},
			isStructured: true,
		});
	});

	return results;
}

function parseLegacyTextFormat(text: string): DocumentSearchParsedResult[] {
	const blocks = text
		.split(/\n{2,}/)
		.map((block) => block.trim())
		.filter(Boolean);

	if (blocks.length <= 1) {
		return [];
	}

	const results: DocumentSearchParsedResult[] = [];
	let current: DocumentSearchParsedResult | null = null;

	blocks.forEach((block) => {
		if (/^metadata:/i.test(block)) {
			if (!current) return;
			const pageMatch = block.match(/page[:\s]+(\d+)/i);
			const relevanceMatch = block.match(/relevance[:\s]+([\d.]+)/i);
			const confidenceMatch = block.match(/confidence[:\s]+([\d.]+)/i);

			current.metadata = current.metadata ?? {};
			if (pageMatch) current.metadata.page = parseInt(pageMatch[1], 10);
			if (relevanceMatch)
				current.metadata.relevance = parseFloat(relevanceMatch[1]);
			if (confidenceMatch)
				current.metadata.confidence = parseFloat(confidenceMatch[1]);
			return;
		}

		if (/^source[:\s]/i.test(block)) {
			if (!current) return;
			const sourceMatch = block.match(/^source[:\s]+(.+)/i);
			if (sourceMatch) {
				current.source = sourceMatch[1].trim();
				current.metadata = current.metadata ?? {};
				current.metadata.source = current.source;
			}
			return;
		}

		const bracketMeta = block.match(/\n?\[([^\]]+)\]\s*$/);
		let content = block;
		const metadata: DocumentSearchParsedResult["metadata"] = {};

		if (bracketMeta && bracketMeta.index !== undefined) {
			content = block.substring(0, bracketMeta.index).trim();
			const meta = bracketMeta[1];
			const pageMatch = meta.match(/page\s*(\d+)/i);
			const relevanceMatch = meta.match(/relevance[:\s]*([\d.]+)/i);

			if (pageMatch) metadata.page = parseInt(pageMatch[1], 10);
			if (relevanceMatch) metadata.relevance = parseFloat(relevanceMatch[1]);
			metadata.source = meta;
		}

		current = {
			content,
			metadata: Object.keys(metadata).length > 0 ? metadata : undefined,
			source: metadata.source,
			isStructured: false,
		};

		results.push(current);
	});

	return results;
}

function normaliseNumber(value: unknown): number | undefined {
	if (typeof value === "number" && !Number.isNaN(value)) {
		return value;
	}
	if (typeof value === "string") {
		const parsed = parseFloat(value);
		if (!Number.isNaN(parsed)) {
			return parsed;
		}
	}
	return undefined;
}

function normaliseScore(value: unknown): number | undefined {
	const num = normaliseNumber(value);
	if (num === undefined) return undefined;

	if (num > 1 && num <= 100) {
		return num / 100;
	}

	return num;
}

function normalisePage(value: string): number | undefined {
	if (!value) return undefined;
	const firstNumber = value.split(/[-\s]/)[0];
	const parsed = parseInt(firstNumber, 10);
	return Number.isNaN(parsed) ? undefined : parsed;
}
