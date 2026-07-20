"""
Budget Mode endpoints.

Budget periods are allocation periods with mode='budget'.
These endpoints provide budget-specific planning views:

  GET  /budget/periods                  – list all budget periods
  GET  /budget/periods/{id}/summary     – full budget breakdown by cost centre / legal entity
  GET  /budget/periods/{id}/by-cost-centre/{cc_id}  – drill-down for one cost centre
  GET  /budget/compare                  – compare two budget periods side by side

All endpoints are read-only (viewer+). Actual data entry goes through the
standard /periods/* endpoints.
"""

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app import auth, db
from app.schemas import BudgetAllocationItem, BudgetSummary, CostCentreRollup
from app.routers.step4_review import (
    _activity_allocated_amount,
    _build_cc_rollup,
    _label_field,
    _tags_for,
)

router = APIRouter(prefix="/budget", tags=["Budget Mode"])


def _get_budget_period(period_id: int) -> dict:
    period = db.periods.get(period_id)
    if not period:
        raise HTTPException(404, "Period not found")
    if period["mode"] != "budget":
        raise HTTPException(400, "Period is not a budget period")
    return period


def _build_budget_allocations(period_id: int) -> list[BudgetAllocationItem]:
    """Expand all distributions into flat allocation rows."""
    items = []
    activities = db.find_many(db.activities, period_id=period_id)
    for act in activities:
        aid = act["activity_id"]
        amount, currency = _activity_allocated_amount(aid, period_id)
        distributions = db.find_many(db.distributions, activity_id=aid)
        for dist in distributions:
            share = (amount * dist["percentage"] / Decimal("100")).quantize(Decimal("0.01"))
            items.append(
                BudgetAllocationItem(
                    cost_centre_id=dist["cost_centre_id"],
                    legal_entity_id=dist["legal_entity_id"],
                    activity_id=aid,
                    activity_name=act["name"],
                    category=_label_field(aid, "category"),
                    allocated_amount=share,
                    currency=currency,
                )
            )
    return items


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/periods", summary="List all budget periods")
def list_budget_periods(
    fiscal_year: int | None = None,
    status: str | None = None,
    _user: Annotated[dict, Depends(auth.require_viewer)] = None,
) -> list[dict]:
    rows = [r for r in db.periods.values() if r["mode"] == "budget"]
    if fiscal_year:
        rows = [r for r in rows if r["fiscal_year"] == fiscal_year]
    if status:
        rows = [r for r in rows if r["status"] == status]
    return rows


@router.get(
    "/periods/{period_id}/summary",
    response_model=BudgetSummary,
    summary="Full budget summary: allocations broken down by cost centre and legal entity",
)
def budget_summary(
    period_id: int,
    _user: Annotated[dict, Depends(auth.require_viewer)] = None,
):
    period = _get_budget_period(period_id)
    expenses = db.find_many(db.expenses, period_id=period_id)
    currencies = {e["currency"] for e in expenses}
    currency = currencies.pop() if len(currencies) == 1 else ("MIXED" if currencies else "GBP")
    total = sum(e["amount"] for e in expenses) if expenses else Decimal("0")

    return BudgetSummary(
        period_id=period_id,
        period_name=period["name"],
        fiscal_year=period["fiscal_year"],
        fiscal_month=period["fiscal_month"],
        total_budget=total.quantize(Decimal("0.01")),
        currency=currency,
        by_cost_centre=_build_cc_rollup(period_id),
        allocations=_build_budget_allocations(period_id),
    )


@router.get(
    "/periods/{period_id}/by-cost-centre/{cost_centre_id}",
    summary="Budget allocations filtered to a single cost centre",
)
def budget_by_cost_centre(
    period_id: int,
    cost_centre_id: int,
    _user: Annotated[dict, Depends(auth.require_viewer)] = None,
) -> dict:
    period = _get_budget_period(period_id)
    cc = db.cost_centres.get(cost_centre_id)
    if not cc:
        raise HTTPException(404, "Cost centre not found")

    allocations = [
        a for a in _build_budget_allocations(period_id)
        if a.cost_centre_id == cost_centre_id
    ]
    total = sum(a.allocated_amount for a in allocations).quantize(Decimal("0.01"))
    currencies = {a.currency for a in allocations}
    currency = currencies.pop() if len(currencies) == 1 else ("MIXED" if currencies else "GBP")

    # Group by legal entity
    from collections import defaultdict
    by_le: dict[int, Decimal] = defaultdict(Decimal)
    for a in allocations:
        by_le[a.legal_entity_id] += a.allocated_amount

    return {
        "period_id": period_id,
        "period_name": period["name"],
        "cost_centre_id": cost_centre_id,
        "cost_centre_code": cc["code"],
        "cost_centre_name": cc["name"],
        "total_amount": float(total),
        "currency": currency,
        "by_legal_entity": [
            {
                "legal_entity_id": le_id,
                "legal_entity_code": (db.legal_entities.get(le_id) or {}).get("code"),
                "legal_entity_name": (db.legal_entities.get(le_id) or {}).get("name"),
                "amount": float(amt.quantize(Decimal("0.01"))),
                "currency": currency,
            }
            for le_id, amt in by_le.items()
        ],
        "allocations": [a.model_dump() for a in allocations],
    }


@router.get(
    "/compare",
    summary="Compare two budget periods side by side",
)
def compare_budget_periods(
    period_a: int = Query(..., description="First budget period ID"),
    period_b: int = Query(..., description="Second budget period ID"),
    _user: Annotated[dict, Depends(auth.require_viewer)] = None,
) -> dict:
    pa = _get_budget_period(period_a)
    pb = _get_budget_period(period_b)

    def _cc_totals(period_id: int) -> dict[int, Decimal]:
        from collections import defaultdict
        totals: dict[int, Decimal] = defaultdict(Decimal)
        for item in _build_budget_allocations(period_id):
            totals[item.cost_centre_id] += item.allocated_amount
        return totals

    totals_a = _cc_totals(period_a)
    totals_b = _cc_totals(period_b)
    all_cc_ids = set(totals_a) | set(totals_b)

    comparison = []
    for cc_id in sorted(all_cc_ids):
        cc = db.cost_centres.get(cc_id) or {}
        amt_a = totals_a.get(cc_id, Decimal("0"))
        amt_b = totals_b.get(cc_id, Decimal("0"))
        variance = (amt_b - amt_a).quantize(Decimal("0.01"))
        pct_change = (
            float(variance / amt_a * 100) if amt_a else None
        )
        comparison.append({
            "cost_centre_id": cc_id,
            "cost_centre_code": cc.get("code"),
            "cost_centre_name": cc.get("name"),
            "period_a_amount": float(amt_a.quantize(Decimal("0.01"))),
            "period_b_amount": float(amt_b.quantize(Decimal("0.01"))),
            "variance": float(variance),
            "pct_change": round(pct_change, 2) if pct_change is not None else None,
        })

    return {
        "period_a": {"period_id": period_a, "name": pa["name"], "fiscal_year": pa["fiscal_year"]},
        "period_b": {"period_id": period_b, "name": pb["name"], "fiscal_year": pb["fiscal_year"]},
        "comparison": comparison,
        "total_a": float(sum(totals_a.values()).quantize(Decimal("0.01"))),
        "total_b": float(sum(totals_b.values()).quantize(Decimal("0.01"))),
    }
