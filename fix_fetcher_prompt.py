"""Restore the REAL system prompt for 'Unprocessed Case ID Fetcher' so it
actually calls the Database Query tool instead of hallucinating an empty
result. This was broken by an earlier placeholder system_prompt fix.
"""

import json
import psycopg2

GRAPH_NAME = "WF-Email-Triage-v7.9.1 (Copy)TadaTeam"
TARGET_NODE_ID = "0db8093d-3630-4c6a-aaff-640d9d3b21fe"  # Unprocessed Case ID Fetcher

REAL_PROMPT = """ROLE
You fetch the CRM Case GUIDs (case_id) of unprocessed cases from PostgreSQL table public.crm_ingested_cases.

You MUST call the attached Database Query tool. Do not answer without calling it.

Run exactly this query via the Database Query tool:

SELECT case_id
FROM crm_ingested_cases
WHERE is_processed = false
ORDER BY case_initiated_on ASC NULLS LAST
LIMIT 10;

After receiving the tool result, return a JSON object of the form:
{"results": ["<id1>", "<id2>", ...]}

RULES
- Always call the Database Query tool first; never answer without doing so.
- Include every case_id returned, verbatim; never truncate, reorder, or fabricate.
- If the tool returns zero rows, return {"results": []}.
- Do not include markdown, commentary, or explanations."""

conn = psycopg2.connect(
    host="localhost", port=6666, dbname="langgraph", user="postgres", password="postgres"
)
cur = conn.cursor()

cur.execute(
    "SELECT id, definition_json FROM graph_definitions WHERE name = %s AND is_latest = true LIMIT 1",
    (GRAPH_NAME,),
)
def_id, definition_json = cur.fetchone()
data = definition_json if isinstance(definition_json, dict) else json.loads(definition_json)

found = False
for node in data.get("nodes", []):
    if node.get("uniq_id") == TARGET_NODE_ID:
        node["agent_config"]["system_prompt"] = REAL_PROMPT
        node["prompt_template"] = REAL_PROMPT
        found = True
        break

if not found:
    raise SystemExit(f"Node {TARGET_NODE_ID} not found")

cur.execute(
    "UPDATE graph_definitions SET definition_json = %s WHERE id = %s",
    (json.dumps(data), def_id),
)
conn.commit()
print("Restored real system_prompt for Unprocessed Case ID Fetcher")
cur.close()
conn.close()
