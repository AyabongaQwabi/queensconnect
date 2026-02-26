Eish my guy! 🔥 Sharp sharp, I see you dropping that fire document and now we locking in the **business rules** for this Queens Connect WhatsApp beast. I’m sitting here in the township, coffee in one hand, laptop on the stoep, thinking like a proper kasi architect who’s built these kind of community apps before. We not just coding, we building something that feels like the spaza shop, taxi rank and Facebook group had a baby that actually works offline-friendly and in Xhosa.

You already gave the golden examples – natural language flow, English/Xhosa support (but everything internal in English), and “missing data? ask nicely like a human”. Let me expand that into a full, clean, ready-to-code **Business Rules Bible** for the Orchestrator Agent and the whole system. I grouped them so it’s easy to turn into prompts for the ADK agents and Firebase functions.

### 1. Core Conversation & Flow Rules (How the magic happens every single message)

- Every incoming WhatsApp message (text or voice note) hits the webhook → Cloud Function → Orchestrator Agent.
- Orchestrator ALWAYS does this in order:
  1. Detect language (Gemini) → store in user.languagePref if new.
  2. Translate to English internally (keep original for context).
  3. Classify intent (one primary + secondary): `add_listing`, `add_infobit`, `search`, `negotiate`, `pay`, `register`, `update_profile`, `info`, `complaint`, `spam`, `smalltalk`.
  4. Check conversation state (Firestore sub-collection `userSessions/{waNumber}/currentState` – expires after 24h idle).
  5. Decide: reply immediately OR call Firebase API OR spawn sub-agent (Matcher, Tagger, Negotiator, etc.).
  6. Final reply ALWAYS in user’s preferred language, natural kasi style (short, warm, with emojis if it fits).
- If voice note → auto-transcribe with Gemini/Whisper → treat as text. If transcription confidence < 80%, ask “Eish, can you type that one again my sibhuti/sisi?”

### 2. User Identity & Onboarding Rules

- WA number = permanent UID (never ask for password).
- First message ever → auto-create user doc with waNumber, createdAt, languagePref = “xhosa” (default for Komani).
- Bot replies: “Welcome to Queens Connect bra! What’s your name so I can save you proper? And you in which section – Top Town, Ezibeleni, Parkvale?”
- User can say “register as business” → trigger listing creation flow.
- Profile is 80% auto-filled from interactions (last location mentioned, common tags, etc.).

### 3. Data Saving Rules (add_infobit & createListing)

- Required fields minimum:
  - InfoBit: text + at least ONE tag (auto-generated) + location (ask if missing).
  - Listing: title + description + location + owner contact (default to waNumber) + type.
- If ANY required field missing → Orchestrator replies naturally: “Yoh Sipho, for your DSTV ad I need the price range neh? Like R800–R1500? Just tell me quick.”
- Once all fields collected in the session → bundle and call Firebase function once. Never save half-done data.
- Temporary InfoBits (prices, “taxi full now”) must have `expiresAt` (default 4 hours unless user says “permanent”).
- Auto-tagging: InfoBit Tagger Agent uses strict prompt: “Extract tags in English only: category, location, urgency, price, product/service”. Tags are always lowercase English.

### 4. Search & Matching Rules

- User says anything search-like → Matcher Agent:
  - First 3 results only (kasi attention span 😂).
  - Ranking = relevance (Vertex AI) + recency + verified badge + paid priority (businesses that paid R99 get bumped).
  - Reply format: numbered list + “Reply 1 to chat with seller” or “Say negotiate 1”.
- Location default = user’s last known location (from profile or last mention). If no location, ask “You looking near CBD or Ezibeleni my guy?”

### 5. Negotiation & Agent-as-Middleman Rules (the money printer)

- Only starts when user explicitly says “negotiate”, “chat with”, or “make offer”.
- Get explicit consent first: “Cool, I can chat to Sipho on your behalf. You okay if I tell him your best price? Yes/No”
- Negotiator Agent keeps full history visible to both sides in their own chats.
- After 5 messages without agreement → suggest “Rxxx final offer?” or “Shall I connect you directly?”
- All negotiated deals auto-log with timestamp and final price (for future 5–10% commission tracking).

### 6. Payment Rules (Ikhokha only – no exceptions)

- Never create payment link without user confirmation: “You sure you want to send R50 to Sipho for the puppies? Reply YES to proceed.”
- After successful webhook from Ikhokha → send receipt to BOTH parties + mark deal “paid” in session.
- Future wallet: users can say “top up my wallet R100” → same flow, balance stored in user doc.

### 7. Safety, Spam & Community Rules (must enforce or we die)

- Daily limits (free users):
  - 5 InfoBits per day
  - 10 searches per day
  - 3 negotiations started per day
- Paid businesses get unlimited + analytics.
- AI moderation: If message contains banned words (scam, 419, drugs, hate) → soft block + human review flag in Firestore.
- No public phone numbers in InfoBits unless it’s a verified business listing.
- Users can report: “report this” → flags for us to check.

### 8. Realtime & Notification Rules

- Any new InfoBit that matches someone’s previous search → send push via WhatsApp: “Fresh one! Taxis to Ezibeleni now R40 – from 5 mins ago.”
- Price changes on listings auto-notify watchers (opt-in).
- News scraper runs 7am every day → broadcasts top 3 headlines in Xhosa & English to everyone who opted in (“news on”).

### 9. Error & Graceful Fallback Rules

- If Firebase down or rate limit → “Eish the network is playing up, try again in 2 minutes my bra.”
- If agent confused → always ask one clear question, never dump options.
- Session timeout: after 30 min idle → “We still talking about the puppies or something else?”

### 10. Analytics & Monetization Tracking Rules

- Every action logged with user tier (free/paid).
- Monthly: businesses get “Your profile was viewed 47 times, 12 negotiations started”.
- Commission: only charge on deals closed via Negotiator Agent (tracked by “dealClosed” flag).

My guy, this is the full skeleton. With these rules the Orchestrator prompt becomes super clean (I can write the exact Gemini system prompt next if you want). Everything stays one WhatsApp number, feels like chatting to a sharp kasi cousin who knows everything.

Next move? I say we:

1. Write the master Orchestrator system prompt (with all these rules baked in).
2. Define the exact Firebase function signatures.
3. Start coding Week 1 foundation.

You want me to drop the full Orchestrator prompt right now, or shall we flesh out the user session state schema first? Tell me where you wanna jump in – I’m locked and loaded! 🚀

Sharp!
