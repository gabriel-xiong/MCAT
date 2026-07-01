#!/usr/bin/env python3
"""Gate shell commands: deny explicitly blocked patterns. Always emits JSON."""
from __future__ import annotations

import json
import re
import sys

# .env.example is allowed; other .env* paths are treated as secret-bearing.
_SECRET_PATH = (
    r"\.env(?!\.example)(?:\.[\w-]+)?\b"
    r"|credentials\.json\b"
    r"|secrets\.json\b"
    r"|(?:^|[\s/])[\w*-]*\.(?:pem|key)\b"
    r"|service[_-]?account[^/\s]*\.json\b"
)


def allow() -> None:
    print(json.dumps({"permission": "allow"}))
    sys.exit(0)


def deny(user_msg: str, agent_msg: str) -> None:
    print(
        json.dumps(
            {
                "permission": "deny",
                "user_message": user_msg,
                "agent_message": agent_msg,
            }
        )
    )
    sys.exit(0)


def _references_secret_path(command: str) -> bool:
    return bool(re.search(_SECRET_PATH, command, re.IGNORECASE))


def main() -> None:
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, ValueError):
        allow()

    command = payload.get("command") or ""
    if not command:
        allow()

    if re.search(r"git\s+reset\s+--hard", command) or re.search(
        r"git\s+clean", command
    ) or re.search(r"git\s+push", command) or re.search(
        r"git\s+rebase", command
    ) or re.search(r"git\s+checkout\s+\.", command):
        deny(
            "Blocked: destructive git command.",
            "Use read-only git commands only (status, diff, log, branch, show, blame, ls-files).",
        )

    if command in ("printenv", "env") or command.startswith(
        "printenv "
    ) or command.startswith("env "):
        deny(
            "Blocked: printenv/env can expose secrets.",
            "Use echo $NODE_ENV or echo $PYTHONPATH for limited env inspection.",
        )

    if re.search(r"npx\s+prisma\s+db\s+push", command) or re.search(
        r"npx\s+prisma\s+migrate", command
    ):
        deny(
            "Blocked: Prisma db push/migrate.",
            "Use npx prisma studio, generate, validate, or format for inspection only.",
        )

    if re.match(r"^docker\s+run", command) or re.match(
        r"^docker\s+exec", command
    ) or re.match(r"^docker\s+compose\s+up", command) or re.match(
        r"^docker\s+system\s+prune", command
    ):
        deny(
            "Blocked: mutating Docker command.",
            "Use docker ps, docker images, docker logs, docker compose ps/logs for inspection.",
        )

    if re.search(r"npm\s+run\s+test:e2e", command):
        deny(
            "Blocked: E2E tests require explicit approval.",
            "Ask the user before running npm run test:e2e.",
        )

    if _references_secret_path(command):
        if re.search(
            r"(?:^|[;&|]\s*)(?:cat|type|head|tail|less|more|Get-Content|gc)\s+",
            command,
            re.IGNORECASE,
        ):
            deny(
                "Blocked: reading secret/credential files via shell.",
                "Do not cat/type/head .env or key files. Use .env.example for templates.",
            )

        if re.search(
            r"(?:^|[;&|]\s*)(?:grep|rg|findstr)\s+",
            command,
            re.IGNORECASE,
        ):
            deny(
                "Blocked: searching inside secret/credential files.",
                "Do not grep/rg .env or key files — contents may leak into agent output.",
            )

        if re.search(r"git\s+add\b", command, re.IGNORECASE):
            deny(
                "Blocked: staging secret/credential files.",
                "Never git add .env, *.pem, *.key, or credentials.json. Use .env.example only.",
            )

        if re.search(
            r"(?:^|[;&|]\s*)(?:source\s+|\.\s+)\.env(?!\.example)",
            command,
            re.IGNORECASE,
        ):
            deny(
                "Blocked: sourcing .env loads secrets into the shell.",
                "Do not source .env in agent shells.",
            )

    allow()


if __name__ == "__main__":
    main()
