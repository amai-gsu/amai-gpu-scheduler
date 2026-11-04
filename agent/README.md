# Node agent

One file, `report.py`, run by cron on each GPU node every 30 minutes. It needs only Python 3 and
`nvidia-smi`.

## Install (one command per node)

```bash
curl -fsSL https://raw.githubusercontent.com/amai-gsu/amai-gpu-scheduler/main/agent/install.sh | sudo bash -s ada6000
```

(`lab2` on the other machine.) It asks for a GitHub token once, tests it, runs one report and
registers the cron job. Re-run it any time to replace the token.

## Manual install (what the script does)

```bash
sudo mkdir -p /opt/gpu-scheduler
sudo curl -fsSL https://raw.githubusercontent.com/amai-gsu/amai-gpu-scheduler/main/agent/report.py -o /opt/gpu-scheduler/report.py
sudo chmod 755 /opt/gpu-scheduler/report.py
```

Create a GitHub token for the agent (classic, scope `public_repo`, from an account with Write
access to this repo; one token can serve both nodes), then add a cron line (`crontab -e`):

```
*/30 * * * * GPU_SCHED_TOKEN=ghp_xxxxxxxx /usr/bin/python3 /opt/gpu-scheduler/report.py ada6000 >> /var/tmp/gpu-report.log 2>&1
```

Use `lab2` instead of `ada6000` on the other machine. Test once by hand:

```bash
GPU_SCHED_TOKEN=ghp_xxxxxxxx python3 /opt/gpu-scheduler/report.py ada6000
```

Within a minute the dashboard shows live usage; after a few samples the timeline and statistics
fill in. `ps -o user=` must be able to see other users' processes (it can on a normal Linux box).

## Mapping Linux users to people

The dashboard colours cards by the person using them. Add each person's Linux username(s) to
`members.json` under `linux`, e.g. `"linux": { "hongyu": "prehoke", "hke3": "prehoke" }`.
Unmapped usernames are shown as they are.
