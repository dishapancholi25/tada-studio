"""Add more dummy CRM cases to push FOR_EACH concurrency closer to its
configured limit (15) with sustained parallel load, to increase the chance
of hitting a timing-dependent node-completion race condition.
"""

import psycopg2

conn = psycopg2.connect(
    host="localhost", port=6666, dbname="langgraph", user="postgres", password="postgres"
)
cur = conn.cursor()

TEMPLATES = [
    "Test complaint: unauthorized deduction of AED {n} from my account.",
    "Test inquiry: what are the current minimum balance requirements?",
    "Test service request: please issue a replacement debit card.",
    "Test feedback: your mobile app update is excellent, well done.",
    "Test complaint: ATM did not dispense cash but account was debited AED {n}.",
    "Test inquiry: eligibility criteria for a personal loan of AED {n}.",
    "Test service request: activate international usage on my credit card.",
    "Test complaint: online banking login keeps failing repeatedly.",
    "Test inquiry: what is the current fixed deposit interest rate?",
    "Test service request: update my registered mobile number.",
]

N_NEW_CASES = 40

for i in range(N_NEW_CASES):
    template = TEMPLATES[i % len(TEMPLATES)]
    description = template.format(n=100 + i * 7)
    ref_no = f"REF-TEST-{100 + i}"
    cif = f"9{1000000 + i}"
    cust_name = f"Load Test Customer {i}"

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
print(f"Seeded {N_NEW_CASES} more cases. Total unprocessed now: {cur.fetchone()[0]}")

cur.close()
conn.close()
