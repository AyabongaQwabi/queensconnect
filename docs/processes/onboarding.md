### **Queens Connect – Onboarding Process v1.0**

**Date:** 24 Feb 2026  
**Version:** 1.0 (Granular DB tools + Dedicated Onboarding Agent)  
**Scope:** Text-only onboarding. Media/voice/notes parked for later.  
**Goal:** Get user from “first hello” to “active & retained” in under 7 messages, feel like chatting to a sharp cousin, collect just enough to make the bot useful immediately.

#### **1. Core Principles (never break these)**

- Max 1–2 questions per reply. Always warm, short, Xhosa-first when possible.
- Never ask for anything we can infer later (passive data).
- Every user has a permanent `waNumber` UID.
- All changes go through **granular DB tools** (no more big insert_data_to_db_tool for users).
- Onboarding state lives in `userSessions/{waNumber}.onboardingStep`
- Expandable to whole Eastern Cape → fields are generic: `town`, `areaSection`, `province` (default “Eastern Cape”).

#### **2. User Document Schema (Firestore – users collection)**

```json
{
  "waNumber": "27712345678",
  "name": "Sipho Mthethwa",
  "email": "sipho@gmail.com", // optional
  "town": "Queenstown",
  "areaSection": "Ezibeleni",
  "province": "Eastern Cape",
  "languagePref": "xhosa",
  "primaryIntent": ["buying", "selling", "looking_for_lifts"], // array
  "watchTags": ["taxi", "puppies", "dstv", "load-shedding"], // array of strings
  "customInfo": [
    // array of string OR object
    "secondary_email: thabo.backup@gmail.com",
    { "key": "gender", "value": "male", "addedAt": "2026-02-24T10:15:00Z" },
    { "key": "ageRange", "value": "25-34", "addedAt": "..." },
    { "key": "hustleType", "value": "spaza_owner", "addedAt": "..." },
    "inferred_location: Ezibeleni (mentioned 3x)"
  ],
  "onboardingComplete": false,
  "onboardingStep": "asked_name", // see state machine below
  "interactionsCount": 6,
  "createdAt": "...",
  "lastActiveAt": "..."
}
```

#### **3. Onboarding State Machine** (lives in `userSessions/{waNumber}`)

| onboardingStep      | Trigger / Condition                        | Bot Action (next reply)                                                               | Next Step after success    |
| ------------------- | ------------------------------------------ | ------------------------------------------------------------------------------------- | -------------------------- |
| `new`               | User does not exist in DB                  | Welcome + ask name + area/town (friendly)                                             | `asked_name`               |
| `asked_name`        | Name received                              | “Sharp [Name]! Which section/area and town you in?” + ask language                    | `asked_area`               |
| `asked_area`        | Area + town received                       | Confirm languagePref + ask primary intent                                             | `asked_language`           |
| `asked_language`    | Language chosen                            | “Cool! What you mainly looking for on Queens Connect? (buy, sell, lifts, news, etc.)” | `asked_intent`             |
| `asked_intent`      | Intent answered                            | Thank + offer watchTags + mark almost complete                                        | `basic_complete`           |
| `basic_complete`    | 5–7 interactions reached                   | Ask optional: gender, age range, hustle type                                          | `advanced_complete`        |
| `advanced_complete` | Advanced details given or skipped          | “You now fully kasi official! 🔥” + safety message                                    | `onboardingComplete: true` |
| `abandoned`         | User returns after >24h idle in onboarding | Recovery message (see section 7)                                                      | back to last step          |

#### **4. New Granular Database Tools we must build** (in firebase_tools.py)

1. `get_user_tool(wa_number: str) → dict`
   - Returns full user doc or `{"exists": false}`

2. `create_user_tool(wa_number: str, initial_data: dict) → dict`
   - Creates minimal user (only waNumber + createdAt + languagePref default “xhosa”)

3. `update_user_tool(wa_number: str, updates: dict) → dict`
   - Flexible partial update. Can update name, town, languagePref, primaryIntent, watchTags, customInfo (append only), interactionsCount, onboardingStep, etc.

4. `append_to_custom_info_tool(wa_number: str, info: str | dict) → dict`
   - Specifically for adding to customInfo array (keeps it clean)

These will be exposed as `FunctionTool` so the new onboarding agent can call them directly.

#### **5. New Dedicated Sub-Agent: onboarding_agent**

We create `sub_agents/onboarding_agent.py`

```python
onboarding_agent = Agent(
    name="onboarding_agent",
    model=GEMINI_MODEL,
    description="Handles entire user onboarding flow, state machine, friendly questions, passive inference",
    instruction= """You are the friendly Queens Connect Onboarding Cousin.
    - Follow the exact state machine above.
    - Always reply in user’s languagePref.
    - Never ask more than 2 questions.
    - When user gives useful info → call append_to_custom_info_tool immediately.
    - When they ask about anything (taxi price, news, etc.) → ask “Want me to notify you next time something like this drops?” and if yes → update watchTags.
    - After every successful step → call update_user_tool to save.
    - Output ONLY the WhatsApp reply unless calling tools.""",
    tools=[get_user_tool, create_user_tool, update_user_tool, append_to_custom_info_tool],
    sub_agents=[]   # pure leaf agent
)
```

Then we add it to the root orchestrator’s `sub_agents` list in agent.py

#### **6. Passive Inference (runs on every message after onboarding starts)**

Orchestrator (or onboarding_agent) will always:

- Scan message for secondary email → append to customInfo
- Scan for gender words (“I’m a guy”, “sisi”, “ndiyintombi”) → infer & save
- Count interactions → increment `interactionsCount`
- If user mentions town/area again → update if different
- If user asks for info → auto-offer watchTags

#### **7. Abandoned Onboarding Recovery**

If `onboardingStep != "onboardingComplete"` and lastActiveAt > 24h ago:
Bot first message:
“Eish [Name if we have]! Sawubona again my guy/sisi. We were busy setting up your profile last time — still want to finish quick? Just reply with your name or area if you forgot.”

#### **8. Safety & Trust Signals (always shown once)**

After `basic_complete`:
“Yoh, quick thing — we NEVER share your number without you saying YES twice. Safety first neh. You can say ‘forget me’ anytime and we delete everything.”

#### **9. Gamified Onboarding (no invites for now)**

- After `asked_name`: “Name locked in! +10 kasi points 🔥”
- After `basic_complete`: “Profile 80% done! You now get priority in searches for 7 days.”
- After `advanced_complete`: “FULLY OFFICIAL! Legend badge unlocked.”

#### **10. Orchestrator Changes (small)**

In root orchestrator:

- First thing on every message → call get_user_tool
- If user does not exist → create_user_tool + delegate to onboarding_agent with step=`new`
- If onboardingStep != complete → always delegate to onboarding_agent first
- Only after onboarding complete → normal intent routing (search, infobit, etc.)

---

No Queenstown hard-coding, fully EC-ready, granular tools only, dedicated agent so the orchestrator stays light, and we can turn on media/voice/notes later without touching this flow.

**Tools we need to build this week (5 total):**

1. get_user_tool
2. create_user_tool
3. update_user_tool
4. append_to_custom_info_tool
5. onboarding_agent.py (with the full prompt + state logic)
