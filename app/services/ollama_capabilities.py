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
from typing import Optional

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


_context_length_cache: dict[str, Optional[int]] = {}

# Separate from _capability_cache/_get_capabilities above rather than folded
# into one shared /api/show response cache - keeps that already-verified
# function untouched; the extra per-model /api/show round trip only ever
# happens once per model per process (cached forever after), same as
# capabilities already are.
_DEFAULT_NUM_PREDICT = 2000  # chat_streaming.py's old hardcoded value, kept as the floor/unknown-model fallback
_ABSOLUTE_MAX_NUM_PREDICT = 8000  # matches SystemConfig.jsx's own Max-Tokens input (min=100, max=8000)
_CONTEXT_LENGTH_DIVISOR = 8  # response budget as a fraction of the model's total context window


async def _get_context_length(model: str) -> Optional[int]:
    if model in _context_length_cache:
        return _context_length_cache[model]

    context_length: Optional[int] = None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "http://localhost:11434/api/show",
                json={"model": model}
            )
            response.raise_for_status()
            model_info = response.json().get("model_info", {})
            # Key is namespaced per model family (e.g. "llama.context_length",
            # "gptoss.context_length") - there's no fixed key name to look up
            # directly, but exactly one *.context_length entry is always
            # present when model_info is non-empty.
            for key, value in model_info.items():
                if key.endswith(".context_length") and isinstance(value, int):
                    context_length = value
                    break
    except Exception:
        context_length = None

    _context_length_cache[model] = context_length
    return context_length


async def get_model_num_predict(model: str, configured_max_tokens: int) -> int:
    """
    Response-length budget for a single Ollama call, replacing the flat
    hardcoded num_predict chat_streaming.py used to send regardless of
    model or the (previously unused - see SystemConfig.jsx/config_service.py)
    admin "Max Tokens" setting.

    `configured_max_tokens` (the admin-configured floor/default) is combined
    with a per-model value derived from the model's own reported context
    window, not used as a hard ceiling for every model - a large-context
    model can exceed the admin default when it has the room for it (e.g. a
    long <workspace_artifact> plan), while a model with no reported context
    length (or an unreachable Ollama) just falls back to the admin value
    unchanged. Both are still capped at _ABSOLUTE_MAX_NUM_PREDICT so neither
    side can request a runaway-length response.
    """
    context_length = await _get_context_length(model)
    if not context_length:
        return min(max(configured_max_tokens, _DEFAULT_NUM_PREDICT), _ABSOLUTE_MAX_NUM_PREDICT)

    model_derived = context_length // _CONTEXT_LENGTH_DIVISOR
    return min(max(configured_max_tokens, model_derived), _ABSOLUTE_MAX_NUM_PREDICT)
