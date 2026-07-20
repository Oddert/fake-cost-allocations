"""Quick smoke-test script — starts uvicorn in-process, runs checks, exits."""
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import json

proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8877"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)
time.sleep(4)

if proc.poll() is not None:
    print("SERVER CRASHED:\n" + proc.stderr.read().decode()[-3000:])
    sys.exit(1)

errors = []

def check(label, fn):
    try:
        result = fn()
        print(f"  OK  {label}: {result}")
    except Exception as e:
        print(f" FAIL {label}: {e}")
        errors.append(label)

def get(path, token=None):
    req = urllib.request.Request(f"http://localhost:8877{path}")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    r = urllib.request.urlopen(req)
    return json.loads(r.read())

def post(path, body, token=None, content_type="application/json"):
    data = urllib.parse.urlencode(body).encode() if content_type.startswith("application/x-www") else json.dumps(body).encode()
    req = urllib.request.Request(f"http://localhost:8877{path}", data=data, method="POST")
    req.add_header("Content-Type", content_type)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    r = urllib.request.urlopen(req)
    return json.loads(r.read())

try:
    # 1. Health
    check("health", lambda: get("/health")["status"])

    # 2. Login as admin
    admin_token = None
    def do_login():
        global admin_token
        resp = post("/auth/token", {"username": "admin", "password": "admin123"}, content_type="application/x-www-form-urlencoded")
        admin_token = resp["access_token"]
        return resp["token_type"]
    check("login admin", do_login)

    # 3. List periods
    check("list periods", lambda: f"{len(get('/periods', admin_token))} periods")

    # 4. Budget summary
    periods = get("/periods", admin_token)
    budget_pid = next(p["period_id"] for p in periods if p["mode"] == "budget")
    check("budget summary", lambda: f"total_budget={get(f'/budget/periods/{budget_pid}/summary', admin_token)['total_budget']}")

    # 5. Actual analytics
    check("actual summary", lambda: f"cc_count={len(get('/actual/summary', admin_token)['cost_centre_breakdown'])}")

    # 6. Actual trends
    check("actual trends", lambda: f"trend_points={len(get('/actual/trends', admin_token))}")

    # 7. Review a submitted actual period
    actual_pid = next(p["period_id"] for p in periods if p["mode"] == "actual" and p["status"] == "submitted")
    check("review submitted period", lambda: f"warnings={len(get(f'/periods/{actual_pid}/review', admin_token)['warnings'])}")

    # 8. Get submission record
    check("get submission", lambda: f"checksum_len={len(get(f'/periods/{actual_pid}/submission', admin_token)['checksum'])}")

    # 9. Analyst token
    analyst_token = post("/auth/token", {"username": "analyst", "password": "analyst123"}, content_type="application/x-www-form-urlencoded")["access_token"]
    check("login analyst", lambda: "ok")

    # 10. Role check: viewer cannot submit
    viewer_token = post("/auth/token", {"username": "viewer", "password": "viewer123"}, content_type="application/x-www-form-urlencoded")["access_token"]
    def check_viewer_blocked():
        req = urllib.request.Request(
            f"http://localhost:8877/periods/{budget_pid}/submit",
            data=json.dumps({"notes": "test"}).encode(),
            method="POST",
        )
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {viewer_token}")
        try:
            urllib.request.urlopen(req)
            return "FAIL: viewer was allowed"
        except urllib.error.HTTPError as e:
            return f"blocked with HTTP {e.code}"
    check("viewer blocked from submit", check_viewer_blocked)

    # 11. Cost centre list
    check("cost centres", lambda: f"{len(get('/cost-centres', admin_token))} cost centres")

    # 12. Legal entities
    check("legal entities", lambda: f"{len(get('/legal-entities', admin_token))} legal entities")

    # 13. Label completeness
    open_period_pid = next(p["period_id"] for p in periods if p["mode"] == "budget")
    check("label completeness", lambda: str(get(f"/periods/{open_period_pid}/labels/completeness", admin_token)))

    print()
    if errors:
        print(f"FAILED checks: {errors}")
        sys.exit(1)
    else:
        print("ALL CHECKS PASSED")

finally:
    proc.terminate()
