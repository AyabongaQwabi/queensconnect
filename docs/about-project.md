**✅ UPDATED README.md** (copy-paste ready)

```markdown
# Queens Connect – Komani/Queenstown WhatsApp Super App

**The living WhatsApp Yellow Pages, price oracle, local news summarizer, lost & found board, community complaint hub, event calendar, taxi & trip planner, cultural knowledge base, and AI-powered connector for Komani (Queenstown) and the entire Eastern Cape kasi.**

One WhatsApp number. Speak in **English or isiXhosa** (voice notes or text).  
The AI automatically translates everything to English so the agents understand perfectly, then replies back in your preferred language.

### What You Can Do Right Now

- Register yourself, your business, service or product for free
- Post live “info bits” (taxi prices, cheap bathtubs, etc.) → AI auto-tags them
- Report **Lost & Found** items
- Report complaints or see community updates
- Save and search local events with dates
- Share & search taxi fares (minibus, lift club, cab) + exact pickup locations
- Ask for weather in Komani or any Eastern Cape town
- Ask about Xhosa traditions and how to perform them
- Search anything local — if it’s not in the database, the AI automatically Google-searches and brings you fresh results

All data is realtime and community-driven.

### Core Features (MVP + Immediate Roadmap)

#### Discovery & Community

- Free listings (business, service, product, person)
- Info Bits (tweet-style short updates with AI tags)
- **Lost & Found** reporting & matching
- Complaints & community reports (with status tracking)
- Community updates feed

#### Events & Culture

- Save & query events (“ stokvel meeting this Saturday”, “traditional ceremony at eRhini”)
- Cultural knowledge base (Xhosa traditions, rituals, how-to guides, proverbs)

#### Transport & Practical Help

- Taxi fares database (minibus, lift clubs, cabs) + pickup locations (“Taxis to East London are next to BP garage on Cathcart Road”)
- AI Trip Planner – “I need to go to Mdantsane for R150 max” → suggests cheapest combo of taxis/lift clubs/cabs + total cost

#### News & External Knowledge

- Daily scraped & summarized news from:
  - https://www.therep.co.za/
  - https://www.komani.co.za/
  - https://www.dailydispatch.co.za/ (RSS)
- Automatic Google fallback search when local DB has no answer

#### Language & Smart Handling

- Full isiXhosa + English support
- Every message is auto-translated to English before agents process it
- Replies sent back in user’s preferred language (remembers your choice)

#### Money-Making Features (Phase 2)

- AI Matcher + Negotiator Agent (connects buyers & sellers, negotiates on your behalf)
- iKhokha payments (P2P, airtime, electricity, vouchers, wallet)

### Tech Stack

- **Interface**: WhatsApp Cloud API (Meta Business) – buttons, lists, voice notes
- **Agents**: Google Agent Development Kit (ADK) – multi-agent Python swarm
  - Translator Agent (Xhosa ↔ English)
  - Orchestrator
  - Registrar, InfoBit Tagger, LostFound Agent, Complaints Agent
  - Event Agent, Taxi & Trip Planner Agent
  - News Scraper, Cultural Knowledge Agent
  - Web Search Fallback Agent
- **Database**: Firebase Firestore (NoSQL realtime) + Firebase Phone Auth (WhatsApp number = login)
- **Payments**: iKhokha iK Pay API
- **Scraping**: Playwright in ADK Browser Tool
- **AI**: Google Gemini (tagging, translation, planning, negotiation)
- **Hosting**: Google Cloud Run + Firebase Cloud Functions

### Database Collections (Firestore)

- `users`
- `listings` (profiles)
- `infoBits`
- `lostFound`
- `complaints`
- `events`
- `taxiFares` + `taxiLocations`
- `culturalKnowledge`
- `news`
- `communityUpdates`

### Architecture
```

WhatsApp Message
↓ (auto-translate to English)
ADK Orchestrator Agent
├── Translator (if needed)
├── Search DB first
├── If not found → Web Search Tool
├── Route to correct specialist agent (LostFound, TaxiPlanner, Event, etc.)
└── Reply in original language

```

### Getting Started (MVP)

1. Firebase project + WhatsApp Business API number + iKhokha account
2. `git clone` this repo
3. Set up environment variables (Firebase, Meta, Gemini, iKhokha)
4. Deploy Cloud Functions + ADK agents to Cloud Run
5. Point WhatsApp webhook to your Firebase function

Full setup guide coming in `SETUP.md`.

### Roadmap (Next 4 Weeks)
**Week 1-2**: Lost & Found, Complaints, Events, Taxi fares + locations, Weather, Translation layer
**Week 3**: Trip Planner Agent + Cultural Knowledge base
**Week 4**: Google fallback search + soft launch in Komani groups

### Legal & Community Rules
- All content moderated lightly by AI + community reports
- POPIA compliant (consent on every registration)
- News is summarized only
- Scraping is respectful and rate-limited

Built for the people, by the people of Komani.
From Randburg with love ❤️

**Xhosa Hip Hop** – Let’s grow this together.

---

```
