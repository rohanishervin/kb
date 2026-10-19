"""Problems + practice log -> per-note COVERAGE -> prioritised study queue.

Coverage answers "how well do the problems I've solved cover this note?". There is no
time/forgetting component: spaced review happens outside this tool.

Model (deliberately simple and explainable):
  * Each note has a skill rating s on the same 1-5 scale as difficulty/level.
  * P(solve problem of difficulty d) = sigmoid(1.2 * (s - d)).
  * Each attempt moves s toward the observed result (Elo-style). The notes a problem
    tests get full credit, their direct prerequisites 30%.
  * coverage = P(solving a problem at the note's own level): low when no / only easy
    problems test a hard note, high once you've solved problems at or above its level.
  * priority = importance (dependents x goal weight) x gap (target - coverage) x readiness (prereqs).
"""
import json
import math
import os
from collections import Counter, defaultdict, deque
from datetime import date

from .config import excluded
from .taxonomy import FINE_TAXONOMY

LOG_PATH = os.path.join("practice", "log.jsonl")
GRADE_LABEL = {0: "couldn't solve", 1: "read solution", 2: "solved with hints", 3: "solved cleanly"}
S0, K, SLOPE = 1.5, 1.5, 1.2


def sigmoid(x):
    return 1 / (1 + math.exp(-x))


