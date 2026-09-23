#!/usr/bin/env bash
#===============================================================================
# archer_router_wifi_fix.sh — diagnose a "stuck" home router
#
# SUMMARY (context from the TP-Link/Archer troubleshooting session):
#   Symptom: Wi-Fi associates with full signal, DHCP lease obtained, but the
#   router's own IPv4 (ping, admin page, DNS, IPv4 internet) is unreachable over
#   WLAN. IPv6, DHCP and client-to-client bridging may still work — this is the
#   classic "half-wedged" router: the management plane is hung, so a web/browser
#   "Reboot" button often never executes.
#   Fix: HARD power-cycle (unplug 30–60 s, replug, wait ~2 min). Verify Wi-Fi
#   in isolation (bind each test to an interface) so an ethernet cable / second
#   NIC can't mask the result. If it still hangs with stock firmware, replace
#   the unit.
#
# USE:  bash archer_router_wifi_fix.sh            # full diagnostic
#       bash archer_router_wifi_fix.sh wifi       # verify Wi-Fi path only (post-reboot)
#       exit codes: 0 = all healthy, 1 = at least one check failed
#===============================================================================
set -u
FAIL=0
MODE="${1:-all}"                       # all | wifi

log()  { printf '\033[1;34m[%s]\033[0m %s\n' "$(date +%H:%M:%S)" "$*"; }
ok()   { printf '    \033[1;32mPASS\033[0m %s\n' "$*"; }
bad()  { printf '    \033[1;31mFAIL\033[0m %s\n' "$*"; FAIL=1; }

#--- targets ---------------------------------------------------------------
GW=$(ip -4 route show default | awk '/^default/{print $3; exit}')
IFACES=$(ip -4 -o addr show scope global | awk '{print $2}' | sort -u)

# if only wifi, filter to wireless NICs
if [ "$MODE" = "wifi" ]; then
  IFACES=$(iw dev 2>/dev/null | awk '/Interface/{print $2}')
fi

log "Gateway (IPv4): ${GW:-NONE (no default route)}"
log "Interfaces to test: $IFACES"

#--- per-interface checks --------------------------------------------------
for I in $IFACES; do
  [ -n "$I" ] || continue
  IP=$(ip -4 -o addr show dev "$I" scope global | awk '{print $4}')
  log "== $I  ($IP) =="

  [ -n "$IP" ] && ok "has IPv4 $IP" || { bad "no IPv4 on $I"; continue; }

  if [ -n "$GW" ]; then
    if ping -I "$I" -c 3 -W 2 "$GW" >/dev/null 2>&1; then
      ok "ping $GW on $I"
    else
      bad "ping $GW on $I"
      if [ "$MODE" != "wifi" ]; then
        printf '      > router not answering IPv4 on %s — try HARD power-cycle\n' "$I"
      fi
    fi
  fi

  if curl -sI -m 6 --interface "$I" "http://$GW" -o /dev/null >/dev/null 2>&1; then
    ok "admin page http://$GW reachable"
  else
    bad "admin page http://$GW not reachable"
  fi

  if curl -sI -m 8 --interface "$I" https://example.com -o /dev/null >/dev/null 2>&1; then
    ok "IPv4 internet via $I (example.com)"
  else
    bad "IPv4 internet via $I"
  fi

  # IPv6 path (optional signal)
  if ping -6 -c 2 -W 2 "fe80::1%$I" >/dev/null 2>&1; then
    ok "IPv6 link-local reachable (router alive on v6)"
  else
    log "IPv6 check skipped/absent on $I"
  fi
done

#--- DNS ------------------------------------------------------------------
log "DNS"
if getent hosts example.com >/dev/null 2>&1; then
  ok "system DNS resolves"
else
  bad "system DNS does not resolve"
fi

printf '\n'
if [ "$FAIL" -eq 0 ]; then
  log "RESULT: all checks OK"
else
  log "RESULT: failures found -> if the 'ping <gateway>' failed above, do a"
  log "        HARD power-cycle of the router (unplug 30–60s), wait 2 min,"
  log "        then re-run:  bash archer_router_wifi_fix.sh wifi"
fi
exit $FAIL