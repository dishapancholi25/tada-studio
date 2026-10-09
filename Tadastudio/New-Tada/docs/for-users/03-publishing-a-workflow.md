# Publishing a Workflow

Publishing exposes a workflow as an HTTP endpoint so it can be triggered from external systems, scripts, or CI/CD pipelines without using the Agentic Studio UI.

> **Note:** The publishing and authentication flow has changed recently and may continue to evolve. This guide reflects the current behaviour.

---

## 1. Publish the Workflow

Open your workflow and click **Publish** in the toolbar. A publish settings panel will appear.

<img width="763" height="597" alt="image" src="https://github.com/user-attachments/assets/511330c5-068b-445c-99c5-70db8a192305" />

Configure the publication settings:

| Setting | Description |
|---------|-------------|
| **Description** | Optional note about what this endpoint does |
| **Require Authentication** | When enabled, callers must supply a valid token. Disable only for fully public workflows. |
| **Custom Slug** | Optional friendly name for the endpoint URL (e.g. `my-report`). Defaults to the workflow's UUID. |

Click **Publish**. The endpoint URL and a workflow-specific token (`wf_...`) are shown in the panel — copy both.

<img width="728" height="709" alt="image" src="https://github.com/user-attachments/assets/07029532-e1f4-47c9-ad4f-f55dad889636" />

---

## 2. Trigger the Workflow

Use the endpoint URL and `wf_` token to call the workflow from any HTTP client. The panel shows a ready-to-use `curl` command with your token already filled in:

<img width="1454" height="757" alt="image" src="https://github.com/user-attachments/assets/4aeb3e88-5764-4722-92e6-3de48f09b160" />

```bash
curl -X POST "https://your-app.com/api/http-execution/trigger/<workflow-id-or-slug>" \
  -H "Authorization: Bearer wf_your_token_here" \
  -H "Content-Type: application/json" \
  -d '{"message": "Your input here"}'
```

By default the request waits for the workflow to complete and returns the output. To trigger asynchronously and poll for the result, add `"async_mode": true` to the request body.

---

## 3. Unpublish

To remove the public endpoint, open the workflow, click **Publish**, and select **Unpublish**.

<img width="962" height="222" alt="image" src="https://github.com/user-attachments/assets/ecd7b3aa-b325-4ef7-b05e-6b3179d0d04a" />

---

## Related

- [User API Tokens](./09-user-api-tokens.md) — Personal Access Tokens (PATs) for multi-workflow or CI/CD access
- [API Authentication](../for-developers/05-api-authentication.md) — Full token type reference for developers
