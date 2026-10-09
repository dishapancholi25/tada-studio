"use client";

import clsx from "clsx";
import React from "react";

interface ProviderLogoProps {
	className?: string;
}

const baseSvg = "h-6 w-6 drop-shadow-[0_6px_12px_rgba(0,0,0,0.35)]";

export function AzureOpenAILogo({ className }: ProviderLogoProps) {
	return (
		<svg
			viewBox="0 0 48 48"
			className={clsx(baseSvg, className)}
			role="img"
			aria-label="Azure OpenAI"
		>
			<defs>
				<linearGradient id="azureGradient" x1="0%" y1="0%" x2="100%" y2="100%">
					<stop offset="0%" stopColor="#00A0F4" />
					<stop offset="100%" stopColor="#0763C5" />
				</linearGradient>
			</defs>
			<path d="M6 40L18.5 8.2h8.4L15.5 40z" fill="url(#azureGradient)" />
			<path d="M26 8.2h7.6L42 40h-8.8z" fill="#33BBFF" />
		</svg>
	);
}

export function OpenAILogo({ className }: ProviderLogoProps) {
	return (
		<svg
			viewBox="0 0 48 48"
			className={clsx(baseSvg, className)}
			role="img"
			aria-label="OpenAI"
		>
			<defs>
				<linearGradient id="openaiGradient" x1="20%" y1="0%" x2="80%" y2="100%">
					<stop offset="0%" stopColor="#B68DFF" />
					<stop offset="100%" stopColor="#6C3BFF" />
				</linearGradient>
			</defs>
			<path
				d="M24 6.5c-3.2 0-6.2 1.2-8.6 3.3l-1 .9-3.4-.2a2 2 0 0 0-2.1 2.6l1.1 3.2-.7 1.1A11.6 11.6 0 0 0 7.5 24c0 3.2 1.2 6.2 3.3 8.6l1 .9-.2 3.4a2 2 0 0 0 2.6 2.1l3.2-1.1 1.1.7A11.6 11.6 0 0 0 24 40.5c3.2 0 6.2-1.2 8.6-3.3l1-.9 3.4.2a2 2 0 0 0 2.1-2.6l-1.1-3.2.7-1.1A11.6 11.6 0 0 0 40.5 24c0-3.2-1.2-6.2-3.3-8.6l-1-.9.2-3.4a2 2 0 0 0-2.6-2.1l-3.2 1.1-1.1-.7A11.6 11.6 0 0 0 24 6.5Z"
				fill="url(#openaiGradient)"
				opacity={0.18}
			/>
			<path
				d="M24 12c-6.6 0-12 5.4-12 12 0 6.5 5.4 12 12 12 6.5 0 12-5.5 12-12 0-6.6-5.5-12-12-12Zm5.8 19.2-5.1 3a1 1 0 0 1-1 0l-5.1-3a1 1 0 0 1-.5-.87v-6L18 21l6-3.4a1 1 0 0 1 1 0l6 3.4.9 3.36v6c0 .37-.2.7-.5.87Z"
				fill="url(#openaiGradient)"
			/>
			<path
				d="M24 20.2 21 22v4l3 1.8 3-1.8V22l-3-1.8Z"
				fill="#130B2B"
				opacity={0.65}
			/>
		</svg>
	);
}

export function AnthropicLogo({ className }: ProviderLogoProps) {
	return (
		<svg
			viewBox="0 0 48 48"
			className={clsx(baseSvg, className)}
			role="img"
			aria-label="Anthropic"
		>
			<defs>
				<linearGradient
					id="anthropicGradient"
					x1="0%"
					y1="0%"
					x2="100%"
					y2="100%"
				>
					<stop offset="0%" stopColor="#FF8A65" />
					<stop offset="100%" stopColor="#FF4F5E" />
				</linearGradient>
			</defs>
			<circle
				cx="24"
				cy="24"
				r="18"
				fill="url(#anthropicGradient)"
				opacity={0.85}
			/>
			<path
				d="M24 14 15 34h4l1.8-4.5h6.4L29 34h4l-9-20Zm1.6 11.5H22.4L24 20l1.6 5.5Z"
				fill="#1C0B08"
				opacity={0.78}
			/>
		</svg>
	);
}

export function ProviderLogo({
	provider,
	className,
}: {
	provider: string;
	className?: string;
}) {
	switch (provider) {
		case "azure_openai":
			return <AzureOpenAILogo className={className} />;
		case "openai":
			return <OpenAILogo className={className} />;
		case "anthropic":
			return <AnthropicLogo className={className} />;
		default:
			return (
				<span
					className={clsx(
						"h-6 w-6 rounded-lg bg-[rgba(var(--color-primary-rgb),0.18)] flex items-center justify-center text-[rgba(var(--color-primary-rgb),0.85)] font-bold text-xs",
						className,
					)}
				>
					AI
				</span>
			);
	}
}
