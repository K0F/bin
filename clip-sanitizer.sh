#!/usr/bin/env bash
# clip-sanitizer — Fleet-wide clipboard sanitizer (nukes NBSP \xc2\xa0 and ZWSP \xe2\x80\x8b)
# Runs as systemd user service and autostart on t520, bazina, and boxC

export DISPLAY="${DISPLAY:-:0}"

# Wait for X server display to become ready
while ! xset q >/dev/null 2>&1; do
    sleep 2
done

# Main event loop (resilient against clipnotify transient exits)
while true; do
    if ! clipnotify 2>/dev/null; then
        sleep 1
        continue
    fi

    # Grab clipboard content safely
    if current_content=$(xclip -selection clipboard -o 2>/dev/null); then
        if [[ -n "$current_content" ]]; then
            # Nuke NBSP (c2 a0 -> standard space) and ZWSP (e2 80 8b -> empty)
            sanitized=$(printf "%s" "$current_content" | sed 's/\xc2\xa0/ /g; s/\xe2\x80\x8b//g')
            
            # Guard: Only write back if a cheesy space was actually destroyed
            # This prevents infinite loops with clipnotify
            if [[ "$current_content" != "$sanitized" ]]; then
                printf "%s" "$sanitized" | xclip -selection clipboard -i
            fi
        fi
    fi
done
