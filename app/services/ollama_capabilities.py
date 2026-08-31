"""
Per-model capability check against Ollama's /api/show.

Confirmed live (see the "Agent" plan): passing a `tools` payload to a model
that doesn't support it isn't gracefully ignored by Ollama - it's a hard
HTTP 400 ("...does not support tools"). /api/show's `capabilities` array
(e.g. ["completion", "tools", "thinking"]) reliably predicts this ahead of
time, so the agent loop in chat_streaming.py checks this before ever
attaching `tools` to a request instead of trying and handling the failure.

Also used to gate the experimental LiNeP transport (see linep_provider.py):
LiNeP uses Ollama's /api/generate (RuntimeProfile.GENERATE, raw completion,
template is just `{{ .Prompt }}`) rather than /api/chat, so it never gets
Ollama's native thinking/content split for reasoning models - confirmed
live with nemotron-3-nano:4b (capabilities include "thinking"), whose
entire reasoning trace streamed as plain visible content instead of being
separated into its own 'thinking' SSE event.

Cached in-memory per model name (the full capabilities list, not just one
derived boolean) - capabilities don't change at runtime, and this avoids a
second /api/show round-trip for models that get checked for both tools and
thinking support.
"""
import httpx

_capability_cache: dict[str, list] = {}


async def _get_capabilities(model: str) -> list:
    if model in _capability_cache:
        return _capability_cache[model]

    capabilities: list = []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "http://localhost:11434/api/show",
                json={"model": model}
            )
            response.raise_for_status()
            capabilities = response.json().get("capabilities", [])
    except Exception:
        # Unknown/unreachable model - default to an empty capability list
        # rather than risk acting on a guess.
        capabilities = []

    _capability_cache[model] = capabilities
    return capabilities


async def model_supports_tools(model: str) -> bool:
    return "tools" in await _get_capabilities(model)


async def model_has_thinking_capability(model: str) -> bool:
    return "thinking" in await _get_capabilities(model)
