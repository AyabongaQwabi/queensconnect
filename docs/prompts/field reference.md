The goal is simple: **one source of truth** for field names, types, whether required, and where they live — so the Orchestrator, sub-agents, and Gemini tool calls don't hallucinate wrong property names like `userId` vs `ownerUid`, `price` vs `priceRange`, `content` vs `text`, etc.

# Queens Connect – Canonical Field Reference (API + Schema Alignment)

**Last updated:** Feb 2026  
**Purpose:** Prevent field name drift between agents, prompts, Firebase functions, and database schema.

## 1. Core Collections & Document Structure

### `users` collection

Every user = one WhatsApp number

| Field              | Type      | Required? | Description / Example                           | Notes / Used by             |
| ------------------ | --------- | --------- | ----------------------------------------------- | --------------------------- |
| waNumber           | string    | yes       | "+27761234567"                                  | Primary key / UID           |
| name               | string    | no        | "Sipho" or "Sis'Thembi"                         | Set during onboarding       |
| languagePref       | string    | yes       | "xhosa" \| "english" (default: "xhosa")         | Orchestrator reply language |
| createdAt          | timestamp | yes       |                                                 | Auto-set                    |
| location           | string    | no        | "Ezibeleni", "Top Town", "Whittlesea"           | Last known / mentioned      |
| isBusiness         | boolean   | no        | true if registered as business                  | Controls limits & features  |
| subscriptionTier   | string    | no        | "free" \| "basic" \| "premium" (default "free") | Monetization                |
| walletBalanceCents | number    | no        | 4500 → R45.00                                   | Future P2P wallet           |

### `listings` collection (business profiles, services, recurring sellers)

| Field         | Type      | Required? | Example / Notes                                            | Searchable? | Used by                |
| ------------- | --------- | --------- | ---------------------------------------------------------- | ----------- | ---------------------- |
| id            | string    | auto      | Firestore doc ID                                           | -           | -                      |
| ownerUid      | string    | yes       | waNumber of owner                                          | yes         | Ownership check        |
| type          | string    | yes       | "business" \| "service" \| "product" \| "person"           | yes         | Filtering              |
| title         | string    | yes       | "Sipho's DSTV Installations"                               | yes         | Search ranking         |
| description   | string    | yes       | Full text                                                  | yes         | Matcher                |
| location      | string    | yes       | "Komani CBD", "Ezibeleni"                                  | yes         | Geo-relevance          |
| priceRange    | string    | no        | "R800–R1500" or "R350" or "negotiable"                     | partial     | Display only           |
| contact       | string    | no        | "0761234567" — only for verified businesses                | no          | Revealed after consent |
| tags          | string[]  | yes       | ["dstv", "installation", "whittlesea"] — lowercase English | yes         | Fast matching          |
| verified      | boolean   | no        | true = manual or paid verification                         | boost       | Ranking                |
| priorityUntil | timestamp | no        | Paid users get search boost until this date                | boost       | Ranking                |
| rating        | number    | no        | 4.7 (future)                                               | boost       | Ranking                |
| createdAt     | timestamp | yes       |                                                            | yes         | Recency                |

### `infoBits` collection (short-lived / ephemeral knowledge)

| Field     | Type      | Required? | Example / Notes                                           | TTL?  | Used by          |
| --------- | --------- | --------- | --------------------------------------------------------- | ----- | ---------------- |
| id        | string    | auto      | Firestore doc ID                                          | -     | -                |
| authorUid | string    | yes       | waNumber who posted                                       | -     | Attribution      |
| text      | string    | yes       | "Taxi to Joburg R750 full now"                            | -     | Display + search |
| tags      | string[]  | yes       | ["taxi", "joburg", "price", "urgent"] — lowercase English | -     | Fast matching    |
| location  | string    | no        | Defaults to author's last location                        | -     | Relevance        |
| expiresAt | timestamp | no        | null = permanent, else e.g. 4 hours for taxi prices       | yes   | Auto-cleanup     |
| createdAt | timestamp | yes       |                                                           | -     | Recency sorting  |
| upvotes   | number    | no        | Future community validation                               | boost | Ranking (maybe)  |

### `news` collection (daily broadcast items)

| Field     | Type      | Required? | Notes                                              |
| --------- | --------- | --------- | -------------------------------------------------- |
| id        | string    | auto      | -                                                  |
| source    | string    | yes       | "dailydispatch", "therep", "komani-news", "manual" |
| title     | string    | yes       | Original title                                     |
| summaryEn | string    | yes       | English summary                                    |
| summaryXh | string    | yes       | Xhosa summary (Gemini translation)                 |
| tags      | string[]  | yes       | ["load-shedding", "berg-sig", "funeral"]           |
| url       | string    | no        | Original article link                              |
| createdAt | timestamp | yes       | -                                                  |

## 2. Frequently Used Request Payloads (Firebase Functions)

Make sure agents send **exactly** these field names.

### `addInfoBit(data)`

```js
{
  authorUid:   string,    // waNumber
  text:        string,
  tags:        string[],  // lowercase English
  location:    string,    // optional
  expiresAt:   string | null   // ISO timestamp or null
}
```

### `createListing(data)`

```js
{
  ownerUid:     string,
  type:         string,
  title:        string,
  description:  string,
  location:     string,
  priceRange:   string | null,
  contact:      string | null,
  tags:         string[]
}
```

### `searchListings(params)`

```js
{
  query:        string,     // natural language or keywords
  location:     string,     // optional, defaults to user profile
  tags:         string[],   // optional
  limit:        number,     // usually 3
  userUid:      string      // for personalization / priority boost
}
```

→ Returns array of listing objects (with `id`, `title`, `description`, `location`, `priceRange`, `tags`, `verified`, etc.)

### `startNegotiation(data)`

```js
{
  buyerUid:     string,
  listingId:    string | null,   // or sellerUid
  sellerUid:    string,
  initialOffer: string | null,   // "R400" or "best price?"
  consent:      boolean          // must be true
}
```

## 3. Golden Rules for All Agents

- **Never** invent fields: no `userId`, `content`, `price`, `body`, `msg`, `postText` — stick to the names above.
- Internal tags **always lowercase English** (`taxi`, `dstv`, `puppy` — never "iTaxi" or "DSTV")
- Location strings = free text but prefer known areas: "ezibeleni", "top town", "cbd", "whittlesea", "cofimvaba"
- Money = string with "R" prefix when talking to user: "R450" — store as string in `priceRange`
- Timestamps = ISO 8601 strings or Firestore Timestamp objects (agents usually send strings)

Copy-paste this table into your Orchestrator system prompt:

> You **MUST** use exactly these field names when calling tools or saving data: waNumber, ownerUid, text, tags, location, expiresAt, priceRange, title, description, verified, priorityUntil, etc. Do NOT use synonyms like userId, content, amount, body, post, messageText.
