"""
Standalone CORS proxy for the Colonist leaderboard API.

Returns the #1 ranked player for a given game mode, continent, and region.
Intended to be deployed on a public server so JSFiddle (or any browser) can
query the Colonist API without CORS issues.

Environment variables:
    PORT              - Server port (default: 8080)
    COLONIST_API_URL  - Upstream API base URL (default: https://colonist.io)
    ALLOWED_ORIGINS   - Comma-separated allowed origins for CORS, or * for all
                        (default: *)
    HOST              - Bind address (default: 0.0.0.0)

Usage:
    python server.py
    PORT=9000 ALLOWED_ORIGINS="https://jsfiddle.net,https://fiddle.jshell.net" python server.py

Example request:
    GET /api/leaderboards/Classic4P/Continent/NA
"""
import http.server
import ssl
import urllib.request
import os
import json

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

PORT = int(os.environ.get("PORT", 8080))
HOST = os.environ.get("HOST", "0.0.0.0")
COLONIST_API_URL = os.environ.get("COLONIST_API_URL", "https://colonist.io")
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*")
ALLOWED_PATH_PREFIX = "/api/leaderboards/"


class LeaderboardProxy(http.server.BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def do_GET(self):
        if not self.path.startswith(ALLOWED_PATH_PREFIX):
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self._cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode())
            return

        # Always fetch only the #1 player
        upstream = COLONIST_API_URL + self.path.split("?")[0] + "?start=1&end=1&search="
        try:
            req = urllib.request.Request(upstream, headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
            })
            with urllib.request.urlopen(req, timeout=5, context=SSL_CTX) as resp:
                body = resp.read()
                self.send_response(resp.status)
                self.send_header("Content-Type", "application/json")
                self._cors_headers()
                self.end_headers()
                self.wfile.write(body)
        except Exception as e:
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self._cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def _cors_headers(self):
        origin = self.headers.get("Origin", "")
        if ALLOWED_ORIGINS == "*":
            self.send_header("Access-Control-Allow-Origin", "*")
        elif origin in [o.strip() for o in ALLOWED_ORIGINS.split(",")]:
            self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")


if __name__ == "__main__":
    http.server.HTTPServer.allow_reuse_address = True
    with http.server.HTTPServer((HOST, PORT), LeaderboardProxy) as httpd:
        print(f"Leaderboard proxy running on http://{HOST}:{PORT}")
        print(f"Upstream: {COLONIST_API_URL}")
        print(f"Allowed origins: {ALLOWED_ORIGINS}")
        print(f"Example: http://localhost:{PORT}/api/leaderboards/Classic4P/Continent/NA")
        httpd.serve_forever()
