# Phoenix → Langfuse Trace Migration

Seamlessly migrates Arize Phoenix traces to Langfuse, preserving all trace data and verifying successful ingestion.

## Required environment variables

- `MIGRATION_LANGFUSE_PUBLIC_KEY` — **required** — Langfuse project public key (`pk-lf-...`).
- `MIGRATION_LANGFUSE_SECRET_KEY` — **required** — Langfuse project secret key (`sk-lf-...`).
- `MIGRATION_LANGFUSE_HOST` — **required** — Langfuse base URL (e.g. `http://localhost:3001`).
- `PHOENIX_ENDPOINT` — **required** — Phoenix base URL (e.g. `http://localhost:6006`; `/v1/traces` suffix is stripped).
- `PHOENIX_API_KEY` — optional — only if Phoenix has auth enabled.

## How to run
Run this script using the existing application environment.



```bash
python scripts/phoenix_to_langfuse_migration/migrate.py
```

## Sample output

```
[1/3] Exporting Phoenix spans from http://localhost:6006 ...
  found 5 project(s): ['default', 'new', 'testing', 'agentic-studio', 'playground']
    [ok]    default: 271 spans
    ...
  wrote 472 spans -> C:\...\phoenix_xxxx.pkl
[2/3] Migrating spans into Langfuse at http://localhost:3001 ...
    sent 200/472 spans
    sent 400/472 spans
    sent 472/472 spans
  migrated 138 traces, 472 spans.
[3/3] Verifying migration ...
  Phoenix : 138 traces, 472 spans
  Langfuse: 138 traces
  OK: every Phoenix trace is present in Langfuse.
```
