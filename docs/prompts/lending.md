You are a senior Python + Firebase + Google ADK engineer building Queens Connect — a WhatsApp super app for Komani/Queenstown townships.

Implement the **Lending & Borrowing** feature exactly following the business logic described below. Do NOT add or change any rules, flows, field names, fee structures, or privacy logic — stick 100% to this spec.

─────────────────────────────
BUSINESS LOGIC BIBLE (must follow word-for-word)

# Queens Connect – Lending & Borrowing Business Logic

(Version 1.2 – Feb 2026 – Komani-first P2P Loan Requests Marketplace inside WhatsApp)

## Core Principles

- Borrowers post once and wait passively
- Lenders actively browse masked requests → pay small fee to unlock full details
- Money moves directly person-to-person (manual EFT/MoMo or payment link)
- Notifications to lenders = SMS only (not WhatsApp for now)
- Proof of payment = lender uploads image/PDF via simple web link
- Platform fees: R5/R10 unlock + 5% of interest on repayment
- Strict schema: no free-form fields, use enums, cents for money, timestamps

## Borrower Flow (Passive)

1. User says: “I want to borrow R200 till Friday, Capitec, for groceries”
2. lending_agent confirms: amount, repay date, purpose, bank
3. Agent asks: “Should I notify trusted lenders about your request? YES/NO”
4. If YES:
   - Create record in loan_requests collection (status = "open")
   - Reply: “Done! Your request is live. I’ll SMS you when a lender agrees.”
5. When lender later agrees → send SMS to borrower: “Lender Bulelwa agreed to lend you R200! Expect funds soon.”

## Lender Flow (Active Browsing)

1. Lender messages: “Show me loan requests” or “List requests”
2. Show 3 masked requests at a time:
   - First name + last initial (e.g. “Awonke S.”)
   - Amount
   - Repay date
   - Reputation score & badges
     Example reply:
     “Here’s 3 out of 12 open requests:
   1. Awonke S. – R200 by Friday – 4.2★ (3 loans, all on time)
   2. ...
      Reply 1, 2 or 3 to unlock (R5 each) or ALL for all three (R10)
      Or NEXT for more.”
3. Lender replies e.g. “1” or “ALL” → create Ikhokha payment link (R5 or R10)
4. After payment success:
   - Mark in lender_views sub-collection that this lender unlocked these requests
   - Show full details: full name, waNumber, bank, purpose, repay date
5. Lender replies e.g. “I’ll take request 1”
   → Create loan document linking borrower + lender
   → Send lender full borrower banking details
   → Send SMS to borrower: “Lender Bulelwa agreed to lend you R200!”
   → Update loan_request status → "matched"
6. Lender sends money directly (off-platform)
7. Lender messages “done” or “sent money”
   → Bot replies with unique web link e.g. https://queensconnect.co.za/pop/loan_abc123
8. Lender opens link → uploads photo/PDF proof-of-payment
   → Frontend POSTs to Firebase function
   → Function uploads to Cloud Storage, updates loan doc with popUrl + popUploadedAt
   → Changes loan_request status to "loaned"
9. Lender replies “done” → thank them and show next batch

## Fees

- Unlock: R5 per request or R10 for batch of 3 (to Queens Connect)
- On repayment: 5% of interest portion only
  Example: R200 loan + R70 interest = R270 repay
  Lender gets R266.50, Queens Connect gets R3.50

## Reputation (same as before)

- Borrower starts at 3.0
  +0.5 on-time, -0.8 late, -2.0 default
- Shown masked until unlocked

## Collections (strict schema – use exactly these fields)

1. loan_requests
   - id (auto)
   - borrowerUid (string)
   - amountCents (int)
   - repayByDate (timestamp)
   - purpose (string, max 80 chars)
   - bank (string enum: "capitec", "fnb", "standard_bank", "absa", "other")
   - status (string enum: "open", "matched", "loaned", "cancelled")
   - createdAt (timestamp)
   - updatedAt (timestamp)

2. loans
   - id (auto)
   - borrowerUid (string)
   - lenderUid (string)
   - loanRequestId (string)
   - amountCents (int)
   - interestCents (int)
   - totalToRepayCents (int)
   - status (enum: "matched", "active", "repaid", "defaulted")
   - createdAt (timestamp)
   - matchedAt (timestamp)
   - dueDate (timestamp)
   - repaidAt (timestamp | null)
   - popUrl (string | null) // Cloud Storage URL
   - popUploadedAt (timestamp | null)
   - notesFromBorrower (string, max 200)
   - notesFromLender (string, max 200)

3. lender_views (subcollection under lenders/{lenderUid}/views)
   - loanRequestId (string)
   - unlockedAt (timestamp)
   - feePaidCents (int)

## Your Task

Generate the complete implementation for Cursor AI:

1. Full Firestore collection schemas & security rules snippets for:
   - loan_requests
   - loans
   - lender_views (subcollection)

2. New ADK tools (Python, using google-cloud-firestore & ADK decorators):
   - fetch_loan_requests_tool (paginated, masked, 3 at a time)
   - unlock_loan_request_tool (handle R5/R10 payment, track in lender_views)
   - accept_loan_request_tool (create loan doc, update statuses, trigger SMS)
   - record_proof_of_payment_tool (called by Firebase function after upload)

3. lending_agent system prompt (full prompt for ADK LlmAgent)
   - Include all flows, masked display logic, fee prompts, confirmation steps
   - Use sub-agent style if needed

4. Firebase callable functions (TypeScript / Node.js):
   - createLoanRequest (from borrower confirmation)
   - getLoanRequestsBatch (for lender browsing – masked)
   - unlockLoanRequests (handle payment webhook → mark viewed)
   - uploadProofOfPayment (secure upload endpoint + update loan)

5. SMS helper function stub (assume you have a third-party SMS API like Clickatell or Twilio)

Follow strict naming: camelCase fields, enums where possible, cents for money, no invented fields.

Output structure:

- Markdown headings for each section
- Code blocks with language labels
- Comments explaining kasi logic

Make it production-ready, secure, and aligned 100% with the business logic above.
