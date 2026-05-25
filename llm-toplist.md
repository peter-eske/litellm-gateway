# LLM Toplist — Top 3 Modelle pro Rolle für OpenCode

> **Ranglisten basieren auf allen Benchmark-Quellen:** SWE-bench (Verified, bash-only, Multilingual) von swebench.com, Scale AI Leaderboard (MCP Atlas, Fortress, etc.), und proprietären Benchmarks (swe_pro, swe_ver, mmlu, lcb, he, gsm8k).
> Datenbasis: `scripts/good.json` (113 Modelle + `scripts/bench.json` mit 45 Benchmarks, 438 Modellen). Stand: Mai 2026.

## nim-llama (Chat/General — OpenCode aktuell)

Sortiert nach: SWE-bench Pro > SWE-bench Ver > MMLU > HumanEval

| Rang | Modell | Parameter | Kontext | Latenz | Benchmarks |
|---|---|---|---|---|---|
| 1 | `deepseek-ai/deepseek-v4-flash` | 284B/13B | 1M | 1.1s | swe_ver=79%, lcb=91.6% |
| 2 | `mistralai/mistral-large-3-675b-instruct-2512` | 675B/41B | 256K | 0.4s | mmlu=85.5 |
| 3 | `meta/llama-3.3-70b-instruct` | 70B | 128K | 2.2s | swe_ver=72%, mmlu=89.2, he=88.4 |
| — | *aktuell: `meta/llama-3.3-70b-instruct`* | 70B | 128K | 2.2s | swe_ver=72%, mmlu=89.2, he=88.4 |

## default (Allrounder)

Sortiert nach: SWE-bench Ver > LCB > MMLU > Tool-Support

| Rang | Modell | Parameter | Latenz | Tools | Benchmarks |
|---|---|---|---|---|---|
| 1 | `deepseek-ai/deepseek-v4-flash` | 284B/13B | 1.1s | ✅ | swe_ver=79%, lcb=91.6% |
| 2 | `mistralai/mistral-large-3-675b-instruct-2512` | 675B/41B | 0.4s | ✅ | mmlu=85.5 |
| 3 | `deepseek-ai/deepseek-v4-pro` | 1.6T/49B | 1.6s | ❌ | swe_ver=80.6, lcb=93.5, mmlu=87.9 |
| — | *aktuell: `deepseek-ai/deepseek-v4-flash`* | 284B/13B | 1.1s | ✅ | swe_ver=79%, lcb=91.6% |

## fast (Low-Latency)

Sortiert nach: Latenz (asc) > GSM8K > Benchmarks, bevorzugt <10B Parameter

| Rang | Modell | Parameter | Latenz | Benchmarks |
|---|---|---|---|---|
| 1 | `mistralai/mistral-7b-instruct-v0.3` | 7B | 0.2s | — |
| 2 | `nvidia/nemotron-mini-4b-instruct` | 4B | 0.2s | — |
| 3 | `meta/llama-3.2-3b-instruct` | 3B | 0.2s | — |
| — | *aktuell: `microsoft/phi-4-mini-instruct`* | 3.8B | 0.3s | gsm8k=88.6% |

## power (Maximale Qualität)

Sortiert nach: SWE-bench Pro > SWE-bench Ver > LCB > MMLU

| Rang | Modell | Parameter | Latenz | Tools | Benchmarks |
|---|---|---|---|---|---|---|
| 1 | `deepseek-ai/deepseek-v4-flash` | 284B/13B | 1.1s | ✅ | swe_ver=79%, lcb=91.6% |
| 2 | `mistralai/mistral-large-3-675b-instruct-2512` | 675B/41B | 0.4s | ✅ | mmlu=85.5 |
| 3 | `qwen/qwen3-coder-480b-a35b-instruct` | 480B/35B | 1.2s | ✅ | swe_pro=38.7%, swe_ver=~70% |
| — | *aktuell: `qwen/qwen3-coder-480b-a35b-instruct`* | 480B/35B | 1.2s | ✅ | **swe_pro=38.7%**, swe_ver=~70% |

## coding (Code + Tool Calling)

Sortiert nach: LCB > SWE-bench Ver > HumanEval > Tool-Support

| Rang | Modell | Parameter | Latenz | Tools | Benchmarks |
|---|---|---|---|---|---|
| 1 | `deepseek-ai/deepseek-v4-flash` | 284B/13B | 1.1s | ✅ | swe_ver=79%, lcb=91.6% |
| 2 | `moonshotai/kimi-k2.6` | ? | ? | ✅ | swe_ver=80.2%, lcb=89.6% |
| 3 | `meta/llama-3.3-70b-instruct` | 70B | 2.2s | ✅ | swe_ver=~72%, he=88.4% |
| — | *aktuell: `deepseek-ai/deepseek-v4-flash`* | 284B/13B | 1.1s | ✅ | swe_ver=79%, lcb=91.6% |

## Benchmark-Übersicht

| Kürzel | Vollname | Quelle | Modelle |
|--------|----------|--------|---------|
| swe_pro | SWE-bench Pro | scaleapi.github.io | 7 |
| swe_ver | SWE-bench Verified | benchmarks.json (proprietär) | 8 |
| SWE-bench Verified | SWE-bench Verified (mini-SWE-agent) | swebench.com | 22 |
| SWE-bench bash-only | SWE-bench bash-only (mini-SWE-agent) | swebench.com | 9 |
| lcb | LiveCodeBench | benchmarks.json | 3 |
| mmlu | MMLU | benchmarks.json | 7 |
| he | HumanEval | benchmarks.json | 2 |
| gsm8k | GSM8K | benchmarks.json | 3 |
| mcp_atlas | MCP Atlas | benchmarks.json | 1 |
| MCP Atlas | MCP Atlas | Scale AI Leaderboard | 1 |
| aime | AIME | benchmarks.json | 1 |
| Fortress | Fortress (Safety) | Scale AI Leaderboard | 2 |

## Datenquellen

| Quelle | URL |
|--------|-----|
| Scale AI Leaderboard | https://labs.scale.com/leaderboard |
| SWE-bench Leaderboard | https://www.swebench.com |
| SWE-bench Pro (GitHub Pages) | https://scaleapi.github.io/SWE-bench_Pro-os/ |
| NVIDIA NIM API | https://integrate.api.nvidia.com/v1 |
| Vollständige Modelldaten | `scripts/good.json`, `scripts/bench.json` |
| Testskripte | `scripts/phase1_quick_test.py`, `scripts/test_models.py` |
| Extraktionsskripte | `scripts/fetch_scale_leaderboard.py`, `scripts/fetch_swebench.py` |
| Ranking | `scripts/rank_models.py` |
