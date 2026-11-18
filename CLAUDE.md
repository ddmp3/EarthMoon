# EarthMoon: start here

You are working on EarthMoon v3: a reproducible tool that **discovers** Earth places that are scientific analogs of lunar and Martian environments, explains why, and states the limits. Work follows a written plan because your context will not survive the whole project.

1. Read [docs/plan/README.md](docs/plan/README.md): context, rules, status of every task.
2. Pick the first task whose status is `todo` and whose dependencies are `done`. Read its file in `docs/plan/tasks/`. It contains everything needed.
3. When you finish a task, update its status line in the plan README, add an entry to [CHANGELOG.md](CHANGELOG.md), and merge its PR with a detailed description.

## Hard rules (never break)

- **Never deploy to Azure.** Do not run `infra/terraform/deploy.sh`, `terraform apply`, `az ...` or anything that touches the live sites. The original project is under NASA evaluation. Test locally with Docker only.
- **Never push to `ddmp3/nasa-space-app-challenge-2026-cyber-space`** (frozen for the jury). Work only in `ddmp3/EarthMoon`.
- No invented data, resolution, availability or reference. Unverified means labelled "not verified".
- Results never depend on a list of expected sites. Missing data is never a bad value.
- TDD: failing test first. Before any merge, `tools/check.sh` must pass (types, lint, tests, dependency audit, Docker e2e).
- Docs are short and human-readable. Detail goes to `docs/wiki/`, only when useful. The GitHub wiki is a mirror of `docs/wiki/` (`python tools/docs/publish_wiki.py`): never edit it by hand.

## Environment notes

- Windows host; Bash is Git Bash. Use Windows `git` for commits (WSL `git` sees false CRLF changes). Use `gh` through WSL: `wsl -e bash -lc "cd /mnt/c/Users/david/_dev.project/EarthMoon && gh ..."`.
- Node is not installed globally: see `docs/plan/README.md`, section "Tooling".
- Docker Desktop may need to be started: `Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"`.
