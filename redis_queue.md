# What We Worked On Today

We worked through several connected local-development problems involving Docker, certificates, Redis, backend execution, frontend loading, and workflow status.

## 1. Backend Docker build failed on certificates

The first backend build failed while installing Microsoft ODBC:

```text
curl: (60) SSL certificate problem: unable to get local issuer certificate
gpg: no valid OpenPGP data found
```

The failure happened in `Dockerfile` while downloading:

```text
https://packages.microsoft.com/keys/microsoft.asc
```

The Docker image was behind the corporate Zscaler/Mashreq TLS proxy, but the container did not trust the corporate certificate chain.

### Initial fix

The Dockerfile was registering custom certificates too late. It tried to download Microsoft and Node.js packages before running:

```bash
update-ca-certificates
```

We moved certificate installation and registration earlier, before any external HTTPS downloads.

We also added these variables:

```dockerfile
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV PIP_CERT=/etc/ssl/certs/ca-certificates.crt
```

The builder stage had the same issue while running `uv sync`, so we added:

```dockerfile
ENV UV_NATIVE_TLS=1
```

That forces `uv` to use the operating system certificate store.

## 2. Corporate certificates were in unsupported formats

The existing certificates included:

```text
.cer
.p7b
.crt
.pem
```

Some `.cer` files were DER-encoded, and the `.p7b` files were PKCS7 bundles.

Debian's `update-ca-certificates` only automatically registers PEM certificate files ending in `.crt`. Therefore, the certificates existed inside the image but were silently ignored.

We found that the actual TLS chain looked like:

```text
packages.microsoft.com
  ↓
Zscaler proxy certificate
  ↓
Mashreq Zscaler proxy certificate
  ↓
MashreqSubCA
  ↓
MashreqCA
```

We added a normalization script:

`docker-normalize-ca-certs.sh`

It:

1. Reads all certificate files.
2. Detects PEM, DER, and PKCS7 formats.
3. Converts them into individual PEM `.crt` files.
4. Copies them into `/usr/local/share/ca-certificates`.
5. Runs `update-ca-certificates`.

The same approach was later added for the frontend:

`docker-normalize-ca-certs.sh`

We also added the actual exported Zscaler certificate to:

`zscaler-root.crt`

After this, the backend Docker image built successfully.

## 3. Frontend Docker build had the same certificate problem

The frontend build later failed here:

```text
npm ERR! code UNABLE_TO_GET_ISSUER_CERT_LOCALLY
request to https://registry.npmjs.org/zwitch/-/zwitch-2.0.4.tgz failed
```

The cause was the same:

- `npm install` ran before custom certificates were registered.
- `.cer` and `.p7b` files were copied without conversion.

We updated `Dockerfile.dev` to:

- Install `openssl`.
- Copy the certificate directory.
- Normalize all certificates before `npm install`.
- Set:

```dockerfile
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
ENV NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-certificates.crt
```

Validation succeeded:

```text
npm install: added 727 packages
next build: Compiled successfully
frontend container: started
```

## 4. Docker networking caused Redis failures

The `.env` file originally contained:

```dotenv
REDIS_URL=redis://localhost:6380/0
```

That works when the backend runs directly on the host.

Inside Docker, however:

```text
localhost = the backend container itself
```

It does not mean the host or the separate `tada-redis` container.

The backend was logging:

```text
Error 111 connecting to localhost:6380
Connection refused
```

We changed the Docker Compose backend override to:

```yaml
- REDIS_URL=redis://host.docker.internal:6380/0
```

`host.docker.internal` allows a Docker container on macOS to access a service published on the host.

## 5. Docker networking also caused PostgreSQL failures

The `.env` file contained:

```dotenv
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:6666/langgraph?sslmode=disable
```

Inside the backend container, `localhost:6666` was incorrect.

Because PostgreSQL is a Compose service, the backend should connect through the service name and internal port:

```yaml
- DATABASE_URL=postgresql+psycopg2://postgres:postgres@postgres:5432/langgraph?sslmode=disable
```

We also added:

```yaml
depends_on:
  postgres:
    condition: service_healthy
```

This makes the backend wait until PostgreSQL passes its health check.

## 6. There were no graphs for testing

The `workspace` directory was empty, so there was no workflow to execute.

We found the graph import endpoint:

```text
POST /api/graph/import-raw
```

