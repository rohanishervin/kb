"""Incremental LLM tagging of notes and problems.

Cache: meta/tags.json. An item is sent to the LLM only when
  * it has never been tagged, or
  * its content changed since it was tagged and retag_on_change is on, or
  * (notes) it grew a lot since tagging and retag_on_growth is on, or
  * you delete its entry, or run `kb.py tag --retag <id>`.
In the automatic pipeline an item is only (re)tagged once its notebook has been untouched
for settle_minutes, so Jupyter autosaves while you are still writing don't trigger LLM calls.
Entries with "locked": true are never touched (use this for manual corrections).
"""
import json
import os
import statistics
import time
from collections import Counter
from datetime import datetime

from .config import excluded
from .llm import LLMUnavailable, from_cfg
from .taxonomy import FINE_TAXONOMY

TAGS_PATH = os.path.join("meta", "tags.json")

NOTE_KINDS = ["definition", "theorem", "technique", "model", "application", "survey"]
PROBLEM_TYPES = ["computation", "proof", "counterexample", "construction", "modeling", "conceptual"]

NOTE_RUBRIC = """Rate the note's LEVEL (1-5) = how advanced the material is for a self-learner:
1 = vocabulary / basic definition (e.g. "outcome", "event", "interval", "absolute value")
2 = elementary result or tool with short proofs (e.g. binomial coefficient, triangle inequality, conditional probability)
3 = core undergraduate theorem/concept with a real proof or derivation (e.g. Bolzano-Weierstrass, Cauchy sequences, normal distribution, eigenvalues & diagonalization)
4 = advanced undergraduate / early graduate (e.g. Arzela-Ascoli, Fatou & convergence theorems, Picard's theorem, GARCH, KKT conditions)
5 = graduate / research level (e.g. construction of Brownian motion, results from recent research papers)
KIND: definition | theorem | technique | model | application | survey (overview of several ideas)."""

PROBLEM_RUBRIC = """Rate the problem's DIFFICULTY (1-5) judging from the statement AND the length/ideas of the solution:
1 = recall / plug into a definition or formula
2 = routine: one standard technique, few steps
3 = standard proof or derivation combining 2-3 results or a well-known trick
4 = hard: non-obvious construction, counterexample or multi-stage argument
5 = challenge: starred textbook exercise / qualifying-exam level
TYPE: computation | proof | counterexample | construction | modeling | conceptual
TESTS: the note ids (from the provided list ONLY) whose concepts the problem actually exercises, most important first, max 6.
EST_MINUTES: realistic time for a student solving it from scratch."""


def load_tags(path=TAGS_PATH):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    else:
        data = {}
    data.setdefault("version", 1)
    data.setdefault("notes", {})
    data.setdefault("problems", {})
    return data


