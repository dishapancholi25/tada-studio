"""Test Microsoft Fabric API connectivity with different auth methods.

Usage:
    # With a token you already have (e.g. from az account get-access-token):
    python -m backend.scripts.test_fabric_connection --token <TOKEN>

    # With a service principal (simulates deployed container):
    python -m backend.scripts.test_fabric_connection \
        --tenant-id <TENANT_ID> \
        --client-id <CLIENT_ID> \
        --client-secret <CLIENT_SECRET>

    # With DefaultAzureCredential (uses az login, managed identity, env vars, etc.):
    python -m backend.scripts.test_fabric_connection
"""

from __future__ import annotations

import argparse
import json
import sys

import requests

FABRIC_API_BASE = "https://api.fabric.microsoft.com/v1"
FABRIC_RESOURCE = "https://api.fabric.microsoft.com"


def get_token_from_credentials(tenant_id: str, client_id: str, client_secret: str) -> str:
    """Get a token using OAuth2 client credentials flow (service principal)."""
    print("\n[AUTH] Requesting token via client credentials flow...")
    print(f"  Tenant:    {tenant_id}")
    print(f"  Client ID: {client_id}")
    print(f"  Secret:    {'*' * min(len(client_secret), 8)}...")

    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    resp = requests.post(token_url, data={
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": f"{FABRIC_RESOURCE}/.default",
    }, timeout=15)

    if resp.status_code != 200:
        print(f"  [FAIL] Token request failed: {resp.status_code}")
        print(f"  {resp.text}")
        sys.exit(1)

    token = resp.json()["access_token"]
    print(f"  [OK] Got token ({len(token)} chars, expires_in={resp.json().get('expires_in')}s)")
    return token


def get_token_from_default_credential() -> str:
    """Get a token using DefaultAzureCredential (az login, managed identity, env vars)."""
    print("\n[AUTH] Requesting token via DefaultAzureCredential...")
    try:
        from azure.identity import DefaultAzureCredential
    except ImportError:
        print("  [FAIL] azure-identity not installed. Run: pip install azure-identity")
        sys.exit(1)

    try:
        credential = DefaultAzureCredential()
        token = credential.get_token(f"{FABRIC_RESOURCE}/.default")
        print(f"  [OK] Got token ({len(token.token)} chars)")
        return token.token
    except Exception as e:
        print(f"  [FAIL] {e}")
        print("  Hint: Run 'az login' first, or set AZURE_TENANT_ID/AZURE_CLIENT_ID/AZURE_CLIENT_SECRET env vars")
        sys.exit(1)


def test_api(token: str, method: str, path: str, description: str, body: dict | None = None) -> dict | None:
    """Make an authenticated Fabric API call and report the result."""
    url = f"{FABRIC_API_BASE}{path}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    print(f"\n[TEST] {description}")
    print(f"  {method} {url}")

    try:
        if method == "GET":
            resp = requests.get(url, headers=headers, timeout=30)
        elif method == "POST":
            resp = requests.post(url, headers=headers, json=body, timeout=30)
        else:
            print(f"  [SKIP] Unsupported method: {method}")
            return None
    except requests.RequestException as e:
        print(f"  [FAIL] Request error: {e}")
        return None

    if resp.status_code == 200:
        data = resp.json()
        print(f"  [OK] {resp.status_code} — Response received")
        return data
    elif resp.status_code == 401:
        print("  [FAIL] 401 Unauthorized — Token is invalid or expired")
    elif resp.status_code == 403:
        error = resp.json() if resp.text else {}
        error_code = error.get("errorCode", "")
        message = error.get("message", resp.text[:200])
        print(f"  [FAIL] 403 Forbidden — {error_code}")
        print(f"  {message}")
        if "ServicePrincipal" in message or "service principal" in message.lower():
            print("  >>> This likely means 'Allow service principals to use Power BI APIs' is DISABLED in tenant settings")
    else:
        print(f"  [FAIL] {resp.status_code}")
        try:
            print(f"  {json.dumps(resp.json(), indent=2)[:500]}")
        except Exception:
            print(f"  {resp.text[:500]}")

    return None


def main():
    parser = argparse.ArgumentParser(description="Test Fabric API connectivity")
    parser.add_argument("--token", help="Bearer token (from 'az account get-access-token')")
    parser.add_argument("--tenant-id", help="Azure tenant ID (for service principal auth)")
    parser.add_argument("--client-id", help="App registration client ID (for service principal auth)")
    parser.add_argument("--client-secret", help="App registration client secret (for service principal auth)")
    args = parser.parse_args()

    print("=" * 60)
    print("Microsoft Fabric API Connectivity Test")
    print("=" * 60)

    # Determine auth method
    if args.token:
        print("\n[MODE] Using provided bearer token")
        token = args.token
    elif args.tenant_id and args.client_id and args.client_secret:
        print("\n[MODE] Using service principal (client credentials)")
        token = get_token_from_credentials(args.tenant_id, args.client_id, args.client_secret)
    else:
        print("\n[MODE] Using DefaultAzureCredential (az login / env vars / managed identity)")
        token = get_token_from_default_credential()

    # Test 1: List workspaces
    result = test_api(token, "GET", "/workspaces", "List workspaces")
    if result:
        workspaces = result.get("value", [])
        print(f"  Found {len(workspaces)} workspace(s):")
        for ws in workspaces[:5]:
            print(f"    - {ws.get('displayName')} (id={ws.get('id')}, type={ws.get('type')})")
        if len(workspaces) > 5:
            print(f"    ... and {len(workspaces) - 5} more")

        # Test 2: List items in first workspace
        if workspaces:
            ws_id = workspaces[0]["id"]
            ws_name = workspaces[0]["displayName"]
            items_result = test_api(
                token, "GET", f"/workspaces/{ws_id}/items",
                f"List items in workspace '{ws_name}'"
            )
            if items_result:
                items = items_result.get("value", [])
                print(f"  Found {len(items)} item(s):")
                by_type: dict[str, int] = {}
                for item in items:
                    t = item.get("type", "Unknown")
                    by_type[t] = by_type.get(t, 0) + 1
                for t, count in sorted(by_type.items()):
                    print(f"    - {t}: {count}")

    # Test 3: Check MCP endpoint availability
    test_api(token, "GET", "/mcp/powerbi", "Check Power BI MCP endpoint")

    print("\n" + "=" * 60)
    print("Test complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
