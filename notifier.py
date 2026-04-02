"""
Email notification system for new reviews.

Sends the business owner an email when a new review is detected, with:
- Review details (platform, rating, reviewer, text)
- For 1-2 star reviews: link to the approval dashboard
- For 3-5 star reviews: confirmation that an auto-response was sent
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from config import settings
from models import Review


STAR_MAP = {1: "⭐", 2: "⭐⭐", 3: "⭐⭐⭐", 4: "⭐⭐⭐⭐", 5: "⭐⭐⭐⭐⭐"}


def _build_new_review_email(review: Review) -> tuple[str, str, str]:
    """Build subject and HTML/plain body for a new review notification."""
    stars = STAR_MAP.get(review.rating, "")
    platform_name = review.platform.title()
    review_text = review.review_text or "(No written review — rating only)"

    # Subject
    if review.rating <= 2:
        subject = (
            f"🚨 ACTION REQUIRED: {review.rating}-Star Review on {platform_name} "
            f"from {review.reviewer_name}"
        )
    else:
        subject = (
            f"🌟 New {review.rating}-Star Review on {platform_name} "
            f"from {review.reviewer_name}"
        )

    dashboard_url = f"{settings.app_base_url}/review/{review.id}"

    if review.rating <= 2:
        action_section = f"""
        <div style="background:#fff3cd;border:1px solid #ffc107;padding:16px;border-radius:8px;margin:16px 0;">
            <strong>⚠️ This review requires your approval before a response is sent.</strong><br><br>
            Claude has generated a draft response. Please review it, edit if needed, then approve to send.
            <br><br>
            <a href="{dashboard_url}"
               style="background:#dc3545;color:white;padding:10px 20px;text-decoration:none;
                      border-radius:6px;display:inline-block;font-weight:bold;">
                Review &amp; Approve Response →
            </a>
        </div>
        """
        plain_action = (
            f"\n⚠️ ACTION REQUIRED: This low-star review needs your approval before a response is sent.\n"
            f"Review &amp; approve here: {dashboard_url}\n"
        )
    else:
        action_section = f"""
        <div style="background:#d4edda;border:1px solid #28a745;padding:16px;border-radius:8px;margin:16px 0;">
            <strong>✅ A personalized response has been automatically sent on your behalf.</strong><br><br>
            <a href="{dashboard_url}"
               style="background:#28a745;color:white;padding:10px 20px;text-decoration:none;
                      border-radius:6px;display:inline-block;font-weight:bold;">
                View Review &amp; Response →
            </a>
        </div>
        """
        plain_action = (
            f"\n✅ A personalized response was automatically sent.\n"
            f"View it here: {dashboard_url}\n"
        )

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;color:#333;">
        <div style="background:#1a1a2e;padding:20px;border-radius:8px 8px 0 0;">
            <h1 style="color:white;margin:0;font-size:20px;">
                {settings.business_name} — Review Alert
            </h1>
        </div>
        <div style="padding:24px;border:1px solid #ddd;border-top:none;border-radius:0 0 8px 8px;">
            <h2 style="margin-top:0;">
                New {platform_name} Review {stars}
            </h2>
            <table style="width:100%;border-collapse:collapse;margin-bottom:16px;">
                <tr>
                    <td style="padding:8px;background:#f8f9fa;width:120px;font-weight:bold;">Platform</td>
                    <td style="padding:8px;">{platform_name}</td>
                </tr>
                <tr>
                    <td style="padding:8px;background:#f8f9fa;font-weight:bold;">Reviewer</td>
                    <td style="padding:8px;">{review.reviewer_name}</td>
                </tr>
                <tr>
                    <td style="padding:8px;background:#f8f9fa;font-weight:bold;">Rating</td>
                    <td style="padding:8px;">{stars} ({review.rating}/5)</td>
                </tr>
                <tr>
                    <td style="padding:8px;background:#f8f9fa;font-weight:bold;">Date</td>
                    <td style="padding:8px;">{review.review_date.strftime("%B %d, %Y")}</td>
                </tr>
            </table>

            <div style="background:#f8f9fa;padding:16px;border-left:4px solid #6c757d;
                        border-radius:4px;margin-bottom:16px;font-style:italic;">
                "{review_text}"
            </div>

            {action_section}

            <p style="color:#6c757d;font-size:12px;margin-top:24px;">
                You're receiving this because you're the owner of {settings.business_name}.
                Manage your review alerts at
                <a href="{settings.app_base_url}">{settings.app_base_url}</a>
            </p>
        </div>
    </body>
    </html>
    """

    plain_body = (
        f"{settings.business_name} — New {platform_name} Review\n"
        f"{'=' * 50}\n\n"
        f"Platform: {platform_name}\n"
        f"Reviewer: {review.reviewer_name}\n"
        f"Rating: {review.rating}/5 stars\n"
        f"Date: {review.review_date.strftime('%B %d, %Y')}\n\n"
        f'Review:\n"{review_text}"\n'
        f"{plain_action}\n"
    )

    return subject, html_body, plain_body


def send_new_review_notification(review: Review) -> tuple[bool, str | None]:
    """
    Send an email notification for a new review.

    Returns (success: bool, error_message: str | None).
    """
    if not settings.smtp_username or not settings.smtp_password:
        print("[Notifier] SMTP not configured — skipping email notification")
        return False, "SMTP not configured"

    try:
        subject, html_body, plain_body = _build_new_review_email(review)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from_email or settings.smtp_username
        msg["To"] = settings.business_owner_email

        msg.attach(MIMEText(plain_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            if settings.smtp_use_tls:
                server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
            server.sendmail(
                settings.smtp_from_email or settings.smtp_username,
                settings.business_owner_email,
                msg.as_string(),
            )

        print(
            f"[Notifier] Email sent for review #{review.id} "
            f"({review.rating}★ from {review.reviewer_name})"
        )
        return True, None

    except Exception as e:
        error = str(e)
        print(f"[Notifier] Failed to send email for review #{review.id}: {error}")
        return False, error
