#!/usr/bin/env python3
"""
fetch_scale_leaderboard.py — Extrahiert Benchmark-Daten aus dem Scale AI Leaderboard
(labs.scale.com/leaderboard) aus dem Next.js RSC Payload.
Speichert als scripts/bench.json (Abschnitt "scale_ai").

Usage: python scripts/fetch_scale_leaderboard.py <html_datei>
"""
import json, re, sys

def extract_from_html(html_path):
    html = open(html_path, encoding="utf8").read()
    idx = html.find('self.__next_f.push([1,"')
    while idx >= 0:
        start = idx + len('self.__next_f.push([1,"')
        end = html.find('"])', start)
        if end < 0:
            break
        content = html[start:end]
        if "categories" in content:
            break
        idx = html.find('self.__next_f.push([1,"', end + 3)
    else:
        raise ValueError("categories push not found in HTML")

    s = content.replace('\\"', '"').replace('\\\\', '\\')
    m = re.match(r'\d+:', s)
    if m:
        s = s[m.end():]
    last_bracket = s.rfind("]")
    if last_bracket >= 0 and last_bracket < len(s) - 1:
        s = s[:last_bracket+1]

    rsc = json.loads(s)
    return rsc[3]["categories"]

def build_output(categories):
    output = {
        "source": "https://labs.scale.com/leaderboard",
        "fetched_at": "2026-05-25",
        "benchmarks": {},
        "models": {},
    }
    for cat in categories:
        name = cat["name"]
        output["benchmarks"][name] = {
            "id": cat["id"],
            "description": cat.get("description", ""),
            "category": cat.get("category", ""),
            "deprecated": cat.get("deprecated", False),
            "scores": {},
        }
        for entry in cat.get("scores", []):
            mn = entry["model"]
            output["benchmarks"][name]["scores"][mn] = {
                "rank": entry.get("rank"),
                "score": entry["score"],
                "ci_upper": entry.get("confidenceInterval_upper"),
                "company": entry.get("company", ""),
            }
            if mn not in output["models"]:
                output["models"][mn] = {"company": entry.get("company", ""), "benchmarks": {}}
            output["models"][mn]["benchmarks"][name] = {
                "rank": entry.get("rank"),
                "score": entry["score"],
                "ci_upper": entry.get("confidenceInterval_upper"),
            }
    return output

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fetch_scale_leaderboard.py <path_to_html>")
        sys.exit(1)
    cats = extract_from_html(sys.argv[1])
    out = build_output(cats)
    json.dump(out, open("scripts/bench_scale.json", "w", encoding="utf8"), indent=2, ensure_ascii=False)
    print(f"Saved scripts/bench_scale.json: {len(out['benchmarks'])} benchmarks, {len(out['models'])} models")
