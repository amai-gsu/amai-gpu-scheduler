#!/usr/bin/env python3
"""Report this node's live GPU usage to the lab scheduler repository.

Run from cron every 30 minutes on each GPU node:
    */30 * * * * GPU_SCHED_TOKEN=ghp_xxx /usr/bin/python3 /opt/gpu-scheduler/report.py ada6000

It runs nvidia-smi, maps each GPU process to its Linux user, and writes two files in the repo
through the GitHub Contents API (needs a token with the public_repo scope and Write access):
    status/<node>.json          the latest snapshot
    status/<node>-history.json  the last ~1500 snapshots (about 30 days at one per 30 min)
Only the standard library is used.
"""
import base64
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone

REPO = os.environ.get("GPU_SCHED_REPO", "amai-gsu/amai-gpu-scheduler")
TOKEN = os.environ.get("GPU_SCHED_TOKEN")
NODE = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GPU_SCHED_NODE")
HISTORY_CAP = 1500
API = "https://api.github.com"


def sh(args):
    return subprocess.run(args, capture_output=True, text=True, check=False).stdout


def snapshot():
    gpus = []
    rows = sh(["nvidia-smi", "--query-gpu=index,uuid,memory.used,memory.total,utilization.gpu",
               "--format=csv,noheader,nounits"]).strip().splitlines()
    by_uuid = {}
    for row in rows:
        idx, uuid, used, total, util = [x.strip() for x in row.split(",")]
        g = {"i": int(idx), "memUsed": int(float(used)), "memTotal": int(float(total)), "util": int(float(util)), "procs": []}
        gpus.append(g)
        by_uuid[uuid] = g
    apps = sh(["nvidia-smi", "--query-compute-apps=gpu_uuid,pid,used_memory,process_name",
               "--format=csv,noheader,nounits"]).strip().splitlines()
    for row in apps:
        parts = [x.strip() for x in row.split(",")]
        if len(parts) < 3:
            continue
        uuid, pid, mem = parts[0], parts[1], parts[2]
        name = parts[3] if len(parts) > 3 else ""
        user = sh(["ps", "-o", "user=", "-p", pid]).strip() or "?"
        g = by_uuid.get(uuid)
        if g is not None:
            g["procs"].append({"user": user, "pid": int(pid), "mem": int(float(mem or 0)), "name": os.path.basename(name)[:40]})
    for g in gpus:
        g["users"] = sorted({p["user"] for p in g["procs"]})
    return {"node": NODE, "at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "gpus": gpus}


def api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{API}{path}", data=data, method=method, headers={
        "Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "gpu-scheduler-agent"})
    try:
        with urllib.request.urlopen(req) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def put_json(path, obj, message, attempts=3):
    for _ in range(attempts):
        cur = api("GET", f"/repos/{REPO}/contents/{path}?ref=main")
        body = {"message": message, "branch": "main",
                "content": base64.b64encode((json.dumps(obj, separators=(",", ":")) + "\n").encode()).decode()}
        if cur:
            body["sha"] = cur["sha"]
        try:
            api("PUT", f"/repos/{REPO}/contents/{path}", body)
            return cur
        except urllib.error.HTTPError as e:
            if e.code != 409:
                raise
    raise SystemExit("could not write " + path)


def main():
    if not TOKEN or not NODE:
        sys.exit("set GPU_SCHED_TOKEN and pass the node id (e.g. ada6000)")
    snap = snapshot()
    put_json(f"status/{NODE}.json", snap, f"status: {NODE} {snap['at']}")
    cur = api("GET", f"/repos/{REPO}/contents/status/{NODE}-history.json?ref=main")
    hist = {"samples": []}
    if cur:
        hist = json.loads(base64.b64decode(cur["content"]).decode())
    # history keeps only what the charts need: per card, memory use, utilisation and users
    hist["samples"].append({"at": snap["at"], "gpus": [{"i": g["i"], "mem": g["memUsed"], "tot": g["memTotal"], "util": g["util"], "users": g["users"]} for g in snap["gpus"]]})
    hist["samples"] = hist["samples"][-HISTORY_CAP:]
    put_json(f"status/{NODE}-history.json", hist, f"status history: {NODE}")
    print(f"reported {NODE}: " + ", ".join(f"GPU{g['i']} {g['memUsed']}/{g['memTotal']}MiB {g['util']}% {','.join(g['users']) or '-'}" for g in snap["gpus"]))


if __name__ == "__main__":
    main()
