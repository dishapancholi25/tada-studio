"use client";

interface UserAvatarProps {
	name: string | null;
	size?: "sm" | "md" | "lg";
	className?: string;
}

const sizeClasses = {
	sm: "w-8 h-8 text-sm",
	md: "w-10 h-10 text-base",
	lg: "w-12 h-12 text-lg",
};

/**
 * User avatar component that displays the first letter of the user's name.
 *
 * Uses a gradient background for visual appeal.
 */
export default function UserAvatar({
	name,
	size = "md",
	className = "",
}: UserAvatarProps) {
	// Get first letter of name, fallback to "U" for User
	const initial = name?.trim().charAt(0).toUpperCase() || "U";

	return (
		<div
			className={`flex items-center justify-center rounded-full font-semibold bg-gradient-to-br from-[color:var(--color-primary)]/20 to-[color:var(--color-accent)]/15 ${sizeClasses[size]} ${className}`}
			style={{
				color: "var(--color-primary)",
			}}
		>
			{initial}
		</div>
	);
}
