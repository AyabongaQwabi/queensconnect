"use strict";
/**
 * Queens Connect – Firebase Cloud Functions
 * One WhatsApp number super app for Komani/Queenstown. Kasi-ready, Xhosa-first.
 */
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.onTransportFareUpdated = exports.onInfoBitCreated = exports.expirePendingGamificationItems = exports.expireOldInfoBits = exports.importKomaniNews = exports.uploadProofOfPayment = exports.unlockLoanRequests = exports.getLoanRequestsBatch = exports.createLoanRequest = exports.checkVerificationResult = exports.createVerificationSession = exports.getCommunityUpdates = exports.reportContent = exports.addLostAndFound = exports.getWalletBalance = exports.ikhokhaWebhook = exports.createIkhokhaPaymentLink = exports.sendNegotiationMessage = exports.startNegotiation = exports.searchEverything = exports.createListing = exports.addInfoBit = exports.updateUserProfile = exports.createUserIfNotExists = exports.orchestratorCall = exports.webhookWhatsApp = void 0;
const functions = __importStar(require("firebase-functions"));
const admin = __importStar(require("firebase-admin"));
admin.initializeApp();
const db = admin.firestore();
const FieldValue = admin.firestore.FieldValue;
// ---------- Helpers ----------
/** Log action for analytics / debugging. */
function logAnalytics(action, uid, extra) {
    console.log("KASI-ORACLE:", action, uid, extra !== undefined ? JSON.stringify(extra) : "");
}
/** Generate 6-char alphanumeric code for pending InfoBits/transportFares (upvote flow). */
function generateShortCode() {
    const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
    let code = "";
    for (let i = 0; i < 6; i++) {
        code += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return code;
}
/** Notify watchers when transport fare changes (writes to notifications). */
async function notifyWatchers(fareId, routeKey, priceCents, location) {
    var _a, _b;
    // In production: query users who watched this route, write to their notifications
    const ref = db.collection("notifications");
    const snapshot = await db
        .collection("configs")
        .doc("global")
        .get();
    const watchers = snapshot.exists ? (_b = (_a = snapshot.data()) === null || _a === void 0 ? void 0 : _a.fareWatcherUids) !== null && _b !== void 0 ? _b : [] : [];
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
    if (watchers.length > 0)
        await batch.commit();
    logAnalytics("notifyWatchers", "system", { fareId, count: watchers.length });
}
/** Require auth and return uid or throw. */
function requireAuth(context) {
    var _a;
    if (!((_a = context.auth) === null || _a === void 0 ? void 0 : _a.uid)) {
        throw new functions.https.HttpsError("unauthenticated", "Eish, you need to be logged in my bra.");
    }
    return context.auth.uid;
}
/** Return standard API shape. */
function ok(data) {
    return { success: true, data };
}
function err(message) {
    return { success: false, error: message };
}
// ---------- 1. webhookWhatsApp (onRequest) ----------
/** The front door – every WhatsApp message lands here. Meta calls with GET (verify) or POST (message). */
exports.webhookWhatsApp = functions.https.onRequest(async (req, res) => {
    const secret = process.env.WEBHOOK_WHATSAPP_SECRET || "";
    if (req.method === "GET") {
        const token = req.query["hub.verify_token"];
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
    const sig = req.headers["x-hub-signature-256"];
    if (secret && (!sig || sig.indexOf("sha256=") !== 0)) {
        res.status(401).send("Unauthorized");
        return;
    }
    const body = req.body;
    console.log("KASI-ORACLE: webhookWhatsApp payload", JSON.stringify(body).slice(0, 500));
    // TODO: Route to ADK Orchestrator; for now echo 200 so Meta is happy
    res.status(200).json({ received: true });
});
// ---------- 2. orchestratorCall (onCall) ----------
/** Main brain – agents call this with action + payload; we dispatch and return result. */
exports.orchestratorCall = functions.https.onCall(async (data, context) => {
    const uid = requireAuth(context);
    const { action, payload } = data || {};
    if (!action || typeof payload !== "object") {
        return err("Need action and payload my bra.");
    }
    try {
        switch (action) {
            case "createUserIfNotExists":
                return ok(await createUserIfNotExistsImpl(Object.assign(Object.assign({}, payload), { waNumber: uid })));
            case "updateUserProfile":
                return ok(await updateUserProfileImpl(uid, payload));
            case "addInfoBit":
                return ok(await addInfoBitImpl(uid, payload));
            case "createListing":
                return ok(await createListingImpl(uid, payload));
            case "searchEverything":
                return ok(await searchEverythingImpl(uid, payload));
            case "startNegotiation":
                return ok(await startNegotiationImpl(uid, payload));
            case "sendNegotiationMessage":
                return ok(await sendNegotiationMessageImpl(uid, payload));
            case "createIkhokhaPaymentLink":
                return ok(await createIkhokhaPaymentLinkImpl(uid, payload));
            case "getWalletBalance":
                return ok(await getWalletBalanceImpl(uid));
            case "addLostAndFound":
                return ok(await addLostAndFoundImpl(uid, payload));
            case "reportContent":
                return ok(await reportContentImpl(uid, payload));
            case "getCommunityUpdates":
                return ok(await getCommunityUpdatesImpl(uid, payload));
            case "createVerificationSession":
                return ok(await createVerificationSessionImpl(uid, payload));
            case "checkVerificationResult":
                return ok(await checkVerificationResultImpl(uid, payload));
            case "notifyStokvelNewMember":
                return ok(await notifyStokvelNewMemberImpl(uid, payload));
            default:
                return err("Unknown action: " + action);
        }
    }
    catch (e) {
        const msg = e instanceof Error ? e.message : "Something went wrong";
        logAnalytics("orchestratorCall_error", uid, { action, error: msg });
        return err(msg);
    }
});
// ---------- 3. createUserIfNotExists ----------
async function createUserIfNotExistsImpl(input) {
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
            name: name !== null && name !== void 0 ? name : null,
            languagePref: "xhosa",
            createdAt: now,
            location: location !== null && location !== void 0 ? location : null,
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
exports.createUserIfNotExists = functions.https.onCall(async (data, context) => {
    const uid = requireAuth(context);
    return ok(await createUserIfNotExistsImpl(Object.assign(Object.assign({}, data), { waNumber: uid })));
});
// ---------- 4. updateUserProfile ----------
async function updateUserProfileImpl(uid, input) {
    const ref = db.collection("users").doc(uid);
    const allowed = {};
    if (input.name !== undefined)
        allowed.name = input.name;
    if (input.languagePref !== undefined)
        allowed.languagePref = input.languagePref;
    if (input.location !== undefined)
        allowed.location = input.location;
    if (input.isBusiness !== undefined)
        allowed.isBusiness = input.isBusiness;
    if (Object.keys(allowed).length === 0)
        return { updated: false };
    allowed.updatedAt = FieldValue.serverTimestamp();
    await ref.update(allowed);
    logAnalytics("updateUserProfile", uid, { fields: Object.keys(allowed) });
    return { updated: true };
}
exports.updateUserProfile = functions.https.onCall(async (data, context) => {
    const uid = requireAuth(context);
    return ok(await updateUserProfileImpl(uid, data));
});
// ---------- 5. addInfoBit ----------
const INFO_BITS_DAILY_LIMIT_FREE = 5;
async function addInfoBitImpl(uid, input) {
    var _a, _b;
    const { text, tags, location, expiresHours } = input;
    if (!text || !Array.isArray(tags) || tags.length === 0) {
        throw new functions.https.HttpsError("invalid-argument", "Need text and at least one tag neh.");
    }
    const userSnap = await db.collection("users").doc(uid).get();
    const tier = (_b = (_a = userSnap.data()) === null || _a === void 0 ? void 0 : _a.subscriptionTier) !== null && _b !== void 0 ? _b : "free";
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
            throw new functions.https.HttpsError("resource-exhausted", "Eish, free limit is 5 InfoBits per day. Try again tomorrow or upgrade bra.");
        }
    }
    const now = FieldValue.serverTimestamp();
    let expiresAt = null;
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
        location: location !== null && location !== void 0 ? location : null,
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
exports.addInfoBit = functions.https.onCall(async (data, context) => {
    const uid = requireAuth(context);
    return ok(await addInfoBitImpl(uid, data));
});
// ---------- 6. createListing ----------
async function createListingImpl(uid, input) {
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
        priceRange: priceRange !== null && priceRange !== void 0 ? priceRange : null,
        contact: contact !== null && contact !== void 0 ? contact : null,
        tags: normalizedTags,
        verified: false,
        createdAt: now,
    });
    logAnalytics("createListing", uid, { listingId: ref.id, type });
    return { listingId: ref.id };
}
exports.createListing = functions.https.onCall(async (data, context) => {
    const uid = requireAuth(context);
    return ok(await createListingImpl(uid, data));
});
// ---------- 7. searchEverything ----------
async function searchEverythingImpl(uid, input) {
    var _a, _b, _c;
    const limit = Math.min((_a = input.limit) !== null && _a !== void 0 ? _a : 3, 10);
    const location = ((_b = input.location) !== null && _b !== void 0 ? _b : "").toLowerCase();
    const query = ((_c = input.query) !== null && _c !== void 0 ? _c : "").toLowerCase();
    const results = [];
    // Search infoBits: by tags or text substring (Firestore no full-text – we filter in memory for small sets)
    const infoBitsSnap = await db
        .collection("infoBits")
        .orderBy("createdAt", "desc")
        .limit(50)
        .get();
    for (const doc of infoBitsSnap.docs) {
        const d = doc.data();
        if (results.length >= limit)
            break;
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
        if (results.length >= limit)
            break;
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
exports.searchEverything = functions.https.onCall(async (data, context) => {
    const uid = requireAuth(context);
    return ok(await searchEverythingImpl(uid, data));
});
// ---------- 8. startNegotiation ----------
async function startNegotiationImpl(uid, input) {
    const { listingId, infoBitId, userOffer, sellerUid } = input;
    if (!sellerUid) {
        throw new functions.https.HttpsError("invalid-argument", "Need sellerUid.");
    }
    const now = FieldValue.serverTimestamp();
    const ref = await db.collection("deals").add({
        buyerUid: uid,
        sellerUid,
        listingId: listingId !== null && listingId !== void 0 ? listingId : null,
        infoBitId: infoBitId !== null && infoBitId !== void 0 ? infoBitId : null,
        initialOffer: userOffer !== null && userOffer !== void 0 ? userOffer : null,
        status: "open",
        messages: [],
        agreedPriceCents: null,
        createdAt: now,
        updatedAt: now,
    });
    logAnalytics("startNegotiation", uid, { dealId: ref.id, sellerUid });
    return { dealId: ref.id };
}
exports.startNegotiation = functions.https.onCall(async (data, context) => {
    const uid = requireAuth(context);
    return ok(await startNegotiationImpl(uid, data));
});
// ---------- 9. sendNegotiationMessage ----------
async function sendNegotiationMessageImpl(uid, input) {
    const { dealId, message, fromBuyerOrSeller } = input;
    if (!dealId || !message || !fromBuyerOrSeller) {
        throw new functions.https.HttpsError("invalid-argument", "Need dealId, message and fromBuyerOrSeller.");
    }
    const dealRef = db.collection("deals").doc(dealId);
    const dealSnap = await dealRef.get();
    if (!dealSnap.exists) {
        throw new functions.https.HttpsError("not-found", "Deal not found.");
    }
    const d = dealSnap.data();
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
exports.sendNegotiationMessage = functions.https.onCall(async (data, context) => {
    const uid = requireAuth(context);
    return ok(await sendNegotiationMessageImpl(uid, data));
});
// ---------- notifyStokvelNewMember (used via orchestratorCall) ----------
async function notifyStokvelNewMemberImpl(uid, input) {
    const { stokvelId, newMemberWaNumber, newMemberName } = input;
    if (!stokvelId) {
        throw new functions.https.HttpsError("invalid-argument", "stokvelId required.");
    }
    const memberWa = (newMemberWaNumber !== null && newMemberWaNumber !== void 0 ? newMemberWaNumber : uid).trim();
    if (memberWa !== uid) {
        throw new functions.https.HttpsError("permission-denied", "Only the joining member can trigger this.");
    }
    const stokvelSnap = await db.collection("stokvels").doc(stokvelId).get();
    if (!stokvelSnap.exists) {
        throw new functions.https.HttpsError("not-found", "Stokvel not found.");
    }
    const stokvel = stokvelSnap.data();
    const ownerWaNumber = stokvel.ownerWaNumber || "";
    const stokvelName = stokvel.name || "Stokvel";
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
async function createIkhokhaPaymentLinkImpl(uid, input) {
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
        description: description !== null && description !== void 0 ? description : "",
        dealId: dealId !== null && dealId !== void 0 ? dealId : null,
        ikhokhaRef: null,
        createdAt: now,
        updatedAt: now,
    });
    // Stub: real implementation would call Ikhokha API and store returned link/ref
    const baseUrl = process.env.IKHOKHA_BASE_URL || "https://pay.ikhokha.com";
    const paymentLink = `${baseUrl}/pay?ref=qc-${paymentRef.id}&amount=${amountCents}&desc=${encodeURIComponent(description !== null && description !== void 0 ? description : "")}`;
    logAnalytics("createIkhokhaPaymentLink", uid, { paymentId: paymentRef.id, amountCents });
    return { paymentLink, paymentId: paymentRef.id };
}
exports.createIkhokhaPaymentLink = functions.https.onCall(async (data, context) => {
    const uid = requireAuth(context);
    return ok(await createIkhokhaPaymentLinkImpl(uid, data));
});
// ---------- 11. ikhokhaWebhook (onRequest) ----------
exports.ikhokhaWebhook = functions.https.onRequest(async (req, res) => {
    if (req.method !== "POST") {
        res.status(405).send("Method Not Allowed");
        return;
    }
    const secret = process.env.IKHOKHA_WEBHOOK_SECRET || "";
    const sig = req.headers["x-ikhokha-signature"];
    if (secret && (!sig || sig !== secret)) {
        res.status(401).send("Unauthorized");
        return;
    }
    const body = req.body;
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
    const payment = snap.data();
    if (payment.status === "paid") {
        res.status(200).json({ success: true, message: "Already processed" });
        return;
    }
    const payeeWalletRef = db.collection("wallets").doc(payment.payeeUid);
    await db.runTransaction(async (tx) => {
        var _a;
        const walletSnap = await tx.get(payeeWalletRef);
        tx.update(paymentRef, {
            status: "paid",
            ikhokhaRef: (_a = body.ref) !== null && _a !== void 0 ? _a : paymentId,
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
async function getWalletBalanceImpl(uid) {
    var _a;
    const walletSnap = await db.collection("wallets").doc(uid).get();
    const balanceCents = !walletSnap.exists ? 0 : ((_a = walletSnap.data().balanceCents) !== null && _a !== void 0 ? _a : 0);
    const paymentsSnap = await db
        .collection("payments")
        .where("payeeUid", "==", uid)
        .orderBy("createdAt", "desc")
        .limit(10)
        .get();
    const recentTransactions = paymentsSnap.docs.map((doc) => {
        var _a, _b, _c, _d, _e;
        const d = doc.data();
        return {
            amountCents: d.amountCents,
            at: (_e = (_d = (_c = (_b = (_a = d.createdAt) === null || _a === void 0 ? void 0 : _a.toDate) === null || _b === void 0 ? void 0 : _b.call(_a)) === null || _c === void 0 ? void 0 : _c.toISOString) === null || _d === void 0 ? void 0 : _d.call(_c)) !== null && _e !== void 0 ? _e : "",
            type: d.payerUid === uid ? "sent" : "received",
        };
    });
    return { balanceCents, recentTransactions };
}
exports.getWalletBalance = functions.https.onCall(async (_data, context) => {
    const uid = requireAuth(context);
    return ok(await getWalletBalanceImpl(uid));
});
// ---------- 13. addLostAndFound ----------
async function addLostAndFoundImpl(uid, input) {
    const { text, photoUrl, location, type } = input;
    if (!text || !location || !type) {
        throw new functions.https.HttpsError("invalid-argument", "Need text, location and type (lost/found).");
    }
    const ref = await db.collection("lostAndFound").add({
        reporterUid: uid,
        text,
        photoUrl: photoUrl !== null && photoUrl !== void 0 ? photoUrl : null,
        location,
        type: type === "found" ? "found" : "lost",
        createdAt: FieldValue.serverTimestamp(),
    });
    logAnalytics("addLostAndFound", uid, { id: ref.id });
    return { id: ref.id };
}
exports.addLostAndFound = functions.https.onCall(async (data, context) => {
    const uid = requireAuth(context);
    return ok(await addLostAndFoundImpl(uid, data));
});
// ---------- 14. reportContent ----------
async function reportContentImpl(uid, input) {
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
exports.reportContent = functions.https.onCall(async (data, context) => {
    const uid = requireAuth(context);
    return ok(await reportContentImpl(uid, data));
});
// ---------- 15. getCommunityUpdates ----------
async function getCommunityUpdatesImpl(_uid, input) {
    var _a;
    const limit = Math.min((_a = input.limit) !== null && _a !== void 0 ? _a : 10, 20);
    const type = input.type;
    const items = [];
    if (!type || type === "news") {
        const newsSnap = await db.collection("news").orderBy("createdAt", "desc").limit(limit).get();
        newsSnap.docs.forEach((doc) => items.push(Object.assign(Object.assign({}, doc.data()), { id: doc.id, _type: "news" })));
    }
    if (!type || type === "events") {
        const eventsSnap = await db.collection("events").orderBy("startAt", "asc").limit(limit).get();
        eventsSnap.docs.forEach((doc) => items.push(Object.assign(Object.assign({}, doc.data()), { id: doc.id, _type: "event" })));
    }
    if (!type || type === "govInfo") {
        const govSnap = await db.collection("govInfo").orderBy("createdAt", "desc").limit(limit).get();
        govSnap.docs.forEach((doc) => items.push(Object.assign(Object.assign({}, doc.data()), { id: doc.id, _type: "govInfo" })));
    }
    return { items: items.slice(0, limit) };
}
exports.getCommunityUpdates = functions.https.onCall(async (data, context) => {
    const uid = requireAuth(context);
    return ok(await getCommunityUpdatesImpl(uid, data));
});
// ---------- 16. createVerificationSession (Didit.me KYC) ----------
const DIDIT_API_BASE = "https://verification.didit.me/v3";
async function createVerificationSessionImpl(uid, input) {
    var _a;
    const apiKey = process.env.DIDIT_API_KEY;
    const workflowId = (_a = input.workflow_id) !== null && _a !== void 0 ? _a : process.env.DIDIT_WORKFLOW_ID;
    if (!apiKey || !workflowId) {
        throw new functions.https.HttpsError("failed-precondition", "Didit verification not configured (DIDIT_API_KEY, DIDIT_WORKFLOW_ID).");
    }
    const waNumber = input.waNumber || uid;
    const body = { workflow_id: workflowId };
    if (waNumber)
        body.vendor_data = waNumber;
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
    const data = (await res.json());
    const { session_id, session_token, url } = data;
    if (!session_id || !session_token || !url) {
        throw new functions.https.HttpsError("internal", "Didit response missing session_id, session_token or url.");
    }
    await db.collection("users").doc(waNumber).set({
        diditSessionId: session_id,
        diditSessionToken: session_token,
        lastActiveAt: FieldValue.serverTimestamp(),
    }, { merge: true });
    logAnalytics("createVerificationSession", waNumber, { session_id });
    return { url, session_id, session_token };
}
exports.createVerificationSession = functions.https.onCall(async (data, context) => {
    const uid = requireAuth(context);
    const payload = Object.assign(Object.assign({}, data), { waNumber: data.waNumber || uid });
    return ok(await createVerificationSessionImpl(uid, payload));
});
// ---------- 17. checkVerificationResult (Didit.me KYC) ----------
const FACE_MATCH_APPROVED_THRESHOLD = 60;
async function checkVerificationResultImpl(uid, input) {
    var _a, _b, _c, _d;
    const apiKey = process.env.DIDIT_API_KEY;
    if (!apiKey) {
        throw new functions.https.HttpsError("failed-precondition", "Didit verification not configured (DIDIT_API_KEY).");
    }
    const waNumber = input.waNumber || uid;
    const userSnap = await db.collection("users").doc(waNumber).get();
    const diditSessionId = (_a = userSnap.data()) === null || _a === void 0 ? void 0 : _a.diditSessionId;
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
    const decision = (await res.json());
    const idOk = ((_c = (_b = decision.id_verifications) === null || _b === void 0 ? void 0 : _b[0]) === null || _c === void 0 ? void 0 : _c.status) === "Approved";
    const faceMatches = (_d = decision.face_matches) !== null && _d !== void 0 ? _d : [];
    const faceOk = faceMatches.length === 0 ||
        faceMatches.some((f) => f.status === "Approved" || (typeof f.score === "number" && f.score >= FACE_MATCH_APPROVED_THRESHOLD));
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
    }
    else {
        await db.collection("users").doc(waNumber).set({ kycStatus: "failed", lastActiveAt: now }, { merge: true });
        logAnalytics("checkVerificationResult_failed", waNumber, { session_id: diditSessionId });
        return { approved: false, message: "Verification did not pass. You can try again with a new link." };
    }
}
exports.checkVerificationResult = functions.https.onCall(async (data, context) => {
    const uid = requireAuth(context);
    const payload = Object.assign(Object.assign({}, data), { waNumber: data.waNumber || uid });
    return ok(await checkVerificationResultImpl(uid, payload));
});
// ---------- 18. createLoanRequest (lending & borrowing) ----------
async function createLoanRequestImpl(uid, input) {
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
    const allowedBanks = ["capitec", "fnb", "standard_bank", "absa", "other"];
    if (!allowedBanks.includes(bank)) {
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
exports.createLoanRequest = functions.https.onCall(async (data, context) => {
    const uid = requireAuth(context);
    return ok(await createLoanRequestImpl(uid, data));
});
// ---------- 19. getLoanRequestsBatch (masked, for lenders) ----------
function maskDisplayNameTs(displayName) {
    const name = (displayName || "").trim();
    if (!name)
        return "Unknown";
    const parts = name.split(/\s+/);
    const first = parts[0].charAt(0).toUpperCase() + parts[0].slice(1);
    if (parts.length === 1)
        return first;
    const lastInitial = parts[parts.length - 1].charAt(0).toUpperCase();
    return `${first} ${lastInitial}.`;
}
function formatBorrowerReputationTs(b) {
    const score = typeof b.reputationScore === "number" ? b.reputationScore : 0;
    const totalLoans = typeof b.totalLoansTaken === "number" ? b.totalLoansTaken : 0;
    const onTime = typeof b.totalRepaidOnTime === "number" ? b.totalRepaidOnTime : 0;
    const late = typeof b.totalRepaidLate === "number" ? b.totalRepaidLate : 0;
    const def = typeof b.totalDefaulted === "number" ? b.totalDefaulted : 0;
    if (totalLoans <= 0)
        return `${score.toFixed(1)}★ (new borrower)`;
    const parts = [];
    if (onTime)
        parts.push(`${onTime} on time`);
    if (late)
        parts.push(`${late} late`);
    if (def)
        parts.push(`${def} defaulted`);
    const details = parts.length ? parts.join(", ") : "history";
    return `${score.toFixed(1)}★ (${totalLoans} loans, ${details})`;
}
async function getLoanRequestsBatchImpl(uid, input) {
    var _a, _b, _c, _d, _e, _f, _g, _h, _j, _k, _l, _m;
    const lenderUid = uid;
    const limit = Math.min((_a = input.limit) !== null && _a !== void 0 ? _a : 3, 10);
    const pageCursor = input.pageCursor;
    // Already unlocked requests for this lender
    const viewsSnap = await db.collection("lenders").doc(lenderUid).collection("views").get();
    const unlockedIds = new Set();
    viewsSnap.docs.forEach((doc) => {
        var _a;
        const d = doc.data();
        unlockedIds.add((_a = d.loanRequestId) !== null && _a !== void 0 ? _a : doc.id);
    });
    let query = db.collection("loan_requests").where("status", "==", "open").orderBy("createdAt", "desc");
    if (pageCursor) {
        const cursorDoc = await db.collection("loan_requests").doc(pageCursor).get();
        if (cursorDoc.exists) {
            query = query.startAfter(cursorDoc);
        }
    }
    const snap = await query.limit(limit + 1).get();
    const items = [];
    let nextCursor;
    for (const doc of snap.docs) {
        const id = doc.id;
        if (unlockedIds.has(id))
            continue;
        const d = doc.data();
        const borrowerUid = d.borrowerUid;
        const borrowerSnap = borrowerUid ? await db.collection("borrowers").doc(borrowerUid).get() : null;
        const borrower = (_b = borrowerSnap === null || borrowerSnap === void 0 ? void 0 : borrowerSnap.data()) !== null && _b !== void 0 ? _b : {};
        const displayName = borrower.displayName || borrowerUid;
        const maskedName = maskDisplayNameTs(displayName);
        const repSummary = formatBorrowerReputationTs(borrower);
        const repayBy = (_g = (_f = (_e = (_d = (_c = d.repayByDate) === null || _c === void 0 ? void 0 : _c.toDate) === null || _d === void 0 ? void 0 : _d.call(_c)) === null || _e === void 0 ? void 0 : _e.toISOString) === null || _f === void 0 ? void 0 : _f.call(_e)) !== null && _g !== void 0 ? _g : null;
        const createdAtIso = (_m = (_l = (_k = (_j = (_h = d.createdAt) === null || _h === void 0 ? void 0 : _h.toDate) === null || _j === void 0 ? void 0 : _j.call(_h)) === null || _k === void 0 ? void 0 : _k.toISOString) === null || _l === void 0 ? void 0 : _l.call(_k)) !== null && _m !== void 0 ? _m : null;
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
exports.getLoanRequestsBatch = functions.https.onCall(async (data, context) => {
    const uid = requireAuth(context);
    return ok(await getLoanRequestsBatchImpl(uid, data));
});
// ---------- 20. unlockLoanRequests (after Ikhokha payment webhook) ----------
async function unlockLoanRequestsImpl(uid, input) {
    var _a;
    const lenderUid = uid;
    const loanRequestIds = (_a = input.loanRequestIds) !== null && _a !== void 0 ? _a : [];
    if (loanRequestIds.length === 0) {
        throw new functions.https.HttpsError("invalid-argument", "loanRequestIds required.");
    }
    if (loanRequestIds.length > 3) {
        throw new functions.https.HttpsError("invalid-argument", "Can only unlock up to 3 loan requests at a time.");
    }
    // Fee: R5 per request or R10 for batch of 3
    let totalFeeCents;
    if (loanRequestIds.length === 1) {
        totalFeeCents = 500;
    }
    else if (loanRequestIds.length === 3) {
        totalFeeCents = 1000;
    }
    else {
        totalFeeCents = 500 * loanRequestIds.length;
    }
    const perRequestFee = Math.floor(totalFeeCents / loanRequestIds.length);
    const viewsCol = db.collection("lenders").doc(lenderUid).collection("views");
    const now = FieldValue.serverTimestamp();
    const unlocked = [];
    for (const rawId of loanRequestIds) {
        const id = String(rawId || "").trim();
        if (!id)
            continue;
        const reqRef = db.collection("loan_requests").doc(id);
        const reqSnap = await reqRef.get();
        if (!reqSnap.exists)
            continue;
        const d = reqSnap.data();
        if (d.status !== "open")
            continue;
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
exports.unlockLoanRequests = functions.https.onCall(async (data, context) => {
    const uid = requireAuth(context);
    return ok(await unlockLoanRequestsImpl(uid, data));
});
// ---------- 21. uploadProofOfPayment (update loan + loan_request) ----------
async function uploadProofOfPaymentImpl(uid, input) {
    const { loanId, popUrl } = input;
    if (!loanId || !popUrl) {
        throw new functions.https.HttpsError("invalid-argument", "Need loanId and popUrl.");
    }
    const loanRef = db.collection("loans").doc(loanId);
    const loanSnap = await loanRef.get();
    if (!loanSnap.exists) {
        throw new functions.https.HttpsError("not-found", "Loan not found.");
    }
    const loan = loanSnap.data();
    if (loan.lenderUid !== uid) {
        throw new functions.https.HttpsError("permission-denied", "Only the lender can upload proof for this loan.");
    }
    const loanRequestId = loan.loanRequestId;
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
exports.uploadProofOfPayment = functions.https.onCall(async (data, context) => {
    const uid = requireAuth(context);
    return ok(await uploadProofOfPaymentImpl(uid, data));
});
// ---------- Helpers for Komani News import ----------
const KOMANI_NEWS_URL = "https://www.komani.co.za/wp-json/wp/v2/posts?per_page=5";
/** Strip HTML tags and normalize whitespace. */
function stripHtml(html) {
    if (!html || typeof html !== "string")
        return "";
    return html
        .replace(/<\/?[^>]+>/g, " ")
        .replace(/\[&hellip;\]|&hellip;/g, "…")
        .replace(/\s+/g, " ")
        .trim();
}
/** Decode common HTML entities in title/text. */
function decodeEntities(s) {
    if (!s || typeof s !== "string")
        return "";
    return s
        .replace(/&#8217;/g, "'")
        .replace(/&#8216;/g, "'")
        .replace(/&#8220;/g, '"')
        .replace(/&#8221;/g, '"')
        .replace(/&amp;/g, "&")
        .replace(/&lt;/g, "<")
        .replace(/&gt;/g, ">")
        .replace(/&quot;/g, '"');
}
/** Derive tags from WP post: Yoast keywords → articleSection → class_list → default. */
function deriveTagsFromWpPost(post) {
    var _a, _b;
    const graph = (_b = (_a = post.yoast_head_json) === null || _a === void 0 ? void 0 : _a.schema) === null || _b === void 0 ? void 0 : _b["@graph"];
    if (Array.isArray(graph)) {
        const article = graph.find((n) => n["@type"] === "NewsArticle");
        if ((article === null || article === void 0 ? void 0 : article.keywords) && Array.isArray(article.keywords) && article.keywords.length > 0) {
            return article.keywords.map((k) => String(k).toLowerCase().trim()).filter(Boolean);
        }
        const section = article === null || article === void 0 ? void 0 : article.articleSection;
        if (section != null) {
            const arr = Array.isArray(section) ? section : [section];
            const out = arr.map((s) => String(s).toLowerCase().trim()).filter(Boolean);
            if (out.length > 0)
                return out;
        }
    }
    const classList = post.class_list;
    if (Array.isArray(classList)) {
        const seen = new Set();
        for (const c of classList) {
            const s = String(c).trim();
            if (s.startsWith("tag-") || s.startsWith("category-")) {
                const part = s.slice(s.indexOf("-") + 1).replace(/-/g, " ").toLowerCase().trim();
                if (part && !seen.has(part))
                    seen.add(part);
            }
        }
        if (seen.size > 0)
            return Array.from(seen);
    }
    return ["komani-news"];
}
// ---------- Scheduled: importKomaniNews ----------
/** Hourly: fetch Komani News WP API, dedupe by sourceId, write to news collection. */
exports.importKomaniNews = functions.pubsub
    .schedule("0 * * * *")
    .timeZone("Africa/Johannesburg")
    .onRun(async () => {
    var _a, _b, _c, _d;
    try {
        const res = await fetch(KOMANI_NEWS_URL);
        if (!res.ok) {
            console.warn("KASI-ORACLE: importKomaniNews fetch failed", res.status, res.statusText);
            return null;
        }
        const data = await res.json();
        if (!Array.isArray(data)) {
            console.warn("KASI-ORACLE: importKomaniNews response is not an array");
            return null;
        }
        let imported = 0;
        for (const post of data) {
            if (typeof (post === null || post === void 0 ? void 0 : post.id) !== "number" || !post.link)
                continue;
            const existing = await db.collection("news").where("sourceId", "==", post.id).limit(1).get();
            if (!existing.empty)
                continue;
            const titleRaw = (_b = (_a = post.title) === null || _a === void 0 ? void 0 : _a.rendered) !== null && _b !== void 0 ? _b : "";
            const title = decodeEntities(stripHtml(titleRaw)) || "Untitled";
            const excerptRaw = (_d = (_c = post.excerpt) === null || _c === void 0 ? void 0 : _c.rendered) !== null && _d !== void 0 ? _d : "";
            const summaryEn = stripHtml(excerptRaw).slice(0, 300);
            const tags = deriveTagsFromWpPost(post);
            const doc = {
                title,
                link: post.link,
                sourceUrl: post.link,
                summaryEn: summaryEn || null,
                tags,
                authorUid: "komani-import",
                createdAt: admin.firestore.Timestamp.fromDate(new Date(post.date)),
                sourceId: post.id,
            };
            await db.collection("news").add(doc);
            imported++;
        }
        console.log("KASI-ORACLE: importKomaniNews imported", imported);
    }
    catch (err) {
        console.error("KASI-ORACLE: importKomaniNews error", err);
    }
    return null;
});
// ---------- Scheduled: expireOldInfoBits ----------
/** Daily cleanup of expired InfoBits. */
exports.expireOldInfoBits = functions.pubsub.schedule("0 2 * * *").onRun(async () => {
    const now = admin.firestore.Timestamp.now();
    const snap = await db.collection("infoBits").where("expiresAt", "<=", now).limit(200).get();
    const batch = db.batch();
    snap.docs.forEach((doc) => batch.delete(doc.ref));
    if (!snap.empty)
        await batch.commit();
    console.log("KASI-ORACLE: expireOldInfoBits deleted", snap.size);
    return null;
});
/** Daily: set status to "expired" for pending InfoBits and transportFares older than 7 days (no points). */
exports.expirePendingGamificationItems = functions.pubsub.schedule("0 3 * * *").onRun(async () => {
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
    if (!infoBitsSnap.empty || !transportSnap.empty)
        await batch.commit();
    console.log("KASI-ORACLE: expirePendingGamificationItems infoBits=", infoBitsSnap.size, "transportFares=", transportSnap.size);
    return null;
});
// ---------- Triggers ----------
/** On new InfoBit → add to moderation queue for light check (e.g. AI later). */
exports.onInfoBitCreated = functions.firestore.document("infoBits/{id}").onCreate(async (snap) => {
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
exports.onTransportFareUpdated = functions.firestore.document("transportFares/{id}").onUpdate(async (change) => {
    const after = change.after.data();
    await notifyWatchers(change.after.id, after.routeKey, after.priceCents, after.location);
});
//# sourceMappingURL=index.js.map