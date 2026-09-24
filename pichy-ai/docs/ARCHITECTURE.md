# Architecture

## What Pichy borrows from public agent research

The agent does **not** copy Claude Code's proprietary leaked source. Public research into the accidental 2026 sourcemap exposure is used only as architectural evidence.

Transferable patterns:
- A small deterministic harness around a strong model often matters more than a giant pile of agent code.
- Tool ordering and stable schemas reduce context churn.
- Long sessions need explicit compaction/memory rather than endlessly growing prompts.
- Separate read-only research from side-effecting actions.
- Use specialists/sub-agents for bounded parallelizable tasks.
- Treat repository state, tests and diffs as evidence.
- Keep model selection separate from the tool/runtime layer.

## Pichy layers

1. **Client**
   Android/web/terminal. Presentation only.

2. **Coordinator**
   Maintains conversation state, routes tasks, requests tools and delegates specialists.

3. **Model router**
   Logical routes: general, reasoning, coding, research, vision. Each points to a replaceable model endpoint.

4. **Tool runtime**
   Files, shell, git, web search, fetch URL, calculator and image generation. Later: browser automation, GitHub write tools, document tools and persistent memory.

5. **Evidence gate**
   Pichy must not report a build/test/search as successful without tool evidence.

6. **Self-improvement lane**
   Pichy can modify itself in a lab branch, run tests and inspect diffs. Promotion requires an external gate; self-editing is not self-approval.

## Why multi-model

No current open-weight model is the cheapest/best at every task. A router lets us combine:
- frontier multimodal/long context,
- dedicated coding,
- deep reasoning,
- cheaper local fallback,
- specialized image generation.

The API/harness stays ours even as models change.

## Phone-first deployment

A Pixel/Android phone should not be expected to host Kimi K3 or a hundreds-of-billions parameter model. The APK talks to:
- a hosted open-model endpoint when online,
- optionally a PC/cloud box running vLLM/SGLang/llama.cpp,
- later a small quantized local model for offline fallback.

GitHub stores source and runs CI; GitHub itself is not the low-latency inference server.
