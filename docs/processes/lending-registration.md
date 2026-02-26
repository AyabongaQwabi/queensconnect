# Queens Connect – Lenders & Borrowers Registration Business Logic

(Version 1.0 – Feb 2026 – KYC + Loans Program Onboarding inside WhatsApp)

## 1. Purpose & Context

Users are already registered in the system as normal WhatsApp users (via waNumber in `users` collection).

When someone wants to **list a business** and that business is a **loans/lending business** (e.g. "I do small loans in Ezibeleni", "I lend money quick", "micro loans service"), and that user does not have a lender profile or borrower profile the Orchestrator must detect this intent and transfer control to a new sub-agent called **loans_registration_agent**.

This agent’s only job is:

- Explain the Queens Connect Small Loans Program
- Answer user follow-up questions flexibly (using the explanation text below)
- Guide verified lenders/borrowers into the program
- Perform KYC via Didit.me (ID + face verification)
- Create either a `lenders` or `borrowers` document
- Hand back to the main `loans_agent` once done

No one can participate in lending/borrowing until they complete this registration + verification flow.

## 2. Core Business Rules

1. Verification is **mandatory** for both lenders and borrowers before joining the loans program.
2. Verification uses **Didit.me API** (ID document + face match).
3. We create a reusable verification link via API → user opens in browser → completes ID + selfie.
4. After user says “done”, we poll the session result and update user profile.
5. Only **approved** users get `lenders` or `borrowers` doc created.
6. Handover: once verified and profile created → transfer back to `loans_agent` to continue (show requests if lender, ask borrow amount if borrower).

## 3. Explanation Text the Agent Must Share (copy-paste friendly)

When the user shows interest in loans/lending business or asks to join:

"Sharp sharp my guy/sisi! 🙌  
Queens Connect has a safe Small Loans Program where trusted community members can lend small amounts (R50–R2 000) to people who need quick cash — and borrowers get help without going to loan sharks.

How it works:

- Borrowers post one request (amount, repay date, purpose) and wait.
- Lenders browse masked requests (name like 'Awonke S.', amount, reputation only).
- Lenders pay small fee (R5–R10) to unlock full details of someone they like.
- If lender agrees → we create a loan record, give banking details, and SMS the borrower.
- Borrower repays via link → lender gets money minus our tiny 5% cut on interest.
- Everyone builds reputation: good payers get higher scores, bad ones get restricted.

To join you must get verified with your ID and face (takes 2–5 min).  
We use a secure partner (Didit.me) — your info stays private and only used for this check.

Benefits of joining:

- Verified lenders get priority matching & trust badge
- Verified borrowers can ask for bigger amounts & better rates
- Everything tracked safely inside WhatsApp

Want to join the program as a lender or borrower? Reply YES or tell me more questions first 😎"

The agent can use this text flexibly to answer follow-ups until the user says YES to join.

## 4. Exact Registration Flow

1. Orchestrator detects intent  
   → phrases like: "I do loans", "small loans business", "I want to lend money", "join loans program", "be a lender", "borrow money through the bot"  
   → transfer to `loans_registration_agent` (sub-agent of `loans_agent`)

2. loans_registration_agent greets and shares the explanation text above.

3. User asks questions → agent answers naturally using the explanation.

4. When user says YES / "I want to join" / "register me" / "yes let's do it":
   - Agent asks: "Are you joining as a **Lender** (you want to lend money) or **Borrower** (you want to borrow money)?"

5. User chooses → Agent starts KYC:  
   "To join you must get verified with your ID number and face photo.  
   Reply with your full name and surname first (e.g. Sipho Ngcobo)"

6. User gives name → Agent asks:  
   "Sharp! Now your South African ID number please (13 digits)"

7. User gives ID → Agent asks:  
   "Last one — your physical address (e.g. 123 Ezibeleni, Zone 3, Komani)"

8. Once all collected:
   - Agent calls `create_verification_link_tool` → gets URL from Didit.me
   - Saves session_token to user profile (`users/{waNumber}.diditSessionToken`)
   - Replies friendly message containing the verification URL:  
     "Done my sibhuti/sisi! Open this link on your phone browser to do the quick ID + face check:  
     https://verify.didit.me/session/abcdef123456  
     It takes 2–5 minutes. When finished, just reply DONE here."

9. UI must detect links in messages and make them clickable (open in new tab).

10. User replies "done" / "DONE" / "finished" → Agent calls `check_verification_result_tool`  
    → GET /v3/session/{sessionId}/decision/

11. Tool parses response:
    - If id_verifications[0].status === "Approved" AND face_matches[0].status === "Approved" (or high enough face_matches[0].score) → success
    - Save full verification result to new collection `verifications` (linked to user waNumber)
    - Update user profile: `kycVerifiedAt`, `kycStatus: "verified" | "failed"`, `diditSessionId`
    - Create either `lenders` or `borrowers` document with waNumber as ID and basic fields (displayName, verifiedAt, etc.)

12. Reply:
    - Success: "Yoh legend! You are now verified 🔥 Your profile is ready for the loans program. Handing you over to the loans team…"
    - Failure: "Eish, something didn’t match up neh. Want to try again? Reply YES to get a new link."  
      (If YES → recall create_verification_link_tool with same details)

13. On success → transfer back to main `loans_agent`:
    - If lender → start showing loan requests
    - If borrower → ask “How much do you want to borrow and by when?”

## 5. Important Business & Safety Notes

- Always store raw ID number after verification
- Verification is one-time per user (unless failed → allow retry).
- If user cancels midway → save partial data but do not create lender/borrower doc.
- All communication stays warm, short, kasi style (yoh, sharp, neh, emojis).

## 6. Tools Needed (high-level – no code yet)

- create_verification_link_tool() → POST to Didit.me → return URL + save session_token
- check_verification_result_tool(sessionId) → GET decision → parse & return success/fail + details
- create_lender_profile_tool(userData) → write to lenders collection
- create_borrower_profile_tool(userData) → write to borrowers collection

This is the complete bible for the registration flow. Cursor Pro must follow it exactly — no extra steps, no invented fields, no skipping verification.
