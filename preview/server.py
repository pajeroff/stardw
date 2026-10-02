#!/usr/bin/env python3
"""Lightweight preview server for the Stardw Godot 4.7 project assets & playable web demo."""

import http.server
import os
import socketserver

PORT = 8080
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class PreviewHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT_DIR, **kwargs)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.path = "/preview/index.html"
        return super().do_GET()

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()


if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", PORT), PreviewHandler) as httpd:
        print(f"Serving Stardw interactive preview on http://0.0.0.0:{PORT}")
        httpd.serve_forever()
