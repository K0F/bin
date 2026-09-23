#!/usr/bin/env bash
set -euo pipefail

KOFI_PAGE="kof86"

usage() {
    echo "Usage: $0 [--no-postgen] [--no-mastodon] [--no-facebook] [--no-kofi] <image-file>" >&2
    exit 1
}

DO_POSTGEN=1
DO_MASTODON=1
DO_FACEBOOK=1
DO_KOFI=1

while [ "${1:-}" = "--no-postgen" ] || [ "${1:-}" = "--no-mastodon" ] || [ "${1:-}" = "--no-facebook" ] || [ "${1:-}" = "--no-kofi" ]; do
    case "$1" in
        --no-postgen)  DO_POSTGEN=0 ;;
        --no-mastodon) DO_MASTODON=0 ;;
        --no-facebook) DO_FACEBOOK=0 ;;
        --no-kofi)     DO_KOFI=0 ;;
    esac
    shift
done

if [ "$#" -ne 1 ]; then
    usage
fi
IMAGE="$1"

if [ ! -f "$IMAGE" ]; then
    echo "ERROR: image not found: $IMAGE" >&2
    exit 1
fi

if [ -z "${EDITOR:-}" ]; then
    EDITOR="vim"
fi

echo "--> Draft message in $EDITOR..."
DRAFT="$(mktemp /tmp/publish-msg-XXXXXX)"
trap 'rm -f "$DRAFT"' EXIT
$EDITOR "$DRAFT"

MSG="$(cat "$DRAFT")"
if [ -z "${MSG//[$'\t\r\n']/}" ]; then
    echo "ERROR: message is empty" >&2
    exit 1
fi

printf '%s' "Add code link? (y/N) "
read -r ADD_CODE
case "$ADD_CODE" in
    y|Y|yes|YES)
        printf '%s' "Code URL: "
        read -r CODE_URL
        if [ -n "$CODE_URL" ]; then
            MSG="$MSG

Code: $CODE_URL"
        fi
        ;;
esac

if [ "$DO_POSTGEN" -eq 1 ]; then
    echo "--> [1/4] postgen..."
    postgen "$IMAGE"
fi

if [ "$DO_MASTODON" -eq 1 ]; then
    if [ -f "$HOME/.mamot-token" ]; then
        echo "--> [2/4] Mastodon..."
        postMastodon.sh "$MSG" "$IMAGE"
    else
        echo "WARNING: ~/.mamot-token missing, skipping Mastodon" >&2
    fi
fi

if [ "$DO_FACEBOOK" -eq 1 ]; then
    printf '%s' "Publish to Facebook? (y/N) "
    read -r DO_FB
    case "$DO_FB" in
        y|Y|yes|YES) ;;
        *) DO_FACEBOOK=0 ;;
    esac
fi

if [ "$DO_FACEBOOK" -eq 1 ]; then
    if [ -f "$HOME/.facebook-token" ] && [ -f "$HOME/.facebook-page-id" ]; then
        echo "--> [3/4] Facebook..."
        postFacebook.sh "$MSG" "$IMAGE"
    else
        echo "--> [3/4] Facebook..."
        echo "    Graph API posts to Pages only (no personal-profile posting); opening browser for manual post."
        xdg-open "https://www.facebook.com/" >/dev/null 2>&1 || true
        echo "    In the browser: create a new post and upload $IMAGE"
    fi
fi

if [ "$DO_KOFI" -eq 1 ]; then
    printf '%s' "Publish to Ko-fi? (y/N) "
    read -r DO_KF
    case "$DO_KF" in
        y|Y|yes|YES) ;;
        *) DO_KOFI=0 ;;
    esac
fi

if [ "$DO_KOFI" -eq 1 ]; then
    echo "--> [4/4] Ko-fi..."
    echo "    Ko-fi has no post API; opening browser for manual post."
    xdg-open "https://ko-fi.com/$KOFI_PAGE" >/dev/null 2>&1 || true
    echo "    In the browser: Create -> Post Something -> Image, upload $IMAGE"
fi

echo "--> publish.sh done."
