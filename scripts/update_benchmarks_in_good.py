#!/usr/bin/env python3
"""
update_benchmarks_in_good.py — Übernimmt Benchmark-Daten aus bench.json in good.json.
V2: MERGED neue Daten, überschreibt nicht. Alte Daten bleiben erhalten.
"""
import json, re

good = json.load(open("scripts/good.json", encoding="utf8"))
bench = json.load(open("scripts/bench.json", encoding="utf8"))

def normalize(name):
    n = name.lower().replace("/", " ").replace("-", " ").replace("_", " ").replace(".", " ")
    n = re.sub(r'[^a-z0-9\s]', '', n)
    return re.sub(r'\s+', ' ', n).strip()

bench_tokens = {}
for bname in bench["models"]:
    for token in normalize(bname).split():
        if len(token) > 2:
            bench_tokens.setdefault(token, set()).add(bname)

manual_map = {
    "qwen/qwen3-coder-480b-a35b-instruct": ["Qwen3-Coder 480B/A35B Instruct", "qwen3-coder-480b-a35b-instruct", "qwen3-coder-480b"],
    "qwen/qwen2.5-coder-32b-instruct": ["Qwen2.5-Coder 32B Instruct", "qwen2.5-coder-32b"],
    "minimaxai/minimax-m2.5": ["MiniMax M2.5 (high reasoning)"],
    "minimaxai/minimax-m2.7": ["MiniMax M2.5 (high reasoning)"],
    "moonshotai/kimi-k2.6": ["Kimi K2 Instruct", "kimi-k2"],
    "moonshotai/kimi-k2.5": ["kimi-k2.5", "Kimi K2.5"],
    "z-ai/glm-5.1": ["GLM-5.1", "glm-5p1"],
    "z-ai/glm-5": ["GLM-5"],
    "openai/gpt-oss-120b": ["gpt-oss-120b", "Gpt-oss-120b"],
    "microsoft/phi-4-mini-instruct": [],
    "microsoft/phi-4-multimodal-instruct": [],
    "meta/llama-3.3-70b-instruct": ["Llama 3.3 70B"],
    "meta/llama-3.1-70b-instruct": ["Llama 3.1 70B"],
    "meta/llama-3.1-8b-instruct": ["Llama 3.1 8B"],
    "meta/llama-4-maverick-17b-128e-instruct": ["Llama 4 Maverick"],
}

matched_new = 0
for mid, entry in good.get("models", {}).items():
    old_benchmarks = dict(entry.get("benchmarks", {}))
    new_data_found = 0
    
    # 1) Manual map
    if mid in manual_map:
        for alias in manual_map[mid]:
            if alias in bench["models"]:
                for bn, sc in bench["models"][alias]["benchmarks"].items():
                    old_benchmarks[bn] = {"score": sc["score"]}
                    new_data_found += 1
                break
    
    # 2) Try normalization match  
    nid = normalize(mid.split("/")[-1])
    for bname in bench["models"]:
        nn = normalize(bname)
        if nid == nn or (nid in nn and len(nid) > 5) or (nn in nid and len(nn) > 5):
            for bn, sc in bench["models"][bname]["benchmarks"].items():
                old_benchmarks[bn] = {"score": sc["score"]}
                new_data_found += 1
            break
    
    # 3) Try token matching
    if new_data_found == 0:
        nid_tokens = set(nid.split())
        candidates = set()
        for token in nid_tokens:
            if len(token) > 2 and token in bench_tokens:
                candidates.update(bench_tokens[token])
        best_match = None
        best_overlap = 0
        for bname in candidates:
            bn_tokens = set(normalize(bname).split())
            overlap = len(nid_tokens & bn_tokens)
            if overlap > best_overlap and overlap >= max(2, len(nid_tokens) // 2):
                best_overlap = overlap
                best_match = bname
        if best_match:
            for bn, sc in bench["models"][best_match]["benchmarks"].items():
                old_benchmarks[bn] = {"score": sc["score"]}
                new_data_found += 1
    
    entry["benchmarks"] = old_benchmarks
    if new_data_found:
        matched_new += 1

total = len(good.get("models", {}))
print(f"Models: {total}")
print(f"Mit neuen Benchmarks ergänzt: {matched_new}")

# Show some results
print("\n--- Ausgewählte Modelle ---")
for mid in ["qwen/qwen3-coder-480b-a35b-instruct", "qwen/qwen2.5-coder-32b-instruct", "meta/llama-3.3-70b-instruct", "deepseek-ai/deepseek-v4-pro", "z-ai/glm-5.1"]:
    b = good["models"].get(mid, {}).get("benchmarks", {})
    print(f"\n{mid}:")
    for bk, bv in sorted(b.items()):
        print(f"  {bk}: score={bv['score']}")

json.dump(good, open("scripts/good.json", "w", encoding="utf8"), indent=2, ensure_ascii=False)
print(f"\nSaved scripts/good.json")
