# Settings

The **Settings** page is organised into tabs. Which tabs are visible depends on your role — some sections are admin-only.

---

## API Tokens

Manage your Personal Access Tokens (PATs) for API and CI/CD access. See [User API Tokens](./09-user-api-tokens.md) for full details.

<img width="1311" height="694" alt="image" src="https://github.com/user-attachments/assets/1f3417d5-fbca-4482-8246-e23ad2642fdb" />

---

## External Services

Configure API keys and connections for services used by built-in nodes. Admins see a **System-wide / Personal** scope toggle — system-wide settings act as defaults for all users, while personal settings override them for your own workflows.

<img width="1317" height="708" alt="image" src="https://github.com/user-attachments/assets/93a45b06-0b83-475e-a8df-8cd87023b2a1" />

### Tavily Web Search

| Field | Description |
|-------|-------------|
| **API Key** | Your Tavily API key — used by **Web Search** nodes to perform AI-powered web searches |

If a system-wide key is configured by an admin, you can leave this blank and the system default will be used. A personal key overrides the system default for your workflows.

### Email Service

| Field | Description |
|-------|-------------|
| **Email Provider** | Choose between **Microsoft Outlook**, **Mailgun**, or **MailSlurp** |
| **User Principal Name** | *(Outlook only)* The mailbox address used to send emails (e.g. `notifications@yourdomain.com`) |
| **API Key** | *(Mailgun / MailSlurp only)* The provider API key |
| **Domain** | *(Mailgun only)* The sending domain (e.g. `sandbox.mailgun.org`) |

Used by **Email Send** nodes. Like Tavily, a personal configuration overrides the system default.

### Document Extraction Provider *(admin, system-wide only)*

Controls how **Document Reader** nodes extract text from uploaded files. Three providers are available:

| Provider | Description | Settings |
|----------|-------------|----------|
| **Model OCR** *(default)* | Uses an LLM vision model — most accurate but slower and more token-intensive | **Default OCR Model** — which model deployment to use; **Vision Detail Level** — `high`, `auto`, or `low` (controls accuracy vs token trade-off) |
| **Apache Tika** | Open-source server-based extraction — fast for structured documents | **Server URL** (e.g. `http://tika:9998`); **Request Timeout** in seconds |
| **Azure Document Intelligence** | Azure's document analysis service — fast, supports tables and key-value pairs | **Endpoint URL**; **API Key** (or enable **Managed Identity**); **Document Model** (`prebuilt-read`, `prebuilt-layout`, `prebuilt-document`, `prebuilt-invoice`, `prebuilt-receipt`) |

Individual File Reader nodes can override the system default on a per-node basis.

### LangChain / LangSmith *(admin, system-wide only)*

Connects your instance to LangSmith for observability and tracing across all workflow executions.

| Field | Description |
|-------|-------------|
| **API Key** | Your LangSmith API key |
| **Enable LangChain Tracing V2** | Toggle tracing on or off |
| **Project Name** | The LangSmith project that traces are sent to (defaults to `default`) |

When enabled, every workflow execution is traced in LangSmith — see [Execution History — LangSmith Trace](./06-executions.md#langsmith-trace) for details on viewing traces.

---

## External Tools

Configure additional integrations that your agent nodes can call as tools.

<img width="1465" height="774" alt="image" src="https://github.com/user-attachments/assets/2094bc5c-c3f4-4471-9c08-0a7c6222701a" />

---

## MCP Servers

Add Model Context Protocol (MCP) servers to extend the tools available to your agents. Each server you configure here appears as a selectable tool source when building agent nodes.

<img width="817" height="725" alt="image" src="https://github.com/user-attachments/assets/6e15c032-97f5-4779-84b2-4c24e800f790" />

---

## Appearance

Customise the look of the interface (theme, colour mode, and similar preferences).

<img width="923" height="575" alt="image" src="https://github.com/user-attachments/assets/6e6475ea-d17c-4eba-9f46-86c5d0373ba2" />

---

## Admin Settings

The sections below are only visible to users with an admin role.

### Model Deployments

Configure the LLM and embedding model deployments available across the instance. All users' workflows draw from the models defined here.

<img width="1323" height="513" alt="image" src="https://github.com/user-attachments/assets/c1e5b51c-99dd-4c13-b352-7b253a13c788" />

Each deployment can be tested after saving to verify connectivity before making it available to users.

### User Management

View and manage all users on the instance.

<img width="1262" height="609" alt="image" src="https://github.com/user-attachments/assets/7c0677b9-50b3-41f6-b4d6-cd62dc743f56" />

### Feature Access

Control which features are enabled for each user or group. Features can be toggled per-user from this panel.

<img width="796" height="659" alt="image" src="https://github.com/user-attachments/assets/e887cb7b-0d1a-4b5e-a5b5-af45c40b319d" />
