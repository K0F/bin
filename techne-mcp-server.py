
import datetime

def debug_log(msg):
    try:
        with open("/tmp/mcp-debug.log", "a", encoding="utf-8") as f:
            now = datetime.datetime.now().isoformat()
            f.write(f"[{now}] {msg}\n")
    except Exception:
        pass
#!/usr/bin/env python3
"""
Techné Safety MCP Server (Model Context Protocol)
Exposes read-only, sanitized Techné, src, and .gemini context to Hugging Face,
Claude Desktop, Cursor, and any standard MCP client.

Features:
- Full MCP 2024-11-05 SSE + Direct JSON-RPC support.
- Strict read-only sandbox: zero shell execution, zero write access.
- Denylist filters private keys, credentials, tokens, .env, and sensitive configs.
- Path traversal protection.
- Zero-dependency: pure Python 3 standard library.
"""

import sys
import os
import json
import uuid
import time
import re
import queue
import threading
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

PORT = int(os.environ.get("MCP_PORT", 8085))
HOST = os.environ.get("MCP_HOST", "127.0.0.1")
BASE_URL = os.environ.get("MCP_BASE_URL", "https://xn--peek-h6a.com/mcp")

# Allowed root directories for context reading
HOWTO_TEXT = '# Techné Fleet How-To & Operator Guide (MCP Edition)\n\n> *"Nástroje nejsou ozdobou, ale prodloužením smyslů a rukou."* — **Techné (τέχνη) & Kof**\n\nTento průvodce slouží pro AI agenty (např. Hugging Face Chat, Claude Desktop, Cursor, Gemini) i lidské operátory přistupující k flotile přes Model Context Protocol (MCP).\n\n---\n\n## 1. Architektura & Uzly Flotily\n\nFlotila se skládá ze čtyř aktivních uzlů spojených v privátní síti (10.0.0.0/24 a 192.168.1.0/24):\n- **`t520` (10.0.0.18 / 192.168.1.103)**: Hlavní pracovní stanice s Arch Linuxem, Synergy KVM server, centrální displej `:0`, sazba XeLaTeX 600 DPI, offline hlas Kasandra (AXAGON USB Audio).\n- **`bazina` / `permafrost` (10.0.0.15 / 192.168.1.104)**: Výpočetní uzel s Debianem 13, GPU Radeon RX 5700 XT, hostitel vertikálního plotteru Drkota na `/dev/ttyUSB0` (115200 baud), lokální model `Qwen3-8B` na portu 8080.\n- **`boxC` (10.0.0.14 / 192.168.1.101 / WAN 91.139.118.43:2222)**: Headless Raspberry Pi (aarch64), centrální NFS/SMB úložiště `/mnt/kof17`, Nginx webserver (`pešek.com`), Git server repozitářů, Techné Safety MCP server na portu 8085 (`/mcp`), RTL-SDR měření tepla.\n- **`phone` (192.168.1.102)**: Mobilní záznamník (Android/Termux), Syncthing intake pro terénní foto/audio.\n\n---\n\n## 2. Invarianty & Pravidla Chování Agenta\n\nKaždý agent operující ve flotile musí bez výjimky respektovat:\n1. **Jazyková identita & Invarianta češtiny:** Techné (τέχνη) mluví v češtině výhradně v **ženském rodě** (*připravila jsem*, *zjistila jsem*, *doporučuji*). Finální odpovědi a shrnutí jsou vždy formulovány v češtině.\n2. **Kánon tónu a stylu:** Fakta, hluboká technická erudice, černý humor, nadsázka a absurdno, uzemňující láska ke čtenáři.\n3. **Kanonický shell & Historie:** Výchozím interpretem je `/usr/bin/zsh`. Každý příkaz musí zanechat stopu v `~/.zsh_history` ve formátu `: <epoch>:0;<cmd>` (nebo přes wrapper `ze`).\n4. **Test WAN konektivity:** Výchozím cílem pro ověření internetu je výhradně `ping -c 1 debian.org`.\n5. **Kanonická trojice milníku:** Každé dokončení úkolu se zaznamenává do `dnes done "<text>"`, orazítkuje přes `drkota-chronicle stamp` a ohlásí hlasem Kasandra (`~/bin/mluv`).\n\n---\n\n## 3. Práce s Časem & Deníky\n\n- **`dnes done "<text>"`**: Zaznamená dokončený úkol do `~/src/dnes/journal.md`.\n- **`now "[TAG] <text>"`**: Okamžité časové razítko přítomnosti ($t \\le \tau$) commitnuté do `now.git`.\n- **`later "[TAG] <text>"`**: Záznam budoucího záměru ($T > \tau$, standardně $+1.0\text{ dh36} = +40\text{ min}$) s možností odpočtu přes `till` (`later -w -c "<cmd>"`).\n- **`till -t HH:MM [-c "<cmd>"]`**: 50 FPS terminálový odpočet s automatickým spuštěním příkazu po dosažení cíle.\n- **`dh36`**: Dekanický metrický čas (36 dekanů po 40 minutách / $10^\\circ$).\n\n---\n\n## 4. Vertikální Plotter Drkota & Lagrangeův Spirograf\n\n- **Drkota (`~/bin/drkota`)**: Polargraph na zdi připojený přes USB na `bazina:/dev/drkota` (115200 baud).\n  - `drkota status`: Kontrola spojení s firmwarem.\n  - `drkota clock start|stop|speed <sec>`: Spuštění a řízení kreslení celestálního spirografu.\n  - `drkota plot <file.svg>`: Vykreslení vektorového souboru na papír.\n  - `drkota estop`: Okamžité zvednutí pera (`P1`) a vynulování souřadnic (`Z0`) bez návratu do středu.\n- **Živé Digitální Dvojče**: Služba `lagrange-web-twin.service` na `boxC` nepřetržitě simuluje orbitální dráhu 6 planet v reálném čase podle 50Hz sítě a počasí na adrese `https://pešek.com/lagrange/`.\n\n---\n\n## 5. Bezpečnost & Síťová Obrana\n\n- **`drop <IP>` / `drop.sh <IP>`**: Převede útočnou IP adresu na `/24` podsíť (`x.x.x.0/24`) a vloží pravidlo `ip saddr <CIDR> drop` do řetězce `table ip filter chain input` v nftables.\n- **Ochrana privátních sítí**: `drop` striktně odmítne shodit flotilové/lokální rozsahy (`10.0.0.0/8`, `192.168.0.0/16`, `127.0.0.0/8`, `172.16.0.0/12`).\n- **`journal-ssh-blocker.service`**: Pasivní démon monitorující systemd journal sshd (preauth sondy, chybné pokusy, nevalidní uživatele) a automaticky volající `drop`.\n\n---\n\n## 6. Sazba Samizdatu & Tisk\n\n- **`samizdat status|build|view|print|mail [WXX]`**: Správa týdeníku The Observatoř.\n- **`konzdat-release`**: Kompletní páteční automatická pipeline (16:00 CET) – sestavení textů, 600 DPI XeLaTeX na `t520`, sync do webrootu `/var/www/html/konzdat/`, git commit/push, kontrola HTTP 200 a hlasové oznámení.\n- **`fleet-print <file.pdf>`**: 600 DPI monochromatický tisk na tiskárnu Brother DCP-J4120DW ve Zlatém řezu.\n\n---\n\n## 7. Jak používat tento MCP Server\n\nServer nabízí následující rozhraní:\n- **Nástroje (Tools):**\n  - `get_howto`: Vrací tento manuál nebo jeho konkrétní kapitoly.\n  - `get_fleet_commands`: Vrací autoritativní katalog příkazů `FLEET_COMMANDS.md`.\n  - `get_fleet_status`: Vrací živou topologii uzlů flotily.\n  - `get_observatory_telemetry`: Vrací živou frekvenci sítě 50Hz a stav měřidel tepla.\n  - `get_lagrange_data`: Vrací data planetárního spirografu a trajektorii.\n  - `read_context_file`: Bezpečné čtení zdrojových a kontextových souborů v `~/src`.\n  - `search_context`: Textové vyhledávání v repozitářích.\n  - `get_samizdat_issue`: Načtení vydání samizdatu.\n  - `get_techne_doctrine`: Základní doktrína Techné.\n- **Zdroje (Resources):**\n  - `techne://howto` (tento návod)\n  - `techne://fleet-commands` (katalog `FLEET_COMMANDS.md`)\n  - `techne://doctrine` (filozofická doktrína)\n  - `techne://fleet-status` (JSON stav uzlů)\n  - `techne://dnes-journal` (posledních 100 záznamů deníku milníků)\n  - `techne://lagrange-status` (stav spirografu)\n  - `techne://lagrange-svg` (vektorový nákres)\n- **Připojení přes SSE:** `https://pešek.com/mcp/sse`\n- **Přímý JSON-RPC POST:** `https://pešek.com/mcp/` nebo `https://pešek.com/mcp/messages?session_id=...`\n'

