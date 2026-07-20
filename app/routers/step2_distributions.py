"""
Step 2 – Activity Distributions.

The user decides how each activity's cost should be shared across different parts
of the business, broken down by Legal Entity within a Cost Centre.

Each (activity_id, cost_centre_id, legal_entity_id) triplet is unique.
Percentages for one activity should total 100% across all distributions.

Roles:
  - analyst+ : create / update / delete
  - viewer   : read
"""

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app import auth, db
from app.schemas import Distribution, DistributionCreate, DistributionSummary, DistributionUpdate

router = APIRouter(tags=["Step 2 – Distributions"])

_PCT_TOLERANCE = Decimal("0.01")


def _get_open_activity(period_id: int, activity_id: int) -> dict:
    period = db.periods.get(period_id)
    if not period:
        raise HTTPException(404, "Period not found")
    if period["status"] != "open":
        raise HTTPException(400, "Period is not open – distributions cannot be modified")
    activity = db.activities.get(activity_id)
    if not activity or activity["period_id"] != period_id:
        raise HTTPException(404, "Activity not found in this period")
    return activity


def _total_pct(activity_id: int) -> Decimal:
    return sum(
        d["percentage"]
        for d in db.find_many(db.distributions, activity_id=activity_id)
    )


def _build_response(row: dict) -> Distribution:
    return Distribution(**row)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/periods/{period_id}/activities/{activity_id}/distributions",
    response_model=Distribution,
    status_code=201,
    summary="Add a distribution slice for an activity",
)
def create_distribution(
    period_id: int,
    activity_id: int,
    body: DistributionCreate,
    user: Annotated[dict, Depends(auth.require_analyst)],
):
    _get_open_activity(period_id, activity_id)

    if not db.cost_centres.get(body.cost_centre_id):
        raise HTTPException(400, "Cost centre not found")
    if not db.legal_entities.get(body.legal_entity_id):
        raise HTTPException(400, "Legal entity not found")

    # Uniqueness: one row per (activity, cost_centre, legal_entity)
    if db.find_one(
        db.distributions,
        activity_id=activity_id,
        cost_centre_id=body.cost_centre_id,
        legal_entity_id=body.legal_entity_id,
    ):
        raise HTTPException(
            400,
            "Distribution for this activity/cost-centre/legal-entity already exists. "
            "Use PATCH to update.",
        )

    # Ceiling guard
    current_total = _total_pct(activity_id)
    if current_total + body.percentage > Decimal("100") + _PCT_TOLERANCE:
        raise HTTPException(
            400,
            f"Adding {body.percentage}% would exceed 100% "
            f"(currently at {current_total}% for this activity)",
        )

    did = db.seq_distributions.nextval()
    row = {
        "distribution_id": did,
        "activity_id": activity_id,
        "cost_centre_id": body.cost_centre_id,
        "legal_entity_id": body.legal_entity_id,
        "percentage": body.percentage,
        "created_by": user["user_id"],
        "created_at": db.utcnow(),
    }
    db.distributions[did] = row
    return _build_response(row)


@router.get(
    "/periods/{period_id}/activities/{activity_id}/distributions",
    response_model=DistributionSummary,
    summary="Get all distributions for an activity with totals",
)
def list_distributions(
    period_id: int,
    activity_id: int,
    _user: Annotated[dict, Depends(auth.require_viewer)] = None,
):
    period = db.periods.get(period_id)
    if not period:
        raise HTTPException(404, "Period not found")
    activity = db.activities.get(activity_id)
    if not activity or activity["period_id"] != period_id:
        raise HTTPException(404, "Activity not found in this period")

    rows = db.find_many(db.distributions, activity_id=activity_id)
    total = sum(r["percentage"] for r in rows) if rows else Decimal("0")

    return DistributionSummary(
        activity_id=activity_id,
        name=activity["name"],
        total_distributed_pct=total,
        distributions=[_build_response(r) for r in rows],
    )


@router.patch(
    "/periods/{period_id}/activities/{activity_id}/distributions/{distribution_id}",
    response_model=Distribution,
    summary="Update the percentage on a distribution",
)
def update_distribution(
    period_id: int,
    activity_id: int,
    distribution_id: int,
    body: DistributionUpdate,
    _user: Annotated[dict, Depends(auth.require_analyst)],
):
    _get_open_activity(period_id, activity_id)
    row = db.distributions.get(distribution_id)
    if not row or row["activity_id"] != activity_id:
        raise HTTPException(404, "Distribution not found")

    other_total = _total_pct(activity_id) - row["percentage"]
    if other_total + body.percentage > Decimal("100") + _PCT_TOLERANCE:
        raise HTTPException(
            400,
            f"Updating to {body.percentage}% would exceed 100% "
            f"(other slices sum to {other_total}%)",
        )

    row["percentage"] = body.percentage
    return _build_response(row)


@router.delete(
    "/periods/{period_id}/activities/{activity_id}/distributions/{distribution_id}",
    status_code=204,
    summary="Remove a distribution slice (analyst+, open period)",
)
def delete_distribution(
    period_id: int,
    activity_id: int,
    distribution_id: int,
    _user: Annotated[dict, Depends(auth.require_analyst)],
):
    _get_open_activity(period_id, activity_id)
    row = db.distributions.get(distribution_id)
    if not row or row["activity_id"] != activity_id:
        raise HTTPException(404, "Distribution not found")
    del db.distributions[distribution_id]


@router.get(
    "/periods/{period_id}/distributions/summary",
    response_model=list[DistributionSummary],
    summary="Summary of all activity distributions in a period",
)
def period_distribution_summary(
    period_id: int,
    _user: Annotated[dict, Depends(auth.require_viewer)] = None,
):
    """Returns one DistributionSummary per activity; useful to spot activities
    that have not yet been fully distributed."""
    if not db.periods.get(period_id):
        raise HTTPException(404, "Period not found")

    activities = db.find_many(db.activities, period_id=period_id)
    result = []
    for activity in activities:
        aid = activity["activity_id"]
        rows = db.find_many(db.distributions, activity_id=aid)
        total = sum(r["percentage"] for r in rows) if rows else Decimal("0")
        result.append(
            DistributionSummary(
                activity_id=aid,
                name=activity["name"],
                total_distributed_pct=total,
                distributions=[_build_response(r) for r in rows],
            )
        )
    return result
