#!/usr/bin/env bash
# Quality gate. Must pass before every merge (docs/plan/README.md, section 3).
#
#   tools/check.sh [api|web|python|e2e|all]      default: all
#
# Everything runs in Docker with pinned images, so no host Node or Python is needed.
# Stages:
#   api     npm ci, tsc --noEmit, vitest, dependency audit
#   web     npm ci, API contract up to date (src/api-schema.ts), tsc -b, oxlint, vitest, vite build, dependency audit
#   python  pytest on every Python package, Markdown link check, pip-audit on the installed environment
#   e2e     docker compose up --build, wait for health, tools/validation/e2e.py, browser audit (desktop and phone)
# Dependency audit, two levels (tools/security/audit-allowlist.json explains the policy):
#   production dependencies   npm audit --omit=dev: 0 vulnerabilities, no exception
#   development dependencies  every advisory must be allowlisted with a reason and an unexpired review date
# Environment:
#   KEEP_UP=1   leave the compose stack running after e2e (default: stop it)
# Screenshots of the browser audit are written to .check/shots (git-ignored).
# This script never deploys anything.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# Docker on Windows (Git Bash) needs a Windows path and no MSYS path conversion.
ROOT_DOCKER="$(cd "$ROOT" && (pwd -W 2>/dev/null || pwd))"
export MSYS_NO_PATHCONV=1

NODE_IMG="node:22.23.5-bookworm"
PY_IMG="python:3.11.11-bookworm"
PW_IMG="mcr.microsoft.com/playwright:v1.64.1-noble"
PW_VERSION="1.64.1"

step() { printf '\n==> %s\n' "$*"; }

# Two-level dependency audit, run inside the Node container (see header).
AUDIT="npm audit --omit=dev --audit-level=low \
  && { npm audit --json || true; } | node /repo/tools/security/npm_audit_gate.mjs /repo/tools/security/audit-allowlist.json"

node_run() {  # node_run <app dir> <command>
  local app="$1" cmd="$2"
  docker run --rm \
    -v "$ROOT_DOCKER:/repo" \
    -v "earthmoon-nm-${app}:/repo/apps/${app}/node_modules" \
    -v earthmoon-npm-cache:/root/.npm \
    -w "/repo/apps/${app}" "$NODE_IMG" bash -euo pipefail -c "$cmd"
}

check_api() {
  step "API: install, types, tests, dependency audit"
  node_run api "node --test /repo/tools/security/npm_audit_gate.test.mjs \
    && npm ci --no-fund --no-audit && npx tsc --noEmit && npx vitest run && $AUDIT"
}

check_web() {
  step "Web: install, API contract, types, lint, tests, build, dependency audit"
  node_run web "npm ci --no-fund --no-audit     && npx -y openapi-typescript@7.13.0 ../api/openapi.yaml -o /tmp/api-schema.ts >/dev/null     && { diff -q --strip-trailing-cr /tmp/api-schema.ts src/api-schema.ts          || { echo 'src/api-schema.ts is out of date: run npm run generate:api in apps/web'; exit 1; }; }     && npx tsc -b && npx oxlint && npx vitest run \
    && npx vite build --outDir /tmp/web-dist --emptyOutDir && $AUDIT"
}

check_python() {
  step "Python: tests and dependency audit"
  docker run --rm \
    -v "$ROOT_DOCKER:/repo" -v earthmoon-pip-cache:/root/.cache/pip \
    -e PYTHONDONTWRITEBYTECODE=1 -w /repo "$PY_IMG" bash -euo pipefail -c "
      pip install --quiet --upgrade pip setuptools wheel
      pip install --quiet -r tools/precompute/requirements.txt \
        -r tools/analog_backend/requirements.txt -r tools/analog_backend/requirements-dev.txt         -r tools/catalog/requirements.txt pip-audit
      python -m pytest -q -p no:cacheprovider tools/precompute tools/scoring tools/validation tools/docs tools/catalog tools/research tools/profiles
      python tools/docs/check_links.py
      python tools/catalog/catalog.py check
      python tools/profiles/profiles.py
      (cd tools/analog_backend && python -m pytest -q -p no:cacheprovider)
      pip-audit --progress-spinner off"
}

wait_for() {  # wait_for <url> <seconds>
  local url="$1" limit="$2" i
  for ((i = 0; i < limit; i += 2)); do
    if docker run --rm --network host curlimages/curl:8.11.1 -fsS -o /dev/null "$url" 2>/dev/null; then return 0; fi
    sleep 2
  done
  echo "timeout waiting for $url" >&2
  return 1
}

check_e2e() {
  step "Docker: build and start the stack"
  (cd "$ROOT" && docker compose up --build -d)
  wait_for http://localhost:3001/api/health 180
  wait_for http://localhost:8080/ 60
  local status=0
  step "End-to-end tests"
  docker run --rm --network host -v "$ROOT_DOCKER:/repo" -w /repo "$PY_IMG" \
    python tools/validation/e2e.py || status=1
  step "Browser audit (desktop and phone)"
  mkdir -p "$ROOT/.check/shots"
  docker run --rm --network host --ipc=host \
    -v "$ROOT_DOCKER:/repo" -v earthmoon-pw:/pw -w /pw "$PW_IMG" bash -euo pipefail -c "
      [ -d node_modules/playwright ] || npm install --no-fund --no-audit --save-exact playwright@${PW_VERSION} >/dev/null
      cp /repo/tools/validation/ui-audit/audit.mjs .
      node audit.mjs http://localhost:8080 /repo/.check/shots" || status=1
  if [ "${KEEP_UP:-0}" != "1" ]; then (cd "$ROOT" && docker compose down); fi
  return $status
}

stage="${1:-all}"
case "$stage" in
  api) check_api ;;
  web) check_web ;;
  python) check_python ;;
  e2e) check_e2e ;;
  all) check_api; check_web; check_python; check_e2e ;;
  *) echo "usage: $0 [api|web|python|e2e|all]" >&2; exit 2 ;;
esac
step "check.sh $stage: passed"
