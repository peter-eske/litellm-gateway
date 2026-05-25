#!/usr/bin/env python3
"""Shared provider-agnostic API helpers for all test scripts.

Loads provider config from config.json, creates OpenAI-compatible clients,
loads model metadata, and provides convenience wrappers.
Uses the openai library (v2.x) instead of raw urllib.
"""

import json, os, time
from openai import OpenAI

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))


def load_config():
    with open(os.path.join(SCRIPTS_DIR, "config.json"), encoding="utf-8") as f:
        return json.load(f)


def get_provider(provider_name):
    cfg = load_config()
    p = cfg["providers"].get(provider_name)
    if not p:
        keys = list(cfg["providers"].keys())
        raise ValueError(f"Unknown provider '{provider_name}'. Available: {keys}")
    return p


def get_api_key(provider_cfg):
    key = os.environ.get(provider_cfg["env_api_key"])
    if not key:
        raise ValueError(
            f"Set {provider_cfg['env_api_key']} environment variable "
            f"(provider: {provider_cfg['name']})"
        )
    return key


def create_client(provider_cfg, timeout=None):
    return OpenAI(
        api_key=get_api_key(provider_cfg),
        base_url=provider_cfg["base_url"],
        timeout=timeout or provider_cfg.get("timeout_s", {}).get("default", 60),
        max_retries=0,
    )


def load_known_specs(provider_cfg):
    path = os.path.join(SCRIPTS_DIR, provider_cfg.get("known_specs_file", ""))
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_benchmarks(provider_cfg):
    path = os.path.join(SCRIPTS_DIR, provider_cfg.get("benchmarks_file", ""))
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _extract_headers(headers):
    """Extract rate-limit/request metadata from httpx.Headers or dict."""
    out = {}
    if headers is None:
        return out
    items = headers.items() if hasattr(headers, "items") else {}
    for k, v in items:
        kl = k.lower() if isinstance(k, str) else str(k).lower()
        if any(x in kl for x in ("ratelimit", "rate-limit", "x-request", "x-cache", "server-timing")):
            out[str(k)] = str(v)
    return out


def fetch_model_list(provider_cfg, timeout=15):
    client = create_client(provider_cfg, timeout=timeout)
    models = client.models.list()
    seen = set()
    result = []
    for m in models:
        mid = m.id
        if mid and mid not in seen:
            seen.add(mid)
            result.append(mid)
    return sorted(result)


def chat_completion(provider_cfg, data, timeout=None):
    """Send a non-streaming chat completion. Returns dict with ok/data/latency/meta."""
    client = create_client(provider_cfg, timeout=timeout)
    model = data.get("model")
    messages = data.get("messages", [])
    kwargs = {k: v for k, v in data.items() if k not in ("model", "messages")}
    t0 = time.perf_counter()
    try:
        raw = client.with_raw_response.chat.completions.create(
            model=model, messages=messages, **kwargs
        )
        resp = raw.parse()
        dt = time.perf_counter() - t0
        meta = {
            "headers": _extract_headers(raw.headers),
            "http_status": raw.status_code,
            "fingerprint": resp.system_fingerprint,
        }
        return {"ok": True, "data": resp.model_dump(), "latency": round(dt, 2), "meta": meta}
    except Exception as e:
        return {"ok": False, "detail": str(e)[:300]}


def add_to_ignore_list(model_id, provider_cfg, provider_name):
    """Add a model ID to ignore.json if not already present. Returns True if newly added."""
    path = os.path.join(SCRIPTS_DIR, provider_cfg.get("ignore_file", ""))
    data = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    ignored = set(data.get(provider_name, []))
    if model_id not in ignored:
        ignored.add(model_id)
        data[provider_name] = sorted(ignored)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    return False


def load_ignore_list(provider_cfg, provider_name):
    path = os.path.join(SCRIPTS_DIR, provider_cfg.get("ignore_file", ""))
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return set(data.get(provider_name, []))


def load_good_data(provider_cfg, provider_name):
    path = os.path.join(SCRIPTS_DIR, provider_cfg.get("good_file", ""))
    if not os.path.exists(path):
        return {"provider": provider_name, "models": {}, "complete_ids": []}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_good_data(good_data, provider_cfg):
    path = os.path.join(SCRIPTS_DIR, provider_cfg.get("good_file", ""))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(good_data, f, indent=2, ensure_ascii=False)


def is_model_complete(good_data, model_id):
    entry = good_data.get("models", {}).get(model_id)
    if not entry:
        return False
    p1 = entry.get("phase1") or {}
    p1_status = p1.get("status")
    if not p1_status:
        return False
    if p1_status == "OK":
        p2 = entry.get("phase2")
        if not p2:
            return False
        if p2.get("stream") is None or p2.get("tool") is None:
            return False
        return True
    return True