def save_tags(tags, path=TAGS_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(tags, fh, indent=1, sort_keys=True, ensure_ascii=False)
    os.replace(tmp, path)


def _needs_note(n, entry, cfg):
    tc = cfg["tagging"]
    if n.is_pset or n.chars < tc["min_chars"] or excluded(n.id, cfg):
        return False
    if entry is None:
        return True
    if entry.get("locked"):
        return False
    if tc["retag_on_change"] and entry.get("hash") != n.hash:
        return True
    if tc["retag_on_growth"]:
        return n.chars >= entry.get("chars", 0) * tc["growth_ratio"]
    return False


def _needs_problem(p, entry, cfg):
    if len(p.text) < 120:  # skip empty "## Problem 7:" stubs still being written
        return False
    if entry is None:
        return True
    if entry.get("locked"):
        return False
    return bool(cfg["tagging"]["retag_on_change"] and entry.get("hash") != p.hash)


def pending(notes, problems, tags, cfg, settle=False):
    """Items that need (re)tagging. With settle=True, items whose notebook changed less than
    settle_minutes ago are held back; returns (notes, problems, seconds_until_next_ready or None)."""
    pn = [n for nid, n in notes.items() if _needs_note(n, tags["notes"].get(nid), cfg)]
    pp = [p for pid, p in problems.items() if _needs_problem(p, tags["problems"].get(pid), cfg)]
    if not settle:
        return pn, pp, None
    wait = cfg["tagging"]["settle_minutes"] * 60
    now = time.time()
    left = [wait - (now - it.mtime) for it in pn + pp if now - it.mtime < wait]
    pn = [n for n in pn if now - n.mtime >= wait]
    pp = [p for p in pp if now - p.mtime >= wait]
    return pn, pp, (max(1, int(min(left))) + 5 if left else None)


def _domains(tags):
    doms = list(FINE_TAXONOMY.keys())
    for e in tags["notes"].values():
        d = e.get("domain")
        if d and d not in doms:
            doms.append(d)
    return doms


def _clip(text, n):
    return text if len(text) <= n else text[:n] + "\n\n[... truncated ...]"


def _median_int(vals, lo, hi, default):
    vals = [int(round(float(v))) for v in vals if isinstance(v, (int, float, str)) and str(v).strip() not in ("",)]
    if not vals:
        return default, 0
    m = int(round(statistics.median(vals)))
    return max(lo, min(hi, m)), (max(vals) - min(vals))


def _mode(vals, allowed, default):
    vals = [v for v in vals if v in allowed] if allowed else [v for v in vals if v]
    return Counter(vals).most_common(1)[0][0] if vals else default


def tag_note(llm, n, tags, cfg):
    doms = _domains(tags)
    schema = {"type": "object", "additionalProperties": False,
              "required": ["domain", "level", "kind", "summary"],
              "properties": {"domain": {"type": "string"},
                             "level": {"type": "integer", "minimum": 1, "maximum": 5},
                             "kind": {"type": "string", "enum": NOTE_KINDS},
                             "summary": {"type": "string"}}}
    system = ("You classify lecture notes in a personal mathematics / statistics / ML knowledge base. "
              "Be calibrated and consistent.\n" + NOTE_RUBRIC +
              "\nDOMAIN: pick exactly one from this list; only if none fits at all, invent a short new domain name "
              "in the same style:\n- " + "\n- ".join(doms) +
              "\nSUMMARY: one sentence (max 25 words) saying what the note covers.")
    user = f"Note id: {n.id}\nTitle: {n.title}\n\n---\n{_clip(n.text, cfg['llm']['max_chars'])}"
    outs = [llm.json(system, user, schema, "note_tags") for _ in range(max(1, cfg["llm"]["samples"]))]
    level, spread = _median_int([o.get("level") for o in outs], 1, 5, 3)
    return {"domain": _mode([o.get("domain", "").strip() for o in outs], None, "General Mathematics"),
            "level": level, "kind": _mode([o.get("kind") for o in outs], NOTE_KINDS, "theorem"),
            "summary": outs[0].get("summary", "").strip(), "needs_review": spread >= 2}


def tag_problem(llm, p, notes, tags, cfg):
    catalog = "\n".join(f"{nid}: {n.title}" for nid, n in sorted(notes.items())
                        if not n.is_pset and not excluded(nid, cfg))
    ids = {nid for nid, n in notes.items() if not n.is_pset and not excluded(nid, cfg)}
    schema = {"type": "object", "additionalProperties": False,
              "required": ["difficulty", "type", "tests", "est_minutes"],
              "properties": {"difficulty": {"type": "integer", "minimum": 1, "maximum": 5},
                             "type": {"type": "string", "enum": PROBLEM_TYPES},
                             "tests": {"type": "array", "items": {"type": "string"}},
                             "est_minutes": {"type": "integer", "minimum": 1, "maximum": 600}}}
    system = ("You tag practice problems in a personal mathematics / statistics / ML knowledge base. "
              "Be calibrated and consistent.\n" + PROBLEM_RUBRIC +
              "\n\nAvailable note ids (id: title):\n" + catalog)
    hint = ", ".join(p.links) if p.links else "none"
    user = (f"Problem id: {p.id}\nNotes linked inside the problem text: {hint}\n\n---\n"
            f"{_clip(p.text, cfg['llm']['max_chars'])}")
    k = max(1, cfg["llm"]["samples"])
    outs = [llm.json(system, user, schema, "problem_tags") for _ in range(k)]
    diff, spread = _median_int([o.get("difficulty") for o in outs], 1, 5, 3)
    mins, _ = _median_int([o.get("est_minutes") for o in outs], 1, 600, 20)
    votes = Counter(t.strip().removesuffix(".ipynb") for o in outs for t in (o.get("tests") or []))
    llm_tests = [t for t, c in votes.most_common() if t in ids and c * 2 >= k]
    tests = list(dict.fromkeys(p.links + llm_tests))[:8]  # explicit links are always kept
    return {"difficulty": diff, "type": _mode([o.get("type") for o in outs], PROBLEM_TYPES, "proof"),
            "tests": tests, "est_minutes": mins, "needs_review": spread >= 2}


def run(notes, problems, cfg, log=print, only=None, settle=False):
    """Tag everything pending. Returns (items tagged, seconds until held-back edits are ready or None).
    Never raises on LLM trouble."""
    tags = load_tags()
    # forget problems/notes whose notebooks were deleted, and excluded notes (cs- case studies)
    for key, live in (("notes", notes), ("problems", problems)):
        for k in [k for k in tags[key] if k not in live and not tags[key][k].get("locked")]:
            del tags[key][k]
    for k in [k for k in tags["notes"] if excluded(k, cfg)]:
        del tags["notes"][k]
    if only:
        for k in only:
            tags["notes"].pop(k, None)
            for pid in [pid for pid in tags["problems"] if pid == k or pid.startswith(k + "#")]:
                tags["problems"].pop(pid, None)
    pn, pp, recheck = pending(notes, problems, tags, cfg, settle=settle and not only)
    if recheck:
        log(f"recently edited items will be (re)tagged once untouched for "
            f"{cfg['tagging']['settle_minutes']} min")
    if not pn and not pp:
        save_tags(tags)
        return 0, recheck
    if not cfg["llm"]["enabled"]:
        log(f"LLM disabled: {len(pp)} problems / {len(pn)} notes left untagged")
        save_tags(tags)
        return 0, None
    llm = from_cfg(cfg["llm"])
    ok, msg = llm.ping()
    if not ok:
        log(f"LLM not available ({msg}); {len(pp)} problems / {len(pn)} notes stay untagged until next run")
        save_tags(tags)
        return 0, None
    retagging = {it.id for it in pn if it.id in tags["notes"]} | {it.id for it in pp if it.id in tags["problems"]}
    log(f"Tagging {len(pp)} problems and {len(pn)} notes with {cfg['llm']['model']}"
        f"{f' ({len(retagging)} edited since last tag)' if retagging else ''} ...")
    done, total = 0, len(pp) + len(pn)
    stamp = lambda: datetime.now().isoformat(timespec="seconds")
    for kind, items in (("problems", pp), ("notes", pn)):
        for it in items:
            t0 = time.time()
            try:
                if kind == "problems":
                    res = tag_problem(llm, it, notes, tags, cfg)
                else:
                    res = tag_note(llm, it, tags, cfg)
                    res["chars"] = it.chars
            except LLMUnavailable as e:
                log(f"LLM went away ({e}); stopping, will resume next run")
                save_tags(tags)
                return done, None
            except Exception as e:
                log(f"  ! {it.id}: {e.__class__.__name__}: {e} (skipped, will retry next run)")
                continue
            res.update({"hash": it.hash, "model": cfg["llm"]["model"], "tagged_at": stamp()})
            tags[kind][it.id] = res
            save_tags(tags)  # save after every item: safe to Ctrl+C
            done += 1
            desc = (f"d{res['difficulty']} {res['type']} -> {', '.join(res['tests'][:3])}" if kind == "problems"
                    else f"L{res['level']} {res['kind']} | {res['domain']}")
            again = " (re-tag)" if it.id in retagging else ""
            log(f"  [{done}/{total}] {it.id}: {desc} ({time.time() - t0:.0f}s){again}")
    return done, recheck
