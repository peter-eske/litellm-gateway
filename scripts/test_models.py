#!/usr/bin/env python3
"""Phase 2 — Testet OK-Modelle auf Streaming, Tool Calling, Max Output.

Nutzt Phase-1-Ergebnisse aus good.json (keine eigene Modell-Liste,
kein ignore-Filter, kein basic-Test). Nur die 3 Spezialtests.

Usage:
    $env:NVIDIA_API_KEY = "nvapi-..."
    python scripts/test_models.py --provider nvidia-nim

Output:
    - Aktualisiert good.json mit Phase-2-Ergebnissen
    - scripts/phase2_summary_{provider}.md (Kurzfassung)
"""

import argparse, json, os, sys, time
from openai import OpenAI

sys.stdout.reconfigure(encoding="utf-8")

from provider_api import (
    get_provider, get_api_key, load_good_data,
    save_good_data, is_model_complete, SCRIPTS_DIR,
)


def _extract_headers(headers):
    out = {}
    if headers is None:
        return out
    items = headers.items() if hasattr(headers, "items") else {}
    for k, v in items:
        kl = k.lower() if isinstance(k, str) else str(k).lower()
        if "ratelimit" in kl or "rate-limit" in kl:
            out[str(k)] = str(v)
    return out


def test_stream(p, model_id):
    client = OpenAI(
        api_key=get_api_key(p),
        base_url=p["base_url"],
        timeout=p.get("timeout_s", {}).get("default", 60),
        max_retries=0,
    )
    t0 = time.perf_counter()
    try:
        stream = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": "Count to 3"}],
            max_tokens=50,
            temperature=0.1,
            stream=True,
        )
        found_data = False
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                found_data = True
                break
            if chunk.choices and chunk.choices[0].finish_reason:
                break
        dt = time.perf_counter() - t0
        return {"ok": True, "stream": found_data, "first_chunk_s": round(dt, 2)}
    except Exception as e:
        return {"ok": False, "detail": str(e)}


def test_tool_call(p, model_id):
    client = OpenAI(
        api_key=get_api_key(p),
        base_url=p["base_url"],
        timeout=p.get("timeout_s", {}).get("default", 60),
        max_retries=0,
    )
    t0 = time.perf_counter()
    try:
        raw = client.with_raw_response.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": "What's the weather in Berlin?"}],
            tools=[{
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather for a city",
                    "parameters": {
                        "type": "object",
                        "properties": {"city": {"type": "string"}},
                        "required": ["city"],
                    },
                },
            }],
            max_tokens=100,
            temperature=0.1,
        )
        resp = raw.parse()
        dt = time.perf_counter() - t0
        has_tool = any(c.message.tool_calls for c in resp.choices if c.message.tool_calls)
        meta = {
            "headers": _extract_headers(raw.headers),
            "fingerprint": resp.system_fingerprint,
            "finish_reason": resp.choices[0].finish_reason if resp.choices else None,
        }
        return {"ok": True, "data": resp.model_dump(), "latency": round(dt, 2), "has_tool": has_tool, "meta": meta}
    except Exception as e:
        return {"ok": False, "detail": str(e)}


