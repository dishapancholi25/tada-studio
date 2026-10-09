/**
 * Date formatting utilities.
 */

/**
 * Format a date string as relative time.
 *
 * @param date - ISO date string or null
 * @returns Relative time string (e.g., "2 hours ago", "3 days ago", "Never")
 */
export function formatRelativeTime(date: string | null): string {
	if (!date) return "Never";

	const now = new Date();
	const then = new Date(date);
	const diffMs = now.getTime() - then.getTime();
	const diffSeconds = Math.floor(diffMs / 1000);
	const diffMinutes = Math.floor(diffSeconds / 60);
	const diffHours = Math.floor(diffMinutes / 60);
	const diffDays = Math.floor(diffHours / 24);
	const diffWeeks = Math.floor(diffDays / 7);
	const diffMonths = Math.floor(diffDays / 30);
	const diffYears = Math.floor(diffDays / 365);

	if (diffSeconds < 60) {
		return "Just now";
	}
	if (diffMinutes < 60) {
		return diffMinutes === 1 ? "1 minute ago" : `${diffMinutes} minutes ago`;
	}
	if (diffHours < 24) {
		return diffHours === 1 ? "1 hour ago" : `${diffHours} hours ago`;
	}
	if (diffDays < 7) {
		return diffDays === 1 ? "1 day ago" : `${diffDays} days ago`;
	}
	if (diffWeeks < 5) {
		return diffWeeks === 1 ? "1 week ago" : `${diffWeeks} weeks ago`;
	}
	if (diffMonths < 12) {
		return diffMonths === 1 ? "1 month ago" : `${diffMonths} months ago`;
	}
	return diffYears === 1 ? "1 year ago" : `${diffYears} years ago`;
}

/**
 * Format a date string as a readable date.
 *
 * @param date - ISO date string
 * @returns Formatted date string (e.g., "Jan 15, 2024")
 */
export function formatDate(date: string): string {
	const d = new Date(date);
	return d.toLocaleDateString("en-US", {
		year: "numeric",
		month: "short",
		day: "numeric",
	});
}

/**
 * Format a date string with time.
 *
 * @param date - ISO date string
 * @returns Formatted date and time string (e.g., "Jan 15, 2024 at 3:45 PM")
 */
export function formatDateTime(date: string): string {
	const d = new Date(date);
	return d.toLocaleDateString("en-US", {
		year: "numeric",
		month: "short",
		day: "numeric",
		hour: "numeric",
		minute: "2-digit",
	});
}
