#!/usr/bin/env python3
"""Collect GPU requests from GitHub issues and write site/data.json.

Runs inside GitHub Actions with GITHUB_TOKEN and GITHUB_REPOSITORY set.

Rules
- A request is an issue with the `gpu-request` label, created from the issue form.
- There is no approval: an open request holds its cards. A closed issue has released them.
  Admins (collaborators with write access) may add the label `rejected` to cancel a booking.
- Card ids come from the form's optional "GPU ids" field, or a `/gpu 0,2` comment by the author
  or an admin; `/note ...` adds a note. Otherwise the lowest free cards are assigned automatically.
"""
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone

REPO = os.environ.get("GITHUB_REPOSITORY", "")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
API = "https://api.github.com"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def api(path, params=""):
    url = f"{API}{path}{params}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "gpu-scheduler-build",
    })
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def paged(path, params=""):
    page, out = 1, []
    while True:
        chunk = api(path, f"{params}&per_page=100&page={page}" if params else f"?per_page=100&page={page}")
        if not chunk:
            return out
        out.extend(chunk)
        if len(chunk) < 100:
            return out
        page += 1


FIELD_RE = re.compile(r"^### (.+?)\s*\n+(.*?)(?=^### |\Z)", re.S | re.M)


def parse_form(body):
    """Issue-form bodies render as '### Label\n\nvalue' blocks."""
    fields = {}
    for m in FIELD_RE.finditer(body or ""):
        key = m.group(1).strip().lower()
        val = m.group(2).strip()
        if val == "_No response_":
            val = ""
        fields[key] = val
    return fields


DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def main():
    if not REPO or not TOKEN:
        sys.exit("GITHUB_REPOSITORY and GITHUB_TOKEN are required")
    with open(os.path.join(ROOT, "nodes.json")) as f:
        nodes = json.load(f)
    node_by_name = {n["name"].lower(): n["id"] for n in nodes}
    node_by_id = {n["id"].lower(): n["id"] for n in nodes}

    admins = sorted({c["login"] for c in paged(f"/repos/{REPO}/collaborators")
                     if c.get("permissions", {}).get("push") or c.get("permissions", {}).get("admin")})
    admin_set = set(admins)

    issues = paged(f"/repos/{REPO}/issues", "?state=all&labels=gpu-request")
    requests_out, problems = [], []
    for it in issues:
        if "pull_request" in it:
            continue
        f = parse_form(it.get("body"))
        node_raw = f.get("node", "").strip()
        gpu_id = node_by_name.get(node_raw.lower()) or node_by_id.get(node_raw.lower())
        try:
            count = int(re.sub(r"\D", "", f.get("cards", "") or "0") or 0)
        except ValueError:
            count = 0
        start, end = f.get("start date", "").strip(), f.get("end date", "").strip()
        if not gpu_id or count < 1 or not DATE_RE.match(start) or not DATE_RE.match(end) or end < start:
            problems.append({"number": it["number"], "url": it["html_url"], "reason": "could not parse node / cards / dates"})
            continue
        # No approval step: an open request holds its cards from the moment it is filed.
        # A `rejected` label (admins only) is the one override, e.g. to cancel a mistaken booking.
        labels = {l["name"] for l in it.get("labels", [])}
        status = "rejected" if "rejected" in labels else "approved"
        closed_at = it.get("closed_at")
        if it.get("state") == "closed":
            status = "released" if status == "approved" else "withdrawn"

        # Card ids: the form's optional "GPU ids" field, or a `/gpu 0,2` comment by the author or an admin.
        slots = None
        ids_raw = f.get("gpu ids", "")
        if ids_raw:
            ids = sorted({int(x) for x in re.findall(r"\d+", ids_raw)})
            if len(ids) == count:
                slots = ids
        note = ""
        if it.get("comments", 0):
            author = it["user"]["login"]
            for c in paged(f"/repos/{REPO}/issues/{it['number']}/comments"):
                login = c["user"]["login"]
                if login != author and login not in admin_set:
                    continue
                body = c.get("body") or ""
                m = re.search(r"^/gpu\s+([\d,\s]+)$", body, re.M)
                if m:
                    ids = sorted({int(x) for x in re.findall(r"\d+", m.group(1))})
                    if len(ids) == count:
                        slots = ids
                m2 = re.search(r"^/note\s+(.+)$", body, re.M)
                if m2:
                    note = m2.group(1).strip()
        decision = {"status": status if status in ("approved", "rejected") else "approved", "slots": slots, "note": note, "decidedBy": None}

        requests_out.append({
            "id": f"i{it['number']}",
            "number": it["number"],
            "url": it["html_url"],
            "uid": it["user"]["login"],
            "gpuId": gpu_id,
            "count": count,
            "start": start,
            "end": end,
            "purpose": f.get("purpose", "") or it.get("title", ""),
            "status": status,
            "decision": decision,
            "createdAt": it["created_at"],
            "closedAt": closed_at,
        })

    out = {
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "repo": REPO,
        "nodes": nodes,
        "admins": admins,
        "requests": requests_out,
        "problems": problems,
    }
    os.makedirs(os.path.join(ROOT, "site"), exist_ok=True)
    with open(os.path.join(ROOT, "site", "data.json"), "w") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
    print(f"wrote {len(requests_out)} requests, {len(problems)} unparsable, {len(admins)} admins")


if __name__ == "__main__":
    main()