The request accepts:

```json
{
  "name": "...",
  "description": "...",
  "workflow_json": {}
}
```

We imported a minimal workflow containing:

```text
START → END
```

The graph was named:

```text
minimal-test-graph
```

The import endpoint successfully created the workflow in PostgreSQL.

## 7. Redis queue execution was verified

The Redis queue is implemented in:

`queue.py`

The queue key is:

```python
QUEUE_KEY = "graph_execution_queue"
```

When an async workflow executes, the backend calls:

```python
self._redis.lpush("graph_execution_queue", json.dumps(job))
```

A background consumer waits using:

```python
self._redis.brpop("graph_execution_queue", timeout=5)
```

We verified the actual Redis traffic using:

```bash
docker exec tada-redis redis-cli monitor
```

The expected sequence appeared:

```text
LPUSH graph_execution_queue ...
BRPOP graph_execution_queue 5
```

The `BRPOP` usually happens immediately after the `LPUSH`, so checking Redis with `LLEN` often returns `0` because the worker has already consumed the job.

## 8. Why `LPUSH` initially appeared to be missing

At first, Redis monitoring showed nothing because the backend was trying to connect to:

```text
localhost:6380
```

That was the wrong address inside the backend container.

After correcting the Redis URL, the queue worked.

There was also a monitoring timing issue. `BRPOP` drains the job almost immediately, so manually starting `redis-cli monitor` in one terminal and switching to another terminal could miss the output.

The reliable command was:

```bash
docker exec tada-redis redis-cli monitor > /tmp/redis_monitor.log 2>&1 &
MPID=$!
sleep 1

curl -s -X POST http://localhost:8880/api/graph/execute \
  -H "Content-Type: application/json" \
  -d '{"graph_name":"minimal-test-graph","initial_input":{},"async_execution":true}' | jq

sleep 2
kill $MPID 2>/dev/null

grep -E "LPUSH|BRPOP" /tmp/redis_monitor.log
```

## 9. Frontend initially loaded slowly

The frontend used:

```typescript
import { Geist, Geist_Mono, Inter } from "next/font/google";
```

Next.js tried to download fonts from:

```text
https://fonts.googleapis.com
```

The corporate certificate/proxy setup blocked those downloads, causing repeated warnings and slow first compilation.

We removed the Google font imports from:

`layout.tsx`

We changed the CSS to use local/fallback font stacks in:

`globals.css`

The first request still took several seconds because Turbopack compiled the route, but later requests were fast:

```text
First request: approximately 6 seconds
Later requests: approximately 80 ms
```

We also removed missing 29LT Bukra `@font-face` declarations because the referenced files were not present:

```text
/frontend/public/fonts/29LTBukra-Regular.woff2
/frontend/public/fonts/29LTBukra-Regular.woff
```

That removed the browser's font 404 errors.

## 10. Frontend API requests returned HTTP 500

The frontend browser showed errors such as:

```text
GET /api/auth/me 500
GET /api/tutorial/progress 500
GET /api/schemas/outputs 500
```

The Next.js logs showed:

```text
Failed to proxy http://localhost:8880
ECONNREFUSED 127.0.0.1:8880
```

The reason was that `BACKEND_URL` was set to:

```yaml
BACKEND_URL=http://localhost:8880
```

But Next.js was running inside a container. From inside that container, `localhost:8880` meant the frontend container itself.

We changed the Compose configuration to separate browser and container addresses:

```yaml
- NEXT_PUBLIC_API_URL=http://localhost:8880
- BACKEND_URL=http://host.docker.internal:8880
```

The browser uses `localhost:8880`, while the frontend container uses `host.docker.internal:8880`.

## 11. Execution status returned a false 404

The frontend polled:

```text
GET /api/graph/execution/<execution_id>/status
```

The backend returned:

```text
404 Execution not found
```

The issue was a race condition:

1. The API pre-registers the execution in memory.
2. The job is sent to Redis.
3. The frontend immediately polls status.
4. The authorization code checks PostgreSQL first.
5. The database execution row may not exist yet.
6. Authorization returns 404, even though the execution exists in memory.

We updated `routes.py` so that if the database execution row is not available yet, the route:

1. Looks up the in-memory execution.
2. Gets its graph name.
3. Verifies workflow access.
4. Returns the current in-memory status.

A fresh status request then returned:

