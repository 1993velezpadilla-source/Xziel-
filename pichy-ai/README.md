# Pichy AI Lab

Pichy AI is an independent, model-agnostic agent experiment. It is intentionally **not connected to HAYUYA, HAYUYA Map, or XZIEL yet**.

The goal is a general assistant first: chat, deep web research, coding, repository work, files, terminal tools, sub-agents, image generation/edit iteration, memory, and self-improvement behind tests.

## Current: v0.3.0 lab

### Brain
- Autonomous multi-step agent loop.
- Logical model routes: general, reasoning, coding, research, vision, map modeling.
- Specialist sub-agents.
- Web search + URL retrieval.
- Workspace-scoped file search/read/write.
- Shell, git status/diff and calculator.
- OpenAI-compatible model and image-provider adapters.
- Git/test evidence requirement for coding work.
- Persistent SQLite conversation memory across server restarts.
- Executable Astral Gate benchmark runner.

### Server
FastAPI exposes:
- `GET /health`
- `GET /v1/capabilities`
- `POST /v1/chat`
- `POST /v1/chat/stream`
- `POST /v1/image`

Sessions are persisted in SQLite and restored after server restarts. Image sessions retain prior prompt context so revisions such as “make it taller” build on the accepted concept. Map Model uses a dedicated specialist prompt and `map_modeling/map_spec.schema.json` covering zones, connections, traversal, lighting, collision, navmesh, streaming, optimization and asset manifests.

### Android
A native lightweight APK provides:
- Chat mode.
- Research mode.
- Code mode.
- Image mode.
- Map Model mode for production-oriented 3D level/world planning.
- Persistent session ID.
- Server URL/token settings.
- Check Brain diagnostics for configured model routes and image provider.
- Image rendering from base64 or URL responses.
- No model weights bundled into the APK.

The phone is the client; large open-weight models run through configured providers or a machine you control.

## Configure

```bash
cd pichy-ai
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp config/pichy.example.json config/pichy.local.json
```

Edit `config/pichy.local.json`. Put API keys in environment variables named by the config; never commit keys.

Optional server authentication:

```bash
export PICHY_SERVER_TOKEN="a-long-random-secret"
```

Run:

```bash
uvicorn server.app:app --host 0.0.0.0 --port 8000
```

For the Android app, set the server URL in Settings. Cleartext HTTP is allowed in the lab APK so a phone can reach a development server on a LAN; production should use HTTPS and disable cleartext.

## Android build

Pinned toolchain:
- Android Gradle Plugin 9.4.0
- Gradle 9.6.0
- JDK 17
- compile/target SDK 36

GitHub Actions builds the APK and uploads `pichy-ai-lab-debug-apk` as a workflow artifact.

Manual build:

```bash
gradle -p android :app:assembleDebug
```

## Docker

```bash
docker build -t pichy-ai .
docker run --rm -p 8000:8000 \
  -e PICHY_GENERAL_API_KEY=... \
  -e PICHY_CODING_API_KEY=... \
  -e PICHY_RESEARCH_API_KEY=... \
  -e PICHY_REASONING_API_KEY=... \
  -e PICHY_VISION_API_KEY=... \
  -e PICHY_IMAGE_API_KEY=... \
  -e PICHY_SERVER_TOKEN=... \
  -v "$PWD/config/pichy.local.json:/app/config/pichy.local.json:ro" \
  -v "$PWD/data:/app/data" \
  pichy-ai
```

## Important boundary

Pichy can inspect and modify its own lab source when explicitly asked, but it cannot self-approve promotion. HAYUYA integration remains a later milestone after the Astral Gate benchmark is strong enough.


## Astral Gate

Run all configured benchmark cases:

```bash
python benchmarks/run_astral_gate.py --config config/pichy.local.json --out data/astral-report.json
```

Run a specific case:

```bash
python benchmarks/run_astral_gate.py --config config/pichy.local.json --only reasoning-boxes
```

The runner deliberately separates transport success from answer quality. A returned answer is not automatically counted as frontier-quality; review/critic grading comes next.
