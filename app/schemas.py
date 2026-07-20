"""
Shared Pydantic schemas for the Cost Allocations API.

Naming convention:
  <Entity>Create  – request body for POST
  <Entity>Update  – request body for PATCH (all fields optional)
  <Entity>        – response model (includes computed/DB fields)
"""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

class CostCentreCreate(BaseModel):
    code: str = Field(..., max_length=20)
    name: str = Field(..., max_length=200)
    description: str | None = Field(None, max_length=500)


class CostCentreUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    description: str | None = Field(None, max_length=500)
    is_active: bool | None = None


class CostCentre(CostCentreCreate):
    cost_centre_id: int
    is_active: bool


class LegalEntityCreate(BaseModel):
    code: str = Field(..., max_length=20)
    name: str = Field(..., max_length=200)
    country_code: str | None = Field(None, max_length=3)


class LegalEntityUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    country_code: str | None = Field(None, max_length=3)
    is_active: bool | None = None


class LegalEntity(LegalEntityCreate):
    legal_entity_id: int
    is_active: bool


# ---------------------------------------------------------------------------
# Allocation Periods
# ---------------------------------------------------------------------------

PeriodMode   = Literal["budget", "actual"]
PeriodStatus = Literal["open", "locked", "submitted"]


class PeriodCreate(BaseModel):
    name: str = Field(..., max_length=100)
    mode: PeriodMode
    fiscal_year: int = Field(..., ge=2000, le=2100)
    fiscal_month: int | None = Field(None, ge=1, le=12)


class PeriodUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    fiscal_month: int | None = Field(None, ge=1, le=12)


class Period(PeriodCreate):
    period_id: int
    status: PeriodStatus
    created_by: int
    created_at: datetime
    locked_at: datetime | None = None


# ---------------------------------------------------------------------------
# Expenses
# ---------------------------------------------------------------------------

class ExpenseCreate(BaseModel):
    cost_centre_id: int
    description: str = Field(..., max_length=500)
    gl_account: str | None = Field(None, max_length=50)
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    currency: str = Field("GBP", max_length=3)
    source_ref: str | None = Field(None, max_length=100)


class ExpenseUpdate(BaseModel):
    description: str | None = Field(None, max_length=500)
    gl_account: str | None = Field(None, max_length=50)
    amount: Decimal | None = Field(None, gt=0, decimal_places=2)
    currency: str | None = Field(None, max_length=3)
    source_ref: str | None = Field(None, max_length=100)


class Expense(ExpenseCreate):
    expense_id: int
    period_id: int
    created_by: int
    created_at: datetime
    # Derived: sum of assignment percentages
    assigned_pct: Decimal = Decimal("0.00")


# ---------------------------------------------------------------------------
# Activities
# ---------------------------------------------------------------------------

class ActivityCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: str | None = Field(None, max_length=500)


class ActivityUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    description: str | None = Field(None, max_length=500)


class Activity(ActivityCreate):
    activity_id: int
    period_id: int
    created_by: int
    created_at: datetime


# ---------------------------------------------------------------------------
# Step 1 – Expense → Activity Assignments
# ---------------------------------------------------------------------------

class AssignmentCreate(BaseModel):
    activity_id: int
    percentage: Decimal = Field(..., gt=0, le=100, decimal_places=2)


class AssignmentUpdate(BaseModel):
    percentage: Decimal = Field(..., gt=0, le=100, decimal_places=2)


class Assignment(AssignmentCreate):
    assignment_id: int
    expense_id: int
    created_by: int
    created_at: datetime


class AssignmentSummary(BaseModel):
    """Summary of how one expense's total 100% is distributed across activities."""
    expense_id: int
    description: str
    amount: Decimal
    currency: str
    total_assigned_pct: Decimal
    assignments: list[Assignment]


# ---------------------------------------------------------------------------
# Step 2 – Activity Distributions
# ---------------------------------------------------------------------------

