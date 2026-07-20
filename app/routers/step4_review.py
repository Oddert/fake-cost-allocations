"""
Step 4 – Review, Visualisation Data, and Submission.

Provides read-only aggregated views of a period's allocation state,
a validation check, and the final submit action.

Submission:
 - Runs a preflight validation (all expenses assigned, all activities distributed,
   all activities labelled).
 - Computes a SHA-256 checksum of the serialised allocation for audit purposes.
 - Marks the period status as 'submitted'.
 - Only admin users can submit.

Roles:
  - analyst+ : read review data, run validation
  - admin    : submit
"""

import hashlib
import json
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app import auth, db
from app.schemas import (
    ActivityBreakdownItem,
    CostCentreRollup,
    Distribution,
    PeriodReviewSummary,
    Submission,
    SubmissionCreate,
)

router = APIRouter(tags=["Step 4 – Review & Submit"])

_PCT_THRESHOLD = Decimal("99.99")   # treat anything ≥ this as "fully allocated"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _tags_for(activity_id: int) -> list[str]:
    label = db.find_one(db.labels, activity_id=activity_id)
    if not label or not label.get("tags"):
        return []
    return [t for t in label["tags"].split("|") if t]


def _label_field(activity_id: int, field: str):
    label = db.find_one(db.labels, activity_id=activity_id)
    return label.get(field) if label else None


def _activity_allocated_amount(activity_id: int, period_id: int) -> tuple[Decimal, str]:
    """
    Sum the expense amounts attributed to an activity across all assignments.
    Returns (total_amount, currency).  Multi-currency periods return 'MIXED'.
    """
    activities_assignments = db.find_many(db.assignments, activity_id=activity_id)
    total = Decimal("0.00")
    currencies: set[str] = set()
    for asn in activities_assignments:
        expense = db.expenses.get(asn["expense_id"])
        if expense and expense["period_id"] == period_id:
            total += expense["amount"] * asn["percentage"] / Decimal("100")
            currencies.add(expense["currency"])
    currency = currencies.pop() if len(currencies) == 1 else ("MIXED" if currencies else "GBP")
    return total.quantize(Decimal("0.01")), currency


