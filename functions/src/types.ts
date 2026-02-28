/**
 * Queens Connect – Firestore schema & API types
 * Aligned with docs/prompts/field reference.md and schema (24 collections).
 * All names camelCase; WA number = uid.
 */

import { Timestamp } from "firebase-admin/firestore";

// ----- 1. users -----
export interface User {
  waNumber: string; // same as doc id / uid
  name?: string;
  languagePref: "xhosa" | "english";
  createdAt: Timestamp;
  location?: string;
  isBusiness?: boolean;
  subscriptionTier?: "free" | "basic" | "premium";
  walletBalanceCents?: number;
}

// ----- 2. userSessions (subcollection users/{uid}/userSessions) -----
export interface UserSession {
  currentState?: Record<string, unknown>;
  updatedAt: Timestamp;
}

// ----- 3. listings -----
export interface Listing {
  ownerUid: string;
  type: "business" | "service" | "product" | "person";
  title: string;
  description: string;
  location: string;
  priceRange?: string;
  contact?: string;
  tags: string[];
  verified?: boolean;
  priorityUntil?: Timestamp;
  rating?: number;
  createdAt: Timestamp;
}

// ----- 4. infoBits -----
export interface InfoBit {
  authorUid: string;
  text: string;
  tags: string[];
  location?: string;
  expiresAt?: Timestamp | null;
  createdAt: Timestamp;
  upvotes?: number;
}

// ----- 5. news -----
export interface News {
  source: string;
  title: string;
  summaryEn: string;
  summaryXh: string;
  tags: string[];
  url?: string;
  createdAt: Timestamp;
}

// ----- 6. knowledgeShare -----
export interface KnowledgeShare {
  title: string;
  contentEn: string;
  contentXh?: string;
  tags: string[];
  createdAt: Timestamp;
}

// ----- 7. events -----
export interface Event {
  title: string;
  description?: string;
  startAt: Timestamp;
  endAt?: Timestamp;
  location: string;
  createdBy: string;
  tags: string[];
  createdAt: Timestamp;
}

// ----- 8. towns -----
export interface Town {
  name: string;
  region?: string;
  createdAt: Timestamp;
}

// ----- 9. suburbs -----
export interface Suburb {
  name: string;
  townId: string;
  createdAt: Timestamp;
}

// ----- 10. govInfo -----
export interface GovInfo {
  title: string;
  body: string;
  source?: string;
  tags: string[];
  createdAt: Timestamp;
}

// ----- 11. emergencyNumbers -----
export interface EmergencyNumber {
  name: string;
  number: string;
  category?: string;
  createdAt: Timestamp;
}

// ----- 12. payments -----
export interface Payment {
  payerUid: string;
  payeeUid: string;
  amountCents: number;
  status: "pending" | "paid" | "failed";
  dealId?: string;
  ikhokhaRef?: string;
  createdAt: Timestamp;
  updatedAt: Timestamp;
}

// ----- 13. wallets -----
export interface Wallet {
  ownerUid: string;
  balanceCents: number;
  updatedAt: Timestamp;
}

// ----- 14. lostAndFound -----
export interface LostAndFound {
  reporterUid: string;
  text: string;
  photoUrl?: string;
  location: string;
  type: "lost" | "found";
  createdAt: Timestamp;
}

// ----- 15. complaints -----
export interface Complaint {
  reporterUid: string;
  itemType: string;
  itemId: string;
  reason: string;
  status?: string;
  createdAt: Timestamp;
}

// ----- 16. communityUpdates -----
export interface CommunityUpdate {
  type: string;
  title: string;
  body: string;
  tags: string[];
  createdAt: Timestamp;
}

// ----- 17. transportFares -----
export interface TransportFare {
  authorUid: string;
  routeKey: string; // e.g. "komani-east-london"
  priceCents: number;
  location?: string;
  expiresAt?: Timestamp | null;
  createdAt: Timestamp;
}

// ----- 18. transportLocations -----
export interface TransportLocation {
  name: string;
  description: string;
  townId?: string;
  createdAt: Timestamp;
}

// ----- 19. subscriptions -----
export interface Subscription {
  userUid: string;
  tier: "basic" | "premium";
  validUntil: Timestamp;
  createdAt: Timestamp;
}

// ----- 20. ratingsAndReviews (subcollection listings/{id}/ratingsAndReviews) -----
export interface RatingAndReview {
  listingId: string;
  reviewerUid: string;
  rating: number;
  text?: string;
  createdAt: Timestamp;
}

// ----- 21. deals -----
export interface Deal {
  buyerUid: string;
  sellerUid: string;
  listingId?: string | null;
  infoBitId?: string | null;
  initialOffer?: string | null;
  status: "open" | "agreed" | "paid" | "cancelled";
  messages: Array<{ from: "buyer" | "seller"; text: string; at: Timestamp }>;
  agreedPriceCents?: number | null;
  createdAt: Timestamp;
  updatedAt: Timestamp;
}

