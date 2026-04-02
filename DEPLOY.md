# Vercel Deployment — Copy-Paste Cheat Sheet

Everything below is ready to paste directly into Vercel.
Open **vercel.com → your project → Settings → Environment Variables** and add each row.

---

## Environment Variables (paste these into Vercel)

| Variable | Value (ready to copy) |
|---|---|
| `DATABASE_URL` | `postgresql://postgres:changeme2026%21%24%24@db.aarysgprbhdiggjtqoif.supabase.co:5432/postgres` |
| `APP_BASE_URL` | *(paste your Vercel URL after first deploy, e.g. `https://macomb-reviews.vercel.app`)* |
| `BUSINESS_NAME` | `Macomb Powersports` |
| `BUSINESS_OWNER_EMAIL` | *(your email)* |
| `BUSINESS_OWNER_NAME` | *(your name)* |
| `ANTHROPIC_API_KEY` | *(from console.anthropic.com → API Keys)* |
| `SMTP_HOST` | `smtp.gmail.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USE_TLS` | `true` |
| `SMTP_USERNAME` | *(your Gmail address)* |
| `SMTP_PASSWORD` | *(Gmail App Password — see note below)* |
| `SMTP_FROM_EMAIL` | *(your Gmail address)* |
| `CRON_SECRET` | *(any random string, e.g. `macombps2026secure`)* |
| `GOOGLE_CLIENT_ID` | *(from Google Cloud Console)* |
| `GOOGLE_CLIENT_SECRET` | *(from Google Cloud Console)* |
| `GOOGLE_REFRESH_TOKEN` | *(from OAuth flow)* |
| `GOOGLE_LOCATION_NAME` | *(e.g. `accounts/123/locations/456`)* |
| `FACEBOOK_PAGE_ACCESS_TOKEN` | *(from Facebook Developers)* |
| `FACEBOOK_PAGE_ID` | *(your Facebook Page numeric ID)* |
| `YELP_API_KEY` | *(from yelp.com/developers)* |
| `YELP_BUSINESS_ID` | `macomb-powersports-macomb` |

---

## Step-by-Step on iPad

### 1. Deploy to Vercel (2 min)
1. Go to **vercel.com** → **Add New Project**
2. Import from GitHub → select **mcps46301/review_agent**
3. Leave build settings as-is (vercel.json handles everything)
4. Click **Deploy** (first deploy — before adding env vars — is fine, it just won't connect to DB yet)
5. Copy your deployment URL (e.g. `https://macomb-reviews.vercel.app`)

### 2. Add Environment Variables (5 min)
1. In Vercel: **Project → Settings → Environment Variables**
2. Add each row from the table above
3. For `APP_BASE_URL` — paste the URL from step 1
4. Click **Save** after each variable (or use bulk import — see tip below)

### 3. Redeploy (30 sec)
1. Go to **Deployments** tab → click the latest deployment → **Redeploy**
2. The app will restart with the new env vars and create the database tables automatically

---

## Gmail App Password (required for email alerts)

1. Make sure 2-Factor Authentication is enabled on your Google account
2. Go to: **myaccount.google.com → Security → 2-Step Verification → App passwords**
3. Select app: **Mail** → Select device: **Other** → name it "Macomb Reviews"
4. Copy the 16-character password shown (no spaces) → paste as `SMTP_PASSWORD`

---

## Vercel Bulk Import Tip

Instead of adding variables one by one, Vercel lets you paste a `.env`-style block.
Click **Import** on the Environment Variables page and paste this (fill in the blanks):

```
DATABASE_URL=postgresql://postgres:changeme2026%21%24%24@db.aarysgprbhdiggjtqoif.supabase.co:5432/postgres
BUSINESS_NAME=Macomb Powersports
BUSINESS_OWNER_EMAIL=
BUSINESS_OWNER_NAME=
APP_BASE_URL=https://YOUR-PROJECT.vercel.app
ANTHROPIC_API_KEY=
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=
CRON_SECRET=macombps2026secure
YELP_BUSINESS_ID=macomb-powersports-macomb
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REFRESH_TOKEN=
GOOGLE_LOCATION_NAME=
FACEBOOK_PAGE_ACCESS_TOKEN=
FACEBOOK_PAGE_ID=
YELP_API_KEY=
```

---

## After Deploying

Once live, the app will:
- **Poll Google, Facebook, and Yelp every 15 minutes** via Vercel Cron
- **Email you** for every new review
- **Auto-respond** to 3-5 star reviews immediately
- **Queue 1-2 star reviews** for your approval at `https://YOUR-PROJECT.vercel.app`
