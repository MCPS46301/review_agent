"""
Background scheduler that polls review platforms and processes new reviews.

Flow for each new review:
1. Fetch from platform APIs (Google, Facebook, Yelp)
2. Skip if already in the database (dedup by platform_review_id)
3. Generate AI draft response via Claude
4. For 3-5 stars: Auto-post the response to the platform
5. For 1-2 stars: Save as PENDING_APPROVAL — owner must approve
6. Send email notification to the business owner
"""

from datetime import datetime
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Review, ReviewResponse, Notification, Platform, ReviewStatus
from ai_responder import generate_response
from notifier import send_new_review_notification
from platforms.google import fetch_google_reviews, post_google_reply
from platforms.facebook import fetch_facebook_reviews, post_facebook_reply
from platforms.yelp import fetch_yelp_reviews
from config import settings


def process_new_review(db: Session, platform: Platform, review_data: dict) -> Review | None:
    """
    Process a single review from a platform:
    - Dedup check
    - Save to DB
    - Generate AI response
    - Auto-post or queue for approval
    - Send notification
    """
    # Dedup check
    existing = (
        db.query(Review)
        .filter(Review.platform_review_id == review_data["platform_review_id"])
        .first()
    )
    if existing:
        return None

    # Save review
    review = Review(
        platform=platform.value,
        platform_review_id=review_data["platform_review_id"],
        reviewer_name=review_data["reviewer_name"],
        reviewer_avatar=review_data.get("reviewer_avatar"),
        rating=review_data["rating"],
        review_text=review_data.get("review_text"),
        review_date=review_data["review_date"],
        platform_url=review_data.get("platform_url"),
        status=ReviewStatus.NEW,
    )
    db.add(review)
    db.flush()  # Get the ID

    print(
        f"[Scheduler] New {platform.value} review #{review.id}: "
        f"{review.rating}★ from {review.reviewer_name}"
    )

    # Generate AI response
    try:
        draft = generate_response(
            reviewer_name=review.reviewer_name,
            rating=review.rating,
            review_text=review.review_text,
        )
    except Exception as e:
        print(f"[Scheduler] AI generation failed for review #{review.id}: {e}")
        draft = ""

    response_record = ReviewResponse(
        review_id=review.id,
        draft_text=draft,
    )
    db.add(response_record)
    db.flush()

    # Decide: auto-post (3-5 stars) or queue for approval (1-2 stars)
    if review.rating >= 3 and draft:
        sent = _post_response(platform, review.platform_review_id, draft)
        if sent:
            review.status = ReviewStatus.RESPONDED
            response_record.final_text = draft
            response_record.sent_at = datetime.utcnow()
            print(f"[Scheduler] Auto-posted response for review #{review.id}")
        else:
            # Posting failed — still show in dashboard, mark as approved
            review.status = ReviewStatus.APPROVED
            response_record.final_text = draft
            response_record.send_error = "Auto-post failed — please post manually"
            print(f"[Scheduler] Auto-post failed for review #{review.id}")
    else:
        # 1-2 stars or no draft → queue for owner approval
        review.status = ReviewStatus.PENDING_APPROVAL
        print(f"[Scheduler] Review #{review.id} queued for owner approval")

    db.commit()

    # Send email notification
    db.refresh(review)
    success, error = send_new_review_notification(review)
    notif = Notification(
        review_id=review.id,
        notification_type="email",
        success=success,
        error_message=error,
    )
    db.add(notif)
    db.commit()

    return review


def _post_response(platform: Platform, platform_review_id: str, text: str) -> bool:
    """Attempt to post a response to the given platform."""
    if platform == Platform.GOOGLE:
        return post_google_reply(platform_review_id, text)
    elif platform == Platform.FACEBOOK:
        return post_facebook_reply(platform_review_id, text)
    elif platform == Platform.YELP:
        # Yelp does not support API-based responses
        return False
    return False


def poll_all_platforms():
    """Main polling job — fetch all platforms and process new reviews."""
    print(f"[Scheduler] Polling platforms at {datetime.utcnow().isoformat()}Z")
    db = SessionLocal()
    new_count = 0

    try:
        platform_fetchers = [
            (Platform.GOOGLE, fetch_google_reviews),
            (Platform.FACEBOOK, fetch_facebook_reviews),
            (Platform.YELP, fetch_yelp_reviews),
        ]

        for platform, fetcher in platform_fetchers:
            try:
                reviews = fetcher()
                print(f"[Scheduler] {platform.value}: fetched {len(reviews)} reviews")
                for review_data in reviews:
                    result = process_new_review(db, platform, review_data)
                    if result:
                        new_count += 1
            except Exception as e:
                print(f"[Scheduler] Error polling {platform.value}: {e}")

    finally:
        db.close()

    print(f"[Scheduler] Done. {new_count} new reviews processed.")
    return new_count


def post_approved_response(review_id: int) -> tuple[bool, str | None]:
    """
    Post an owner-approved response for a 1-2 star review.
    Called from the web route when the owner clicks "Send Response".
    """
    db = SessionLocal()
    try:
        review = db.query(Review).filter(Review.id == review_id).first()
        if not review:
            return False, "Review not found"

        response = review.response
        if not response:
            return False, "No response draft found"

        text = response.final_text or response.draft_text

        if review.platform == Platform.YELP:
            # Can't post via API — mark as responded and let owner copy manually
            review.status = ReviewStatus.RESPONDED
            response.final_text = text
            response.sent_at = datetime.utcnow()
            db.commit()
            return True, "yelp_manual"

        sent = _post_response(Platform(review.platform), review.platform_review_id, text)

        if sent:
            review.status = ReviewStatus.RESPONDED
            response.final_text = text
            response.approved_at = response.approved_at or datetime.utcnow()
            response.sent_at = datetime.utcnow()
            response.send_error = None
            db.commit()
            return True, None
        else:
            response.send_error = "Failed to post to platform — check API credentials"
            db.commit()
            return False, response.send_error

    finally:
        db.close()
