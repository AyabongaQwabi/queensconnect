/**
 * Queens Connect – Firebase Cloud Functions
 * One WhatsApp number super app for Komani/Queenstown. Kasi-ready, Xhosa-first.
 */

import * as functions from "firebase-functions";
import * as admin from "firebase-admin";
import type {
  ApiResponse,
  CreateUserIfNotExistsInput,
  UpdateUserProfileInput,
  AddInfoBitInput,
  CreateListingInput,
  SearchEverythingInput,
  StartNegotiationInput,
  SendNegotiationMessageInput,
  CreateIkhokhaPaymentLinkInput,
  AddLostAndFoundInput,
  ReportContentInput,
  GetCommunityUpdatesInput,
  OrchestratorCallInput,
  CreateVerificationSessionInput,
  CreateVerificationSessionOutput,
  CheckVerificationResultInput,
  CheckVerificationResultOutput,
  CreateLoanRequestInput,
  GetLoanRequestsBatchInput,
  UnlockLoanRequestsInput,
  UploadProofOfPaymentInput,
  NotifyStokvelNewMemberInput,
} from "./types";

admin.initializeApp();
const db = admin.firestore();
const FieldValue = admin.firestore.FieldValue;

// ---------- Helpers ----------

/** Log action for analytics / debugging. */
function logAnalytics(action: string, uid: string, extra?: Record<string, unknown>): void {
  console.log("KASI-ORACLE:", action, uid, extra !== undefined ? JSON.stringify(extra) : "");
}

