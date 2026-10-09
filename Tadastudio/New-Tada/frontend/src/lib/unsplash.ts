/**
 * Unsplash API integration for fetching category images
 */

import type { TemplateCategory } from "@/types/library";

/**
 * Mapping of categories to Unsplash image URLs
 * Using direct photo URLs for reliability
 */
export const CATEGORY_IMAGES: Record<TemplateCategory, string> = {
	Finance:
		"https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=800&auto=format&fit=crop&q=75",
	Sales:
		"https://images.unsplash.com/photo-1556761175-b413da4baf72?w=800&auto=format&fit=crop&q=75",
	Recruitment:
		"https://images.unsplash.com/photo-1521791136064-7986c2920216?w=800&auto=format&fit=crop&q=75",
	Marketing:
		"https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800&auto=format&fit=crop&q=75",
	"Customer Service":
		"https://images.unsplash.com/photo-1556742111-a301076d9d18?w=800&auto=format&fit=crop&q=75",
	Education:
		"https://images.unsplash.com/photo-1503676260728-1c00da094a0b?w=800&auto=format&fit=crop&q=75",
	Operations:
		"https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?w=800&auto=format&fit=crop&q=75",
	Analytics:
		"https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=800&auto=format&fit=crop&q=75",
	Technology:
		"https://images.unsplash.com/photo-1518770660439-4636190af475?w=800&auto=format&fit=crop&q=75",
	"Risk & Compliance":
		"https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=800&auto=format&fit=crop&q=75",
	"Human Resources":
		"https://images.unsplash.com/photo-1552664730-d307ca884978?w=800&auto=format&fit=crop&q=75",
	Cybersecurity:
		"https://images.unsplash.com/photo-1614064641938-3bbee52942c7?w=800&auto=format&fit=crop&q=75",
	General:
		"https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=800&auto=format&fit=crop&q=75",
};

/**
 * Get the image URL for a category
 * Returns the direct Unsplash photo URL
 */
export function getCategoryImageUrl(category: TemplateCategory): string {
	return CATEGORY_IMAGES[category] || CATEGORY_IMAGES.General;
}

/**
 * Get image URL with explicit dimensions
 */
export function getCategoryImageUrlWithDimensions(
	category: TemplateCategory,
	width: number = 800,
	height: number = 600,
): string {
	const baseUrl = CATEGORY_IMAGES[category] || CATEGORY_IMAGES.General;

	// Remove existing width parameter if present and add new dimensions
	const url = new URL(baseUrl);
	url.searchParams.set("w", width.toString());
	url.searchParams.set("h", height.toString());
	url.searchParams.set("fit", "crop");

	return url.toString();
}
