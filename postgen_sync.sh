#!/usr/bin/env bash
# postgen_sync.sh — Sync queued posts from phone-DCIM/postgen to k0f.github.io
set -euo pipefail

PHONE_POSTGEN="${PHONE_POSTGEN:-$HOME/phone-DCIM/postgen}"
REPO="${KOF_REPO:-$HOME/src/k0f.github.io}"

if [ ! -d "$PHONE_POSTGEN" ]; then
    mkdir -p "$PHONE_POSTGEN/assets" "$PHONE_POSTGEN/_posts"
fi

if [ ! -d "$REPO" ]; then
    echo "ERROR: k0f.github.io repo not found at $REPO" >&2
    exit 1
fi

COUNT=0

# Sync assets
if [ -d "$PHONE_POSTGEN/assets" ] && [ "$(ls -A "$PHONE_POSTGEN/assets" 2>/dev/null)" ]; then
    mkdir -p "$REPO/assets"
    cp -n "$PHONE_POSTGEN/assets"/* "$REPO/assets/" || true
fi

# Sync markdown posts
if [ -d "$PHONE_POSTGEN/_posts" ] && [ "$(ls -A "$PHONE_POSTGEN/_posts" 2>/dev/null)" ]; then
    mkdir -p "$REPO/_posts"
    for post in "$PHONE_POSTGEN/_posts"/*.markdown; do
        [ -e "$post" ] || continue
        base="$(basename "$post")"
        if [ ! -f "$REPO/_posts/$base" ]; then
            cp "$post" "$REPO/_posts/$base"
            COUNT=$((COUNT + 1))
        fi
    done
fi

if [ "$COUNT" -gt 0 ]; then
    echo "[postgen_sync] Synced $COUNT new post(s) to $REPO"
    cd "$REPO"
    git add .
    git commit -m "archive: sync $COUNT post(s) via postgen"
    git push origin master || git push
    echo "[postgen_sync] Successfully pushed to GitHub!"
else
    echo "[postgen_sync] No new posts to sync."
fi
