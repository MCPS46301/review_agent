"""
Background scheduler that polls Google reviews and processes them.

Flow for each new review:
1. Fetch from Google Business Profile API
2. Skip if already in the database (dedup by platform_review_id)
3. Generate AI draft response via Claude
4. For 3-5 stars: Auto-post the response to Google
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
from config import settings


def process_new_review(db: Session, platform: Platform, review_data: dict) -> Review | None:
    existing = (
        db.query(Review)
        .filter(Review.platform_review_id == review_data["platform_review_id"])
        .first()
    )
    if existing:
        return None

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
    db.flush()

    print(
        f"[Scheduler] New {platform.value} review #{review.id}: "
        f"{review.rating}\u2605 from {review.reviewer_name}"
    )

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

    if review.rating >= 3 and draft:
        sent = post_google_reply(review.platform_review_id, draft)
        if sent:
            review.status = ReviewStatus.RESPONDED
            response_record.final_text = draft
            response_record.sent_at = datetime.utcnow()
            print(f"[Scheduler] Auto-posted response for review #{review.id}")
        else:
            review.status = ReviewStatus.APPROVED
            response_record.final_text = draft
            response_record.send_error = "Auto-post failed — please post manually"
            print(f"[Scheduler] Auto-post failed for review #{review.id}")
    else:
        review.status = ReviewStatus.PENDING_APPROVAL
        print(f"[Scheduler] Review #{review.id} queued for owner approval")

    db.commit()

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


def poll_all_platforms():
    """Main polling job — fetch Google reviews and process new ones."""
    print(f"[Scheduler] Polling Google at {datetime.utcnow().isoformat()}Z")
    db = SessionLocal()
    new_count = 0

    try:
        try:
            reviews = fetch_google_reviews()
            print(f"[Scheduler] Google: fetched {len(reviews)} reviews")
            for review_data in reviews:
                result = process_new_review(db, Platform.GOOGLE, review_data)
                if result:
                    new_count += 1
        except Exception as e:
            print(f"[Scheduler] Error polling Google: {e}")
    finally:
        db.close()

    print(f"[Scheduler] Done. {new_count} new reviews processed.")
    return new_count


def post_approved_response(review_id: int) -> tuple[bool, str | None]:
    """
    Post an owner-approved response for a 1-2 star review.
    Called from the web route when the owner clicks Send Response.
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
        sent = post_google_reply(review.platform_review_id, text)

        if sent:
            review.status = ReviewStatus.RESPONDED
            response.final_text = text
            response.approved_at = response.approved_at or datetime.utcnow()
            response.sent_at = datetime.utcnow()
            response.send_error = None
            db.commit()
            return True, None
        else:
            response.send_error = "Failed to post to Google — check API credentials"
            db.commit()
            return False, response.send_error

    finally:
        db.close()
