# Queens Connect – Lending & Borrowing Business Logic

(Version 1.2 – Feb 2026 – Komani-first P2P Loan Requests Marketplace inside WhatsApp)

## 1. Why We Are Doing This

Township people already borrow and lend small money every day, but it’s messy — voice notes disappear, trust gets broken, fights start.  
Queens Connect turns it into a **safe, transparent marketplace** where borrowers post requests and trusted lenders browse & choose.

Goal:

- Borrowers get quick R50–R2 000 without chasing people
- Lenders find serious borrowers easily and earn 30–40% interest safely
- Platform takes sustainable small fees
- Everything tracked, reputation-based, and POPIA-safe

## 2. Core Principles (Non-Negotiable)

1. Borrowers post once and chill — no spamming.
2. Lenders browse anonymously first (masked info) → pay small fee to unlock full details.
3. All money moves directly person-to-person (Ikhokha/MTN MoMo or manual EFT).
4. SMS notifications only at launch (cheaper, works on any phone).
5. Proof of payment via simple web link (lender uploads photo/PDF).
6. Reputation is everything — bad payers get restricted fast.

## 3. Key Entities

- **Loan Request** – What the borrower posts (lives in `loan_requests` collection).
- **Lender** – Verified person who browses requests.
- **Borrower** – Anyone who posts a request.
- **Loan** – Final agreement created only when lender commits.

## 4. High-Level Flow – Borrower Side (Passive)

1. User messages:  
   “I want to borrow R200 till Friday, Capitec, for groceries”

2. Orchestrator → `lending_agent`  
   Agent confirms details (amount, repay date, purpose, bank).

3. Agent asks:  
   “Sharp! Should I notify trusted lenders about your request? Reply YES or NO”

4. If YES:
   - Create record in `loan_requests` collection (status = "open")
   - Reply to borrower: “Done my guy/sisi! Your request is live. I’ll SMS you the moment a lender agrees to help. Sit tight neh 🙌”

5. If NO: cancel and offer other help.

6. Borrower waits. When a lender later agrees, borrower gets SMS:  
   “Queens Connect: Lender Bulelwa agreed to lend you R200! She will send soon. Check your phone.”

## 5. High-Level Flow – Lender Side (Active Browsing)

1. Lender messages the bot: “Show me loan requests” or “List requests”

2. `lending_agent` calls `fetch_loan_requests_tool` → shows 3 requests at a time (masked):
   - First name + last initial (e.g. “Awonke S.”)
   - Amount needed
   - Repay date
   - Reputation score & badges only  
     Example:  
     “Here’s 3 out of 12 open requests:
   1. Awonke S. – R200 by Friday – 4.2★ (3 loans, all on time)
   2. ...  
      Reply 1, 2 or 3 to unlock details (R5 each) or reply ALL for all three (R10)  
      Or reply NEXT for more requests.”

3. Lender chooses:
   - “1” or “ALL” → pay R5 / R10 via Ikhokha link (fee to Queens Connect)
   - System tracks in a `lender_views` sub-collection which requests this lender already unlocked (so no double pay).

4. After payment: lender sees full details (name, address, full stats, bank, purpose, exact repay date). Borrower WhatsApp/phone is never shown.

5. Lender can reply:  
   “I’ll take request 1” → system:
   - Creates `loan` document (links borrowerUid + lenderUid)
   - Gives lender disbursement details (EFT only for immediate_eft; in-app instruction for atm_voucher; no phone)
   - Sends SMS to borrower: “Lender Bulelwa agreed to lend you R200! Expect funds soon.”
   - Loan request status → “matched”

6. Lender sends the money directly (EFT, Capitec app, MoMo, etc.).

7. Lender messages bot “done” or “sent money” → bot replies with unique web link (e.g. queensconnect.co.za/pop/loan_abc123)

8. Lender opens link on any phone/browser → uploads proof-of-payment (photo or PDF).  
   UI posts to server → server stores image in Cloud Storage, updates `loans` doc with popUrl + popUploadedAt, changes loan request status to “loaned”.

9. Lender replies “done” again → agent thanks them and offers next batch of requests.

## 6. Money Model (How Everyone Wins)

- Borrower pays **5% of the interest portion** only when repaying (same as before).  
  Example: R200 loan @ 35% interest = R70 interest → borrower pays R270 total  
  Lender gets R266.50 (95%), Queens Connect gets R3.50 (5%).

- Lender pays:
  - R5 to unlock one borrower’s full details
  - R10 to unlock a whole batch of 3  
    (100% of these fees go to Queens Connect)

- No fee on principal — only on interest and unlock fees.

## 7. Reputation & Safety

- Borrower reputationScore calculated exactly like before.
- Lenders see only aggregate score until they pay to unlock.
- After loan is marked “loaned”, reputations update on repayment.
- 2+ defaults → borrower auto-restricted.
- Lenders can report bad borrowers → moderationQueue.

## 8. Collections (Strict Schema Only)

- `loan_requests` – open requests (status: open | matched | loaned | cancelled). Disbursement: **immediate_eft** or **atm_voucher** only (PayShap removed).
- `loans` – final agreements (status: matched | active | repaid | defaulted)
- `lender_views` – sub-collection under lenders to track what they already paid to see
- `pending_repayments` – Yoco repayment links; when borrower pays, status is checked then loan marked repaid and stats updated (see schema).
- `lenders` & `borrowers` – same strict schemas from previous doc. Lender repayment details: **EFT only** (PayShap removed). Borrower repayment: via Yoco link only; never expose WhatsApp/phone between parties.

## 9. Notifications

- All lender alerts → SMS only at launch
- Borrower match alert → SMS
- Proof-of-payment confirmation → WhatsApp to both

## 10. Risk Controls

- Max 3 active loan requests per borrower
- Lenders see only 3 at a time to prevent overload
- All unlocks and loans logged for audit
- Manual admin blacklist for serious issues

-
