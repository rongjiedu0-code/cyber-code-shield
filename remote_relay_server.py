#!/usr/bin/env python3
"""Read-only authenticated Git diff relay. Author: rongjiedu0-code.

License: Apache-2.0. Does not execute approvals or apply patches.
"""
from __future__ import annotations

import argparse
import hmac
import http.server
import json
import os
import pathlib
import subprocess
import urllib.parse


class ShieldRelayServer(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, repo_root, token):
        self.repo_root = pathlib.Path(repo_root).resolve(strict=True)
        if not self.repo_root.is_dir():
            raise ValueError("Repository path must be a directory")
        if not token or len(token) < 32:
            raise ValueError("SHIELD_RELAY_TOKEN must contain at least 32 characters")
        self.token = token
        super().__init__(address, ShieldRelayHandler)


class ShieldRelayHandler(http.server.BaseHTTPRequestHandler):
    def _send_json(self, status_code, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        # Never log URLs, query strings or authentication values.
        pass

    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        if path == "/health":
            self._send_json(200, {"status": "online", "service": "cyber-code-shield-relay-v2"})
            return
        supplied = self.headers.get("Authorization", "")
        expected = "Bearer " + self.server.token
        if not hmac.compare_digest(supplied.encode("utf-8"), expected.encode("utf-8")):
            self._send_json(401, {"error": "Unauthorized"})
            return
        if path != "/diff":
            self._send_json(404, {"error": "Not Found"})
            return
        staged = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get("staged") == ["1"]
        command = ["git", "--no-pager", "diff", "--no-ext-diff", "--no-textconv"]
        if staged:
            command.append("--cached")
        try:
            result = subprocess.run(command, cwd=self.server.repo_root, capture_output=True,
                                    encoding="utf-8", errors="replace", timeout=15, check=False)
        except (OSError, subprocess.TimeoutExpired):
            self._send_json(503, {"error": "Git diff unavailable or timed out"})
            return
        if result.returncode:
            self._send_json(500, {"error": "Git diff failed; check the configured repository"})
            return
        self._send_json(200, {"has_diff": bool(result.stdout.strip()),
                              "staged": staged, "diff": result.stdout})


def run_server(host="127.0.0.1", port=8765, repo_path=".", token=None):
    with ShieldRelayServer((host, port), repo_path, token or os.environ.get("SHIELD_RELAY_TOKEN")) as server:
        print(f"[Cyber-Code-Shield] Read-only relay on {host}:{server.server_port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--repo", default=".")
    args = parser.parse_args()
    try:
        run_server(args.host, args.port, args.repo)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Relay startup failed: {exc}\n")
