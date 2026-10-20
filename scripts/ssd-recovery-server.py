#!/usr/bin/env python3
"""Loopback-only web control for the fixed external storage recovery action."""

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import subprocess
import time


PORT = 3101
ALLOWED_ORIGIN = "https://recover.arowana-cat.ts.net"
HOMELAB_DIR = Path(os.environ["HOMELAB_DIR"]).resolve()
COMPOSE_FILE = HOMELAB_DIR / "compose.yaml"
PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>External drive recovery</title>
  <style>
    :root { color-scheme: dark; font: 16px system-ui, sans-serif; }
    body { margin: 0; padding: 12px 18px; color: #e5e7eb; background: #1E293B; }
    main { display: grid; }
    button { display: inline-flex; align-items: center; justify-content: center; gap: 10px;
      border: 0; border-radius: 8px; padding: 12px 16px; color: #fff;
      background: #2A3445; font: inherit; font-weight: 650; cursor: pointer; }
    button:hover { background: #354154; }
    button:disabled { opacity: .6; cursor: wait; }
    .spinner { width: 16px; height: 16px; border: 2px solid currentColor;
      border-right-color: transparent; border-radius: 50%; animation: spin .7s linear infinite; }
    .spinner[hidden] { display: none; }
    @keyframes spin { to { transform: rotate(360deg); } }
    @media (prefers-reduced-motion: reduce) { .spinner { animation-duration: 1.5s; } }
  </style>
</head>
<body>
  <main>
    <button id="recover" type="button">
      <span>Recover external drive</span>
      <span id="spinner" class="spinner" aria-hidden="true" hidden></span>
    </button>
  </main>
  <script>
    const button = document.querySelector("#recover");
    const spinner = document.querySelector("#spinner");
    button.addEventListener("click", async () => {
      button.disabled = true;
      button.setAttribute("aria-busy", "true");
      spinner.hidden = false;
      try {
        const response = await fetch("/recover", { method: "POST" });
        if (!response.ok) throw new Error("Recovery failed");
      } catch (error) {
        // Keep the compact button-only interface; return to its ready state on failure.
      } finally {
        spinner.hidden = true;
        button.removeAttribute("aria-busy");
        button.disabled = false;
      }
    });
  </script>
</body>
</html>"""


def run_command(args):
    return subprocess.run(
        args,
        cwd=HOMELAB_DIR,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=240,
        check=False,
    )


class Handler(BaseHTTPRequestHandler):
    server_version = "HomelabRecovery/1.0"

    def log_message(self, fmt, *args):
        # Keep the system journal useful without logging request bodies.
        super().log_message(fmt, *args)

    def send_json(self, status, payload):
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path != "/":
            self.send_error(404)
            return
        data = PAGE.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; frame-ancestors https://home.arowana-cat.ts.net")
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path != "/recover":
            self.send_error(404)
            return
        if self.headers.get("Origin") != ALLOWED_ORIGIN:
            self.send_json(403, {"message": "Request origin is not allowed."})
            return
        if not COMPOSE_FILE.is_file():
            self.send_json(500, {"message": f"Compose file not found: {COMPOSE_FILE}"})
            return

        started = time.monotonic()
        try:
            mount = run_command(["/usr/bin/mount", "-a"])
            output = mount.stdout
            if mount.returncode != 0:
                self.send_json(500, {"message": f"mount -a failed (exit {mount.returncode}).", "output": output[-8000:]})
                return

            compose = run_command([
                "/usr/bin/docker", "compose", "-f", str(COMPOSE_FILE), "restart",
                "jellyfin", "qbittorrent", "torrentlab",
            ])
            output += compose.stdout
            payload = {
                "message": "Recovery completed." if compose.returncode == 0 else f"Compose restart failed (exit {compose.returncode}).",
                "output": output[-8000:],
                "durationSeconds": round(time.monotonic() - started, 1),
            }
            self.send_json(200 if compose.returncode == 0 else 500, payload)
        except subprocess.TimeoutExpired as error:
            output = error.stdout or b""
            if isinstance(output, bytes):
                output = output.decode(errors="replace")
            self.send_json(500, {"message": "Recovery command timed out.", "output": output[-8000:]})
        except OSError as error:
            self.send_json(500, {"message": f"Could not run recovery command: {error}"})


if __name__ == "__main__":
    if not COMPOSE_FILE.is_file():
        raise SystemExit(f"Compose file not found: {COMPOSE_FILE}")
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
