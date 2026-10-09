# Creating a Workflow

This guide walks through building and running your first workflow in Agentic Studio.

---

## 1. Create a New Workflow

From the home screen, click **New Workflow**. Give it a name and an optional description, then confirm.

<img width="946" height="758" alt="image" src="https://github.com/user-attachments/assets/7141a091-dcbb-4cef-9cac-2a432c026648" />

You'll land on the workflow canvas — a blank graph with a **Start** node already placed.

<img width="1107" height="711" alt="image" src="https://github.com/user-attachments/assets/f01ed074-c0bd-40bc-8068-b35e15ee5db1" />

---

## 2. Add a Node

Click the **+** button on the canvas (or on an existing node's output handle) to open the node picker.

<img width="594" height="777" alt="image" src="https://github.com/user-attachments/assets/79437d5e-ea16-4b03-ae4c-e49d52679501" />

Select **Agent** to add an AI reasoning node. The node appears on the canvas.

<img width="1009" height="713" alt="image" src="https://github.com/user-attachments/assets/23323beb-a0aa-4c19-9feb-300dddc04ade" />

---

## 3. Configure the Agent

Double-click the Agent node to open its configuration panel.

<img width="1078" height="720" alt="image" src="https://github.com/user-attachments/assets/f5cd73e6-e245-45df-9950-622cc25dd2bf" />

Key settings:

| Setting | What it does |
|---------|-------------|
| **Name** | Label shown on the canvas |
| **System Prompt** | Instructions that define the agent's role and behaviour |
| **LLM Provider / Model** | Which language model the agent uses |
| **Temperature** | Controls response creativity (0 = focused, 1 = varied) |
| **Memory** | Enable to carry conversation history across turns |

Fill in a system prompt describing what you want the agent to do, then close the panel.

---

## 4. Add Tools to the Agent

Inside the agent configuration panel, find the **Tools** section. Click **+** to attach a tool.

<img width="1008" height="727" alt="image" src="https://github.com/user-attachments/assets/0abf194b-35e1-451b-86ad-ef212aaa3b0f" />

Available built-in tools include:

- **Web Search** — Search the web for up-to-date information
- **Document Search** — Search your uploaded document collections (RAG)
- **HTTP Request** — Call external APIs
- **Database Query** — Query a connected database
- **Email Send** — Send emails from the workflow

Select the tools you want, configure any required settings (such as an API endpoint for HTTP Request), and save.

<img width="949" height="638" alt="image" src="https://github.com/user-attachments/assets/7f9c106e-628e-4ba6-b8cb-22212857af78" />

---

## 5. Add More Nodes (Optional)

Repeat the **+** steps to add additional nodes. Common patterns:

- **Agent → Agent** — Chain agents in sequence, each building on the previous output
- **Agent → Condition** — Branch the workflow based on the agent's response
- **Agent → End** — Single-agent workflow, output flows straight to End

<img width="1110" height="515" alt="image" src="https://github.com/user-attachments/assets/61283f7a-79a3-4da2-95c5-9476b82c2cfa" />

---

## 6. Run the Workflow

Click the **▶ Run** button in the top toolbar. Enter an initial message or input when prompted.

<img width="234" height="167" alt="image" src="https://github.com/user-attachments/assets/8a07bb53-70fb-4b15-bd02-f3f7634ff61a" />

The execution panel opens and streams live updates as each node runs — you'll see nodes highlight as they execute and their outputs appear in real time.

<img width="622" height="810" alt="image" src="https://github.com/user-attachments/assets/e45b4487-7b75-43a9-9c06-323e049c3a94" />

When complete, the final result is shown under the **End** node output.

<img width="522" height="425" alt="image" src="https://github.com/user-attachments/assets/4610f08d-de82-47e5-add9-548e99a41473" />

---

## Next Steps

- **Save and name versions** — Use the workflow menu to save named checkpoints
- **Publish for API access** — See [User API Tokens](./09-user-api-tokens.md) to trigger workflows via HTTP
- **Import pre-built agents** — See [Importing Agents](./08-importing-agents.md) to load agents from JSON
