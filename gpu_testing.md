# GPU Onboarding — Model 3.6 → 3.8 Testing Task

## Task

Test the GPU Tata onboarding integration on the newer model version. Currently configured model: **3.6**. Requested test target: **3.8**.

- Page to check: **QnGPL** — contains the details/configuration referenced below.
- Flow: one cURL command generates a token, that token is passed into a second cURL command (the model call). Some of this work is already done.
- Two things to understand: (1) token generation, (2) the model cURL call.
- The model cURL currently on file is outdated; an updated version has already been placed there.

## What to change

- Find the **Gateway Endpoint** parameter.
- In the Gateway Endpoint value, the model name/version appears after a slash — change **3.6 to 3.8**.
- Create the new configuration and test it.

## Functional testing

- Build a workflow: **Start → Agent → Chain/Tool → End**, assign something to the agent, and confirm it works.
- Also test with something like **Document Search or a chatbot tool** against the model.
- Test **reasoning effort** — unconfirmed whether this currently works correctly (not touched in ~1–2 months); check for parameter changes or issues.
- Reuse existing test scenarios (previously built, covering tool connections and similar). Test cases include:
  - Invoke a tool
  - Send JSON
  - Extract something from JSON
  - JSON schema generation
  - Agent/tool functionality
  - Free to add any other useful test cases

## Environments

- **DEV** — detailed testing (full integration, all test cases above).
- **UAT** — basic smoke test only: confirm the connection works with a small workflow (**Start → Agent → End → Response**). A successful response = basic integration working.

## SSL check

- Test whether SSL ON vs OFF affects the connection.
- If it works with SSL OFF but fails with SSL ON, raise it with **Harish, Vinod, or Sachin**.

**Finding (2026-09-30):** Access token generation in UAT fails when SSL verification is enabled, and only succeeds with SSL disabled. Discussed with Sunil — he asked to raise this with Aarif, with an ETA, since it needs resolving before the **4 October production deployment** and QAT sign-off. Questions sent to Aarif: whether the SSL cert issue can be fixed in UAT, whether the required cert exists and who owns providing/installing it, whether the same config is needed in PROD, whether this is a DevOps/network/cert issue or needs a code change, and the ETA. Once Aarif confirms a fix, re-test with SSL enabled to verify (this last verification step is mine to do, not Aarif's).

## Background context (already implemented — Gateway integration)

- Different models run on different GPU/model-hosting setups, but all respond in an **OpenAI-compatible format**.
- Integration flow already built: get token → pass token to endpoint → send request to model → get response back.
- The OpenAI-compatible setup already existed; the work was the integration on top of it.
- GPU infrastructure itself (stability, latency, throughput, GPU performance) is **owned by the GPU/infrastructure team**, not us. Our responsibility is the integration layer only.
- The integration is referred to as **GPU_CON** (GPU_CON) — ask Copilot/ChatGPT for a general overview if needed.

## Also check

- **Response latency** — how quickly the GPU model responds.

## Scope Revised (2026-09-30, per Dipankar — supersedes detailed plan above)

Testing is to stay high-level, not exhaustive. Urgent — send screenshots ASAP.

- **Payload changes (explicit instruction):** use `qwen-3.8-27b-fp8` instead of `qwen-3.6-27b-fp8`. Add `"reasoning_effort": low/medium/xhigh` to the request body, alongside `"stream"`.
- **Use the "Tada user," not "Tada UAT user."** `X-USER-ID: TADAUATUSER` is confirmed wrong for this testing — likely the cause of the earlier "User doesn't have permission to Access or Not Registered" error. Use the correct Tada user value instead.
- **SSL:** test with SSL disabled for now — this is accepted as fine at this stage. Only escalate to Arif and Sachin if something else still fails after that.
- **Backend:** only a couple of representative scenarios, across the two models (3.6 and 3.8) — high-level validation only, not every test case.
- **Tool invocation:** use at least one tool during testing (some automation use cases involve tool calls).
- **Reasoning check:** simple test only — ask something like "2 + 2" while increasing the reasoning level; a higher level taking longer to respond confirms the setting has an effect. No need for deeper testing than this.
- **Evidence:** capture 2–4 screenshots showing (a) a successful response and (b) tool invocation working.

## Logistics

- ~2:30 meeting today — no need to have something ready immediately; will be tagged in and can share whatever has been tested by then. Possible scheduling conflict on the other side — Smriti may join in that case.
- Test scenario files/pages will be shared, with a tag in the relevant place.
- Call for help during any test session if needed — available to join.
