#!/usr/bin/env python3
"""KB command line.

    ./kb.sh log pset-topology-01#3 3 [--min 25] [--date 2026-10-18] [--note "forgot the trick"]
    ./kb.sh log                      # interactive: pick from today's queue
    ./kb.sh next                     # print the study queue
    ./kb.sh status                   # tagging / LLM status
    ./kb.sh tag [--retag ID ...]     # run only the tagging step
    ./kb.sh build [--no-tag]         # full pipeline (dev.sh does this automatically)
"""
import argparse
import os
import sys
from datetime import date

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from pipeline import config, extract, mastery, tagger  # noqa: E402
from pipeline.llm import from_cfg  # noqa: E402


def _state():
    cfg = config.load()
    notes, problems = extract.load()
    tags = tagger.load_tags()
    return cfg, notes, problems, tags


def cmd_log(a):
    cfg, notes, problems, tags = _state()
    pid, grade = a.problem, a.grade
    if pid is None:
        res = mastery.compute(notes, problems, tags, cfg)
        sug = [res["notes"][n]["suggest"] for n in res["queue"] if res["notes"][n]["suggest"]]
        sug = list(dict.fromkeys(sug))
        for i, s in enumerate(sug, 1):
            print(f"  {i}. {s:32s} {problems[s].title[:60]}")
        raw = input("Problem (number above or id like pset-x#3): ").strip()
        pid = sug[int(raw) - 1] if raw.isdigit() and 0 < int(raw) <= len(sug) else raw
    if pid not in problems:
        close = [p for p in problems if pid.split("#")[0] in p][:10]
        sys.exit(f"Unknown problem '{pid}'." + (f" Did you mean: {', '.join(close)}" if close else ""))
    if grade is None:
        grade = int(input("Grade 0 couldn't / 1 read solution / 2 with hints / 3 clean: ").strip())
    if grade not in (0, 1, 2, 3):
        sys.exit("grade must be 0, 1, 2 or 3")
    e = {"p": pid, "date": a.date or date.today().isoformat(), "grade": grade}
    if a.min:
        e["min"] = a.min
    if a.note:
        e["note"] = a.note
    mastery.append_log(e)
    print(f"logged {pid} · {mastery.GRADE_LABEL[grade]} · {e['date']}")
    if not a.no_build:
        import build
        build.main(["--no-tag"])


def cmd_next(a):
    cfg, notes, problems, tags = _state()
    res = mastery.compute(notes, problems, tags, cfg)
    for i, nid in enumerate(res["queue"], 1):
        r = res["notes"][nid]
        print(f"{i:2d}. [{r['action']:10s}] {r['title']}  ({r['domain']}, L{r['level']}, {r['current']:.0%})")
        print(f"    {r['reason']}")
        if r["suggest"]:
            p = res["problems"][r["suggest"]]
            print(f"    -> {p['id']}  d{p['difficulty']}  {p['title'][:70]}")


def cmd_status(a):
    cfg, notes, problems, tags = _state()
    pn, pp, _ = tagger.pending(notes, problems, tags, cfg)
    reg = [n for n in notes.values() if not n.is_pset and not config.excluded(n.id, cfg)]
    print(f"notes:    {sum(1 for n in reg if n.id in tags['notes'])}/{len(reg)} tagged, {len(pn)} pending")
    print(f"problems: {len(tags['problems'])}/{len(problems)} tagged, {len(pp)} pending")
    print(f"log:      {len(mastery.read_log())} explicit attempts in {mastery.LOG_PATH}")
    if cfg["llm"]["enabled"]:
        ok, msg = from_cfg(cfg["llm"]).ping()
        print(f"llm:      {cfg['llm']['model']} @ {cfg['llm']['base_url']} -> {msg if ok else 'NOT OK: ' + msg}")
    else:
        print("llm:      disabled")


def cmd_tag(a):
    cfg, notes, problems, tags = _state()
    tagger.run(notes, problems, cfg, only=a.retag)


def cmd_build(a):
    import build
    build.main(["--no-tag"] if a.no_tag else [])


def main():
    ap = argparse.ArgumentParser(description="KB study tools")
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("log", help="log a practice attempt")
    p.add_argument("problem", nargs="?")
    p.add_argument("grade", nargs="?", type=int)
    p.add_argument("--date")
    p.add_argument("--min", type=int)
    p.add_argument("--note")
    p.add_argument("--no-build", action="store_true")
    p.set_defaults(fn=cmd_log)
    sp.add_parser("next", help="show the study queue").set_defaults(fn=cmd_next)
    sp.add_parser("status", help="tagging and LLM status").set_defaults(fn=cmd_status)
    p = sp.add_parser("tag", help="run only the tagging step")
    p.add_argument("--retag", nargs="*")
    p.set_defaults(fn=cmd_tag)
    p = sp.add_parser("build", help="full pipeline")
    p.add_argument("--no-tag", action="store_true")
    p.set_defaults(fn=cmd_build)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
