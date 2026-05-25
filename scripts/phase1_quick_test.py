#!/usr/bin/env python3
"""Phase 1 — Quick health check aller Modelle eines API-Providers.

Sendet 1-Token Chat-Completion an jedes gelistete Modell, klassifiziert:
  OK  = funktioniert (mit Latenz + Tokens)
  404 = Modell existiert nicht (nur gelistet)
  410 = Modell dauerhaft entfernt
  T/O = Timeout
  ERR = Anderer Fehler

Usage:
    $env:NVIDIA_API_KEY = "nvapi-..."
    python scripts/phase1_quick_test.py --provider nvidia-nim

Output:
    scripts/phase1_results_{provider}.json
    scripts/good.json (updated)
"""

import argparse, json, os, sys, time
from openai import (
    OpenAI,
    NotFoundError,
    RateLimitError,
    APIStatusError,
    APITimeoutError,
    APIConnectionError,
)

sys.stdout.reconfigure(encoding="utf-8")

from provider_api import (
    get_provider, get_api_key, load_known_specs,
    load_ignore_list, add_to_ignore_list,
    load_good_data, save_good_data,
    is_model_complete, fetch_model_list, SCRIPTS_DIR,
)


CHECKPOINT_PATH = None
PROVIDER = None


def _save_checkpoint(all_models, to_test, results, ok_count, fail_404, fail_to, fail_other):
    ok_models = sorted([m for m, r in results.items() if r["status"] == "OK"])
    out = {
        "phase": 1,
        "provider": PROVIDER,
        "total_models": len(all_models),
        "models_tested": len(to_test),
        "summary": {"ok": ok_count, "404": fail_404, "timeout": fail_to, "error": fail_other},
        "ok_models": ok_models,
        "all_model_ids": all_models,
        "all_model_ids_tested": to_test,
        "results": results,
    }
    with open(CHECKPOINT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)


def quick_test(p, model_id, timeout):
    client = OpenAI(
        api_key=get_api_key(p),
        base_url=p["base_url"],
        timeout=timeout,
        max_retries=0,
    )
    try:
        t0 = time.perf_counter()
        raw = client.with_raw_response.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=1,
            temperature=0.1,
            stream=False,
        )
        resp = raw.parse()
        dt = time.perf_counter() - t0
        used = resp.model or "?"
        tok = resp.usage.total_tokens if resp.usage else 0
        fingerprint = resp.system_fingerprint
        finish = resp.choices[0].finish_reason if resp.choices else None
        rl = {}
        if raw.headers:
            for k, v in raw.headers.items():
                kl = k.lower()
                if "ratelimit" in kl or "rate-limit" in kl:
                    rl[k] = str(v)
        return {
            "status": "OK", "latency_s": round(dt, 2), "tokens": tok,
            "model_used": used, "fingerprint": fingerprint,
            "finish_reason": finish, "rate_limit_headers": rl,
        }
    except NotFoundError as e:
        return {"status": "404", "http": 404}
    except RateLimitError as e:
        return {"status": "RL", "http": 429}
    except APIStatusError as e:
        code = e.status_code
        if code == 410:
            return {"status": "410", "http": 410}
        return {"status": f"HTTP{code}", "http": code, "detail": e.message[:80]}
    except APITimeoutError as e:
        return {"status": "T/O", "detail": str(e)[:80]}
    except APIConnectionError as e:
        msg = str(e)
        if "timed out" in msg.lower() or "timeout" in msg.lower():
            return {"status": "T/O", "detail": msg[:80]}
        return {"status": "ERR", "detail": msg[:80]}
    except Exception as e:
        msg = str(e)
        if "timed out" in msg.lower() or "timeout" in msg.lower():
            return {"status": "T/O", "detail": msg[:80]}
        return {"status": "ERR", "detail": msg[:80]}


