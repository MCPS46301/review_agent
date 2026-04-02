from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import String, Integer, Float, Text, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class Platform(str, PyEnum):
    GOOGLE = "google"
    FACEBOOK = "facebook"
    YELP = "yelp"


class ReviewStatus(str, PyEnum):
    NEW = "new"               # Just fetched, AI response being generated
    PENDING_APPROVAL = "pending_approval"  # 1-2 stars, awaiting owner review
    APPROVED = "approved"     # Owner approved response (1-2 stars)
    RESPONDED = "responded"   # Response has been posted
    DISMISSED = "dismissed"   # Owner chose not to respond


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    platform: Mapped[str] = mapped_column(Enum(Platform), nullable=False)
    platform_review_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    reviewer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    reviewer_avatar: Mapped[str | None] = mapped_column(String(500), nullable=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5
    review_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(ReviewStatus), default=ReviewStatus.NEW, nullable=False
    )
    platform_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    response: Mapped["ReviewResponse | None"] = relationship(
        "ReviewResponse", back_populates="review", uselist=False
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification", back_populates="review"
    )

    @property
    def requires_approval(self) -> bool:
        return self.rating <= 2

    @property
    def star_display(self) -> str:
        return "★" * self.rating + "☆" * (5 - self.rating)

    @property
    def platform_badge_color(self) -> str:
        colors = {
            Platform.GOOGLE: "bg-blue-100 text-blue-800",
            Platform.FACEBOOK: "bg-indigo-100 text-indigo-800",
            Platform.YELP: "bg-red-100 text-red-800",
        }
        return colors.get(self.platform, "bg-gray-100 text-gray-800")

    @property
    def rating_color(self) -> str:
        if self.rating <= 2:
            return "text-red-600"
        elif self.rating == 3:
            return "text-yellow-600"
        return "text-green-600"


class ReviewResponse(Base):
    __tablename__ = "review_responses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    review_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("reviews.id"), unique=True, nullable=False
    )
    draft_text: Mapped[str] = mapped_column(Text, nullable=False)
    final_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    send_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    review: Mapped["Review"] = relationship("Review", back_populates="response")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    review_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("reviews.id"), nullable=False
    )
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    review: Mapped["Review"] = relationship("Review", back_populates="notifications")
