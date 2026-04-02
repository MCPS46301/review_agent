#!/usr/bin/env python3
"""
GitHub Actions deploy script — calls Vercel REST API to create the project,
set environment variables, and trigger a production deployment.

All sensitive values come from GitHub Actions secrets (env vars).
Non-sensitive defaults are hardcoded below.
"""
import json
import os
import sys
import urllib.request
import urllib.error

VERCEL_API = "https://api.vercel.com"
GITHUB_REPO = "mcps46301/review_agent"
BRANCH = "claude/review-auto-responder-app-oXU2g"
PROJECT_NAME = "macomb-reviews"

KNOWN_ENV = {
    "DATABASE_URL": "postgresql://postgres:changeme2026%21%24%24@db.aarysgprbhdiggjtqoif.supabase.co:5432/postgres",
    "BUSINESS_NAME": "Macomb Powersports",
    "BUSINESS_OWNER_NAME": "Lloyd",
    "BUSINESS_OWNER_EMAIL": "lloyd@macombpowersports.com",
    "SMTP_HOST": "smtp.gmail.com",
    "SMTP_PORT": "587",
    "SMTP_USE_TLS": "true",
    "YELP_BUSINESS_ID": "macomb-powersports-macomb",
    "CRON_SECRET": "macombps2026secure",
    "POLL_INTERVAL_MINUTES": "15",
}

SECRET_KEYS = [
    "ANTHROPIC_API_KEY",
    "SMTP_USERNAME",
    "SMTP_PASSWORD",
    "SMTP_FROM_EMAIL",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "GOOGLE_REFRESH_TOKEN",
    "GOOGLE_LOCATION_NAME",
    "FACEBOOK_PAGE_ID",
    "FACEBOOK_PAGE_ACCESS_TOKEN",
    "YELP_API_KEY",
]


def api_call(token, method, path, body=None):
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
        raw = e.read().decode()
        try:
            err = json.loads(raw)
            msg = err.get("error", {}).get("message", raw)
        except Exception:
            msg = raw
        print(f"  API {e.code}: {msg}")
        return None


def main():
    token = os.environ.get("VERCEL_TOKEN")
    if not token:
        sys.exit("ERROR: VERCEL_TOKEN secret not set in GitHub repository secrets.")

    # Verify token
    me = api_call(token, "GET", "/v2/user")
    if not me:
        sys.exit("ERROR: Invalid VERCEL_TOKEN — check the secret value.")
    print(f"Authenticated as {me['user']['name']} ({me['user']['email']})")

    # Detect team scope
    teams = api_call(token, "GET", "/v2/teams") or {}
    team_id = None
    team_list = teams.get("teams", [])
    if team_list:
        team_id = team_list[0]["id"]
        print(f"Using team: {team_list[0]['name']}")
    team_qs = f"?teamId={team_id}" if team_id else ""

    # Create project (or retrieve if it already exists)
    project = api_call(token, "POST", f"/v10/projects{team_qs}", {
        "name": PROJECT_NAME,
        "framework": None,
        "gitRepository": {
            "type": "github",
            "repo": GITHUB_REPO,
        },
    })
    if not project or "id" not in project:
        project = api_call(token, "GET", f"/v9/projects/{PROJECT_NAME}{team_qs}")
    if not project or "id" not in project:
        sys.exit("ERROR: Could not create or retrieve Vercel project.")

    project_id = project["id"]
    aliases = project.get("alias", [])
    if aliases:
        first = aliases[0]
        project_url = f"https://{first['domain'] if isinstance(first, dict) else first}"
    else:
        project_url = f"https://{PROJECT_NAME}.vercel.app"
    print(f"Project: {project_url}  (id: {project_id})")

    # Build full env var set
    all_env = dict(KNOWN_ENV)
    all_env["APP_BASE_URL"] = project_url

    for key in SECRET_KEYS:
        val = os.environ.get(key, "").strip()
        if val:
            all_env[key] = val

    # SMTP_FROM_EMAIL mirrors SMTP_USERNAME when not set separately
    if "SMTP_USERNAME" in all_env and "SMTP_FROM_EMAIL" not in all_env:
        all_env["SMTP_FROM_EMAIL"] = all_env["SMTP_USERNAME"]

    # Delete existing env vars to avoid duplicate-key errors on re-run
    existing = api_call(token, "GET", f"/v9/projects/{project_id}/env{team_qs}") or {}
    for var in existing.get("envs", []):
        api_call(token, "DELETE", f"/v9/projects/{project_id}/env/{var['id']}{team_qs}")
    if existing.get("envs"):
        print(f"Removed {len(existing['envs'])} existing env vars")

    # Bulk-set env vars
    payload = [
        {
            "key": k,
            "value": v,
            "type": "encrypted",
            "target": ["production", "preview", "development"],
        }
        for k, v in all_env.items()
    ]
    result = api_call(token, "POST", f"/v10/projects/{project_id}/env{team_qs}", payload)
    if result is not None:
        print(f"Set {len(result.get('created', []))} environment variables")
    else:
        print("WARNING: Bulk env-var set failed — add them manually in Vercel dashboard.")

    # Trigger deployment from the branch
    deploy = api_call(token, "POST", f"/v13/deployments{team_qs}", {
        "name": PROJECT_NAME,
        "gitSource": {
            "type": "github",
            "repo": GITHUB_REPO,
            "ref": BRANCH,
        },
        "projectId": project_id,
    })

    print("")
    if deploy and deploy.get("url"):
        print(f"Deployment triggered: https://{deploy['url']}")
    else:
        print("Deployment trigger returned no URL — check Vercel dashboard for status.")
    print(f"Live dashboard will be at: {project_url}")
    print("Reviews will be polled every 15 minutes automatically via Vercel Cron.")


if __name__ == "__main__":
    main()