```text
HTTP 200
status: pending
```

instead of the false 404.

## 12. The frontend stayed stuck on "Streaming"

The frontend execution panel uses a WebSocket to receive:

```text
node_update
execution_status
execution_complete
```

The UI only resets `isExecuting` when it receives a completion, failure, pause, or stop event.

In local Docker development, the frontend was connecting to:

```text
ws://localhost:3330/api/ws/execution/...
```

Next.js rewrites normal HTTP requests, but its development server does not reliably proxy WebSockets to the backend.

We added this backend environment setting:

```yaml
- RUNTIME_API_URL=http://localhost:8880
```

This makes `/api/config` tell the browser to connect directly to:

```text
ws://localhost:8880/api/ws/execution/<execution_id>
```

instead of using the frontend port.

## 13. Multiple backend reload processes caused execution-state problems

The Redis trace showed multiple Redis consumers, and backend logs showed:

```text
Started reloader process
```

With Uvicorn reload enabled, multiple backend processes could each initialize their own:

```python
GraphExecutionManager()
```

That means:

- Multiple Redis consumers exist.
- Execution state is held separately in each process.
- One process may receive the HTTP request.
- Another process may consume the Redis job.
- The UI may not find the execution state or completion event.

We changed the backend Compose command from:

```yaml
command: ["python", "-m", "backend.app"]
```

to:

```yaml
command: ["python", "-m", "backend.app", "--no-reload"]
```

This ensures one backend process and one Redis consumer.

After changing it, recreate the backend:

```bash
docker compose -f docker-compose.dev.yml up -d --force-recreate backend
```

## 14. Why executions were stuck

The execution list showed entries like:

```json
{
  "status": "pending",
  "current_node": null
}
```

and:

```json
{
  "status": "running",
  "current_node": null
}
```

For a minimal `START → END` graph, that is abnormal. The workflow should complete almost immediately.

The Redis trace proved:

```text
LPUSH occurred
BRPOP occurred
```

Therefore, Redis connectivity was working. The remaining issue was backend process ownership and execution/WebSocket state, which is why we disabled reload and configured the direct runtime WebSocket URL.

## 15. Why the model dropdown is empty

The agent-node model selector calls:

```text
GET /api/model-deployments/select-options
```

The actual response was:

```json
{
  "success": true,
  "data": []
}
```

This means there are no active LLM model deployments in the local database.

This issue is unrelated to Redis.

To populate the dropdown, create an active model deployment through:

```text
Settings → Model Deployments
```

It needs:

```text
model_type: llm
provider: azure_openai, openai, or anthropic
model_name: your model/deployment name
is_active: true
```

After creating it, reload the agent node configuration panel.

## Current important configuration

The local Docker backend should have:

```yaml
- ENABLE_REDIS_QUEUE=true
- REDIS_URL=redis://host.docker.internal:6380/0
- DATABASE_URL=postgresql+psycopg2://postgres:postgres@postgres:5432/langgraph?sslmode=disable
- RUNTIME_API_URL=http://localhost:8880
```

The backend should run without reload:

```yaml
command: ["python", "-m", "backend.app", "--no-reload"]
```

The frontend should use:

```yaml
- NEXT_PUBLIC_API_URL=http://localhost:8880
- BACKEND_URL=http://host.docker.internal:8880
```

## Recommended clean restart

```bash
docker compose -f docker-compose.dev.yml up -d --force-recreate backend frontend
```

Then verify:

```bash
curl -s http://localhost:8880/api/config | jq
```

Expected:

```json
{
  "apiUrl": "http://localhost:8880",
  "deployment": "separate-domains"
}
```

Verify Redis:

```bash
docker exec tada-redis redis-cli ping
```

Expected:

```text
PONG
```

Watch Redis:

```bash
docker exec tada-redis redis-cli monitor
```

Execute one workflow:

```bash
curl -s -X POST http://localhost:8880/api/graph/execute \
  -H "Content-Type: application/json" \
  -d '{"graph_name":"minimal-test-graph","initial_input":{},"async_execution":true}' | jq
```

Expected Redis sequence:

```text
LPUSH graph_execution_queue ...
BRPOP graph_execution_queue 5
```

Expected final API state:

```json
{
  "active_executions": [],
  "recent_executions": [
    {
      "status": "completed"
    }
  ]
}
```

No git commit was created.
