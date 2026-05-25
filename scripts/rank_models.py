#!/usr/bin/env python3
"""Rank top 3 models per OpenCode task from good.json"""
import json, re

good = json.load(open("scripts/good.json", encoding="utf8"))
models = good.get("models", {})

def val(v, default=0):
    if v is None: return default
    if isinstance(v, str):
        v = v.replace("~", "").replace("%", "").replace(",", ".")
        try: return float(v)
        except ValueError: return default
    if isinstance(v, (int, float)): return float(v)
    if isinstance(v, dict) and "score" in v:
        return val(v["score"])
    return default

def param_num(params):
    if isinstance(params, (int, float)): return params
    if isinstance(params, str):
        m = re.search(r'([\d.]+)', params.replace(",", "."))
        if m:
            n = float(m.group(1))
            if "T" in params: n *= 1000
            return n
    return 0

ok = {}
for mid, e in models.items():
    p1 = e.get("phase1") or {}
    p2 = e.get("phase2") or {}
    if p1.get("status") == "OK" and p2 and p2.get("stream") is not None:
        b = e.get("benchmarks") or {}
        s = e.get("specs") or {}
        lat = p1.get("latency_s")
        ok[mid] = {
            "params": s.get("p", 0),
            "latency": lat,
            "stream": p2.get("stream"),
            "tool": p2.get("tool"),
            "max_out": p2.get("max_out"),
            "benchmarks": b,
        }

print(f"OK models with Phase 2: {len(ok)}")

tasks = {
    "nim-llama": {
        "title": "Chat/General (OpenCode aktuell)",
        "rank_by": ["swe_pro", "swe_ver", "mmlu", "he", "SWE-bench Verified", "SWE-bench bash-only"],
    },
    "default": {
        "title": "Allrounder (Default-Alias)",
        "rank_by": ["swe_pro", "swe_ver", "mcp_atlas", "mmlu", "MCP Atlas", "SWE-bench Verified"],
    },
    "fast": {
        "title": "Low-Latency (Fast-Alias)",
        "rank_by": ["latency", "gsm8k", "swe_pro", "swe_ver"],
    },
    "power": {
        "title": "Maximale Qualitaet (Power-Alias)",
        "rank_by": ["swe_pro", "swe_ver", "lcb", "mmlu", "SWE-bench Verified", "SWE-bench bash-only"],
    },
    "coding": {
        "title": "Code + Tool Calling (Coding-Alias)",
        "rank_by": ["swe_pro", "swe_ver", "lcb", "he", "SWE-bench Verified", "SWE-bench bash-only"],
    },
}

current_config = {
    "nim-llama": "meta/llama-3.3-70b-instruct",
    "default": "z-ai/glm-5.1",
    "fast": "microsoft/phi-4-mini-instruct",
    "power": "qwen/qwen3-coder-480b-a35b-instruct",
    "coding": "qwen/qwen2.5-coder-32b-instruct",
}

def score_model(mid, fields, ok_data):
    b = ok_data.get("benchmarks") or {}
    total = 0
    count = 0
    for f in fields:
        v = b.get(f)
        if v is not None:
            total += val(v)
            count += 1
    return total / count if count > 0 else 0, count

for name, cfg in tasks.items():
    fields = [f for f in cfg["rank_by"] if f != "latency"]
    print(f"\n--- {name} - {cfg['title']} ---")
    
    candidates = []
    for mid, data in ok.items():
        b = data.get("benchmarks") or {}
        relevant = sum(1 for f in fields if f in b and b[f] is not None)
        if relevant == 0 and "latency" not in cfg["rank_by"]:
            continue
        comp_score, count = score_model(mid, fields, data)
        lat_penalty = 0
        if "latency" in cfg["rank_by"]:
            lat = data.get("latency")
            if lat is not None:
                lat_penalty = 1.0 / (1.0 + lat)
            pn = param_num(data.get("params", 0))
            if pn and pn < 10:
                lat_penalty += 0.3
        candidates.append((mid, data, comp_score, lat_penalty, relevant, count))

    if "latency" in cfg["rank_by"]:
        candidates.sort(key=lambda x: (x[3], x[2]), reverse=True)
    else:
        candidates.sort(key=lambda x: (x[2], x[4]), reverse=True)

    print(f"  {'Rank':<5} {'Model':<52} {'Params':<10} {'Lat':<7} {'Score':<8} {'#B':<4} Benchmarks")
    print(f"  {'-'*5} {'-'*52} {'-'*10} {'-'*7} {'-'*8} {'-'*4} {'-'*55}")
    for rank, (mid, data, score, lat_score, rel, cnt) in enumerate(candidates[:3], 1):
        b = data.get("benchmarks") or {}
        params = data.get("params") or "?"
        lat = data.get("latency")
        lat_s = f"{lat:.1f}s" if lat else "?"
        param_s = f"{params}B" if isinstance(params, (int, float)) else str(params)
        bench_str = " ".join(f"{k}={val(b.get(k),0):.1f}" for k in fields if k in b and b[k] is not None)
        extra = ""
        if "latency" in cfg["rank_by"]:
            extra = f" lat_score={lat_score:.2f}"
        print(f"  {rank:<5} {mid:<52} {param_s:<10} {lat_s:<7} {score:<8.4f} {cnt:<4} {bench_str}{extra}")
    
    curr = current_config.get(name, "")
    if curr and curr in ok:
        b = ok[curr]["benchmarks"]
        curr_bench = " ".join(f"{k}={val(b.get(k),0):.1f}" for k in fields if k in b and b[k] is not None)
        print(f"  [aktuell: {curr}] -> {curr_bench or 'keine Benchmarks'}")

# Full matrix
print("\n--- Vollstaendige Benchmark-Matrix ---")
all_bench_fields = ["swe_pro", "swe_ver", "lcb", "he", "gsm8k", "mmlu", "mcp_atlas", "aime", "mmlu_pro", "SWE-bench Verified", "SWE-bench bash-only", "SWE-bench Multilingual"]
hf = "  " + f"{'Model':<50}" + "".join(f"{f[:7]:>8}" for f in all_bench_fields)
print(hf)
print("  " + "-"*50 + "".join("-"*8 for _ in all_bench_fields))
for mid, data in sorted(ok.items(), key=lambda x: val(x[1]["benchmarks"].get("swe_pro", 0)), reverse=True):
    b = data.get("benchmarks") or {}
    line = f"  {mid:<50}"
    for f in all_bench_fields:
        v = b.get(f)
        line += f" {val(v):>7.1f}" if v is not None else f" {'':>8}"
    print(line)
