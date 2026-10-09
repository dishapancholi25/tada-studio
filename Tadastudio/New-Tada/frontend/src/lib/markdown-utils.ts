/**
 * Utility functions for handling markdown content with base64 images
 */

/**
 * Check if a string contains markdown syntax
 */
export function hasMarkdownSyntax(content: string): boolean {
	if (!content || typeof content !== "string") return false;

	// Check for common markdown patterns
	const markdownPatterns = [
		/^#{1,6}\s+/m, // Headers
		/!\[([^\]]*)\]\(([^)]+)\)/, // Images
		/\[([^\]]+)\]\(([^)]+)\)/, // Links
		/^\s*[-*+]\s+/m, // Unordered lists
		/^\s*\d+\.\s+/m, // Ordered lists
		/\*\*([^*]+)\*\*/, // Bold
		/\*([^*]+)\*/, // Italic
		/```[\s\S]*?```/, // Code blocks
		/`[^`]+`/, // Inline code
		/^>\s+/m, // Blockquotes
		/^\|.*\|.*\|/m, // Tables (at least 2 columns)
		/^\s*\|?\s*:?-+:?\s*\|/m, // Table separator row
	];

	return markdownPatterns.some((pattern) => pattern.test(content));
}

/**
 * Check if content contains data:image URLs
 */
export function containsDataImage(content: string): boolean {
	if (!content || typeof content !== "string") return false;
	return /data:image\/[a-zA-Z0-9.+-]+;base64,/.test(content);
}

/**
 * Check if a string contains base64 image data (either as data URI or markdown)
 */
export function hasBase64Image(content: string): boolean {
	if (!content || typeof content !== "string") return false;

	// Check for data URI
	if (containsDataImage(content)) return true;

	// Check for common base64 patterns (PNG, JPEG, GIF, WebP headers)
	if (content.match(/iVBORw0KGg/)) return true; // PNG
	if (content.match(/\/9j\//)) return true; // JPEG
	if (content.match(/R0lGOD/)) return true; // GIF
	if (content.match(/UklGR/)) return true; // WebP

	return false;
}

/**
 * Guess MIME type from base64 string
 */
export function guessMimeType(base64: string): string {
	if (base64.startsWith("iVBORw0")) return "image/png";
	if (base64.startsWith("/9j/")) return "image/jpeg";
	if (base64.startsWith("R0lGOD")) return "image/gif";
	if (base64.startsWith("UklGR")) return "image/webp";
	return "image/png"; // Default to PNG
}

/**
 * Check if content has markdown with base64 images
 */
export function hasMarkdownWithBase64(content: string): boolean {
	if (!content || typeof content !== "string") return false;

	// Check for markdown image syntax with base64 data URI
	const markdownImageWithBase64 = /!\[([^\]]*)\]\((data:image\/[^)]+)\)/;
	return markdownImageWithBase64.test(content);
}

/**
 * Unescape content while preserving base64 data
 */
export function unescapeContent(content: string): string {
	if (!content || typeof content !== "string") return content;

	// First, handle newlines and tabs
	let processed = content.replace(/\\n/g, "\n").replace(/\\t/g, "\t");

	// Handle escaped quotes
	processed = processed.replace(/\\"/g, '"');

	// For escaped backslashes, be careful not to corrupt base64
	if (!processed.includes("data:image")) {
		// No base64, safe to replace all double backslashes
		processed = processed.replace(/\\\\/g, "\\");
	} else {
		// Has base64, need to be more careful
		// Split by data URI, process non-base64 parts, then rejoin
		const base64Pattern = /(data:image\/[a-z]+;base64,[A-Za-z0-9+/=]+)/g;
		const parts = processed.split(base64Pattern);

		for (let i = 0; i < parts.length; i++) {
			// Only process non-base64 parts (even indices)
			if (i % 2 === 0 && !parts[i].startsWith("data:image")) {
				parts[i] = parts[i].replace(/\\\\/g, "\\");
			}
		}

		processed = parts.join("");
	}

	return processed;
}

/**
 * Extract response content from various data structures
 */
export function extractResponseContent(data: any): string | null {
	if (!data) return null;

	// Direct string
	if (typeof data === "string") return data;

	// Object with response field
	if (data.response && typeof data.response === "string") {
		return data.response;
	}

	// Object with content field
	if (data.content && typeof data.content === "string") {
		return data.content;
	}

	// Object with message field
	if (data.message && typeof data.message === "string") {
		return data.message;
	}

	// Object with text field
	if (data.text && typeof data.text === "string") {
		return data.text;
	}

	// Object with output field
	if (data.output && typeof data.output === "string") {
		return data.output;
	}

	// Object with answer field
	if (data.answer && typeof data.answer === "string") {
		return data.answer;
	}

	return null;
}

/**
 * Process content for rendering (unescape and prepare for markdown)
 * Also strips whitespace/newlines INSIDE data: URIs
 */
export function processContentForRendering(
	content: string | any,
): string | null {
	// Try to extract string content
	const extracted =
		typeof content === "string" ? content : extractResponseContent(content);

	if (!extracted) return null;

	// Unescape the content while preserving base64
	let processed = unescapeContent(extracted);

	// Strip whitespace/newlines INSIDE data: URIs (some models insert \n)
	processed = processed.replace(
		/(data:image\/[a-zA-Z0-9.+-]+;base64,)([A-Za-z0-9+/=\s]+)/g,
		(_, p1, p2) => p1 + p2.replace(/\s+/g, ""),
	);

	return processed;
}

/**
 * Determine if content should be rendered as markdown
 * More permissive - renders any string with data:image as markdown
 */
export function shouldRenderAsMarkdown(content: string | any): boolean {
	const processed = processContentForRendering(content);
	if (!processed) return false;

	// More permissive: render as markdown if it has markdown syntax OR contains data:image
	return (
		hasMarkdownSyntax(processed) ||
		hasBase64Image(processed) ||
		containsDataImage(processed)
	);
}
