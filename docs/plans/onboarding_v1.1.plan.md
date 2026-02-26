---
name: Onboarding v1 Implementation
overview: 'Implement Queens Connect onboarding v1.0: four granular user/session Firestore tools, a dedicated leaf onboarding_agent, and orchestrator routing that calls get_user_tool first and delegates to onboarding until complete. Design is ADK-aligned so workflow agents (e.g. Sequential) can wrap this flow later.'
todos: []
isProject: false
---

### **UPDATED IMPLEMENTATION PLAN – Onboarding v1.1 (Refined for your feedback)**

**Date:** 24 Feb 2026

**Version:** 1.1

#### **Refinement 1: NO DB calls on every single message (your first point)**

**Decision:** We **will cache** the full user doc + userSession doc inside the ADK **session.state** (the same `initial_state` we already pass in `main.py` and `run_orchestrator.py`).

**Why this is better (constructive explanation):**

- Firestore read on every WhatsApp message = unnecessary cost + latency (even if fast). In kasi reality people send 5–10 msgs in a row when chatting.
- ADK session.state is already designed for this exact thing `{currentState?}` and we can add `{userProfile?}` and `{userSession?}`).
- In the Python layer `main.py` `_run_async` and `run_orchestrator.py`) we do **one single combined load** before starting the Runner: call the two new tools once, merge into `initial_state["userProfile"]` and `initial_state["userSession"]`.
- Orchestrator prompt now says: “Use the cached userProfile and userSession from state first. Only call get_user_tool or get_user_session_tool if the cached data is missing or you just did an update.”
- When onboarding_agent updates the DB, it also calls a tiny new tool `sync_user_to_session_state` (or we let the Python wrapper re-load after the run — simpler for v1).
- Trade-off: slight extra code in `main.py` (10 lines), but zero extra DB calls during normal chat after onboarding. Perfect for EC scaling later.
- This keeps us ADK-native (no custom caching layer).

#### **Refinement 2: customInfo = ONLY dicts (your second point)**

**Decision:** customInfo will be **strictly array of objects** only. No plain strings.

**Why:**

- Spec said “array of objects or array of strings” but you now want clean dict-only. Easier to query later (“show me all users with gender”), no parsing hell.
- Every entry will look like: `{"key": "gender", "value": "male", "addedAt": "2026-02-24T10:15:00Z", "source": "user_message"}`
- `append_to_custom_info_tool` will enforce this format and auto-add addedAt + source.
- update_user_tool will reject non-dict items for customInfo.

#### **Refinement 3: Separate “core” agent instead of bloating the root orchestrator (your third point)**

**Decision:** We create **two root-level agents** instead of one fat orchestrator:

- `gatekeeper_orchestrator` (new slim root) → only does the “is user new or onboarding incomplete?” check using cached state + tools, then transfers.
- `core_orchestrator` (the old orchestrator logic) → contains ALL existing sub-agents (search, news, infobit_tagger, etc.) and normal tools. No onboarding logic at all.

**Why this is the cleanest (constructive explanation):**

- Root gatekeeper stays super light and fast (5–10 lines of instruction).
- Once onboardingComplete = true, it transfers to core_orchestrator and never comes back.
- Matches ADK best practice for multi-agent systems (gatekeeper → specialist).
- Later when we add workflow agents (Sequential/Loop), we can plug the gatekeeper on top easily.
- No change to existing sub-agents or tools.
- In `agent.py` we now return the gatekeeper as the root_agent.

---

### **Full Updated File Changes (ready for Cursor)**

**Files to CREATE**

- `queens_connect/sub_agents/onboarding_agent/agent.py` + `__init__.py` (same as before, but now uses cached state in instruction)
- `queens_connect/agents/gatekeeper_orchestrator.py` (new slim root)
- `queens_connect/agents/core_orchestrator.py` (move old orchestrator logic here)

**Files to MODIFY**

- `queens_connect/main.py` & `run_orchestrator.py` → add the one-time load of userProfile + userSession into initial_state
- `queens_connect/tools/firebase_tools.py` → the 6 tools + new `sync_user_to_session_state_tool` (optional, 5 lines)
- `queens_connect/tools/__init__.py`
- `queens_connect/config.py` → add `ONBOARDING_COMPLETE_STEP = "onboardingComplete"`
- `docs/prompts/orchestrator-system-prompt.md` → split into gatekeeper prompt + core prompt

**New tools (still 6 + 1 tiny)**

- Same 6 as before
- `sync_user_to_session_state_tool` (called by onboarding_agent after any update so next message has fresh cache)

**Routing flow (now perfect)**

1. Python layer ([main.py](http://main.py)) → load user + session once → put in ADK state
2. gatekeeper_orchestrator (root) → looks at cached state:

- if no user or onboardingStep != "onboardingComplete" → transfer_to_agent("onboarding_agent")
- else → transfer_to_agent("core_orchestrator")

1. core_orchestrator → does everything else (exactly like old orchestrator, no onboarding check)

---

**My bra, this is now bulletproof.**

- Zero unnecessary DB calls after onboarding
- customInfo clean dict-only
- Clean separation of concerns (gatekeeper vs core)
- Still 2–3 hour build
- Fully EC-ready and ADK-workflow-ready