def test_max_output(p, model_id):
    client = OpenAI(
        api_key=get_api_key(p),
        base_url=p["base_url"],
        timeout=p.get("timeout_s", {}).get("default", 60),
        max_retries=0,
    )
    t0 = time.perf_counter()
    try:
        raw = client.with_raw_response.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": "Write a paragraph about AI. 5 sentences max."}],
            max_tokens=200,
            temperature=0.1,
        )
        resp = raw.parse()
        dt = time.perf_counter() - t0
        meta = {
            "headers": _extract_headers(raw.headers),
            "fingerprint": resp.system_fingerprint,
            "finish_reason": resp.choices[0].finish_reason if resp.choices else None,
        }
        tokens = resp.usage.completion_tokens if resp.usage else None
        return {"ok": True, "data": resp.model_dump(), "latency": round(dt, 2), "meta": meta, "tokens": tokens}
    except Exception as e:
        return {"ok": False, "detail": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Phase 2 — stream, tool, max_output tests")
    parser.add_argument("--provider", default="nvidia-nim", help="Provider name from config.json")
    args = parser.parse_args()
    PROVIDER = args.provider

    p = get_provider(PROVIDER)
    delay = p["rate_limit"]["delay_s"]

    print("=" * 70)
    print(f"PHASE 2 — Stream, Tool, Max Output: {p['name']}")
    print(f"Provider: {PROVIDER} | RPM-Delay: {delay}s")
    print("=" * 70)

    # ── 1. Load Phase 1 data from good.json ────────────────────────────
    print("\n[1] Loading Phase 1 results from good.json...")
    good_data = load_good_data(p, PROVIDER)
    models = good_data.get("models", {})

    phase1_ok = sorted([
        mid for mid, e in models.items()
        if e.get("phase1", {}).get("status") == "OK"
    ])
    print(f"  Phase 1 OK models: {len(phase1_ok)}")

    complete_set = set(good_data.get("complete_ids", []))
    to_test = [mid for mid in phase1_ok
               if mid not in complete_set or not is_model_complete(good_data, mid)]
    already_good = [mid for mid in phase1_ok if mid in complete_set and is_model_complete(good_data, mid)]

    if already_good:
        print(f"  Skipped (good.json complete): {len(already_good)}")
        for m in already_good:
            print(f"    - {m}")

    # ── 2. Run Phase 2 tests ───────────────────────────────────────────
    print(f"\n[2] Testing {len(to_test)} models (stream, tool, max_out)...")
    test_results = {}

    for i, mid in enumerate(to_test):
        print(f"  [{i+1}/{len(to_test)}] {mid[:55]:55s}", end=" ", flush=True)

        p1 = models.get(mid, {}).get("phase1", {})

        time.sleep(delay)
        stream = test_stream(p, mid)
        s_ok = stream.get("ok") and stream.get("stream", False)
        s_lat = stream.get("first_chunk_s", 0)

        time.sleep(delay)
        tool = test_tool_call(p, mid)
        t_ok = tool.get("ok") and tool.get("has_tool", False)

        time.sleep(delay)
        max_out = test_max_output(p, mid)

        meta_max = max_out.get("meta", {}) if max_out.get("ok") else {}
        mo_tokens = max_out.get("tokens") if max_out.get("ok") else None

        test_results[mid] = {
            "status": "OK",
            "latency_s": p1.get("latency_s"),
            "total_tokens": p1.get("tokens"),
            "model_used": p1.get("model_used"),
            "fingerprint": p1.get("fingerprint"),
            "finish_reason": p1.get("finish_reason"),
            "rate_limit_headers": p1.get("rate_limit_headers"),
            "stream_supported": s_ok,
            "stream_first_chunk_s": s_lat,
            "tool_call_supported": t_ok,
            "max_output_tokens": mo_tokens,
            "max_output_latency_s": max_out.get("latency") if max_out.get("ok") else None,
            "max_output_fingerprint": meta_max.get("fingerprint"),
            "max_output_finish_reason": meta_max.get("finish_reason"),
            "error_code": None,
            "error_detail": None,
        }

        mo_str = f"{mo_tokens}tok" if mo_tokens else "ERR"
        print(f"\r  [{i+1}/{len(to_test)}] {mid[:50]:50s} OK {p1.get('latency_s',0):5.1f}s "
              f"strm={'Y' if s_ok else 'N'}, tool={'Y' if t_ok else 'N'}, max_out={mo_str}, strm_lat={s_lat}s", flush=True)

    # ── 3. Update good.json ────────────────────────────────────────────
    print(f"\n[3] Writing results to good.json...")
    updated = 0
    for mid, r in test_results.items():
        entry = models.setdefault(mid, {})
        entry["phase2"] = {
            "stream": r.get("stream_supported"),
            "stream_lat": r.get("stream_first_chunk_s"),
            "tool": r.get("tool_call_supported"),
            "max_out": r.get("max_output_tokens"),
            "fingerprint": r.get("fingerprint"),
            "finish_reason": r.get("finish_reason"),
            "rate_limit_headers": r.get("rate_limit_headers"),
            "max_output_fingerprint": r.get("max_output_fingerprint"),
            "max_output_finish_reason": r.get("max_output_finish_reason"),
        }
        if is_model_complete(good_data, mid) and mid not in good_data.get("complete_ids", []):
            good_data.setdefault("complete_ids", []).append(mid)
            updated += 1

    good_data["complete_count"] = len(good_data.get("complete_ids", []))
    good_data["model_count"] = len(models)
    save_good_data(good_data, p)

    # ── 4. Short summary markdown ──────────────────────────────────────
    md_path = os.path.join(SCRIPTS_DIR, f"phase2_summary_{PROVIDER}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Phase 2 Summary: {p['name']}\n\n")
        f.write(f"Tested: {len(test_results)} | Already complete: {len(already_good)}\n\n")
        f.write("| Model ID | Latency | Stream | Tool | MaxOut | Fingerprint |\n")
        f.write("|---|---|---|---|---|---|\n")
        for mid, r in sorted(test_results.items()):
            lat = f"{r['latency_s']:.1f}s" if r.get("latency_s") else "\u2014"
            strm = "Y" if r.get("stream_supported") else "N"
            tool = "Y" if r.get("tool_call_supported") else "N"
            mo = f"{r['max_output_tokens']}t" if r.get("max_output_tokens") else "\u2014"
            fp = (r.get("fingerprint") or "\u2014")[:20]
            f.write(f"| `{mid}` | {lat} | {strm} | {tool} | {mo} | {fp} |\n")

    print(f"  Summary: {md_path}")
    print(f"  good.json: {updated} newly complete (total: {good_data['complete_count']}/{good_data['model_count']})")
    print("\nPhase 2 done.")


if __name__ == "__main__":
    main()
