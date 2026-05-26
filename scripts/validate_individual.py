"""Validate all 8 models individually (one at a time)."""
import os
os.environ["NO_PROXY"] = "*"
import json, time, sys
from openai import OpenAI

PROXY = "http://localhost:4000"
API_KEY = "sk-master-aRKrPNvkqJ78WTGLnUxgwluYMs9zS4pO"
client = OpenAI(base_url=PROXY, api_key=API_KEY)

MODELS = [
    "default", "nim-llama", "fast", "power",
    "coding", "reasoning", "vision", "safety",
]

results = {}
all_ok = True

for alias in MODELS:
    print(f"\n{'='*60}")
    print(f"  Testing: {alias}")
    print(f"{'='*60}")
    model_results = {}

    # 1. Chat
    t0 = time.perf_counter()
    try:
        r = client.chat.completions.create(
            model=alias,
            messages=[{"role": "user", "content": "Test: Say hello in 3 words."}],
            max_tokens=50, temperature=0.1,
        )
        t = time.perf_counter() - t0
        msg = (r.choices[0].message.content or "")
        tok = (getattr(r, "usage", None) or type("u",(),{"total_tokens":0})()).total_tokens
        print(f"  CHAT:   OK {t:>7.1f}s, {tok}tok, \"{msg[:40]}\"")
        model_results["chat"] = {"ok": True, "latency": round(t,1), "tokens": tok}
    except Exception as e:
        t = time.perf_counter() - t0
        print(f"  CHAT:   FAIL {t:>7.1f}s — {e}")
        model_results["chat"] = {"ok": False, "latency": round(t,1), "error": str(e)}
        all_ok = False

    # 2. Stream
    t0 = time.perf_counter()
    try:
        chunks = []
        for chunk in client.chat.completions.create(
            model=alias,
            messages=[{"role": "user", "content": "Count to 3."}],
            max_tokens=100, temperature=0.1, stream=True,
        ):
            if chunk.choices and chunk.choices[0].delta.content:
                chunks.append(chunk.choices[0].delta.content)
        t = time.perf_counter() - t0
        print(f"  STREAM: OK {t:>7.1f}s, {len(chunks)}chunks")
        model_results["stream"] = {"ok": True, "latency": round(t,1), "chunks": len(chunks)}
    except Exception as e:
        t = time.perf_counter() - t0
        print(f"  STREAM: FAIL {t:>7.1f}s — {e}")
        model_results["stream"] = {"ok": False, "latency": round(t,1), "error": str(e)}
        all_ok = False

    # 3. Tools
    t0 = time.perf_counter()
    try:
        r = client.chat.completions.create(
            model=alias,
            messages=[{"role": "user", "content": "Weather in Berlin?"}],
            tools=[{"type":"function","function":{"name":"get_weather","description":"Get weather","parameters":{"type":"object","properties":{"city":{"type":"string"}},"required":["city"]}}}],
            max_tokens=100, temperature=0.1,
        )
        t = time.perf_counter() - t0
        tool = r.choices[0].message.tool_calls[0].function.name if getattr(r.choices[0].message, "tool_calls", None) else None
        print(f"  TOOLS:  OK {t:>7.1f}s, tool={'get_weather' if tool else 'none'}")
        model_results["tools"] = {"ok": True, "latency": round(t,1), "has_tool": bool(tool)}
    except Exception as e:
        t = time.perf_counter() - t0
        status = "expected" if "nvidia/llama-3.1-nemoguard" in str(e) or "not been enabled" in str(e) else "unexpected"
        print(f"  TOOLS:  FAIL {t:>7.1f}s ({status}) — {e}")
        model_results["tools"] = {"ok": False, "latency": round(t,1), "error": str(e), "expected": status == "expected"}
        if status == "unexpected":
            all_ok = False

    results[alias] = model_results

print(f"\n{'='*60}")
print(f"  SUMMARY")
print(f"{'='*60}")
for alias in MODELS:
    r = results[alias]
    chat = r.get("chat",{}).get("ok",False)
    stream = r.get("stream",{}).get("ok",False)
    tools = r.get("tools",{}).get("ok",False)
    exp = r.get("tools",{}).get("expected",False)
    tools_str = "Y" if tools else ("(expected)" if exp else "N")
    ok_str = "OK" if chat and stream and (tools or exp) else "FAIL"
    print(f"  {alias:<12} chat={'Y' if chat else 'N'} stream={'Y' if stream else 'N'} tools={tools_str}  => {ok_str}")

print(f"\n  Overall: {'ALL PASSED' if all_ok else 'SOME FAILED'}")

out = "scripts/individual_validation.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print(f"\n  Report: {out}")
