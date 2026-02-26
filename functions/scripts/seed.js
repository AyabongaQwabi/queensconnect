/**
 * Queens Connect – EXTRA SEED SCRIPT (seed-more.js)
 * Drops 10+ of everything you asked for + long cultural & complaint data
 * Run after original seed.js
 * Usage: cd functions && node scripts/seed.js   (uses emulator by default)
 *        cd functions && npm run seed:emulator  (same)
 * For production: unset FIRESTORE_EMULATOR_HOST and set GOOGLE_APPLICATION_CREDENTIALS.
 */
// Use Firestore emulator by default so we don't need production credentials.
if (!process.env.FIRESTORE_EMULATOR_HOST) {
  process.env.FIRESTORE_EMULATOR_HOST = '127.0.0.1:8086';
}

const admin = require('firebase-admin');
const path = require('path');

const PROJECT_ID = 'queens-connect-2c94d';

function ts(date) {
  return admin.firestore.Timestamp.fromDate(
    date instanceof Date ? date : new Date(date),
  );
}

function now() {
  return admin.firestore.Timestamp.now();
}

async function main() {
  if (!admin.apps.length) {
    admin.initializeApp({ projectId: PROJECT_ID });
  }
  const db = admin.firestore();

  const emulator = 'http://127.0.0.1:5002/queens-connect-2c94d/us-central1';
  console.log(
    emulator
      ? `🌍 Seeding emulator at ${emulator}`
      : `🚀 Seeding production ${PROJECT_ID}`,
  );

  const base = now();
  const in4h = new Date(base.toDate());
  in4h.setHours(in4h.getHours() + 4);
  const in4hTs = ts(in4h);

  try {
    // === USERS (4 real kasi hustlers) ===
    const userData = [
      { wa: '+27761234567', name: 'Sipho', loc: 'Top Town, Komani' },
      { wa: '+27762345678', name: 'Nomsa', loc: 'Ezibeleni' },
      { wa: '+27763456789', name: 'Lungile', loc: 'Whittlesea' },
      { wa: '+27764567890', name: 'Thabo', loc: 'Parkvale, Komani' },
    ];

    for (const u of userData) {
      await db
        .collection('users')
        .doc(u.wa)
        .set({
          waNumber: u.wa,
          name: u.name,
          languagePref: 'xhosa',
          createdAt: now(),
          location: u.loc,
          isBusiness: Math.random() > 0.5,
          subscriptionTier: 'free',
          walletBalanceCents: 0,
        });
      await db
        .collection('wallets')
        .doc(u.wa)
        .set({
          ownerUid: u.wa,
          balanceCents: Math.floor(Math.random() * 12000),
          updatedAt: now(),
        });
    }
    console.log('  ✅ 4 extra users + wallets');

    // === TOWNS (3 more) ===
    const extraTowns = ['Whittlesea', 'Cofimvaba', 'Lady Frere'];
    const townRefs = [];
    for (const name of extraTowns) {
      const ref = await db
        .collection('towns')
        .add({ name, region: 'Eastern Cape', createdAt: now() });
      townRefs.push(ref);
    }
    console.log('  ✅ 3 extra towns');

    // === SUBURBS (10 fresh ones) ===
    const suburbNames = [
      'Ezibeleni',
      'Mlungisi',
      'Parkvale',
      'Tantyi',
      'Ilinge',
      'Leslie',
      'New Rest',
      'Zingodla',
      'Hlala',
      'Balfour',
    ];
    for (let i = 0; i < 10; i++) {
      await db.collection('suburbs').add({
        name: suburbNames[i],
        townId: townRefs[i % townRefs.length].id,
        createdAt: now(),
      });
    }
    console.log('  ✅ 10 suburbs');

    // === LISTINGS (10 fire ones) ===
    const listingData = [
      {
        owner: userData[1].wa,
        type: 'service',
        title: "Nomsa's Hair Braiding",
        desc: 'Best braids, weaves, dreads & relaxers in Ezibeleni. Walk-ins welcome. Open 7 days.',
        loc: 'Ezibeleni',
        price: 'R150–R650',
        tags: ['hair', 'braids', 'ezibeleni'],
      },
      {
        owner: userData[0].wa,
        type: 'product',
        title: 'Pure Boerboel Puppies',
        desc: '5 strong healthy puppies, vaccinated, dewormed, ready for new homes. Parents on site.',
        loc: 'Top Town',
        price: 'R3800 each',
        tags: ['puppies', 'boerboel', 'dogs'],
      },
      {
        owner: userData[2].wa,
        type: 'service',
        title: 'Thabo Car Wash & Detailing',
        desc: 'Full wash, polish, interior clean. R80 basic, R250 full detail. Next to BP.',
        loc: 'Whittlesea',
        price: 'R80–R250',
        tags: ['carwash', 'detailing'],
      },
      {
        owner: userData[3].wa,
        type: 'service',
        title: 'Lungile Plumbing & Leak Fixes',
        desc: 'Geyser, toilet, tap leaks fixed same day. 24/7 emergency.',
        loc: 'Parkvale',
        price: 'R350–R1200',
        tags: ['plumbing', 'leaks'],
      },
      {
        owner: userData[0].wa,
        type: 'product',
        title: 'Second-hand Hisense Fridge',
        desc: 'Working perfectly, 300L, white, collection only.',
        loc: 'Komani CBD',
        price: 'R2200 negotiable',
        tags: ['fridge', 'appliances'],
      },
      {
        owner: userData[1].wa,
        type: 'service',
        title: 'DSTV & Satellite Installations',
        desc: 'New installs, repairs, extra points. 1-year guarantee.',
        loc: 'Komani & surrounds',
        price: 'R850–R1600',
        tags: ['dstv', 'installation'],
      },
      {
        owner: userData[2].wa,
        type: 'product',
        title: 'Fresh Farm Veggies & Eggs',
        desc: 'Spinach, cabbage, mealies, free-range eggs. Daily from farm.',
        loc: 'Whittlesea',
        price: 'R25–R80',
        tags: ['veggies', 'farm', 'eggs'],
      },
      {
        owner: userData[3].wa,
        type: 'service',
        title: 'Phone Repairs & Unlocking',
        desc: 'Screen, battery, software. iPhone & Android. 30 min fixes.',
        loc: 'Parkvale',
        price: 'R150–R950',
        tags: ['phone', 'repair'],
      },
      {
        owner: userData[0].wa,
        type: 'product',
        title: 'Ladies Winter Coats & Jeans',
        desc: 'Brand new stock from Joburg, sizes 30–42.',
        loc: 'Top Town',
        price: 'R180–R450',
        tags: ['clothes', 'winter'],
      },
      {
        owner: userData[1].wa,
        type: 'service',
        title: 'House & Office Cleaning',
        desc: 'Deep clean, after-party, move-in. R450 half day.',
        loc: 'Ezibeleni & Komani',
        price: 'R450–R1200',
        tags: ['cleaning', 'house'],
      },
    ];

    const listingRefs = [];
    for (const l of listingData) {
      const ref = await db.collection('listings').add({
        ownerUid: l.owner,
        type: l.type,
        title: l.title,
        description: l.desc,
        location: l.loc,
        priceRange: l.price,
        contact: l.owner.slice(-9),
        tags: l.tags,
        verified: Math.random() > 0.6,
        createdAt: now(),
      });
      listingRefs.push(ref);
    }
    console.log('  ✅ 10 listings');

    // === INFOBITS (10 hot ones) ===
    const infoBitData = [
      {
        text: 'Taxis to East London full, next one 25 min R130',
        tags: ['taxi', 'east-london', 'urgent'],
        loc: 'Komani rank',
        expires: 4,
      },
      {
        text: 'Shoprite special: 5kg chicken R189 this week only!',
        tags: ['special', 'chicken', 'shoprite'],
        loc: 'Komani CBD',
      },
      {
        text: 'Load shedding stage 2 from 4pm–10pm tonight',
        tags: ['loadshedding', 'eskom'],
        loc: 'Komani',
        expires: 6,
      },
      {
        text: 'Cheap 2nd hand iPhone 11 at the rank R3200',
        tags: ['iphone', 'secondhand', 'rank'],
        loc: 'Ezibeleni',
      },
      {
        text: 'Rain expected 40mm tomorrow – farmers happy!',
        tags: ['weather', 'rain'],
        loc: 'Whittlesea',
      },
      {
        text: 'BP garage has 93 petrol again after shortage',
        tags: ['petrol', 'bp'],
        loc: 'Cathcart Road',
      },
      {
        text: 'Stokvel meeting moved to Friday 6pm community hall',
        tags: ['stokvel', 'ezibeleni'],
        loc: 'Ezibeleni',
      },
      {
        text: 'Lost dog found – brown boerboel, answers to Max',
        tags: ['dog', 'found'],
        loc: 'Top Town',
      },
      {
        text: 'Sassa grants paid early this month – check your card',
        tags: ['sassa', 'grants'],
        loc: 'Komani',
      },
      {
        text: 'Fresh mealies R15 each at roadside near Whittlesea',
        tags: ['mealies', 'farm'],
        loc: 'Whittlesea',
      },
    ];

    const infoBitRefs = [];
    for (const ib of infoBitData) {
      const ref = await db.collection('infoBits').add({
        authorUid: userData[Math.floor(Math.random() * userData.length)].wa,
        text: ib.text,
        tags: ib.tags,
        location: ib.loc,
        expiresAt: ib.expires
          ? ts(new Date(Date.now() + ib.expires * 60 * 60 * 1000))
          : null,
        createdAt: now(),
        upvotes: Math.floor(Math.random() * 25),
      });
      infoBitRefs.push(ref);
    }
    console.log('  ✅ 10 infoBits');

    // === NEWS (10 proper local stories) ===
    const newsData = [
      {
        title: 'N6 roadworks between Komani and East London start Monday',
        summaryEn: 'Construction will last 21 days. Use R63 alternative.',
        summaryXh: 'Umsebenzi wendlela uza kuqala ngoMsombuluko.',
      },
      {
        title: 'Komani SAPS arrest 3 for house breaking in Parkvale',
        summaryEn: 'Suspects aged 19-24. Community applauded quick response.',
        summaryXh: 'Amapolisa abambe abantu abathathu.',
      },
      {
        title: 'Whittlesea High School reopens with new library',
        summaryEn: 'Funded by local business donations. Big win for learners.',
        summaryXh: 'Isikolo saseWhittlesea sivule kwakhona.',
      },
      {
        title: 'Water outage in Ezibeleni tomorrow 8am-4pm',
        summaryEn: 'Municipality doing urgent pipe repairs.',
        summaryXh: 'Amanzi aya kucima e-Ezibeleni kusasa.',
      },
      {
        title: 'Komani Cultural Festival this weekend at Victoria Park',
        summaryEn: 'Traditional dance, food, music. Entry R20.',
        summaryXh: 'Umnyhadala wenkcubeko eKomani.',
      },
      {
        title: 'Eskom warns of possible stage 3 this Friday',
        summaryEn: 'Due to maintenance at Komani substation.',
        summaryXh: 'I-Eskom ixwayisa ngesiteji 3.',
      },
      {
        title: 'Lost & Found: 14 goats recovered near Cofimvaba',
        summaryEn: 'Owner identified, animals returned safely.',
        summaryXh: 'Iimpahla ezilahlekileyo zibuyisiwe.',
      },
      {
        title: 'New spaza shop opens in Mlungisi – fresh bread daily',
        summaryEn: 'Owned by local auntie. Support black business!',
        summaryXh: 'Ispaza entsha ivuliwe.',
      },
      {
        title: 'Traffic lights at Cathcart & Queen streets fixed',
        summaryEn: 'After 3 weeks of chaos, finally working.',
        summaryXh: 'Amalambu okukhanya alungisiwe.',
      },
      {
        title: 'SASSA office Komani to close early Friday for audit',
        summaryEn: 'Grants will still be paid, office reopens Monday.',
        summaryXh: 'Iofisi yeSASSA ivala ngoLwesihlanu.',
      },
    ];

    for (const n of newsData) {
      await db.collection('news').add({
        source: 'therep,dd,local',
        title: n.title,
        summaryEn: n.summaryEn,
        summaryXh: n.summaryXh,
        tags: ['local', 'komani'],
        url: 'https://example.com/news',
        createdAt: now(),
      });
    }
    console.log('  ✅ 10 news');

    // === LOST & FOUND (10) ===
    const lfData = [
      {
        text: 'Lost black Huawei phone with blue cover at BP garage',
        photo: 'https://picsum.photos/id/20/300/200',
        loc: 'Komani CBD',
        type: 'lost',
      },
      {
        text: 'Found: Brown school bag with books near taxi rank',
        photo: 'https://picsum.photos/id/64/300/200',
        loc: 'Ezibeleni',
        type: 'found',
      },
      {
        text: 'Lost brown wallet with ID and R340 cash',
        photo: 'https://picsum.photos/id/101/300/200',
        loc: 'Top Town',
        type: 'lost',
      },
      {
        text: 'Found: White & brown Jack Russell dog, answers to Rocky',
        photo: 'https://picsum.photos/id/201/300/200',
        loc: 'Whittlesea',
        type: 'found',
      },
      {
        text: 'Lost gold chain with cross pendant at Shoprite',
        photo: 'https://picsum.photos/id/180/300/200',
        loc: 'Komani',
        type: 'lost',
      },
    ];
    for (let i = 0; i < 10; i++) {
      const item = lfData[i % lfData.length];
      await db.collection('lostAndFound').add({
        reporterUid: userData[Math.floor(Math.random() * userData.length)].wa,
        text: item.text + (i > 4 ? ` (reported ${i - 4} days ago)` : ''),
        photoUrl: item.photo,
        location: item.loc,
        type: item.type,
        createdAt: now(),
      });
    }
    console.log('  ✅ 10 lostAndFound');

    // === KNOWLEDGESHARE (5 LONG cultural gems) ===
    const ksData = [
      {
        title: 'Ulwaluko – The Sacred Xhosa Initiation',
        contentEn:
          'Ulwaluko is the traditional rite of passage that transforms Xhosa boys into responsible men. It involves a period of seclusion in the bush where initiates (abakhwetha) learn about culture, respect, responsibility, and the importance of community. The ceremony is guided by elders and includes teachings on manhood, marriage, and protecting the family. It is a deeply respected practice that strengthens family bonds and cultural identity in the Eastern Cape. Families prepare for months and the whole community celebrates when the initiates return as men.',
        contentXh:
          'I-Ulwaluko yinkqubo yesiko yamaXhosa eguqula amakhwenkwe abe ngamadoda anoxanduva. Ibandakanya ukuhlala ehlathini apho abakhwetha bafunda isiko, uhlonipho, uxanduva nokukhusela usapho. Umkhosi ukhokelwa ngabantu abadala kwaye wonke umphakathi uyawubhiyozela xa abakhwetha bebuya njengamadoda.',
      },
      {
        title: 'Umemulo – Celebrating a Xhosa Girl Becoming a Woman',
        contentEn:
          'Umemulo is the beautiful coming-of-age ceremony for Xhosa girls, usually held when she turns 21. The family slaughters a cow, the girl wears traditional beadwork and performs dances in front of the community. It is a proud moment where she is celebrated as a responsible young woman ready for adulthood. Gifts, speeches, and feasting go on all day and night.',
        contentXh:
          'Umemulo ngumkhosi omhle wokuba intombi ibe ngumfazi omdala. Umndeni unqaba inkomo, intombi inxiba imihomba yesintu kwaye idanise phambi koluntu. Yinto ebonisa ukuba sele elungele ukuba ngumfazi.',
      },
      {
        title: 'How to Cook Perfect Umqusho (Samp & Beans)',
        contentEn:
          'Umqusho is the ultimate comfort food in every kasi household. Soak samp and beans overnight. Boil with a smoked pork bone or chicken feet for 3 hours until soft. Add salt, Aromat, and a spoon of sugar at the end. Serve with fried cabbage or chakalaka. This dish brings families together – perfect for Sunday lunch or after a long taxi ride home.',
        contentXh:
          'Umqusho ngokutya okumnandi kakhulu kwindlu yonke. Vutha isamp neembotyi ubusuku bonke. Bilisa nebhanti yenyama yehagu okanye iinyawo zenkukhu iiyure ezi-3. Yongeza ityuwa, i-Aromat kunye ne spoon yeswekile ekugqibeleni.',
      },
      {
        title: 'Xhosa Traditional Wedding Customs',
        contentEn:
          'A Xhosa wedding (umtshato) is a multi-day celebration. It starts with lobola negotiations, then the bride’s family welcomes the groom with songs and dances. The bride wears a long white dress and traditional beads. Families exchange gifts, slaughter animals, and the couple is blessed by elders. Music, ululation and laughter fill the air for days.',
        contentXh:
          'Umtshato wamaXhosa ngumkhosi weentsuku ezininzi. Uqala nge-lobola, emva koko usapho lomakoti lwamkele umyeni ngeengoma nokudanisa.',
      },
      {
        title: 'The History of Komani (Queenstown)',
        contentEn:
          'Komani, also known as Queenstown, was founded in 1853 as a military outpost. Named after Queen Victoria, it became a thriving farming and trading town. Today it is the heart of the Eastern Cape with strong Xhosa culture, beautiful mountains, and a vibrant township spirit. From the old sandstone buildings to the bustling taxi ranks, Komani carries the soul of our people.',
        contentXh:
          'I-Komani, ekwabizwa ngokuba yiQueenstown, yasungulwa ngo-1853 njengendawo yomkhosi. Namhlanje ingumzimba we-Eastern Cape enenkcubeko eyomeleleyo yamaXhosa.',
      },
    ];

    for (const ks of ksData) {
      await db.collection('knowledgeShare').add({
        title: ks.title,
        contentEn: ks.contentEn,
        contentXh: ks.contentXh,
        tags: ['culture', 'xhosa', 'tradition'],
        createdAt: now(),
      });
    }
    console.log('  ✅ 5 long knowledgeShare');

    // === COMPLAINTS (5 with LONG reasons) ===
    for (let i = 0; i < 5; i++) {
      const itemType = i < 3 ? 'listing' : 'infoBit';
      const itemId = i < 3 ? listingRefs[i].id : infoBitRefs[i - 3].id;
      await db.collection('complaints').add({
        reporterUid: userData[Math.floor(Math.random() * userData.length)].wa,
        itemType: itemType,
        itemId: itemId,
        reason: `This ${itemType} looks like a proper scam my guy. The photos are from Google Images, the price is way too low for what they offering, and when I asked for video proof the seller ghosted me. I saw the same ad last week with different number. People are losing money left and right – we need to take this down before more aunties get burned! The description also has broken English that doesn’t match a real local seller. Reported this one because I care about our community staying safe.`,
        status: 'pending',
        createdAt: now(),
      });
    }
    console.log('  ✅ 5 long complaints');

    console.log(
      '\n🎉 SEED-MORE COMPLETE! Database now has serious volume. Run the original seed first if you haven’t. All data fresh, realistic and ready for testing. Let’s go make Queens Connect the biggest thing in Komani! 🚀',
    );
  } catch (err) {
    console.error('Seed failed bro:', err);
    process.exit(1);
  }
}

main();
