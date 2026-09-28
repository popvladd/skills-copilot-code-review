"""
Announcement endpoints for the High School Management System API
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, field_validator

from ..database import announcements_collection, teachers_collection

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)

MAX_TITLE_LENGTH = 120
MAX_MESSAGE_LENGTH = 1000


class AnnouncementPayload(BaseModel):
    """Data required to create or update an announcement"""

    title: str
    message: str
    expiration_date: datetime
    start_date: Optional[datetime] = None

    @field_validator("title", "message")
    @classmethod
    def not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Value cannot be empty")
        return cleaned

    @field_validator("title")
    @classmethod
    def title_length(cls, value: str) -> str:
        if len(value) > MAX_TITLE_LENGTH:
            raise ValueError("Title is too long")
        return value

    @field_validator("message")
    @classmethod
    def message_length(cls, value: str) -> str:
        if len(value) > MAX_MESSAGE_LENGTH:
            raise ValueError("Message is too long")
        return value


def _as_utc(value: Optional[datetime]) -> Optional[datetime]:
    """Normalize a datetime to timezone-aware UTC"""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _require_teacher(teacher_username: Optional[str]) -> Dict[str, Any]:
    """Validate that the request comes from a known teacher account"""
    if not teacher_username:
        raise HTTPException(
            status_code=401, detail="Authentication required for this action")

    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(
            status_code=401, detail="Invalid teacher credentials")

    return teacher


def _serialize(announcement: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a stored announcement into an API friendly dictionary"""
    start_date = _as_utc(announcement.get("start_date"))
    expiration_date = _as_utc(announcement.get("expiration_date"))

    return {
        "id": announcement["_id"],
        "title": announcement.get("title", ""),
        "message": announcement.get("message", ""),
        "start_date": start_date.isoformat() if start_date else None,
        "expiration_date": expiration_date.isoformat() if expiration_date else None,
        "created_by": announcement.get("created_by"),
    }


def _validate_dates(payload: AnnouncementPayload) -> Dict[str, Optional[datetime]]:
    """Ensure the start date comes before the expiration date"""
    start_date = _as_utc(payload.start_date)
    expiration_date = _as_utc(payload.expiration_date)

    if start_date and expiration_date and start_date >= expiration_date:
        raise HTTPException(
            status_code=400,
            detail="The start date must be before the expiration date")

    return {"start_date": start_date, "expiration_date": expiration_date}


@router.get("", response_model=List[Dict[str, Any]])
@router.get("/", response_model=List[Dict[str, Any]])
def get_active_announcements() -> List[Dict[str, Any]]:
    """
    Get all announcements that are currently visible.

    An announcement is visible when its optional start date has passed and its
    expiration date is still in the future.
    """
    now = datetime.now(timezone.utc)
    query = {
        "expiration_date": {"$gt": now},
        "$or": [
            {"start_date": None},
            {"start_date": {"$exists": False}},
            {"start_date": {"$lte": now}},
        ],
    }

    announcements = announcements_collection.find(query).sort("expiration_date", 1)
    return [_serialize(announcement) for announcement in announcements]


@router.get("/all", response_model=List[Dict[str, Any]])
def get_all_announcements(
    teacher_username: Optional[str] = Query(None)
) -> List[Dict[str, Any]]:
    """Get every announcement, including expired ones - requires teacher authentication"""
    _require_teacher(teacher_username)

    announcements = announcements_collection.find().sort("expiration_date", -1)
    return [_serialize(announcement) for announcement in announcements]


@router.post("", response_model=Dict[str, Any])
@router.post("/", response_model=Dict[str, Any])
def create_announcement(
    payload: AnnouncementPayload,
    teacher_username: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Create a new announcement - requires teacher authentication"""
    teacher = _require_teacher(teacher_username)
    dates = _validate_dates(payload)

    announcement = {
        "_id": uuid.uuid4().hex,
        "title": payload.title,
        "message": payload.message,
        "start_date": dates["start_date"],
        "expiration_date": dates["expiration_date"],
        "created_by": teacher["_id"],
        "created_at": datetime.now(timezone.utc),
    }

    try:
        announcements_collection.insert_one(announcement)
    except Exception:
        logger.exception("Failed to create announcement")
        raise HTTPException(
            status_code=500, detail="Failed to create announcement")

    return _serialize(announcement)


@router.put("/{announcement_id}", response_model=Dict[str, Any])
def update_announcement(
    announcement_id: str,
    payload: AnnouncementPayload,
    teacher_username: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Update an existing announcement - requires teacher authentication"""
    _require_teacher(teacher_username)
    dates = _validate_dates(payload)

    result = announcements_collection.update_one(
        {"_id": announcement_id},
        {"$set": {
            "title": payload.title,
            "message": payload.message,
            "start_date": dates["start_date"],
            "expiration_date": dates["expiration_date"],
            "updated_at": datetime.now(timezone.utc),
        }}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")

    announcement = announcements_collection.find_one({"_id": announcement_id})
    return _serialize(announcement)


@router.delete("/{announcement_id}")
def delete_announcement(
    announcement_id: str,
    teacher_username: Optional[str] = Query(None)
) -> Dict[str, str]:
    """Delete an announcement - requires teacher authentication"""
    _require_teacher(teacher_username)

    result = announcements_collection.delete_one({"_id": announcement_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")

    return {"message": "Announcement deleted"}
