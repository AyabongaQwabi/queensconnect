You are a senior Google ADK + Firebase engineer building Queens Connect — the WhatsApp super app for Komani/Queenstown townships.

IMPORTANT INSTRUCTIONS BEFORE YOU START:

- You MUST reference the official Google ADK documentation (especially sections on Workflow Agents, LoopAgent, SequentialAgent, state management, transfer_to_agent, and multi-turn conversation handling).
- You also have access to my local MCP server with the latest ADK docs — use it to ensure you use correct 2026 ADK patterns.
- For any back-and-forth conversation (collecting name, ID, address, waiting for “done”, retry on failed verification), you MUST use a **LoopAgent** (or ADK workflow with Loop pattern) — do NOT use simple LlmAgent with manual state.
- Keep everything strict, no invented fields, follow the bible 100%.

─────────────────────────────────────────────
BUSINESS LOGIC BIBLE (single source of truth)

# Queens Connect – Lenders & Borrowers Registration Business Logic

(Version 1.0 – Feb 2026)

Users already exist as normal WhatsApp users (waNumber in users collection).

When user wants to list a loans/lending business (“I do small loans”, “lend money quick”, “join loans program”, “be a lender”, etc.), Orchestrator transfers to loans_registration_agent (sub-agent of loans_agent).

loans_registration_agent’s job:

- Explain the Small Loans Program using the exact text below
- Answer follow-up questions naturally
- Guide through mandatory Didit.me KYC (ID + face)
- Create lenders or borrowers document ONLY after successful verification
- On success, transfer back to loans_agent (if lender → show requests, if borrower → ask borrow amount)

Exact explanation text the agent must use/paraphrase:
"Sharp sharp my guy/sisi! 🙌  
Queens Connect has a safe Small Loans Program where trusted community members can lend small amounts (R50–R2 000) to people who need quick cash — and borrowers get help without going to loan sharks.

How it works:

- Borrowers post one request and wait.
- Lenders browse masked requests, pay R5–R10 to unlock details.
- If lender agrees we create loan record and SMS borrower.
- Borrower repays via link → lender gets money minus our 5% cut on interest.
- Good reputation = better rates and priority.

To join you must get verified with ID and face (2–5 min) using secure partner Didit.me.

Want to join as Lender or Borrower? Reply YES or ask me anything first 😎"

Flow (must be implemented with LoopAgent for the collection + verification loop):

1. Orchestrator detects intent → transfer_to_agent("loans_registration_agent")

2. Agent shares explanation.

3. User asks questions → answer from explanation.

4. User says YES → ask: “Lender (you lend) or Borrower (you borrow)?”

5. User chooses → start KYC loop (use LoopAgent here):
   - Ask full name + surname
   - Ask SA ID number (13 digits)
   - Ask physical address
   - Call create_verification_link_tool → POST https://verification.didit.me/v3/session/
   - Save session_token to users/{waNumber}.diditSessionToken
   - Reply with clickable verification URL + “When finished reply DONE”

6. User replies “done” → LoopAgent calls check_verification_result_tool (GET /v3/session/{sessionId}/decision/)

7. Parse result:
   - If id_verifications[0].status === "Approved" → success
   - Save full result JSON to verifications/{waNumber}
   - Update users: kycVerifiedAt, kycStatus = "verified"
   - Create lenders/{waNumber} or borrowers/{waNumber} doc
   - Reply success + transfer back to loans_agent
   - If failed → “Eish, want to try again? YES for new link” → loop back to create new link

─────────────────────────────────────────────

TASK: Generate the FULL implementation using proper ADK workflow/LoopAgent patterns.

Deliver in this order:

1. Updated main Orchestrator system prompt (add intent detection for loans business and transfer_to_agent("loans_registration_agent"))

2. Full ADK Python code for:
   - loans_registration_agent as LoopAgent + sub-agents if needed
   - All tools: create_verification_link_tool, check_verification_result_tool, create_lender_profile_tool, create_borrower_profile_tool

3. Firestore schemas + security rules:
   - users updates (diditSessionToken, kycVerifiedAt, kycStatus)
   - verifications collection
   - lenders and borrowers collections (minimal fields on creation)

4. Firebase callable functions (TypeScript) for verification session and result check

5. State management notes for the LoopAgent (how it remembers name, ID, address, sessionId across turns)

Use exact field names, warm kasi tone in all prompts/replies, strict enums, cents where money appears later.

Production-ready, secure, and 100% faithful to the bible above.
