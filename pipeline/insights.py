"""Cross-topic connections per note (local LLM).

For every note (not psets, not excluded prefixes like cs-) the LLM suggests up to 3 notes,
ideally in OTHER domains and not already linked, with a genuine mathematical relationship
(generalisation, special case, shared proof technique, analogy) and one sentence on why.

Cached in meta/insights.json, incremental exactly like tags: new notes are processed,
edited notes are re-processed after the settle delay (retag_on_change), "locked": true wins.
"""
import json
import os
import time
from datetime import datetime

from .config import excluded
from .llm import LLMUnavailable, from_cfg

INSIGHTS_PATH = os.path.join("meta", "insights.json")

SYSTEM = """You help a self-learner see how the mathematical ideas in their knowledge base connect.
Given one note, list 0 to 3 other notes from the catalog that have a genuine mathematical relationship
with it (generalisation, special case, same proof technique, deep analogy, one is used to prove the
other). Strongly prefer notes from a DIFFERENT domain and notes NOT already linked.
"why" = one sentence naming the precise relationship. Return an empty list rather than a weak link."""

SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["connections"],
    "properties": {
        "connections": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["id", "why"],
            "properties": {"id": {"type": "string"}, "why": {"type": "string"}}}},
    },
}


def load(path=INSIGHTS_PATH):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def save(data, path=INSIGHTS_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, sort_keys=True, ensure_ascii=False)
    os.replace(tmp, path)


def _eligible(n, cfg):
    return not n.is_pset and not excluded(n.id, cfg) and n.chars >= cfg["tagging"]["min_chars"]


def pending(notes, data, cfg, settle=False):
    todo = []
    for nid, n in notes.items():
        if not _eligible(n, cfg):
            continue
        e = data.get(nid)
        if e is None or (not e.get("locked") and cfg["tagging"]["retag_on_change"] and e.get("hash") != n.hash):
            todo.append(n)
    if not settle:
        return todo, None
    wait, now = cfg["tagging"]["settle_minutes"] * 60, time.time()
    left = [wait - (now - n.mtime) for n in todo if now - n.mtime < wait]
    return [n for n in todo if now - n.mtime >= wait], (max(1, int(min(left))) + 5 if left else None)


def _one(llm, n, notes, domains, cfg):
    catalog = "\n".join(f"{nid}: {m.title} [{domains.get(nid, '?')}]" for nid, m in sorted(notes.items())
                        if _eligible(m, cfg) and nid != n.id)
    linked = sorted(set(n.links) | {nid for nid, m in notes.items() if n.id in m.links})
    user = (f"Note id: {n.id}\nTitle: {n.title}\nDomain: {domains.get(n.id, '?')}\n"
            f"Already linked: {', '.join(linked) or 'none'}\n\nCatalog (id: title [domain]):\n{catalog}\n\n---\n"
            + (n.text if len(n.text) <= cfg["llm"]["max_chars"] else n.text[:cfg["llm"]["max_chars"]] + "\n[...]"))
    out = llm.json(SYSTEM, user, SCHEMA, "note_connections")
    cons, seen = [], set()
    for c in out.get("connections", []):
        cid = str(c.get("id", "")).strip().removesuffix(".ipynb")
        if cid in notes and cid != n.id and cid not in seen and _eligible(notes[cid], cfg) and c.get("why"):
            seen.add(cid)
            cons.append({"id": cid, "why": c["why"].strip(), "new": cid not in linked})
    return {"connections": cons[:3]}


def run(notes, domains, cfg, log=print, settle=False):
    """Process pending notes. Returns (count, seconds until held-back edits are ready or None)."""
    data = load()
    for k in [k for k in data if (k not in notes or excluded(k, cfg)) and not data[k].get("locked")]:
        del data[k]
    for e in data.values():
        e.pop("questions", None)  # older runs also generated questions; no longer used
    todo, recheck = pending(notes, data, cfg, settle)
    if not todo or not cfg["llm"]["enabled"]:
        save(data)
        return 0, recheck
    llm = from_cfg(cfg["llm"])
    ok, msg = llm.ping()
    if not ok:
        save(data)
        return 0, None
    log(f"Finding connections for {len(todo)} notes ...")
    done = 0
    for n in todo:
        t0 = time.time()
        try:
            res = _one(llm, n, notes, domains, cfg)
        except LLMUnavailable as e:
            log(f"LLM went away ({e}); will resume next run")
            break
        except Exception as e:
            log(f"  ! {n.id}: {e.__class__.__name__}: {e} (will retry next run)")
            continue
        res.update(hash=n.hash, model=cfg["llm"]["model"], at=datetime.now().isoformat(timespec="seconds"))
        data[n.id] = res
        save(data)
        done += 1
        log(f"  [connections {done}/{len(todo)}] {n.id}: "
            f"{sum(c['new'] for c in res['connections'])} new ({time.time() - t0:.0f}s)")
    return done, recheck
