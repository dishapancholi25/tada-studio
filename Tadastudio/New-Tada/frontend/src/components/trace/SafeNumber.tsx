"use client";

import React from "react";

interface SafeNumberProps {
	value: any;
	decimals: number;
	prefix?: string;
	suffix?: string;
	fallback?: string;
	label?: string;
}

export default function SafeNumber({
	value,
	decimals,
	prefix = "",
	suffix = "",
	fallback = "0",
	label = "",
}: SafeNumberProps) {
	const formatNumber = () => {
		try {
			// Log the input for debugging
			if (label) {
				console.log(
					`[SafeNumber] ${label} - value:`,
					value,
					"type:",
					typeof value,
				);
			}

			// Handle null/undefined
			if (value === null || value === undefined) {
				return fallback;
			}

			// Convert to number if string
			let num = value;
			if (typeof value === "string") {
				num = parseFloat(value);
			}

			// Check if it's a valid number
			if (typeof num !== "number" || isNaN(num) || !isFinite(num)) {
				console.warn(`[SafeNumber] Invalid number for ${label}:`, value);
				return fallback;
			}

			// Format with toFixed
			return num.toFixed(decimals);
		} catch (error) {
			console.error(
				`[SafeNumber] Error formatting ${label}:`,
				error,
				"value:",
				value,
			);
			return fallback;
		}
	};

	return (
		<>
			{prefix}
			{formatNumber()}
			{suffix}
		</>
	);
}