/** Generate 6-char alphanumeric code for pending InfoBits/transportFares (upvote flow). */
function generateShortCode(): string {
  const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
  let code = "";
  for (let i = 0; i < 6; i++) {
    code += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return code;
}

/** Notify watchers when transport fare changes (writes to notifications). */
async function notifyWatchers(
  fareId: string,
  routeKey: string,
  priceCents: number,
  location?: string
): Promise<void> {
  // In production: query users who watched this route, write to their notifications
  const ref = db.collection("notifications");
  const snapshot = await db
    .collection("configs")
    .doc("global")
    .get();
  const watchers: string[] = snapshot.exists ? (snapshot.data()?.fareWatcherUids as string[]) ?? [] : [];
  const body = `Taxis ${routeKey} now R${(priceCents / 100).toFixed(0)}${location ? " – " + location : ""}`;
  const batch = db.batch();
  for (const targetUid of watchers.slice(0, 50)) {
    batch.set(ref.doc(), {
      targetUid,
      title: "Fresh taxi price",
      body,
      type: "transport_fare",
      read: false,
      createdAt: FieldValue.serverTimestamp(),
    });
  }
  if (watchers.length > 0) await batch.commit();
  logAnalytics("notifyWatchers", "system", { fareId, count: watchers.length });
}

/** Require auth and return uid or throw. */
function requireAuth(context: functions.https.CallableContext): string {
  if (!context.auth?.uid) {
    throw new functions.https.HttpsError("unauthenticated", "Eish, you need to be logged in my bra.");
  }
  return context.auth.uid;
}

/** Return standard API shape. */
function ok<T>(data: T): ApiResponse<T> {
  return { success: true, data };
}
function err(message: string): ApiResponse<never> {
  return { success: false, error: message };
}

// ---------- 1. webhookWhatsApp (onRequest) ----------

/** The front door – every WhatsApp message lands here. Meta calls with GET (verify) or POST (message). */
export const webhookWhatsApp = functions.https.onRequest(async (req, res) => {
  const secret = process.env.WEBHOOK_WHATSAPP_SECRET || "";
  if (req.method === "GET") {
    const token = req.query["hub.verify_token"] as string | undefined;
    if (token === secret) {
      res.status(200).send(req.query["hub.challenge"]);
      return;
    }
    res.status(403).send("Forbidden");
    return;
  }
  if (req.method !== "POST") {
    res.status(405).send("Method Not Allowed");
    return;
  }
  const sig = req.headers["x-hub-signature-256"] as string | undefined;
  if (secret && (!sig || sig.indexOf("sha256=") !== 0)) {
    res.status(401).send("Unauthorized");
    return;
  }
  const body = req.body as Record<string, unknown>;
  console.log("KASI-ORACLE: webhookWhatsApp payload", JSON.stringify(body).slice(0, 500));
  // TODO: Route to ADK Orchestrator; for now echo 200 so Meta is happy
  res.status(200).json({ received: true });
});

// ---------- 2. orchestratorCall (onCall) ----------

/** Main brain – agents call this with action + payload; we dispatch and return result. */
export const orchestratorCall = functions.https.onCall(async (data: OrchestratorCallInput, context) => {
  const uid = requireAuth(context);
  const { action, payload } = data || {};
  if (!action || typeof payload !== "object") {
    return err("Need action and payload my bra.");
  }
  try {
    switch (action) {
      case "createUserIfNotExists":
        return ok(await createUserIfNotExistsImpl({ ...(payload as Record<string, unknown>), waNumber: uid } as CreateUserIfNotExistsInput & { waNumber: string }));
      case "updateUserProfile":
        return ok(await updateUserProfileImpl(uid, payload as unknown as UpdateUserProfileInput));
      case "addInfoBit":
        return ok(await addInfoBitImpl(uid, payload as unknown as AddInfoBitInput));
      case "createListing":
        return ok(await createListingImpl(uid, payload as unknown as CreateListingInput));
      case "searchEverything":
        return ok(await searchEverythingImpl(uid, payload as unknown as SearchEverythingInput));
      case "startNegotiation":
        return ok(await startNegotiationImpl(uid, payload as unknown as StartNegotiationInput));
      case "sendNegotiationMessage":
        return ok(await sendNegotiationMessageImpl(uid, payload as unknown as SendNegotiationMessageInput));
      case "createIkhokhaPaymentLink":
        return ok(await createIkhokhaPaymentLinkImpl(uid, payload as unknown as CreateIkhokhaPaymentLinkInput));
      case "getWalletBalance":
        return ok(await getWalletBalanceImpl(uid));
      case "addLostAndFound":
        return ok(await addLostAndFoundImpl(uid, payload as unknown as AddLostAndFoundInput));
      case "reportContent":
        return ok(await reportContentImpl(uid, payload as unknown as ReportContentInput));
      case "getCommunityUpdates":
        return ok(await getCommunityUpdatesImpl(uid, payload as unknown as GetCommunityUpdatesInput));
      case "createVerificationSession":
        return ok(await createVerificationSessionImpl(uid, payload as unknown as CreateVerificationSessionInput));
      case "checkVerificationResult":
        return ok(await checkVerificationResultImpl(uid, payload as unknown as CheckVerificationResultInput));
      case "notifyStokvelNewMember":
        return ok(await notifyStokvelNewMemberImpl(uid, payload as unknown as NotifyStokvelNewMemberInput));
      default:
        return err("Unknown action: " + action);
    }
  } catch (e) {
    const msg = e instanceof Error ? e.message : "Something went wrong";
    logAnalytics("orchestratorCall_error", uid, { action, error: msg });
    return err(msg);
  }
});

// ---------- 3. createUserIfNotExists ----------

async function createUserIfNotExistsImpl(
  input: CreateUserIfNotExistsInput & { waNumber: string }
): Promise<{ userId: string; created: boolean }> {
  const { waNumber, name, location } = input;
  const userRef = db.collection("users").doc(waNumber);
  const userSnap = await userRef.get();
  if (userSnap.exists) {
    return { userId: waNumber, created: false };
  }
  const now = FieldValue.serverTimestamp();
  const walletRef = db.collection("wallets").doc(waNumber);
  await db.runTransaction(async (tx) => {
    tx.set(userRef, {
      waNumber,
      name: name ?? null,
      languagePref: "xhosa",
      createdAt: now,
      location: location ?? null,
      isBusiness: false,
      subscriptionTier: "free",
      walletBalanceCents: 0,
    });
    tx.set(walletRef, {
      ownerUid: waNumber,
      balanceCents: 0,
      updatedAt: now,
    });
  });
  logAnalytics("createUserIfNotExists", waNumber, { name });
  return { userId: waNumber, created: true };
}

export const createUserIfNotExists = functions.https.onCall(async (data: CreateUserIfNotExistsInput, context) => {
  const uid = requireAuth(context);
  return ok(await createUserIfNotExistsImpl({ ...data, waNumber: uid }));
});

// ---------- 4. updateUserProfile ----------

async function updateUserProfileImpl(uid: string, input: UpdateUserProfileInput): Promise<{ updated: boolean }> {
  const ref = db.collection("users").doc(uid);
  const allowed: Record<string, unknown> = {};
  if (input.name !== undefined) allowed.name = input.name;
  if (input.languagePref !== undefined) allowed.languagePref = input.languagePref;
  if (input.location !== undefined) allowed.location = input.location;
  if (input.isBusiness !== undefined) allowed.isBusiness = input.isBusiness;
  if (Object.keys(allowed).length === 0) return { updated: false };
  allowed.updatedAt = FieldValue.serverTimestamp();
  await ref.update(allowed);
  logAnalytics("updateUserProfile", uid, { fields: Object.keys(allowed) });
  return { updated: true };
}

export const updateUserProfile = functions.https.onCall(async (data: UpdateUserProfileInput, context) => {
  const uid = requireAuth(context);
  return ok(await updateUserProfileImpl(uid, data));
});

// ---------- 5. addInfoBit ----------

const INFO_BITS_DAILY_LIMIT_FREE = 5;

async function addInfoBitImpl(
  uid: string,
  input: AddInfoBitInput
): Promise<{ infoBitId: string; shortCode: string }> {
  const { text, tags, location, expiresHours } = input;
  if (!text || !Array.isArray(tags) || tags.length === 0) {
    throw new functions.https.HttpsError("invalid-argument", "Need text and at least one tag neh.");
  }
  const userSnap = await db.collection("users").doc(uid).get();
  const tier = userSnap.data()?.subscriptionTier ?? "free";
  if (tier === "free") {
    const start = new Date();
    start.setHours(0, 0, 0, 0);
    const countSnap = await db
      .collection("infoBits")
      .where("authorUid", "==", uid)
      .where("createdAt", ">=", admin.firestore.Timestamp.fromDate(start))
      .count()
      .get();
    if (countSnap.data().count >= INFO_BITS_DAILY_LIMIT_FREE) {
      throw new functions.https.HttpsError(
        "resource-exhausted",
        "Eish, free limit is 5 InfoBits per day. Try again tomorrow or upgrade bra."
      );
    }
  }
  const now = FieldValue.serverTimestamp();
  let expiresAt: admin.firestore.FieldValue | null = null;
  if (expiresHours != null && expiresHours > 0) {
    const t = new Date();
    t.setHours(t.getHours() + expiresHours);
    expiresAt = admin.firestore.Timestamp.fromDate(t);
  }
  const shortCode = generateShortCode();
  const ref = await db.collection("infoBits").add({
    authorUid: uid,
    text,
    tags: tags.map((t) => String(t).toLowerCase()),
    location: location ?? null,
    expiresAt,
    createdAt: now,
    status: "pending",
    shortCode,
    upvoteWaNumbers: [],
    pendingCreatedAt: now,
  });
  logAnalytics("addInfoBit", uid, { infoBitId: ref.id });
  return { infoBitId: ref.id, shortCode };
}

export const addInfoBit = functions.https.onCall(async (data: AddInfoBitInput, context) => {
  const uid = requireAuth(context);
  return ok(await addInfoBitImpl(uid, data));
});

// ---------- 6. createListing ----------

async function createListingImpl(uid: string, input: CreateListingInput): Promise<{ listingId: string }> {
  const { title, description, location, type, priceRange, contact, tags } = input;
  if (!title || !description || !location || !type || !Array.isArray(tags)) {
    throw new functions.https.HttpsError("invalid-argument", "Need title, description, location, type and tags.");
  }
  const normalizedTags = tags.map((t) => String(t).toLowerCase());
  const now = FieldValue.serverTimestamp();
  const ref = await db.collection("listings").add({
    ownerUid: uid,
    type,
    title,
    description,
    location,
    priceRange: priceRange ?? null,
    contact: contact ?? null,
    tags: normalizedTags,
    verified: false,
    createdAt: now,
  });
  logAnalytics("createListing", uid, { listingId: ref.id, type });
  return { listingId: ref.id };
}

export const createListing = functions.https.onCall(async (data: CreateListingInput, context) => {
  const uid = requireAuth(context);
  return ok(await createListingImpl(uid, data));
});

// ---------- 7. searchEverything ----------

async function searchEverythingImpl(
  uid: string,
  input: SearchEverythingInput
): Promise<{ results: Array<{ type: string; id: string; title?: string; text?: string; location?: string; priceRange?: string }> }> {
  const limit = Math.min(input.limit ?? 3, 10);
  const location = (input.location ?? "").toLowerCase();
  const query = (input.query ?? "").toLowerCase();
  const results: Array<{ type: string; id: string; title?: string; text?: string; location?: string; priceRange?: string }> = [];

  // Search infoBits: by tags or text substring (Firestore no full-text – we filter in memory for small sets)
  const infoBitsSnap = await db
    .collection("infoBits")
    .orderBy("createdAt", "desc")
    .limit(50)
    .get();
  for (const doc of infoBitsSnap.docs) {
    const d = doc.data();
    if (results.length >= limit) break;
    const text = (d.text || "").toLowerCase();
    const tags = (d.tags || []).join(" ");
    const loc = (d.location || "").toLowerCase();
    const match = !query || text.includes(query) || tags.includes(query) || (location && loc.includes(location));
    if (match) {
      results.push({
        type: "infoBit",
        id: doc.id,
        text: d.text,
        location: d.location,
      });
    }
  }

  // Search listings
  const listingsSnap = await db
    .collection("listings")
    .orderBy("createdAt", "desc")
    .limit(50)
    .get();
  for (const doc of listingsSnap.docs) {
    if (results.length >= limit) break;
    const d = doc.data();
    const title = (d.title || "").toLowerCase();
    const desc = (d.description || "").toLowerCase();
    const tags = (d.tags || []).join(" ");
    const loc = (d.location || "").toLowerCase();
    const match = !query || title.includes(query) || desc.includes(query) || tags.includes(query) || (location && loc.includes(location));
    if (match) {
      results.push({
        type: "listing",
        id: doc.id,
        title: d.title,
        location: d.location,
        priceRange: d.priceRange,
      });
    }
  }

  logAnalytics("searchEverything", uid, { query: input.query, count: results.length });
  return { results: results.slice(0, limit) };
}

export const searchEverything = functions.https.onCall(async (data: SearchEverythingInput, context) => {
  const uid = requireAuth(context);
  return ok(await searchEverythingImpl(uid, data));
});

// ---------- 8. startNegotiation ----------

async function startNegotiationImpl(
  uid: string,
  input: StartNegotiationInput
): Promise<{ dealId: string }> {
  const { listingId, infoBitId, userOffer, sellerUid } = input;
  if (!sellerUid) {
    throw new functions.https.HttpsError("invalid-argument", "Need sellerUid.");
  }
  const now = FieldValue.serverTimestamp();
  const ref = await db.collection("deals").add({
    buyerUid: uid,
    sellerUid,
    listingId: listingId ?? null,
    infoBitId: infoBitId ?? null,
    initialOffer: userOffer ?? null,
    status: "open",
    messages: [],
    agreedPriceCents: null,
    createdAt: now,
    updatedAt: now,
  });
  logAnalytics("startNegotiation", uid, { dealId: ref.id, sellerUid });
  return { dealId: ref.id };
}

export const startNegotiation = functions.https.onCall(async (data: StartNegotiationInput, context) => {
  const uid = requireAuth(context);
  return ok(await startNegotiationImpl(uid, data));
});

// ---------- 9. sendNegotiationMessage ----------

async function sendNegotiationMessageImpl(
  uid: string,
  input: SendNegotiationMessageInput
): Promise<{ sent: boolean }> {
  const { dealId, message, fromBuyerOrSeller } = input;
  if (!dealId || !message || !fromBuyerOrSeller) {
    throw new functions.https.HttpsError("invalid-argument", "Need dealId, message and fromBuyerOrSeller.");
  }
  const dealRef = db.collection("deals").doc(dealId);
  const dealSnap = await dealRef.get();
  if (!dealSnap.exists) {
    throw new functions.https.HttpsError("not-found", "Deal not found.");
  }
  const d = dealSnap.data()!;
  const isBuyer = fromBuyerOrSeller === "buyer";
  if ((isBuyer && d.buyerUid !== uid) || (!isBuyer && d.sellerUid !== uid)) {
    throw new functions.https.HttpsError("permission-denied", "Not your deal.");
  }
  const newMsg = { from: fromBuyerOrSeller, text: message, at: FieldValue.serverTimestamp() };
  await dealRef.update({
    messages: FieldValue.arrayUnion(newMsg),
    updatedAt: FieldValue.serverTimestamp(),
  });
  const otherUid = isBuyer ? d.sellerUid : d.buyerUid;
  await db.collection("notifications").add({
    targetUid: otherUid,
    title: "New negotiation message",
    body: message.slice(0, 80),
    type: "deal_message",
    read: false,
    createdAt: FieldValue.serverTimestamp(),
  });
  logAnalytics("sendNegotiationMessage", uid, { dealId });
  return { sent: true };
}

export const sendNegotiationMessage = functions.https.onCall(async (data: SendNegotiationMessageInput, context) => {
  const uid = requireAuth(context);
  return ok(await sendNegotiationMessageImpl(uid, data));
});

// ---------- notifyStokvelNewMember (used via orchestratorCall) ----------

async function notifyStokvelNewMemberImpl(
  uid: string,
  input: NotifyStokvelNewMemberInput
): Promise<{ notified: boolean }> {
  const { stokvelId, newMemberWaNumber, newMemberName } = input;
  if (!stokvelId) {
    throw new functions.https.HttpsError("invalid-argument", "stokvelId required.");
  }
  const memberWa = (newMemberWaNumber ?? uid).trim();
  if (memberWa !== uid) {
    throw new functions.https.HttpsError("permission-denied", "Only the joining member can trigger this.");
  }
  const stokvelSnap = await db.collection("stokvels").doc(stokvelId).get();
  if (!stokvelSnap.exists) {
    throw new functions.https.HttpsError("not-found", "Stokvel not found.");
  }
  const stokvel = stokvelSnap.data()!;
  const ownerWaNumber = (stokvel.ownerWaNumber as string) || "";
  const stokvelName = (stokvel.name as string) || "Stokvel";
  const displayName = (newMemberName || memberWa).trim() || "A member";
  await db.collection("notifications").add({
    targetUid: ownerWaNumber,
    title: "New stokvel join request",
    body: `${displayName} requested to join your stokvel **${stokvelName}**.`,
    type: "stokvel_new_member",
    read: false,
    createdAt: FieldValue.serverTimestamp(),
  });
  logAnalytics("notifyStokvelNewMember", uid, { stokvelId, ownerWaNumber: ownerWaNumber.slice(0, 6) + "***" });
  return { notified: true };
}

// ---------- 10. createIkhokhaPaymentLink ----------

async function createIkhokhaPaymentLinkImpl(
  uid: string,
  input: CreateIkhokhaPaymentLinkInput
): Promise<{ paymentLink: string; paymentId: string }> {
  const { amountCents, payeeUid, description, dealId } = input;
  if (amountCents <= 0 || !payeeUid) {
    throw new functions.https.HttpsError("invalid-argument", "Need amount and payee.");
  }
  const now = FieldValue.serverTimestamp();
  const paymentRef = await db.collection("payments").add({
    payerUid: uid,
    payeeUid,
    amountCents,
    status: "pending",
    description: description ?? "",
    dealId: dealId ?? null,
    ikhokhaRef: null,
    createdAt: now,
    updatedAt: now,
  });
  // Stub: real implementation would call Ikhokha API and store returned link/ref
  const baseUrl = process.env.IKHOKHA_BASE_URL || "https://pay.ikhokha.com";
  const paymentLink = `${baseUrl}/pay?ref=qc-${paymentRef.id}&amount=${amountCents}&desc=${encodeURIComponent(description ?? "")}`;
  logAnalytics("createIkhokhaPaymentLink", uid, { paymentId: paymentRef.id, amountCents });
  return { paymentLink, paymentId: paymentRef.id };
}

export const createIkhokhaPaymentLink = functions.https.onCall(async (data: CreateIkhokhaPaymentLinkInput, context) => {
  const uid = requireAuth(context);
  return ok(await createIkhokhaPaymentLinkImpl(uid, data));
});

// ---------- 11. ikhokhaWebhook (onRequest) ----------

export const ikhokhaWebhook = functions.https.onRequest(async (req, res) => {
  if (req.method !== "POST") {
    res.status(405).send("Method Not Allowed");
    return;
  }
  const secret = process.env.IKHOKHA_WEBHOOK_SECRET || "";
  const sig = req.headers["x-ikhokha-signature"] as string | undefined;
  if (secret && (!sig || sig !== secret)) {
    res.status(401).send("Unauthorized");
    return;
  }
  const body = req.body as { paymentId?: string; status?: string; ref?: string };
  const paymentId = body.paymentId || body.ref;
  if (!paymentId) {
    res.status(400).send("Bad Request");
    return;
  }
  const paymentRef = db.collection("payments").doc(paymentId);
  const snap = await paymentRef.get();
  if (!snap.exists) {
    res.status(404).send("Not Found");
    return;
  }
  const payment = snap.data()!;
  if (payment.status === "paid") {
    res.status(200).json({ success: true, message: "Already processed" });
    return;
  }
  const payeeWalletRef = db.collection("wallets").doc(payment.payeeUid);
  await db.runTransaction(async (tx) => {
    const walletSnap = await tx.get(payeeWalletRef);
    tx.update(paymentRef, {
      status: "paid",
      ikhokhaRef: body.ref ?? paymentId,
      updatedAt: FieldValue.serverTimestamp(),
    });
    if (walletSnap.exists) {
      tx.update(payeeWalletRef, {
        balanceCents: FieldValue.increment(payment.amountCents),
        updatedAt: FieldValue.serverTimestamp(),
      });
    }
  });
  await db.collection("notifications").add({
    targetUid: payment.payeeUid,
    title: "Payment received",
    body: `R${(payment.amountCents / 100).toFixed(2)} received`,
    type: "payment",
    read: false,
    createdAt: FieldValue.serverTimestamp(),
  });
  logAnalytics("ikhokhaWebhook", "system", { paymentId });
  res.status(200).json({ success: true });
});

// ---------- 12. getWalletBalance ----------

async function getWalletBalanceImpl(
  uid: string
): Promise<{ balanceCents: number; recentTransactions: Array<{ amountCents: number; at: string; type: string }> }> {
  const walletSnap = await db.collection("wallets").doc(uid).get();
  const balanceCents = !walletSnap.exists ? 0 : (walletSnap.data()!.balanceCents ?? 0);
  const paymentsSnap = await db
    .collection("payments")
    .where("payeeUid", "==", uid)
    .orderBy("createdAt", "desc")
    .limit(10)
    .get();
  const recentTransactions = paymentsSnap.docs.map((doc) => {
    const d = doc.data();
    return {
      amountCents: d.amountCents,
      at: (d.createdAt as admin.firestore.Timestamp)?.toDate?.()?.toISOString?.() ?? "",
      type: d.payerUid === uid ? "sent" : "received",
    };
  });
  return { balanceCents, recentTransactions };
}

export const getWalletBalance = functions.https.onCall(async (_data, context) => {
  const uid = requireAuth(context);
  return ok(await getWalletBalanceImpl(uid));
});

// ---------- 13. addLostAndFound ----------

async function addLostAndFoundImpl(uid: string, input: AddLostAndFoundInput): Promise<{ id: string }> {
  const { text, photoUrl, location, type } = input;
  if (!text || !location || !type) {
    throw new functions.https.HttpsError("invalid-argument", "Need text, location and type (lost/found).");
  }
  const ref = await db.collection("lostAndFound").add({
    reporterUid: uid,
    text,
    photoUrl: photoUrl ?? null,
    location,
    type: type === "found" ? "found" : "lost",
    createdAt: FieldValue.serverTimestamp(),
  });
  logAnalytics("addLostAndFound", uid, { id: ref.id });
  return { id: ref.id };
}

export const addLostAndFound = functions.https.onCall(async (data: AddLostAndFoundInput, context) => {
  const uid = requireAuth(context);
  return ok(await addLostAndFoundImpl(uid, data));
});

// ---------- 14. reportContent ----------

async function reportContentImpl(uid: string, input: ReportContentInput): Promise<{ reported: boolean }> {
  const { itemType, itemId, reason } = input;
  if (!itemType || !itemId || !reason) {
    throw new functions.https.HttpsError("invalid-argument", "Need itemType, itemId and reason.");
  }
  await db.collection("moderationQueue").add({
    itemType,
    itemId,
    reason,
    reporterUid: uid,
    status: "pending",
    createdAt: FieldValue.serverTimestamp(),
  });
  logAnalytics("reportContent", uid, { itemType, itemId });
  return { reported: true };
}

export const reportContent = functions.https.onCall(async (data: ReportContentInput, context) => {
  const uid = requireAuth(context);
  return ok(await reportContentImpl(uid, data));
});

// ---------- 15. getCommunityUpdates ----------

async function getCommunityUpdatesImpl(
  _uid: string,
  input: GetCommunityUpdatesInput
): Promise<{ items: Array<Record<string, unknown>> }> {
  const limit = Math.min(input.limit ?? 10, 20);
  const type = input.type;
  const items: Array<Record<string, unknown>> = [];

  if (!type || type === "news") {
    const newsSnap = await db.collection("news").orderBy("createdAt", "desc").limit(limit).get();
    newsSnap.docs.forEach((doc) => items.push({ ...doc.data(), id: doc.id, _type: "news" }));
  }
  if (!type || type === "events") {
    const eventsSnap = await db.collection("events").orderBy("startAt", "asc").limit(limit).get();
    eventsSnap.docs.forEach((doc) => items.push({ ...doc.data(), id: doc.id, _type: "event" }));
  }
  if (!type || type === "govInfo") {
    const govSnap = await db.collection("govInfo").orderBy("createdAt", "desc").limit(limit).get();
    govSnap.docs.forEach((doc) => items.push({ ...doc.data(), id: doc.id, _type: "govInfo" }));
  }

  return { items: items.slice(0, limit) };
}

export const getCommunityUpdates = functions.https.onCall(async (data: GetCommunityUpdatesInput, context) => {
  const uid = requireAuth(context);
  return ok(await getCommunityUpdatesImpl(uid, data));
});

// ---------- 16. createVerificationSession (Didit.me KYC) ----------

const DIDIT_API_BASE = "https://verification.didit.me/v3";

async function createVerificationSessionImpl(
  uid: string,
  input: CreateVerificationSessionInput
): Promise<CreateVerificationSessionOutput> {
  const apiKey = process.env.DIDIT_API_KEY;
  const workflowId = input.workflow_id ?? process.env.DIDIT_WORKFLOW_ID;
  if (!apiKey || !workflowId) {
    throw new functions.https.HttpsError("failed-precondition", "Didit verification not configured (DIDIT_API_KEY, DIDIT_WORKFLOW_ID).");
  }
  const waNumber = input.waNumber || uid;
  const body: Record<string, unknown> = { workflow_id: workflowId };
  if (waNumber) body.vendor_data = waNumber;

  const res = await fetch(`${DIDIT_API_BASE}/session/`, {
    method: "POST",
    headers: {
      "x-api-key": apiKey,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new functions.https.HttpsError("internal", `Didit create session failed: ${res.status} ${text}`);
  }
  const data = (await res.json()) as { session_id: string; session_token: string; url: string };
  const { session_id, session_token, url } = data;
  if (!session_id || !session_token || !url) {
    throw new functions.https.HttpsError("internal", "Didit response missing session_id, session_token or url.");
  }

  await db.collection("users").doc(waNumber).set(
    {
      diditSessionId: session_id,
      diditSessionToken: session_token,
      lastActiveAt: FieldValue.serverTimestamp(),
    },
    { merge: true }
  );
  logAnalytics("createVerificationSession", waNumber, { session_id });
  return { url, session_id, session_token };
}

export const createVerificationSession = functions.https.onCall(async (data: CreateVerificationSessionInput, context) => {
  const uid = requireAuth(context);
  const payload = { ...data, waNumber: data.waNumber || uid };
  return ok(await createVerificationSessionImpl(uid, payload));
});

// ---------- 17. checkVerificationResult (Didit.me KYC) ----------

const FACE_MATCH_APPROVED_THRESHOLD = 60;

async function checkVerificationResultImpl(
  uid: string,
  input: CheckVerificationResultInput
): Promise<CheckVerificationResultOutput> {
  const apiKey = process.env.DIDIT_API_KEY;
  if (!apiKey) {
    throw new functions.https.HttpsError("failed-precondition", "Didit verification not configured (DIDIT_API_KEY).");
  }
  const waNumber = input.waNumber || uid;
  const userSnap = await db.collection("users").doc(waNumber).get();
  const diditSessionId = userSnap.data()?.diditSessionId as string | undefined;
  if (!diditSessionId) {
    return { approved: false, message: "No verification session found. Start verification first." };
  }

  const res = await fetch(`${DIDIT_API_BASE}/session/${diditSessionId}/decision/`, {
    method: "GET",
    headers: { "x-api-key": apiKey },
  });
  if (!res.ok) {
    const text = await res.text();
    return { approved: false, message: `Could not fetch decision: ${res.status} ${text}` };
  }
  const decision = (await res.json()) as {
    id_verifications?: Array<{ status: string }>;
    face_matches?: Array<{ status: string; score?: number }>;
    session_id?: string;
    status?: string;
    created_at?: string;
    [key: string]: unknown;
  };

  const idOk = decision.id_verifications?.[0]?.status === "Approved";
  const faceMatches = decision.face_matches ?? [];
  const faceOk =
    faceMatches.length === 0 ||
    faceMatches.some(
      (f) => f.status === "Approved" || (typeof f.score === "number" && f.score >= FACE_MATCH_APPROVED_THRESHOLD)
    );
  const approved = idOk && faceOk;

  const now = FieldValue.serverTimestamp();
  if (approved) {
    await db.collection("verifications").doc(waNumber).set({
      waNumber,
      sessionId: diditSessionId,
      status: "verified",
      rawResponse: decision,
      createdAt: now,
    });
    await db.collection("users").doc(waNumber).update({
      kycVerifiedAt: now,
      kycStatus: "verified",
      lastActiveAt: now,
    });
    logAnalytics("checkVerificationResult_approved", waNumber, { session_id: diditSessionId });
    return { approved: true, message: "Verification approved.", decision };
  } else {
    await db.collection("users").doc(waNumber).set(
      { kycStatus: "failed", lastActiveAt: now },
      { merge: true }
    );
    logAnalytics("checkVerificationResult_failed", waNumber, { session_id: diditSessionId });
    return { approved: false, message: "Verification did not pass. You can try again with a new link." };
  }
}

export const checkVerificationResult = functions.https.onCall(async (data: CheckVerificationResultInput, context) => {
  const uid = requireAuth(context);
  const payload = { ...data, waNumber: data.waNumber || uid };
  return ok(await checkVerificationResultImpl(uid, payload));
});

// ---------- 18. createLoanRequest (lending & borrowing) ----------

async function createLoanRequestImpl(
  uid: string,
  input: CreateLoanRequestInput
): Promise<{ loanRequestId: string }> {
  const { amountCents, repayByDate, purpose, bank } = input;
  if (!amountCents || amountCents <= 0) {
    throw new functions.https.HttpsError("invalid-argument", "Need a positive amount my friend.");
  }
  if (!repayByDate || !purpose || !bank) {
    throw new functions.https.HttpsError("invalid-argument", "Need repay date, purpose and bank.");
  }
  if (purpose.length > 80) {
    throw new functions.https.HttpsError("invalid-argument", "Purpose must be at most 80 characters.");
  }
  const allowedBanks = ["capitec", "fnb", "standard_bank", "absa", "other"] as const;
  if (!allowedBanks.includes(bank as (typeof allowedBanks)[number])) {
    throw new functions.https.HttpsError("invalid-argument", "Bank must be one of capitec, fnb, standard_bank, absa, other.");
  }
  const d = new Date(repayByDate);
  if (isNaN(d.getTime())) {
    throw new functions.https.HttpsError("invalid-argument", "repayByDate must be a valid date (YYYY-MM-DD or ISO string).");
  }
  const repayTs = admin.firestore.Timestamp.fromDate(d);
  const now = FieldValue.serverTimestamp();
  const ref = await db.collection("loan_requests").add({
    borrowerUid: uid,
    amountCents,
    repayByDate: repayTs,
    purpose,
    bank,
    status: "open",
    createdAt: now,
    updatedAt: now,
  });
  logAnalytics("createLoanRequest", uid, { loanRequestId: ref.id, amountCents });
  return { loanRequestId: ref.id };
}

export const createLoanRequest = functions.https.onCall(async (data: CreateLoanRequestInput, context) => {
  const uid = requireAuth(context);
  return ok(await createLoanRequestImpl(uid, data));
});

// ---------- 19. getLoanRequestsBatch (masked, for lenders) ----------

function maskDisplayNameTs(displayName: string): string {
  const name = (displayName || "").trim();
  if (!name) return "Unknown";
  const parts = name.split(/\s+/);
  const first = parts[0].charAt(0).toUpperCase() + parts[0].slice(1);
  if (parts.length === 1) return first;
  const lastInitial = parts[parts.length - 1].charAt(0).toUpperCase();
  return `${first} ${lastInitial}.`;
}

function formatBorrowerReputationTs(b: Partial<{ reputationScore: number; totalLoansTaken: number; totalRepaidOnTime: number; totalRepaidLate: number; totalDefaulted: number }>): string {
  const score = typeof b.reputationScore === "number" ? b.reputationScore : 0;
  const totalLoans = typeof b.totalLoansTaken === "number" ? b.totalLoansTaken : 0;
  const onTime = typeof b.totalRepaidOnTime === "number" ? b.totalRepaidOnTime : 0;
  const late = typeof b.totalRepaidLate === "number" ? b.totalRepaidLate : 0;
  const def = typeof b.totalDefaulted === "number" ? b.totalDefaulted : 0;
  if (totalLoans <= 0) return `${score.toFixed(1)}★ (new borrower)`;
  const parts: string[] = [];
  if (onTime) parts.push(`${onTime} on time`);
  if (late) parts.push(`${late} late`);
  if (def) parts.push(`${def} defaulted`);
  const details = parts.length ? parts.join(", ") : "history";
  return `${score.toFixed(1)}★ (${totalLoans} loans, ${details})`;
}

async function getLoanRequestsBatchImpl(
  uid: string,
  input: GetLoanRequestsBatchInput
): Promise<{ items: Array<Record<string, unknown>>; nextCursor?: string }> {
  const lenderUid = uid;
  const limit = Math.min(input.limit ?? 3, 10);
  const pageCursor = input.pageCursor;

  // Already unlocked requests for this lender
  const viewsSnap = await db.collection("lenders").doc(lenderUid).collection("views").get();
  const unlockedIds = new Set<string>();
  viewsSnap.docs.forEach((doc) => {
    const d = doc.data() as { loanRequestId?: string };
    unlockedIds.add(d.loanRequestId ?? doc.id);
  });

  let query = db.collection("loan_requests").where("status", "==", "open").orderBy("createdAt", "desc");
  if (pageCursor) {
    const cursorDoc = await db.collection("loan_requests").doc(pageCursor).get();
    if (cursorDoc.exists) {
      query = query.startAfter(cursorDoc);
    }
  }

  const snap = await query.limit(limit + 1).get();
  const items: Array<Record<string, unknown>> = [];
  let nextCursor: string | undefined;

  for (const doc of snap.docs) {
    const id = doc.id;
    if (unlockedIds.has(id)) continue;
    const d = doc.data() as any;
    const borrowerUid = d.borrowerUid as string;
    const borrowerSnap = borrowerUid ? await db.collection("borrowers").doc(borrowerUid).get() : null;
    const borrower = (borrowerSnap?.data() as any) ?? {};
    const displayName = (borrower.displayName as string) || borrowerUid;
    const maskedName = maskDisplayNameTs(displayName);
    const repSummary = formatBorrowerReputationTs(borrower);
    const repayBy = (d.repayByDate as admin.firestore.Timestamp | undefined)?.toDate?.()?.toISOString?.() ?? null;
    const createdAtIso = (d.createdAt as admin.firestore.Timestamp | undefined)?.toDate?.()?.toISOString?.() ?? null;

    items.push({
      loanRequestId: id,
      maskedName,
      amountCents: d.amountCents,
      repayByDate: repayBy,
      reputationSummary: repSummary,
      reputationScore: typeof borrower.reputationScore === "number" ? borrower.reputationScore : 0,
      createdAt: createdAtIso,
    });
    if (items.length === limit) {
      nextCursor = id;
      break;
    }
  }

  logAnalytics("getLoanRequestsBatch", lenderUid, { count: items.length, nextCursor });
  return { items, nextCursor };
}

export const getLoanRequestsBatch = functions.https.onCall(async (data: GetLoanRequestsBatchInput, context) => {
  const uid = requireAuth(context);
  return ok(await getLoanRequestsBatchImpl(uid, data));
});

// ---------- 20. unlockLoanRequests (after Ikhokha payment webhook) ----------

async function unlockLoanRequestsImpl(
  uid: string,
  input: UnlockLoanRequestsInput
): Promise<{ unlocked: string[]; totalFeeCents: number }> {
  const lenderUid = uid;
  const loanRequestIds = input.loanRequestIds ?? [];
  if (loanRequestIds.length === 0) {
    throw new functions.https.HttpsError("invalid-argument", "loanRequestIds required.");
  }
  if (loanRequestIds.length > 3) {
    throw new functions.https.HttpsError("invalid-argument", "Can only unlock up to 3 loan requests at a time.");
  }

  // Fee: R5 per request or R10 for batch of 3
  let totalFeeCents: number;
  if (loanRequestIds.length === 1) {
    totalFeeCents = 500;
  } else if (loanRequestIds.length === 3) {
    totalFeeCents = 1000;
  } else {
    totalFeeCents = 500 * loanRequestIds.length;
  }
  const perRequestFee = Math.floor(totalFeeCents / loanRequestIds.length);

  const viewsCol = db.collection("lenders").doc(lenderUid).collection("views");
  const now = FieldValue.serverTimestamp();
  const unlocked: string[] = [];

  for (const rawId of loanRequestIds) {
    const id = String(rawId || "").trim();
    if (!id) continue;
    const reqRef = db.collection("loan_requests").doc(id);
    const reqSnap = await reqRef.get();
    if (!reqSnap.exists) continue;
    const d = reqSnap.data() as any;
    if (d.status !== "open") continue;

    const viewRef = viewsCol.doc(id);
    const viewSnap = await viewRef.get();
    if (!viewSnap.exists) {
      await viewRef.set({
        loanRequestId: id,
        unlockedAt: now,
        feePaidCents: perRequestFee,
      });
    }
    unlocked.push(id);
  }

  logAnalytics("unlockLoanRequests", lenderUid, { unlockedCount: unlocked.length, totalFeeCents });
  return { unlocked, totalFeeCents };
}

export const unlockLoanRequests = functions.https.onCall(async (data: UnlockLoanRequestsInput, context) => {
  const uid = requireAuth(context);
  return ok(await unlockLoanRequestsImpl(uid, data));
});

// ---------- 21. uploadProofOfPayment (update loan + loan_request) ----------

async function uploadProofOfPaymentImpl(
  uid: string,
  input: UploadProofOfPaymentInput
): Promise<{ updated: boolean }> {
  const { loanId, popUrl } = input;
  if (!loanId || !popUrl) {
    throw new functions.https.HttpsError("invalid-argument", "Need loanId and popUrl.");
  }
  const loanRef = db.collection("loans").doc(loanId);
  const loanSnap = await loanRef.get();
  if (!loanSnap.exists) {
    throw new functions.https.HttpsError("not-found", "Loan not found.");
  }
  const loan = loanSnap.data() as any;
  if (loan.lenderUid !== uid) {
    throw new functions.https.HttpsError("permission-denied", "Only the lender can upload proof for this loan.");
  }
  const loanRequestId = loan.loanRequestId as string | undefined;
  const now = FieldValue.serverTimestamp();

  await loanRef.update({
    popUrl,
    popUploadedAt: now,
    status: "active",
  });
  if (loanRequestId) {
    await db.collection("loan_requests").doc(loanRequestId).update({
      status: "loaned",
      updatedAt: now,
    });
  }

  logAnalytics("uploadProofOfPayment", uid, { loanId, loanRequestId });
  return { updated: true };
}

export const uploadProofOfPayment = functions.https.onCall(async (data: UploadProofOfPaymentInput, context) => {
  const uid = requireAuth(context);
  return ok(await uploadProofOfPaymentImpl(uid, data));
});

// ---------- Scheduled: expireOldInfoBits ----------

/** Daily cleanup of expired InfoBits. */
export const expireOldInfoBits = functions.pubsub.schedule("0 2 * * *").onRun(async () => {
  const now = admin.firestore.Timestamp.now();
  const snap = await db.collection("infoBits").where("expiresAt", "<=", now).limit(200).get();
  const batch = db.batch();
  snap.docs.forEach((doc) => batch.delete(doc.ref));
  if (!snap.empty) await batch.commit();
  console.log("KASI-ORACLE: expireOldInfoBits deleted", snap.size);
  return null;
});

/** Daily: set status to "expired" for pending InfoBits and transportFares older than 7 days (no points). */
export const expirePendingGamificationItems = functions.pubsub.schedule("0 3 * * *").onRun(async () => {
  const now = admin.firestore.Timestamp.now();
  const sevenDaysAgo = new Date(now.toMillis() - 7 * 24 * 60 * 60 * 1000);
  const cutoff = admin.firestore.Timestamp.fromDate(sevenDaysAgo);

  const infoBitsSnap = await db
    .collection("infoBits")
    .where("status", "==", "pending")
    .where("pendingCreatedAt", "<", cutoff)
    .limit(200)
    .get();
  const transportSnap = await db
    .collection("transportFares")
    .where("status", "==", "pending")
    .where("pendingCreatedAt", "<", cutoff)
    .limit(200)
    .get();

  const batch = db.batch();
  infoBitsSnap.docs.forEach((doc) => batch.update(doc.ref, { status: "expired" }));
  transportSnap.docs.forEach((doc) => batch.update(doc.ref, { status: "expired" }));
  if (!infoBitsSnap.empty || !transportSnap.empty) await batch.commit();
  console.log(
    "KASI-ORACLE: expirePendingGamificationItems infoBits=",
    infoBitsSnap.size,
    "transportFares=",
    transportSnap.size
  );
  return null;
});

// ---------- Triggers ----------

/** On new InfoBit → add to moderation queue for light check (e.g. AI later). */
export const onInfoBitCreated = functions.firestore.document("infoBits/{id}").onCreate(async (snap) => {
  const d = snap.data();
  await db.collection("moderationQueue").add({
    itemType: "infoBit",
    itemId: snap.id,
    reason: "auto_new",
    reporterUid: d.authorUid,
    status: "pending",
    createdAt: FieldValue.serverTimestamp(),
  });
  logAnalytics("onInfoBitCreated_moderation", d.authorUid, { infoBitId: snap.id });
});

/** On transport fare update → notify watchers. */
export const onTransportFareUpdated = functions.firestore.document("transportFares/{id}").onUpdate(async (change) => {
  const after = change.after.data();
  await notifyWatchers(change.after.id, after.routeKey, after.priceCents, after.location);
});
