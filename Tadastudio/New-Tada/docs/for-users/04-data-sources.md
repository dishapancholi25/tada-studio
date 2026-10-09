# Data Sources

Agentic Studio supports two types of data sources that agents can query during workflow execution:

| Type | What it stores | Used by |
|------|---------------|---------|
| **Document Collections** | Uploaded files (PDFs, Word docs, spreadsheets, etc.) | Document Search node |
| **Database Connections** | External databases (PostgreSQL, etc.) | Database Query node |

---

## Document Collections

A collection is a named group of documents that have been processed and embedded for semantic search. Agents use the **Document Search** node to query collections at runtime.

### Creating a Collection

Navigate to **Data Sources** and click **New Collection**. Give it a name and optional description.

<img width="1340" height="569" alt="image" src="https://github.com/user-attachments/assets/35be1631-047f-47da-af94-cb43983ee1a9" />

> **Note:** Collection names are unique across all users in the instance. If the name is taken, use a descriptive prefix (e.g. `finance-q4-reports`).

### Uploading Documents

Open a collection and click **Upload**. You can upload multiple files at once.

<img width="878" height="765" alt="image" src="https://github.com/user-attachments/assets/1c16bf27-16ec-4e8e-aeba-5c8adb382cf4" />

Supported formats: PDF, Word (DOCX), Excel (XLSX), plain text, and images (via OCR).

Each file is split into chunks and embedded using the configured embedding model. The first upload locks in the embedding model for that collection — all subsequent uploads must use the same model.

Processing status is shown per document: **Processing**, **Processed**, or **Failed**.

### Sharing a Collection

By default, a collection is private to its creator. To share it with other users, set its **visibility groups**.

<img width="796" height="199" alt="image" src="https://github.com/user-attachments/assets/5d8c0854-6126-42bf-841b-11328ac3bf17" />

- Only the collection creator can upload, delete, or modify documents
- Users in a shared group see the collection as **read-only** — they can use it in their workflows but cannot change its contents

---

## Using a Collection in a Workflow

Add a **Document Search** node to your workflow and select the collection(s) to search. At execution time, the agent's current context is used as the search query and the most relevant chunks are returned as context.

<img width="1399" height="719" alt="image" src="https://github.com/user-attachments/assets/be879c4c-a23e-4ce4-8814-d01b3e3860ae" />

Collections you own and collections shared with your groups both appear in the selector.

---

## Database Connections

Database connections let agents run SQL queries against external databases using the **Database Query** node.

Navigate to **Data Sources → Database Connections** and click **New Connection**. Provide the connection details (host, port, database name, credentials) and test the connection before saving.

<img width="1466" height="734" alt="image" src="https://github.com/user-attachments/assets/17fda477-ad34-448d-bf9c-e25302a076ae" />
<img width="769" height="797" alt="image" src="https://github.com/user-attachments/assets/344a5942-ac09-4c9c-a9e0-dac0039d351e" />

Credentials are encrypted at rest. Connections can be marked read-only and restricted to specific tables for safety.

---

## Structured vs Unstructured

These two source types are suited to different kinds of information:

**Unstructured (Document Collections)**

- Best for prose content: reports, policies, documentation, emails
- Search is semantic — the agent finds relevant passages even without exact keyword matches
- Returns text excerpts with source attribution

**Structured (Database Connections)**

- Best for tabular data: records, transactions, metrics
- Queries are precise SQL — you get exact rows back, not approximations
- Requires knowing (or discovering) the schema

For mixed use cases, combine both in the same workflow: use a Database Query node to fetch structured records and a Document Search node to pull in relevant policy or reference text.
