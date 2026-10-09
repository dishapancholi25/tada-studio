/**
 * Compliance-specific PII entity type presets.
 *
 * Each preset maps to a major data protection regulation and includes
 * the exact entity types relevant to that framework.
 */

export interface CompliancePreset {
	id: string;
	label: string;
	shortLabel: string;
	description: string;
	regulation?: string;
	references?: string;
	entityTypes: string[];
}

// ─── Quick-action presets ────────────────────────────────────────────────────

export const RECOMMENDED_ENTITY_TYPES: string[] = [
	"CREDIT_CARD",
	"EMAIL_ADDRESS",
	"PERSON",
	"PHONE_NUMBER",
	"US_SSN",
	"CRYPTO",
	"IBAN_CODE",
	"IP_ADDRESS",
];

// ─── Compliance framework presets ────────────────────────────────────────────

export const COMPLIANCE_PRESETS: CompliancePreset[] = [
	{
		id: "gdpr",
		label: "GDPR (EU Data Protection)",
		shortLabel: "GDPR",
		description: "EU General Data Protection Regulation",
		regulation: "EU General Data Protection Regulation",
		references: "GDPR Article 4(1), Article 9",
		entityTypes: [
			"PERSON",
			"EMAIL_ADDRESS",
			"PHONE_NUMBER",
			"IP_ADDRESS",
			"LOCATION",
			"DATE_TIME",
			"NRP",
			"IBAN_CODE",
			"UK_NHS",
			"ES_NIF",
			"IT_FISCAL_CODE",
			"IT_DRIVER_LICENSE",
			"IT_VAT_CODE",
			"IT_PASSPORT",
			"IT_IDENTITY_CARD",
		],
	},
	{
		id: "hipaa",
		label: "HIPAA (US Healthcare)",
		shortLabel: "HIPAA",
		description: "Health Insurance Portability and Accountability Act",
		regulation: "Health Insurance Portability and Accountability Act",
		references: "45 CFR 160.103, 45 CFR 164.514(b)(2)",
		entityTypes: [
			"PERSON",
			"PHONE_NUMBER",
			"EMAIL_ADDRESS",
			"US_SSN",
			"MEDICAL_LICENSE",
			"DATE_TIME",
			"LOCATION",
			"IP_ADDRESS",
			"URL",
			"US_DRIVER_LICENSE",
			"US_PASSPORT",
			"US_BANK_NUMBER",
			"CREDIT_CARD",
		],
	},
	{
		id: "pci-dss",
		label: "PCI-DSS (Payment Card Industry)",
		shortLabel: "PCI-DSS",
		description: "Payment Card Industry Data Security Standard",
		regulation: "Payment Card Industry Data Security Standard",
		references: "PCI-DSS v4.0 Requirement 3, Requirement 4",
		entityTypes: [
			"CREDIT_CARD",
			"CREDIT_CARD_RE",
			"CRYPTO",
			"PERSON",
			"EMAIL_ADDRESS",
			"PHONE_NUMBER",
			"LOCATION",
			"IP_ADDRESS",
			"US_SSN",
			"IBAN_CODE",
			"US_BANK_NUMBER",
		],
	},
	{
		id: "ccpa",
		label: "CCPA (California Consumer Privacy)",
		shortLabel: "CCPA",
		description: "California Consumer Privacy Act",
		regulation: "California Consumer Privacy Act",
		references: "Cal. Civ. Code 1798.140(o)(1)",
		entityTypes: [
			"PERSON",
			"EMAIL_ADDRESS",
			"PHONE_NUMBER",
			"US_SSN",
			"US_DRIVER_LICENSE",
			"US_PASSPORT",
			"IP_ADDRESS",
			"LOCATION",
			"CREDIT_CARD",
			"US_BANK_NUMBER",
		],
	},
	{
		id: "pipeda",
		label: "PIPEDA (Canadian Privacy)",
		shortLabel: "PIPEDA",
		description: "Personal Information Protection and Electronic Documents Act",
		regulation: "Personal Information Protection and Electronic Documents Act",
		references: "PIPEDA Schedule 1",
		entityTypes: [
			"PERSON",
			"EMAIL_ADDRESS",
			"PHONE_NUMBER",
			"LOCATION",
			"DATE_TIME",
			"IP_ADDRESS",
			"CREDIT_CARD",
			"CRYPTO",
			"SG_NRIC_FIN",
		],
	},
];

/** Lookup map: preset id -> CompliancePreset */
export const COMPLIANCE_PRESET_MAP: Record<string, CompliancePreset> = Object.fromEntries(
	COMPLIANCE_PRESETS.map((p) => [p.id, p]),
);
