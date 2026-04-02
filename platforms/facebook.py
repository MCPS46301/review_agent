"""
Facebook Graph API integration for Page reviews/recommendations.

Setup required:
1. Create a Facebook App at developers.facebook.com
2. Add "Pages" product and request permissions:
   - pages_read_engagement
   - pages_manage_posts
   - pages_read_user_content
3. Generate a long-lived Page Access Token for your business page
4. Set FACEBOOK_PAGE_ACCESS_TOKEN and FACEBOOK_PAGE_ID in .env

Note: Facebook replaced star ratings with a binary "Recommend" / "Don't Recommend"
system. Recommendations without a star rating are treated as 5 stars (positive)
or 1 star (negative) for routing purposes.
"""

from datetime import datetime
import httpx
from config import settings

FB_GRAPH_BASE = "https://graph.facebook.com/v19.0"


def fetch_facebook_reviews() -> list[dict]:
    """
    Fetch recent recommendations/reviews from the Facebook Page.

    Returns a list of normalized review dicts.
    """
    if not settings.facebook_page_access_token or not settings.facebook_page_id:
        return []

    try:
        url = f"{FB_GRAPH_BASE}/{settings.facebook_page_id}/ratings"
        resp = httpx.get(
            url,
            params={
                "access_token": settings.facebook_page_access_token,
                "fields": "reviewer,rating,review_text,created_time,recommendation_type",
                "limit": 50,
            },
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[Facebook] Failed to fetch reviews: {e}")
        return []

    reviews = []
    for r in data.get("data", []):
        try:
            review_date = datetime.strptime(r["created_time"], "%Y-%m-%dT%H:%M:%S+0000")

            # Facebook uses recommendation_type (positive/negative) or numeric rating
            if "rating" in r:
                rating = int(r["rating"])
            elif r.get("recommendation_type") == "positive":
                rating = 5
            elif r.get("recommendation_type") == "negative":
                rating = 1
            else:
                rating = 3

            reviewer = r.get("reviewer", {})
            reviews.append({
                "platform_review_id": r["id"],
                "reviewer_name": reviewer.get("name", "Anonymous"),
                "reviewer_avatar": None,
                "rating": rating,
                "review_text": r.get("review_text", "").strip() or None,
                "review_date": review_date,
                "platform_url": (
                    f"https://www.facebook.com/{settings.facebook_page_id}/reviews"
                ),
            })
        except Exception as e:
            print(f"[Facebook] Error parsing review {r.get('id')}: {e}")

    return reviews


def post_facebook_reply(platform_review_id: str, reply_text: str) -> bool:
    """
    Post a comment reply to a Facebook review/recommendation.

    Returns True on success, False on failure.
    """
    if not settings.facebook_page_access_token:
        return False

    try:
        url = f"{FB_GRAPH_BASE}/{platform_review_id}/comments"
        resp = httpx.post(
            url,
            params={"access_token": settings.facebook_page_access_token},
            json={"message": reply_text},
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"[Facebook] Failed to post reply to {platform_review_id}: {e}")
        return False