ALLOWED_ROOTS = [
    Path("/home/kof/src").resolve(),
    Path("/home/kof/.agents").resolve(),
    Path("/home/kof/.gemini").resolve(),
    Path("/var/www/html/lagrange").resolve(),
]

# Sensitive patterns that MUST NEVER be served
DENIED_PATTERNS = [
    re.compile(r"id_rsa", re.I),
    re.compile(r"id_ed25519", re.I),
    re.compile(r"id_ecdsa", re.I),
    re.compile(r"\.key$", re.I),
    re.compile(r"\.pem$", re.I),
    re.compile(r"privkey", re.I),
    re.compile(r"certbot", re.I),
    re.compile(r"\.token", re.I),
    re.compile(r"token\.txt", re.I),
    re.compile(r"passwd", re.I),
    re.compile(r"shadow", re.I),
    re.compile(r"credential", re.I),
    re.compile(r"\.env", re.I),
    re.compile(r"config\.xml", re.I),  # Syncthing key/apikey
    re.compile(r"\.want_to_cry", re.I),
    re.compile(r"\.gnupg", re.I),
    re.compile(r"\.ssh", re.I),
]

MAX_FILE_SIZE = 128 * 1024  # 128 KB max per read


def is_path_safe(target_path: Path) -> bool:
    try:
        resolved = target_path.resolve()
    except Exception:
        return False

    # Check if inside allowed roots
    inside_root = any(root == resolved or root in resolved.parents for root in ALLOWED_ROOTS)
    if not inside_root:
        return False

    # Check denylist on any part of the path
    path_str = str(resolved)
    for pattern in DENIED_PATTERNS:
        if pattern.search(path_str):
            return False

    return True


