# Pichy AI Lab

Pichy AI is an independent, model-agnostic agent experiment. It is intentionally **not connected to HAYUYA, HAYUYA Map, or XZIEL yet**.

The goal is to build a general assistant first: chat, deep web research, coding, repository work, files, terminal tools, sub-agents, image generation, memory, and self-improvement behind tests. If it passes the Astral Gate benchmark, HAYUYA integration becomes a separate phase.

## Design

Pichy is not one model. It is a **router + agent harness**.

- General/reasoning model: configurable.
- Coding model: configurable.
- Research model: configurable.
- Vision/multimodal model: configurable.
- Image model: configurable.
- All language-model endpoints use OpenAI-compatible chat-completions where possible.
- Tools are owned by Pichy, not by a model vendor.

This lets one installation use Kimi, GLM, Qwen, DeepSeek, gpt-oss, a local llama.cpp server, or another compatible endpoint without rewriting the agent.

## Current v0.1

- Autonomous tool loop.
- Workspace-scoped file read/write/search.
- Shell execution with timeout.
- Git status/diff.
- Web search through DDGS.
- URL retrieval and text extraction.
- Calculator.
- Image generation through an OpenAI-compatible image endpoint.
- Sub-agent delegation for coding, research, debugging, architecture, and review.
- Model routing by task category.
- Conversation history.
- Explicit test gate before self-modifying changes are accepted.
- No dependency on leaked proprietary Claude Code source.

## Start

```bash
cd pichy-ai
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp config/pichy.example.json config/pichy.local.json
# edit endpoints/model ids and put API keys in environment variables, never in git
python agent/pichy_agent.py --config config/pichy.local.json
```

Then type a task.

## Phone strategy

The Android APK should remain a thin client. Running frontier open-weight models directly on a phone is not realistic; the APK will call this agent backend or a compatible hosted/local endpoint. Small GGUF models can later run on-device through llama.cpp for offline fallback.

## Self-improvement rule

Pichy may edit its own source when explicitly tasked to improve itself, but the branch is the safety boundary: changes must remain reviewable in git and pass tests/benchmarks before promotion. It never silently merges itself into HAYUYA.
