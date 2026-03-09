# Firebase Storage: bucket and rules for CV uploads

The CV agent uploads generated PDF/DOCX files to Firebase Storage. This doc covers creating the bucket and deploying rules.

## 1. Enable Storage and get the bucket name

1. Open [Firebase Console](https://console.firebase.google.com) and select project **queens-connect-2c94d** (or your project).
2. Go to **Build → Storage**.
3. If Storage is not enabled, click **Get started** and complete the wizard (choose a location, secure rules mode). This creates the default bucket.
4. In the Storage tab, note the **bucket name**:
   - Newer projects: `queens-connect-2c94d.firebasestorage.app`
   - Older projects: `queens-connect-2c94d.appspot.com`

If your bucket is `*.appspot.com`, edit **firebase.json** and change the `storage[].bucket` value to match (e.g. `queens-connect-2c94d.appspot.com`).

## 2. Optional: set bucket in backend env

The backend defaults to `{FIREBASE_PROJECT_ID}.appspot.com`. If your bucket is different (e.g. `*.firebasestorage.app`), set in **backend/.env**:

```bash
FIREBASE_STORAGE_BUCKET=queens-connect-2c94d.firebasestorage.app
```

Use the exact bucket name from the Firebase Console.

## 3. Deploy Firestore and Storage rules

From the **repo root** (where `firebase.json` and `storage.rules` live):

```bash
# Login if needed (once)
firebase login

# Deploy only rules (no functions)
firebase deploy --only firestore:rules,storage
```

To deploy everything (Firestore rules, Storage rules, and Cloud Functions):

```bash
firebase deploy
```

After deploy, Storage rules in **storage.rules** are active: only the owning user (`request.auth.uid == waNumber`) can read files under `cvs/{waNumber}/`; writes are done by the backend (Admin SDK bypasses these rules).

## 4. Backend credentials

The backend uses **Firebase Admin SDK** (service account) to upload CVs. Ensure:

- **Local:** `GOOGLE_APPLICATION_CREDENTIALS` points to your service account JSON, or use Application Default Credentials (`gcloud auth application-default login`).
- **Render:** Add the same service account JSON via Render’s **Secret Files** or env and set `GOOGLE_APPLICATION_CREDENTIALS` to that path (see [docs/deploy-render.md](deploy-render.md)).

The service account needs **Storage Object Creator** (and **Viewer** if you use public URLs) on the bucket. In Google Cloud Console → IAM, the default Firebase Admin SDK service account usually already has this.

## Summary

| Step | Action |
|------|--------|
| 1 | Enable Storage in Firebase Console and note bucket name |
| 2 | (Optional) Set `FIREBASE_STORAGE_BUCKET` in backend `.env` if not using `*.appspot.com` |
| 3 | From repo root: `firebase deploy --only firestore:rules,storage` |
| 4 | Ensure backend has Firebase Admin credentials (local or Render) |
