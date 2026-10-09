"use client";

interface DatabaseTypeIconProps {
	type: string;
	size?: "sm" | "md" | "lg";
	className?: string;
}

interface DbStyle {
	label: string;
	color: string;
	bgColor: string;
}

const DB_STYLES: Record<string, DbStyle> = {
	postgres: {
		label: "PG",
		color: "#336791",
		bgColor: "rgba(51, 103, 145, 0.15)",
	},
	mysql: {
		label: "My",
		color: "#00758F",
		bgColor: "rgba(0, 117, 143, 0.15)",
	},
	mongodb: {
		label: "Mg",
		color: "#47A248",
		bgColor: "rgba(71, 162, 72, 0.15)",
	},
	sqlite: {
		label: "SL",
		color: "#003B57",
		bgColor: "rgba(0, 59, 87, 0.2)",
	},
	mssql: {
		label: "MS",
		color: "#CC2927",
		bgColor: "rgba(204, 41, 39, 0.15)",
	},
	oracle: {
		label: "Or",
		color: "#F80000",
		bgColor: "rgba(248, 0, 0, 0.12)",
	},
};

const SIZE_MAP = {
	sm: { container: "w-8 h-8 rounded-md", text: "text-[10px]" },
	md: { container: "w-10 h-10 rounded-lg", text: "text-xs" },
	lg: { container: "w-12 h-12 rounded-xl", text: "text-sm" },
};

export default function DatabaseTypeIcon({
	type,
	size = "md",
	className = "",
}: DatabaseTypeIconProps) {
	const style = DB_STYLES[type.toLowerCase()] ?? {
		label: type.slice(0, 2).toUpperCase(),
		color: "var(--color-text-muted)",
		bgColor: "var(--color-surface)",
	};
	const sizeStyle = SIZE_MAP[size];

	return (
		<div
			className={`${sizeStyle.container} flex items-center justify-center font-bold flex-shrink-0 ${className}`}
			style={{
				background: style.bgColor,
				color: style.color,
				border: `1px solid ${style.color}33`,
			}}
			title={type.charAt(0).toUpperCase() + type.slice(1)}
		>
			<span className={sizeStyle.text}>{style.label}</span>
		</div>
	);
}

export function getDatabaseTypeLabel(type: string): string {
	const labels: Record<string, string> = {
		postgres: "PostgreSQL",
		mysql: "MySQL",
		mongodb: "MongoDB",
		sqlite: "SQLite",
		mssql: "SQL Server",
		oracle: "Oracle",
	};
	return labels[type.toLowerCase()] ?? type;
}