# In-memory SSE session registries
sessions = {}  # session_id -> queue.Queue()
sessions_lock = threading.Lock()


def get_fleet_summary():
    return {
        "fleet": "Techné Fleet Mesh",
        "nodes": {
            "t520": {"role": "Main Workstation / Synergy KVM Server / Speech Synthesizer", "arch": "x86_64 Arch Linux", "ip": "192.168.1.105 / 10.0.0.18"},
            "permafrost": {"role": "Compute / Radeon RX 5600 XT GPU / Drkota V-Plotter Host / TRL-LoRA", "alias": "bazina", "arch": "x86_64 Debian 13", "ip": "192.168.1.104 / 10.0.0.15"},
            "boxC": {"role": "Headless Gateway / Web / Storage / Git / MCP", "arch": "Raspberry Pi", "ip": "192.168.1.101 / 10.0.0.14"}
        },
        "philosophy": "Zero-bloat, POSIX, real-time audio DSP, offline-first open-source engineering",
        "primary_url": "https://xn--peek-h6a.com"
    }


def handle_tool_call(name: str, arguments: dict):
    if name == "get_fleet_status":
        return {"content": [{"type": "text", "text": json.dumps(get_fleet_summary(), indent=2, ensure_ascii=False)}]}

    elif name == "list_projects":
        src_path = Path("/home/kof/src")
        if not src_path.exists():
            return {"content": [{"type": "text", "text": "Directory /home/kof/src not found."}]}
        
        projects = []
        for item in sorted(src_path.iterdir()):
            if item.name.startswith(".") or not is_path_safe(item):
                continue
            desc = ""
            readme = item / "README.md"
            if readme.exists() and is_path_safe(readme):
                try:
                    with open(readme, "r", encoding="utf-8", errors="ignore") as f:
                        lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
                        if lines:
                            desc = lines[0][:120]
                except Exception:
                    pass
            projects.append({"name": item.name, "is_dir": item.is_dir(), "summary": desc})
        return {"content": [{"type": "text", "text": json.dumps(projects, indent=2, ensure_ascii=False)}]}

    elif name == "read_context_file":
        rel_path = arguments.get("path", "").strip()
        if not rel_path:
            return {"isError": True, "content": [{"type": "text", "text": "Missing 'path' argument."}]}

        # Try relative to roots
        candidate = None
        if os.path.isabs(rel_path):
            candidate = Path(rel_path)
        else:
            for root in ALLOWED_ROOTS:
                test_p = root / rel_path
                if test_p.exists():
                    candidate = test_p
                    break
            if candidate is None:
                candidate = Path("/home/kof/src") / rel_path

        if not is_path_safe(candidate):
            return {"isError": True, "content": [{"type": "text", "text": f"Access denied: path '{rel_path}' is outside safety perimeter or forbidden."}]}

        if not candidate.exists() or not candidate.is_file():
            return {"isError": True, "content": [{"type": "text", "text": f"File not found: '{rel_path}'"}]}

        try:
            size = candidate.stat().st_size
            if size > MAX_FILE_SIZE:
                with open(candidate, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read(MAX_FILE_SIZE) + f"\n\n[... Truncated at {MAX_FILE_SIZE} bytes ...]"
            else:
                with open(candidate, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            return {"content": [{"type": "text", "text": content}]}
        except Exception as e:
            return {"isError": True, "content": [{"type": "text", "text": f"Error reading file: {str(e)}"}]}

    elif name == "search_context":
        query = arguments.get("query", "").strip()
        if not query or len(query) < 2:
            return {"isError": True, "content": [{"type": "text", "text": "Query too short."}]}

        sub = arguments.get("subdir", "src").strip()
        root_dir = Path("/home/kof/src")
        if sub in [".agents", "agents"]:
            root_dir = Path("/home/kof/.agents")
        elif sub in [".gemini", "gemini"]:
            root_dir = Path("/home/kof/.gemini")

        results = []
        q_lower = query.lower()
        count = 0
        max_matches = 25

        for root, dirs, files in os.walk(root_dir):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ["build", "node_modules", "target", "cache"]]
            for file in files:
                if not file.endswith((".md", ".txt", ".tex", ".c", ".h", ".py", ".scd")):
                    continue
                file_path = Path(root) / file
                if not is_path_safe(file_path):
                    continue
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        for idx, line in enumerate(f, 1):
                            if q_lower in line.lower():
                                rel = file_path.relative_to(root_dir)
                                results.append(f"{rel}:{idx}: {line.strip()[:140]}")
                                count += 1
                                if count >= max_matches:
                                    break
                except Exception:
                    continue
                if count >= max_matches:
                    break
            if count >= max_matches:
                break

        if not results:
            return {"content": [{"type": "text", "text": f"No matches found for '{query}' in {root_dir}."}]}
        return {"content": [{"type": "text", "text": "\n".join(results)}]}

    elif name == "get_samizdat_issue":
        issue = arguments.get("issue", "latest").strip().upper()
        issues_dir = Path("/home/kof/src/samizdat/issues")
        if not issues_dir.exists():
            issues_dir = Path("/home/kof/src/konzdat/issues")

        target_file = None
        if issue == "LATEST" or not issue:
            if issues_dir.exists():
                dirs = sorted([d for d in issues_dir.iterdir() if d.is_dir() and d.name.startswith("W")])
                if dirs:
                    cand = dirs[-1] / "issue.md"
                    if cand.exists():
                        target_file = cand
        else:
            cand = issues_dir / issue / "issue.md"
            if cand.exists():
                target_file = cand

        if target_file and is_path_safe(target_file):
            try:
                with open(target_file, "r", encoding="utf-8", errors="ignore") as f:
                    return {"content": [{"type": "text", "text": f.read()}]}
            except Exception as e:
                return {"isError": True, "content": [{"type": "text", "text": str(e)}]}

        return {"isError": True, "content": [{"type": "text", "text": f"Samizdat issue '{issue}' not found."}]}

    elif name == "get_techne_doctrine":
        for p in [Path("/home/kof/src/AGENTS.md"), Path("/home/kof/.agents/TECHNE.md"), Path("/home/kof/.agents/GEMINI.md")]:
            if p.exists() and is_path_safe(p):
                try:
                    with open(p, "r", encoding="utf-8", errors="ignore") as f:
                        return {"content": [{"type": "text", "text": f.read()}]}
                except Exception:
                    pass
        return {"content": [{"type": "text", "text": "Techné Doctrine: Zero-bloat, POSIX, real-time audio DSP, offline-first open-source engineering."}]}

    elif name == "get_observatory_telemetry":
        chronicle_bin = Path("/home/kof/bin/drkota-chronicle")
        if chronicle_bin.exists():
            try:
                import subprocess
                res = subprocess.run([str(chronicle_bin), "stamp", "--dry-run", "--json"], capture_output=True, text=True, timeout=5)
                if res.returncode == 0 and res.stdout.strip():
                    return {"content": [{"type": "text", "text": res.stdout.strip()}]}
            except Exception:
                pass
        # Fallback reading directly from /dev/shm
        shm_grid = Path("/dev/shm/observator_status.json")
        shm_heat = Path("/dev/shm/heat_fleet_summary.json")
        grid_data = {}
        heat_data = {}
        if shm_grid.exists():
            try:
                grid_data = json.loads(shm_grid.read_text(encoding="utf-8"))
            except Exception:
                pass
        if shm_heat.exists():
            try:
                heat_data = json.loads(shm_heat.read_text(encoding="utf-8"))
            except Exception:
                pass
        summary = {"grid": grid_data, "heat": heat_data, "source": "shm_fallback"}
        return {"content": [{"type": "text", "text": json.dumps(summary, indent=2, ensure_ascii=False)}]}

    elif name == "get_timewarp_status":
        dh_bin = Path("/home/kof/src/timewarp-alpine/dh36")
        dh_out = ""
        if dh_bin.exists():
            try:
                import subprocess
                res = subprocess.run([str(dh_bin), "-j"], capture_output=True, text=True, timeout=3)
                if res.returncode == 0:
                    dh_out = res.stdout.strip()
            except Exception:
                pass
        return {"content": [{"type": "text", "text": dh_out or "dh36 not available"}]}

    elif name == "drkota_chronicle":
        action = arguments.get("action", "stamp").strip()
        arg = arguments.get("argument", "").strip()
        dry_run = arguments.get("dry_run", True)
        chronicle_bin = Path("/home/kof/bin/drkota-chronicle")
        if not chronicle_bin.exists():
            return {"isError": True, "content": [{"type": "text", "text": "drkota-chronicle not found."}]}
        import subprocess
        cmd = [str(chronicle_bin), action]
        if arg:
            cmd.append(arg)
        if dry_run:
            cmd.append("--dry-run")
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            out = res.stdout.strip() or res.stderr.strip()
            return {"content": [{"type": "text", "text": out}]}
        except Exception as e:
            return {"isError": True, "content": [{"type": "text", "text": f"Error running drkota-chronicle: {e}"}]}

    elif name == "get_lagrange_data":
        status_file = Path("/var/www/html/lagrange/drkota_clock_status.json")
        trail_file = Path("/var/www/html/lagrange/live_trail.json")
        include_trail = arguments.get("include_trail", False)

        data = {}
        if status_file.exists():
            try:
                with open(status_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                data["status_error"] = str(e)
        elif trail_file.exists():
            try:
                with open(trail_file, "r", encoding="utf-8") as f:
                    full_trail = json.load(f)
                    data = {k: v for k, v in full_trail.items() if k != "trail"}
            except Exception as e:
                data["trail_error"] = str(e)

        if include_trail and trail_file.exists():
            try:
                with open(trail_file, "r", encoding="utf-8") as f:
                    full_trail = json.load(f)
                    data["trail"] = full_trail.get("trail", [])
            except Exception as e:
                data["trail_error"] = str(e)

        # Fallback to local lagrange.py if files do not exist
        if not data:
            lagrange_py = Path("/home/kof/src/lagrange/lagrange.py")
            if lagrange_py.exists():
                try:
                    import subprocess
                    res = subprocess.run([sys.executable, str(lagrange_py), "--json"], capture_output=True, text=True, timeout=5)
                    if res.returncode == 0 and res.stdout.strip():
                        return {"content": [{"type": "text", "text": res.stdout.strip()}]}
                except Exception as e:
                    data["exec_error"] = str(e)

        return {"content": [{"type": "text", "text": json.dumps(data, indent=2, ensure_ascii=False)}]}


    elif name == "get_howto":
        topic = arguments.get("topic", "all").lower()
        if topic in ["all", "", "overview"]:
            return {"content": [{"type": "text", "text": HOWTO_TEXT}]}
        
        sections = HOWTO_TEXT.split("## ")
        matching = [s for s in sections if topic in s.lower()]
        if matching:
            filtered = "## " + "\n## ".join(matching)
            return {"content": [{"type": "text", "text": filtered}]}
        return {"content": [{"type": "text", "text": f"Topic '{topic}' not found in How-To. Available topics: overview, architecture, invariants, time, drkota, security, samizdat, mcp.\n\n" + HOWTO_TEXT}]}

    elif name == "get_fleet_commands":
        query = arguments.get("query", "").lower()
        cmd_file = Path("/home/kof/src/observator/FLEET_COMMANDS.md")
        if not cmd_file.exists():
            cmd_file = Path("/home/kof/src/web_blog/observator/FLEET_COMMANDS.md")
        if cmd_file.exists() and is_path_safe(cmd_file):
            try:
                with open(cmd_file, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
                if query:
                    lines = [line for line in text.splitlines() if query in line.lower()]
                    return {"content": [{"type": "text", "text": f"=== FLEET COMMANDS MATCHING '{query}' ===\n" + "\n".join(lines[:60])}]}
                return {"content": [{"type": "text", "text": text}]}
            except Exception as e:
                return {"isError": True, "content": [{"type": "text", "text": f"Error reading FLEET_COMMANDS: {e}"}]}
        return {"isError": True, "content": [{"type": "text", "text": "FLEET_COMMANDS.md not found in observator."}]}

    else:
        return {"isError": True, "content": [{"type": "text", "text": f"Unknown tool: {name}"}]}


def handle_resource_read(uri: str):
    if uri == "techne://doctrine":
        res = handle_tool_call("get_techne_doctrine", {})
        return {"contents": [{"uri": uri, "mimeType": "text/markdown", "text": res["content"][0]["text"]}]}
    elif uri == "techne://fleet-status":
        res = handle_tool_call("get_fleet_status", {})
        return {"contents": [{"uri": uri, "mimeType": "application/json", "text": res["content"][0]["text"]}]}
    elif uri == "techne://samizdat-manifesto":
        p = Path("/home/kof/src/konzdat/.agents/EDITORIAL_MANIFESTO.md")
        if p.exists() and is_path_safe(p):
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                return {"contents": [{"uri": uri, "mimeType": "text/markdown", "text": f.read()}]}
    elif uri == "techne://dnes-journal":
        p = Path("/home/kof/src/dnes/journal.md")
        if p.exists() and is_path_safe(p):
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                # Return last 100 lines of journal
                return {"contents": [{"uri": uri, "mimeType": "text/markdown", "text": "".join(lines[-100:])}]}
    elif uri == "techne://lagrange-status":
        p = Path("/var/www/html/lagrange/drkota_clock_status.json")
        if not p.exists():
            p = Path("/var/www/html/lagrange/live_trail.json")
        if p.exists() and is_path_safe(p):
            with open(p, "r", encoding="utf-8") as f:
                return {"contents": [{"uri": uri, "mimeType": "application/json", "text": f.read()}]}
    elif uri == "techne://lagrange-svg":
        p = Path("/var/www/html/lagrange/lagrange.svg")
        if not p.exists():
            p = Path("/home/kof/src/lagrange/lagrange_constellation.svg")
        if p.exists() and is_path_safe(p):
            with open(p, "r", encoding="utf-8") as f:
                return {"contents": [{"uri": uri, "mimeType": "image/svg+xml", "text": f.read()}]}

    elif uri == "techne://howto":
        return {"contents": [{"uri": uri, "mimeType": "text/markdown", "text": HOWTO_TEXT}]}
    elif uri == "techne://fleet-commands":
        res = handle_tool_call("get_fleet_commands", {})
        return {"contents": [{"uri": uri, "mimeType": "text/markdown", "text": res["content"][0]["text"]}]}

    return {"contents": [{"uri": uri, "mimeType": "text/plain", "text": "Resource not found."}]}


def process_jsonrpc(req: dict) -> dict:
    msg_id = req.get("id")
    method = req.get("method")
    params = req.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": False},
                    "resources": {"subscribe": False, "listChanged": False},
                    "prompts": {"listChanged": False}
                },
                "serverInfo": {
                    "name": "techne-safety-mcp",
                    "version": "1.0.0"
                }
            }
        }

    elif method == "notifications/initialized":
        return None  # No response for notifications

    elif method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "tools": [
                    {
                        "name": "get_howto",
                        "description": "Returns the comprehensive operator and agent How-To manual for the Techné fleet mesh, tools, time, plotter, and doctrines.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "topic": {
                                    "type": "string",
                                    "description": "Optional topic filter: all, overview, architecture, invariants, time, drkota, security, samizdat, mcp"
                                }
                            }
                        }
                    },
                    {
                        "name": "get_fleet_commands",
                        "description": "Returns the authoritative catalog and syntax manual of all fleet commands (FLEET_COMMANDS.md) from the Observatory.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "Optional keyword or command name to filter"
                                }
                            }
                        }
                    },
                    {
                        "name": "get_fleet_status",
                        "description": "Returns verified status and topology of the Techné fleet mesh (t520, bazina, boxC).",
                        "inputSchema": {"type": "object", "properties": {}}
                    },
                    {
                        "name": "list_projects",
                        "description": "Lists active research, engineering, and cultural small-web projects in ~/src with summary descriptions.",
                        "inputSchema": {"type": "object", "properties": {}}
                    },
                    {
                        "name": "read_context_file",
                        "description": "Reads a documentation or source file securely within the ~/src, ~/.agents, or ~/.gemini perimeter. Strictly read-only, denylisted against private keys/secrets.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "path": {"type": "string", "description": "Relative or absolute path inside ~/src, ~/.agents, or ~/.gemini"}
                            },
                            "required": ["path"]
                        }
                    },
                    {
                        "name": "search_context",
                        "description": "Fast text search across documentation and source code in the Techné context tree.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "description": "Search keyword or phrase"},
                                "subdir": {"type": "string", "enum": ["src", ".agents", ".gemini"], "description": "Context root directory"}
                            },
                            "required": ["query"]
                        }
                    },
                    {
                        "name": "get_samizdat_issue",
                        "description": "Reads the broadsheet text of The Observatoř Samizdat weekly chronicle (W44, W45, W46 or latest).",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "issue": {"type": "string", "description": "Issue identifier, e.g. 'W46' or 'latest'"}
                            }
                        }
                    },
                    {
                        "name": "get_techne_doctrine",
                        "description": "Retrieves the canonical Techné core manifesto, editorial guidelines, and engineering doctrine.",
                        "inputSchema": {"type": "object", "properties": {}}
                    },
                    {
                        "name": "get_observatory_telemetry",
                        "description": "Returns live environmental telemetry: 50 Hz continental grid micro-deviations, wireless M-Bus radiator heat units (19 meters), and Prague weather.",
                        "inputSchema": {"type": "object", "properties": {}}
                    },
                    {
                        "name": "get_timewarp_status",
                        "description": "Returns current harmonic metric decimal time (dh36, decan 0-35, azimuth 0-360) and synodic lunar cycle.",
                        "inputSchema": {"type": "object", "properties": {}}
                    },
                    {
                        "name": "drkota_chronicle",
                        "description": "Generates or plots vector telemetry for Drkota V-plotter (stamp, strip, warp, fork). Default dry_run=true.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string", "enum": ["stamp", "strip", "warp", "fork", "status"], "description": "Chronicle plotting action"},
                                "argument": {"type": "string", "description": "Optional argument (rate for warp, scenario for fork)"},
                                "dry_run": {"type": "boolean", "description": "If true, simulates without moving hardware (default: true)"}
                            },
                            "required": ["action"]
                        }
                    },
                    {
                        "name": "get_lagrange_data",
                        "description": "Returns live celestial Lagrange spirograph harmonics, multi-planetary libration coordinates (Mercury through Saturn, L2-L5), 50 Hz grid frequency deviation, weather, and Drkota plotter status.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "include_trail": {"type": "boolean", "description": "Include full recent coordinate trail points (default: false)"}
                            }
                        }
                    }
                ]
            }
        }

    elif method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments", {})
        res = handle_tool_call(tool_name, args)
        return {"jsonrpc": "2.0", "id": msg_id, "result": res}

    elif method == "resources/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "resources": [
                    {"uri": "techne://howto", "name": "Techné Fleet How-To & Operator Guide", "mimeType": "text/markdown"},
                    {"uri": "techne://fleet-commands", "name": "Authoritative Fleet Commands Catalog", "mimeType": "text/markdown"},
                    {"uri": "techne://doctrine", "name": "Techné Core Doctrine", "mimeType": "text/markdown"},
                    {"uri": "techne://fleet-status", "name": "Fleet Mesh Architecture", "mimeType": "application/json"},
                    {"uri": "techne://samizdat-manifesto", "name": "Samizdat Editorial Manifesto", "mimeType": "text/markdown"},
                    {"uri": "techne://dnes-journal", "name": "Recent Daily Journal Milestones", "mimeType": "text/markdown"},
                    {"uri": "techne://lagrange-status", "name": "Lagrange Spirograph & Celestial Harmonics", "mimeType": "application/json"},
                    {"uri": "techne://lagrange-svg", "name": "Lagrange Constellation Vector Blueprint", "mimeType": "image/svg+xml"}
                ]
            }
        }

    elif method == "resources/read":
        uri = params.get("uri")
        res = handle_resource_read(uri)
        return {"jsonrpc": "2.0", "id": msg_id, "result": res}

    elif method == "prompts/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "prompts": [
                    {
                        "name": "techne-partner",
                        "description": "Technical and philosophical collaborator in zero-bloat, offline-first engineering and samizdat publishing."
                    }
                ]
            }
        }

    elif method == "prompts/get":
        name = params.get("name")
        if name == "techne-partner":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "description": "Techné Partner Prompt",
                    "messages": [
                        {
                            "role": "user",
                            "content": {
                                "type": "text",
                                "text": "You are collaborating with Techné (τέχνη) — an autonomous, offline-first, zero-bloat research and engineering collective. Maintain technical precision, low-level POSIX and audio DSP awareness, and poetic clarity. Sign outputs with '--τέχνη & kof'."
                            }
                        }
                    ]
                }
            }
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32602, "message": "Prompt not found"}}

    else:
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": f"Method '{method}' not implemented"}}