class DistributionCreate(BaseModel):
    cost_centre_id: int
    legal_entity_id: int
    percentage: Decimal = Field(..., gt=0, le=100, decimal_places=2)


class DistributionUpdate(BaseModel):
    percentage: Decimal = Field(..., gt=0, le=100, decimal_places=2)


class Distribution(DistributionCreate):
    distribution_id: int
    activity_id: int
    created_by: int
    created_at: datetime


class DistributionSummary(BaseModel):
    """How one activity's cost is split across the business."""
    activity_id: int
    name: str
    total_distributed_pct: Decimal
    distributions: list[Distribution]


# ---------------------------------------------------------------------------
# Step 3 – Activity Labels / Classification
# ---------------------------------------------------------------------------

class LabelUpsert(BaseModel):
    category: str | None = Field(None, max_length=100)
    sub_category: str | None = Field(None, max_length=100)
    tags: list[str] = Field(default_factory=list)
    notes: str | None = Field(None, max_length=1000)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        for tag in v:
            if len(tag) > 50:
                raise ValueError("Each tag must be 50 characters or fewer")
        return [t.strip().lower() for t in v if t.strip()]


class Label(LabelUpsert):
    label_id: int
    activity_id: int
    created_by: int
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Step 4 – Submission
# ---------------------------------------------------------------------------

class SubmissionCreate(BaseModel):
    notes: str | None = Field(None, max_length=1000)


class Submission(SubmissionCreate):
    submission_id: int
    period_id: int
    submitted_by: int
    submitted_at: datetime
    checksum: str


# ---------------------------------------------------------------------------
# Review / Visualisation payloads (Step 4 read side)
# ---------------------------------------------------------------------------

class ActivityBreakdownItem(BaseModel):
    activity_id: int
    activity_name: str
    category: str | None
    sub_category: str | None
    tags: list[str]
    total_allocated_amount: Decimal
    currency: str
    distributions: list[Distribution]


class CostCentreRollup(BaseModel):
    cost_centre_id: int
    cost_centre_code: str
    cost_centre_name: str
    total_amount: Decimal
    currency: str
    by_legal_entity: list[dict]


class PeriodReviewSummary(BaseModel):
    period_id: int
    period_name: str
    mode: PeriodMode
    status: PeriodStatus
    fiscal_year: int
    fiscal_month: int | None
    total_expenses: Decimal
    total_assigned_pct: Decimal          # should be 100 for complete periods
    activities: list[ActivityBreakdownItem]
    cost_centre_rollup: list[CostCentreRollup]
    warnings: list[str]                  # e.g. unassigned expenses, over-allocated


# ---------------------------------------------------------------------------
# Budget mode – planning schemas
# ---------------------------------------------------------------------------

class BudgetAllocationItem(BaseModel):
    cost_centre_id: int
    legal_entity_id: int
    activity_id: int
    activity_name: str
    category: str | None
    allocated_amount: Decimal
    currency: str


class BudgetSummary(BaseModel):
    period_id: int
    period_name: str
    fiscal_year: int
    fiscal_month: int | None
    total_budget: Decimal
    currency: str
    by_cost_centre: list[CostCentreRollup]
    allocations: list[BudgetAllocationItem]


# ---------------------------------------------------------------------------
# Actual mode – analytics schemas
# ---------------------------------------------------------------------------

class ActualTrendPoint(BaseModel):
    fiscal_year: int
    fiscal_month: int | None
    period_name: str
    total_spend: Decimal
    currency: str


class ActualCostCentreAnalysis(BaseModel):
    cost_centre_id: int
    cost_centre_code: str
    cost_centre_name: str
    periods: list[ActualTrendPoint]
    total_spend: Decimal
    currency: str


class ActualAnalyticsSummary(BaseModel):
    cost_centre_breakdown: list[ActualCostCentreAnalysis]
    top_activities_by_spend: list[dict]
    category_breakdown: list[dict]
