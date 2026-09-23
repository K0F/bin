#!/usr/bin/env bash
set -euo pipefail

INSTANCE="https://mamot.fr"
TOKEN="${MAMOT_TOKEN:-}"
if [ -z "$TOKEN" ] && [ -f "$HOME/.mamot-token" ]; then
    TOKEN="$(tr -d '\n' < "$HOME/.mamot-token")"
fi
if [ -z "$TOKEN" ]; then
    echo "ERROR: no token. Set MAMOT_TOKEN or create ~/.mamot-token" >&2
    exit 1
fi

usage() {
    echo "Usage: $0 [--edit STATUS_ID] 'post text' [audio-file]" >&2
    exit 1
}

MODE="post"
if [ "${1:-}" = "--edit" ]; then
    MODE="edit"
    shift
    if [ "$#" -lt 2 ]; then
        usage
    fi
    STATUS_ID="$1"
    shift
fi

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    usage
fi
TEXT="$1"
MEDIA="${2:-}"

json_field() {
    python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('$1','') or '')"
}

if [ "$MODE" = "edit" ]; then
    echo "--> Editing status $STATUS_ID..."
    RESP="$(curl -sS -X PUT "$INSTANCE/api/v1/statuses/$STATUS_ID" \
        -H "Authorization: Bearer $TOKEN" \
        --data-urlencode "status=$TEXT")"
    URL="$(echo "$RESP" | json_field url)"
    if [ -z "$URL" ]; then
        echo "ERROR: edit failed: $RESP" >&2
        exit 1
    fi
    echo "--> Edited: $URL"
    exit 0
fi

MEDIA_IDS=()
if [ -n "$MEDIA" ]; then
    echo "--> Uploading media: $MEDIA"
    RESP="$(curl -sS -f -X POST "$INSTANCE/api/v2/media" \
        -H "Authorization: Bearer $TOKEN" \
        -F "file=@$MEDIA" \
        -F "description=Asciisync session audio (terminal + synth/mic mix)")"
    MEDIA_ID="$(echo "$RESP" | json_field id)"
    if [ -z "$MEDIA_ID" ]; then
        echo "ERROR: media upload failed: $RESP" >&2
        exit 1
    fi
    MEDIA_IDS+=("$MEDIA_ID")
    echo "--> Media uploaded, id: $MEDIA_ID"

    echo "--> Waiting for media processing..."
    for i in $(seq 1 20); do
        STATUS="$(curl -sS -H "Authorization: Bearer $TOKEN" "$INSTANCE/api/v1/media/$MEDIA_ID")"
        if echo "$STATUS" | grep -q '"original"'; then
            echo "--> Media ready."
            break
        fi
        sleep 2
    done
fi

echo "--> Posting status..."
ARGS=(-sS -X POST "$INSTANCE/api/v1/statuses" \
    -H "Authorization: Bearer $TOKEN" \
    --data-urlencode "status=$TEXT" \
    --data-urlencode "visibility=public" \
    --data-urlencode "language=en")
for id in "${MEDIA_IDS[@]}"; do
    ARGS+=("--data-urlencode" "media_ids[]=$id")
done

RESP=""
for i in $(seq 1 10); do
    RESP="$(curl "${ARGS[@]}")"
    if echo "$RESP" | grep -q '"error"'; then
        if echo "$RESP" | grep -q 'not finished processing'; then
            echo "--> Media still processing, retry $i..."
            sleep 3
            continue
        fi
        break
    fi
    break
done
URL="$(echo "$RESP" | json_field url)"
if [ -z "$URL" ]; then
    echo "ERROR: post failed: $RESP" >&2
    exit 1
fi
echo "--> Posted: $URL"
