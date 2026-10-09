import { NextResponse } from "next/server";

export async function GET() {
	// Runtime API URL configuration
	// If RUNTIME_API_URL is set, use it (for separate domain deployments like Azure)
	// Otherwise, use empty string for relative paths (reverse proxy deployments)
	const apiUrl = process.env.RUNTIME_API_URL || "";

	const config = {
		apiUrl,
		deployment: apiUrl ? "separate-domains" : "reverse-proxy",
		timestamp: new Date().toISOString(),
	};

	return NextResponse.json(config, {
		headers: {
			"Cache-Control": "public, max-age=300, s-maxage=300", // Cache for 5 minutes
		},
	});
}
