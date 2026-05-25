# NVIDIA NIM Failure Log

Stand: Mai 2026. Ermittelt durch:
- `scripts/phase1_quick_test.py --provider nvidia-nim` (30s Timeout, 3s RPM-Delay)
- `scripts/phase1_special_test.py` (60-90s Timeout, spezielle Parameter für Problem-Modelle, 3s RPM-Delay)
- **5 Modelle als "Downloadable (nur Self-Hosted)" klassifiziert und via `scripts/ignore.json` aus allen Tests ausgeschlossen**

## Root Cause Analysis

NVIDIA `/v1/models` listet **alle NIM-kompatiblen Modelle** (inkl. Self-Hosted/Container), aber der gehostete Endpoint `https://integrate.api.nvidia.com/v1` hat nur eine Teilmenge tatsächlich deployed. **57 Modelle** (51% aller gelisteten) geben 404 zurück — sie existieren nur im NIM-Katalog, nicht auf dem Shared-Hosted-API-Endpoint.

Zusätzlich wurden **5 Modelle** als "Downloadable (nur Self-Hosted)" identifiziert und in `ignore.json` ausgeschlossen (siehe `scripts/ignore.json`).

Fehlertypen:

| Kategorie | Count | Ursache |
|---|---|---|
| **404 — Nicht-chat Endpoint** | ~22 | Vision, Embedding, Safety, Speech Modelle (andere Endpoints erwartet) |
| **404 — Deprecated/Removed** | ~12 | Alte Modell-IDs (llama2, codegemma, mistral-large ohne Version) |
| **404 — Self-Hosted Only** | ~14 | Modelle nur für Container-NIM verfügbar (ibm/granite, writer/palmyra, ai21labs) |
| **404 — Nicht deployiert** | ~9 | Im Katalog gelistet aber auf hosted API nicht verfügbar |
| **T/O — Server Capacity** | 1 | Gemma-4-31b-it unter Last |
| **HTTP400 — Falscher Input** | 2 | Nemoretriever/Nemotron-Parse erwarten strukturierten Input |
| **HTTP500 — Server Error** | 1 | AI Synthetic Video Detector ist kaputt |

---

## 1. Non-Chat Endpoints (404)

Diese Modelle sind richtige Chat-Completion-Modelle und geben 404 weil sie einen anderen Endpoint benötigen (z.B. `/v1/embeddings`, `/v1/images/generations`, vision-spezifische Content-Formate).

| Modell-ID | Eigentlicher Endpoint |
|---|---|
| `adept/fuyu-8b` | `/v1/chat/completions` mit vision content format |
| `baai/bge-m3` | `/v1/embeddings` |
| `google/deplot` | `/v1/chat/completions` mit vision content format |
| `meta/llama-3.2-11b-vision-instruct` | OK — *funktioniert doch auf chat endpoint* |
| `meta/llama-3.2-90b-vision-instruct` | OK — *funktioniert doch auf chat endpoint* |
| `microsoft/kosmos-2` | `/v1/chat/completions` mit vision content |
| `microsoft/phi-3-vision-128k-instruct` | `/v1/chat/completions` mit vision content |
| `microsoft/phi-4-multimodal-instruct` | OK mit chat (0.3s) |
| `nvidia/cosmos-reason2-8b` | Vision |
| `nvidia/embed-qa-4` | `/v1/embeddings` |
| `nvidia/llama-3.1-nemotron-nano-vl-8b-v1` | OK mit chat (0.3s) |
| `nvidia/llama-3.2-nemoretriever-1b-vlm-embed-v1` | Embedding |
| `nvidia/llama-3.2-nv-embedqa-1b-v1` | `/v1/embeddings` |
| `nvidia/llama-nemotron-embed-1b-v2` | `/v1/embeddings` |
| `nvidia/llama-nemotron-embed-vl-1b-v2` | Embedding |
| `nvidia/neva-22b` | Vision |
| `nvidia/nv-embed-v1` | `/v1/embeddings` |
| `nvidia/nv-embedcode-7b-v1` | `/v1/embeddings` |
| `nvidia/nv-embedqa-e5-v5` | `/v1/embeddings` |
| `nvidia/nv-embedqa-mistral-7b-v2` | `/v1/embeddings` |
| `nvidia/nvclip` | Vision |
| `nvidia/vila` | Vision |
| `snowflake/arctic-embed-l` | `/v1/embeddings` |

