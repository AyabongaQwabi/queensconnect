// ==============================
// FIREBASE (FIRESTORE) SCHEMA
// ==============================

// ==============================
// 1. lenders (collection)
// ==============================
/lenders/{lenderUid} {
lenderUid: string, // = users.waNumber (doc id)
displayName: string,

maxAmountCents: number, // default: 50000
maxDurationDays: number, // default: 30
interestRatePercent: number, // default: 0

currentAvailableCents: number, // default: 0
maxLoansAtOnce: number, // default: 3

reputationScore: number, // float, default: 0.0 (0–5)
totalLoansGiven: number, // default: 0
totalRepaid: number, // default: 0
totalDefaulted: number, // default: 0
totalValueRepaidCents: number, // default: 0

badges: string[], // default: []
preferredLocations: string[], // default: []
preferredBanks: string[], // default: []

status: string, // "active" | "paused" | "blacklisted"
verifiedAt: Timestamp | null,

// Repayment details: where the borrower should send repayment (saved after first loan, reused). Only EFT supported (PayShap removed).
repaymentBankingDetails: { method: "eft", accountNumber?, branchCode?, bank?, accountType? } | null,

lendingSince: Timestamp,
lastActive: Timestamp,
createdAt: Timestamp,
updatedAt: Timestamp
}

// ==============================
// 2. borrowers (collection)
// ==============================
/borrowers/{borrowerUid} {
borrowerUid: string, // = users.waNumber (doc id)
displayName: string,
address?: string,   // shown to lender only after unlock (never waNumber to other party)

verifiedAt: Timestamp | null,

totalLoansTaken: number, // default: 0
totalRepaidOnTime: number, // default: 0
totalRepaidLate: number, // default: 0
totalDefaulted: number, // default: 0

totalAmountRepaidCents: number, // default: 0
totalAmountOwingCents: number, // default: 0
currentActiveLoansCount: number, // default: 0

reputationScore: number, // float, default: 0.0 (0–5)
badges: string[], // default: []
preferredBanks: string[], // default: []

status: string, // "active" | "restricted" | "blacklisted"

createdAt: Timestamp,
updatedAt: Timestamp
}

// ==============================
// 3. loans (collection) – Lending & Borrowing
// ==============================
/loans/{loanId} {
borrowerUid: string,        // borrower waNumber (users/borrowers doc id)
lenderUid: string,          // lender waNumber (lenders doc id)
loanRequestId: string,      // link back to loan_requests/{id}

amountCents: number,        // principal in cents
interestCents: number,      // interest portion in cents
totalToRepayCents: number,  // amountCents + interestCents

status: "matched" | "active" | "repaid" | "defaulted",

createdAt: Timestamp,
matchedAt: Timestamp,
dueDate: Timestamp,
repaidAt: Timestamp | null,

popUrl: string | null,       // Cloud Storage URL of proof-of-payment
popUploadedAt: Timestamp | null,
notesFromBorrower: string,   // max 200 chars
notesFromLender: string      // max 200 chars
}

// ==============================
// 4. loan_requests (collection)
// ==============================
/loan_requests/{loanRequestId} {
borrowerUid: string,   // borrower waNumber
amountCents: number,   // requested principal in cents
repayByDate: Timestamp,
purpose: string,       // max 80 chars
bank: "capitec" | "fnb" | "standard_bank" | "absa" | "other",
disbursementMethod: "immediate_eft" | "atm_voucher",  // PayShap removed
// For immediate_eft:
accountNumber?: string,
branchCode?: string,
accountType?: string,
// For atm_voucher:
atmVoucherCellphone?: string,
status: "open" | "matched" | "loaned" | "cancelled",
createdAt: Timestamp,
updatedAt: Timestamp
}

// ==============================
// 5. lender_views (subcollection under lenders/{lenderUid}/views)
// ==============================
/lenders/{lenderUid}/views/{viewId} {
loanRequestId: string,
unlockedAt: Timestamp,
feePaidCents: number    // R5 per request or R10 for batch of 3 (in cents)
}

// ==============================
// 6. pending_unlocks (collection) – Yoco pay link; doc id = externalTransactionID
// ==============================
/pending_unlocks/{externalTransactionID} {
lenderUid: string,
loanRequestIds: string[],
totalFeeCents: number,
paylinkID?: string,     // set after Yoco returns it
createdAt: Timestamp
}

// ==============================
// 7. pending_repayments (collection) – Yoco repayment link; doc id = externalTransactionID
// ==============================
/pending_repayments/{externalTransactionID} {
loanId: string,
borrowerUid: string,
totalCents: number,
paylinkID?: string,
createdAt: Timestamp
}

// ==============================
// REQUIRED COMPOSITE INDEXES
// ==============================

// lenders:
// status ASC
// currentAvailableCents DESC
// reputationScore DESC

// borrowers:
// status ASC
// reputationScore DESC

// loans:
// status ASC
// dueDate ASC
// borrowerUid ASC
// lenderUid ASC
// loanRequestId ASC
