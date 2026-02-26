You are a senior Firebase Cloud Functions architect who has built 8+ WhatsApp township apps in South Africa (Xhosa-first, low-data, Ikhokha payments, ADK agent integration).

Project: Queens Connect – one WhatsApp number super app for Komani/Queenstown.

Requirements:

- Use Firebase Admin SDK + TypeScript
- All functions in one index.ts (or split if you want, but keep simple)
- Use the exact Firestore schema we created yesterday (users, listings, infoBits, etc. – assume collections exist)
- Every callable function must be wrapped with onCall + auth check
- webhookWhatsApp and ikhokhaWebhook are onRequest with proper secret validation
- All replies to agents must be JSON: { success: boolean, data?: any, error?: string }
- Natural error handling with kasi-friendly messages
- Rate limiting: free users 5 infoBits/day, etc. (check user tier)
- Use Firebase Auth uid = waNumber (string)
- Import necessary: admin, functions, firestore, etc.
- Add JSDoc comments on every function explaining kasi use case

All functions live in **Firebase Cloud Functions (TypeScript)** – one single `functions/` folder.  
Security: Every callable function uses Firebase Auth (WA number = uid).  
Webhook functions are public but have secret token validation.

| Function Name              | Type                  | Purpose (kasi style)                                    | Called By                | Key Input Params                        | Main Output / Side Effects                                |
| -------------------------- | --------------------- | ------------------------------------------------------- | ------------------------ | --------------------------------------- | --------------------------------------------------------- |
| `webhookWhatsApp`          | onRequest (POST)      | The front door – every WhatsApp message lands here      | Meta WhatsApp Cloud API  | body (WhatsApp payload)                 | Routes to Orchestrator or replies directly                |
| `orchestratorCall`         | callable              | Main brain – agents call this when they need DB action  | ADK Orchestrator Agent   | action + payload                        | Runs the right logic, returns result                      |
| `createUserIfNotExists`    | callable              | Auto on first message                                   | Orchestrator             | waNumber, name, location                | Creates user doc + default wallet                         |
| `updateUserProfile`        | callable              | Change name, languagePref, location, business flag      | Orchestrator             | fields to update                        | Updates user doc                                          |
| `addInfoBit`               | callable              | Post taxi price, load shedding, “puppies for sale” etc. | Orchestrator / Tagger    | text, tags[], location, expiresHours?   | Saves to infoBits + triggers notifications                |
| `createListing`            | callable              | DSTV guy, spaza, car wash, second-hand fridge           | Orchestrator             | title, desc, priceRange, tags, location | Saves to listings + creates subscription slot if business |
| `searchEverything`         | callable              | “cheap puppies Ezibeleni”, “taxi to Joburg price”       | Matcher Agent            | query, location?, limit=3, filters?     | Returns mixed results (infoBits + listings) ranked        |
| `startNegotiation`         | callable              | User says “negotiate 2”                                 | Orchestrator             | listingId or infoBitId, userOffer       | Creates deal doc + gives permission to Negotiator Agent   |
| `sendNegotiationMessage`   | callable              | Middleman chat – AI talks to seller on buyer’s behalf   | Negotiator Agent         | dealId, message, fromBuyerOrSeller      | Saves message + notifies other party                      |
| `createIkhokhaPaymentLink` | callable              | “Send R150 to Sipho for the fridge”                     | Payment Agent            | amount, payeeUid, description, dealId?  | Returns clickable payment link                            |
| `ikhokhaWebhook`           | onRequest (POST)      | Ikhokha tells us money landed                           | Ikhokha                  | transaction payload + secret            | Marks payment paid, credits wallet, notifies both         |
| `getWalletBalance`         | callable              | Check my money                                          | Orchestrator             | -                                       | Returns balance + recent transactions                     |
| `addLostAndFound`          | callable              | “Lost brown wallet Top Town”                            | Orchestrator             | text, photoUrl?, location               | Saves to lostAndFound                                     |
| `reportContent`            | callable              | “This guy is scamming”                                  | Orchestrator             | itemType, itemId, reason                | Adds to moderationQueue + soft hides                      |
| `getCommunityUpdates`      | callable              | News, events, govInfo                                   | Orchestrator             | type?, limit                            | Returns fresh stuff                                       |
| `adminBroadcast`           | callable (admin only) | We send load-shedding alert to everyone                 | Us (via dashboard later) | message, targetTags?                    | Creates notifications + sends WhatsApp                    |

**Extra helper functions (internal):**

- `logAnalytics` – every action
- `expireOldInfoBits` – scheduled daily
- `notifyWatchers` – realtime price changes

All functions return `{ success: true, data?, error? }` – clean for agents.

Create the FULL backend code starting with these exact functions (in this order):

1. webhookWhatsApp (onRequest)
2. orchestratorCall (onCall)
3. createUserIfNotExists (onCall)
4. updateUserProfile (onCall)
5. addInfoBit (onCall)
6. createListing (onCall)
7. searchEverything (onCall)
8. startNegotiation (onCall)
9. sendNegotiationMessage (onCall)
10. createIkhokhaPaymentLink (onCall)
11. ikhokhaWebhook (onRequest)
12. getWalletBalance (onCall)
13. addLostAndFound (onCall)
14. reportContent (onCall)
15. getCommunityUpdates (onCall)

For each function:

- Full implementation with security checks
- Input validation (zod or simple if statements)
- Firestore transactions where needed (e.g. payment + wallet)
- Trigger realtime notifications via FCM or direct WhatsApp API call (use admin.messaging() or call WhatsApp API helper)
- Logging with console.log("KASI-ORACLE: ...")

After all functions:

- Full package.json dependencies
- .firebaserc example
- firebase.json for functions
- TypeScript interfaces for all inputs/outputs
- Security Rules reminder (link to previous schema)
- Deployment commands
- How the ADK Orchestrator should call these (example HTTP tool calls)

Style: Clean, heavily commented, kasi spirit in comments (“// This one makes Sis’Thembi happy 😂”), production ready, no placeholders.

Output everything in one big Markdown with code blocks. Make it so I can copy the whole functions folder and deploy in 15 minutes.

Start now bra! Make this backend sharper than a new Okapi knife! 🚀
