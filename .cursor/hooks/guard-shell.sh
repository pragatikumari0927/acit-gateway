#!/usr/bin/env bash
# beforeShellExecution guard: best-effort block of catastrophic commands. Fails OPEN on any error.
set +e
payload=$(cat)
cmd=$(printf '%s' "$payload" | grep -o '"command"[[:space:]]*:[[:space:]]*"[^"]*"' | head -n1 | cut -d'"' -f4)
[ -z "$cmd" ] && { printf '{"permission":"allow"}\n'; exit 0; }
if printf '%s' "$cmd" | grep -qE 'rm +-[a-zA-Z]*[rf][a-zA-Z]* +/([[:space:]]|$)|rm +-[a-zA-Z]*r[a-zA-Z]*f?[a-zA-Z]* +~|mkfs|dd +if=.*of=/dev/(sd|nvme|disk)|chmod +-R +777 +/|git +push[^|;]*--force[^|;]*(main|master)'; then
  printf '{"permission":"deny","user_message":"Blocked by ACIT guard: destructive command refused. If genuinely required, ask the user to run it manually."}\n'
  exit 0
fi
printf '{"permission":"allow"}\n'
