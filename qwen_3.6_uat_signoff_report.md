# UAT Test Report — Qwen 3.6 (GPU_CON Integration)

**Model:** qwen-3.6-27b-fp8
**Provider:** GPU_CON
**Environment:** UAT (`https://tadastudio.uat.mashreq...`)
**Tester:** Vipul Sharma
**Date:** [INSERT DATE]

## 1. Objective

Validate that the GPU_CON model deployment (Qwen 3.6) works correctly in Tada Studio UAT — the deployment is reachable, authenticates successfully, and an agent using this model can respond to a message and invoke a connected tool (Document Search).

## 2. Deployment Configuration

The model was added as a new deployment in Tada Studio with the following configuration:

- **Gateway Endpoint:** `https://internal.apigateway.cibg.mashreqdev.com/mashreqtest/uae/msgpuai-api/...`
- **Token URL:** `https://internal.apigateway.cibg.mashreqdev.com/mashreqtest/uae/oauth-v6/oauth2/token`
- **OAuth Scope:** CORP
- **X-USER-ID Header:** TADAUSER
- **Verify SSL Certificates:** [Off / On — state which was used for this test]

**[SCREENSHOT 1 — Model Configuration]**
*Insert one of your two model-config screenshots here (the "Add Model Deployment" form showing Gateway Endpoint, Token URL, Client ID, OAuth Scope, X-USER-ID).*

**[SCREENSHOT 2 — Model Configuration]**
*Insert your second model-config screenshot here (e.g. the Agent's model selection, or the Document Search tool configuration showing it's connected to this agent).*

## 3. Test Cases Executed

UAT scope is a smoke test (per agreed scope: basic connection check via a small workflow, not the full Dev test matrix). The two cases below are executed through the Tada Studio UI (workflow run), not as raw API calls — the request body shown is what the workflow sends to the GPU_CON model endpoint underneath.

| TC ID | Description | Test Input | Expected Result | Actual Result | Status |
|---|---|---|---|---|---|
| TC-01 | Basic chat response via workflow (Start → Agent → End) | User message to agent, e.g. `{"messages":[{"role":"user","content":"tell me best place in Dubai"}],"stream":true}` (model = `qwen-3.6-27b-fp8`) | Workflow completes, agent returns a coherent streamed response, no error | Workflow executed successfully; agent responded correctly | Pass |
| TC-03 | Tool invocation — Agent connected to Document Search tool | User message that requires the tool, e.g. `{"messages":[{"role":"user","content":"<query requiring document lookup>"}],"tools":[{"type":"function","function":{"name":"document_search", ...}}],"stream":false}` | Agent invokes the Document Search tool and returns a response grounded in the retrieved document(s) | Document Search was invoked as part of the execution trace; agent returned the expected result | Pass |

Full Dev-level test matrix (all payload/JSON variants — tool calls, JSON-output, reasoning-effort, user-id validation, SSL) is tracked separately in `gpu_con_test_cases.md` and is out of scope for this UAT sign-off.

### Not Covered in This UAT Round

Only the sample workflow (Start → Agent → End, with/without Document Search) was validated. The following functional scenarios were **not** tested in UAT and are not represented above:

- JSON field extraction (structured output parsing)
- SQL query generation
- Greeting / small-talk response handling
- Conditional tool-use logic — AI-requiring query correctly triggers tool invocation vs. non-AI/simple query correctly skips tool invocation

These would need to be scoped as additional test cases (functional/business-scenario testing) beyond this basic connectivity/smoke validation if sign-off is expected to cover them.

## 4. Performance Metrics

Pulled from the execution's Trace Stats panel (Executions → select run → trace view) for each test case run above.

| TC ID | Avg Input Tokens | Avg Output Tokens | Avg Duration | TTFT | Avg Tokens/s | Cost |
|---|---|---|---|---|---|---|
| TC-01 | [INSERT] | [INSERT] | [INSERT]s | [INSERT] | [INSERT] | [INSERT] |
| TC-03 | 2,071 | 334 | 4.01s | 3,942ms | 83.0 | $0.013132 (prompt $0.007983 + completion $0.005150) |

Total Latency (Agent node): 4,025ms. Request window: 7:07:00 AM – 7:07:04 AM.

**[SCREENSHOT 6 — Trace Stats Panel]**
*Insert a screenshot of the Trace Stats panel for one of the runs, showing these numbers.*

## 5. Test Evidence

### TC-01 — Basic Workflow Execution

**[SCREENSHOT 3 — Workflow Run 1]**
*Insert one of your two "running workflow" screenshots here — the one showing the basic Start → Agent → End execution and response.*

### TC-03 — Tool Invocation (Document Search)

**[SCREENSHOT 4 — Workflow Run 2]**
*Insert your second "running workflow" screenshot here — the one showing Document Search being invoked as part of the execution trace.*

**[SCREENSHOT 5 — Zoomed-in Detail]**
*Insert your zoomed-in screenshot here — use it to show the execution result/output clearly (e.g. the Document Search step and Agent's final response in detail).*

## 6. Notes / Observations

- SSL certificate verification for this endpoint is not trusted by default outside Mashreq's internal infrastructure (self-signed internal CA). This does not affect the deployed application itself, only manual local testing tools.
- `X-USER-ID` must be set to `TADAUSER`. Using `TADAUATUSER` results in a `400 - User doesn't have permission to Access or Not Registered` error.

## 7. Conclusion

Qwen 3.6 via GPU_CON is functioning correctly in the UAT environment: the deployment authenticates successfully, the agent responds to messages, and tool invocation (Document Search) works as expected.

**Recommendation:** Ready for UAT sign-off for Qwen 3.6.

## 8. Sign-off

| Role | Name | Date | Signature/Approval |
|---|---|---|---|
| Tester | Vipul Sharma | | |
| Reviewer | | | |
| Approver | | | |
