#!/usr/bin/env bash
# =============================================================================
# fleet-beacon.sh — Multi-node Realtime Telemetry Beacon (Pure Bash Fallback)
# Observatoř Telemetry Platform // Fleet Operations
#
# Broadcasts lightweight UDP telemetry packets (port 9850) every 1.5s.
# Zero external dependencies, pure coreutils + bash.
# =============================================================================

set -e

PORT=9850
INTERVAL=1.5
TARGETS=(
    "255.255.255.255"
    "192.168.1.255"
    "192.168.1.100"
    "192.168.1.102"
    "192.168.1.104"
    "192.168.1.101"
    "192.168.1.105"
    "192.168.1.103"
    "10.39.9.255"
    "10.39.9.1"
    "10.0.0.255"
    "10.0.0.18"
    "10.0.0.14"
    "91.139.118.43"
    "192.168.43.255"
    "192.168.43.1"
    "127.0.0.1"
)

# Identity resolution
if [ -z "$FLEET_NODE" ] || [ -z "$FLEET_ARCH" ]; then
    [ -f "/etc/fleet_id" ] && source "/etc/fleet_id" 2>/dev/null || true
    [ -f "$HOME/.fleet_id" ] && source "$HOME/.fleet_id" 2>/dev/null || true
fi

RAW_HOST="$(hostname -s 2>/dev/null || uname -n)"
if [ -z "$FLEET_NODE" ]; then
    if [ -d "/data/data/com.termux" ] || [ -n "$TERMUX_VERSION" ] || [ "$RAW_HOST" = "localhost" ] || [ "$RAW_HOST" = "android" ]; then
        FLEET_NODE="android"
    elif [ "$RAW_HOST" = "penguin" ]; then
        FLEET_NODE="crostini"
    else
        FLEET_NODE="$RAW_HOST"
    fi
fi
FLEET_ARCH="${FLEET_ARCH:-$(uname -m)}"
FLEET_SIGN="${FLEET_SIGN:-[${FLEET_NODE}:${FLEET_ARCH}]}"

RUN_ONCE=0
PRINT_JSON=0
for arg in "$@"; do
    case "$arg" in
        --once|-1) RUN_ONCE=1 ;;
        --json|-j) RUN_ONCE=1; PRINT_JSON=1 ;;
    esac
done

if [ "$PRINT_JSON" -eq 0 ]; then
    echo "[fleet-beacon-sh] Starting Bash telemetry beacon on $FLEET_NODE $FLEET_SIGN (port $PORT)..."
fi

prev_work=0
prev_total=0

