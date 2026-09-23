#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import secrets
import socket
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass, field
from email.parser import BytesHeaderParser
from pathlib import Path
from urllib.parse import quote, unquote, urlparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STATIC = HERE / "studio"
DEFAULT_JOBS_ROOT = ROOT / "out" / "hayuya3d" / "studio-jobs"

ALLOWED_PROFILES = {"preview", "mobile", "game", "monster", "ultra"}
ALLOWED_MODES = {"auto", "prop", "character", "architecture"}
ALLOWED_TIERS = {"auto", "compatibility", "balanced", "high", "flagship"}

STAGE_PROGRESS = {
    "queued": 0,
    "planning": 4,
    "viewforge": 12,
    "generating": 25,
    "judge": 50,
    "refinement": 60,
    "mesh_doctor": 68,
    "retopo": 74,
    "gameprep": 84,
    "portable": 91,
    "qa": 96,
    "complete": 100,
    "failed": 100,
}


@dataclass
class CandidateState:
    label: str
    path: str
    url: str | None = None
    score: float | None = None
    is_champion: bool = False


@dataclass
class JobState:
    id: str
    root: str
    status: str = "queued"
    stage: str = "queued"
    progress: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    command: list[str] = field(default_factory=list)
    inputs: list[str] = field(default_factory=list)
    profile: str = "monster"
    mode: str = "auto"
    portable_target: str = "auto"
    candidates: dict[str, CandidateState] = field(default_factory=dict)
    champion: str | None = None
    final_model_url: str | None = None
    final_model_path: str | None = None
    error: str | None = None
    events: list[dict] = field(default_factory=list)
    _condition: threading.Condition = field(default_factory=threading.Condition, repr=False)

    def public(self) -> dict:
        data = asdict(self)
        data.pop("_condition", None)
        data["candidates"] = [asdict(x) for x in self.candidates.values()]
        data["event_count"] = len(self.events)
        data.pop("events", None)
        return data


JOBS: dict[str, JobState] = {}
JOBS_LOCK = threading.Lock()


def _safe_name(value: str) -> str:
    value = Path(value).name
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value)
    return value[:120] or "upload.bin"


def _job_url(job: JobState, path: Path) -> str | None:
    try:
        root = Path(job.root).resolve()
        rel = path.resolve().relative_to(root)
    except Exception:
        return None
    return f"/api/jobs/{job.id}/files/{quote(rel.as_posix())}"


def _viewer_artifact(job: JobState, label: str, path: Path) -> Path | None:
    if not path.is_file():
        return None
    if path.suffix.lower() in {".glb", ".gltf"}:
        return path
    if path.suffix.lower() not in {".obj", ".ply", ".stl"}:
        return None
    try:
        from qa import export_glb
        preview_dir = Path(job.root) / "viewer-previews"
        preview = preview_dir / f"{_safe_name(label)}.glb"
        export_glb(path, preview)
        return preview
    except Exception as exc:
        _emit(job, "viewer_warning", {
            "label": label,
            "message": f"could not normalize {path.suffix} candidate for viewer: {type(exc).__name__}: {exc}",
        })
        return None


def _emit(job: JobState, kind: str, payload: dict) -> None:
    event = {
        "seq": len(job.events),
        "time": time.time(),
        "kind": kind,
        **payload,
    }
    with job._condition:
        job.events.append(event)
        job.updated_at = time.time()
        job._condition.notify_all()


def _set_stage(job: JobState, stage: str, *, status: str | None = None) -> None:
    job.stage = stage
    job.progress = STAGE_PROGRESS.get(stage, job.progress)
    if status:
        job.status = status
    _emit(job, "stage", {"stage": job.stage, "progress": job.progress, "status": job.status})


