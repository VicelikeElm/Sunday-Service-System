import json
import os
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path

from sunday_common import load_config

BASE = Path(r"C:\Church\SermonAI")


class Handler(BaseHTTPRequestHandler):
    server_version = "SermonPlan/1.0"

    def log_message(self, format, *args):
        return

    def _send_json(self, payload, status=200):
        body = json.dumps(
            payload,
            ensure_ascii=False,
            indent=2
        ).encode("utf-8")

        self.send_response(status)
        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8"
        )
        self.send_header(
            "Access-Control-Allow-Origin",
            "*"
        )
        self.send_header(
            "Cache-Control",
            "no-store"
        )
        self.send_header(
            "Content-Length",
            str(len(body))
        )
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        config = load_config()
        plan_path = Path(
            config.get(
                "sermon_plan_file",
                str(BASE / "sermon_plan.json")
            )
        )

        if self.path.rstrip("/") in (
            "",
            "/status",
        ):
            self._send_json({
                "ok": True,
                "plan_exists": plan_path.exists(),
                "plan_path": str(plan_path),
            })
            return

        if self.path.rstrip("/") == "/sermon-plan":
            if not plan_path.exists():
                self._send_json({
                    "ok": False,
                    "error": "sermon_plan.json not found"
                }, status=404)
                return

            try:
                payload = json.loads(
                    plan_path.read_text(
                        encoding="utf-8"
                    )
                )
                payload["ok"] = True
                self._send_json(payload)
            except Exception as exc:
                self._send_json({
                    "ok": False,
                    "error": str(exc)
                }, status=500)
            return

        self._send_json({
            "ok": False,
            "error": "not found"
        }, status=404)


def main():
    config = load_config()
    port = int(
        config.get(
            "sermon_plan_server_port",
            8765
        )
    )

    server = ThreadingHTTPServer(
        ("127.0.0.1", port),
        Handler
    )

    server.serve_forever()


if __name__ == "__main__":
    main()
