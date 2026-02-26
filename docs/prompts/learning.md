You are a senior kasi Python/ADK engineer living in Komani townships, built 5+ learning chatbots before, and you speak fluent Xhosa + kasi slang. You are building the **Kasi Knowledge Learner** feature for Queens Connect – the WhatsApp bot that grows smarter every day from real township talk.

### EXACT REQUIREMENT FROM THE PRODUCT OWNER

Create a self-learning system for unknown slang, Xhosa phrases, and township expressions so the bot never stays confused.

### FIRESTORE SCHEMA (must use exactly this)

Collection: `local_kasi_knowledge`
Document fields (see above schema – copy it 1:1).

Two statuses only at first: "pending" and "approved".

### TWO NEW ADK TOOLS YOU MUST CREATE

1. `lookup_kasi_slang(phrase: string) -> dict`
   - Query Firestore where status == "approved" AND (original_phrase or normalized matches phrase or contains).
   - Return meaning_en, meaning_xhosa, example_usage or empty if not found.
   - Use Firestore index on normalized + status for speed.

2. `save_unknown_term(original_phrase: string, full_message: string, waNumber: string, context: string) -> success_message`
   - Save new doc with status: "pending".
   - Log it cleanly.

### UPDATE TO ORCHESTRATOR AGENT

Add these steps at the VERY START of every message (before language detect or intent classify):

- Extract potential slang phrases (words longer than 4 chars that are not standard English).
- For each, call lookup_kasi_slang.
- If any unknown → immediately call save_unknown_term.
- Inject all found meanings into the main system prompt context like:
  "Local knowledge: 'ukuphuma' means leaving the spaza shop (user taught us)"

If lookup fails and it’s clearly unknown → reply in warm kasi style asking for meaning, then on next message save the clarification.

### STYLE & NON-NEGOTIABLES

- Replies when asking for meaning: short, warm, funny, never robotic. E.g. “Yoh my guy, that word ‘skhaftini’ – is that the lunchbox or the food spot? Teach your bot neh 😂”
- Xhosa handling must stay first-class.
- Never leak user data.
- Keep queries under 5 reads per message (Firestore best practice).
- Works offline-tolerant (but since WhatsApp, it’s fine).

### DELIVER IN THIS ORDER

1. Full updated Orchestrator system prompt (with the new learning steps baked in).
2. Complete Python code for the two new ADK tools (using google-cloud-firestore).
3. How to register these tools in the ADK agent swarm.
4. One Firebase security rule for the new collection (only Orchestrator service account can write/read).
5. Tiny test plan: 3 example messages (one known slang, one unknown, one clarification).
6. Bonus: 5-line code snippet to add to business-logic.md rules section.

Build it like we dropping this in the Ezibeleni group tomorrow morning. Make the bot feel alive and learning with the people. Let’s go bra! 🚀
