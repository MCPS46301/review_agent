#!/usr/bin/env python3
"""
Automated Vercel deployment script for Macomb Powersports Review App.

Run this from GitHub Codespaces (free, browser-based) or any terminal:
  python3 scripts/deploy_to_vercel.py

You will need:
  1. A Vercel Access Token  →  vercel.com/account/tokens → Create
  2. Your Anthropic API Key →  console.anthropic.com/api-keys
  3. Gmail App Password     →  myaccount.google.com → Security → App passwords
  4. (Optional) Google/Facebook/Yelp API keys for each review platform

The script creates the Vercel project, sets all environment variables,
and triggers the first deployment automatically.
"""

import json
import os
import sys
import urllib.request
import urllib.error
import getpass

# ── Pre-filled values (already known) ──────────────────────────────────────
KNOWN_ENV = {
    "DATABASE_URL": "postgresql://postgres:changeme2026%21%24%24@db.aarysgprbhdiggjtqoif.supabase.co:5432/postgres",
    "BUSINESS_NAME": "Macomb Powersports",
    "SMTP_HOST": "smtp.gmail.com",
    "SMTP_PORT": "587",
    "SMTP_USE_TLS": "true",
    "YELP_BUSINESS_ID": "macomb-powersports-macomb",
    "CRON_SECRET": "macombps2026secure",
    "POLL_INTERVAL_MINUTES": "15",
}

VERCEL_API = "https://api.vercel.com"
GITHUB_REPO = "mcps46301/review_agent"


def api(token, method, path, body=None):
    url = VERCEL_API + path
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        err = json.loads(e.read().decode())
        print(f"\n  ✗ API error {e.code}: {err.get('error', {}).get('message', str(err))}")
        return None


def prompt(label, secret=False, default=None):
    suffix = f" [{default}]" if default else ""
    full = f"  {label}{suffix}: "
    if secret:
        val = getpass.getpass(full)
    else:
        val = input(full).strip()
    return val or default or ""


def main():
    print("\n" + "=" * 60)
    print("  Macomb Powersports — Vercel Auto-Deploy")
    print("=" * 60 + "\n")

    # ── Step 1: Vercel token ──────────────────────────────────────
    print("Step 1 of 4 — Vercel Access Token")
    print("  Get one at: vercel.com/account/tokens → Create Token\n")
    vercel_token = prompt("Vercel token", secret=True)
    if not vercel_token:
        sys.exit("Token required.")

    # Verify token
    me = api(vercel_token, "GET", "/v2/user")
    if not me:
        sys.exit("Invalid Vercel token — please check and try again.")
    print(f"  ✓ Authenticated as {me['user']['name']} ({me['user']['email']})\n")

    # Get team id if needed
    teams = api(vercel_token, "GET", "/v2/teams") or {}
    team_id = None
    team_list = teams.get("teams", [])
    if team_list:
        print(f"  Found team: {team_list[0]['name']} — using team scope")
        team_id = team_list[0]["id"]

    team_qs = f"?teamId={team_id}" if team_id else ""

    # ── Step 2: Collect remaining env vars ───────────────────────
    print("Step 2 of 4 — API Keys & Email Setup")
    print("  (Leave blank to skip any platform for now)\n")

    extra_env = {}
    extra_env["BUSINESS_OWNER_EMAIL"] = prompt("Your email address")
    extra_env["BUSINESS_OWNER_NAME"] = prompt("Your name", default="Owner")
    extra_env["ANTHROPIC_API_KEY"] = prompt("Anthropic API key (console.anthropic.com)", secret=True)

    print("\n  Email notifications (Gmail):")
    extra_env["SMTP_USERNAME"] = prompt("Gmail address")
    extra_env["SMTP_PASSWORD"] = prompt("Gmail App Password (16 chars)", secret=True)
    extra_env["SMTP_FROM_EMAIL"] = extra_env["SMTP_USERNAME"]

    print("\n  Google Business Profile (optional — press Enter to skip):")
    extra_env["GOOGLE_CLIENT_ID"] = prompt("Google Client ID")
    if extra_env["GOOGLE_CLIENT_ID"]:
        extra_env["GOOGLE_CLIENT_SECRET"] = prompt("Google Client Secret", secret=True)
        extra_env["GOOGLE_REFRESH_TOKEN"] = prompt("Google Refresh Token", secret=True)
        extra_env["GOOGLE_LOCATION_NAME"] = prompt("Google Location Name (accounts/x/locations/y)")

    print("\n  Facebook (optional — press Enter to skip):")
    extra_env["FACEBOOK_PAGE_ID"] = prompt("Facebook Page ID")
    if extra_env["FACEBOOK_PAGE_ID"]:
        extra_env["FACEBOOK_PAGE_ACCESS_TOKEN"] = prompt("Facebook Page Access Token", secret=True)

    print("\n  Yelp (optional — press Enter to skip):")
    extra_env["YELP_API_KEY"] = prompt("Yelp API key")

    # ── Step 3: Create Vercel project ────────────────────────────
    print("\nStep 3 of 4 — Creating Vercel Project\n")

    project_body = {
        "name": "macomb-reviews",
        "framework": None,
        "gitRepository": {
            "type": "github",
            "repo": GITHUB_REPO,
        },
    }

    project = api(vercel_token, "POST", f"/v10/projects{team_qs}", project_body)
    if not project or "id" not in project:
        # Try to get existing project
        project = api(vercel_token, "GET", f"/v9/projects/macomb-reviews{team_qs}")

    if not project:
        sys.exit("Could not create or find project.")

    project_id = project["id"]
    project_url = f"https://{project.get('alias', ['macomb-reviews.vercel.app'])[0]}" \
        if project.get("alias") else "https://macomb-reviews.vercel.app"
    print(f"  ✓ Project ready: {project_url}\n")

    # ── Step 4: Set environment variables ────────────────────────
    print("Step 4 of 4 — Setting Environment Variables\n")

    all_env = {**KNOWN_ENV, **{k: v for k, v in extra_env.items() if v}}
    all_env["APP_BASE_URL"] = project_url

    env_payload = [
        {
            "key": k,
            "value": v,
            "type": "encrypted",
            "target": ["production", "preview", "development"],
        }
        for k, v in all_env.items()
    ]

    result = api(
        vercel_token,
        "POST",
        f"/v10/projects/{project_id}/env{team_qs}",
        env_payload,
    )
    if result is not None:
        created = len(result.get("created", []))
        print(f"  ✓ {created} environment variables set\n")
    else:
        print("  ⚠ Could not set env vars via bulk — try the DEPLOY.md manual steps\n")

    # Trigger deployment
    deploy = api(
        vercel_token,
        "POST",
        f"/v13/deployments{team_qs}",
        {
            "name": "macomb-reviews",
            "gitSource": {
                "type": "github",
                "repo": GITHUB_REPO,
                "ref": "claude/review-auto-responder-app-oXU2g",
            },
            "projectId": project_id,
        },
    )

    print("=" * 60)
    if deploy and deploy.get("url"):
        print(f"\n  🚀 Deploying! Visit: https://{deploy['url']}")
    else:
        print(f"\n  ✓ Setup complete! Go to vercel.com → {project_url}")
        print("     Click 'Redeploy' to trigger the first live deployment.")
    print("\n  Your review dashboard will be live at:")
    print(f"    {project_url}")
    print("\n  Reviews will be polled every 15 minutes automatically.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
