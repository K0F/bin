
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
ALLOWED_ROOTS = [
    Path("/home/kof/src").resolve(),
    Path("/home/kof/.agents").resolve(),
    Path("/home/kof/.gemini").resolve(),
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
            "t520": {"role": "Main Workstation / Synergy KVM Server", "arch": "x86_64", "ip": "192.168.1.100"},
            "bazina": {"role": "Compute / GPU / Drkota V-Plotter Host", "arch": "x86_64 Debian 13", "ip": "192.168.1.104"},
            "boxC": {"role": "Headless Gateway / Web / Storage / Git / MCP", "arch": "Raspberry Pi", "ip": "192.168.1.101"}
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
                    {"uri": "techne://doctrine", "name": "Techné Core Doctrine", "mimeType": "text/markdown"},
                    {"uri": "techne://fleet-status", "name": "Fleet Mesh Architecture", "mimeType": "application/json"},
                    {"uri": "techne://samizdat-manifesto", "name": "Samizdat Editorial Manifesto", "mimeType": "text/markdown"},
                    {"uri": "techne://dnes-journal", "name": "Recent Daily Journal Milestones", "mimeType": "text/markdown"}
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


def main():
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
