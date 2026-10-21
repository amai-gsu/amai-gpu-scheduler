# Lab GPU Scheduler

## 🔗 https://amai-gsu.github.io/amai-gpu-scheduler/

Book GPU cards on the lab's nodes straight from the page. No approval step: a booking takes effect
the moment you submit it, and the page refuses windows where the cards are already taken.

## For lab members

1. Open the link above and click **Sign in** (top right). The page walks you through creating a
   GitHub token (classic, `public_repo` scope only). Paste it once; your browser remembers it.
2. Pick a node, click a start and an end day on the calendar (the numbers are free cards per day),
   say what it's for, tick **Can share** / **Can be preempted** if that applies, optionally type
   the exact GPU ids you want (`0,2`), and click **Book**.
3. Run with the cards you were given, e.g. `CUDA_VISIBLE_DEVICES=0,2`. Ids match `nvidia-smi` on
   the node.
4. Done early? Click **Release early** on your booking so others can use the cards.

You need **Write** access to this repository to book. Ask a lab admin to add you under
Settings → Collaborators.

## For admins

- **Add a member**: Settings → Collaborators and teams → Add people → role **Write**.
- **Cancel someone's booking**: sign in as a repository Maintainer/Admin; the **All bookings** tab
  shows a *Cancel booking* button.
- **Add or change nodes**: edit [`nodes.json`](nodes.json) and commit. Fields: `id`, `name`,
  `model`, `cards`, `memoryGb`, `status` (`available` or `maintenance`), `note`.
- **Fix a booking by hand**: edit [`bookings.json`](bookings.json); every booking is one object
  with `uid`, `gpuId`, `count`, `start`, `end` (inclusive dates), optional `slots`, and
  `closedAt` / `cancelled` once it ends.

## How it works

The page is static (GitHub Pages, deployed by the workflow in `.github/workflows/pages.yml`).
All data lives in two JSON files in this repository, which the page reads and writes through the
GitHub Contents API using each member's own token. (Classic tokens, because the repository is owned
by a user account and GitHub does not let collaborators use fine-grained tokens there.) Every booking is therefore a commit, so
`git log bookings.json` is the audit trail. Writes are compare-and-swap on the file's SHA, so two
people booking at the same moment cannot overwrite each other.

The repository is public, so bookings (GitHub usernames, dates, purposes) are visible to anyone.
