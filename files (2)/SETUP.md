# Setup Guide — Fiber Sales Lead Form

Follow these steps in order. Takes about 15 minutes total.

---

## Step 1 — Create your Google Sheet

1. Go to sheets.google.com and create a new blank sheet
2. Name it something like **Fiber Sales Leads**
3. Copy the Sheet ID from the URL — it's the long string between /d/ and /edit
   - Example URL: `https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms/edit`
   - Your Sheet ID: `1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms`
4. Leave the sheet blank — the script will create the tabs and headers automatically

---

## Step 2 — Set up the Apps Script backend

1. In your Google Sheet, click **Extensions → Apps Script**
2. Delete any existing code in the editor
3. Paste the entire contents of **Code.gs** into the editor
4. Replace `YOUR_GOOGLE_SHEET_ID_HERE` with your actual Sheet ID from Step 1
5. Click the **Save** button (floppy disk icon)
6. Run the test function first:
   - Select `testWrite` from the function dropdown
   - Click **Run**
   - Accept any permissions it asks for
   - Check your sheet — you should see a "Test User" row appear in a new Warm Leads tab
   - Delete that test row once confirmed

---

## Step 3 — Deploy the Apps Script as a web app

1. In Apps Script, click **Deploy → New deployment**
2. Click the gear icon next to "Select type" and choose **Web app**
3. Fill in the settings:
   - Description: `Lead Intake Form`
   - Execute as: **Me**
   - Who has access: **Anyone**
4. Click **Deploy**
5. Copy the **Web app URL** — you'll need this next
   - It looks like: `https://script.google.com/macros/s/AKfyc.../exec`

---

## Step 4 — Connect the form to your backend

1. Open **index.html** in any text editor
2. Find this line near the bottom:
   ```
   const SCRIPT_URL = 'YOUR_APPS_SCRIPT_URL_HERE';
   ```
3. Replace `YOUR_APPS_SCRIPT_URL_HERE` with the Web app URL from Step 3
4. Save the file

---

## Step 5 — Deploy the form on GitHub Pages

1. Go to github.com and create a free account if you don't have one
2. Click **New repository**
   - Name it: `leads-form`
   - Set to **Public**
   - Click **Create repository**
3. Upload **index.html** to the repo:
   - Click **Add file → Upload files**
   - Drag in index.html
   - Click **Commit changes**
4. Enable GitHub Pages:
   - Go to **Settings → Pages**
   - Under Source, select **Deploy from a branch**
   - Branch: **main**, folder: **/ (root)**
   - Click **Save**
5. Wait about 60 seconds, then your form is live at:
   `https://yourgithubusername.github.io/leads-form`

---

## Step 6 — Add to your iPhone home screen

1. Open Safari on your iPhone (must be Safari, not Chrome)
2. Go to your GitHub Pages URL
3. Tap the **Share** button (box with arrow pointing up)
4. Scroll down and tap **Add to Home Screen**
5. Name it **Leads** and tap **Add**

It now lives on your home screen and opens full screen like an app.

---

## How the data flows

```
You fill out the form on your iPhone
        ↓
Form POSTs to your Apps Script URL
        ↓
Apps Script reads the contact type
        ↓
Warm lead → written to "Warm Leads" tab
Current customer → written to "Customers" tab
        ↓
Your agents read from these tabs on their monthly schedule
```

---

## Sheet column reference

**Warm Leads tab**
| Column | Description |
|---|---|
| Timestamp | When you submitted the form |
| First Name | |
| Last Name | |
| Phone | 10-digit number |
| Address | Optional |
| Notes | Timing context for the agent |
| Referred By | Which customer sent them |
| Status | New / Contacted / Booked / Closed / Archived |
| Last Contacted | Agent fills this in automatically |

**Customers tab**
| Column | Description |
|---|---|
| Timestamp | When you added them |
| First Name | |
| Last Name | |
| Phone | 10-digit number |
| Address | Optional |
| Notes | Any context |
| Status | Active / Inactive |
| Referral Count | Auto-incremented when a referral closes |

---

## Troubleshooting

**Form submits but nothing appears in the sheet**
- Make sure you redeployed Apps Script after editing it (Deploy → Manage deployments → edit → deploy new version)
- Check that your Sheet ID in Code.gs is correct

**GitHub Pages URL isn't working**
- Wait a few more minutes — it can take up to 5 minutes the first time
- Make sure the file is named exactly `index.html`

**Need to update the form after deploying**
- Edit index.html locally, upload the new version to GitHub, it updates automatically within a minute
