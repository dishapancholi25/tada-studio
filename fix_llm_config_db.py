"""Directly patch definition_json in Postgres to add Groq LLM config
to every AGENT node, bypassing the broken save-after-reload API flow.

Run with: python fix_llm_config_db.py
"""

import json
import psycopg2

GRAPH_NAME = "WF-Email-Triage-v7.9.1 (Copy)TadaTeam"
GROQ_DEPLOYMENT_ID = "3ed28c0a-e4b3-4481-b504-e8f32dce8d53"

LLM_CONFIG = {
    "provider": "openai",
    "model_name": "openai/gpt-oss-20b",
    "model_type": "llm",
    "temperature": 0,
    "max_tokens": None,
    "top_p": None,
    "reasoning_effort": None,
    "api_base": None,
    "api_version": None,
    "deployment_name": None,
    "api_key_env_var": "OPENAI_API_KEY",
    "base_url_env_var": None,
    "model_deployment_id": GROQ_DEPLOYMENT_ID,
    "display_name": "Groq Llama 3.3",
    "credentials": {},
    "config": {},
    "additional_params": {},
    "supports_function_calling": True,
    "supports_streaming": True,
    "timeout": 30,
    "organization_id": None,
    "max_retries": 3,
}

conn = psycopg2.connect(
    host="localhost",
    port=6666,
    dbname="langgraph",
    user="postgres",
    password="postgres",
)
conn.autocommit = False
cur = conn.cursor()

cur.execute(
    "SELECT id, definition_json FROM graph_definitions "
    "WHERE name = %s AND is_latest = true LIMIT 1",
    (GRAPH_NAME,),
)
row = cur.fetchone()
if not row:
    raise SystemExit(f"No graph_definitions row found for name={GRAPH_NAME!r}")

def_id, definition_json = row
# psycopg2 may already give us a dict for JSON columns
data = definition_json if isinstance(definition_json, dict) else json.loads(definition_json)

updated_count = 0
for node in data.get("nodes", []):
    if node.get("type") == "AGENT":
        if not node.get("agent_config"):
            node["agent_config"] = {}
        node["agent_config"]["llm_config"] = LLM_CONFIG
        if not node["agent_config"].get("system_prompt"):
            node["agent_config"]["system_prompt"] = (
                node.get("description")
                or f"You are the {node.get('name', 'agent')}. "
                "Process the input and return a JSON object with your result."
            )
        if not node.get("prompt_template"):
            node["prompt_template"] = node["agent_config"]["system_prompt"]
        updated_count += 1

cur.execute(
    "UPDATE graph_definitions SET definition_json = %s WHERE id = %s",
    (json.dumps(data), def_id),
)
conn.commit()
print(f"Updated {updated_count} AGENT nodes in graph_definitions id={def_id}")

cur.close()
conn.close()
