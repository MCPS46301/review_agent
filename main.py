"""
Macomb Powersports — Review Auto-Responder
FastAPI web application for the owner dashboard.

Routes:
  GET  /              → Dashboard (all reviews, stats, pending approvals)
  GET  /review/{id}   → Review detail with draft response editor
  POST /review/{id}/approve    → Approve & send a response (1-2 star)
  POST /review/{id}/regenerate → Regenerate AI draft with owner notes
  POST /review/{id}/dismiss    → Dismiss a review (no response)
  POST /poll          → Manually trigger a platform poll
  GET  /api/stats     → JSON stats for the dashboard
"""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Depends, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from config import settings
from database import get_db, init_db
from models import Review, ReviewResponse, Notification, ReviewStatus, Platform
from scheduler import poll_all_platforms, post_approved_response
from ai_responder import regenerate_response


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    scheduler.add_job(
        poll_all_platforms,
        "interval",
        minutes=settings.poll_interval_minutes,
        id="poll_platforms",
        replace_existing=True,
        next_run_time=datetime.utcnow(),  # Run immediately on startup
    )
    scheduler.start()
    print(
        f"[App] Started. Polling every {settings.poll_interval_minutes} min. "
        f"Dashboard at {settings.app_base_url}"
    )
    yield
    scheduler.shutdown(wait=False)
    print("[App] Shutting down.")


app = FastAPI(
    title=f"{settings.business_name} — Review Manager",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ---------------------------------------------------------------------------
# Template helpers
# ---------------------------------------------------------------------------

def _get_stats(db: Session) -> dict:
    total = db.query(func.count(Review.id)).scalar() or 0
    pending = (
        db.query(func.count(Review.id))
        .filter(Review.status == ReviewStatus.PENDING_APPROVAL)
        .scalar() or 0
    )
    responded = (
        db.query(func.count(Review.id))
        .filter(Review.status == ReviewStatus.RESPONDED)
        .scalar() or 0
    )
    avg_rating = db.query(func.avg(Review.rating)).scalar()
    avg_rating = round(float(avg_rating), 1) if avg_rating else 0.0

    response_rate = round((responded / total * 100), 1) if total else 0.0

    platform_counts = {}
    for platform in Platform:
        count = (
            db.query(func.count(Review.id))
            .filter(Review.platform == platform.value)
            .scalar() or 0
        )
        if count:
            platform_counts[platform.value] = count

    return {
        "total": total,
        "pending": pending,
        "responded": responded,
        "avg_rating": avg_rating,
        "response_rate": response_rate,
        "platform_counts": platform_counts,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    filter: Optional[str] = None,
    platform: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Review).order_by(desc(Review.review_date))

    if filter == "pending":
        query = query.filter(Review.status == ReviewStatus.PENDING_APPROVAL)
    elif filter == "responded":
        query = query.filter(Review.status == ReviewStatus.RESPONDED)
    elif filter == "positive":
        query = query.filter(Review.rating >= 3)
    elif filter == "negative":
        query = query.filter(Review.rating <= 2)

    if platform and platform in [p.value for p in Platform]:
        query = query.filter(Review.platform == platform)

    reviews = query.limit(100).all()
    stats = _get_stats(db)

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "reviews": reviews,
            "stats": stats,
            "active_filter": filter,
            "active_platform": platform,
            "business_name": settings.business_name,
            "poll_interval": settings.poll_interval_minutes,
        },
    )


@app.get("/review/{review_id}", response_class=HTMLResponse)
async def review_detail(
    review_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    return templates.TemplateResponse(
        "review_detail.html",
        {
            "request": request,
            "review": review,
            "business_name": settings.business_name,
            "is_yelp": review.platform == Platform.YELP.value,
        },
    )


@app.post("/review/{review_id}/approve")
async def approve_review(
    review_id: int,
    response_text: str = Form(...),
    db: Session = Depends(get_db),
):
    """Owner approves and sends a response (1-2 star reviews, or manual send)."""
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    # Save the (possibly edited) final text
    if review.response:
        review.response.final_text = response_text.strip()
        review.response.approved_at = datetime.utcnow()
    else:
        resp = ReviewResponse(
            review_id=review.id,
            draft_text=response_text.strip(),
            final_text=response_text.strip(),
            approved_at=datetime.utcnow(),
        )
        db.add(resp)
    db.commit()

    # Post to platform
    success, detail = post_approved_response(review_id)

    if detail == "yelp_manual":
        # Redirect back with a "copy response" message
        return RedirectResponse(
            url=f"/review/{review_id}?sent=yelp_manual", status_code=303
        )
    elif success:
        return RedirectResponse(url=f"/review/{review_id}?sent=1", status_code=303)
    else:
        return RedirectResponse(
            url=f"/review/{review_id}?error=post_failed", status_code=303
        )


@app.post("/review/{review_id}/regenerate")
async def regenerate_draft(
    review_id: int,
    owner_notes: str = Form(default=""),
    db: Session = Depends(get_db),
):
    """Regenerate the AI draft response, optionally with owner guidance."""
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    new_draft = regenerate_response(
        reviewer_name=review.reviewer_name,
        rating=review.rating,
        review_text=review.review_text,
        owner_notes=owner_notes.strip(),
    )

    if review.response:
        review.response.draft_text = new_draft
        review.response.final_text = None
    else:
        resp = ReviewResponse(review_id=review.id, draft_text=new_draft)
        db.add(resp)

    db.commit()
    return RedirectResponse(url=f"/review/{review_id}?regenerated=1", status_code=303)


@app.post("/review/{review_id}/dismiss")
async def dismiss_review(
    review_id: int,
    db: Session = Depends(get_db),
):
    """Dismiss a review — owner chose not to respond."""
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review.status = ReviewStatus.DISMISSED
    review.updated_at = datetime.utcnow()
    db.commit()
    return RedirectResponse(url="/?filter=pending", status_code=303)


@app.post("/poll")
async def manual_poll(request: Request):
    """Manually trigger a platform poll (useful for testing)."""
    count = poll_all_platforms()
    return JSONResponse({"success": True, "new_reviews": count})


@app.get("/api/stats")
async def api_stats(db: Session = Depends(get_db)):
    """JSON endpoint for live stats refresh."""
    return _get_stats(db)