## 2. Deprecated / Removed Model IDs (404)

Diese Modelle waren früher auf dem hosted API verfügbar, wurden aber entfernt. Die Modell-IDs existieren nur noch im `/v1/models`-Katalog für Abwärtskompatibilität mit Self-Hosted NIM.

| Modell-ID | Ersetzt durch |
|---|---|
| `google/gemma-2b` | `google/gemma-2-2b-it` |
| `google/recurrentgemma-2b` | Kein direkter Ersatz |
| `meta/codellama-70b` | `meta/llama-3.1-70b-instruct` (plus coding) |
| `meta/llama2-70b` | `meta/llama-3.3-70b-instruct` |
| `mistralai/codestral-22b-instruct-v0.1` | `mistralai/codestral-25.1` (falls deployed) |
| `mistralai/mistral-large` | `mistralai/mistral-large-3-675b-instruct-2512` |
| `mistralai/mistral-large-2-instruct` | `mistralai/mistral-large-3-675b-instruct-2512` |
| `nvidia/llama-3.1-nemotron-51b-instruct` | `nvidia/llama-3.3-nemotron-super-49b-v1` |
| `nvidia/llama3-chatqa-1.5-70b` | Kein direkter Ersatz |
| `nvidia/riva-translate-4b-instruct` | `nvidia/riva-translate-4b-instruct-v1.1` (OK) |

## 3. Self-Hosted Only (404)

Diese Modelle sind für Self-Hosted/Container-NIM-Deployments gedacht, nicht für den hosted Shared-API-Endpoint.

| Modell-ID | Notiz |
|---|---|
| `ai21labs/jamba-1.5-large-instruct` | Jamba Modelle nur über AI21 API direkt |
| `aisingapore/sea-lion-7b-instruct` | SEA-LION nur via Self-Hosted NIM |
| `ibm/granite-3.0-3b-a800m-instruct` | Granite Modelle nur via IBM/BAM API |
| `ibm/granite-3.0-8b-instruct` | Granite Modelle nur via Self-Hosted NIM |
| `ibm/granite-34b-code-instruct` | Granite Modelle nur via Self-Hosted NIM |
| `ibm/granite-8b-code-instruct` | Granite Modelle nur via Self-Hosted NIM |
| `nv-mistralai/mistral-nemo-12b-instruct` | Nur via Self-Hosted NIM |
| `nvidia/mistral-nemo-minitron-8b-8k-instruct` | Nur via Self-Hosted NIM |
| `nvidia/nemotron-4-340b-instruct` | Nur via Self-Hosted NIM |
| `nvidia/nemotron-4-340b-reward` | Nur via Self-Hosted NIM |
| `writer/palmyra-creative-122b` | Writer Modelle nur via Writer API |
| `writer/palmyra-fin-70b-32k` | Writer Modelle nur via Writer API |
| `writer/palmyra-med-70b` | Writer Modelle nur via Writer API |
| `writer/palmyra-med-70b-32k` | Writer Modelle nur via Writer API |

## 4. Not Deployed on Hosted API (404)

Diese Modelle sind im Katalog gelistet aber aktuell nicht auf dem hosted Endpoint deployt.

| Modell-ID |
|---|
| `bigcode/starcoder2-15b` |
| `databricks/dbrx-instruct` |
| `deepseek-ai/deepseek-coder-6.7b-instruct` |
| `google/codegemma-1.1-7b` |
| `google/codegemma-7b` |
| `google/gemma-3-12b-it` |
| `google/gemma-3-4b-it` |
| `microsoft/phi-3.5-moe-instruct` |
| `mistralai/mixtral-8x22b-v0.1` |
| `nvidia/llama-3.1-nemotron-70b-instruct` |
| `nvidia/llama-3.1-nemotron-ultra-253b-v1` |
| `nvidia/nemotron-nano-3-30b-a3b` |
| `zyphra/zamba2-7b-instruct` |

## 5. Special Tests — Corrected Results

Diese Modelle wurden im 30s-Standard-Test fälschlich als T/O oder Error klassifiziert.
Durch Special Tests (60-90s Timeout, spezielle Parameter) ergaben sich Korrekturen:

