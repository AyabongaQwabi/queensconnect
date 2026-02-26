You are a senior Firebase Firestore architect who has built 10+ hyper-local WhatsApp community apps in South African townships (low data, Xhosa-first, offline-tolerant).

Project: Queens Connect – WhatsApp Super App for Komani/Queenstown & surrounds (Ezibeleni, Whittlesea, Cofimvaba etc.). One WhatsApp number = local everything: real-time InfoBits (taxi prices, load shedding), safe marketplace (listings), news, events, lost & found, government info, emergency numbers, transport fares. Everything must feel like chatting to a sharp kasi cousin.

Database rules from product docs:

- NoSQL Firestore (not relational)
- WA number = permanent UID
- Heavy use of arrays for tags, maps for flexible fields
- Heavy denormalization for speed (e.g. location string + reference)
- ExpiresAt timestamps for temporary InfoBits & fares
- Realtime listeners everywhere (new taxi price → instant push)
- Security: only authenticated users (phone auth via WA number), owners can only edit own docs, public reads for search, paid users get extra fields

Create the COMPLETE Firestore schema including:

COLLECTIONS (in this exact order):

1. users
2. userSessions (subcollection under users/{uid})
3. listings
4. infoBits
5. news
6. knowledgeShare
7. events
8. towns
9. suburbs (with town reference)
10. govInfo
11. emergencyNumbers
12. payments
13. wallets
14. lostAndFound
15. complaints
16. communityUpdates
17. transportFares
18. transportLocations
19. subscriptions
20. ratingsAndReviews (subcollection under listings/{listingId})
21. deals
22. moderationQueue
23. notifications
24. configs (single document "global")

For EACH collection:

- Purpose (1 sentence)
- All fields with:
  - Type (string, number, boolean, timestamp, array<string>, map, reference)
  - Required? (yes/no)
  - Default value
  - Validation notes (e.g. "tags must be lowercase English only")
  - Example value
- Indexes needed (single + composite, especially for search: tags + location + createdAt desc, expiresAt queries)
- Security rules snippet (allow read/write conditions)

After all collections:

- Full Firestore Security Rules (complete rules object)
- Recommended composite indexes (list with collection + fields)
- 1 sample document JSON per collection
- Any Cloud Function triggers we should set up (e.g. onCreate infoBits → check moderation, onUpdate transportFares → notify watchers)

Style:

- All collection & field names in camelCase
- Comments in the JSON explaining kasi logic
- Make it copy-paste ready for Firebase console + TypeScript types
- Keep data small (no heavy blobs – voice notes stored in Cloud Storage, only URL here)

Output format (use Markdown):

1. Text architecture diagram
2. Collection breakdown (use tables)
3. Security Rules (full code block)
4. Indexes
5. Sample documents
6. Next steps for me (the developer)

Start now. Make it so clean that I can deploy in 30 minutes and the Orchestrator Agent will love it. Sharp!
