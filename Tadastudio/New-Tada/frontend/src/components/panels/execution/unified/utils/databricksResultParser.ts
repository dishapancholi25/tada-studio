/**
 * Databricks-specific result parsing utilities for MCP execution panel
 */

export interface DatabricksTableResult {
	columns: string[];
	rows: any[][];
	is_truncated: boolean;
	row_count: number;
}

export type DatabricksResultType = "table" | "object" | "text" | "raw";

/**
 * Detect if a result is a Databricks Unity Catalog Functions table format ({ columns, rows })
 */
function isUnityCatalogTableResult(result: any): boolean {
	return (
		result != null &&
		Array.isArray(result.columns) &&
		Array.isArray(result.rows)
	);
}

/**
 * Detect if a result is a Databricks SQL MCP format (manifest + data_array)
 */
export function isDatabricksSqlResult(result: any): boolean {
	return (
		result != null &&
		result.manifest?.schema?.columns != null &&
		result.result?.data_array != null
	);
}

/**
 * Detect if a result is any supported Databricks table format
 */
export function isDatabricksTableResult(result: any): boolean {
	return isUnityCatalogTableResult(result) || isDatabricksSqlResult(result);
}

/**
 * Parse Databricks SQL MCP result into DatabricksTableResult
 */
function parseSqlResult(result: any): DatabricksTableResult {
	const schemaColumns = result.manifest.schema.columns;
	const columns = [...schemaColumns]
		.sort((a: any, b: any) => a.position - b.position)
		.map((c: any) => c.name);

	const rows = (result.result.data_array || []).map((row: any) =>
		(row.values || []).map((v: any) => v.string_value ?? null),
	);

	return {
		columns,
		rows,
		is_truncated: result.manifest.truncated === true,
		row_count: rows.length,
	};
}

/**
 * Parse Databricks table result into structured format
 */
export function parseDatabricksTableResult(
	result: any,
): DatabricksTableResult | null {
	if (isUnityCatalogTableResult(result)) {
		return {
			columns: result.columns,
			rows: result.rows,
			is_truncated: result.is_truncated === true,
			row_count: result.rows.length,
		};
	}

	if (isDatabricksSqlResult(result)) {
		return parseSqlResult(result);
	}

	return null;
}

/**
 * Detect the Databricks result type
 */
export function getDatabricksResultType(result: any): DatabricksResultType {
	if (!result) return "raw";
	if (isDatabricksTableResult(result)) return "table";
	if (typeof result === "string") return "text";
	if (typeof result === "object") return "object";
	return "raw";
}

/**
 * Format a cell value for display in a table
 */
export function formatCellValue(value: any): string {
	if (value === null || value === undefined) return "\u2014";
	if (typeof value === "number") return value.toLocaleString();
	if (typeof value === "boolean") return value ? "true" : "false";
	if (typeof value === "object") return JSON.stringify(value);
	return String(value);
}
