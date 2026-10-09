/**
 * Detects suggestion/follow-up prompts at the end of an assistant message and
 * splits them out so they can be rendered as clickable chips (ChatGPT-style).
 *
 * Detection rules (conservative — requires ≥2 items to avoid false positives):
 *  • A numbered (1. 2. 3.) or bulleted (- * •) list at the tail of the message
 *  • Optionally preceded by a suggestion-header line
 */

export interface ParsedContent {
	mainContent: string;
	suggestions: string[];
}

const SUGGESTION_HEADER_RE =
	/^(suggestions?|what (?:would you like to do|'?s next)|try asking|you could ask|next steps?|follow[- ]up questions?|would you like to|here are some|you might also|what else|related questions?|some options?|you can also|explore more|want to know more)[:\?]?\s*$/i;

const LIST_ITEM_RE = /^\s*(?:\d+[.)]\s+|[-*•]\s+)(.+)/;

export function parseSuggestions(content: string): ParsedContent {
	if (!content || !content.trim()) return { mainContent: content, suggestions: [] };

	const lines = content.split("\n");

	// Walk up from the bottom, skipping trailing blank lines
	let bottom = lines.length - 1;
	while (bottom >= 0 && !lines[bottom].trim()) bottom--;

	// Collect consecutive list items from the bottom
	const suggestions: string[] = [];
	let cursor = bottom;

	while (cursor >= 0) {
		const m = lines[cursor].match(LIST_ITEM_RE);
		if (m) {
			suggestions.unshift(m[1].trim());
			cursor--;
		} else {
			break;
		}
	}

	// Need at least 2 items to treat as suggestions (avoids false positives)
	if (suggestions.length < 2) return { mainContent: content, suggestions: [] };

	// Skip blank lines above the list
	while (cursor >= 0 && !lines[cursor].trim()) cursor--;

	// Optionally consume a suggestion header line
	if (cursor >= 0 && SUGGESTION_HEADER_RE.test(lines[cursor].trim())) cursor--;

	// Everything above is the main content
	const mainContent = lines
		.slice(0, cursor + 1)
		.join("\n")
		.trim();

	return { mainContent, suggestions };
}
