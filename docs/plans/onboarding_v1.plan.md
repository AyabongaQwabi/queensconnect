---
name: Onboarding v1 Implementation
overview: 'Implement Queens Connect onboarding v1.0: four granular user/session Firestore tools, a dedicated leaf onboarding_agent, and orchestrator routing that calls get_user_tool first and delegates to onboarding until complete. Design is ADK-aligned so workflow agents (e.g. Sequential) can wrap this flow later.'
todos: []
isProject: false
---

# Queens Connect – Onboarding v1.0 Implementation Plan

Sharp, my bra — here’s the full plan so we can ship onboarding in one 2–3 hour session. Every choice is explained so we stay EC-ready and ADK-ready for workflow agents later.

---

## Why these decisions (short)

- **Onboarding state in userSessions only**  
  Spec says `userSessions/{waNumber}.onboardingStep` (not in users doc). So we add **session tools** as well as the four **user tools**: orchestrator and onboarding_agent need to read/write session for step, and user doc for profile. Keeps session = “this conversation’s step” and user = “identity + preferences”; no mixing.
- **Dedicated leaf onboarding_agent**  
  One agent, no sub-agents, only the new granular tools. Orchestrator stays thin: “get user → if new or not complete → transfer to onboarding_agent”. Later you can wrap this in a **Sequential** or **Loop** workflow agent (ADK docs: [Workflow Agents](https://google.github.io/adk-docs/agents/workflow-agents/index.md)) without changing the leaf.
- **Orchestrator calls get_user_tool first, then routes**  
  So every message is “do we have this user? is onboarding done?” then either delegate to onboarding_agent or do normal intent routing. Matches ADK multi-agent pattern (transfer_to_agent) and keeps one source of truth (Firestore).
- **customInfo: string or dict**  
  Spec allows both (e.g. `"secondary_email: ..."` and `{"key":"gender","value":"male","addedAt":"..."}`). We validate in `append_to_custom_info_tool` and in `update_user_tool` when touching customInfo.
- **No media/voice in v1**  
  Text-only; media handling is explicitly Phase 2. No new branches for images/voice in this plan.
- **town, areaSection, province (default "Eastern Cape")**  
  No Queenstown hard-coding; any EC town works. Province default keeps it EC-wide from day one.
- **Defensive + logged**  
  Missing user → `get_user_tool` returns `{"exists": false}`. Missing session → session tools return a safe default (e.g. `onboardingStep: "new"`). All tools log at INFO (masked waNumber) and handle Firestore errors without crashing.

---

## 1. Files to CREATE

| Full path                                                                                                        | Purpose                                                                                                                                                                      |
| ---------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [queens_connect/sub_agents/onboarding_agent/agent.py](queens_connect/sub_agents/onboarding_agent/agent.py)       | Leaf agent: instruction (state machine + kasi tone), tools = get_user, create_user, update_user, append_to_custom_info, get_user_session, update_user_session; sub_agents=[] |
| [queens_connect/sub_agents/onboarding_agent/**init**.py](queens_connect/sub_agents/onboarding_agent/__init__.py) | Export `onboarding_agent` for `from .sub_agents.onboarding_agent import onboarding_agent`                                                                                    |

---

## 2. Files to MODIFY

### 2.1 [queens_connect/tools/firebase_tools.py](queens_connect/tools/firebase_tools.py)

- **Add users collection access**
  - No new schema in `SCHEMAS` (users/userSessions are free-form per spec).
  - Add helpers (or inline) to read/write `users` and `userSessions` by document id = normalized `waNumber` (e.g. strip, ensure string).
- **New functions (plain Python, then wrap with FunctionTool):**
  - **get_user_tool(wa_number: str) -> dict**
    - Normalize wa_number; get `users/{wa_number}`.
    - Return full doc (with id) if exists, else `{"exists": false}`.
    - Log with masked number; on Firestore error return e.g. `{"exists": false, "error": "..."}`.
  - **create_user_tool(wa_number: str, initial_data: dict | None = None) -> dict**
    - Creates `users/{wa_number}` with: waNumber, createdAt (SERVER_TIMESTAMP), languagePref from initial_data or default "xhosa". Optionally merge other allowed fields from initial_data (name, town, areaSection, province, etc.) if provided.
    - Return `{"status": "success", "waNumber": wa_number}` or `{"status": "error", "error_message": "..."}`.
    - If doc already exists, return error (do not overwrite).
  - **update_user_tool(wa_number: str, updates: dict) -> dict**
    - Partial update on `users/{wa_number}`. Allowed fields: name, email, town, areaSection, province, languagePref, primaryIntent, watchTags, customInfo (replace or merge per spec), onboardingComplete, interactionsCount, lastActiveAt. Do not allow overwriting waNumber or createdAt.
    - For customInfo: accept list of strings and/or dicts; append-only semantics if we pass a list (or merge by key for dicts).
    - Return `{"status": "success"}` or `{"status": "error", "error_message": "..."}`.
    - Set lastActiveAt to SERVER_TIMESTAMP on each update.
  - **append_to_custom_info_tool(wa_number: str, info: str | dict) -> dict**
    - Get current user doc; if not exists return error.
    - If info is str: append to customInfo. If info is dict: must have key/value (and optionally addedAt); append.
    - Return success/error.
    - customInfo array must accept both strings and dicts (per spec).
  - **get_user_session_tool(wa_number: str) -> dict**
    - Read `userSessions/{wa_number}`.
    - Return doc (e.g. onboardingStep, lastActiveAt) or `{"exists": false, "onboardingStep": "new"}` so orchestrator/onboarding can assume "new" when missing.
  - **update_user_session_tool(wa_number: str, updates: dict) -> dict**
    - Partial update on `userSessions/{wa_number}` (create doc if missing). Allowed: onboardingStep, lastActiveAt, and any other session-scoped fields you want.
    - Return success/error.
- **Wrap all six as FunctionTool** at bottom of file (same pattern as existing save* / fetch*).
- **Export** the six new tools (names obvious: get_user_tool, create_user_tool, update_user_tool, append_to_custom_info_tool, get_user_session_tool, update_user_session_tool).

### 2.2 [queens_connect/tools/**init**.py](queens_connect/tools/__init__.py)

- Import the six new tools from `.firebase_tools`.
- Add them to `__all`.

### 2.3 [queens_connect/agent.py](queens_connect/agent.py)

- Add import: `from .tools import get_user_tool, get_user_session_tool` (and optionally create_user_tool if orchestrator is to create user; else onboarding_agent can do it after transfer).
- Add to orchestrator **tools** list: `get_user_tool`, `get_user_session_tool`, and `create_user_tool` (so orchestrator can create user when missing then transfer).
- Add import: `from .sub_agents.onboarding_agent import onboarding_agent`.
- Add `onboarding_agent` to **sub_agents** list (e.g. first or early so it’s clearly “onboarding first when needed”).

### 2.4 Orchestrator system prompt

- File: path from [config.ORCHESTRATOR_PROMPT_PATH](queens_connect/config.py) (e.g. `queens_connect/docs/prompts/orchestrator-system-prompt.md`); if that path doesn’t exist, use project root [docs/prompts/orchestrator-system-prompt.md](docs/prompts/orchestrator-system-prompt.md).
- **Exact changes:**
  - At the **top** of “Think step-by-step” (or equivalent) add a **mandatory first step**:
    - “On every message, first call get_user_tool with {waNumber?}. If the result has exists false, call create_user_tool for that waNumber, then transfer to onboarding_agent. If the user exists but onboarding is not complete, call get_user_session_tool to check onboardingStep; if step is not onboardingComplete (or session missing), transfer to onboarding_agent. Only when user exists and onboarding is complete, proceed with normal intent (save/fetch/sub-agents).”
  - In the sub-agents list, add **onboarding_agent** and state: “Handles all new-user onboarding and incomplete onboarding; use transfer_to_agent to send user to onboarding_agent when they are new or onboarding not complete.”

So: **routing** = get_user_tool → [create_user_tool if missing] → get_user_session_tool (if you want to double-check step) → transfer to onboarding_agent if new or not complete; else normal flow.

---

## 3. New functions/tools – signatures and return format

- **get_user_tool(wa_number: str) -> dict**
  - Out: `{"exists": true, **user_doc}` or `{"exists": false}` (optional `"error": "..."` on failure).
- **create_user_tool(wa_number: str, initial_data: dict | None = None) -> dict**
  - Out: `{"status": "success", "waNumber": "..."}` or `{"status": "error", "error_message": "..."}`.
- **update_user_tool(wa_number: str, updates: dict) -> dict**
  - Out: `{"status": "success"}` or `{"status": "error", "error_message": "..."}`.
- **append_to_custom_info_tool(wa_number: str, info: str | dict) -> dict**
  - Out: `{"status": "success"}` or `{"status": "error", "error_message": "..."}`.
- **get_user_session_tool(wa_number: str) -> dict**
  - Out: `{"exists": true, **session_doc}` or `{"exists": false, "onboardingStep": "new"}` (and optional error).
- **update_user_session_tool(wa_number: str, updates: dict) -> dict**
  - Out: `{"status": "success"}` or `{"status": "error", "error_message": "..."}`.

All six exposed as **FunctionTool** in firebase_tools and exported from tools/**init**.py.

---

## 4. onboarding_agent – full code skeleton and system instruction

**File:** [queens_connect/sub_agents/onboarding_agent/agent.py](queens_connect/sub_agents/onboarding_agent/agent.py)

- Imports: `Agent` from `google.adk.agents`; config `GEMINI_MODEL`; from `...tools` (or `...tools.firebase_tools`) import the six tools.
- **Tools list:** get_user_tool, create_user_tool, update_user_tool, append_to_custom_info_tool, get_user_session_tool, update_user_session_tool.
- **sub_agents:** [] (leaf).
- **instruction:** One coherent string that includes:
  - Role: “You are the friendly Queens Connect Onboarding Cousin.”
  - State machine: follow the exact steps from [docs/processes/onboarding.md](docs/processes/onboarding.md) (new → asked_name → asked_area → asked_language → asked_intent → basic_complete → advanced_complete → onboardingComplete; abandoned recovery).
  - Onboarding state lives in **userSessions**: always read/update via get_user_session_tool / update_user_session_tool. User profile (name, town, areaSection, languagePref, primaryIntent, watchTags, etc.) via get_user_tool / update_user_tool / create_user_tool / append_to_custom_info_tool.
  - Reply in user’s languagePref; max 1–2 questions per reply; warm, short, Xhosa-first when possible.
  - When user gives useful info (e.g. email, gender, area) → append_to_custom_info_tool immediately where appropriate.
  - When they ask about something (taxi, news, etc.) → offer “Want me to notify you next time something like this drops?” and if yes → update watchTags.
  - After every successful step → update_user_tool and/or update_user_session_tool to persist step and profile.
  - Gamified lines: after asked_name “Name locked in! +10 kasi points”; after basic_complete “Profile 80% done! You now get priority in searches for 7 days”; after advanced_complete “FULLY OFFICIAL! Legend badge unlocked.”
  - Safety message once after basic_complete: “Yoh, quick thing — we NEVER share your number without you saying YES twice. Safety first neh. You can say ‘forget me’ anytime and we delete everything.”
  - Abandoned recovery: if lastActiveAt > 24h and step != complete, say “Eish [Name]! Sawubona again … We were busy setting up your profile last time — still want to finish quick? Just reply with your name or area if you forgot.”
  - Use fields: town, areaSection, province (default “Eastern Cape”). No media; text only.
  - Output ONLY the WhatsApp reply unless calling tools.

**File:** [queens_connect/sub_agents/onboarding_agent/**init**.py](queens_connect/sub_agents/onboarding_agent/__init__.py)

- Single line: `from .agent import onboarding_agent` (and optionally `__all__ = ["onboarding_agent"]`).

---

## 5. Config / constants

- No new env vars required. Use existing `config.GEMINI_MODEL`, `FIREBASE_PROJECT_ID`, `FIRESTORE_EMULATOR_HOST`.
- Optional: in config or in onboarding_agent, a constant list of **ONBOARDING_STEPS** = ["new", "asked_name", "asked_area", "asked_language", "asked_intent", "basic_complete", "advanced_complete", "onboardingComplete", "abandoned"] for validation or prompts. Not strictly required for v1.

---

## 6. How the orchestrator routes to onboarding_agent

1. User sends a message → Runner invokes orchestrator with session state (e.g. waNumber, languagePref).
2. Orchestrator instruction says: first call **get_user_tool(waNumber)**.
3. If **exists false** → call **create_user_tool(waNumber)** then **transfer_to_agent("onboarding_agent")** (ADK will hand off to onboarding_agent; onboarding_agent will see step “new” via get_user_session_tool and send welcome + name/area).
4. If user exists → optionally **get_user_session_tool(waNumber)**; if **onboardingStep** is missing or not “onboardingComplete” → **transfer_to_agent("onboarding_agent")**.
5. If user exists and onboarding is complete → proceed with normal intent (save/fetch, other sub-agents). No change to existing run_orchestrator or main.py invocation; routing is prompt + tools + transfer_to_agent.

---

## 7. Testing steps

- **CLI (run_orchestrator.py):**
  - Use a test waNumber (e.g. 27712345678). First run: send “Hi” or “Hello” → expect welcome + ask name/area (onboarding_agent). Then send name + area (e.g. “Sipho, Ezibeleni Queenstown”) → expect next step (language/intent). Then complete a few steps and confirm session and user docs in Firestore (users/{waNumber}, userSessions/{waNumber}) with correct onboardingStep and profile fields.
  - New number (e.g. 27798765432): “Hi” → get_user_tool returns exists false → create_user_tool + transfer → same welcome flow.
  - After onboarding complete for one number, send “what’s the taxi to East London?” → orchestrator should not transfer to onboarding; should use normal tools/sub-agents.
- **Firestore emulator:**
  - Start emulator; run tools against it; confirm users and userSessions collections created and updated. Check customInfo accepts both string and dict entries.
- **Defensive:**
  - Call get_user_tool with non-existent number → `{"exists": false}`.
  - Call create_user_tool twice same number → second returns error.
  - append_to_custom_info_tool for non-existent user → error.

---

## 8. ADK and future workflow agents

- Current design: **LLM orchestrator** + **transfer_to_agent** to a single **onboarding_agent** (LLM leaf). This matches [Multi-agent systems](https://google.github.io/adk-docs/agents/multi-agents/index.md) and keeps routing in the orchestrator prompt.
- Later you can introduce a **Sequential Agent** (or similar) that: step 1 = “ensure user exists (get_user / create_user)”, step 2 = “run onboarding_agent until complete”, step 3 = “run main orchestrator”. The same tools and onboarding_agent can be reused; only the parent flow changes.

---

## 9. Summary checklist (2–3 hour session)

- Add 6 tools in firebase_tools.py (users + userSessions), wrap as FunctionTool, export.
- Export 6 tools from tools/**init**.py.
- Create onboarding_agent package (agent.py + **init**.py) with full instruction and 6 tools, sub_agents=[].
- Add get_user_tool, get_user_session_tool, create_user_tool to orchestrator tools; add onboarding_agent to sub_agents; update orchestrator prompt with “get_user first → create if missing → transfer to onboarding if not complete”.
- Run CLI tests and one full onboarding flow; verify Firestore and defensive cases.

No new config files required; no media handling. Production-ready, defensive, and ready to extend to full EC and workflow agents.
