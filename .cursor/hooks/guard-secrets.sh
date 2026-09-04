#!/usr/bin/env bash
# beforeReadFile guard: best-effort block of secret files. Fails OPEN (allow) on any error.
set +e
payload=$(cat)
path=$(printf '%s' "$payload" | grep -o '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' | head -n1 | cut -d'"' -f4)
base=${path##*/}
deny() { printf '{"permission":"deny","user_message":"%s"}\n' "$1"; exit 0; }
allow() { printf '{"permission":"allow"}\n'; exit 0; }
[ -z "$base" ] && allow
case "$base" in
  .env.example|.env.sample|.env.template) allow ;;
  *.env*) deny "Blocked: '$base' may contain secrets. Use .env.example for structure." ;;
  *.pem|*.key|*.p12|*.pfx|*.kdbx|id_rsa*|id_ed25519*) deny "Blocked: '$base' looks like a key/certificate file." ;;
esac
allow
