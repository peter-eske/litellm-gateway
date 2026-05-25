#!/usr/bin/env python3
"""Restore lost benchmark data from the old benchmarks.json"""
import json

g = json.load(open("scripts/good.json", encoding="utf8"))

restore = {
    "ibm/granite-3.0-8b-instruct": {"he": "89.7%"},
    "meta/llama-3.1-70b-instruct": {"swe_ver": "~65%", "mmlu": "86.4%"},
    "meta/llama-3.3-70b-instruct": {"swe_ver": "~72%", "mmlu": "89.2%", "he": "88.4%"},
    "meta/llama-3.1-8b-instruct": {"gsm8k": "84.5%"},
    "meta/llama-4-maverick-17b-128e-instruct": {"swe_pro": "5.24", "swe_ver": "32%"},
    "microsoft/phi-4-mini-instruct": {"gsm8k": "88.6%"},
    "moonshotai/kimi-k2.6": {"swe_pro": "27.67", "swe_ver": "80.2%", "lcb": "89.6%", "mcp_atlas": "64.4%"},
    "openai/gpt-oss-120b": {"swe_pro": "16.20", "mmlu": "83.5%"},
    "qwen/qwen3-coder-480b-a35b-instruct": {"swe_pro": "38.70%", "swe_ver": "~70%"},
}

for mid, data in restore.items():
    if mid in g["models"]:
        for k, v in data.items():
            g["models"][mid]["benchmarks"][k] = v
        print(f"  {mid}: restored {list(data.keys())}")

json.dump(g, open("scripts/good.json", "w", encoding="utf8"), indent=2, ensure_ascii=False)
print(f"\nSaved scripts/good.json")
