**🔥 FULL BUILD PLAN: Queens Connect (Komani/Queenstown WhatsApp Super App)**  
Option 1 + Option 7 combined into one beast. Semi-generic, user-driven, self-growing local knowledge + marketplace + payments.

### 1. High-Level Architecture

```
WhatsApp Cloud API (webhook)
    ↓
Firebase Cloud Function (Node.js) → routes message
    ↓
ADK Agent Swarm (Python on Cloud Run or Vertex)
    ├── Registrar Agent
    ├── InfoBit AI Tagger + Saver
    ├── News Scraper Agent (daily)
    ├── Search/Matcher Agent
    ├── Negotiator Agent (paid)
    ├── Payment Agent (Ikhokha)
    └── Orchestrator (decides which agent runs)
    ↓
Firebase Firestore (realtime) + Auth
```

Everything lives in **one WhatsApp number**. Users never leave chat.

### 2. Database Choice → **Firebase (Firestore + Auth)** ✅ (not Supabase)

Why Firebase wins here:

- Perfect NoSQL free-form docs (profiles can have totally different fields)
- Realtime listeners (taxi price changes appear instantly for everyone)
- Phone Auth built-in → WhatsApp number = login (no extra passwords)
- Free tier is huge for MVP (50k users, generous reads/writes)
- Cloud Functions = your secure API (no need for separate Express server)
- Scales to millions, Google ecosystem (ADK + Vertex = natural fit)

Supabase would force more rigid tables — skip it for now.

**Core Collections:**

```js
users: { uid, waNumber, name, languagePref: "xhosa|english", createdAt }

listings (profiles): {
  id,
  ownerUid,
  type: "business" | "service" | "product" | "person",
  title: "Sipho's DSTV Installations",
  description,
  location: "Top Town, Komani",
  priceRange,
  contact: "0761234567",
  tags: ["dstv", "installation"],
  verified: false,
  rating: 4.8,
  createdAt
}

infoBits: {   // the "tweet" collection
  id,
  authorUid,
  text: "Taxi to Ezibeleni now R45 (full)",
  tags: ["taxi", "ezibeleni", "price", "urgent"],
  location: "Komani CBD",
  expiresAt: null,   // for temporary prices
  createdAt,
  upvotes: 12
}

news: {
  id,
  source: "therep" | "komani" | "dailydispatch",
  title,
  summary,
  tags: ["power", "bergSig"],
  url,
  createdAt
}
```

### 3. Backend API (all in Firebase Cloud Functions – Node.js/TS)

You’ll have ~8 secure HTTPS functions:

- `createListing`
- `addInfoBit` (calls Gemini to generate tags)
- `searchListings` (text + tags + location)
- `createIkhokhaPaymentLink`
- `webhookWhatsApp` (entry point for all messages)

ADK agents will call these via simple HTTP tool (you give them the URL + Firebase Auth token).

### 4. ADK Agent Swarm (this is the magic)

You’ll have **one main WhatsApp Orchestrator agent** that decides who does what.

Special agents:

- **InfoBit Tagger Agent** → user sends voice note or text → extracts clean text + auto-tags (location, category, urgency, price) using Gemini prompt in Xhosa/English.
- **News Scraper Agent** → runs every morning:
  - Pulls RSS from Daily Dispatch (they have it!)
  - Browser tool (Playwright/Selenium) for the other two sites
  - Summarizes in Xhosa + English, adds tags, saves to Firestore
- **Matcher + Negotiator Agent** (your money printer) → “find me cheap puppies” → returns 3 options + starts AI chat with seller on your behalf (with permission).

### 5. Scraping Setup (exactly as you wanted)

- Use the official YouTube tutorial: “Build a Browser Use Agent with ADK and Selenium” (it exists, made for exactly this).
- Or even better: Use Playwright in a custom ADK function tool (more reliable in 2026).
- Sites are scrape-friendly (no Cloudflare, standard HTML).
- Daily Dispatch RSS = zero scraping needed for regional news.
- Run as scheduled task via Cloud Scheduler → Cloud Function → ADK agent.

### 6. WhatsApp Bot (Meta Cloud API – free tier)

- Get WhatsApp Business number via Meta Business Manager (takes 1-3 days).
- Webhook → Firebase Cloud Function → ADK.
- Full Xhosa support (Gemini handles it).
- Login flow: User messages “register” → bot sends interactive buttons → Firebase Phone Auth (or just trust WA number as ID).

### 7. Payments – Ikhokha (perfect choice)

- Sign up at signup.ikhokha.com → get API keys.
- Use “Create Payment Link” endpoint (official examples on GitHub in Node.js).
- In bot: User says “send R50 to Sipho” → Payment Agent creates link → bot sends clickable link.
- Webhook from Ikhokha → mark transaction done + credit wallet.
- Later add P2P wallet balance in Firestore.

### 8. Monetization (free discovery → paid matching)

- Free forever: Anyone can search & be found.
- Paid (R99–R499/month per business):
  - Priority in search results
  - Negotiator Agent works for them (AI replies to customers 24/7)
  - “Verified” badge + analytics (who viewed their profile)
- 5–10% cut on successful negotiated deals (tracked via bot).

### 9. Step-by-Step Build Roadmap (realistic)

**Week 1 – Foundation**

1. Create Firebase project + enable Auth (Phone), Firestore, Functions.
2. Set up WhatsApp Cloud API + webhook to Cloud Function (hello world bot).
3. Build basic `createListing` & `addInfoBit` functions.

**Week 2 – Core Agents** 4. Deploy simple ADK agent that replies via WhatsApp. 5. Add InfoBit Tagger (Gemini prompt engineering for tags). 6. Build News Scraper Agent (start with RSS, then browser).

**Week 3 – Magic** 7. Matcher + Negotiator Agent. 8. Ikhokha Payment Agent. 9. Simple web page (Next.js optional) for desktop adding of listings.

**Week 4 – Polish & Launch** 10. Xhosa voice notes (Gemini Live or Whisper). 11. Deploy ADK on Cloud Run. 12. Soft launch in Komani Facebook groups.

Total realistic time for MVP: **3–4 weeks** if you code every day.

### 10. Quick Start Commands (copy-paste ready)

```bash
# Firebase
firebase init functions --typescript
firebase deploy --only functions

# ADK (after pip install google-adk)
adk new my-kasi-oracle
adk add tool http  # for calling your Firebase functions
```
