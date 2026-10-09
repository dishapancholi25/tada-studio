/**
 * PII Entity Types supported by Presidio / LLM Guard Anonymize scanner.
 *
 * Complete list of 38+ entity types organized by category.
 * See: https://microsoft.github.io/presidio/supported_entities/
 */

export interface PIIEntityType {
	value: string;
	label: string;
	description: string;
	category: PIIEntityCategory;
}

export type PIIEntityCategory =
	| "financial"
	| "us_identifiers"
	| "international_ids"
	| "european_ids"
	| "personal_data"
	| "technical"
	| "other";

export const PII_CATEGORY_LABELS: Record<PIIEntityCategory, string> = {
	financial: "Financial",
	us_identifiers: "US Identifiers",
	international_ids: "International IDs",
	european_ids: "European IDs",
	personal_data: "Personal Data",
	technical: "Technical",
	other: "Other",
};

export const PII_ENTITY_TYPES: PIIEntityType[] = [
	// ── Financial ────────────────────────────────────────────────────────
	{
		value: "CREDIT_CARD",
		label: "Credit Card",
		description: "Credit card numbers (Visa, Mastercard, Amex, etc.)",
		category: "financial",
	},
	{
		value: "CREDIT_CARD_RE",
		label: "Credit Card (Regex)",
		description: "Credit card numbers detected via regex patterns",
		category: "financial",
	},
	{
		value: "CRYPTO",
		label: "Cryptocurrency",
		description: "Cryptocurrency wallet addresses (Bitcoin, Ethereum, etc.)",
		category: "financial",
	},
	{
		value: "IBAN_CODE",
		label: "IBAN",
		description: "International Bank Account Numbers",
		category: "financial",
	},
	{
		value: "US_BANK_NUMBER",
		label: "US Bank Account",
		description: "US bank account numbers",
		category: "financial",
	},

	// ── US Identifiers ───────────────────────────────────────────────────
	{
		value: "US_SSN",
		label: "US SSN",
		description: "US Social Security Numbers",
		category: "us_identifiers",
	},
	{
		value: "US_SSN_RE",
		label: "US SSN (Regex)",
		description: "US Social Security Numbers detected via regex",
		category: "us_identifiers",
	},
	{
		value: "US_DRIVER_LICENSE",
		label: "US Driver License",
		description: "US state driver license numbers",
		category: "us_identifiers",
	},
	{
		value: "US_PASSPORT",
		label: "US Passport",
		description: "US passport numbers",
		category: "us_identifiers",
	},
	{
		value: "US_ITIN",
		label: "US ITIN",
		description: "US Individual Taxpayer Identification Numbers",
		category: "us_identifiers",
	},
	{
		value: "MEDICAL_LICENSE",
		label: "Medical License",
		description: "Medical license numbers (DEA, NPI)",
		category: "us_identifiers",
	},

	// ── International IDs ────────────────────────────────────────────────
	{
		value: "UK_NHS",
		label: "UK NHS Number",
		description: "UK National Health Service numbers",
		category: "international_ids",
	},
	{
		value: "SG_NRIC_FIN",
		label: "Singapore NRIC/FIN",
		description: "Singapore National Registration Identity Card / Foreign Identification Number",
		category: "international_ids",
	},
	{
		value: "AU_ABN",
		label: "AU ABN",
		description: "Australian Business Number",
		category: "international_ids",
	},
	{
		value: "AU_ACN",
		label: "AU ACN",
		description: "Australian Company Number",
		category: "international_ids",
	},
	{
		value: "AU_TFN",
		label: "AU TFN",
		description: "Australian Tax File Number",
		category: "international_ids",
	},
	{
		value: "AU_MEDICARE",
		label: "AU Medicare",
		description: "Australian Medicare card numbers",
		category: "international_ids",
	},
	{
		value: "IN_PAN",
		label: "India PAN",
		description: "Indian Permanent Account Number",
		category: "international_ids",
	},
	{
		value: "IN_AADHAAR",
		label: "India Aadhaar",
		description: "Indian Aadhaar identification numbers",
		category: "international_ids",
	},
	{
		value: "NRP",
		label: "NRP",
		description: "Nationality, Religious or Political group affiliation",
		category: "international_ids",
	},

	// ── European IDs ─────────────────────────────────────────────────────
	{
		value: "ES_NIF",
		label: "Spain NIF",
		description: "Spanish tax identification number (NIF/NIE)",
		category: "european_ids",
	},
	{
		value: "IT_FISCAL_CODE",
		label: "Italy Fiscal Code",
		description: "Italian fiscal code (Codice Fiscale)",
		category: "european_ids",
	},
	{
		value: "IT_DRIVER_LICENSE",
		label: "Italy Driver License",
		description: "Italian driver license numbers",
		category: "european_ids",
	},
	{
		value: "IT_VAT_CODE",
		label: "Italy VAT Code",
		description: "Italian VAT identification number",
		category: "european_ids",
	},
	{
		value: "IT_PASSPORT",
		label: "Italy Passport",
		description: "Italian passport numbers",
		category: "european_ids",
	},
	{
		value: "IT_IDENTITY_CARD",
		label: "Italy Identity Card",
		description: "Italian national identity card numbers",
		category: "european_ids",
	},

	// ── Personal Data ────────────────────────────────────────────────────
	{
		value: "PERSON",
		label: "Person Name",
		description: "Names of individuals",
		category: "personal_data",
	},
	{
		value: "EMAIL_ADDRESS",
		label: "Email Address",
		description: "Email addresses",
		category: "personal_data",
	},
	{
		value: "EMAIL_ADDRESS_RE",
		label: "Email Address (Regex)",
		description: "Email addresses detected via regex patterns",
		category: "personal_data",
	},
	{
		value: "PHONE_NUMBER",
		label: "Phone Number",
		description: "Phone numbers in various international formats",
		category: "personal_data",
	},
	{
		value: "DATE_TIME",
		label: "Date / Time",
		description: "Date and time expressions",
		category: "personal_data",
	},
	{
		value: "LOCATION",
		label: "Location",
		description: "Physical addresses and location references",
		category: "personal_data",
	},
	{
		value: "AGE",
		label: "Age",
		description: "Age references",
		category: "personal_data",
	},

	// ── Technical ────────────────────────────────────────────────────────
	{
		value: "IP_ADDRESS",
		label: "IP Address",
		description: "IPv4 and IPv6 addresses",
		category: "technical",
	},
	{
		value: "UUID",
		label: "UUID",
		description: "Universally Unique Identifiers",
		category: "technical",
	},
	{
		value: "URL",
		label: "URL",
		description: "Web URLs and URIs",
		category: "technical",
	},

	// ── Other ────────────────────────────────────────────────────────────
	{
		value: "TITLE",
		label: "Title",
		description: "Personal titles (Mr., Dr., etc.)",
		category: "other",
	},
	{
		value: "ORGANIZATION",
		label: "Organization",
		description: "Organization and company names",
		category: "other",
	},
];

/** Lookup map: entity value -> PIIEntityType */
export const PII_ENTITY_TYPE_MAP: Record<string, PIIEntityType> = Object.fromEntries(
	PII_ENTITY_TYPES.map((t) => [t.value, t]),
);

/** Export just the values for easy checking */
export const PII_ENTITY_TYPE_VALUES = PII_ENTITY_TYPES.map((t) => t.value);

/** Default: empty array = all types */
export const DEFAULT_PII_ENTITY_TYPES: string[] = [];

/**
 * Backward-compatible MultiSelectOption format.
 * Used by any code that still expects the old shape.
 */
export const PII_ENTITY_TYPE_OPTIONS = PII_ENTITY_TYPES.map((t) => ({
	value: t.value,
	label: t.label,
	description: t.description,
}));
