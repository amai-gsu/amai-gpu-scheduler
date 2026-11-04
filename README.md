# Lab GPU Scheduler

## 🔗 https://amai-gsu.github.io/amai-gpu-scheduler/

Book GPU cards on the lab's nodes straight from the page. No approval step: a booking takes effect
the moment you submit it, and the page refuses windows where the cards are already taken.

## For lab members

1. Open the link above and click **Sign in** (top right). The page walks you through creating a
   GitHub token (classic, `public_repo` scope only). Paste it once; your browser remembers it.
2. Your cards are listed under **Card assignment**. Switch **Can share** on if others may run on
   them; to use someone else's cards, they must have shared them, and you agree the details in the
   WeChat group (💬 button, top right).
3. Run only on your cards, e.g. `CUDA_VISIBLE_DEVICES=0,2`. Ids match `nvidia-smi` on the node.
4. Fill in your row under **Targets** (venue, deadline) so everyone can see who is under pressure.
5. The sign-in box also asks for your real name; it is shown on your bookings so everyone knows
   who holds the cards. Sign in again any time to change it.

You need **Write** access to this repository to book. Ask a lab admin to add you under
Settings → Collaborators.

**Policy, penalties and the chat button** come from [`policy.json`](policy.json): edit the lists
there. The lab talks in a WeChat group; drop the group QR code at `site/wechat-qr.png` (group QR
codes expire after 7 days, so replace it when needed) and it shows under the 💬 button.

## For admins

- **Add a member**: Settings → Collaborators and teams → Add people → role **Write**.
- **Cancel someone's booking**: sign in as a repository Maintainer/Admin; the **All bookings** tab
  shows a *Cancel booking* button.
- **Card assignment**: every card has a standing owner, listed in
  [`assignments.json`](assignments.json) (`uid`, `gpuId`, `slots`, `share`). Owners switch
  **Can share** on or off on the page; only shared cards can be booked by someone else.
- **Add or change nodes**: edit [`nodes.json`](nodes.json) and commit. Fields: `id`, `name`,
  `model`, `cards`, `memoryGb`, `status` (`available` or `maintenance`), `note`.
- **Targets** live in [`targets.json`](targets.json); members edit their own row on the page.
- **Fill in people's names**: edit [`members.json`](members.json), `"github-login": "Real Name"`.
  It overrides the GitHub profile name.
- **Fix a booking by hand**: edit [`bookings.json`](bookings.json); every booking is one object
  with `uid`, `gpuId`, `slots`, `count`, `start`, `end` (inclusive dates), `modelSize`, `vramGb`, and
  `closedAt` / `cancelled` once it ends.

## Live usage (node agents)

Each node runs [`agent/report.py`](agent/report.py) from cron every 30 minutes. It reports every
card's memory use, utilisation and the Linux users running on it to `status/<node>.json` and a
30-day history. The dashboard's node cards, timeline and statistics are built from these reports;
a card counts as busy above 1 GB used or 5% utilisation. Install steps: [`agent/README.md`](agent/README.md).
Map Linux usernames to people in `members.json` under `linux`.

## How it works

The page is static (GitHub Pages, deployed by the workflow in `.github/workflows/pages.yml`).
All data lives in two JSON files in this repository, which the page reads and writes through the
GitHub Contents API using each member's own token. (Classic tokens, because the repository is owned
by a user account and GitHub does not let collaborators use fine-grained tokens there.) Every booking is therefore a commit, so
`git log bookings.json` is the audit trail. Writes are compare-and-swap on the file's SHA, so two
people booking at the same moment cannot overwrite each other.

The repository is public, so bookings (GitHub usernames, dates, purposes) are visible to anyone.
