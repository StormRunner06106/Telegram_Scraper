"""Dependency-free, loopback-only CSV browser: gscraper ui run."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from githubscraper.core import OUTPUT_DIR
from githubscraper.csv_storage import csv_lock, read_csv, read_flag, write_csv

STATIC_DIR = Path(__file__).with_name("web")


class RowChangedError(ValueError):
    pass


def row_key(row: dict[str, str]) -> str:
    # Independent of is_read so queued toggles and other tabs remain valid.
    data = {key: value for key, value in row.items() if key != "is_read"}
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class CsvLibrary:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def resolve(self, name: str) -> Path:
        if not isinstance(name, str) or not name or Path(name).is_absolute():
            raise ValueError("Choose a CSV from the file list.")
        path = (self.root / name).resolve()
        if not path.is_relative_to(self.root) or path.suffix.casefold() != ".csv":
            raise ValueError("Choose a CSV inside the configured directory.")
        if not path.is_file():
            raise FileNotFoundError("CSV no longer exists. Refresh the file list.")
        return path

    def list_files(self) -> list[dict]:
        files = []
        for path in self.root.rglob("*"):
            if path.is_file() and path.suffix.casefold() == ".csv" and path.resolve().is_relative_to(self.root):
                relative = path.relative_to(self.root).as_posix()
                files.append({"name": relative, "size": path.stat().st_size})
        return sorted(files, key=lambda item: item["name"].casefold())

    def table(self, name: str) -> dict:
        path = self.resolve(name)
        with csv_lock(path):
            fields, rows, has_bom = read_csv(path)
            if "is_read" not in fields:
                fields.append("is_read")
                for row in rows:
                    row["is_read"] = "false"
                write_csv(path, fields, rows, has_bom)
        return {
            "name": name,
            "fields": fields,
            "rows": [{"index": index, "key": row_key(row), "values": row, "is_read": read_flag(row.get("is_read"))}
                     for index, row in enumerate(rows)],
        }

    def set_read(self, name: str, index: int, key: str, value: bool) -> dict:
        if type(index) is not int or index < 0 or not isinstance(key, str) or type(value) is not bool:
            raise ValueError("Expected a row index, row key, and boolean is_read.")
        path = self.resolve(name)
        with csv_lock(path):
            fields, rows, has_bom = read_csv(path)
            if index >= len(rows) or row_key(rows[index]) != key:
                raise RowChangedError("This row changed on disk. Refresh the CSV before editing it.")
            if "is_read" not in fields:
                fields.append("is_read")
                for row in rows:
                    row["is_read"] = "false"
            rows[index]["is_read"] = "true" if value else "false"
            write_csv(path, fields, rows, has_bom)
        return {"index": index, "is_read": value}


def create_server(root: Path, port: int = 8765) -> ThreadingHTTPServer:
    library = CsvLibrary(root)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def respond(self, status: int, data: bytes, content_type: str):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(data)

        def json(self, status: int, payload):
            self.respond(status, json.dumps(payload, ensure_ascii=False).encode(), "application/json; charset=utf-8")

        def dispatch(self, write: bool = False):
            host = self.headers.get("Host", "")
            port = self.server.server_port
            if host not in {f"127.0.0.1:{port}", f"localhost:{port}"}:
                self.json(403, {"error": "Use the local URL printed by gscraper."})
                return
            url = urlsplit(self.path)
            if url.path.startswith("/api/"):
                if self.headers.get("X-GScraper-UI") != "1" or self.headers.get("Origin", f"http://{host}") != f"http://{host}":
                    self.json(403, {"error": "Requests must come from the local CSV browser."})
                    return
            try:
                if write and url.path == "/api/read":
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 0 < length <= 16384:
                        raise ValueError("Invalid request size.")
                    if self.headers.get_content_type() != "application/json":
                        raise ValueError("Expected JSON.")
                    body = json.loads(self.rfile.read(length))
                    if not isinstance(body, dict):
                        raise ValueError("Expected a JSON object.")
                    result = library.set_read(body.get("name"), body.get("index"), body.get("key"), body.get("is_read"))
                    self.json(200, result)
                elif not write and url.path == "/api/files":
                    self.json(200, {"files": library.list_files(), "directory": str(library.root)})
                elif not write and url.path == "/api/table":
                    name = parse_qs(url.query).get("name", [""])[0]
                    self.json(200, library.table(name))
                elif not write and url.path in {"/", "/index.html", "/app.js", "/state.js", "/styles.css"}:
                    name = url.path.lstrip("/") or "index.html"
                    mime = {".html": "text/html", ".js": "text/javascript", ".css": "text/css"}[Path(name).suffix]
                    self.respond(200, (STATIC_DIR / name).read_bytes(), f"{mime}; charset=utf-8")
                else:
                    self.json(404, {"error": "Not found."})
            except RowChangedError as error:
                self.json(409, {"error": str(error)})
            except FileNotFoundError as error:
                self.json(404, {"error": str(error)})
            except PermissionError:
                self.json(423, {"error": "CSV is busy or locked by another program. Close it there and try again."})
            except (ValueError, csv.Error) as error:
                self.json(400, {"error": str(error)})
            except OSError:
                self.json(500, {"error": "Could not access the CSV. Check the file and directory permissions."})

        def do_GET(self):
            self.dispatch()

        def do_POST(self):
            self.dispatch(write=True)

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = False  # Finish pending saves before closing.
    return server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gscraper ui", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="Open the local CSV browser")
    run.add_argument("--directory", type=Path, default=OUTPUT_DIR, help="CSV directory, including subdirectories")
    run.add_argument("--port", type=int, default=8765)
    run.add_argument("--no-browser", action="store_true", help="Print the URL without opening a browser")
    args = parser.parse_args(argv)
    if not 0 <= args.port <= 65535:
        parser.error("--port must be between 0 and 65535")
    if args.directory.exists() and not args.directory.is_dir():
        parser.error("--directory must be a directory")
    try:
        server = create_server(args.directory, args.port)
    except OSError as error:
        print(f"Cannot start CSV browser: {error}. Try a different --port.", file=sys.stderr)
        return 1
    with server:
        url = f"http://127.0.0.1:{server.server_port}"
        print(f"CSV browser: {url}\nCSV directory: {args.directory.resolve()}\nPress Ctrl+C to stop.", flush=True)
        if not args.no_browser:
            try:
                webbrowser.open(url)
            except webbrowser.Error:
                print("Open the URL above in your browser.", file=sys.stderr)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    return 0
