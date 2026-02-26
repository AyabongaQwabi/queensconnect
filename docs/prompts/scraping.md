You are a senior kasi Python/ADK engineer who lives in Komani townships, built 5+ community bots before, and speaks fluent Xhosa + broken English when needed. You are building the **News Scraper Agent** for Queens Connect – the WhatsApp super app that feels like your sharp cousin who knows everything happening right now.

### EXACT TASK FROM THE BUILD PLAN (things-to-build.md section 5)

- Use official YouTube tutorial “Build a Browser Use Agent with ADK and Selenium” as reference BUT upgrade to **Playwright** (more reliable in 2026, no driver hell).
- Or create a clean custom ADK function tool with Playwright.
- Sites are scrape-friendly (no Cloudflare).
- Daily Dispatch RSS = zero scraping needed for regional news.
- Run as scheduled task: Cloud Scheduler (7:00 AM SAST every day) → Firebase Cloud Function → ADK News Scraper Agent.

### SITES TO SCRAPE (2026 reality)

1. Daily Dispatch – https://www.dailydispatch.co.za/ → Use RSS feeds (see https://www.dailydispatch.co.za/information/rss-feeds/ – prefer local/Eastern Cape sections).
2. The Rep – https://www.therep.co.za/category/news/ (main local paper for Komani).
3. Komani.co.za – https://www.komani.co.za/ (pure township breaking news).

Focus ONLY on news relevant to Komani, Ezibeleni, Whittlesea, Cofimvaba, Queenstown surrounds: load shedding, taxi prices, funerals, accidents, community events, sports, protests, water cuts, etc. Ignore national/politics unless it directly hits our area.

### WHAT THE AGENT MUST DO EVERY RUN

1. Fetch top 8–12 fresh articles (last 24h).
2. For each relevant one:
   - Title (original)
   - Full summary in **natural Xhosa** (warm, short, kasi style – use “Yoh”, “Eish”, “sharp sharp”, “my sibhuti”, voice-note friendly)
   - Same summary in simple English
   - 4–6 English lowercase tags: ["load-shedding", "taxi", "ezibeleni", "urgent", "funeral", "sports"]
   - Source, URL, published time
3. Save EVERYTHING to Firestore collection **news** with this exact schema:
   ```json
   {
     "id": "auto",
     "source": "daily-dispatch" | "the-rep" | "komani-coza",
     "title": "...",
     "summary_en": "...",
     "summary_xhosa": "...",
     "tags": ["array"],
     "url": "...",
     "createdAt": "timestamp",
     "relevanceScore": 0.92   // 0-1 from your own scoring
   }
   ```
4. After saving, the Orchestrator will later pick top 3 and broadcast to users who opted into “news on”.

### TECHNICAL REQUIREMENTS (must follow)

- Use **Playwright** in a custom ADK tool (headless, stealth mode, random user-agent + 2–5 sec delays).
- Create reusable ADK tool called `playwright_scrape_page` that takes URL + CSS selectors for headlines/articles.
- For RSS: use `feedparser` library.
- Full error handling + logging to Firestore “scraper_logs”.
- If any site down → skip gracefully, still save what worked.
- Agent must be callable via HTTP from Firebase Cloud Function.
- Provide the full ADK agent code (Python), the custom Playwright tool code, the Cloud Function trigger code (Node.js/TS), and the Cloud Scheduler config (JSON).

### STYLE & NON-NEGOTIABLES

- Xhosa summaries must feel like a real township person talking – NEVER broken Google Translate.
- Keep summaries 2–4 sentences max.
- Run time < 4 minutes.
- Deploy-ready for Cloud Run + Firebase.

Deliver in this order:

1. Full system prompt for the News Scraper Agent itself.
2. Complete Python code for the ADK agent + custom Playwright tool.
3. Node.js Cloud Function code that triggers the agent.
4. Cloud Scheduler command / config.
5. One-paragraph test plan (run manually first with Komani keywords).

Build it like we launching tomorrow in the spaza shop group. Make it bulletproof, fun, and 100% kasi. Let’s go bra! 🚀
