"""
Step 1 – Expense-to-Activity Assignments.

The user decides what percentage of each expense belongs to each activity.
Assignments are percentage-based; all assignments for one expense should total 100%
(the API warns if they don't, but does not hard-block to allow incremental saving).

Roles:
  - analyst+ : create / update / delete
  - viewer   : read
"""

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app import auth, db
from app.schemas import Assignment, AssignmentCreate, AssignmentSummary, AssignmentUpdate

router = APIRouter(tags=["Step 1 – Assignments"])

_PCT_TOLERANCE = Decimal("0.01")  # rounding grace margin


def _get_open_expense(period_id: int, expense_id: int) -> dict:
    period = db.periods.get(period_id)
    if not period:
        raise HTTPException(404, "Period not found")
    if period["status"] != "open":
        raise HTTPException(400, "Period is not open – assignments cannot be modified")
    expense = db.expenses.get(expense_id)
    if not expense or expense["period_id"] != period_id:
        raise HTTPException(404, "Expense not found in this period")
    return expense


def _check_activity_in_period(activity_id: int, period_id: int) -> dict:
    activity = db.activities.get(activity_id)
    if not activity or activity["period_id"] != period_id:
        raise HTTPException(400, "Activity does not belong to this period")
    return activity


def _total_pct(expense_id: int) -> Decimal:
    return sum(
        a["percentage"]
        for a in db.find_many(db.assignments, expense_id=expense_id)
    )


def _build_response(row: dict) -> Assignment:
    return Assignment(**row)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/periods/{period_id}/expenses/{expense_id}/assignments",
    response_model=Assignment,
    status_code=201,
    summary="Assign a percentage of an expense to an activity",
)
def create_assignment(
    period_id: int,
    expense_id: int,
    body: AssignmentCreate,
    user: Annotated[dict, Depends(auth.require_analyst)],
):
    _get_open_expense(period_id, expense_id)
    _check_activity_in_period(body.activity_id, period_id)

    # Enforce uniqueness: one row per (expense, activity)
    if db.find_one(db.assignments, expense_id=expense_id, activity_id=body.activity_id):
        raise HTTPException(
            400, "Assignment for this expense/activity pair already exists. Use PATCH to update."
        )

    # Prevent exceeding 100% for the expense
    current_total = _total_pct(expense_id)
    if current_total + body.percentage > Decimal("100") + _PCT_TOLERANCE:
        raise HTTPException(
            400,
            f"Adding {body.percentage}% would exceed 100% "
            f"(currently at {current_total}% for this expense)",
        )

    aid = db.seq_assignments.nextval()
    row = {
        "assignment_id": aid,
        "expense_id": expense_id,
        "activity_id": body.activity_id,
        "percentage": body.percentage,
        "created_by": user["user_id"],
        "created_at": db.utcnow(),
    }
    db.assignments[aid] = row
    return _build_response(row)


@router.get(
    "/periods/{period_id}/expenses/{expense_id}/assignments",
    response_model=AssignmentSummary,
    summary="Get all assignments for an expense, with totals",
)
def list_assignments(
    period_id: int,
    expense_id: int,
    _user: Annotated[dict, Depends(auth.require_viewer)] = None,
):
    period = db.periods.get(period_id)
    if not period:
        raise HTTPException(404, "Period not found")
    expense = db.expenses.get(expense_id)
    if not expense or expense["period_id"] != period_id:
        raise HTTPException(404, "Expense not found in this period")

    rows = db.find_many(db.assignments, expense_id=expense_id)
    total = sum(r["percentage"] for r in rows) if rows else Decimal("0")

    return AssignmentSummary(
        expense_id=expense_id,
        description=expense["description"],
        amount=expense["amount"],
        currency=expense["currency"],
        total_assigned_pct=total,
        assignments=[_build_response(r) for r in rows],
    )


@router.patch(
    "/periods/{period_id}/expenses/{expense_id}/assignments/{assignment_id}",
    response_model=Assignment,
    summary="Update the percentage on an assignment",
)
def update_assignment(
    period_id: int,
    expense_id: int,
    assignment_id: int,
    body: AssignmentUpdate,
    _user: Annotated[dict, Depends(auth.require_analyst)],
):
    _get_open_expense(period_id, expense_id)
    row = db.assignments.get(assignment_id)
    if not row or row["expense_id"] != expense_id:
        raise HTTPException(404, "Assignment not found")

    # Recalculate ceiling excluding this assignment's current value
    other_total = _total_pct(expense_id) - row["percentage"]
    if other_total + body.percentage > Decimal("100") + _PCT_TOLERANCE:
        raise HTTPException(
            400,
            f"Updating to {body.percentage}% would push total beyond 100% "
            f"(other assignments sum to {other_total}%)",
        )

    row["percentage"] = body.percentage
    return _build_response(row)


@router.delete(
    "/periods/{period_id}/expenses/{expense_id}/assignments/{assignment_id}",
    status_code=204,
    summary="Remove an assignment (analyst+, open period)",
)
def delete_assignment(
    period_id: int,
    expense_id: int,
    assignment_id: int,
    _user: Annotated[dict, Depends(auth.require_analyst)],
):
    _get_open_expense(period_id, expense_id)
    row = db.assignments.get(assignment_id)
    if not row or row["expense_id"] != expense_id:
        raise HTTPException(404, "Assignment not found")
    del db.assignments[assignment_id]


@router.get(
    "/periods/{period_id}/assignments/summary",
    response_model=list[AssignmentSummary],
    summary="Summary of all expense assignments in a period",
)
def period_assignment_summary(
    period_id: int,
    _user: Annotated[dict, Depends(auth.require_viewer)] = None,
):
    """
    Returns one AssignmentSummary per expense, useful for identifying
    expenses that are under- or over-assigned.
    """
    if not db.periods.get(period_id):
        raise HTTPException(404, "Period not found")
    expenses = db.find_many(db.expenses, period_id=period_id)
    result = []
    for expense in expenses:
        eid = expense["expense_id"]
        rows = db.find_many(db.assignments, expense_id=eid)
        total = sum(r["percentage"] for r in rows) if rows else Decimal("0")
        result.append(
            AssignmentSummary(
                expense_id=eid,
                description=expense["description"],
                amount=expense["amount"],
                currency=expense["currency"],
                total_assigned_pct=total,
                assignments=[_build_response(r) for r in rows],
            )
        )
    return result
