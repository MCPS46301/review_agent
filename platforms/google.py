"""
Google Business Profile API integration.

Setup required:
1. Create a Google Cloud project at console.cloud.google.com
2. Enable the "Business Profile API" (formerly My Business API)
3. Create OAuth 2.0 credentials (Desktop App type)
4. Run the OAuth flow once to get GOOGLE_REFRESH_TOKEN
5. Set GOOGLE_LOCATION_NAME to your business location resource name
   (e.g. "accounts/123456789/locations/987654321")
   Find it via: GET https://mybusinessaccountmanagement.googleapis.com/v1/accounts
"""

from datetime import datetime
import httpx
from config import settings

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REVIEWS_BASE = "https://mybusiness.googleapis.com/v4"


def _get_access_token() -> str:
    """Exchange refresh token for a fresh access token."""
    resp = httpx.post(
        GOOGLE_TOKEN_URL,
        data={
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "refresh_token": settings.google_refresh_token,
            "grant_type": "refresh_token",
        },
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def fetch_google_reviews() -> list[dict]:
    """
    Fetch recent reviews from Google Business Profile.

    Returns a list of normalized review dicts with keys:
        platform_review_id, reviewer_name, reviewer_avatar,
        rating, review_text, review_date, platform_url
    """
    if not all([
        settings.google_client_id,
        settings.google_client_secret,
        settings.google_refresh_token,
        settings.google_location_name,
    ]):
        return []

    try:
        token = _get_access_token()
        url = f"{GOOGLE_REVIEWS_BASE}/{settings.google_location_name}/reviews"
        resp = httpx.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            params={"pageSize": 50},
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[Google] Failed to fetch reviews: {e}")
        return []

    reviews = []
    for r in data.get("reviews", []):
        try:
            review_date = datetime.fromisoformat(
                r["createTime"].replace("Z", "+00:00")
            ).replace(tzinfo=None)
            reviews.append({
                "platform_review_id": r["reviewId"],
                "reviewer_name": r.get("reviewer", {}).get("displayName", "Anonymous"),
                "reviewer_avatar": r.get("reviewer", {}).get("profilePhotoUrl"),
                "rating": _star_rating_to_int(r.get("starRating", "ZERO")),
                "review_text": r.get("comment", "").strip() or None,
                "review_date": review_date,
                "platform_url": (
                    f"https://search.google.com/local/reviews?placeid="
                    + settings.google_location_name.split("/")[-1]
                ),
            })
        except Exception as e:
            print(f"[Google] Error parsing review {r.get('reviewId')}: {e}")

    return reviews


def post_google_reply(platform_review_id: str, reply_text: str) -> bool:
    """
    Post a reply to a Google review.

    Returns True on success, False on failure.
    """
    if not all([
        settings.google_client_id,
        settings.google_client_secret,
        settings.google_refresh_token,
        settings.google_location_name,
    ]):
        return False

    try:
        token = _get_access_token()
        url = (
            f"{GOOGLE_REVIEWS_BASE}/{settings.google_location_name}"
            f"/reviews/{platform_review_id}/reply"
        )
        resp = httpx.put(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={"comment": reply_text},
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"[Google] Failed to post reply to {platform_review_id}: {e}")
        return False


def _star_rating_to_int(star_rating: str) -> int:
    mapping = {
        "ONE": 1,
        "TWO": 2,
        "THREE": 3,
        "FOUR": 4,
        "FIVE": 5,
    }
    return mapping.get(star_rating.upper(), 0)
