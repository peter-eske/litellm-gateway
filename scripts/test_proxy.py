#!/usr/bin/env python3
"""Test all 8 model aliases against local LiteLLM proxy on port 4000.

Usage:
    python scripts/test_proxy.py
"""
import json, os, sys, time, datetime
os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"
import httpx
from openai import OpenAI

def _client(timeout=600):
    return OpenAI(
        base_url=PROXY, api_key=API_KEY,
        http_client=httpx.Client(proxy=None, timeout=httpx.Timeout(timeout, connect=10)),
    )

PROXY = "http://localhost:4000"
MASTER_KEY = os.environ.get("LITELLM_MASTER_KEY", "sk-master-aRKrPNvkqJ78WTGLnUxgwluYMs9zS4pO")
API_KEY = MASTER_KEY  # Use master key for local testing (OpenCode key not registered in fresh DB)

MODELS = [
    ("default", "deepseek-ai/deepseek-v4-flash"),
    ("nim-llama", "meta/llama-3.3-70b-instruct"),
    ("fast", "mistralai/ministral-14b-instruct-2512"),
    ("power", "mistralai/mistral-large-3-675b-instruct-2512"),
    ("coding", "openai/gpt-oss-120b"),
    ("reasoning", "deepseek-ai/deepseek-v4-pro"),
    ("vision", "meta/llama-3.2-90b-vision-instruct"),
    ("safety", "nvidia/llama-3.1-nemoguard-8b-content-safety"),
]

results = {}


def test_health():
    print("[1/6] Testing /health/liveliness...", end=" ")
    try:
        import urllib.request
        resp = urllib.request.urlopen(f"{PROXY}/health/liveliness", timeout=5)
        body = resp.read().decode()
        ok = "alive" in body.lower()
        print(f"OK ({body})" if ok else f"FAIL ({body})")
        return {"ok": ok, "body": body}
    except Exception as e:
        print(f"ERROR: {e}")
        return {"ok": False, "error": str(e)}


def test_models_list():
    print("[2/6] Listing /v1/models...", end=" ")
    client = _client()
    try:
        models = client.models.list()
        names = sorted(getattr(m, 'id', getattr(m, 'model', str(m))) for m in models)
        expected = set(a for a, _ in MODELS)
        found = set(names)
        missing = expected - found
        if missing:
            print(f"PARTIAL (missing: {missing})")
            return {"ok": False, "found": list(found), "missing": list(missing), "names": names}
        print(f"OK ({len(names)} models)")
        return {"ok": True, "names": names}
    except Exception as e:
        print(f"ERROR: {e}")
        return {"ok": False, "error": str(e)}


def test_chat(client, alias, label):
    print(f"  [{label}] chat...", end=" ", flush=True)
    t0 = time.perf_counter()
    try:
        resp = client.chat.completions.create(
            model=alias,
            messages=[{"role": "user", "content": "Antworte kurz: Sag Hallo in 3-5 Worten."}],
            max_tokens=50,
            temperature=0.1,
        )
        dt = time.perf_counter() - t0
        choices = getattr(resp, 'choices', None)
        if not choices:
            raise ValueError(f"No choices in response: {resp}")
        msg = (choices[0].message.content or "")
        usage = getattr(resp, 'usage', None)
        tok = usage.total_tokens if usage else 0
        preview = msg[:60].encode("utf-8", errors="replace").decode("utf-8", errors="replace")
        print(f"OK {dt:.1f}s, {tok}tok")
        return {"ok": True, "latency_s": round(dt, 2), "tokens": tok, "text": msg[:60]}
    except Exception as e:
        dt = time.perf_counter() - t0
        print(f"FAIL ({dt:.1f}s): {e}")
        return {"ok": False, "latency_s": round(dt, 2), "error": str(e)}


