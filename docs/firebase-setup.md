# Setting up Firebase for LocumDoc

LocumDoc keeps its records in **Cloud Firestore** and uploaded PDFs in **Firebase Storage**. This is a one-time setup of about 15 minutes in the Firebase console. Firebase's screens change from time to time, so the wording below may differ slightly from what you see.

## 1. Create the project

1. Go to https://console.firebase.google.com and click **Create a project**.
2. Name it, for example `locumdoc`. Firebase suggests a **project ID** (such as `locumdoc-3f2a1`). Note it down: it's the `FIREBASE_PROJECT_ID` setting.
3. Google Analytics isn't needed. You can turn it off.

## 2. Switch to the Blaze (pay-as-you-go) plan

Firebase Storage buckets require the Blaze plan. At LocumDoc's size, usage stays within or close to the free allowance, so expect a few dollars a month at most.

1. Click **Upgrade** at the bottom of the left menu and add a billing account.
2. In Google Cloud **Billing → Budgets & alerts**, set a budget, for example $10 a month with email alerts. Then a mistake can't run up a surprise bill.

## 3. Create the Firestore database (in Doha)

1. In the left menu: **Build → Firestore Database → Create database**.
2. **Location:** choose **`me-central1` (Doha)**. You can't change this later. Keeping the data in Qatar helps with Qatar's data-protection law (PDPPL) and with hospital customers.
3. **Rules:** choose **production mode**. That locks the database to everyone except the LocumDoc server, which is what we want: the website reads and writes through its own server key, never from visitors' browsers.

LocumDoc doesn't need any custom indexes.

## 4. Create the Storage bucket

1. **Build → Storage → Get started**.
2. Pick a location. Choose `me-central1` (Doha) if it's offered, so the PDFs sit next to the database.
3. Choose **production mode** for the rules, so the bucket stays private.
4. The bucket name appears at the top of the Storage page, for example `gs://locumdoc-3f2a1.firebasestorage.app`. The part after `gs://` is the `FIREBASE_STORAGE_BUCKET` setting.

## 5. Make the server key

1. Click the gear icon → **Project settings → Service accounts**.
2. Click **Generate new private key**, then **Generate key**. A `.json` file downloads.
3. Treat this file like a master password. Don't email it, don't put it in GitHub, and delete the download once it's in Render.

## 6. Give the key to Render

On https://dashboard.render.com, open the **locumdoc** service → **Environment** and add:

| Key | Value |
|---|---|
| `FIREBASE_PROJECT_ID` | the project ID from step 1 |
| `FIREBASE_STORAGE_BUCKET` | the bucket name from step 4, without `gs://` |
| `FIREBASE_CREDENTIALS_JSON` | open the `.json` key file in a text editor, copy **everything**, and paste it here |

Click **Save, rebuild and deploy**. When the deploy finishes, LocumDoc creates the countries, cities, specialties and admin account in Firestore on its first start.

## 7. Check it worked

- Open the site and sign up a test doctor account, then upload a PDF.
- In the Firebase console, **Firestore Database → Data** should now show collections such as `users`, `doctors` and `documents`, and **Storage** a `documents/` folder with the PDF.
- Redeploy on Render: the account is still there afterwards.

## Optional: a narrower key

The Firebase key from step 5 can manage the whole project. For tighter security, create a dedicated service account in Google Cloud (**IAM & Admin → Service accounts**) with only these two roles:
- **Cloud Datastore User**
- **Storage Object Admin** on the bucket

Then use its key instead.

## Backups

In **Firestore Database → Disaster recovery**, turn on daily backups. Losing the database would mean losing every account.