def read_log(path=LOG_PATH):
    out = []
    if not os.path.exists(path):
        return out
    with open(path, "r", encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                e = json.loads(line)
                e["grade"] = max(0, min(3, int(e["grade"])))
                date.fromisoformat(e["date"])
                out.append(e)
            except Exception as ex:
                print(f"[mastery] ignoring bad log line {i}: {ex}")
    return out


def append_log(entry, path=LOG_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def domains(notes, tags):
    """note id -> domain. Curated taxonomy > LLM tag > neighbour vote > 'Unsorted'."""
    curated = {fn[:-6]: d for d, fl in FINE_TAXONOMY.items() for fn in fl}
    dom = {}
    for nid, n in notes.items():
        if nid in curated:
            dom[nid] = curated[nid]
        elif tags["notes"].get(nid, {}).get("domain"):
            dom[nid] = tags["notes"][nid]["domain"]
    incoming = defaultdict(list)
    for nid, n in notes.items():
        for t in n.links:
            incoming[t].append(nid)
    for _ in range(2):
        for nid, n in notes.items():
            if nid in dom or n.is_pset:
                continue
            votes = [dom[x] for x in n.links + incoming[nid] if x in dom and not notes[x].is_pset]
            if votes:
                dom[nid] = Counter(votes).most_common(1)[0][0]
    for nid, n in notes.items():
        if n.is_pset:
            ds = [dom[t] for t in n.links if t in dom]
            dom[nid] = Counter(ds).most_common(1)[0][0] if ds else "Problem Sets"
        dom.setdefault(nid, "Unsorted")
    return dom


def compute(notes, problems, tags, cfg, today=None):
    today = today or date.today()
    pc = cfg["practice"]
    regular = {k: v for k, v in notes.items() if not v.is_pset and not excluded(k, cfg)}
    dom = domains(notes, tags)

    # ── problem facts (tags with graceful defaults) ──
    P = {}
    for pid, p in problems.items():
        t = tags["problems"].get(pid)
        tests = [x for x in (t["tests"] if t else p.links) if x in regular] or \
                [x for x in notes[p.pset].links if x in regular][:3]
        P[pid] = {"id": pid, "pset": p.pset, "number": p.number, "title": p.title,
                  "difficulty": t["difficulty"] if t else 3, "type": t["type"] if t else None,
                  "est_minutes": t.get("est_minutes") if t else None, "tests": tests,
                  "tagged": bool(t), "date": p.date, "attempts": []}
        P[pid]["domain"] = Counter(dom[x] for x in tests).most_common(1)[0][0] if tests else dom[p.pset]

    # ── attempts: explicit log + one implicit attempt for each written-up problem ──
    log = [e for e in read_log() if e["p"] in P]
    explicit_first = {}
    for e in log:
        explicit_first[e["p"]] = min(explicit_first.get(e["p"], e["date"]), e["date"])
    attempts = [dict(e, implicit=False) for e in log]
    for pid, p in P.items():
        if pc["implicit_grade"] is not None and not (pid in explicit_first and explicit_first[pid] <= p["date"]):
            attempts.append({"p": pid, "date": p["date"], "grade": int(pc["implicit_grade"]), "implicit": True})
    attempts.sort(key=lambda e: (e["date"], e["implicit"] is False))

    # ── replay attempts ──
    st = {nid: {"s": S0, "n": 0} for nid in regular}
    surprises = []
    for a in attempts:
        p = P[a["p"]]
        score = a["grade"] / 3
        p["attempts"].append({"date": a["date"], "grade": a["grade"], "implicit": a["implicit"]})
        direct = p["tests"]
        prereq = {q for t in direct for q in regular[t].links if q in regular and q not in direct}
        preds = []
        for nid, w in [(x, 1.0) for x in direct] + [(x, 0.3) for x in prereq]:
            s = st[nid]
            pred = sigmoid(SLOPE * (s["s"] - p["difficulty"]))
            if w == 1.0:
                preds.append(pred)
            s["s"] = max(0.0, min(6.0, s["s"] + K * w * (score - pred)))
            if w == 1.0:
                s["n"] += 1
        if preds and not a["implicit"] and abs(score - sum(preds) / len(preds)) >= 0.55:
            surprises.append({"p": p["id"], "title": p["title"], "date": a["date"], "grade": a["grade"],
                              "difficulty": p["difficulty"], "expected": round(sum(preds) / len(preds), 2)})

    # ── graph: prerequisites and transitive dependents ──
    rev = defaultdict(set)
    for nid, n in regular.items():
        for t in n.links:
            if t in regular:
                rev[t].add(nid)

    def dependents(nid):
        seen, q = set(), deque([nid])
        while q:
            for x in rev[q.popleft()]:
                if x not in seen and x != nid:
                    seen.add(x)
                    q.append(x)
        return len(seen)

    depth_memo = {}

    def depth(nid, stack=()):
        if nid in depth_memo:
            return depth_memo[nid]
        pre = [q for q in regular[nid].links if q in regular and q not in stack]
        d = 1 + max((depth(q, stack + (nid,)) for q in pre), default=0)
        depth_memo[nid] = d
        return d

    tests_of = defaultdict(list)
    for pid, p in P.items():
        for t in p["tests"]:
            tests_of[t].append(pid)

    # ── per-note results ──
    goals = cfg.get("goals", {})
    target = pc["target"]
    rows = {}
    for nid, n in regular.items():
        t = tags["notes"].get(nid, {})
        level = t.get("level", 3)
        s = st[nid]
        coverage = sigmoid(SLOPE * (s["s"] - level))
        rows[nid] = {"id": nid, "title": n.title, "domain": dom[nid], "level": level, "level_tagged": "level" in t,
                     "kind": t.get("kind"), "summary": t.get("summary", ""), "chars": n.chars,
                     "completeness": "stub" if n.chars < 1500 else ("partial" if n.chars < 5000 else "full"),
                     "skill": round(s["s"], 2), "current": round(coverage, 3), "attempts": s["n"],
                     "problems": sorted(tests_of[nid]), "prereqs": [q for q in n.links if q in regular],
                     "dependents": dependents(nid), "depth": depth(nid), "date": n.date,
                     "needs_review": t.get("needs_review", False)}

    for r in rows.values():
        pre = [rows[q]["current"] for q in r["prereqs"]]
        readiness = 0.5 + 0.5 * min(1.0, (sum(pre) / len(pre)) / target) if pre else 1.0
        importance = (1 + math.log2(1 + r["dependents"])) * float(goals.get(r["domain"], 1.0))
        gap = max(0.0, target - r["current"])
        # a note with no problems can't be practised yet: still listed, but writing problems for a
        # basic definition matters less than for a real theorem
        write_f = 1.0 if r["problems"] else 0.6 * min(1.0, r["level"] / 3) * (0.5 if r["kind"] == "definition" else 1.0)
        prio = importance * gap * readiness * write_f
        r.update(importance=round(importance, 2), readiness=round(readiness, 2), priority=round(prio, 3))
        r.update(_action(r, P))

    queue = _queue(rows)
    return {"notes": rows, "problems": P, "surprises": surprises[-15:], "queue": queue,
            "attempts_explicit": len(log), "today": today.isoformat()}


def _action(r, P):
    probs = [P[x] for x in r["problems"]]
    if not probs:
        return {"action": "write", "suggest": None,
                "reason": f"No problem tests this yet; {r['dependents']} notes build on it." if r["dependents"]
                else "No problem tests this yet."}
    fresh = [p for p in probs if not p["attempts"]]
    solved_max = max((p["difficulty"] for p in probs if any(a["grade"] >= 2 for a in p["attempts"])), default=0)
    harder = [p for p in probs if p["difficulty"] > solved_max]
    if r["current"] >= 0.55 and harder:
        pick = min(harder, key=lambda p: (len(p["attempts"]) > 0, p["difficulty"]))
        act, why = "climb", f"Covered up to difficulty {solved_max}; a harder problem would cover level {r['level']} properly."
    elif fresh:
        want = min(5, max(1, round(r["skill"] + 0.5)))
        pick = min(fresh, key=lambda p: abs(p["difficulty"] - want))
        act = "practice"
        why = f"Coverage {r['current']:.0%}; {len(fresh)} of {len(probs)} problem(s) testing it not attempted yet."
    else:
        pick = None
        act = "write"
        why = (f"Coverage {r['current']:.0%}: all {len(probs)} problem(s) testing it are done; "
               f"add another one at difficulty {r['level']} or above.")
    if r["dependents"] >= 15 and r["current"] < 0.3:
        act, why = "foundation", f"{r['dependents']} notes depend on this and coverage is {r['current']:.0%}. " + why
    return {"action": act, "suggest": pick["id"] if pick else None, "reason": why}


def _queue(rows, n=10, per_domain=3):
    out, per = [], Counter()
    for r in sorted(rows.values(), key=lambda r: -r["priority"]):
        if r["priority"] <= 0:
            break
        if per[r["domain"]] >= per_domain:
            continue
        per[r["domain"]] += 1
        out.append(r["id"])
        if len(out) >= n:
            break
    return out
