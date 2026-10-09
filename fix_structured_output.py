"""Add back the structured_outputs schema for 'Unprocessed Case ID Fetcher'
so its output has a 'results' field, which 'For each 1' depends on
(field_path: fields.results).
"""

import json
import psycopg2

GRAPH_NAME = "WF-Email-Triage-v7.9.1 (Copy)TadaTeam"
TARGET_NODE_ID = "0db8093d-3630-4c6a-aaff-640d9d3b21fe"  # Unprocessed Case ID Fetcher

STRUCTURED_OUTPUTS = [
    {
        "id": "5kbxhba55",
        "model_name": "crm_ingested_cases",
        "description": "Agent output schema",
        "fields": [
            {
                "id": "tbhruq5mf",
                "name": "results",
                "description": "all rows returned by the database query",
                "type": "List[str]",
                "required": True,
            }
        ],
    }
]

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
        node["agent_config"]["structured_outputs"] = STRUCTURED_OUTPUTS
        found = True
        break

if not found:
    raise SystemExit(f"Node {TARGET_NODE_ID} not found")

cur.execute(
    "UPDATE graph_definitions SET definition_json = %s WHERE id = %s",
    (json.dumps(data), def_id),
)
conn.commit()
print(f"Added structured_outputs to node {TARGET_NODE_ID}")
cur.close()
conn.close()
