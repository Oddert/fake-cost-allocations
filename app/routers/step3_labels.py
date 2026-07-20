"""
Step 3 – Activity Classification / Labelling.

Each activity can have exactly one Label record (upsert semantics).
Labels carry a category, sub-category, free-form tags, and notes.
These are used downstream for reporting groupings and analysis.

Roles:
  - analyst+ : create / update / delete
  - viewer   : read
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app import auth, db
from app.schemas import Label, LabelUpsert

router = APIRouter(tags=["Step 3 – Labels"])


def _get_activity(period_id: int, activity_id: int) -> dict:
    period = db.periods.get(period_id)
    if not period:
        raise HTTPException(404, "Period not found")
    activity = db.activities.get(activity_id)
    if not activity or activity["period_id"] != period_id:
        raise HTTPException(404, "Activity not found in this period")
    return activity


def _get_open_activity(period_id: int, activity_id: int) -> dict:
    activity = _get_activity(period_id, activity_id)
    period = db.periods.get(period_id)
    if period["status"] != "open":
        raise HTTPException(400, "Period is not open – labels cannot be modified")
    return activity


def _row_to_label(row: dict) -> Label:
    # Tags stored pipe-separated in the DB (Oracle VARCHAR2 column)
    tags_raw = row.get("tags") or ""
    tags = [t for t in tags_raw.split("|") if t]
    return Label(
        label_id=row["label_id"],
        activity_id=row["activity_id"],
        category=row.get("category"),
        sub_category=row.get("sub_category"),
        tags=tags,
        notes=row.get("notes"),
        created_by=row["created_by"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.put(
    "/periods/{period_id}/activities/{activity_id}/label",
    response_model=Label,
    summary="Create or replace the classification label for an activity (analyst+)",
)
def upsert_label(
    period_id: int,
    activity_id: int,
    body: LabelUpsert,
    user: Annotated[dict, Depends(auth.require_analyst)],
):
    _get_open_activity(period_id, activity_id)
    now = db.utcnow()
    tags_str = "|".join(body.tags)

    existing = db.find_one(db.labels, activity_id=activity_id)
    if existing:
        existing["category"] = body.category
        existing["sub_category"] = body.sub_category
        existing["tags"] = tags_str
        existing["notes"] = body.notes
        existing["updated_at"] = now
        return _row_to_label(existing)
    else:
        lid = db.seq_labels.nextval()
        row = {
            "label_id": lid,
            "activity_id": activity_id,
            "category": body.category,
            "sub_category": body.sub_category,
            "tags": tags_str,
            "notes": body.notes,
            "created_by": user["user_id"],
            "created_at": now,
            "updated_at": now,
        }
        db.labels[lid] = row
        return _row_to_label(row)


@router.get(
    "/periods/{period_id}/activities/{activity_id}/label",
    response_model=Label,
    summary="Get the classification label for an activity",
)
def get_label(
    period_id: int,
    activity_id: int,
    _user: Annotated[dict, Depends(auth.require_viewer)] = None,
):
    _get_activity(period_id, activity_id)
    row = db.find_one(db.labels, activity_id=activity_id)
    if not row:
        raise HTTPException(404, "No label set for this activity")
    return _row_to_label(row)


@router.delete(
    "/periods/{period_id}/activities/{activity_id}/label",
    status_code=204,
    summary="Remove the classification label for an activity (analyst+, open period)",
)
def delete_label(
    period_id: int,
    activity_id: int,
    _user: Annotated[dict, Depends(auth.require_analyst)],
):
    _get_open_activity(period_id, activity_id)
    row = db.find_one(db.labels, activity_id=activity_id)
    if not row:
        raise HTTPException(404, "No label set for this activity")
    del db.labels[row["label_id"]]


@router.get(
    "/periods/{period_id}/labels",
    response_model=list[Label],
    summary="List all activity labels in a period",
)
def list_period_labels(
    period_id: int,
    category: str | None = None,
    tag: str | None = None,
    _user: Annotated[dict, Depends(auth.require_viewer)] = None,
):
    if not db.periods.get(period_id):
        raise HTTPException(404, "Period not found")

    activity_ids = {
        a["activity_id"]
        for a in db.find_many(db.activities, period_id=period_id)
    }
    rows = [r for r in db.labels.values() if r["activity_id"] in activity_ids]

    if category:
        rows = [r for r in rows if (r.get("category") or "").lower() == category.lower()]
    if tag:
        rows = [r for r in rows if tag.lower() in (r.get("tags") or "").lower().split("|")]

    return [_row_to_label(r) for r in rows]


@router.get(
    "/periods/{period_id}/labels/completeness",
    summary="Check which activities are missing labels",
)
def label_completeness(
    period_id: int,
    _user: Annotated[dict, Depends(auth.require_viewer)] = None,
) -> dict:
    if not db.periods.get(period_id):
        raise HTTPException(404, "Period not found")

    activities = db.find_many(db.activities, period_id=period_id)
    labelled_ids = {
        r["activity_id"]
        for r in db.labels.values()
        if r["activity_id"] in {a["activity_id"] for a in activities}
    }

    unlabelled = [
        {"activity_id": a["activity_id"], "name": a["name"]}
        for a in activities
        if a["activity_id"] not in labelled_ids
    ]

    return {
        "total_activities": len(activities),
        "labelled": len(labelled_ids),
        "unlabelled": len(unlabelled),
        "unlabelled_activities": unlabelled,
    }
