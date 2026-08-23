"""
Per-model capability check against Ollama's /api/show.

Confirmed live (see the "Agent" plan): passing a `tools` payload to a model
that doesn't support it isn't gracefully ignored by Ollama - it's a hard
HTTP 400 ("...does not support tools"). /api/show's `capabilities` array
(e.g. ["completion", "tools", "thinking"]) reliably predicts this ahead of
time, so the agent loop in chat_streaming.py checks this before ever
attaching `tools` to a request instead of trying and handling the failure.

Cached in-memory per model name - capabilities don't change at runtime, and
this avoids an extra Ollama round-trip on every single chat message.
"""
import httpx

_capability_cache: dict[str, bool] = {}


async def model_supports_tools(model: str) -> bool:
    if model in _capability_cache:
        return _capability_cache[model]

    supports_tools = False
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "http://localhost:11434/api/show",
                json={"model": model}
            )
            response.raise_for_status()
            capabilities = response.json().get("capabilities", [])
            supports_tools = "tools" in capabilities
    except Exception:
        # Unknown/unreachable model - default to no tools rather than risk
        # a 400 on the actual chat request.
        supports_tools = False

    _capability_cache[model] = supports_tools
    return supports_tools
