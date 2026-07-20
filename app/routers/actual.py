"""
Actual Mode – Analytics endpoints.

Actual periods have mode='actual' and status='submitted'.
These endpoints provide historical spend analytics across submitted periods.

  GET  /actual/periods                       – list submitted actual periods
  GET  /actual/summary                       – cross-period rollup by cost centre
  GET  /actual/trends                        – spend trend over time per cost centre
  GET  /actual/cost-centre/{cc_id}           – deep-dive on one cost centre
  GET  /actual/categories                    – spend broken down by label category
  GET  /actual/activities/top                – top N activities by allocated spend

All endpoints are read-only (viewer+).
"""

from collections import defaultdict
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app import auth, db
from app.routers.step4_review import _activity_allocated_amount, _label_field
from app.schemas import ActualAnalyticsSummary, ActualCostCentreAnalysis, ActualTrendPoint

router = APIRouter(prefix="/actual", tags=["Actual Mode – Analytics"])


def _get_submitted_actual_periods(
    fiscal_year: int | None = None,
    cost_centre_id: int | None = None,
) -> list[dict]:
    """Return actual-mode, submitted periods, optionally filtered."""
    periods = [
        p for p in db.periods.values()
        if p["mode"] == "actual" and p["status"] == "submitted"
    ]
    if fiscal_year:
        periods = [p for p in periods if p["fiscal_year"] == fiscal_year]
    return sorted(periods, key=lambda p: (p["fiscal_year"], p.get("fiscal_month") or 0))


def _period_cc_amounts(period_id: int) -> dict[int, tuple[Decimal, str]]:
    """
    Returns {cost_centre_id: (total_allocated_amount, currency)}
    for all distributions in the period.
    """
    from app.routers.step4_review import _build_cc_rollup
    rollup = _build_cc_rollup(period_id)
    return {r.cost_centre_id: (r.total_amount, r.currency) for r in rollup}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/periods", summary="List submitted actual periods")
def list_actual_periods(
    fiscal_year: int | None = None,
    _user: Annotated[dict, Depends(auth.require_viewer)] = None,
) -> list[dict]:
    return _get_submitted_actual_periods(fiscal_year=fiscal_year)


@router.get(
    "/summary",
    response_model=ActualAnalyticsSummary,
    summary="Cross-period analytics: spend by cost centre, top activities, category breakdown",
)
def actual_summary(
    fiscal_year: int | None = None,
    _user: Annotated[dict, Depends(auth.require_viewer)] = None,
):
    periods = _get_submitted_actual_periods(fiscal_year=fiscal_year)

    # --- Cost centre analysis ---
    cc_period_amounts: dict[int, list] = defaultdict(list)
    for period in periods:
        pid = period["period_id"]
        for cc_id, (amt, currency) in _period_cc_amounts(pid).items():
            cc_period_amounts[cc_id].append(
                ActualTrendPoint(
                    fiscal_year=period["fiscal_year"],
                    fiscal_month=period.get("fiscal_month"),
                    period_name=period["name"],
                    total_spend=amt,
                    currency=currency,
                )
            )

    cc_analysis = []
    for cc_id, trend_points in cc_period_amounts.items():
        cc = db.cost_centres.get(cc_id)
        if not cc:
            continue
        total = sum(p.total_spend for p in trend_points).quantize(Decimal("0.01"))
        currencies = {p.currency for p in trend_points}
        currency = currencies.pop() if len(currencies) == 1 else "MIXED"
        cc_analysis.append(
            ActualCostCentreAnalysis(
                cost_centre_id=cc_id,
                cost_centre_code=cc["code"],
                cost_centre_name=cc["name"],
                periods=trend_points,
                total_spend=total,
                currency=currency,
            )
        )

    # --- Top activities by total allocated amount ---
    activity_spend: dict[int, Decimal] = defaultdict(Decimal)
    for period in periods:
        pid = period["period_id"]
        for act in db.find_many(db.activities, period_id=pid):
            amt, _ = _activity_allocated_amount(act["activity_id"], pid)
            activity_spend[act["activity_id"]] += amt

    top_activities = sorted(
        [
            {
                "activity_id": aid,
                "activity_name": (db.activities.get(aid) or {}).get("name"),
                "category": _label_field(aid, "category"),
                "total_spend": float(spend.quantize(Decimal("0.01"))),
            }
            for aid, spend in activity_spend.items()
        ],
        key=lambda x: x["total_spend"],
        reverse=True,
    )[:20]

    # --- Category breakdown ---
    category_spend: dict[str, Decimal] = defaultdict(Decimal)
    for period in periods:
        pid = period["period_id"]
        for act in db.find_many(db.activities, period_id=pid):
            cat = _label_field(act["activity_id"], "category") or "Uncategorised"
            amt, _ = _activity_allocated_amount(act["activity_id"], pid)
            category_spend[cat] += amt

    category_breakdown = [
        {"category": cat, "total_spend": float(amt.quantize(Decimal("0.01")))}
        for cat, amt in sorted(category_spend.items(), key=lambda x: x[1], reverse=True)
    ]

    return ActualAnalyticsSummary(
        cost_centre_breakdown=cc_analysis,
        top_activities_by_spend=top_activities,
        category_breakdown=category_breakdown,
    )


