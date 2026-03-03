/**
 * Load voucher codes into Firestore voucher_pool for Kasi Points redemption.
 *
 * CSV format (no header): code,value
 * - code: the voucher code string (e.g. X7K9P2M4Q8R5) — becomes document ID
 * - value: 10 | 20 | 50 (R10, R20, R50)
 *
 * Example CSV:
 *   X7K9P2M4Q8R5,10
 *   A1B2C3D4E5F6,20
 *   Z9Y8X7W6V5U4,50
 *
 * Usage:
 *   cd functions && node scripts/load-voucher-pool.js path/to/vouchers.csv
 *   cd functions && node scripts/load-voucher-pool.js path/to/vouchers.csv --dry-run
 *
 * Uses FIRESTORE_EMULATOR_HOST if set (e.g. 127.0.0.1:8080); otherwise production.
 */
const admin = require("firebase-admin");
const fs = require("fs");
const path = require("path");

const PROJECT_ID = process.env.GCLOUD_PROJECT || "queens-connect-2c94d";

function parseCsv(filePath) {
  const content = fs.readFileSync(filePath, "utf-8");
  const lines = content.split(/\r?\n/).filter((line) => line.trim());
  const rows = [];
  for (const line of lines) {
    const parts = line.split(",").map((s) => s.trim());
    if (parts.length < 2) continue;
    const [code, valueStr] = parts;
    const value = parseInt(valueStr, 10);
    if (!code || isNaN(value) || ![10, 20, 50].includes(value)) {
      console.warn("Skipping invalid line:", line);
      continue;
    }
    rows.push({ code, value });
  }
  return rows;
}

async function main() {
  const args = process.argv.slice(2);
  const csvPath = args.find((a) => !a.startsWith("--"));
  const dryRun = args.includes("--dry-run");

  if (!csvPath) {
    console.error("Usage: node load-voucher-pool.js <path/to/vouchers.csv> [--dry-run]");
    process.exit(1);
  }

  const resolved = path.resolve(csvPath);
  if (!fs.existsSync(resolved)) {
    console.error("File not found:", resolved);
    process.exit(1);
  }

  const rows = parseCsv(resolved);
  if (rows.length === 0) {
    console.error("No valid rows in CSV. Expected: code,value (value 10, 20, or 50)");
    process.exit(1);
  }

  if (!admin.apps.length) {
    admin.initializeApp({ projectId: PROJECT_ID });
  }
  const db = admin.firestore();

  console.log(
    dryRun ? "[DRY RUN] Would load" : "Loading",
    rows.length,
    "vouchers into voucher_pool. Emulator:",
    !!process.env.FIRESTORE_EMULATOR_HOST
  );

  if (dryRun) {
    console.log("Dry run: no writes. Sample:", rows.slice(0, 3));
    return;
  }

  const BATCH_SIZE = 500;
  for (let i = 0; i < rows.length; i += BATCH_SIZE) {
    const chunk = rows.slice(i, i + BATCH_SIZE);
    const batch = db.batch();
    for (const { code, value } of chunk) {
      const ref = db.collection("voucher_pool").doc(code);
      batch.set(ref, {
        value,
        status: "available",
      });
    }
    await batch.commit();
    console.log("Committed", chunk.length, "vouchers (batch", Math.floor(i / BATCH_SIZE) + 1, ")");
  }
  console.log("Done. Loaded", rows.length, "vouchers.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
