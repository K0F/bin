#!/usr/bin/env bash

while clipnotify; do
    # Grab what was just copied
    current_content=$(xclip -selection clipboard -o 2>/dev/null)
    
    if [[ -n "$current_content" ]]; then
        # Nuke NBSP (c2 a0) and ZWSP (e2 80 8b)
        sanitized=$(echo -n "$current_content" | sed 's/\xc2\xa0/ /g; s/\xe2\x80\x8b//g')
        
        # Guard: Only write back if a cheesy space was actually destroyed
        # This prevents an infinite event loop
        if [[ "$current_content" != "$sanitized" ]]; then
            echo -n "$sanitized" | xclip -selection clipboard -i
        fi
    fi
done