def test_stream(client, alias, label):
    print(f"  [{label}] stream...", end=" ", flush=True)
    t0 = time.perf_counter()
    try:
        chunks = []
        stream = client.chat.completions.create(
            model=alias,
            messages=[{"role": "user", "content": "Count to 5, one per line."}],
            max_tokens=100,
            temperature=0.1,
            stream=True,
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                chunks.append(chunk.choices[0].delta.content)
        dt = time.perf_counter() - t0
        print(f"OK {dt:.1f}s, {len(chunks)}chunks")
        return {"ok": True, "latency_s": round(dt, 2), "chunks": len(chunks)}
    except Exception as e:
        dt = time.perf_counter() - t0
        print(f"FAIL ({dt:.1f}s): {e}")
        return {"ok": False, "latency_s": round(dt, 2), "error": str(e)}


def test_tools(client, alias, label):
    print(f"  [{alias}] tools...", end=" ", flush=True)
    t0 = time.perf_counter()
    try:
        resp = client.chat.completions.create(
            model=alias,
            messages=[{"role": "user", "content": "What's the weather in Berlin?"}],
            tools=[{
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather for a city.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "city": {"type": "string", "description": "City name"}
                        },
                        "required": ["city"]
                    }
                }
            }],
            max_tokens=100,
            temperature=0.1,
        )
        dt = time.perf_counter() - t0
        msg = resp.choices[0].message
        has_tool = bool(getattr(msg, 'tool_calls', None))
        if has_tool:
            tool_name = msg.tool_calls[0].function.name
            print(f"OK {dt:.1f}s, called \"{tool_name}(...)\"")
        else:
            text = (getattr(msg, 'content', None) or "")
            print(f"OK {dt:.1f}s, no tool call (text: \"{text[:40]}\")")
        return {"ok": True, "latency_s": round(dt, 2), "has_tool": has_tool}
    except Exception as e:
        dt = time.perf_counter() - t0
        print(f"FAIL ({dt:.1f}s): {e}")
        return {"ok": False, "latency_s": round(dt, 2), "error": str(e)}


def run():
    print("=" * 70)
    print(f"LOCAL PROXY TEST — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Proxy: {PROXY}")
    print("=" * 70)

    # 1. Health
    health = test_health()
    if not health.get("ok"):
        print("Proxy not healthy, aborting.")
        return {"health": health}

    # 2. Model list
    models_list = test_models_list()
    results["models_list"] = models_list

    # 3-6. For each model alias
    client = _client()
    stream_client = _client(timeout=600)
    results["models"] = {}

    print(f"\n[3/6] Chat completions (all 8 models)")
    for alias, _ in MODELS:
        r = test_chat(client, alias, alias)
        results["models"].setdefault(alias, {})["chat"] = r

    print(f"\n[4/6] Streaming")
    for alias, _ in MODELS:
        r = test_stream(stream_client, alias, alias)
        results["models"].setdefault(alias, {})["stream"] = r

    print(f"\n[5/6] Tool calling")
    for alias, _ in MODELS:
        r = test_tools(client, alias, alias)
        results["models"].setdefault(alias, {})["tools"] = r

    print(f"\n[6/6] Safety guard test")
    safety_client = _client()
    t0 = time.perf_counter()
    try:
        resp = safety_client.chat.completions.create(
            model="safety",
            messages=[{"role": "user", "content": "Sag Hallo"}],
            max_tokens=50,
        )
        dt = time.perf_counter() - t0
        msg = resp.choices[0].message.content
        print(f"  [safety] OK {dt:.1f}s: \"{msg[:60]}\"")
        results["models"]["safety"]["safety_test"] = {"ok": True, "latency_s": round(dt, 2), "text": msg[:60]}
    except Exception as e:
        dt = time.perf_counter() - t0
        print(f"  [safety] FAIL ({dt:.1f}s): {e}")
        results["models"]["safety"]["safety_test"] = {"ok": False, "latency_s": round(dt, 2), "error": str(e)}

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    all_ok = True
    for alias, _ in MODELS:
        r = results["models"].get(alias, {})
        chat = r.get("chat", {}).get("ok", False)
        stream = r.get("stream", {}).get("ok", False)
        tools = r.get("tools", {}).get("ok", False)
        ok_count = sum([chat, stream, tools])
        status = "OK" if ok_count == 3 else f"{ok_count}/3"
        if ok_count < 3:
            all_ok = False
        print(f"  {alias:<20} chat={'Y' if chat else 'N'} stream={'Y' if stream else 'N'} tools={'Y' if tools else 'N'} => {status}")
    print(f"\nOverall: {'ALL PASSED' if all_ok else 'SOME FAILED'}")
    return results


if __name__ == "__main__":
    results = run()
    out_path = "scripts/proxy_test_report.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nReport saved: {out_path}")
