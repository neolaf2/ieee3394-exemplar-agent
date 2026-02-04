#!/usr/bin/env python3
"""
Simple HTTP server to serve the web chat interface
"""

import http.server
import socketserver
import sys
from pathlib import Path

PORT = 8080
Handler = http.server.SimpleHTTPRequestHandler

def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT

    with socketserver.TCPServer(("", port), Handler) as httpd:
        print(f"╔{'═' * 60}╗")
        print(f"║  IEEE 3394 Agent - Web Chat Server                        ║")
        print(f"╠{'═' * 60}╣")
        print(f"║  🌐 Server running at: http://localhost:{port:<26}║")
        print(f"║  📄 Open: http://localhost:{port}/web_chat.html         ║")
        print(f"║                                                            ║")
        print(f"║  ⚠️  Make sure the agent daemon is running:                ║")
        print(f"║     uv run python -m ieee3394_agent --daemon \\            ║")
        print(f"║       --anthropic-api --api-port 8100                     ║")
        print(f"║                                                            ║")
        print(f"║  Press Ctrl+C to stop                                     ║")
        print(f"╚{'═' * 60}╝")
        print()

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n👋 Server stopped")
            sys.exit(0)

if __name__ == "__main__":
    main()