def parse_pipeline_line(job: JobState, line: str) -> None:
    line = line.strip()
    if not line:
        return
    _emit(job, "log", {"line": line})

    if line.startswith("HAYUYA_VIEWFORGE"):
        _set_stage(job, "viewforge")
    elif line.startswith("HAYUYA_CANDIDATE_READY"):
        _set_stage(job, "generating")
        parts = line.split()
        match = re.match(
            r"^HAYUYA_CANDIDATE_READY\s+(\S+)\s+(.+?)(?:\s+(?:source|sources|real_sources)=|$)",
            line,
        )
        if match:
            label = match.group(1)
            path = match.group(2).strip()
            viewer_path = _viewer_artifact(job, label, Path(path))
            candidate = CandidateState(label=label, path=path)
            candidate.url = _job_url(job, viewer_path) if viewer_path is not None else None
            job.candidates[label] = candidate
            _emit(job, "candidate", asdict(candidate))
    elif line.startswith("HAYUYA_REFINEMENT"):
        _set_stage(job, "refinement")
    elif line.startswith("HAYUYA_MESH_DOCTOR"):
        _set_stage(job, "mesh_doctor")
    elif line.startswith("HAYUYA_RETOPO"):
        _set_stage(job, "retopo")
    elif line.startswith("HAYUYA_GAMEPREP"):
        _set_stage(job, "gameprep")
    elif line.startswith("HAYUYA_PORTABLE_PACK"):
        _set_stage(job, "portable")
    elif line.startswith("HAYUYA_QA"):
        _set_stage(job, "qa")
    elif line.startswith("HAYUYA_MONSTER_READY"):
        parts = line.split(maxsplit=1)
        if len(parts) == 2:
            path = Path(parts[1])
            job.final_model_path = str(path)
            job.final_model_url = _job_url(job, path)
            _emit(job, "model", {"path": str(path), "url": job.final_model_url})
    elif line.startswith("HAYUYA_CHAMPION"):
        match = re.search(r"backend=([^\s]+).*score=([0-9.]+)", line)
        if match:
            label = match.group(1)
            score = float(match.group(2))
            job.champion = label
            if label in job.candidates:
                job.candidates[label].score = score
                job.candidates[label].is_champion = True
            _emit(job, "champion", {"label": label, "score": score})
    elif "Judge" in line or "ranking" in line.lower():
        if job.progress < STAGE_PROGRESS["judge"]:
            _set_stage(job, "judge")


