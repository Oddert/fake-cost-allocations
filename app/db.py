"""
Mock in-memory database designed to mirror an Oracle schema.

Oracle design notes:
- All PKs use INTEGER sequences (seq_<table>_id) instead of SERIAL/UUID.
- String columns annotated with their Oracle equivalent VARCHAR2 length.
- Decimal amounts stored as Python Decimal to match Oracle NUMBER(15,2).
- Timestamps are UTC, matching Oracle TIMESTAMP WITH TIME ZONE.
- Foreign key relationships are enforced at the service layer (as Oracle constraints would be).
- Tables are represented as Dict[int, dict] keyed by their PK.
"""

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from threading import Lock
from typing import Any

# ---------------------------------------------------------------------------
# Sequence emulation  (Oracle: CREATE SEQUENCE seq_xxx START WITH 1)
# ---------------------------------------------------------------------------

class _Sequence:
    """Thread-safe integer sequence, mirrors Oracle SEQUENCE behaviour."""

    def __init__(self, start: int = 1):
        self._val = start - 1
        self._lock = Lock()

    def nextval(self) -> int:
        with self._lock:
            self._val += 1
            return self._val


# One sequence per table, mirroring Oracle conventions
seq_users           = _Sequence()
seq_cost_centres    = _Sequence()
seq_legal_entities  = _Sequence()
seq_periods         = _Sequence()
seq_expenses        = _Sequence()
seq_activities      = _Sequence()
seq_assignments     = _Sequence()   # expense → activity assignments
seq_distributions   = _Sequence()   # activity → legal entity distributions
seq_labels          = _Sequence()   # activity classification labels
seq_submissions     = _Sequence()   # step-4 submissions

# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------
# Each dict represents a table row; keys are column names.
# Oracle type hints are left in comments for when real DDL is written.

# CA_USERS
# user_id       NUMBER          PK
# username      VARCHAR2(100)   UNIQUE NOT NULL
# email         VARCHAR2(255)   UNIQUE NOT NULL
# hashed_pwd    VARCHAR2(255)   NOT NULL
# role          VARCHAR2(20)    NOT NULL  CHECK (role IN ('admin','analyst','viewer'))
# is_active     NUMBER(1)       NOT NULL  DEFAULT 1
# created_at    TIMESTAMP WITH TIME ZONE
users: dict[int, dict[str, Any]] = {}

# CA_COST_CENTRES
# cost_centre_id   NUMBER        PK
# code             VARCHAR2(20)  UNIQUE NOT NULL
# name             VARCHAR2(200) NOT NULL
# description      VARCHAR2(500)
# is_active        NUMBER(1)     DEFAULT 1
cost_centres: dict[int, dict[str, Any]] = {}

# CA_LEGAL_ENTITIES
# legal_entity_id  NUMBER        PK
# code             VARCHAR2(20)  UNIQUE NOT NULL
# name             VARCHAR2(200) NOT NULL
# country_code     VARCHAR2(3)
# is_active        NUMBER(1)     DEFAULT 1
legal_entities: dict[int, dict[str, Any]] = {}

# CA_ALLOCATION_PERIODS
# period_id        NUMBER        PK
# name             VARCHAR2(100) NOT NULL
# mode             VARCHAR2(10)  NOT NULL  CHECK (mode IN ('budget','actual'))
# fiscal_year      NUMBER(4)     NOT NULL
# fiscal_month     NUMBER(2)     -- NULL allowed (annual periods)
# status           VARCHAR2(20)  NOT NULL  CHECK (status IN ('open','locked','submitted'))
# created_by       NUMBER        FK → CA_USERS
# created_at       TIMESTAMP WITH TIME ZONE
# locked_at        TIMESTAMP WITH TIME ZONE
periods: dict[int, dict[str, Any]] = {}

