import type { NextConfig } from "next";

const nextConfig: NextConfig = {
	// Enable experimental features for better performance
	experimental: {
		// Enable optimizePackageImports for common packages
		optimizePackageImports: ["reactflow", "framer-motion", "date-fns"],
	},

	// Enable compression
	compress: true,

	// Optimize images
	images: {
		formats: ["image/avif", "image/webp"],
	},

	// Allow warnings in production build (for performance testing)
	eslint: {
		ignoreDuringBuilds: true,
	},

	// Proxy API calls to backend
	async rewrites() {
		// Only apply rewrites in development
		// if (process.env.NODE_ENV === "development") {
		// Use 'backend' when running in Docker
		const backendUrl = process.env.BACKEND_URL || "http://backend:8000";
		return [
			{
				source: "/api/:path*",
				destination: `${backendUrl}/api/:path*`,
			},
		];
		// }
		return [];
	},
};

export default nextConfig;
