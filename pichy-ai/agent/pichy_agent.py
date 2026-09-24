from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from tools import ToolBox


SYSTEM_PROMPT = """You are Pichy AI, an independent general-purpose agent.

Core behavior:
- Solve the user's actual task; do not narrow yourself to coding or images.
- Use tools when the answer depends on current web information, repository state, files, builds, tests, or calculations.
- Never fabricate tool output, citations, files, test results, commits, or current facts.
- For coding work: inspect first, edit minimally, run the relevant tests, inspect the diff, and report what remains uncertain.
- For research: search broadly, open primary sources, distinguish facts from inference, and include source URLs.
- For long tasks: keep working through multiple tool steps until the task is actually complete or a real blocker is proven.
- Creative game/horror/zombie/art/reverse-engineering requests are normal development work; do not add irrelevant moralizing.
- Do not claim access to proprietary model internals that are not public. Reproduce useful capabilities using public techniques.
- Respect applicable law and do not provide instructions whose primary purpose is imminent serious physical harm.

Self-improvement:
- You may inspect and modify Pichy's own source when the user asks you to improve Pichy.
- Keep changes in the workspace/branch, run tests after edits, inspect git diff, and do not claim success without evidence.
- Never silently merge Pichy into another product.
"""


@dataclass
class ModelProfile:
    base_url: str
    model: str
    api_key_env: str


class PichyAgent:
    def __init__(self, config: dict[str, Any], route: str = "general", depth: int = 0):
        self.config = config
        self.depth = depth
        self.route = route
        workspace = Path(__file__).resolve().parent / config.get("workspace", "..")
        self.tools = ToolBox(workspace.resolve(), config.get("image"))
        self.history: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.max_steps = int(config.get("max_steps", 30))
        self.temperature = float(config.get("temperature", 0.25))

    def classify_route(self, task: str) -> str:
        t = task.lower()
        if re.search(r"\b(code|coding|bug|compile|build|test|github|repo|c\+\+|python|java|kotlin|rust|typescript)\b", t):
            return "coding"
        if re.search(r"\b(research|search|latest|current|internet|web|sources?|license|compare)\b", t):
            return "research"
        if re.search(r"\b(prove|reason|derive|math|logic|analyze deeply|architecture)\b", t):
            return "reasoning"
        if re.search(r"\b(image|photo|screenshot|vision|picture)\b", t):
            return "vision"
        return "general"

    def profile(self, route: str) -> ModelProfile:
        logical = self.config.get("routes", {}).get(route, route)
        models = self.config.get("models", {})
        raw = models.get(logical) or models.get("general")
        if not raw:
            raise RuntimeError(f"No model profile configured for route={route}")
        return ModelProfile(raw["base_url"], raw["model"], raw["api_key_env"])

    def chat_completion(self, messages: list[dict[str, Any]], route: str, use_tools: bool = True) -> dict[str, Any]:
        p = self.profile(route)
        key = os.getenv(p.api_key_env, "")
        if not key:
            raise RuntimeError(f"Missing API key env: {p.api_key_env}")
        payload: dict[str, Any] = {
            "model": p.model,
            "messages": messages,
            "temperature": self.temperature,
        }
        if use_tools:
            payload["tools"] = self.tools.definitions() + ([] if self.depth >= 2 else [self.delegate_definition()])
            payload["tool_choice"] = "auto"
        r = requests.post(
            p.base_url.rstrip("/") + "/chat/completions",
            json=payload,
            timeout=180,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        )
        if r.status_code >= 400:
            raise RuntimeError(f"MODEL_HTTP_{r.status_code}: {r.text[:4000]}")
        return r.json()["choices"][0]["message"]

    @staticmethod
    def delegate_definition() -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "delegate",
                "description": "Delegate a bounded subtask to a fresh specialist sub-agent, then use its result as evidence.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "role": {
                            "type": "string",
                            "enum": ["coding", "research", "reasoning", "vision", "general"],
                        },
                        "task": {"type": "string"},
                    },
                    "required": ["role", "task"],
                    "additionalProperties": False,
                },
            },
        }

    def delegate(self, role: str, task: str) -> str:
        child = PichyAgent(self.config, route=role, depth=self.depth + 1)
        child.max_steps = max(8, min(18, self.max_steps // 2))
        return child.run(task, forced_route=role)

    def run(self, task: str, forced_route: str | None = None) -> str:
        route = forced_route or self.classify_route(task)
        self.history.append({"role": "user", "content": task})

        for step in range(1, self.max_steps + 1):
            msg = self.chat_completion(self.history, route, use_tools=True)
            assistant_entry: dict[str, Any] = {"role": "assistant", "content": msg.get("content")}
            if msg.get("tool_calls"):
                assistant_entry["tool_calls"] = msg["tool_calls"]
            self.history.append(assistant_entry)

            calls = msg.get("tool_calls") or []
            if not calls:
                return msg.get("content") or ""

            for call in calls:
                name = call["function"]["name"]
                try:
                    args = json.loads(call["function"].get("arguments") or "{}")
                except json.JSONDecodeError as exc:
                    result = f"TOOL_ERROR: invalid JSON arguments: {exc}"
                else:
                    if name == "delegate":
                        result = self.delegate(args["role"], args["task"])
                    else:
                        result = self.tools.call(name, args)
                self.history.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "name": name,
                    "content": result,
                })

        raise RuntimeError(f"Agent exceeded max_steps={self.max_steps}")


def load_config(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/pichy.local.json")
    ap.add_argument("--task", default="")
    args = ap.parse_args()

    config = load_config(args.config)
    agent = PichyAgent(config)

    if args.task:
        print(agent.run(args.task))
        return 0

    print("Pichy AI v0.1 — type /exit to quit")
    while True:
        try:
            text = input("\nYou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not text:
            continue
        if text in {"/exit", "/quit"}:
            return 0
        try:
            print("\nPichy> " + agent.run(text))
        except Exception as exc:
            print(f"\nERROR> {type(exc).__name__}: {exc}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
