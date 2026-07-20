"""
Seed / fixture data for development and testing.

Loaded once at startup via `import app.seed` in app/main.py.

Scenario:
  - 3 users: admin, analyst, viewer
  - 4 cost centres: Technology, Finance, HR, Operations
  - 3 legal entities: UK Ltd, Ireland Ltd, Germany GmbH
  - 2 budget periods (FY2025, FY2026) and 2 submitted actual periods (FY2024 Q1, Q2)
  - Each period has expenses, activities, full assignments, distributions, labels
  - Actual periods are fully submitted so analytics endpoints return data immediately
"""

from decimal import Decimal

from app import db
from app.auth import hash_password

# ---------------------------------------------------------------------------
# Guard: only seed once
# ---------------------------------------------------------------------------
if db.users:
    pass  # already seeded (e.g. during hot-reload)
else:
    # -----------------------------------------------------------------------
    # Users
    # -----------------------------------------------------------------------
    _users = [
        ("admin",   "admin@example.com",   "admin123",   "admin"),
        ("analyst", "analyst@example.com", "analyst123", "analyst"),
        ("viewer",  "viewer@example.com",  "viewer123",  "viewer"),
    ]
    _user_ids: dict[str, int] = {}
    for username, email, password, role in _users:
        uid = db.seq_users.nextval()
        db.users[uid] = {
            "user_id": uid,
            "username": username,
            "email": email,
            "hashed_pwd": hash_password(password),
            "role": role,
            "is_active": True,
            "created_at": db.utcnow(),
        }
        _user_ids[username] = uid

    ADMIN = _user_ids["admin"]
    ANALYST = _user_ids["analyst"]

    # -----------------------------------------------------------------------
    # Cost Centres
    # -----------------------------------------------------------------------
    _cost_centres = [
        ("TECH", "Technology",  "IT infrastructure, software, and development"),
        ("FIN",  "Finance",     "Finance and accounting operations"),
        ("HR",   "Human Resources", "People and talent management"),
        ("OPS",  "Operations",  "Core business operations"),
    ]
    _cc_ids: dict[str, int] = {}
    for code, name, desc in _cost_centres:
        cid = db.seq_cost_centres.nextval()
        db.cost_centres[cid] = {
            "cost_centre_id": cid, "code": code,
            "name": name, "description": desc, "is_active": True,
        }
        _cc_ids[code] = cid

    # -----------------------------------------------------------------------
    # Legal Entities
    # -----------------------------------------------------------------------
    _legal_entities = [
        ("UK001",  "Acme UK Ltd",        "GBR"),
        ("IE001",  "Acme Ireland Ltd",   "IRL"),
        ("DE001",  "Acme Germany GmbH",  "DEU"),
    ]
    _le_ids: dict[str, int] = {}
    for code, name, country in _legal_entities:
        eid = db.seq_legal_entities.nextval()
        db.legal_entities[eid] = {
            "legal_entity_id": eid, "code": code,
            "name": name, "country_code": country, "is_active": True,
        }
        _le_ids[code] = eid

    # -----------------------------------------------------------------------
    # Helper to build a complete period (expenses → activities → step1-4)
    # -----------------------------------------------------------------------

    def _build_period(
        name: str,
        mode: str,
        fiscal_year: int,
        fiscal_month: int | None,
        submit: bool = False,
    ) -> int:
        pid = db.seq_periods.nextval()
        db.periods[pid] = {
            "period_id": pid,
            "name": name,
            "mode": mode,
            "fiscal_year": fiscal_year,
            "fiscal_month": fiscal_month,
            "status": "open",
            "created_by": ADMIN,
            "created_at": db.utcnow(),
            "locked_at": None,
        }

        # --- Expenses ---
        _expenses = [
            (_cc_ids["TECH"], "AWS Cloud Infrastructure",    "GL-5001", Decimal("45000.00")),
            (_cc_ids["TECH"], "Software Licences",           "GL-5002", Decimal("12500.00")),
            (_cc_ids["FIN"],  "Audit Fees",                  "GL-6001", Decimal("28000.00")),
            (_cc_ids["HR"],   "Recruitment Agency Fees",     "GL-7001", Decimal("18000.00")),
            (_cc_ids["OPS"],  "Office Rent",                 "GL-8001", Decimal("55000.00")),
            (_cc_ids["OPS"],  "Utilities",                   "GL-8002", Decimal("8500.00")),
        ]
        exp_ids = []
        for cc_id, desc, gl, amount in _expenses:
            eid = db.seq_expenses.nextval()
            db.expenses[eid] = {
                "expense_id": eid, "period_id": pid,
                "cost_centre_id": cc_id, "description": desc,
                "gl_account": gl, "amount": amount,
                "currency": "GBP", "source_ref": None,
                "created_by": ANALYST, "created_at": db.utcnow(),
            }
            exp_ids.append(eid)

        # --- Activities ---
        _activities = [
            ("Platform Engineering",    "Core platform and infrastructure work"),
            ("Product Development",     "Feature development across product lines"),
            ("Finance Operations",      "Day-to-day finance and reporting"),
            ("Talent Acquisition",      "Recruiting and onboarding"),
            ("Facilities Management",   "Office and facilities costs"),
        ]
        act_ids = []
        for act_name, act_desc in _activities:
            aid = db.seq_activities.nextval()
            db.activities[aid] = {
                "activity_id": aid, "period_id": pid,
                "name": act_name, "description": act_desc,
                "created_by": ANALYST, "created_at": db.utcnow(),
            }
            act_ids.append(aid)

        # ---- Step 1: Expense → Activity assignments ----
        # Each expense splits across one or two activities (totalling 100%)
        _assignments = [
            # (expense_index, activity_index, percentage)
            (0, 0, Decimal("70")),   # AWS → Platform Eng 70%
            (0, 1, Decimal("30")),   # AWS → Product Dev 30%
            (1, 0, Decimal("40")),   # Licences → Platform Eng 40%
            (1, 1, Decimal("60")),   # Licences → Product Dev 60%
            (2, 2, Decimal("100")),  # Audit → Finance Ops 100%
            (3, 3, Decimal("100")),  # Recruitment → Talent Acq 100%
            (4, 4, Decimal("100")),  # Rent → Facilities 100%
            (5, 4, Decimal("100")),  # Utilities → Facilities 100%
        ]
        for exp_idx, act_idx, pct in _assignments:
            asn_id = db.seq_assignments.nextval()
            db.assignments[asn_id] = {
                "assignment_id": asn_id,
                "expense_id": exp_ids[exp_idx],
                "activity_id": act_ids[act_idx],
                "percentage": pct,
                "created_by": ANALYST,
                "created_at": db.utcnow(),
            }

        # ---- Step 2: Activity → Cost Centre / Legal Entity distributions ----
        # Each activity distributed 100% across CC+LE slices
        UK  = _le_ids["UK001"]
        IE  = _le_ids["IE001"]
        DE  = _le_ids["DE001"]
        T   = _cc_ids["TECH"]
        F   = _cc_ids["FIN"]
        H   = _cc_ids["HR"]
        O   = _cc_ids["OPS"]

        _distributions = [
            # Platform Engineering: split across UK/IE/DE in Tech CC
            (0, T, UK, Decimal("50")),
            (0, T, IE, Decimal("30")),
            (0, T, DE, Decimal("20")),
            # Product Development: split UK/IE in Tech CC
            (1, T, UK, Decimal("60")),
            (1, T, IE, Decimal("40")),
            # Finance Operations: all UK, Finance CC
            (2, F, UK, Decimal("100")),
            # Talent Acquisition: split across HR CC, all UK
            (3, H, UK, Decimal("100")),
            # Facilities Management: split Ops CC, UK + IE
            (4, O, UK, Decimal("70")),
            (4, O, IE, Decimal("30")),
        ]
        for act_idx, cc_id, le_id, pct in _distributions:
            did = db.seq_distributions.nextval()
            db.distributions[did] = {
                "distribution_id": did,
                "activity_id": act_ids[act_idx],
                "cost_centre_id": cc_id,
                "legal_entity_id": le_id,
                "percentage": pct,
                "created_by": ANALYST,
                "created_at": db.utcnow(),
            }

        # ---- Step 3: Activity labels ----
        _labels = [
            # (act_idx, category, sub_category, tags, notes)
            (0, "Technology",  "Infrastructure",  ["cloud", "aws", "platform"],
             "Core infrastructure supporting all product lines"),
            (1, "Technology",  "Development",     ["product", "engineering"],
             "Feature and product development effort"),
            (2, "Finance",     "Compliance",      ["audit", "regulatory"],
             "Annual statutory audit fees"),
            (3, "People",      "Recruitment",     ["hiring", "talent"],
             "External recruitment agency spend"),
            (4, "Operations",  "Facilities",      ["rent", "utilities", "office"],
             "Office space and utilities allocation"),
        ]
        for act_idx, cat, sub_cat, tags, notes in _labels:
            lid = db.seq_labels.nextval()
            db.labels[lid] = {
                "label_id": lid,
                "activity_id": act_ids[act_idx],
                "category": cat,
                "sub_category": sub_cat,
                "tags": "|".join(tags),
                "notes": notes,
                "created_by": ANALYST,
                "created_at": db.utcnow(),
                "updated_at": db.utcnow(),
            }

        # ---- Step 4: Submit (for actual periods) ----
        if submit:
            import hashlib, json
            db.periods[pid]["status"] = "locked"
            db.periods[pid]["locked_at"] = db.utcnow()

            payload = {
                "period_id": pid,
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
                        for e in db.find_many(db.expenses, period_id=pid)
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
                        if db.activities.get(d["activity_id"], {}).get("period_id") == pid
                    ],
                    key=lambda x: (x["activity_id"], x["cost_centre_id"], x["legal_entity_id"]),
                ),
            }
            checksum = hashlib.sha256(
                json.dumps(payload, sort_keys=True).encode()
            ).hexdigest()

            sid = db.seq_submissions.nextval()
            db.submissions[sid] = {
                "submission_id": sid,
                "period_id": pid,
                "submitted_by": ADMIN,
                "submitted_at": db.utcnow(),
                "notes": f"Seed submission for {name}",
                "checksum": checksum,
            }
            db.periods[pid]["status"] = "submitted"

        return pid

    # -----------------------------------------------------------------------
    # Create the seeded periods
    # -----------------------------------------------------------------------

    # Budget periods
    _build_period("FY2025 Annual Budget",  "budget", 2025, None,  submit=False)
    _build_period("FY2026 Annual Budget",  "budget", 2026, None,  submit=False)

    # Actual periods (submitted so analytics endpoints have data)
    _build_period("FY2024 Q1 Actuals",     "actual", 2024, 1,     submit=True)
    _build_period("FY2024 Q2 Actuals",     "actual", 2024, 4,     submit=True)
