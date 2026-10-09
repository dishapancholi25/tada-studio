/**
 * Shared helpers for formatting node output field summaries.
 * Used by SpecificNodeConfig (node list) and FlowPreview (diagram).
 */

interface FieldLike {
	name: string;
	type: string;
}

/**
 * Full format: "response (string)" or "success (boolean), data (object) +2 more"
 */
export function formatFieldsSummary(
	fields: FieldLike[],
	maxShow = 3,
): string | null {
	if (!fields || fields.length === 0) return null;
	const shown = fields.slice(0, maxShow).map((f) => `${f.name} (${f.type})`);
	const remainder = fields.length - maxShow;
	const result = shown.join(", ");
	return remainder > 0 ? `${result} +${remainder} more` : result;
}

/**
 * Short format for tight spaces: "response" or "success, data +2"
 */
export function formatFieldsSummaryShort(
	fields: FieldLike[],
	maxShow = 2,
): string | null {
	if (!fields || fields.length === 0) return null;
	const shown = fields.slice(0, maxShow).map((f) => f.name);
	const remainder = fields.length - maxShow;
	const result = shown.join(", ");
	return remainder > 0 ? `${result} +${remainder}` : result;
}
