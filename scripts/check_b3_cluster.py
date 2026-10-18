"""Explicit, non-deploying B3 adapter smoke test against a chosen cluster.

Without --execute this only prints the plan; no SDK/config import or network I/O.
Pass an existing client key file, never key material. Inference may use cloud
tasks; all prompts are synthetic. No model-selected tools are executed.
Prepared run location: liara (.50), target VM108 (.161), TCP 9000/UDP 9001.
Only task routes backed by linep-ollama are covered. This is NOT an acceptance
test for parallel tool calls, explicit llama.cpp/VINOX models, or Personal UI.
"""
import argparse
import asyncio
import json
from pathlib import Path
import sys


PLAN = [
    "Signed lease/session bind and CAPABILITIES; task:fast/tool/json advertised",
    "Structured text CHAT: distinct system/user messages",
    "Structured CHAT streaming on task:fast: content/thinking separated",
    "Native b3_echo tool call: validate exact synthetic arguments locally",
    "Return tool result with call ID and request a final answer without tools",
    "task:json: validate prompted JSON (no schema-constrained format option yet)",
]
MARKER = "B3_SMOKE_7319"
TEXT_BUDGET = 512
TOOL_BUDGET = 2048
JSON_BUDGET = 2048


async def check_json(provider):
    response = await asyncio.to_thread(provider.chat_sync, "task:json", [
        {"role": "system", "content": 'Return only JSON: {"decisions":["Use LiNeP"],"open_tasks":["Check B3"]}'},
        {"role": "user", "content": "We decided to use LiNeP. Checking B3 is still open."},
    ], JSON_BUDGET, 0.0)
    assert json.loads(response) == {"decisions": ["Use LiNeP"], "open_tasks": ["Check B3"]}, "JSON mismatch"
    print("PASS structured JSON")


async def check(provider, json_only=False):
    if json_only:
        await check_json(provider)
        return
    caps = await asyncio.to_thread(provider._query_capabilities_sync)
    assert caps is not None, "No capabilities"
    advertised = set(caps.descriptor.supported_models)
    assert {"task:fast", "task:tool", "task:json"} <= advertised, "Required tasks missing"
    print("PASS capabilities")

    messages = [
        {"role": "system", "content": "Reply with only the exact marker supplied by the user."},
        {"role": "user", "content": MARKER},
    ]
    response = await asyncio.to_thread(provider.chat_message_sync, "task:fast", messages, TEXT_BUDGET, 0.0)
    assert MARKER in response["content"] and not response["tool_calls"], "Text reply mismatch"
    print("PASS structured text")

    content = []
    async for kind, payload in provider.chat_stream("task:fast", messages, TEXT_BUDGET, 0.0):
        assert kind in ("content", "thinking"), "Unexpected tool in text stream"
        if kind == "content":
            content.append(payload)
    assert MARKER in "".join(content), "Streaming reply mismatch"
    print("PASS structured stream")

    tools = [{"type": "function", "function": {
        "name": "b3_echo", "description": "Return the supplied marker unchanged.",
        "parameters": {"type": "object", "properties": {"marker": {"type": "string"}},
                       "required": ["marker"], "additionalProperties": False},
    }}]
    tool_messages = [
        {"role": "system", "content": "Call b3_echo once with the user's marker. After its result, return that marker."},
        {"role": "user", "content": MARKER},
    ]
    response = await asyncio.to_thread(
        provider.chat_message_sync, "task:tool", tool_messages, TOOL_BUDGET, 0.0, tools
    )
    calls = response["tool_calls"]
    assert len(calls) == 1, "Expected exactly one tool call"
    call = calls[0]
    if call["function"]["name"] != "b3_echo":
        print("Tool name diagnostic: " + json.dumps(call["function"]["name"][:80]))
    assert call["function"]["name"] == "b3_echo", "Unexpected tool name"
    assert call["function"]["arguments"] == {"marker": MARKER}, "Unexpected tool arguments"
    # Strict local fixture only: no dynamic dispatch, filesystem or remote tool.
    result = {"role": "tool", "content": MARKER}
    if call.get("id"):
        result["tool_call_id"] = call["id"]
    tool_messages.extend([{"role": "assistant", "content": response["content"], "tool_calls": calls}, result])
    final = await asyncio.to_thread(provider.chat_message_sync, "task:tool", tool_messages, TOOL_BUDGET, 0.0)
    assert MARKER in final["content"] and not final["tool_calls"], "Tool roundtrip did not finish"
    print("PASS single-tool roundtrip (parallel calls not covered)")

    await check_json(provider)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Actually send synthetic inference requests")
    parser.add_argument("--json-only", action="store_true", help="Isolate JSON after an earlier tool failure")
    parser.add_argument("--host")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--control-port", type=int, default=9001)
    parser.add_argument("--key-file", type=Path)
    parser.add_argument("--timeout", type=float, default=180)
    args = parser.parse_args()
    if not args.execute:
        print("PLAN ONLY - no network requests")
        for step in PLAN:
            print("- " + step)
        return 0
    if not args.host or not args.key_file or not args.key_file.is_file():
        parser.error("--execute requires --host and an existing --key-file")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
    from services.linep_provider import LinepChatProvider
    provider = LinepChatProvider(args.host, args.port, args.timeout,
                                 args.control_port, str(args.key_file))
    try:
        asyncio.run(check(provider, json_only=args.json_only))
    except Exception as error:
        # Never print SDK error strings, model responses, credentials or tracebacks.
        print("FAIL B3 smoke: " + type(error).__name__, file=sys.stderr)
        if isinstance(error, AssertionError):
            print("Check: " + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
