"""
Yelp Fusion API integration (READ ONLY).

Important: Yelp does NOT allow businesses to post review responses via the
public Fusion API. Responses must be submitted through the Yelp Business
Owner portal at biz.yelp.com.

For Yelp reviews, this app will:
1. Detect new reviews and notify the owner
2. Generate a draft response via Claude
3. Display a "Copy Response" button in the dashboard
4. Owner pastes the response manually at biz.yelp.com

Setup required:
1. Create a Yelp App at https://www.yelp.com/developers/v3/manage_app
2. Copy the API Key to YELP_API_KEY in .env
3. Find your business ID by searching at https://www.yelp.com — the URL slug
   (e.g. "macomb-powersports-macomb") is your YELP_BUSINESS_ID
"""

from datetime import datetime
import httpx
from config import settings

YELP_API_BASE = "https://api.yelp.com/v3"


def fetch_yelp_reviews() -> list[dict]:
    """
    Fetch recent reviews from Yelp Fusion API.

    Returns a list of normalized review dicts.
    Note: Yelp API returns a maximum of 3 most recent reviews per call.
    """
    if not settings.yelp_api_key or not settings.yelp_business_id:
        return []

    try:
        url = f"{YELP_API_BASE}/businesses/{settings.yelp_business_id}/reviews"
        resp = httpx.get(
            url,
            headers={"Authorization": f"Bearer {settings.yelp_api_key}"},
            params={"limit": 50, "sort_by": "yelp_sort"},
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[Yelp] Failed to fetch reviews: {e}")
        return []

    reviews = []
    for r in data.get("reviews", []):
        try:
            review_date = datetime.strptime(r["time_created"], "%Y-%m-%d %H:%M:%S")
            user = r.get("user", {})
            reviews.append({
                "platform_review_id": r["id"],
                "reviewer_name": user.get("name", "Anonymous"),
                "reviewer_avatar": user.get("image_url"),
                "rating": int(r["rating"]),
                "review_text": r.get("text", "").strip() or None,
                "review_date": review_date,
                "platform_url": r.get("url"),
            })
        except Exception as e:
            print(f"[Yelp] Error parsing review {r.get('id')}: {e}")

    return reviews
