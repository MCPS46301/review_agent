# Macomb Powersports — Review Auto-Responder

Automated online reputation management for Macomb Powersports. Monitors Google, Facebook, and Yelp for new customer reviews, generates AI-powered responses using Claude, and streamlines the owner's approval workflow.

## How It Works

| Review Rating | What Happens |
|---------------|-------------|
| ⭐⭐⭐⭐⭐ (5 stars) | Claude generates a warm, personalized response → **auto-posted** on the platform |
| ⭐⭐⭐⭐ (4 stars) | Claude generates a warm, personalized response → **auto-posted** on the platform |
| ⭐⭐⭐ (3 stars) | Claude generates a warm response → **auto-posted** |
| ⭐⭐ (2 stars) | Claude generates a draft → **Owner reviews & approves** before posting |
| ⭐ (1 star) | Claude generates a draft → **Owner reviews & approves** before posting |

**Email alerts** are sent for every new review. For 1–2 star reviews, the alert contains a direct link to the approval page.

## Quick Start

### 1. Clone and Install

```bash
cd review_agent
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env with your credentials (see sections below)
```

The **minimum required** credentials to get started:
- `ANTHROPIC_API_KEY` — for AI response generation
- `SMTP_*` settings — for email notifications
- At least one review platform (Google, Facebook, or Yelp)

### 3. Run

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000** in your browser.

## Platform Setup

### Google Business Profile

1. Go to [Google Cloud Console](https://console.cloud.google.com) → Create or select a project
2. Enable the **Business Profile API**
3. Create **OAuth 2.0 credentials** (Desktop App type) → download `credentials.json`
4. Run the one-time OAuth flow to get your refresh token:
   ```python
   from google_auth_oauthlib.flow import InstalledAppFlow
   flow = InstalledAppFlow.from_client_secrets_file('credentials.json',
       scopes=['https://www.googleapis.com/auth/business.manage'])
   creds = flow.run_local_server(port=0)
   print("Refresh token:", creds.refresh_token)
   ```
5. Find your location name:
   - `GET https://mybusinessaccountmanagement.googleapis.com/v1/accounts`
   - Then: `GET https://mybusinessbusinessinformation.googleapis.com/v1/{account}/locations`

### Facebook

1. Go to [Facebook Developers](https://developers.facebook.com) → Create App → Consumer type
2. Add the **Pages** product
3. Request permissions: `pages_read_engagement`, `pages_manage_posts`, `pages_read_user_content`
4. Generate a **Page Access Token** (long-lived) using the Graph API Explorer
5. Your **Page ID** is found in your Facebook Page Settings → Page Info

### Yelp

1. Create an app at [Yelp Developer Console](https://www.yelp.com/developers/v3/manage_app)
2. Copy the **API Key** to `YELP_API_KEY`
3. Your **Business ID** is the URL slug: `yelp.com/biz/macomb-powersports-macomb`

> **Note:** Yelp does not allow API-based review responses. The app will notify you and generate a draft, but you must paste it manually at [biz.yelp.com](https://biz.yelp.com).

### Email (Gmail)

1. Enable 2-Factor Authentication on your Google account
2. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Create an App Password for "Mail"
4. Use your Gmail address as `SMTP_USERNAME` and the app password as `SMTP_PASSWORD`

## Dashboard Features

- **Stats overview** — total reviews, pending approvals, average rating, response rate
- **Amber alert banner** — prominently shows when 1–2 star reviews need your approval
- **Filter & search** — by platform, rating, status
- **Review detail page** — full review text, editable response draft, regenerate button
- **Manual poll** — click "Refresh" to fetch new reviews immediately
- **Yelp copy button** — one-click copy for manual Yelp responses

## File Structure

```
review_agent/
├── main.py              # FastAPI app and routes
├── config.py            # Settings (loaded from .env)
├── database.py          # SQLite/SQLAlchemy setup
├── models.py            # Database models
├── ai_responder.py      # Claude API integration
├── scheduler.py         # Background polling + response workflow
├── notifier.py          # Email notifications
├── platforms/
│   ├── google.py        # Google Business Profile API
│   ├── facebook.py      # Facebook Graph API
│   └── yelp.py          # Yelp Fusion API (read-only)
├── templates/
│   ├── base.html        # Base layout
│   ├── dashboard.html   # Main review dashboard
│   └── review_detail.html  # Per-review page with response editor
├── static/style.css     # Additional styles
├── requirements.txt
└── .env.example         # Configuration template
```

## Customizing AI Responses

Edit the prompts in `ai_responder.py`:

- `POSITIVE_RESPONSE_PROMPT` — template for 3–5 star responses
- `NEGATIVE_RESPONSE_PROMPT` — template for 1–2 star responses  
- `BUSINESS_CONTEXT` — business background/personality given to Claude

The app uses **Claude Opus 4.6 with adaptive thinking** for the best response quality.
