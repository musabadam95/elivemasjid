import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

import requests

logger = logging.getLogger(__name__)


class AudioProxyServer:
    def __init__(self, port, user_agent):
        self.port = port
        self.user_agent = user_agent
        self._stream_url = None
        self._lock = threading.Lock()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.0"

            def do_GET(self):
                self._proxy_stream()

            def do_HEAD(self):
                self._proxy_stream(head_only=True)

            def _proxy_stream(self, head_only=False):
                if urlsplit(self.path).path != "/stream":
                    self.send_error(404)
                    return

                with owner._lock:
                    stream_url = owner._stream_url
                if not stream_url:
                    logger.warning("Rejected audio request because the stream is offline")
                    self.send_error(503, "Stream is offline")
                    return

                headers = {
                    "User-Agent": owner.user_agent,
                    "Accept-Encoding": "identity"
                }
                for header in ("Range", "Icy-MetaData"):
                    value = self.headers.get(header)
                    if value:
                        headers[header] = value

                response = None
                try:
                    response = requests.get(
                        stream_url,
                        headers=headers,
                        stream=True,
                        timeout=(10, None)
                    )
                    if response.status_code >= 400:
                        logger.error("Relay returned HTTP %s", response.status_code)
                        self.send_error(response.status_code)
                        return

                    self.send_response(response.status_code)
                    for header in ("Content-Type", "Content-Length", "Content-Range", "Accept-Ranges"):
                        value = response.headers.get(header)
                        if value:
                            self.send_header(header, value)
                    for header, value in response.headers.items():
                        if header.lower().startswith("icy-"):
                            self.send_header(header, value)
                    self.send_header("Connection", "close")
                    self.end_headers()
                    logger.info(
                        "Proxying audio to %s (HTTP %s, content type: %s)",
                        self.client_address[0],
                        response.status_code,
                        response.headers.get("Content-Type", "unknown")
                    )

                    if not head_only:
                        for chunk in response.iter_content(chunk_size=16 * 1024):
                            if chunk:
                                self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    logger.debug("Audio client %s disconnected", self.client_address[0])
                except requests.exceptions.RequestException as error:
                    logger.error("Audio relay request failed (%s)", type(error).__name__)
                finally:
                    if response is not None:
                        response.close()
                    self.close_connection = True

            def log_message(self, format, *args):
                logger.info("Audio proxy request from %s: %s", self.client_address[0], format % args)

        self._server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
        self._server.daemon_threads = True
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def set_stream_url(self, stream_url):
        with self._lock:
            self._stream_url = stream_url or None

    def start(self):
        self._thread.start()
        logger.info("Audio proxy listening on port %s", self.port)
