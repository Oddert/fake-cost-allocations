"""
Reference data router: Cost Centres, Legal Entities, Periods, Expenses, Activities.

These are the foundational records that the workflow steps operate on.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app import auth, db
from app.schemas import (
    Activity, ActivityCreate, ActivityUpdate,
    CostCentre, CostCentreCreate, CostCentreUpdate,
    Expense, ExpenseCreate, ExpenseUpdate,
    LegalEntity, LegalEntityCreate, LegalEntityUpdate,
    Period, PeriodCreate, PeriodUpdate,
)

router = APIRouter(tags=["Reference Data"])


# ---------------------------------------------------------------------------
# Cost Centres
# ---------------------------------------------------------------------------

@router.post("/cost-centres", response_model=CostCentre, status_code=201,
             summary="Create a cost centre (admin)")
def create_cost_centre(
    body: CostCentreCreate,
    _user: Annotated[dict, Depends(auth.require_admin)],
):
    if db.find_one(db.cost_centres, code=body.code):
        raise HTTPException(400, "Cost centre code already exists")
    cid = db.seq_cost_centres.nextval()
    row = {"cost_centre_id": cid, "is_active": True, **body.model_dump()}
    db.cost_centres[cid] = row
    return CostCentre(**row)


@router.get("/cost-centres", response_model=list[CostCentre],
            summary="List cost centres")
def list_cost_centres(
    active_only: bool = True,
    _user: Annotated[dict, Depends(auth.require_viewer)] = None,
):
    rows = db.cost_centres.values()
    if active_only:
        rows = [r for r in rows if r["is_active"]]
    return [CostCentre(**r) for r in rows]


@router.get("/cost-centres/{cost_centre_id}", response_model=CostCentre,
            summary="Get a cost centre")
def get_cost_centre(
    cost_centre_id: int,
    _user: Annotated[dict, Depends(auth.require_viewer)] = None,
):
    row = db.cost_centres.get(cost_centre_id)
    if not row:
        raise HTTPException(404, "Cost centre not found")
    return CostCentre(**row)


@router.patch("/cost-centres/{cost_centre_id}", response_model=CostCentre,
              summary="Update a cost centre (admin)")
def update_cost_centre(
    cost_centre_id: int,
    body: CostCentreUpdate,
    _user: Annotated[dict, Depends(auth.require_admin)],
):
    row = db.cost_centres.get(cost_centre_id)
    if not row:
        raise HTTPException(404, "Cost centre not found")
    for field, value in body.model_dump(exclude_none=True).items():
        row[field] = value
    return CostCentre(**row)


# ---------------------------------------------------------------------------
# Legal Entities
# ---------------------------------------------------------------------------

@router.post("/legal-entities", response_model=LegalEntity, status_code=201,
             summary="Create a legal entity (admin)")
def create_legal_entity(
    body: LegalEntityCreate,
    _user: Annotated[dict, Depends(auth.require_admin)],
):
    if db.find_one(db.legal_entities, code=body.code):
        raise HTTPException(400, "Legal entity code already exists")
    eid = db.seq_legal_entities.nextval()
    row = {"legal_entity_id": eid, "is_active": True, **body.model_dump()}
    db.legal_entities[eid] = row
    return LegalEntity(**row)


@router.get("/legal-entities", response_model=list[LegalEntity],
            summary="List legal entities")
def list_legal_entities(
    active_only: bool = True,
    _user: Annotated[dict, Depends(auth.require_viewer)] = None,
):
    rows = db.legal_entities.values()
    if active_only:
        rows = [r for r in rows if r["is_active"]]
    return [LegalEntity(**r) for r in rows]


@router.get("/legal-entities/{legal_entity_id}", response_model=LegalEntity,
            summary="Get a legal entity")
def get_legal_entity(
    legal_entity_id: int,
    _user: Annotated[dict, Depends(auth.require_viewer)] = None,
):
    row = db.legal_entities.get(legal_entity_id)
    if not row:
        raise HTTPException(404, "Legal entity not found")
    return LegalEntity(**row)


@router.patch("/legal-entities/{legal_entity_id}", response_model=LegalEntity,
              summary="Update a legal entity (admin)")
def update_legal_entity(
    legal_entity_id: int,
    body: LegalEntityUpdate,
    _user: Annotated[dict, Depends(auth.require_admin)],
):
    row = db.legal_entities.get(legal_entity_id)
    if not row:
        raise HTTPException(404, "Legal entity not found")
    for field, value in body.model_dump(exclude_none=True).items():
        row[field] = value
    return LegalEntity(**row)


# ---------------------------------------------------------------------------
# Allocation Periods
# ---------------------------------------------------------------------------

@router.post("/periods", response_model=Period, status_code=201,
             summary="Create an allocation period (analyst+)")
def create_period(
    body: PeriodCreate,
    user: Annotated[dict, Depends(auth.require_analyst)],
):
    pid = db.seq_periods.nextval()
    row = {
        "period_id": pid,
        "status": "open",
        "created_by": user["user_id"],
        "created_at": db.utcnow(),
        "locked_at": None,
        **body.model_dump(),
    }
    db.periods[pid] = row
    return Period(**row)


@router.get("/periods", response_model=list[Period],
            summary="List allocation periods")
def list_periods(
    mode: str | None = None,
    status: str | None = None,
    fiscal_year: int | None = None,
    _user: Annotated[dict, Depends(auth.require_viewer)] = None,
):
    rows = list(db.periods.values())
    if mode:
        rows = [r for r in rows if r["mode"] == mode]
    if status:
        rows = [r for r in rows if r["status"] == status]
    if fiscal_year:
        rows = [r for r in rows if r["fiscal_year"] == fiscal_year]
    return [Period(**r) for r in rows]


@router.get("/periods/{period_id}", response_model=Period,
            summary="Get an allocation period")
def get_period(
    period_id: int,
    _user: Annotated[dict, Depends(auth.require_viewer)] = None,
):
    row = db.periods.get(period_id)
    if not row:
        raise HTTPException(404, "Period not found")
    return Period(**row)


@router.patch("/periods/{period_id}", response_model=Period,
              summary="Update period name/month (analyst+, period must be open)")
def update_period(
    period_id: int,
    body: PeriodUpdate,
    _user: Annotated[dict, Depends(auth.require_analyst)],
):
    row = db.periods.get(period_id)
    if not row:
        raise HTTPException(404, "Period not found")
    if row["status"] != "open":
        raise HTTPException(400, "Only open periods can be edited")
    for field, value in body.model_dump(exclude_none=True).items():
        row[field] = value
    return Period(**row)


@router.post("/periods/{period_id}/lock", response_model=Period,
             summary="Lock a period to prevent further editing (admin)")
def lock_period(
    period_id: int,
    _user: Annotated[dict, Depends(auth.require_admin)],
):
    row = db.periods.get(period_id)
    if not row:
        raise HTTPException(404, "Period not found")
    if row["status"] != "open":
        raise HTTPException(400, "Period is not open")
    row["status"] = "locked"
    row["locked_at"] = db.utcnow()
    return Period(**row)


# ---------------------------------------------------------------------------
# Expenses  (nested under a period)
# ---------------------------------------------------------------------------

def _get_open_period(period_id: int) -> dict:
    row = db.periods.get(period_id)
    if not row:
        raise HTTPException(404, "Period not found")
    if row["status"] != "open":
        raise HTTPException(400, "Period is not open – cannot modify expenses")
    return row


def _expense_with_pct(row: dict) -> Expense:
    from decimal import Decimal
    pct = sum(
        a["percentage"]
        for a in db.find_many(db.assignments, expense_id=row["expense_id"])
    )
    return Expense(**{**row, "assigned_pct": pct})


@router.post("/periods/{period_id}/expenses", response_model=Expense, status_code=201,
             summary="Add an expense to a period (analyst+)")
def create_expense(
    period_id: int,
    body: ExpenseCreate,
    user: Annotated[dict, Depends(auth.require_analyst)],
):
    _get_open_period(period_id)
    if not db.cost_centres.get(body.cost_centre_id):
        raise HTTPException(400, "Cost centre not found")
    eid = db.seq_expenses.nextval()
    row = {
        "expense_id": eid,
        "period_id": period_id,
        "created_by": user["user_id"],
        "created_at": db.utcnow(),
        **body.model_dump(),
    }
    db.expenses[eid] = row
    return _expense_with_pct(row)


@router.get("/periods/{period_id}/expenses", response_model=list[Expense],
            summary="List expenses for a period")
def list_expenses(
    period_id: int,
    cost_centre_id: int | None = None,
    _user: Annotated[dict, Depends(auth.require_viewer)] = None,
):
    if not db.periods.get(period_id):
        raise HTTPException(404, "Period not found")
    rows = db.find_many(db.expenses, period_id=period_id)
    if cost_centre_id:
        rows = [r for r in rows if r["cost_centre_id"] == cost_centre_id]
    return [_expense_with_pct(r) for r in rows]


@router.get("/periods/{period_id}/expenses/{expense_id}", response_model=Expense,
            summary="Get a single expense")
def get_expense(
    period_id: int,
    expense_id: int,
    _user: Annotated[dict, Depends(auth.require_viewer)] = None,
):
    row = db.expenses.get(expense_id)
    if not row or row["period_id"] != period_id:
        raise HTTPException(404, "Expense not found")
    return _expense_with_pct(row)


@router.patch("/periods/{period_id}/expenses/{expense_id}", response_model=Expense,
              summary="Update an expense (analyst+, open period)")
def update_expense(
    period_id: int,
    expense_id: int,
    body: ExpenseUpdate,
    _user: Annotated[dict, Depends(auth.require_analyst)],
):
    _get_open_period(period_id)
    row = db.expenses.get(expense_id)
    if not row or row["period_id"] != period_id:
        raise HTTPException(404, "Expense not found")
    for field, value in body.model_dump(exclude_none=True).items():
        row[field] = value
    return _expense_with_pct(row)


@router.delete("/periods/{period_id}/expenses/{expense_id}", status_code=204,
               summary="Delete an expense and its assignments (analyst+, open period)")
def delete_expense(
    period_id: int,
    expense_id: int,
    _user: Annotated[dict, Depends(auth.require_analyst)],
):
    _get_open_period(period_id)
    row = db.expenses.get(expense_id)
    if not row or row["period_id"] != period_id:
        raise HTTPException(404, "Expense not found")
    # Cascade-delete assignments (Oracle would use ON DELETE CASCADE)
    for aid, a in list(db.assignments.items()):
        if a["expense_id"] == expense_id:
            del db.assignments[aid]
    del db.expenses[expense_id]


# ---------------------------------------------------------------------------
# Activities  (nested under a period)
# ---------------------------------------------------------------------------

@router.post("/periods/{period_id}/activities", response_model=Activity, status_code=201,
             summary="Create an activity for a period (analyst+)")
def create_activity(
    period_id: int,
    body: ActivityCreate,
    user: Annotated[dict, Depends(auth.require_analyst)],
):
    _get_open_period(period_id)
    aid = db.seq_activities.nextval()
    row = {
        "activity_id": aid,
        "period_id": period_id,
        "created_by": user["user_id"],
        "created_at": db.utcnow(),
        **body.model_dump(),
    }
    db.activities[aid] = row
    return Activity(**row)


@router.get("/periods/{period_id}/activities", response_model=list[Activity],
            summary="List activities for a period")
def list_activities(
    period_id: int,
    _user: Annotated[dict, Depends(auth.require_viewer)] = None,
):
    if not db.periods.get(period_id):
        raise HTTPException(404, "Period not found")
    return [Activity(**r) for r in db.find_many(db.activities, period_id=period_id)]


@router.get("/periods/{period_id}/activities/{activity_id}", response_model=Activity,
            summary="Get an activity")
def get_activity(
    period_id: int,
    activity_id: int,
    _user: Annotated[dict, Depends(auth.require_viewer)] = None,
):
    row = db.activities.get(activity_id)
    if not row or row["period_id"] != period_id:
        raise HTTPException(404, "Activity not found")
    return Activity(**row)


@router.patch("/periods/{period_id}/activities/{activity_id}", response_model=Activity,
              summary="Update an activity (analyst+, open period)")
def update_activity(
    period_id: int,
    activity_id: int,
    body: ActivityUpdate,
    _user: Annotated[dict, Depends(auth.require_analyst)],
):
    _get_open_period(period_id)
    row = db.activities.get(activity_id)
    if not row or row["period_id"] != period_id:
        raise HTTPException(404, "Activity not found")
    for field, value in body.model_dump(exclude_none=True).items():
        row[field] = value
    return Activity(**row)


@router.delete("/periods/{period_id}/activities/{activity_id}", status_code=204,
               summary="Delete an activity and all related data (analyst+, open period)")
def delete_activity(
    period_id: int,
    activity_id: int,
    _user: Annotated[dict, Depends(auth.require_analyst)],
):
    _get_open_period(period_id)
    row = db.activities.get(activity_id)
    if not row or row["period_id"] != period_id:
        raise HTTPException(404, "Activity not found")
    # Cascade-delete assignments, distributions, labels
    for table in (db.assignments, db.distributions, db.labels):
        for rid, r in list(table.items()):
            if r.get("activity_id") == activity_id:
                del table[rid]
    del db.activities[activity_id]