| Modell-ID | Alter Status | Neuer Status | Grund |
|---|---|---|---|
| `z-ai/glm-5.1` | T/O | **OK** (10.6s) | Braucht >30s für ersten Token |
| `qwen/qwen3.5-122b-a10b` | T/O | **OK** (14.9s) | Braucht >30s für ersten Token |
| `bytedance/seed-oss-36b-instruct` | T/O | **OK** (21.7s) | Braucht `thinking_budget` Parameter + >30s |
| `qwen/qwen3-next-80b-a3b-instruct` | T/O | **404** | "Deprecation in 7d", nur Self-Hosted |
| `qwen/qwen3.5-397b-a17b` | T/O | **404** | Nur Self-Hosted ("Downloadable") |
| `nvidia/ai-synthetic-video-detector` | HTTP500 | **ERR** | Kein Chat-Modell (Video via gRPC) |
| `nvidia/nemoretriever-parse` | HTTP400 | **ERR** | Kein Chat-Modell (Parser) |
| `nvidia/nemotron-parse` | HTTP400 | **ERR** | Kein Chat-Modell (Parser) |

### Special Test Details

**qwen3.5-122b-a10b** (14.9s):
- Standard chat request, `max_tokens=5`
- War vorher im 30s-Test, aber die 3s RPM-Delay + Serien-Test hat den Timeout verschärft
- Mit 60s und alleinigem Test funktioniert es

**z-ai/glm-5.1** (10.6s):
- Standard chat request, `max_tokens=5`
- 754B MoE — braucht lange zum Cold-Start aber liefert dann schnell
- Glm-5.1 hat **MCP Atlas 75.6%** — wäre idealer `power`-Kandidat
- Funktioniert reproduzierbar mit 60s Timeout

**bytedance/seed-oss-36b-instruct** (21.7s):
- Braucht `chat_template_kwargs: {"thinking_budget": 512}` Parameter
- Hat ein "thinking budget" Feature (Seed-spezifisch)
- Ohne diesen Parameter timed es aus (30s oder 60s reichen nicht)

## 7. Models Using `stg/` Prefix

Diese Modelle wurden über einen `stg/` (Staging) Präfix ausgeliefert, d.h. sie laufen auf einem separaten Staging-Inferenz-Stack:

| API-Name | Tatsächliches Model |
|---|---|
| `mistralai/ministral-14b-instruct-2512` | `stg/mistralai/ministral-14b-instruct-2512` |
| `mistralai/mixtral-8x7b-instruct-v0.1` | `stg/mistralai/mixtral-8x7b-instruct-v0.1` |
| `nvidia/nemotron-content-safety-reasoning-4b` | `stg/nvidia/nemotron-content-safety-reasoning-4b` |
| `stockmark/stockmark-2-100b-instruct` | `stg/stockmark/stockmark-2-100b-instruct` |

## 8. Timeouts (T/O — Server Capacity)

Einziger verbleibender T/O nach Special Tests:

| Modell-ID | Param | Timeout | Wahrscheinliche Ursache |
|---|---|---|---|
| `google/gemma-4-31b-it` | 31B | 60s | Serverkapazität/Neues Modell |

## 9. Error Models (Non-Chat)

Diese Modelle sind **keine Chat-Modelle** und wurden fälschlich auf `/v1/chat/completions` getestet:

| Modell-ID | Korrekter Endpoint |
|---|---|
| `nvidia/ai-synthetic-video-detector` | gRPC Video Analysis API (nicht HTTP chat) |
| `nvidia/nemoretriever-parse` | Eigener Parse/Rerank Endpoint |
| `nvidia/nemotron-parse` | Eigener Parse/Rerank Endpoint |

## Summary (Final Phase 1, nach ignore.json)

| Status | Count | % von 112 |
|---|---|---|
| **OK** | 51 | 45.5% |
| **404 (unavailable)** | 57 | 50.9% |
| **T/O** | 1 | 0.9% |
| **Error (non-chat)** | 3 | 2.7% |
| **Ignored (downloadable)** | 5 | — |

**Korrekturen durch Special Tests:**
- 3 Modelle wurden von T/O zu OK aufgewertet (glm-5.1, qwen3.5-122b, seed-oss-36b), aber anschließend in `ignore.json` ausgeschlossen
- 2 Modelle wurden von T/O zu 404 abgewertet (Downloadable-only: qwen3-next-80b, qwen3.5-397b)
- 3 Error-Modelle sind non-chat (falscher Endpoint) — gehören nicht in die Chat-Liste

**Fazit:** 51 Chat-Modelle funktionieren auf dem hosted API Endpoint. Die 404er (57) teilen sich auf in deprecated, self-hosted-only und nicht deployte Modelle.
