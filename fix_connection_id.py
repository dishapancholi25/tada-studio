"""Replace the old UAT datasource connection_id with our new local
Postgres connection everywhere it appears in the workflow definition.
"""

import json
import psycopg2

GRAPH_NAME = "WF-Email-Triage-v7.9.1 (Copy)TadaTeam"
OLD_CONNECTION_ID = "db384f35-6055-43f0-91be-1c5ec013084d"
NEW_CONNECTION_ID = "ecfbbd01-494c-4d55-b40d-cebc096ef0b3"

conn = psycopg2.connect(
    host="localhost", port=6666, dbname="langgraph", user="postgres", password="postgres"
)
cur = conn.cursor()

cur.execute(
    "SELECT id, definition_json FROM graph_definitions WHERE name = %s AND is_latest = true LIMIT 1",
    (GRAPH_NAME,),
)
def_id, definition_json = cur.fetchone()

# Simplest reliable way to replace every occurrence regardless of nesting depth:
raw = json.dumps(definition_json if isinstance(definition_json, dict) else json.loads(definition_json))
count = raw.count(OLD_CONNECTION_ID)
raw = raw.replace(OLD_CONNECTION_ID, NEW_CONNECTION_ID)
data = json.loads(raw)

cur.execute(
    "UPDATE graph_definitions SET definition_json = %s WHERE id = %s",
    (json.dumps(data), def_id),
)
conn.commit()
print(f"Replaced {count} occurrence(s) of the old connection_id with the local one")
cur.close()
conn.close()