def main():
    global CHECKPOINT_PATH, PROVIDER
    parser = argparse.ArgumentParser(description="Phase 1 quick health check")
    parser.add_argument("--provider", default="nvidia-nim", help="Provider name from config.json")
    parser.add_argument("--resume", action="store_true", help="Load existing results and test only failed/untested models")
    args = parser.parse_args()
    PROVIDER = args.provider

    p = get_provider(PROVIDER)
    delay = p["rate_limit"]["delay_s"]
    timeout = p.get("timeout_s", {}).get("phase1", 30)
    CHECKPOINT_PATH = os.path.join(SCRIPTS_DIR, f"phase1_results_{PROVIDER}.json")
    known_specs = load_known_specs(p)

    print("=" * 70)
    mode = "RESUME (failed/untested only)" if args.resume else "FULL RUN (all models)"
    print(f"PHASE 1 — Quick Health Check: {p['name']}")
    print(f"Provider: {PROVIDER} | Mode: {mode} | Timeout: {timeout}s | RPM-Delay: {delay}s")
    print(f"API Key: ${p['env_api_key']}")
    print("=" * 70)

    # Fetch model list
    print("\n[1] Fetching model list from API...")
    try:
        all_models = fetch_model_list(p, timeout=15)
    except Exception as e:
        print(f"  ERROR: {e}")
        sys.exit(1)
    total_from_api = len(all_models)

    ignore_list = load_ignore_list(p, PROVIDER)
    if ignore_list:
        ignored = [m for m in all_models if m in ignore_list]
        all_models = [m for m in all_models if m not in ignore_list]
        print(f"  Ignored (downloadable-only): {len(ignored)}")
        for m in ignored:
            print(f"    - {m}")

    good_data = load_good_data(p, PROVIDER)
    if good_data.get("complete_ids"):
        complete_set = set(good_data["complete_ids"])
        already_good = [m for m in all_models if m in complete_set and is_model_complete(good_data, m)]
        if args.resume:
            all_models = [m for m in all_models if m not in complete_set or not is_model_complete(good_data, m)]
            print(f"  Skipped (good.json complete): {len(already_good)}")
            for m in already_good:
                print(f"    - {m}")

    known_chat = [m for m in all_models if known_specs.get(m, {}).get("t") == "chat"]
    unknown = [m for m in all_models if m not in known_chat]
    print(f"  Bekannte Chat-LLMs:  {len(known_chat)}")
    print(f"  Unbekannte/exotische: {len(unknown)}")
    if unknown:
        for m in unknown:
            t = known_specs.get(m, {}).get("t", "?")
            print(f"    - {m:55s} ({t})")

    # Load existing results if resuming
    results = {}
    ok_count = 0
    fail_404 = 0
    fail_to = 0
    fail_other = 0

    if args.resume and os.path.exists(CHECKPOINT_PATH):
        with open(CHECKPOINT_PATH, encoding="utf-8") as f:
            existing = json.load(f)
        results = existing.get("results", {})
        ok_count = sum(1 for r in results.values() if r["status"] == "OK")
        fail_404 = sum(1 for r in results.values() if r["status"] == "404")
        fail_to = sum(1 for r in results.values() if r["status"] == "T/O")
        fail_other = sum(1 for r in results.values() if r["status"] not in ("OK", "404", "T/O"))
        print(f"  Loaded existing: {len(results)} results ({ok_count} OK)")

    # Determine which models to test
    if args.resume and results:
        to_test = [m for m in all_models if m not in results or results[m]["status"] != "OK"]
        print(f"\n[2] Resume: {len(to_test)} models need testing ({delay}s delay)...")
    else:
        to_test = all_models
        print(f"\n[2] Testing {len(to_test)} models ({timeout}s timeout, {delay}s delay)...")

    for i, mid in enumerate(to_test):
        print(f"  [{i+1}/{len(to_test)}] {mid[:56]:56s}", end=" ", flush=True)
        result = quick_test(p, mid, timeout)
        results[mid] = result
        status = result["status"]

        if status == "OK":
            ok_count += 1
            lat = result["latency_s"]
            tok = result["tokens"]
            used = result["model_used"][:35]
            print(f"\r  [{i+1}/{len(to_test)}] OK    {mid[:55]:55s} {lat:5.1f}s {tok:3d}tok {used}", flush=True)
        elif status == "404":
            fail_404 += 1
            if add_to_ignore_list(mid, p, PROVIDER):
                print(f"\r  [{i+1}/{len(to_test)}] 404   {mid[:55]:55s}  [ignored]", flush=True)
            else:
                print(f"\r  [{i+1}/{len(to_test)}] 404   {mid[:55]:55s}", flush=True)
        elif status == "410":
            fail_other += 1
            print(f"\r  [{i+1}/{len(to_test)}] 410   {mid[:55]:55s}", flush=True)
        elif status == "T/O":
            fail_to += 1
            print(f"\r  [{i+1}/{len(to_test)}] T/O   {mid[:55]:55s}  ({result.get('detail','')[:40]})", flush=True)
        else:
            fail_other += 1
            det = result.get("detail", "")[:40]
            print(f"\r  [{i+1}/{len(to_test)}] {status:5s} {mid[:55]:55s}  {det}", flush=True)

        time.sleep(delay)

        if (i + 1) % 10 == 0 or i == 0:
            _save_checkpoint(all_models, to_test, results, ok_count, fail_404, fail_to, fail_other)

    avg_test_time = sum(r.get("latency_s", timeout / 2) for r in results.values() if r.get("latency_s")) / max(ok_count, 1)
    total_time = len(to_test) * (min(avg_test_time, timeout / 2) + delay) / 60
    print(f"\n  Avg latency: {avg_test_time:.1f}s — est. total: ~{total_time:.0f} min")

    # ── Summary ──────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("PHASE 1 — ZUSAMMENFASSUNG")
    print("=" * 70)
    print(f"  Provider:       {p['name']} ({PROVIDER})")
    print(f"  Modelle gesamt: {total_from_api}")
    print(f"  Getestet:       {len(to_test)}")
    print(f"  ---")
    print(f"  OK:             {ok_count}")
    print(f"  404:            {fail_404}")
    print(f"  Timeout:        {fail_to}")
    print(f"  Fehler:         {fail_other}")
    print()

    ok_models = sorted([mid for mid, r in results.items() if r["status"] == "OK"])
    print("--- OK Models ---")
    for mid in ok_models:
        r = results[mid]
        print(f"  {mid:60s} lat={r['latency_s']:.1f}s tok={r['tokens']}")

    print()
    print("--- 404 Models ---")
    for mid in sorted([mid for mid, r in results.items() if r["status"] == "404"]):
        print(f"  {mid}")

    print()
    print("--- Timeout Models ---")
    for mid in sorted([mid for mid, r in results.items() if r["status"] == "T/O"]):
        print(f"  {mid}")

    print()
    print("--- Error Models ---")
    for mid in sorted([mid for mid, r in results.items() if r["status"] not in ("OK", "404", "T/O")]):
        r = results[mid]
        print(f"  {mid:60s} {r['status']:10s} {r.get('detail','')[:60]}")

    # ── Retry failed models once (nur bei FULL RUN, nicht bei Resume) ──────
    failed = {mid: r for mid, r in results.items() if r["status"] not in ("OK",)}
    if failed and not args.resume:
        print(f"\n[3] Retry {len(failed)} failed models once...")
        retry_ok = 0
        for i, (mid, _) in enumerate(failed.items()):
            print(f"  [{i+1}/{len(failed)}] RETRY {mid[:56]:56s}", end=" ", flush=True)
            result = quick_test(p, mid, timeout)
            results[mid] = result
            if result["status"] == "OK":
                ok_count += 1
                retry_ok += 1
                lat = result["latency_s"]
                tok = result["tokens"]
                used = result["model_used"][:35]
                print(f"\r  [{i+1}/{len(failed)}] OK    {mid[:55]:55s} {lat:5.1f}s {tok:3d}tok {used}", flush=True)
            elif result["status"] == "404":
                if add_to_ignore_list(mid, p, PROVIDER):
                    print(f"\r  [{i+1}/{len(failed)}] 404   {mid[:55]:55s}  [ignored]", flush=True)
                else:
                    print(f"\r  [{i+1}/{len(failed)}] 404   {mid[:55]:55s}", flush=True)
            else:
                print(f"\r  [{i+1}/{len(failed)}] {result['status']:5s} {mid[:55]:55s}", flush=True)
            time.sleep(delay)
        print(f"\n  Retry ergab {retry_ok}/{len(failed)} neu OK")
        _save_checkpoint(all_models, to_test, results, ok_count, fail_404, fail_to, fail_other)
        print("  Checkpoint saved after retry")

    ok_count = sum(1 for r in results.values() if r["status"] == "OK")
    fail_404 = sum(1 for r in results.values() if r["status"] == "404")
    fail_to = sum(1 for r in results.values() if r["status"] == "T/O")
    fail_other = sum(1 for r in results.values() if r["status"] not in ("OK", "404", "T/O"))

    _save_checkpoint(all_models, to_test, results, ok_count, fail_404, fail_to, fail_other)
    print(f"\nErgebnisse gespeichert: {CHECKPOINT_PATH}")

    # ── Update good.json with new results ─────────────────────────────
    updated = 0
    for mid, r in results.items():
        entry = good_data.setdefault("models", {}).setdefault(mid, {})
        entry["phase1"] = {
            "status": r.get("status"),
            "latency_s": r.get("latency_s"),
            "tokens": r.get("tokens"),
            "model_used": r.get("model_used"),
            "fingerprint": r.get("fingerprint"),
            "finish_reason": r.get("finish_reason"),
            "rate_limit_headers": r.get("rate_limit_headers"),
            "http": r.get("http"),
            "detail": r.get("detail"),
        }
        if is_model_complete(good_data, mid) and mid not in good_data.get("complete_ids", []):
            good_data.setdefault("complete_ids", []).append(mid)
            updated += 1
    good_data["complete_count"] = len(good_data.get("complete_ids", []))
    good_data["model_count"] = len(good_data.get("models", {}))
    save_good_data(good_data, p)
    print(f"  good.json updated: {updated} newly complete models")
    print("\nPhase 1 abgeschlossen.")


if __name__ == "__main__":
    main()
