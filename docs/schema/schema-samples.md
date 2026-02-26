# Queens Connect – Firestore sample documents

One sample per collection for emulator seeding / reference. All camelCase; voice notes = URL only (no blobs).

---

## 1. users

```json
{
  "waNumber": "+27761234567",
  "name": "Sipho",
  "languagePref": "xhosa",
  "createdAt": "<Timestamp>",
  "location": "Top Town, Komani",
  "isBusiness": false,
  "subscriptionTier": "free",
  "walletBalanceCents": 0
}
```

---

## 2. userSessions (subcollection: users/{uid}/userSessions/{sessionId})

```json
{
  "currentState": { "intent": "add_infobit", "collected": { "text": "Taxi to Ezibeleni R40" } },
  "updatedAt": "<Timestamp>"
}
```

---

## 3. listings

```json
{
  "ownerUid": "+27761234567",
  "type": "service",
  "title": "Sipho's DSTV Installations",
  "description": "Professional DSTV install Komani and surrounds.",
  "location": "Komani CBD",
  "priceRange": "R800–R1500",
  "contact": "0761234567",
  "tags": ["dstv", "installation", "whittlesea"],
  "verified": false,
  "createdAt": "<Timestamp>"
}
```

---

## 4. infoBits

```json
{
  "authorUid": "+27761234567",
  "text": "Taxi to Ezibeleni now R45 full",
  "tags": ["taxi", "ezibeleni", "price", "urgent"],
  "location": "Komani CBD",
  "expiresAt": "<Timestamp 4h later>",
  "createdAt": "<Timestamp>",
  "upvotes": 0
}
```

---

## 5. news

```json
{
  "source": "therep",
  "title": "Load shedding stage 2 from 5pm",
  "summaryEn": "Eskom announces stage 2 from 5pm to 10pm.",
  "summaryXh": "I-Eskom ithi isiteji 2 kusukela ngo-5pm.",
  "tags": ["load-shedding", "berg-sig"],
  "url": "https://www.therep.co.za/...",
  "createdAt": "<Timestamp>"
}
```

---

## 6. knowledgeShare

```json
{
  "title": "Ukomosiko (coming of age)",
  "contentEn": "Brief guide to the ceremony and customs.",
  "contentXh": "Isikhokelo esifutshane.",
  "tags": ["culture", "xhosa", "ceremony"],
  "createdAt": "<Timestamp>"
}
```

---

## 7. events

```json
{
  "title": "Stokvel meeting Saturday",
  "description": "Monthly meeting at community hall",
  "startAt": "<Timestamp>",
  "endAt": "<Timestamp>",
  "location": "Ezibeleni Community Hall",
  "createdBy": "+27761234567",
  "tags": ["stokvel", "ezibeleni"],
  "createdAt": "<Timestamp>"
}
```

---

## 8. towns

```json
{
  "name": "Komani",
  "region": "Eastern Cape",
  "createdAt": "<Timestamp>"
}
```

---

## 9. suburbs

```json
{
  "name": "Top Town",
  "townId": "<town doc id>",
  "createdAt": "<Timestamp>"
}
```

---

## 10. govInfo

```json
{
  "title": "Sassa grant dates February",
  "body": "Old age and disability grants paid 3rd.",
  "source": "sassa.gov.za",
  "tags": ["sassa", "grants"],
  "createdAt": "<Timestamp>"
}
```

---

## 11. emergencyNumbers

```json
{
  "name": "Komani SAPS",
  "number": "0458382424",
  "category": "police",
  "createdAt": "<Timestamp>"
}
```

---

## 12. payments

```json
{
  "payerUid": "+27761111111",
  "payeeUid": "+27762222222",
  "amountCents": 5000,
  "status": "pending",
  "dealId": "<deal doc id>",
  "ikhokhaRef": null,
  "createdAt": "<Timestamp>",
  "updatedAt": "<Timestamp>"
}
```

---

## 13. wallets

```json
{
  "ownerUid": "+27761234567",
  "balanceCents": 4500,
  "updatedAt": "<Timestamp>"
}
```

---

## 14. lostAndFound

```json
{
  "reporterUid": "+27761234567",
  "text": "Lost brown wallet near BP garage Cathcart Road",
  "photoUrl": "https://storage.../wallet.jpg",
  "location": "Komani CBD",
  "type": "lost",
  "createdAt": "<Timestamp>"
}
```

---

## 15. complaints

```json
{
  "reporterUid": "+27761234567",
  "itemType": "listing",
  "itemId": "<listing id>",
  "reason": "Scam – never delivered",
  "status": "pending",
  "createdAt": "<Timestamp>"
}
```

---

## 16. communityUpdates

```json
{
  "type": "announcement",
  "title": "Water outage tomorrow",
  "body": "Municipality notice: 9am–2pm.",
  "tags": ["water", "komani"],
  "createdAt": "<Timestamp>"
}
```

---

## 17. transportFares

```json
{
  "authorUid": "+27761234567",
  "routeKey": "komani-east-london",
  "priceCents": 45000,
  "location": "BP Cathcart Road",
  "expiresAt": "<Timestamp 4h>",
  "createdAt": "<Timestamp>"
}
```

---

## 18. transportLocations

```json
{
  "name": "Taxis to East London",
  "description": "Next to BP garage on Cathcart Road",
  "townId": "<town doc id>",
  "createdAt": "<Timestamp>"
}
```

---

## 19. subscriptions

```json
{
  "userUid": "+27761234567",
  "tier": "premium",
  "validUntil": "<Timestamp>",
  "createdAt": "<Timestamp>"
}
```

---

## 20. ratingsAndReviews (subcollection: listings/{listingId}/ratingsAndReviews)

```json
{
  "listingId": "<listing doc id>",
  "reviewerUid": "+27761234567",
  "rating": 5,
  "text": "Sharp service, on time.",
  "createdAt": "<Timestamp>"
}
```

---

## 21. deals

```json
{
  "buyerUid": "+27761111111",
  "sellerUid": "+27762222222",
  "listingId": "<listing id>",
  "infoBitId": null,
  "initialOffer": "R400",
  "status": "open",
  "messages": [
    { "from": "buyer", "text": "R400?", "at": "<Timestamp>" },
    { "from": "seller", "text": "R450 final", "at": "<Timestamp>" }
  ],
  "agreedPriceCents": null,
  "createdAt": "<Timestamp>",
  "updatedAt": "<Timestamp>"
}
```

---

## 22. moderationQueue

```json
{
  "itemType": "infoBit",
  "itemId": "<infoBit id>",
  "reason": "Reported as spam",
  "reporterUid": "+27761234567",
  "status": "pending",
  "createdAt": "<Timestamp>"
}
```

---

## 23. notifications

```json
{
  "targetUid": "+27761234567",
  "title": "Fresh taxi price",
  "body": "Taxis to Joburg now R450 – posted 5 min ago",
  "type": "infobit_match",
  "read": false,
  "createdAt": "<Timestamp>"
}
```

---

## 24. configs (single document: configs/global)

```json
{
  "maintenanceMode": false,
  "infoBitsDailyLimitFree": 5,
  "searchDailyLimitFree": 10,
  "updatedAt": "<Timestamp>"
}
```

---

Replace `<Timestamp>` with a Firestore Timestamp (or ISO string when importing via Admin SDK).