# CA_EXPENSES
# expense_id       NUMBER         PK
# period_id        NUMBER         FK → CA_ALLOCATION_PERIODS
# cost_centre_id   NUMBER         FK → CA_COST_CENTRES
# description      VARCHAR2(500)  NOT NULL
# gl_account       VARCHAR2(50)
# amount           NUMBER(15,2)   NOT NULL
# currency         VARCHAR2(3)    DEFAULT 'GBP'
# source_ref       VARCHAR2(100)  -- e.g. invoice/PO number
# created_by       NUMBER         FK → CA_USERS
# created_at       TIMESTAMP WITH TIME ZONE
expenses: dict[int, dict[str, Any]] = {}

# CA_ACTIVITIES
# activity_id      NUMBER         PK
# period_id        NUMBER         FK → CA_ALLOCATION_PERIODS
# name             VARCHAR2(200)  NOT NULL
# description      VARCHAR2(500)
# created_by       NUMBER         FK → CA_USERS
# created_at       TIMESTAMP WITH TIME ZONE
activities: dict[int, dict[str, Any]] = {}

# CA_EXPENSE_ACTIVITY_ASSIGNMENTS  (Step 1)
# assignment_id    NUMBER         PK
# expense_id       NUMBER         FK → CA_EXPENSES
# activity_id      NUMBER         FK → CA_ACTIVITIES
# percentage       NUMBER(5,2)    NOT NULL  CHECK (percentage > 0 AND percentage <= 100)
# created_by       NUMBER         FK → CA_USERS
# created_at       TIMESTAMP WITH TIME ZONE
# UNIQUE (expense_id, activity_id)
assignments: dict[int, dict[str, Any]] = {}

# CA_ACTIVITY_DISTRIBUTIONS  (Step 2)
# distribution_id  NUMBER         PK
# activity_id      NUMBER         FK → CA_ACTIVITIES
# cost_centre_id   NUMBER         FK → CA_COST_CENTRES
# legal_entity_id  NUMBER         FK → CA_LEGAL_ENTITIES
# percentage       NUMBER(5,2)    NOT NULL  CHECK (percentage > 0 AND percentage <= 100)
# created_by       NUMBER         FK → CA_USERS
# created_at       TIMESTAMP WITH TIME ZONE
# UNIQUE (activity_id, cost_centre_id, legal_entity_id)
distributions: dict[int, dict[str, Any]] = {}

# CA_ACTIVITY_LABELS  (Step 3)
# label_id         NUMBER         PK
# activity_id      NUMBER         FK → CA_ACTIVITIES  UNIQUE
# category         VARCHAR2(100)
# sub_category     VARCHAR2(100)
# tags             VARCHAR2(500)  -- pipe-separated, normalise to CA_TAGS in Oracle
# notes            VARCHAR2(1000)
# created_by       NUMBER         FK → CA_USERS
# created_at       TIMESTAMP WITH TIME ZONE
# updated_at       TIMESTAMP WITH TIME ZONE
labels: dict[int, dict[str, Any]] = {}

# CA_ALLOCATION_SUBMISSIONS  (Step 4)
# submission_id    NUMBER         PK
# period_id        NUMBER         FK → CA_ALLOCATION_PERIODS  UNIQUE
# submitted_by     NUMBER         FK → CA_USERS
# submitted_at     TIMESTAMP WITH TIME ZONE
# notes            VARCHAR2(1000)
# checksum         VARCHAR2(64)   -- SHA-256 of payload for audit trail
submissions: dict[int, dict[str, Any]] = {}

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _next_page(table: dict, offset: int, limit: int) -> list[dict]:
    """Simple offset/limit pagination matching Oracle OFFSET n ROWS FETCH NEXT m ROWS ONLY."""
    rows = list(table.values())
    return rows[offset: offset + limit]


def find_one(table: dict, **kwargs) -> dict | None:
    """Return first row matching all supplied column=value filters."""
    for row in table.values():
        if all(row.get(k) == v for k, v in kwargs.items()):
            return row
    return None


def find_many(table: dict, **kwargs) -> list[dict]:
    """Return all rows matching all supplied column=value filters."""
    return [
        row for row in table.values()
        if all(row.get(k) == v for k, v in kwargs.items())
    ]
