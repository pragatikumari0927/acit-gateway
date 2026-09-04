#!/usr/bin/env bash
# Mirror canonical ECC skills (.agents/skills/) into the Qwen and Grok skill dirs.
# Only ECC-managed skills are updated/pruned (tracked in a .ecc-managed list per
# mirror); any other skills in those dirs are left untouched. Idempotent.
set -euo pipefail
src=".agents/skills"
[ -d "$src" ] || { echo "ERROR: $src missing - nothing to sync"; exit 1; }
for dst in .qwen/skills .grok/skills; do
  mkdir -p "$dst"
  list="$dst/.ecc-managed"
  if [ -f "$list" ]; then
    while IFS= read -r name; do
      [ -z "$name" ] && continue
      if [ ! -d "$src/$name" ]; then
        rm -rf "${dst:?}/$name"
        echo "pruned stale: $dst/$name"
      fi
    done < "$list"
  fi
  find "$src" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort > "$list"
  cp -ru "$src"/. "$dst"/
  echo "$dst -> $(find "$dst" -mindepth 1 -maxdepth 1 -type d | wc -l) skills"
done