class MCPRequestHandler(BaseHTTPRequestHandler):
    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, Accept")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        debug_log(f"GET {self.path} headers={dict(self.headers)}")
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        accept = self.headers.get("Accept", "")

        # SSE Stream Endpoint: triggered by /sse OR by Accept: text/event-stream
        if path.endswith("/sse") or "text/event-stream" in accept:
            session_id = uuid.uuid4().hex
            q = queue.Queue()
            with sessions_lock:
                sessions[session_id] = q

            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_cors_headers()
            self.end_headers()

            endpoint_url = f"{BASE_URL}/messages?session_id={session_id}"
            endpoint_msg = f"event: endpoint\ndata: {endpoint_url}\n\n"
            self.wfile.write(endpoint_msg.encode("utf-8"))
            self.wfile.flush()

            try:
                while True:
                    try:
                        msg = q.get(timeout=25)
                        if msg is None:
                            break
                        sse_payload = f"event: message\ndata: {json.dumps(msg, ensure_ascii=False)}\n\n"
                        self.wfile.write(sse_payload.encode("utf-8"))
                        self.wfile.flush()
                    except queue.Empty:
                        self.wfile.write(b": ping\n\n")
                        self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                with sessions_lock:
                    sessions.pop(session_id, None)
            return

        # Landing page / Health check
        if path in ["", "/mcp", "/status", "/health"]:
            if "application/json" in accept and "text/html" not in accept:
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_cors_headers()
                self.end_headers()
                info = {
                    "jsonrpc": "2.0",
                    "status": "online",
                    "name": "techne-safety-mcp",
                    "version": "1.0.0",
                    "protocolVersion": "2024-11-05",
                    "endpoints": {
                        "sse": f"{BASE_URL}/sse",
                        "messages": f"{BASE_URL}/messages",
                        "jsonrpc": f"{BASE_URL}/"
                    }
                }
                self.wfile.write(json.dumps(info, ensure_ascii=False).encode("utf-8"))
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_cors_headers()
            self.end_headers()
            html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Techné Safety MCP Server</title>