while true; do
    # 1. CPU
    cpu_pct=0.0
    if [ -r /proc/stat ]; then
        read -r _ u n s i io irq sirq stl _ < /proc/stat 2>/dev/null || true
        work=$(( u + n + s + irq + sirq + stl ))
        total=$(( work + i + io ))
        if [ "$prev_total" -gt 0 ] && [ "$total" -gt "$prev_total" ]; then
            d_work=$(( work - prev_work ))
            d_total=$(( total - prev_total ))
            if [ "$d_total" -gt 0 ]; then
                cpu_pct=$(awk -v w="$d_work" -v t="$d_total" 'BEGIN { printf "%.1f", (w/t)*100 }')
            fi
        fi
        prev_work=$work
        prev_total=$total
    fi

    # 2. RAM
    mem_used=0.0
    mem_total=0.0
    if [ -r /proc/meminfo ]; then
        tot_kb=$(awk '/^MemTotal:/ {print $2}' /proc/meminfo)
        avail_kb=$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo)
        if [ -z "$avail_kb" ]; then
            free_kb=$(awk '/^MemFree:/ {print $2}' /proc/meminfo)
            buf_kb=$(awk '/^Buffers:/ {print $2}' /proc/meminfo)
            cache_kb=$(awk '/^Cached:/ {print $2}' /proc/meminfo)
            avail_kb=$(( free_kb + buf_kb + cache_kb ))
        fi
        if [ -n "$tot_kb" ] && [ "$tot_kb" -gt 0 ]; then
            mem_total=$(awk -v t="$tot_kb" 'BEGIN { printf "%.1f", t/1048576 }')
            used_kb=$(( tot_kb - avail_kb ))
            mem_used=$(awk -v u="$used_kb" 'BEGIN { printf "%.1f", u/1048576 }')
        fi
    fi

    # 3. Disk
    disk_mount="/"
    if [ "$FLEET_NODE" = "boxC" ] && [ -d "/mnt/kof17" ]; then
        disk_mount="/mnt/kof17"
    elif [ "$FLEET_NODE" = "bazina" ] && [ -d "/mnt/ssd" ]; then
        disk_mount="/mnt/ssd"
    fi
    df_out=$(df -B1G "$disk_mount" 2>/dev/null | tail -n 1) || df_out=""
    disk_total=$(echo "$df_out" | awk '{print $2}')
    disk_free=$(echo "$df_out" | awk '{print $4}')
    disk_total="${disk_total:-0.0}"
    disk_free="${disk_free:-0.0}"

    # 4. GPU (sysfs)
    gpu_str=""
    for gpath in /sys/class/drm/card*/device/gpu_busy_percent; do
        if [ -r "$gpath" ]; then
            gpu_val=$(cat "$gpath" 2>/dev/null || echo "")
            [ -n "$gpu_val" ] && gpu_str="Navi10 ${gpu_val}%" && break
        fi
    done

    # 5. Temp
    temp_c=0
    for tpath in /sys/class/thermal/thermal_zone0/temp /sys/class/hwmon/hwmon0/temp1_input; do
        if [ -r "$tpath" ]; then
            traw=$(cat "$tpath" 2>/dev/null || echo 0)
            [ "$traw" -gt 0 ] && temp_c=$(( traw / 1000 )) && break
        fi
    done

    # 6. Battery
    bat_pct=-1
    for bpath in /sys/class/power_supply/BAT*/capacity /sys/class/power_supply/*battery*/capacity; do
        if [ -r "$bpath" ]; then
            bval=$(cat "$bpath" 2>/dev/null || echo -1)
            [ "$bval" -ge 0 ] && bat_pct=$bval && break
        fi
    done

    # 7. Alert
    alert=""
    if [ "$FLEET_NODE" = "boxC" ] && [ "$disk_mount" = "/mnt/kof17" ]; then
        awk_crit=$(awk -v df="$disk_free" 'BEGIN { print (df < 3.0) ? 1 : 0 }')
        [ "$awk_crit" -eq 1 ] && alert="kof17 CRITICAL: ${disk_free}G free"
    elif [ "$FLEET_NODE" = "crostini" ]; then
        awk_crit=$(awk -v df="$disk_free" 'BEGIN { print (df < 1.0) ? 1 : 0 }')
        [ "$awk_crit" -eq 1 ] && alert="crostini LOW DISK: ${disk_free}G free"
    fi
    if [ "$bat_pct" -ge 0 ] && [ "$bat_pct" -le 15 ]; then
        alert="$FLEET_NODE BATTERY CRITICAL: ${bat_pct}%"
    fi

    ts=$(date +%s)
    payload=$(printf '{"name":"%s","hostname":"%s","node":"%s","arch":"%s","sign":"%s","timestamp":%s,"cpu_percent":%s,"mem_used_gb":%s,"mem_total_gb":%s,"disk_mount":"%s","disk_free_gb":%s,"disk_total_gb":%s,"gpu_str":"%s","temp_c":%d,"battery_percent":%d,"alert":"%s"}' \
        "$FLEET_NODE" "$RAW_HOST" "$FLEET_NODE" "$FLEET_ARCH" "$FLEET_SIGN" \
        "$ts" "$cpu_pct" "$mem_used" "$mem_total" \
        "$disk_mount" "$disk_free" "$disk_total" \
        "$gpu_str" "$temp_c" "$bat_pct" "$alert")

    # Broadcast UDP
    for target in "${TARGETS[@]}"; do
        if [ -w /dev/udp ]; then
            echo -n "$payload" > "/dev/udp/$target/$PORT" 2>/dev/null || true
        elif command -v socat >/dev/null 2>&1; then
            echo -n "$payload" | socat - "UDP-DATAGRAM:$target:$PORT,broadcast" 2>/dev/null || true
        elif command -v nc >/dev/null 2>&1; then
            echo -n "$payload" | nc -u -w1 "$target" "$PORT" 2>/dev/null || true
        fi
    done

    # Update SHM cache
    shm_fleet="/dev/shm/fleet_telemetry.json"
    tmp_path="${shm_fleet}.tmp.$$"
    if [ -f "$shm_fleet" ]; then
        # Merge using awk/sed
        grep -v "\"${FLEET_NODE}\":" "$shm_fleet" 2>/dev/null | sed -e 's/^}$//' > "$tmp_path" || true
        echo "  ,\"${FLEET_NODE}\": $payload" >> "$tmp_path"
        echo "}" >> "$tmp_path"
    else
        printf '{\n  "%s": %s\n}\n' "$FLEET_NODE" "$payload" > "$tmp_path"
    fi
    chmod 666 "$tmp_path" 2>/dev/null || true
    mv -f "$tmp_path" "$shm_fleet" 2>/dev/null || true

    # WAN HTTP fallback
    if [ "$FLEET_NODE" != "boxC" ]; then
        if command -v curl >/dev/null 2>&1; then
            curl -s -m 1.5 -X POST "http://91.139.118.43/telemetry.php" \
                -H "Content-Type: application/json" -d "$payload" >/dev/null 2>&1 || true
        fi
    fi

    if [ "$PRINT_JSON" -eq 1 ]; then
        echo "$payload"
    fi

    [ "$RUN_ONCE" -eq 1 ] && break
    sleep "$INTERVAL"
done