// ----- 22. moderationQueue -----
export interface ModerationQueueItem {
  itemType: string;
  itemId: string;
  reason: string;
  reporterUid: string;
  status: "pending" | "reviewed";
  createdAt: Timestamp;
}

// ----- 23. notifications -----
export interface Notification {
  targetUid: string;
  title: string;
  body: string;
  type?: string;
  read: boolean;
  createdAt: Timestamp;
}

// ----- 24. configs (single doc "global") -----
export interface ConfigGlobal {
  maintenanceMode?: boolean;
  infoBitsDailyLimitFree?: number;
  searchDailyLimitFree?: number;
  updatedAt: Timestamp;
}

// ----- 25. loan_requests (lending & borrowing) -----
export interface LoanRequest {
  borrowerUid: string;
  amountCents: number;
  repayByDate: Timestamp;
  purpose: string;
  bank: "capitec" | "fnb" | "standard_bank" | "absa" | "other";
  status: "open" | "matched" | "loaned" | "cancelled";
  createdAt: Timestamp;
  updatedAt: Timestamp;
}

// ----- 26. loans (lending & borrowing) -----
export interface Loan {
  borrowerUid: string;
  lenderUid: string;
  loanRequestId: string;
  amountCents: number;
  interestCents: number;
  totalToRepayCents: number;
  status: "matched" | "active" | "repaid" | "defaulted";
  createdAt: Timestamp;
  matchedAt: Timestamp;
  dueDate: Timestamp;
  repaidAt: Timestamp | null;
  popUrl: string | null;
  popUploadedAt: Timestamp | null;
  notesFromBorrower: string;
  notesFromLender: string;
}

// ----- 27. lender_views (subcollection lenders/{lenderUid}/views) -----
export interface LenderView {
  loanRequestId: string;
  unlockedAt: Timestamp;
  feePaidCents: number;
}

// ----- API response shape (all callables) -----
export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
}

// ----- Callable input types -----
export interface CreateUserIfNotExistsInput {
  waNumber: string;
  name?: string;
  location?: string;
}

export interface UpdateUserProfileInput {
  name?: string;
  languagePref?: "xhosa" | "english";
  location?: string;
  isBusiness?: boolean;
}

export interface AddInfoBitInput {
  text: string;
  tags: string[];
  location?: string;
  expiresHours?: number | null;
}

export interface CreateListingInput {
  title: string;
  description: string;
  location: string;
  type: "business" | "service" | "product" | "person";
  priceRange?: string;
  contact?: string;
  tags: string[];
}

export interface SearchEverythingInput {
  query: string;
  location?: string;
  limit?: number;
  filters?: { type?: string; tags?: string[] };
}

export interface StartNegotiationInput {
  listingId?: string | null;
  infoBitId?: string | null;
  userOffer: string;
  sellerUid: string;
}

export interface SendNegotiationMessageInput {
  dealId: string;
  message: string;
  fromBuyerOrSeller: "buyer" | "seller";
}

export interface CreateIkhokhaPaymentLinkInput {
  amountCents: number;
  payeeUid: string;
  description: string;
  dealId?: string;
}

export interface AddLostAndFoundInput {
  text: string;
  photoUrl?: string;
  location: string;
  type: "lost" | "found";
}

export interface ReportContentInput {
  itemType: string;
  itemId: string;
  reason: string;
}

export interface GetCommunityUpdatesInput {
  type?: string;
  limit?: number;
}

export interface OrchestratorCallInput {
  action: string;
  payload: Record<string, unknown>;
}

// ----- Didit.me KYC verification -----
export interface CreateVerificationSessionInput {
  waNumber: string;
  workflow_id?: string;
}

export interface CreateVerificationSessionOutput {
  url: string;
  session_id: string;
  session_token: string;
}

export interface CheckVerificationResultInput {
  waNumber: string;
}

export interface CheckVerificationResultOutput {
  approved: boolean;
  message?: string;
  decision?: Record<string, unknown>;
}

// ----- Lending & Borrowing callable inputs -----

export interface CreateLoanRequestInput {
  amountCents: number;
  repayByDate: string; // ISO date string
  purpose: string;
  bank: "capitec" | "fnb" | "standard_bank" | "absa" | "other";
}

export interface GetLoanRequestsBatchInput {
  limit?: number;
  pageCursor?: string;
}

export interface UnlockLoanRequestsInput {
  loanRequestIds: string[];
  feePaidCents?: number;
}

export interface UploadProofOfPaymentInput {
  loanId: string;
  popUrl: string;
}

// ----- Stokvel -----
export interface NotifyStokvelNewMemberInput {
  stokvelId: string;
  newMemberWaNumber?: string;
  newMemberName?: string;
}
