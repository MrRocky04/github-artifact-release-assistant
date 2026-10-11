"""Small local web server (Python standard library only).

It serves the React user interface from ``frontend/dist`` and exposes the
release workflow as a JSON API under ``/api``.  It only listens on this
computer (127.0.0.1) and every GitHub operation still goes through the GitHub
CLI (``gh``) and ``git`` - no GitHub REST API calls are made from here.
"""

import json
import mimetypes
import re
import shutil
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

import questions as qstore
import workflow
from config import ALLOWED_EXTENSION, FRONTEND_DIST, UPLOAD_DIR

MAX_UPLOAD_BYTES = 2 * 1024 * 1024 * 1024      # 2 GB safety limit
_uploads: dict[str, dict] = {}                 # artifact id -> {name, path, size}
_SAFE_NAME = re.compile(r"[^\w.\- ()\[\]+@]")


class ApiError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message, self.status = message, status


def validate_artifact_name(filename: str) -> str:
    name = Path(unquote(filename or "").replace("\\", "/")).name.strip()
    if not name:
        raise ApiError("No file was selected.")
    if not name.lower().endswith(ALLOWED_EXTENSION) or len(name) <= len(ALLOWED_EXTENSION):
        raise ApiError(
            f"'{name}' is not an artifact. Only {ALLOWED_EXTENSION} (Android library) files can be uploaded.",
            HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
    return _SAFE_NAME.sub("_", name)


class Handler(BaseHTTPRequestHandler):
    server_version = "ReleaseAssistant/1.0"

    def log_message(self, fmt, *args):          # keep the terminal quiet
        pass

    # ---------------------------------------------------------------- helpers
    def _send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length > 5 * 1024 * 1024:
            raise ApiError("Request too large.", HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError):
            raise ApiError("Invalid request.")
        return data if isinstance(data, dict) else {}

    def _check_origin(self):
        """Only allow requests that come from this local page (blocks other websites)."""
        host = (self.headers.get("Host") or "").split(":")[0]
        if host not in {"127.0.0.1", "localhost", "[::1]"}:
            raise ApiError("Forbidden.", HTTPStatus.FORBIDDEN)
        origin = self.headers.get("Origin")
        if origin and urlparse(origin).hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ApiError("Forbidden.", HTTPStatus.FORBIDDEN)

    def _artifact(self, payload: dict) -> dict:
        art = _uploads.get(str(payload.get("artifact_id", "")))
        if not art or not Path(art["path"]).exists():
            raise ApiError("Please upload the artifact first.")
        return art

    # ---------------------------------------------------------------- routing
    def _dispatch(self, method: str):
        try:
            self._check_origin()
            path = urlparse(self.path).path
            if path.startswith("/api/"):
                self._api(method, path)
            elif method == "GET":
                self._static(path)
            else:
                raise ApiError("Not found.", HTTPStatus.NOT_FOUND)
        except ApiError as exc:
            self._send_json({"error": exc.message}, exc.status)
        except workflow.WorkflowError as exc:
            self._send_json({"error": str(exc)}, 400)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as exc:               # never crash the server
            self._send_json({"error": f"Unexpected error: {exc}"}, 500)

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_DELETE(self):
        self._dispatch("DELETE")

    # -------------------------------------------------------------------- API
    def _api(self, method: str, path: str):
        if method == "GET" and path == "/api/status":
            return self._send_json(workflow.status())

        if method == "GET" and path == "/api/questions":
            return self._send_json({"sections": qstore.SECTIONS, "questions": qstore.list_questions(),
                                    "upload_questions": qstore.UPLOAD_QUESTIONS})

        if method == "POST" and path == "/api/questions":
            data = self._read_json()
            try:
                item = qstore.add_question(data.get("section"), data.get("label"),
                                           data.get("type", "text"), bool(data.get("required")))
            except ValueError as exc:
                raise ApiError(str(exc))
            return self._send_json({"question": item}, HTTPStatus.CREATED)

        if method == "DELETE" and path.startswith("/api/questions/"):
            qid = unquote(path[len("/api/questions/"):])
            try:
                removed = qstore.delete_question(qid)
            except KeyError as exc:
                raise ApiError(str(exc.args[0]), HTTPStatus.NOT_FOUND)
            except ValueError as exc:
                raise ApiError(str(exc), HTTPStatus.FORBIDDEN)
            return self._send_json({"removed": removed})

        if method == "POST" and path == "/api/artifact":
            return self._upload_artifact()

        if method == "POST" and path == "/api/release/summary":
            data = self._read_json()
            return self._send_json(workflow.summary(data, self._artifact(data)))

        if method == "POST" and path == "/api/release/prepare":
            data = self._read_json()
            return self._send_json(workflow.prepare(data, self._artifact(data)))

        if method == "POST" and path == "/api/release/confirm":
            return self._send_json(workflow.confirm(self._read_json()))

        if method == "POST" and path == "/api/release/cancel":
            return self._send_json(workflow.cancel())

        raise ApiError("Not found.", HTTPStatus.NOT_FOUND)

    def _upload_artifact(self):
        name = validate_artifact_name(self.headers.get("X-Filename", ""))
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            raise ApiError("The selected file is empty.")
        if length > MAX_UPLOAD_BYTES:
            raise ApiError("The file is too large.", HTTPStatus.REQUEST_ENTITY_TOO_LARGE)

        artifact_id = uuid.uuid4().hex
        folder = UPLOAD_DIR / artifact_id
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / name
        remaining, first = length, True
        try:
            with open(target, "wb") as out:
                while remaining > 0:
                    chunk = self.rfile.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise ApiError("Upload was interrupted.")
                    if first:
                        first = False
                        # an AAR is a ZIP archive - reject renamed non-artifact files
                        if not chunk.startswith(b"PK\x03\x04"):
                            raise ApiError(
                                f"'{name}' has an .aar name but is not a valid AAR (ZIP) archive.",
                                HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
                    out.write(chunk)
                    remaining -= len(chunk)
        except Exception:
            shutil.rmtree(folder, ignore_errors=True)
            raise

        size = target.stat().st_size
        _uploads[artifact_id] = {"name": name, "path": str(target), "size": size}
        self._send_json({"artifact_id": artifact_id, "name": name, "size": size})

    # ----------------------------------------------------------------- static
    def _static(self, path: str):
        root = FRONTEND_DIST.resolve()
        if not root.exists():
            raise ApiError("The frontend has not been built yet. Run: cd frontend && npm install && npm run build",
                           HTTPStatus.SERVICE_UNAVAILABLE)
        rel = unquote(path).lstrip("/") or "index.html"
        target = (root / rel).resolve()
        if root not in target.parents and target != root or not target.is_file():
            target = root / "index.html"            # single-page app fallback
        ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", f"{ctype}; charset=utf-8" if ctype.startswith("text/") or ctype.endswith("javascript") else ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)


def make_server(host: str, port: int) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), Handler)
