from __future__ import annotations

import json
import mimetypes
import re
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from fshorts.studio.ratings import REASONS, RatingStore, ShortRating

PAGE = Path(__file__).with_name("index.html")
CHUNK = 1 << 20
RANGE = re.compile(r"bytes=(\d*)-(\d*)")
SAFE_NAME = re.compile(r"^[\w.-]+$")


class Library:
    """The finished Shorts of every match under the outputs folder, in match and time order."""

    def __init__(self, outputs: Path, ratings: RatingStore) -> None:
        self._outputs = outputs
        self._ratings = ratings

    def queue(self) -> list[dict]:
        items = []
        for listing in sorted(self._outputs.glob("*/shorts.json")):
            match = listing.parent.name
            rated = self._ratings.load(match)
            for clip in json.loads(listing.read_text(encoding="utf-8")):
                if not (listing.parent / "shorts" / clip["file"]).is_file():
                    continue
                rating = rated.get(clip["id"])
                items.append({
                    "match": match, "id": clip["id"], "kind": clip["kind"], "label": clip.get("label", ""),
                    "title": clip.get("title", ""), "hook": clip.get("hook", ""),
                    "start": clip["start"], "end": clip["end"],
                    "video": f"/video/{match}/{clip['file']}",
                    "rating": asdict(rating) if rating else None,
                })
        return items

    def video(self, match: str, name: str) -> Path | None:
        if not (SAFE_NAME.match(match) and SAFE_NAME.match(name)):
            return None
        path = self._outputs / match / "shorts" / name
        return path if path.is_file() else None

    def clip(self, match: str, clip_id: str) -> dict | None:
        listing = self._outputs / match / "shorts.json"
        if not SAFE_NAME.match(match) or not listing.is_file():
            return None
        return next((c for c in json.loads(listing.read_text(encoding="utf-8")) if c["id"] == clip_id), None)


def make_handler(library: Library, ratings: RatingStore):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args) -> None:   # keep the console for errors only
            pass

        def do_GET(self) -> None:
            path = unquote(self.path.split("?", 1)[0])
            if path == "/":
                self._send(HTTPStatus.OK, PAGE.read_bytes(), "text/html; charset=utf-8")
            elif path == "/api/queue":
                body = {"items": library.queue(), "reasons": list(REASONS)}
                self._send(HTTPStatus.OK, json.dumps(body, ensure_ascii=False).encode(), "application/json")
            elif path.startswith("/video/") and path.count("/") == 3:
                _, _, match, name = path.split("/")
                video = library.video(match, name)
                if video is None:
                    self._send(HTTPStatus.NOT_FOUND, b"not found", "text/plain")
                else:
                    self._stream(video)
            else:
                self._send(HTTPStatus.NOT_FOUND, b"not found", "text/plain")

        def do_POST(self) -> None:
            if self.path != "/api/rate":
                self._send(HTTPStatus.NOT_FOUND, b"not found", "text/plain")
                return
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
                clip = library.clip(body["match"], body["id"])
                if clip is None:
                    raise ValueError("unknown clip")
                rating = ShortRating(clip["id"], int(body["stars"]), tuple(body.get("reasons", [])),
                                     str(body.get("note", ""))[:1000], clip["start"], clip["end"], clip["kind"])
                ratings.save(body["match"], rating)
            except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
                self._send(HTTPStatus.BAD_REQUEST, json.dumps({"error": str(error)}).encode(), "application/json")
                return
            self._send(HTTPStatus.OK, json.dumps({"rating": asdict(rating)}).encode(), "application/json")

        def _send(self, status: HTTPStatus, body: bytes, kind: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _stream(self, video: Path) -> None:
            """Serves byte ranges so the browser can seek inside the video."""
            size = video.stat().st_size
            start, end = 0, size - 1
            match = RANGE.match(self.headers.get("Range", ""))
            if match and (match.group(1) or match.group(2)):
                if match.group(1):
                    start = int(match.group(1))
                    end = int(match.group(2)) if match.group(2) else end
                else:
                    start = max(0, size - int(match.group(2)))
                end = min(end, size - 1)
                self.send_response(HTTPStatus.PARTIAL_CONTENT)
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            else:
                self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", mimetypes.guess_type(video.name)[0] or "video/mp4")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(end - start + 1))
            self.end_headers()
            try:
                with video.open("rb") as file:
                    file.seek(start)
                    left = end - start + 1
                    while left > 0:
                        chunk = file.read(min(CHUNK, left))
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        left -= len(chunk)
            except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
                pass   # the player cancelled the request while seeking

    return Handler


def serve(outputs: Path, labels: Path, host: str, port: int) -> ThreadingHTTPServer:
    ratings = RatingStore(labels)
    return ThreadingHTTPServer((host, port), make_handler(Library(outputs, ratings), ratings))
