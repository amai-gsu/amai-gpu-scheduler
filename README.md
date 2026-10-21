# Lab GPU Scheduler

A GitHub-native GPU request/approval board. Requests are GitHub issues, approvals are labels,
and the dashboard (cluster map, per-card timeline, calendar picker, usage statistics) is a static
page on GitHub Pages that GitHub Actions rebuilds whenever an issue changes.

## How it works

| Action | How |
|---|---|
| Request GPUs | Open an issue with the **GPU request** form (the dashboard's calendar pre-fills it) |
| Approve / reject | A collaborator with write access adds the label `approved` or `rejected` |
| Pin specific cards | Comment `/gpu 0,2` on the issue (admins only; count must match the request) |
| Add a note | Comment `/note low priority, may be preempted` |
| Withdraw / release early | Close the issue |
| Add or change nodes | Edit `nodes.json` and commit |
| Who is an admin | Anyone with write/maintain/admin permission on this repo |

Members type their GitHub username once in the dashboard's top-right corner to highlight their own
requests (it is only remembered in their browser; nothing is enforced client-side, GitHub does the
permission checks).

## One-time setup

1. **Settings → Pages → Build and deployment → Source: GitHub Actions.**
2. **Settings → Actions → General → Workflow permissions: Read repository contents** (default is fine;
   the workflow only needs `issues: read` and `pages: write`).
3. Create the two labels `approved` and `rejected` (Issues → Labels → New label).
4. Give lab members access to the repo so they can open issues (private repo: add them as
   collaborators with *Read* or *Triage*; admins get *Write*).
5. Push to `main`, or run the **Build and deploy GPU scheduler** workflow once by hand.
   The dashboard is then at `https://<org>.github.io/<repo>/`.

## Files

- `site/index.html` – the dashboard (reads `site/data.json`)
- `scripts/build_data.py` – turns issues into `site/data.json`
- `nodes.json` – the GPU nodes
- `.github/ISSUE_TEMPLATE/gpu-request.yml` – the request form; keep its field labels in sync with the parser
- `.github/workflows/pages.yml` – rebuild + deploy on issue events and pushes

Dates are inclusive calendar days. Card ids in the dashboard match `nvidia-smi` indices on the node,
so a member assigned GPU 2 runs with `CUDA_VISIBLE_DEVICES=2`.
