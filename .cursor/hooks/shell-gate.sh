#!/usr/bin/env bash
# Gate shell commands: deny explicitly blocked patterns (fail-closed via hooks.json).
# Allowlist auto-run is configured separately in .cursor/permissions.json.
# Secret-path rules live in shell-gate.py (active hook); keep destructive blocks here as fallback.
set -euo pipefail

input=$(cat)

command=""
if command -v python3 >/dev/null 2>&1; then
  command=$(printf '%s' "$input" | python3 -c "import sys,json; print(json.load(sys.stdin).get('command',''))" 2>/dev/null || true)
elif command -v python >/dev/null 2>&1; then
  command=$(printf '%s' "$input" | python -c "import sys,json; print(json.load(sys.stdin).get('command',''))" 2>/dev/null || true)
fi

deny() {
  local user_msg="$1"
  local agent_msg="$2"
  cat <<EOF
{"permission":"deny","user_message":"${user_msg}","agent_message":"${agent_msg}"}
EOF
  exit 0
}

allow() {
  printf '{"permission":"allow"}\n'
  exit 0
}

if [[ -z "$command" ]]; then
  allow
fi

# Destructive / mutating git
if [[ "$command" =~ git[[:space:]]+reset[[:space:]]+--hard ]] \
  || [[ "$command" =~ git[[:space:]]+clean ]] \
  || [[ "$command" =~ git[[:space:]]+push ]] \
  || [[ "$command" =~ git[[:space:]]+rebase ]] \
  || [[ "$command" =~ git[[:space:]]+checkout[[:space:]]+\. ]]; then
  deny "Blocked: destructive git command." "Use read-only git commands only (status, diff, log, branch, show, blame, ls-files)."
fi

# Environment dumps (secrets risk)
if [[ "$command" == "printenv" ]] \
  || [[ "$command" == printenv\ * ]] \
  || [[ "$command" == "env" ]] \
  || [[ "$command" == env\ * ]]; then
  deny "Blocked: printenv/env can expose secrets." "Use echo \$NODE_ENV or echo \$PYTHONPATH for limited env inspection."
fi

# Prisma mutations
if [[ "$command" =~ npx[[:space:]]+prisma[[:space:]]+db[[:space:]]+push ]] \
  || [[ "$command" =~ npx[[:space:]]+prisma[[:space:]]+migrate ]]; then
  deny "Blocked: Prisma db push/migrate." "Use npx prisma studio, generate, validate, or format for inspection only."
fi

# Docker mutations
if [[ "$command" =~ ^docker[[:space:]]+run ]] \
  || [[ "$command" =~ ^docker[[:space:]]+exec ]] \
  || [[ "$command" =~ ^docker[[:space:]]+compose[[:space:]]+up ]] \
  || [[ "$command" =~ ^docker[[:space:]]+system[[:space:]]+prune ]]; then
  deny "Blocked: mutating Docker command." "Use docker ps, docker images, docker logs, docker compose ps/logs for inspection."
fi

# E2E tests — hold until user approves explicitly
if [[ "$command" =~ npm[[:space:]]+run[[:space:]]+test:e2e ]]; then
  deny "Blocked: E2E tests require explicit approval." "Ask the user before running npm run test:e2e."
fi

allow