def _run_job(job: JobState) -> None:
    _set_stage(job, "planning", status="running")
    log_path = Path(job.root) / "studio.log"
    try:
        with log_path.open("w", encoding="utf-8", buffering=1) as log:
            proc = subprocess.Popen(
                job.command,
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            assert proc.stdout is not None
            for raw in proc.stdout:
                log.write(raw)
                parse_pipeline_line(job, raw)
            code = proc.wait()

        for ranking_path in sorted(Path(job.root).glob("output/**/ranking.json")):
            try:
                ranking = json.loads(ranking_path.read_text(encoding="utf-8"))
                for item in ranking:
                    label = str(item.get("backend", ""))
                    if label in job.candidates and item.get("score") is not None:
                        job.candidates[label].score = float(item["score"])
                _emit(job, "ranking", {
                    "candidates": [asdict(x) for x in job.candidates.values()]
                })
            except Exception:
                pass

        if code != 0:
            job.error = f"Hayuya exited with code {code}"
            _set_stage(job, "failed", status="failed")
            _emit(job, "error", {"message": job.error})
            return
        _set_stage(job, "complete", status="complete")
    except Exception as exc:
        job.error = f"{type(exc).__name__}: {exc}"
        _set_stage(job, "failed", status="failed")
        _emit(job, "error", {"message": job.error})


def _parse_content_disposition(value: str) -> tuple[str | None, str | None]:
    name = re.search(r'(?:^|;)\s*name="([^"]*)"', value)
    filename = re.search(r'(?:^|;)\s*filename="([^"]*)"', value)
    return (name.group(1) if name else None, filename.group(1) if filename else None)


def parse_multipart(body: bytes, content_type: str) -> tuple[dict[str, str], list[tuple[str, str, bytes]]]:
    match = re.search(r'boundary=(?:"([^"]+)"|([^;]+))', content_type)
    if not match:
        raise ValueError("multipart boundary missing")
    boundary = (match.group(1) or match.group(2)).encode("utf-8")
    token = b"--" + boundary

    fields: dict[str, str] = {}
    files: list[tuple[str, str, bytes]] = []
    parser = BytesHeaderParser()
    for block in body.split(token):
        block = block.strip(b"\r\n")
        if not block or block == b"--":
            continue
        if block.endswith(b"--"):
            block = block[:-2].rstrip(b"\r\n")
        head, sep, payload = block.partition(b"\r\n\r\n")
        if not sep:
            continue
        headers = parser.parsebytes(head + b"\r\n")
        disposition = headers.get("Content-Disposition", "")
        name, filename = _parse_content_disposition(disposition)
        if not name:
            continue
        if payload.endswith(b"\r\n"):
            payload = payload[:-2]
        if filename is not None:
            files.append((name, _safe_name(filename), payload))
        else:
            fields[name] = payload.decode("utf-8", errors="replace")
    return fields, files


def local_addresses(port: int) -> list[str]:
    found = {"127.0.0.1"}
    try:
        host = socket.gethostname()
        for item in socket.getaddrinfo(host, None, socket.AF_INET):
            ip = item[4][0]
            if ip and not ip.startswith("127."):
                found.add(ip)
    except OSError:
        pass
    return [f"http://{ip}:{port}" for ip in sorted(found)]


class StudioHandler(BaseHTTPRequestHandler):
    server_version = "HAYUYAStudio/0.1"

    def _json(self, value, status=200):
        data = json.dumps(value, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _serve_file(self, path: Path):
        if not path.is_file():
            self.send_error(404)
            return
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        size = path.stat().st_size
        range_header = self.headers.get("Range")
        start, end = 0, max(0, size - 1)

        if range_header:
            match = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header.strip())
            if not match:
                self.send_error(416)
                return
            raw_start, raw_end = match.groups()
            if raw_start:
                start = int(raw_start)
                end = int(raw_end) if raw_end else end
            elif raw_end:
                suffix = int(raw_end)
                start = max(0, size - suffix)
            end = min(end, size - 1)
            if start < 0 or start > end or start >= size:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.end_headers()
                return

        length = end - start + 1
        self.send_response(206 if range_header else 200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(length))
        self.send_header("Accept-Ranges", "bytes")
        if range_header:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        with path.open("rb") as f:
            f.seek(start)
            remaining = length
            while remaining > 0:
                chunk = f.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/info":
            self._json({
                "name": "HAYUYA Studio",
                "version": 1,
                "addresses": local_addresses(self.server.server_port),
                "mobile_ready": True,
            })
            return

        if path == "/api/jobs":
            with JOBS_LOCK:
                jobs = sorted(JOBS.values(), key=lambda x: x.created_at, reverse=True)
            self._json([x.public() for x in jobs])
            return

        match = re.fullmatch(r"/api/jobs/([A-Za-z0-9_-]+)", path)
        if match:
            job = JOBS.get(match.group(1))
            if not job:
                self.send_error(404)
                return
            self._json(job.public())
            return

        match = re.fullmatch(r"/api/jobs/([A-Za-z0-9_-]+)/events", path)
        if match:
            job = JOBS.get(match.group(1))
            if not job:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            index = 0
            try:
                while True:
                    with job._condition:
                        while index >= len(job.events):
                            if job.status in {"complete", "failed"}:
                                break
                            job._condition.wait(timeout=12)
                            if index >= len(job.events):
                                self.wfile.write(b": keepalive\n\n")
                                self.wfile.flush()
                        while index < len(job.events):
                            event = job.events[index]
                            payload = json.dumps(event, separators=(",", ":"))
                            self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
                            self.wfile.flush()
                            index += 1
                        if job.status in {"complete", "failed"} and index >= len(job.events):
                            break
            except (BrokenPipeError, ConnectionResetError):
                pass
            return

        match = re.fullmatch(r"/api/jobs/([A-Za-z0-9_-]+)/files/(.+)", path)
        if match:
            job = JOBS.get(match.group(1))
            if not job:
                self.send_error(404)
                return
            rel = Path(unquote(match.group(2)))
            root = Path(job.root).resolve()
            candidate = (root / rel).resolve()
            try:
                candidate.relative_to(root)
            except ValueError:
                self.send_error(403)
                return
            self._serve_file(candidate)
            return

        if path == "/":
            path = "/index.html"
        static_path = (STATIC / path.lstrip("/")).resolve()
        try:
            static_path.relative_to(STATIC.resolve())
        except ValueError:
            self.send_error(403)
            return
        self._serve_file(static_path)

    def do_POST(self):
        if self.path != "/api/jobs":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 512 * 1024 * 1024:
            self._json({"error": "upload body must be between 1 byte and 512MB"}, 413)
            return
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            self._json({"error": "multipart/form-data required"}, 400)
            return

        try:
            fields, files = parse_multipart(self.rfile.read(length), content_type)
        except Exception as exc:
            self._json({"error": f"bad upload: {exc}"}, 400)
            return

        image_files = [item for item in files if item[0] == "images"]
        if not image_files:
            self._json({"error": "at least one image is required"}, 400)
            return

        profile = fields.get("profile", "monster")
        mode = fields.get("mode", "auto")
        tier = fields.get("portable_target", "auto")
        if profile not in ALLOWED_PROFILES or mode not in ALLOWED_MODES or tier not in ALLOWED_TIERS:
            self._json({"error": "invalid profile/mode/portable target"}, 400)
            return

        job_id = f"{int(time.time())}-{secrets.token_hex(3)}"
        job_root = (self.server.jobs_root / job_id).resolve()
        inputs_dir = job_root / "inputs"
        output_root = job_root / "output"
        inputs_dir.mkdir(parents=True, exist_ok=True)
        output_root.mkdir(parents=True, exist_ok=True)

        input_paths: list[Path] = []
        for index, (_field, filename, payload) in enumerate(image_files):
            ext = Path(filename).suffix.lower()
            if ext not in {".png", ".jpg", ".jpeg", ".webp"}:
                continue
            dst = inputs_dir / f"{index:03d}-{_safe_name(filename)}"
            dst.write_bytes(payload)
            input_paths.append(dst)

        if not input_paths:
            self._json({"error": "no supported PNG/JPG/WEBP files"}, 400)
            return

        cmd = [
            sys.executable,
            str(HERE / "hayuya.py"),
            "--profile", profile,
            "--mode", mode,
            "--portable-target", tier,
            "--portable-pack", "auto",
            "--texture-delivery", "auto",
            "--output-root", str(output_root),
            "--execute",
        ]
        for p in input_paths:
            cmd.extend(["--input", str(p)])

        job = JobState(
            id=job_id,
            root=str(job_root),
            command=cmd,
            inputs=[str(p) for p in input_paths],
            profile=profile,
            mode=mode,
            portable_target=tier,
        )
        with JOBS_LOCK:
            JOBS[job_id] = job
        _emit(job, "created", {"job": job.public()})
        threading.Thread(target=_run_job, args=(job,), daemon=True).start()
        self._json(job.public(), 201)

    def log_message(self, fmt, *args):
        sys.stdout.write("[studio] " + (fmt % args) + "\n")


class StudioHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, handler, jobs_root: Path):
        self.jobs_root = jobs_root
        super().__init__(address, handler)


def main() -> int:
    parser = argparse.ArgumentParser(description="HAYUYA Studio — live local/LAN UI for the Hayuya pipeline.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--lan", action="store_true", help="listen on 0.0.0.0 so phones/tablets on the same LAN can open Studio")
    parser.add_argument("--jobs-root", type=Path, default=DEFAULT_JOBS_ROOT)
    args = parser.parse_args()

    host = "0.0.0.0" if args.lan else args.host
    args.jobs_root.mkdir(parents=True, exist_ok=True)
    server = StudioHTTPServer((host, args.port), StudioHandler, args.jobs_root.resolve())

    print("HAYUYA_STUDIO_READY")
    for url in local_addresses(args.port):
        if args.lan or "127.0.0.1" in url:
            print(f"  {url}")
    if args.lan:
        print("LAN mode exposes Studio to devices on your local network. Use a trusted network.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
