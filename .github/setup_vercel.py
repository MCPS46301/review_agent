#!/usr/bin/env python3
"""
Sets up the Vercel project and configures all environment variables.
Run by GitHub Actions before deployment.
"""
import json
import os
import sys
import urllib.request
import urllib.error

VERCEL_API = "https://api.vercel.com"
PROJECT_NAME = "macomb-reviews"


def api(method, path, body=None):
    req = urllib.request.Request(
        VERCEL_API + path,
        data=json.dumps(body).encode() if body else None,
        headers={"Authorization": f"Bearer {os.environ['VERCEL_TOKEN']}", "Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"  {e.code}: {e.read().decode()}")
        return None


def main():
    token = os.environ.get("VERCEL_TOKEN", "")
    if not token:
        sys.exit("VERCEL_TOKEN not set")

    me = api("GET", "/v2/user")
    if not me:
        sys.exit("Invalid VERCEL_TOKEN")
    print(f"Authenticated: {me['user']['name']}")
    org_id = me["user"]["id"]

    project = api("POST", "/v10/projects", {"name": PROJECT_NAME, "framework": None})
    if not project or "id" not in project:
        project = api("GET", f"/v9/projects/{PROJECT_NAME}")
    if not project or "id" not in project:
        sys.exit("Could not get or create project")

    project_id = project["id"]
    print(f"Project: {PROJECT_NAME} ({project_id})")

    # Write .vercel/project.json for the CLI
    os.makedirs(".vercel", exist_ok=True)
    with open(".vercel/project.json", "w") as f:
        json.dump({"projectId": project_id, "orgId": org_id}, f)
    print("Wrote .vercel/project.json")

    smtp_user = os.environ.get("SMTP_USERNAME", "")
    env_vars = {
        "DATABASE_URL": "postgresql://postgres:changeme2026%21%24%24@db.aarysgprbhdiggjtqoif.supabase.co:5432/postgres",
        "BUSINESS_NAME": "Macomb Powersports",
        "BUSINESS_OWNER_NAME": "Lloyd",
        "BUSINESS_OWNER_EMAIL": "lloyd@macombpowersports.com",
        "SMTP_HOST": "smtp.gmail.com",
        "SMTP_PORT": "587",
        "SMTP_USE_TLS": "true",
        "CRON_SECRET": "macombps2026secure",
        "POLL_INTERVAL_MINUTES": "15",
        "APP_BASE_URL": "https://macomb-reviews.vercel.app",
    }
    for key in ["ANTHROPIC_API_KEY", "SMTP_USERNAME", "SMTP_PASSWORD"]:
        val = os.environ.get(key, "").strip()
        if val:
            env_vars[key] = val
    if smtp_user:
        env_vars["SMTP_FROM_EMAIL"] = smtp_user

    existing = api("GET", f"/v9/projects/{project_id}/env") or {}
    for var in existing.get("envs", []):
        api("DELETE", f"/v9/projects/{project_id}/env/{var['id']}")

    payload = [
        {"key": k, "value": v, "type": "encrypted", "target": ["production", "preview", "development"]}
        for k, v in env_vars.items()
    ]
    result = api("POST", f"/v10/projects/{project_id}/env", payload) or {}
    print(f"Set {len(result.get('created', []))} env vars")


if __name__ == "__main__":
    main()
