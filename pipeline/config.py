"""Load study.toml with sensible defaults; env vars KB_LLM_URL / KB_LLM_MODEL override."""
import os
try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    tomllib = None

DEFAULTS = {
    "llm": {"enabled": True, "api": "ollama", "base_url": "http://localhost:11434", "model": "qwen3:14b",
            "num_ctx": 16384, "think": None,
            "api_key": "local", "samples": 1, "timeout": 300, "max_chars": 12000, "temperature": 0.2},
    "tagging": {"min_chars": 600, "retag_on_change": True, "settle_minutes": 5,
                "retag_on_growth": True, "growth_ratio": 1.6},
    "practice": {"implicit_grade": 2, "target": 0.8},
    "goals": {},
    "study": {"exclude_prefixes": ["cs-"]},
}


def excluded(nid, cfg):
    """Notes left out of tagging and the Study Focus tab (e.g. cs- case studies)."""
    return any(nid.startswith(p) for p in cfg.get("study", {}).get("exclude_prefixes", []))


def load(path="study.toml"):
    cfg = {k: dict(v) for k, v in DEFAULTS.items()}
    if os.path.exists(path):
        if tomllib is None:
            print("[config] Python < 3.11: study.toml ignored, using defaults")
            user = {}
        else:
            with open(path, "rb") as fh:
                user = tomllib.load(fh)
        for k, v in user.items():
            if isinstance(v, dict):
                cfg.setdefault(k, {}).update(v)
            else:
                cfg[k] = v
    if os.environ.get("KB_LLM_URL"):
        cfg["llm"]["base_url"] = os.environ["KB_LLM_URL"]
    if os.environ.get("KB_LLM_MODEL"):
        cfg["llm"]["model"] = os.environ["KB_LLM_MODEL"]
    if os.environ.get("KB_NO_LLM"):
        cfg["llm"]["enabled"] = False
    return cfg
