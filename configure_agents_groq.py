"""One-off script: point every AGENT node in the imported workflow at the
local Groq deployment instead of the missing Azure OpenAI deployment.

Run with: python configure_agents_groq.py
"""

import urllib.request
import urllib.parse
import json

BASE_URL = "http://localhost:8000"
GRAPH_NAME = "WF-Email-Triage-v7.9.1 (Copy)TadaTeam"
GROQ_DEPLOYMENT_ID = "3ed28c0a-e4b3-4481-b504-e8f32dce8d53"

AGENT_NODE_IDS = [
    "426fade0-9bba-4fdb-bbec-bbd50ee3f5dd",
    "41e11522-64e3-48f2-8bc9-5229d1f09209",
    "a9d6338a-df84-4395-8301-f46b6cae5b4b",
    "a72bccc3-072a-4bf0-9d40-158193c2143c",
    "c3404ca4-84eb-4088-91e9-9bdfb287d436",
    "5d6cf77c-f46f-4041-90e7-0e2ad5652fde",
    "43eae7c3-446a-4b92-9dda-04efd7db0900",
    "34b928f7-48fd-4a54-a384-5468df6b6ece",
    "9233b18d-b225-4c99-8996-5113649122ea",
    "e1a70002-2222-4a22-8a22-000000000002",
    "e1a70003-3333-4a33-8a33-000000000003",
    "e1a70004-4444-4a44-8a44-000000000004",
    "e1a70005-5555-4a55-8a55-000000000005",
    "3b928915-3b23-441c-b954-54155b08c05d",
    "ba6bc419-a999-496a-a40a-41a04cee24ac",
    "66dd704f-f17f-40b6-ba60-768beb56c739",
    "0ffe3752-aab3-4074-bfa7-a14c881641f8",
    "0db8093d-3630-4c6a-aaff-640d9d3b21fe",
    "b8c6663e-446a-4895-8098-d0bbcee22d2e",
    "4860d27c-dba6-49ac-9e93-36d1de9bac45",
    "7f6306e5-baf4-4932-96f5-cc3f5ca9aca7",
    "e1a70001-1111-4a11-8a11-000000000001",
    "c5a5a74e-0b04-4b4a-9c50-68628fa1fa93",
    "02905598-806d-4d50-9e04-24930c3f681a",
    "927a1054-64a8-4b8f-be1e-645fcfea5e1a",
    "664e8d2d-7bf9-4188-84b9-b52a62bb8ca7",
    "ceced533-5dd0-4a83-8ba9-786dbfa58fa1",
]

LLM_CONFIG = {
    "provider": "openai",
    "model_name": "llama-3.3-70b-versatile",
    "model_type": "llm",
    "temperature": 0,
    "model_deployment_id": GROQ_DEPLOYMENT_ID,
}


def configure_node(node_id: str) -> None:
    payload = json.dumps(
        {
            "graph_name": GRAPH_NAME,
            "node_id": node_id,
            "llm_config": LLM_CONFIG,
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        f"{BASE_URL}/api/graph/node/llm/configure",
        data=payload,
        method="PUT",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
            print(f"OK  {node_id}: {body[:120]}")
    except urllib.error.HTTPError as e:
        print(f"FAIL {node_id}: {e.code} {e.read().decode('utf-8')[:200]}")


def save_graph() -> None:
    encoded_name = urllib.parse.quote(GRAPH_NAME, safe="")
    req = urllib.request.Request(
        f"{BASE_URL}/api/graph/save/{encoded_name}",
        data=b"",
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            print(f"SAVE OK: {resp.read().decode('utf-8')[:200]}")
    except urllib.error.HTTPError as e:
        print(f"SAVE FAIL: {e.code} {e.read().decode('utf-8')[:300]}")


if __name__ == "__main__":
    print(f"Configuring {len(AGENT_NODE_IDS)} agent nodes...")
    for nid in AGENT_NODE_IDS:
        configure_node(nid)
    save_graph()
    print("Done.")
