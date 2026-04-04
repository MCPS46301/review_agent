"""
Macomb Powersports — Review Auto-Responder
FastAPI web application for the owner dashboard.

Routes:
  GET  /              → Dashboard (all reviews, stats, pending approvals)
  GET  /review/{id}   → Review detail with draft response editor
  POST /review/{id}/approve    → Approve & send a response (1-2 star)
  POST /review/{id}/regenerate → Regenerate AI draft with owner notes
  POST /review/{id}/dismiss    → Dismiss a review (no response)
  GET  /api/cron      → Called by Vercel Cron every day to poll platforms
  POST /poll          → Manually trigger a platform poll from the dashboard
  GET  /api/stats     → JSON stats for live dashboard refresh
"""

import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Depends, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from config import settings
from database import get_db, init_db
from models import Review, ReviewResponse, ReviewStatus, Platform
from scheduler import poll_all_platforms, post_approved_response
from ai_responder import regenerate_response

# Absolute paths so templates/static work on both local and Vercel
BASE_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# App lifecycle — APScheduler runs locally; Vercel uses its own Cron Jobs
# ---------------------------------------------------------------------------

IS_VERCEL = os.getenv("VERCEL") == "1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
        print("[App] Database initialized successfully")
    except Exception as e:
        print(f"[App] Database init failed (non-fatal): {e}")
    if not IS_VERCEL:
        from apscheduler.schedulers.background import BackgroundScheduler
        _scheduler = BackgroundScheduler()
        _scheduler.add_job(
            poll_all_platforms,
            "interval",
            minutes=settings.poll_interval_minutes,
            id="poll_platforms",
            replace_existing=True,
            next_run_time=datetime.utcnow(),
        )
        _scheduler.start()
        print(
            f"[App] Local mode. Polling every {settings.poll_interval_minutes} min. "
            f"Dashboard at {settings.app_base_url}"
        )
        yield
        _scheduler.shutdown(wait=False)
    else:
        print("[App] Vercel mode. Polling driven by Vercel Cron → /api/cron")
        yield


app = FastAPI(
    title=f"{settings.business_name} — Review Manager",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


# ---------------------------------------------------------------------------
# Template helpers
# ---------------------------------------------------------------------------

def _get_stats(db: Session) -> dict:
    try:
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
    except Exception as e:
        print(f"[App] Stats error: {e}")
        return {"total": 0, "pending": 0, "responded": 0, "avg_rating": 0.0, "response_rate": 0.0, "platform_counts": {}}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db), status_filter: Optional[str] = None):
    stats = _get_stats(db)
    query = db.query(Review).order_by(desc(Review.review_date))
    if status_filter and status_filter != "all":
        query = query.filter(Review.status == status_filter)
    reviews = query.limit(50).all()
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "reviews": reviews,
        "stats": stats,
        "status_filter": status_filter or "all",
        "settings": settings,
    })


@app.get("/review/{review_id}", response_class=HTMLResponse)
async def review_detail(review_id: int, request: Request, db: Session = Depends(get_db)):
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return templates.TemplateResponse("review_detail.html", {
        "request": request,
        "review": review,
        "settings": settings,
    })


@app.post("/review/{review_id}/approve")
async def approve_review(review_id: int, response_text: str = Form(...), db: Session = Depends(get_db)):
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    if review.response:
        review.response.final_text = response_text
        review.response.approved_at = datetime.utcnow()
    review.status = ReviewStatus.APPROVED
    db.commit()
    success, error = post_approved_response(review_id)
    if success:
        return RedirectResponse(url=f"/review/{review_id}?sent=1", status_code=303)
    return RedirectResponse(url=f"/review/{review_id}?error=1", status_code=303)


@app.post("/review/{review_id}/regenerate")
async def regenerate_review_response(
    review_id: int,
    owner_notes: str = Form(""),
    db: Session = Depends(get_db)
):
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    try:
        new_draft = regenerate_response(
            reviewer_name=review.reviewer_name,
            rating=review.rating,
            review_text=review.review_text,
            owner_notes=owner_notes,
        )
        if review.response:
            review.response.draft_text = new_draft
        else:
            from models import ReviewResponse as RR
            db.add(RR(review_id=review.id, draft_text=new_draft))
        db.commit()
    except Exception as e:
        print(f"[App] Regenerate failed: {e}")
    return RedirectResponse(url=f"/review/{review_id}", status_code=303)


@app.post("/review/{review_id}/dismiss")
async def dismiss_review(review_id: int, db: Session = Depends(get_db)):
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    review.status = ReviewStatus.DISMISSED
    db.commit()
    return RedirectResponse(url="/", status_code=303)


@app.get("/api/cron")
async def cron_job(request: Request):
    secret = request.headers.get("x-vercel-cron-secret") or request.query_params.get("secret")
    if settings.cron_secret and secret != settings.cron_secret:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        count = poll_all_platforms()
        return JSONResponse({"status": "ok", "new_reviews": count})
    except Exception as e:
        return JSONResponse({"status": "error", "error": str(e)}, status_code=500)


@app.post("/poll")
async def manual_poll():
    try:
        count = poll_all_platforms()
        return RedirectResponse(url=f"/?polled={count}", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/?poll_error=1", status_code=303)


@app.get("/api/stats")
async def api_stats(db: Session = Depends(get_db)):
    return JSONResponse(_get_stats(db))
