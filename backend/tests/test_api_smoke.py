#!/usr/bin/env python3
"""
Auteur — backend smoke test (blueprint Section 31.3).

Runs against a live uvicorn instance (start it first with
`uvicorn backend.main:app --port 8000`). Exercises every endpoint in the
Table 38 API surface (stubs included) + the health check.

Usage:
  uvicorn backend.main:app --port 8000 &
  python3 backend/tests/test_api_smoke.py
"""
from __future__ import annotations

import json
import sys
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE = "http://127.0.0.1:8000"
TIMEOUT = 10


def call(method: str, path: str, body: dict | None = None) -> tuple[int, dict | str]:
    url = BASE + path
    data = json.dumps(body).encode() if body else None
    req = Request(url, data=data, method=method,
                  headers={"Content-Type": "application/json"} if body else {})
    try:
        with urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read().decode()
            try:
                return r.status, json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                return r.status, raw
    except HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            return e.code, raw
    except URLError as e:
        return -1, str(e)


def main() -> int:
    results = []

    # 1. Root
    s, _ = call("GET", "/")
    results.append(("/", s, "root"))

    # 2. /api/health (the Cloud Run smoke test)
    s, h = call("GET", "/api/health")
    ok = s == 200 and h.get("status") == "ok"
    results.append(("/api/health", s, "status=ok" if ok else f"FAIL: {h}"))

    # 3. /api (api root)
    s, _ = call("GET", "/api")
    results.append(("/api", s, "api root"))

    # 4. POST /api/projects (create a project)
    s, p = call("POST", "/api/projects", {"logline": "An 1892 lighthouse keeper discovers a message in a bottle."})
    project_id = p.get("project_id") if isinstance(p, dict) else None
    results.append(("POST /api/projects", s,
                    f"project_id={project_id}" if project_id else f"FAIL: {p}"))

    # 5. GET /api/projects/{id}
    if project_id:
        s, g = call("GET", f"/api/projects/{project_id}")
        results.append((f"GET /api/projects/{project_id[:8]}", s,
                        f"status={g.get('project',{}).get('status')}" if isinstance(g, dict) else f"FAIL: {g}"))

        # 6. GET /api/projects/{id}/bible (no bible yet -> 404)
        s, b = call("GET", f"/api/projects/{project_id}/bible")
        results.append(("GET /bible (no bible yet)", s,
                        "404 expected" if s == 404 else f"FAIL: {b}"))

        # 7. GET /api/projects/{id}/shots
        s, sh = call("GET", f"/api/projects/{project_id}/shots")
        results.append(("GET /shots", s, f"{sh.get('shots')}" if isinstance(sh, dict) else f"FAIL: {sh}"))

        # 8. POST /api/projects/{id}/shots/{shotId}/generate (stub -> 404, shot doesn't exist)
        s, gen = call("POST", f"/api/projects/{project_id}/shots/nonexistent/generate", {"bible_version": 1})
        results.append(("POST /generate (stub)", s, "404 expected" if s == 404 else f"FAIL: {gen}"))

        # 9. POST /api/projects/{id}/assemble (stub)
        s, asm = call("POST", f"/api/projects/{project_id}/assemble")
        results.append(("POST /assemble (stub)", s, "accepted" if s == 200 else f"FAIL: {asm}"))

        # 10. POST /api/projects/{id}/share
        s, sh_link = call("POST", f"/api/projects/{project_id}/share")
        slug = sh_link.get("public_slug") if isinstance(sh_link, dict) else None
        results.append(("POST /share", s, f"slug={slug}" if slug else f"FAIL: {sh_link}"))

        # 11. GET /api/projects/{id}/export/shots (CSV)
        s, csv = call("GET", f"/api/projects/{project_id}/export/shots")
        results.append(("GET /export/shots (csv)", s, "csv header ok" if "order,id,status" in str(csv) else f"FAIL: {csv}"))

        # 12. GET /api/projects/{id}/events
        s, ev = call("GET", f"/api/projects/{project_id}/events")
        ev_count = ev.get("count") if isinstance(ev, dict) else None
        results.append(("GET /events", s, f"{ev_count} events" if ev_count is not None else f"FAIL: {ev}"))

    # Print results
    print("\n" + "=" * 70)
    print(f"{'ENDPOINT':<35} {'STATUS':<8} RESULT")
    print("-" * 70)
    failures = 0
    for path, status, detail in results:
        marker = "✓" if (status == 200 or (isinstance(detail, str) and "404 expected" in detail)) else "✗"
        if marker == "✗":
            failures += 1
        print(f"{marker} {path:<33} {status:<8} {detail[:50]}")
    print("=" * 70)
    print(f"{'PASS' if failures == 0 else 'FAIL'} — {len(results) - failures}/{len(results)} endpoints OK")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
