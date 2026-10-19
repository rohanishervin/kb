"""Minimal LLM client for local servers. No extra dependencies (urllib only).

Two APIs:
  * api = "ollama": Ollama's native /api/chat. Supports per-request options
    such as num_ctx (context length), so no OLLAMA_CONTEXT_LENGTH / systemd edit is needed.
  * api = "openai": any OpenAI-compatible server (LM Studio, llama.cpp, vLLM, Ollama's /v1).
"""
import json
import re
import urllib.error
import urllib.request


class LLMUnavailable(Exception):
    pass


class LLM:
    def __init__(self, base_url, model, api_key="local", timeout=300, temperature=0.2,
                 api="ollama", num_ctx=None, think=None):
        self.api = api
        base_url = base_url.rstrip("/")
        if api == "ollama":
            base_url = re.sub(r"/v1$", "", base_url)  # accept either form
        self.base_url = base_url
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        self.temperature = temperature
        self.num_ctx = num_ctx
        self.think = think
        self._schema_ok = True  # openai: fall back to plain JSON mode if server rejects json_schema

    def _req(self, path, payload=None, timeout=None):
        req = urllib.request.Request(
            self.base_url + path,
            data=json.dumps(payload).encode("utf-8") if payload is not None else None,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
        )
        with urllib.request.urlopen(req, timeout=timeout or self.timeout) as r:
            return json.loads(r.read().decode("utf-8"))

    # ── health check ──
    def ping(self):
        """Return (ok, message). Checks the server is up and the model exists."""
        try:
            data = self._req("/api/tags" if self.api == "ollama" else "/models", timeout=5)
        except Exception as e:
            return False, f"cannot reach {self.base_url} ({e.__class__.__name__})"
        if self.api == "ollama":
            names = [m.get("name", "") for m in data.get("models", [])]
        else:
            names = [m.get("id", "") for m in data.get("data", [])]
        known = set(names) | {n[:-7] for n in names if n.endswith(":latest")}
        if names and self.model not in known:
            return False, f"model '{self.model}' not found on server. Available: {', '.join(names[:10])}"
        extra = f", num_ctx={self.num_ctx}" if self.api == "ollama" and self.num_ctx else ""
        return True, f"ok ({self.api} api{extra})"

    # ── structured call ──
    def json(self, system, user, schema, name="result"):
        msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        try:
            if self.api == "ollama":
                return parse_json(self._ollama(msgs, schema))
            return parse_json(self._openai(msgs, schema, name))
        except urllib.error.HTTPError:
            raise
        except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
            raise LLMUnavailable(str(e))

    def _ollama(self, msgs, schema):
        options = {"temperature": self.temperature}
        if self.num_ctx:
            options["num_ctx"] = int(self.num_ctx)
        payload = {"model": self.model, "messages": msgs, "stream": False, "format": schema, "options": options}
        if self.think is not None:
            payload["think"] = bool(self.think)
        resp = self._req("/api/chat", payload)
        if resp.get("done_reason") == "length":
            raise ValueError("output hit the length limit (raise num_ctx in study.toml)")
        return resp.get("message", {}).get("content") or ""

    def _openai(self, msgs, schema, name):
        payload = {"model": self.model, "messages": msgs, "temperature": self.temperature}
        if self._schema_ok:
            payload["response_format"] = {"type": "json_schema",
                                          "json_schema": {"name": name, "schema": schema, "strict": True}}
        try:
            resp = self._req("/chat/completions", payload)
        except urllib.error.HTTPError as e:
            if not (self._schema_ok and e.code in (400, 422, 500)):
                raise
            self._schema_ok = False
            payload["response_format"] = {"type": "json_object"}
            payload["messages"][0]["content"] += "\nReply with JSON only, matching this schema:\n" + json.dumps(schema)
            resp = self._req("/chat/completions", payload)
        return resp["choices"][0]["message"].get("content") or ""


def from_cfg(c):
    """Build an LLM from the [llm] section of study.toml."""
    return LLM(c["base_url"], c["model"], c.get("api_key", "local"), c.get("timeout", 300),
               c.get("temperature", 0.2), c.get("api", "ollama"), c.get("num_ctx"), c.get("think"))


def parse_json(content):
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.S).strip()
    content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip())
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", content, re.S)
        if m:
            return json.loads(m.group(0))
        raise
