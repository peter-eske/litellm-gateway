#!/usr/bin/env python3
"""
fetch_swebench.py — Extrahiert SWE-bench Leaderboard-Daten von swebench.com
(Verified, bash-only, Multilingual, Lite, Full, Multimodal).
Speichert als scripts/bench_swebench.json.

Usage: python scripts/fetch_swebench.py <html_datei_von_index.html>
"""
import json, sys

def extract_from_html(html_path):
    html = open(html_path, encoding="utf8").read()
    start = html.index('<script type="application/json" id="leaderboard-data">')
    start = html.index(">", start) + 1
    end = html.index("</script>", start)
    data = html[start:end].strip()
    return json.loads(data)

def build_output(leaderboards):
    output = {
        "source": "https://www.swebench.com",
        "fetched_at": "2026-05-25",
        "benchmarks": {},
        "models": {},
    }
    for lb in leaderboards:
        name = f"SWE-bench {lb['name']}"
        output["benchmarks"][name] = {
            "id": f"swebench_{lb['name']}",
            "description": lb.get("description", ""),
            "category": "coding",
            "deprecated": False,
            "scores": {},
        }
        for entry in lb.get("results", []):
            mn = entry["name"]
            resolved = entry.get("resolved", 0)
            output["benchmarks"][name]["scores"][mn] = {
                "score": float(resolved) if resolved else 0,
                "oss": entry.get("oss", False),
                "date": entry.get("date", ""),
                "tags": entry.get("tags", []),
                "agent_version": entry.get("mini-swe-agent_version", ""),
                "company": "",
            }
            if mn not in output["models"]:
                output["models"][mn] = {"company": "", "benchmarks": {}}
            output["models"][mn]["benchmarks"][name] = {"score": float(resolved) if resolved else 0}
    return output

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fetch_swebench.py <path_to_index.html>")
        sys.exit(1)
    lbs = extract_from_html(sys.argv[1])
    out = build_output(lbs)
    json.dump(out, open("scripts/bench_swebench.json", "w", encoding="utf8"), indent=2, ensure_ascii=False)
    print(f"Saved scripts/bench_swebench.json: {len(out['benchmarks'])} benchmarks, {len(out['models'])} models")