def _build_cc_rollup(period_id: int) -> list[CostCentreRollup]:
    """
    Aggregate allocated amounts per cost centre (further broken down by legal entity).
    """
    # Map cost_centre_id -> legal_entity_id -> amount
    from collections import defaultdict
    cc_le: dict[int, dict[int, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    cc_currency: dict[int, set[str]] = defaultdict(set)

    activities = db.find_many(db.activities, period_id=period_id)
    for activity in activities:
        aid = activity["activity_id"]
        amount, currency = _activity_allocated_amount(aid, period_id)
        distributions = db.find_many(db.distributions, activity_id=aid)
        for dist in distributions:
            share = amount * dist["percentage"] / Decimal("100")
            cc_le[dist["cost_centre_id"]][dist["legal_entity_id"]] += share
            cc_currency[dist["cost_centre_id"]].add(currency)

    rollups = []
    for cc_id, le_map in cc_le.items():
        cc = db.cost_centres.get(cc_id)
        if not cc:
            continue
        curr_set = cc_currency[cc_id]
        currency = curr_set.pop() if len(curr_set) == 1 else "MIXED"
        total = sum(le_map.values()).quantize(Decimal("0.01"))
        by_le = [
            {
                "legal_entity_id": le_id,
                "legal_entity_code": (db.legal_entities.get(le_id) or {}).get("code"),
                "legal_entity_name": (db.legal_entities.get(le_id) or {}).get("name"),
                "amount": float(amt.quantize(Decimal("0.01"))),
                "currency": currency,
            }
            for le_id, amt in le_map.items()
        ]
        rollups.append(
            CostCentreRollup(
                cost_centre_id=cc_id,
                cost_centre_code=cc["code"],
                cost_centre_name=cc["name"],
                total_amount=total,
                currency=currency,
                by_legal_entity=by_le,
            )
        )
    return rollups


def _build_warnings(period_id: int) -> list[str]:
    warnings = []
    expenses = db.find_many(db.expenses, period_id=period_id)
    activities = db.find_many(db.activities, period_id=period_id)

    # Expenses not at 100%
    for exp in expenses:
        eid = exp["expense_id"]
        total = sum(
            a["percentage"] for a in db.find_many(db.assignments, expense_id=eid)
        )
        if total < _PCT_THRESHOLD:
            warnings.append(
                f"Expense '{exp['description']}' (id={eid}) is only {total}% assigned."
            )

    # Activities not at 100% distributed
    for act in activities:
        aid = act["activity_id"]
        total = sum(
            d["percentage"] for d in db.find_many(db.distributions, activity_id=aid)
        )
        if total < _PCT_THRESHOLD:
            warnings.append(
                f"Activity '{act['name']}' (id={aid}) is only {total}% distributed."
            )

    # Unlabelled activities
    labelled_ids = {r["activity_id"] for r in db.labels.values()}
    for act in activities:
        if act["activity_id"] not in labelled_ids:
            warnings.append(
                f"Activity '{act['name']}' (id={act['activity_id']}) has no classification label."
            )

    return warnings


def _compute_checksum(period_id: int) -> str:
    """SHA-256 of a deterministic JSON snapshot of the period's allocation."""
    payload = {
        "period_id": period_id,
        "expenses": sorted(
            [
                {
                    "expense_id": e["expense_id"],
                    "amount": str(e["amount"]),
                    "assignments": sorted(
                        [
                            {"activity_id": a["activity_id"], "pct": str(a["percentage"])}
                            for a in db.find_many(db.assignments, expense_id=e["expense_id"])
                        ],
                        key=lambda x: x["activity_id"],
                    ),
                }
                for e in db.find_many(db.expenses, period_id=period_id)
            ],
            key=lambda x: x["expense_id"],
        ),
        "distributions": sorted(
            [
                {
                    "activity_id": d["activity_id"],
                    "cost_centre_id": d["cost_centre_id"],
                    "legal_entity_id": d["legal_entity_id"],
                    "pct": str(d["percentage"]),
                }
                for d in db.distributions.values()
                if db.activities.get(d["activity_id"], {}).get("period_id") == period_id
            ],
            key=lambda x: (x["activity_id"], x["cost_centre_id"], x["legal_entity_id"]),
        ),
    }
    serialised = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(serialised.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/periods/{period_id}/review",
    response_model=PeriodReviewSummary,
    summary="Full review summary of a period's allocation state",
)
def get_review(
    period_id: int,
    _user: Annotated[dict, Depends(auth.require_viewer)] = None,
):
    period = db.periods.get(period_id)
    if not period:
        raise HTTPException(404, "Period not found")

    expenses = db.find_many(db.expenses, period_id=period_id)
    activities = db.find_many(db.activities, period_id=period_id)

    total_expenses = sum(e["amount"] for e in expenses) if expenses else Decimal("0")

    # Overall assignment percentage (weighted average across all expenses)
    total_assigned_pct = Decimal("0.00")
    if expenses:
        assigned_sum = Decimal("0.00")
        exp_total = sum(e["amount"] for e in expenses)
        for exp in expenses:
            pct = sum(
                a["percentage"]
                for a in db.find_many(db.assignments, expense_id=exp["expense_id"])
            )
            assigned_sum += exp["amount"] * pct / Decimal("100")
        total_assigned_pct = (
            (assigned_sum / exp_total * Decimal("100")).quantize(Decimal("0.01"))
            if exp_total else Decimal("0.00")
        )

    # Build activity breakdown items
    breakdown = []
    for act in activities:
        aid = act["activity_id"]
        amount, currency = _activity_allocated_amount(aid, period_id)
        dists = db.find_many(db.distributions, activity_id=aid)
        breakdown.append(
            ActivityBreakdownItem(
                activity_id=aid,
                activity_name=act["name"],
                category=_label_field(aid, "category"),
                sub_category=_label_field(aid, "sub_category"),
                tags=_tags_for(aid),
                total_allocated_amount=amount,
                currency=currency,
                distributions=[Distribution(**d) for d in dists],
            )
        )

    return PeriodReviewSummary(
        period_id=period_id,
        period_name=period["name"],
        mode=period["mode"],
        status=period["status"],
        fiscal_year=period["fiscal_year"],
        fiscal_month=period["fiscal_month"],
        total_expenses=total_expenses.quantize(Decimal("0.01")),
        total_assigned_pct=total_assigned_pct,
        activities=breakdown,
        cost_centre_rollup=_build_cc_rollup(period_id),
        warnings=_build_warnings(period_id),
    )


@router.get(
    "/periods/{period_id}/review/validate",
    summary="Validate a period is ready to submit — returns errors if not",
)
def validate_period(
    period_id: int,
    _user: Annotated[dict, Depends(auth.require_analyst)] = None,
) -> dict:
    period = db.periods.get(period_id)
    if not period:
        raise HTTPException(404, "Period not found")
    warnings = _build_warnings(period_id)
    return {
        "period_id": period_id,
        "ready": len(warnings) == 0,
        "warnings": warnings,
    }


@router.post(
    "/periods/{period_id}/submit",
    response_model=Submission,
    status_code=201,
    summary="Submit a period (admin only) — locks it and records an audit checksum",
)
def submit_period(
    period_id: int,
    body: SubmissionCreate,
    user: Annotated[dict, Depends(auth.require_admin)],
):
    period = db.periods.get(period_id)
    if not period:
        raise HTTPException(404, "Period not found")
    if period["status"] == "submitted":
        raise HTTPException(400, "Period has already been submitted")
    if period["status"] == "open":
        # Auto-lock on submission
        period["status"] = "locked"
        period["locked_at"] = db.utcnow()

    # Run validation
    warnings = _build_warnings(period_id)
    if warnings:
        raise HTTPException(
            422,
            {
                "detail": "Period has unresolved issues. Resolve them before submitting.",
                "warnings": warnings,
            },
        )

    # Check no duplicate submission
    if db.find_one(db.submissions, period_id=period_id):
        raise HTTPException(400, "A submission record already exists for this period")

    checksum = _compute_checksum(period_id)
    sid = db.seq_submissions.nextval()
    now = db.utcnow()
    row = {
        "submission_id": sid,
        "period_id": period_id,
        "submitted_by": user["user_id"],
        "submitted_at": now,
        "notes": body.notes,
        "checksum": checksum,
    }
    db.submissions[sid] = row
    period["status"] = "submitted"

    return Submission(**row)


@router.get(
    "/periods/{period_id}/submission",
    response_model=Submission,
    summary="Get the submission record for a period",
)
def get_submission(
    period_id: int,
    _user: Annotated[dict, Depends(auth.require_viewer)] = None,
):
    if not db.periods.get(period_id):
        raise HTTPException(404, "Period not found")
    row = db.find_one(db.submissions, period_id=period_id)
    if not row:
        raise HTTPException(404, "Period has not been submitted yet")
    return Submission(**row)
