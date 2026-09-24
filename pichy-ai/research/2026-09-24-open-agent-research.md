# Open-agent research ledger — 2026-09-24

This file records the design evidence used for Pichy. It deliberately excludes proprietary leaked Claude Code source.

## Claude Code sourcemap incident

Public research repositories report that on 2026-03-31 a published Claude Code npm sourcemap exposed enough source information to reconstruct a large TypeScript tree. Independent analysis documents agent-loop, tools, prompt caching, context compaction, memory, skills and multi-agent design.

Use for Pichy: **behavioral/architectural lessons only**. Do not copy or redistribute Anthropic proprietary source.

Sources:
- https://github.com/cablate/claude-code-research
- https://github.com/anthropics/claude-code

## Open model families worth testing

### Kimi K3
Moonshot describes Kimi K3 as open-weight, native multimodal, 2.8T parameters, 1M context, and aimed at long-horizon coding, knowledge work and reasoning. License permits broad use subject to its stated service/revenue conditions.
- https://github.com/MoonshotAI/Kimi-K3
- https://github.com/MoonshotAI/Kimi-K3/blob/main/LICENSE

### GLM-4.7
Z.AI's GLM-4.7 is a coding/reasoning/tool-use MoE release. Model card lists MIT.
- https://huggingface.co/zai-org/GLM-4.7
- https://github.com/zai-org/GLM-4.5 (family repository and newer-series notes)

### Qwen3-Coder-Next
Qwen's coding-agent model supports 256K context and dedicated tool parsing in vLLM/SGLang, with GGUF distribution available.
- https://github.com/QwenLM/Qwen3-Coder

### DeepSeek-V3.2
DeepSeek describes V3.2 as reasoning-first for agents and its first model to integrate thinking directly into tool use.
- https://www.deepseek.com/en/news/deepseek-v3-2/
- https://github.com/deepseek-ai

### gpt-oss
OpenAI publishes gpt-oss-120b and gpt-oss-20b as Apache-2.0 open-weight reasoning/agentic models. 120b targets a single 80GB-class GPU; 20b is intended for lower-memory local/edge use.
- https://github.com/openai/gpt-oss
- https://openai.com/index/introducing-gpt-oss/

## Open agent harnesses worth learning from

### mini-SWE-agent
Minimal software-engineering agent, intentionally tiny and hackable, with shell as the principal tool and strong SWE-bench performance.
- https://github.com/SWE-agent/mini-swe-agent

### Aider
Repository map, git-native edits, broad model support, practical edit/test loop.
- https://github.com/Aider-AI/aider

### OpenHands
Full software-development agent environment with code edits, commands, browsing and APIs.
- https://github.com/All-Hands-AI/OpenHands

## Pichy conclusion

Do not build a single giant imitation model from a phone. Build a durable harness that can route between the strongest legally usable open models, own its tools and memory, and continuously benchmark replacements. That gives Pichy a path to frontier-level *system capability* even when no single model fits the user's hardware.