@router.get(
    "/trends",
    summary="Spend trend over time — optionally filter to one cost centre",
)
def actual_trends(
    cost_centre_id: int | None = None,
    fiscal_year: int | None = None,
    _user: Annotated[dict, Depends(auth.require_viewer)] = None,
) -> list[dict]:
    periods = _get_submitted_actual_periods(fiscal_year=fiscal_year)
    result = []
    for period in periods:
        pid = period["period_id"]
        cc_amounts = _period_cc_amounts(pid)
        if cost_centre_id:
            if cost_centre_id not in cc_amounts:
                continue
            amounts = [cc_amounts[cost_centre_id]]
        else:
            amounts = list(cc_amounts.values())

        total = sum(a[0] for a in amounts).quantize(Decimal("0.01"))
        currencies = {a[1] for a in amounts}
        currency = currencies.pop() if len(currencies) == 1 else "MIXED"
        result.append({
            "period_id": pid,
            "period_name": period["name"],
            "fiscal_year": period["fiscal_year"],
            "fiscal_month": period.get("fiscal_month"),
            "total_spend": float(total),
            "currency": currency,
        })
    return result


@router.get(
    "/cost-centre/{cost_centre_id}",
    summary="Deep-dive analytics for a single cost centre across all submitted actual periods",
)
def actual_cost_centre(
    cost_centre_id: int,
    fiscal_year: int | None = None,
    _user: Annotated[dict, Depends(auth.require_viewer)] = None,
) -> dict:
    cc = db.cost_centres.get(cost_centre_id)
    if not cc:
        raise HTTPException(404, "Cost centre not found")

    periods = _get_submitted_actual_periods(fiscal_year=fiscal_year)
    period_rows = []
    total_spend = Decimal("0.00")

    for period in periods:
        pid = period["period_id"]
        cc_amounts = _period_cc_amounts(pid)
        if cost_centre_id not in cc_amounts:
            continue
        amt, currency = cc_amounts[cost_centre_id]
        total_spend += amt

        # Activities contributing to this cost centre in this period
        contributing = []
        for act in db.find_many(db.activities, period_id=pid):
            aid = act["activity_id"]
            act_amount, _ = _activity_allocated_amount(aid, pid)
            dists = db.find_many(db.distributions, activity_id=aid, cost_centre_id=cost_centre_id)
            for dist in dists:
                share = (act_amount * dist["percentage"] / Decimal("100")).quantize(Decimal("0.01"))
                le = db.legal_entities.get(dist["legal_entity_id"]) or {}
                contributing.append({
                    "activity_id": aid,
                    "activity_name": act["name"],
                    "category": _label_field(aid, "category"),
                    "legal_entity_code": le.get("code"),
                    "legal_entity_name": le.get("name"),
                    "amount": float(share),
                    "currency": currency,
                })

        period_rows.append({
            "period_id": pid,
            "period_name": period["name"],
            "fiscal_year": period["fiscal_year"],
            "fiscal_month": period.get("fiscal_month"),
            "total_spend": float(amt.quantize(Decimal("0.01"))),
            "currency": currency,
            "activities": contributing,
        })

    return {
        "cost_centre_id": cost_centre_id,
        "cost_centre_code": cc["code"],
        "cost_centre_name": cc["name"],
        "total_spend": float(total_spend.quantize(Decimal("0.01"))),
        "periods": period_rows,
    }


@router.get(
    "/categories",
    summary="Spend breakdown by label category across submitted actual periods",
)
def actual_by_category(
    fiscal_year: int | None = None,
    _user: Annotated[dict, Depends(auth.require_viewer)] = None,
) -> list[dict]:
    periods = _get_submitted_actual_periods(fiscal_year=fiscal_year)
    category_spend: dict[str, Decimal] = defaultdict(Decimal)

    for period in periods:
        pid = period["period_id"]
        for act in db.find_many(db.activities, period_id=pid):
            cat = _label_field(act["activity_id"], "category") or "Uncategorised"
            amt, _ = _activity_allocated_amount(act["activity_id"], pid)
            category_spend[cat] += amt

    return [
        {"category": cat, "total_spend": float(amt.quantize(Decimal("0.01")))}
        for cat, amt in sorted(category_spend.items(), key=lambda x: x[1], reverse=True)
    ]


@router.get(
    "/activities/top",
    summary="Top N activities by total allocated spend",
)
def top_activities(
    limit: int = Query(10, ge=1, le=100),
    fiscal_year: int | None = None,
    _user: Annotated[dict, Depends(auth.require_viewer)] = None,
) -> list[dict]:
    periods = _get_submitted_actual_periods(fiscal_year=fiscal_year)
    activity_spend: dict[int, Decimal] = defaultdict(Decimal)

    for period in periods:
        pid = period["period_id"]
        for act in db.find_many(db.activities, period_id=pid):
            amt, _ = _activity_allocated_amount(act["activity_id"], pid)
            activity_spend[act["activity_id"]] += amt

    return sorted(
        [
            {
                "activity_id": aid,
                "activity_name": (db.activities.get(aid) or {}).get("name"),
                "category": _label_field(aid, "category"),
                "sub_category": _label_field(aid, "sub_category"),
                "total_spend": float(spend.quantize(Decimal("0.01"))),
            }
            for aid, spend in activity_spend.items()
        ],
        key=lambda x: x["total_spend"],
        reverse=True,
    )[:limit]
