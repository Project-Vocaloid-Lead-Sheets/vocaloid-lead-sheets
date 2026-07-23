from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
import socket

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
_logger = logging.getLogger(__name__)

# FIXME: We're getting rid of this stupid HTTP server when we actually start developing stuff
#        This is just a sanity check that you can start the server and have it at least run SOME code.
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = f"Discord Bot Dev Server - Time: {datetime.now()}, Hostname: {socket.gethostname()}, Path: {self.path}"
        body = body.encode()

        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()

        self.wfile.write(body)

    def log_message(self, fmt, *args):
        _logger.info(f"[HTTP] {self.address_string()} {fmt % args}")


def main():
    _logger.info("=" * 60)
    _logger.info("Discord bot development container")
    _logger.info(f"Started: {datetime.now()}")
    _logger.info("Listening on http://0.0.0.0:8000")
    _logger.info("=" * 60)

    HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()


if __name__ == "__main__":
    main()
