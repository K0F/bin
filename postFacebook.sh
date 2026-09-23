#!/usr/bin/env bash
set -euo pipefail

API="https://graph.facebook.com/v25.0"
TOKEN="${FACEBOOK_TOKEN:-}"
if [ -z "$TOKEN" ] && [ -f "$HOME/.facebook-token" ]; then
    TOKEN="$(tr -d '\n' < "$HOME/.facebook-token")"
fi
if [ -z "$TOKEN" ]; then
    echo "ERROR: no token. Set FACEBOOK_TOKEN or create ~/.facebook-token (long-lived Page access token)" >&2
    exit 1
fi

PAGE_ID="${FACEBOOK_PAGE_ID:-}"
if [ -z "$PAGE_ID" ] && [ -f "$HOME/.facebook-page-id" ]; then
    PAGE_ID="$(tr -d '\n' < "$HOME/.facebook-page-id")"
fi
if [ -z "$PAGE_ID" ]; then
    echo "ERROR: no page id. Set FACEBOOK_PAGE_ID or create ~/.facebook-page-id" >&2
    exit 1
fi

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    echo "Usage: $0 'post caption' [image-file]" >&2
    exit 1
fi
CAPTION="$1"
IMAGE="${2:-}"

json_field() {
    python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('$1','') or '')"
}

if [ -n "$IMAGE" ]; then
    if [ ! -f "$IMAGE" ]; then
        echo "ERROR: image not found: $IMAGE" >&2
        exit 1
    fi
    echo "--> Publishing photo to page $PAGE_ID..."
    RESP="$(curl -sS -X POST "$API/$PAGE_ID/photos" \
        -H "Authorization: Bearer $TOKEN" \
        -F "source=@$IMAGE" \
        --form-string "caption=$CAPTION")"
    ID="$(echo "$RESP" | json_field id)"
    if [ -z "$ID" ]; then
        echo "ERROR: photo post failed: $RESP" >&2
        exit 1
    fi
    echo "--> Posted photo, id: $ID"
    echo "    https://www.facebook.com/photo.php?fbid=$ID"
else
    echo "--> Publishing text post to page $PAGE_ID..."
    RESP="$(curl -sS -X POST "$API/$PAGE_ID/feed" \
        -H "Authorization: Bearer $TOKEN" \
        --data-urlencode "message=$CAPTION")"
    ID="$(echo "$RESP" | json_field id)"
    if [ -z "$ID" ]; then
        echo "ERROR: post failed: $RESP" >&2
        exit 1
    fi
    echo "--> Posted, id: $ID"
fi
