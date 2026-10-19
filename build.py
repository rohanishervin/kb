#!/usr/bin/env python3
"""One-shot KB build pipeline (called by dev.sh on start and on every change).

    1. extract   notes + individual problems from nodes/*.ipynb
    2. render    graph_output.html + coverage_output.html with the tags we already have (fast)
    3. tag       only NEW notes/problems via the local LLM  -> meta/tags.json
    4. insights  cross-topic connections per note -> meta/insights.json
    5. re-render if anything changed

Usage:
    python build.py            # full pipeline
    python build.py --no-tag   # skip the LLM step (also: KB_NO_LLM=1)
"""
import argparse
import os
import runpy
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from pipeline import config, extract, insights, mastery, study_page, tagger  # noqa: E402


def log(msg):
    print(f"[build] {msg}", flush=True)


def render(cfg):
    t0 = time.time()
    runpy.run_path(os.path.join(ROOT, "create_graph.py"), run_name="__main__")
    notes, problems = extract.load()
    tags = tagger.load_tags()
    res = mastery.compute(notes, problems, tags, cfg)
    ins = insights.load()
    study_page.write(study_page.build_data(res, tags, notes, problems, cfg, ins))
    top = [res["notes"][i]["title"] for i in res["queue"][:3]]
    log(f"rendered graph + study page in {time.time() - t0:.1f}s · next up: {'; '.join(top)}")
    return notes, problems


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-tag", action="store_true", help="skip LLM tagging")
    ap.add_argument("--retag", nargs="*", default=None, help="force re-tag these note/pset ids")
    ap.add_argument("--settle", action="store_true",
                    help="hold back notebooks edited < settle_minutes ago (used by dev.py)")
    args = ap.parse_args(argv)
    cfg = config.load()

    notes, problems = render(cfg)
    if args.no_tag:
        return 0
    n, recheck = tagger.run(notes, problems, cfg, log=log, only=args.retag, settle=args.settle)
    if n:
        log(f"tagged {n} item(s); re-rendering")
        notes, problems = render(cfg)
    # connections run after tagging so domains are known
    m, recheck2 = insights.run(notes, mastery.domains(notes, tagger.load_tags()), cfg, log=log, settle=args.settle)
    if m:
        log(f"wrote insights for {m} note(s); re-rendering")
        render(cfg)
    recheck = min([r for r in (recheck, recheck2) if r] or [0]) or None
    if recheck:
        print(f"RECHECK_IN={recheck}", flush=True)  # dev.py schedules another run for held-back edits
    return 0


if __name__ == "__main__":
    sys.exit(main())
