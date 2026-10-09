"""Create minimal Altair business schema + seed data so the imported
WF-Email-Triage workflow's FOR_EACH loop has real cases to iterate over,
enabling concurrent execution of its 35-node body (where Bug 7705's
node-completion race condition is most likely to surface).

Schema inferred from the SQL statements embedded in the workflow's agent
prompts (Case Insert Agent, Customer Upsert Agent, Triage Insert Agent,
Classification Insert Agent, Taxonomy Validation Sub-Agent).
"""

import psycopg2

conn = psycopg2.connect(
    host="localhost", port=6666, dbname="langgraph", user="postgres", password="postgres"
)
conn.autocommit = False
cur = conn.cursor()

DDL = """
CREATE TABLE IF NOT EXISTS crm_ingested_cases (
    crm_ingested_case_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL DEFAULT gen_random_uuid(),
    business_operating_group TEXT,
    case_initiated_on TEXT,
    case_origin TEXT,
    case_owner TEXT,
    case_ref_no TEXT,
    case_resolution_comments TEXT,
    case_status TEXT,
    case_sub_type TEXT,
    case_type TEXT,
    cif_number TEXT,
    created_by TEXT,
    created_on TIMESTAMPTZ DEFAULT now(),
    customer_name TEXT,
    customer_segment TEXT,
    customer_product_account TEXT,
    customer_product_contact TEXT,
    description TEXT,
    owner TEXT,
    preferred_language TEXT,
    product_type TEXT,
    service_type TEXT,
    source_mailbox TEXT,
    sub_product_type TEXT,
    is_processed BOOLEAN DEFAULT false
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cif TEXT,
    customer_name TEXT,
    customer_email_id TEXT,
    additional_contact TEXT,
    preferred_language TEXT,
    verified BOOLEAN DEFAULT false,
    account_number TEXT,
    customer_segment TEXT,
    individual_or_company TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS case_types (
    case_type_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_type_name TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS service_type (
    service_type_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_type_id UUID REFERENCES case_types(case_type_id),
    service_type_name TEXT
);

CREATE TABLE IF NOT EXISTS case_sub_type (
    case_sub_type_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_type_id UUID REFERENCES service_type(service_type_id),
    case_sub_type_name TEXT
);

CREATE TABLE IF NOT EXISTS cases (
    case_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(customer_id),
    case_origin TEXT,
    email_body TEXT,
    translated_email_body TEXT,
    crm_case_reference_number TEXT,
    crm_case_guid UUID,
    crm_status TEXT,
    crm_created_dt TEXT,
    classification_id UUID,
    attachment_id UUID,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ai_sentiment (
    sentiment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sentiment_name TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS ai_tone (
    tone_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tone_name TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS priorities (
    priority_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    priority_name TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS triage_statuses (
    triage_status_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    triage_status_name TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS triages (
    triage_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID REFERENCES cases(case_id),
    triage_status_id UUID,
    source TEXT,
    product_type TEXT,
    sub_product_type TEXT,
    crm_product_type_guid UUID,
    crm_sub_product_type_guid UUID,
    rejection_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ai_classifications (
    classification_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    triage_id UUID REFERENCES triages(triage_id),
    predicted_case_type_id UUID,
    predicted_service_type_id UUID,
    predicted_case_sub_type_id UUID,
    case_subtype_id UUID,
    sentiment_id UUID,
    tone_id UUID,
    priority_id UUID,
    confidence_score NUMERIC,
    reasoning TEXT,
    risk TEXT,
    repeat TEXT,
    summary TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
"""

cur.execute(DDL)

# --- Seed minimal taxonomy so classification lookups succeed ---
cur.execute(
    "INSERT INTO case_types (case_type_name) VALUES ('Complaint'), ('Inquiry'), "
    "('Service Request'), ('Feedback') ON CONFLICT DO NOTHING RETURNING case_type_id, case_type_name"
)
case_types = {name: cid for cid, name in cur.fetchall()}
if not case_types:
    cur.execute("SELECT case_type_id, case_type_name FROM case_types")
    case_types = {name: cid for cid, name in cur.fetchall()}

cur.execute(
    "INSERT INTO service_type (case_type_id, service_type_name) VALUES (%s, 'Card Services') "
    "RETURNING service_type_id",
    (case_types.get("Complaint"),),
)
service_type_id = cur.fetchone()[0]

cur.execute(
    "INSERT INTO case_sub_type (service_type_id, case_sub_type_name) VALUES (%s, 'Card Blocked') "
    "RETURNING case_sub_type_id",
    (service_type_id,),
)

for name in ["Angry / Escalated", "Frustrated / Dissatisfied", "Concerned / Anxious", "Neutral", "Positive"]:
    cur.execute("INSERT INTO ai_sentiment (sentiment_name) VALUES (%s) ON CONFLICT DO NOTHING", (name,))
cur.execute("INSERT INTO ai_tone (tone_name) VALUES ('Neutral') ON CONFLICT DO NOTHING")
for name in ["High", "Medium", "Low"]:
    cur.execute("INSERT INTO priorities (priority_name) VALUES (%s) ON CONFLICT DO NOTHING", (name,))
cur.execute(
    "INSERT INTO triage_statuses (triage_status_name) VALUES ('Pending Verification') ON CONFLICT DO NOTHING"
)

# --- Seed a handful of dummy CRM cases so FOR_EACH has items to loop over ---
DUMMY_CASES = [
    ("Test complaint about ATM not dispensing cash correctly.", "REF-TEST-001", "Test Customer One", "1234567"),
    ("Test inquiry about fixed deposit interest rates.", "REF-TEST-002", "Test Customer Two", "1234568"),
    ("Test service request to issue a new debit card.", "REF-TEST-003", "Test Customer Three", "1234569"),
    ("Test feedback praising quick loan approval process.", "REF-TEST-004", "Test Customer Four", "1234570"),
    ("Test complaint about unauthorized transaction on credit card.", "REF-TEST-005", "Test Customer Five", "1234571"),
]

for description, ref_no, cust_name, cif in DUMMY_CASES:
    cur.execute(
        """
        INSERT INTO crm_ingested_cases
            (business_operating_group, case_initiated_on, case_origin, case_owner,
             case_ref_no, case_status, cif_number, created_by, customer_name,
             description, owner, preferred_language, is_processed)
        VALUES
            ('Retail Banking', now()::text, 'Email', 'System',
             %s, 'New', %s, 'System', %s,
             %s, 'System', 'English', false)
        """,
        (ref_no, cif, cust_name, description),
    )

conn.commit()
cur.execute("SELECT count(*) FROM crm_ingested_cases WHERE is_processed = false")
print(f"Seeded schema. Unprocessed cases available: {cur.fetchone()[0]}")

cur.close()
conn.close()