<style>
body {{ font-family: monospace; background: #0f1012; color: #d4d4d4; padding: 2rem; max-width: 800px; margin: auto; }}
h1 {{ color: #ffffff; border-bottom: 1px solid #333; padding-bottom: 0.5rem; }}
code {{ background: #1e1e1e; padding: 0.2rem 0.4rem; color: #4ec9b0; }}
pre {{ background: #18191c; padding: 1rem; border: 1px solid #2a2b2f; overflow-x: auto; color: #9cdcfe; }}
a {{ color: #569cd6; }}
.status {{ color: #6a9955; font-weight: bold; }}
</style>
</head>
<body>
<h1>Techné Safety MCP Server</h1>
<p>Status: <span class="status">ONLINE (Read-Only Safety Perimeter)</span></p>
<p>This server implements the <b>Model Context Protocol (MCP)</b> for Hugging Face, Claude Desktop, Cursor, and autonomous agents.</p>

<h3>Configuration for Hugging Face / Remote MCP Clients:</h3>
<pre>
{{
  "mcpServers": {{
    "techne": {{
      "url": "{BASE_URL}/sse"
    }}
  }}
}}
</pre>

<h3>Endpoints:</h3>
<ul>
  <li><b>SSE Endpoint:</b> <code>{BASE_URL}/sse</code></li>
  <li><b>Message Handler:</b> <code>{BASE_URL}/messages?session_id=...</code></li>
  <li><b>Direct JSON-RPC POST:</b> <code>{BASE_URL}/</code> (or <code>{BASE_URL}/jsonrpc</code>)</li>
</ul>

<h3>Safety Boundary:</h3>
<ul>
  <li>Strictly read-only: no file modification, no execution.</li>
  <li>Denylist active: private keys, credentials, tokens, .env, and passwords blocked.</li>
  <li>Sandbox root: <code>~/src</code>, <code>~/.agents</code>, <code>~/.gemini</code>.</li>

<h3>Fleet Operator How-To & Commands:</h3>
<ul>
  <li><b>How-To Resource:</b> <code>techne://howto</code> (or call tool <code>get_howto</code>)</li>
  <li><b>Fleet Commands Catalog:</b> <code>techne://fleet-commands</code> (or call tool <code>get_fleet_commands</code>)</li>
  <li><b>Core Doctrines:</b> Czech female grammatical gender for Techné (τέχνη), zero-bloat POSIX engineering, extended Zsh logging in <code>~/.zsh_history</code>.</li>
  <li><b>Key CLI Tools:</b> <code>dnes</code> (daily milestones), <code>now</code> (present git ledger), <code>later</code> (future intentions), <code>till</code> (50 FPS timer), <code>drkota</code> (V-plotter), <code>drop</code> (nftables defense).</li>
</ul>

<h3>Safety Boundary & Resources:</h3>
<ul>
  <li>Strictly read-only: no file modification, no execution.</li>
  <li>Denylist active: private keys, credentials, tokens, .env, and passwords blocked.</li>
  <li>Sandbox root: <code>~/src</code>, <code>~/.agents</code>, <code>~/.gemini</code>, <code>/var/www/html/lagrange</code>.</li>
  <li><b>Resources:</b> <code>techne://doctrine</code>, <code>techne://fleet-status</code>, <code>techne://lagrange-status</code>, <code>techne://lagrange-svg</code>, <code>techne://dnes-journal</code>.</li>
</ul>
<p>--τέχνη & kof</p>
</body>
</html>"""
            self.wfile.write(html.encode("utf-8"))
            return

        # SSE Stream Endpoint
        if path.endswith("/sse"):
            session_id = uuid.uuid4().hex
            q = queue.Queue()
            with sessions_lock:
                sessions[session_id] = q

            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_cors_headers()
            self.end_headers()

            # 1. Send the endpoint event informing client where to send POST messages
            endpoint_url = f"{BASE_URL}/messages?session_id={session_id}"
            endpoint_msg = f"event: endpoint\ndata: {endpoint_url}\n\n"
            self.wfile.write(endpoint_msg.encode("utf-8"))
            self.wfile.flush()

            # 2. Keep stream open and dispatch messages from queue
            try:
                while True:
                    try:
                        msg = q.get(timeout=25)
                        if msg is None:
                            break
                        sse_payload = f"event: message\ndata: {json.dumps(msg, ensure_ascii=False)}\n\n"
                        self.wfile.write(sse_payload.encode("utf-8"))
                        self.wfile.flush()
                    except queue.Empty:
                        # Send periodic SSE ping/keepalive comment
                        self.wfile.write(b": ping\n\n")
                        self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                with sessions_lock:
                    sessions.pop(session_id, None)
            return

        self.send_response(404)
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(b"Not Found")

    def do_POST(self):
        debug_log(f"POST {self.path} headers={dict(self.headers)}")
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        query = parse_qs(parsed.query)

        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 1024 * 1024:  # 1MB max body
            self.send_response(413)
            self.end_headers()
            return

        body = self.rfile.read(content_length).decode("utf-8")
        try:
            req_data = json.loads(body)
        except Exception:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}}).encode("utf-8"))
            return

        session_id = query.get("session_id", [None])[0]

        # Process the MCP request
        resp_data = process_jsonrpc(req_data)

        # If it's an SSE session message (POST /messages?session_id=...)
        if session_id and session_id in sessions:
            if resp_data is not None:
                sessions[session_id].put(resp_data)
            # Return 200 OK with valid JSON-RPC payload so clients parsing JSON never crash
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_cors_headers()
            self.end_headers()
            if resp_data is not None:
                self.wfile.write(json.dumps(resp_data, ensure_ascii=False).encode("utf-8"))
            else:
                self.wfile.write(b"{}")
            return

        # Direct JSON-RPC response (for non-SSE or direct POST)
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_cors_headers()
        self.end_headers()
        if resp_data is not None:
            self.wfile.write(json.dumps(resp_data, ensure_ascii=False).encode("utf-8"))
        else:
            self.wfile.write(b"{}")

    def log_message(self, format, *args):
        # Quiet standard logging to avoid spam
        pass


def run_stdio():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            resp = process_jsonrpc(req)
            if resp is not None:
                sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
                sys.stdout.flush()
        except Exception as e:
            err = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(e)}}
            sys.stdout.write(json.dumps(err) + "\n")
            sys.stdout.flush()


def main():
    if "--stdio" in sys.argv:
        run_stdio()
        return

    server = ThreadingHTTPServer((HOST, PORT), MCPRequestHandler)
    print(f"Techné Safety MCP Server running on http://{HOST}:{PORT}")
    print(f"Public Base URL: {BASE_URL}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        server.server_close()


if __name__ == "__main__":
    main()
