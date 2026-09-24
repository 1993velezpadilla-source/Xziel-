from __future__ import annotations

import ast
import base64
import json
import math
import os
import re
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from ddgs import DDGS


class ToolError(RuntimeError):
    pass


class ToolBox:
    def __init__(self, workspace: str | Path, image_config: dict[str, Any] | None = None):
        self.workspace = Path(workspace).resolve()
        self.image_config = image_config or {}

    def _path(self, value: str) -> Path:
        p = (self.workspace / value).resolve()
        if p != self.workspace and self.workspace not in p.parents:
            raise ToolError("Path escapes workspace")
        return p

    def definitions(self) -> list[dict[str, Any]]:
        def fn(name: str, description: str, properties: dict[str, Any], required: list[str] | None = None):
            return {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required or [],
                        "additionalProperties": False,
                    },
                },
            }

        return [
            fn("read_file", "Read a UTF-8 text file inside the workspace.",
               {"path": {"type": "string"}, "max_chars": {"type": "integer"}}, ["path"]),
            fn("write_file", "Create or replace a UTF-8 text file inside the workspace.",
               {"path": {"type": "string"}, "content": {"type": "string"}}, ["path", "content"]),
            fn("search_files", "Regex-search text files in the workspace.",
               {"pattern": {"type": "string"}, "glob": {"type": "string"}, "max_results": {"type": "integer"}}, ["pattern"]),
            fn("shell", "Run a command in the workspace with a timeout. Use for builds, tests and git.",
               {"command": {"type": "string"}, "timeout_seconds": {"type": "integer"}}, ["command"]),
            fn("git_status", "Return git status --short and current branch.", {}),
            fn("git_diff", "Return git diff, optionally for a path.",
               {"path": {"type": "string"}}, []),
            fn("web_search", "Search the live web. Returns titles, snippets and URLs.",
               {"query": {"type": "string"}, "max_results": {"type": "integer"}}, ["query"]),
            fn("fetch_url", "Fetch a public HTTP(S) page and extract readable text.",
               {"url": {"type": "string"}, "max_chars": {"type": "integer"}}, ["url"]),
            fn("calculate", "Evaluate a basic arithmetic expression.",
               {"expression": {"type": "string"}}, ["expression"]),
            fn("generate_image", "Generate an image through the configured OpenAI-compatible image endpoint.",
               {"prompt": {"type": "string"}, "output_path": {"type": "string"}, "size": {"type": "string"}}, ["prompt"]),
        ]

    def call(self, name: str, args: dict[str, Any]) -> str:
        method = getattr(self, name, None)
        if not method or name.startswith("_"):
            raise ToolError(f"Unknown tool: {name}")
        try:
            result = method(**args)
            return result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as exc:
            return f"TOOL_ERROR: {type(exc).__name__}: {exc}"

    def read_file(self, path: str, max_chars: int = 120_000) -> str:
        p = self._path(path)
        return p.read_text(encoding="utf-8", errors="replace")[:max_chars]

    def write_file(self, path: str, content: str) -> str:
        p = self._path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"WROTE {p.relative_to(self.workspace)} ({len(content)} chars)"

    def search_files(self, pattern: str, glob: str = "**/*", max_results: int = 100) -> str:
        rx = re.compile(pattern, re.IGNORECASE)
        hits: list[str] = []
        for p in self.workspace.glob(glob):
            if len(hits) >= max_results:
                break
            if not p.is_file() or p.stat().st_size > 2_000_000:
                continue
            try:
                text = p.read_text(encoding="utf-8")
            except Exception:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if rx.search(line):
                    hits.append(f"{p.relative_to(self.workspace)}:{i}: {line[:400]}")
                    if len(hits) >= max_results:
                        break
        return "\n".join(hits) if hits else "NO_MATCHES"

    def shell(self, command: str, timeout_seconds: int = 120) -> str:
        timeout_seconds = max(1, min(timeout_seconds, 900))
        if os.getenv("PICHY_UNSAFE_SHELL") != "1":
            forbidden = [
                r"(^|\s)sudo(\s|$)",
                r"rm\s+-rf\s+/(\s|$)",
                r"(^|\s)(shutdown|reboot|poweroff)(\s|$)",
                r":\(\)\s*\{\s*:\|:&\s*\};:",
            ]
            if any(re.search(x, command) for x in forbidden):
                raise ToolError("Blocked destructive host command. Set PICHY_UNSAFE_SHELL=1 only in a disposable sandbox.")
        cp = subprocess.run(
            command,
            cwd=self.workspace,
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_seconds,
            env=os.environ.copy(),
        )
        out = cp.stdout[-80_000:]
        return f"EXIT={cp.returncode}\n{out}"

    def git_status(self) -> str:
        return self.shell("git branch --show-current && git status --short", 30)

    def git_diff(self, path: str = "") -> str:
        suffix = ""
        if path:
            suffix = " -- " + subprocess.list2cmdline([str(self._path(path).relative_to(self.workspace))])
        return self.shell("git diff" + suffix, 30)

    def web_search(self, query: str, max_results: int = 8) -> str:
        max_results = max(1, min(max_results, 20))
        rows = DDGS().text(query, max_results=max_results)
        return json.dumps(list(rows), ensure_ascii=False, indent=2)

    def fetch_url(self, url: str, max_chars: int = 60_000) -> str:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            raise ToolError("Only http/https URLs are allowed")
        r = requests.get(url, timeout=25, headers={"User-Agent": "PichyAI/0.1"})
        r.raise_for_status()
        ctype = r.headers.get("content-type", "")
        if "html" in ctype:
            soup = BeautifulSoup(r.text, "html.parser")
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            text = "\n".join(x.strip() for x in soup.stripped_strings)
        else:
            text = r.text
        return text[:max_chars]

    def calculate(self, expression: str) -> str:
        allowed_names = {k: getattr(math, k) for k in dir(math) if not k.startswith("_")}
        node = ast.parse(expression, mode="eval")
        for n in ast.walk(node):
            if isinstance(n, (ast.Call, ast.Name, ast.Load, ast.Expression, ast.BinOp, ast.UnaryOp,
                              ast.Constant, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod,
                              ast.USub, ast.UAdd, ast.FloorDiv)):
                continue
            raise ToolError(f"Unsupported expression node: {type(n).__name__}")
        value = eval(compile(node, "<calc>", "eval"), {"__builtins__": {}}, allowed_names)
        return repr(value)

    def generate_image(self, prompt: str, output_path: str = "pichy-output.png", size: str = "1024x1024") -> str:
        cfg = self.image_config
        if not cfg:
            raise ToolError("Image provider is not configured")
        key = os.getenv(cfg.get("api_key_env", ""), "")
        if not key:
            raise ToolError("Image API key environment variable is missing")
        url = cfg["base_url"].rstrip("/") + "/images/generations"
        payload = {
            "model": cfg["model"],
            "prompt": prompt,
            "n": 1,
            "size": size,
            "response_format": "b64_json",
        }
        r = requests.post(url, json=payload, timeout=180, headers={"Authorization": f"Bearer {key}"})
        r.raise_for_status()
        first = r.json()["data"][0]
        if first.get("b64_json"):
            data = base64.b64decode(first["b64_json"])
            p = self._path(output_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
            return f"IMAGE_SAVED {p.relative_to(self.workspace)}"
        if first.get("url"):
            return f"IMAGE_URL {first['url']}"
        raise ToolError("Provider returned no image data")
