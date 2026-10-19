# kb

Personal knowledge base: https://rohanishervin.github.io/kb/

## Workflow

```bash
./dev.sh              # Quarto preview + Jupyter + watcher. Runs the whole pipeline on start and on every change.
./dev.sh --anki       # same, and also runs create_anki.py after every build
```

Add or edit a notebook in `nodes/` and everything else is automatic:

1. **extract**: notes, plus every `## Problem N: …` inside `pset-*.ipynb` as its own item (`pset-x#N`)
2. **render**: `graph_output.html` and `coverage_output.html` (the Study Focus tab)
3. **tag**: only *new* notes/problems are sent to your local LLM, and the results are cached in `meta/tags.json`
   - notes: domain, level 1–5, kind, one-line summary
   - problems: difficulty 1–5, type, which notes it tests, estimated minutes
4. **connections**: related notes suggested by the LLM (see below), cached in `meta/insights.json`
5. **re-render** with the new tags

Notes starting with `cs-` (case studies) are left out of tagging and the Study Focus tab (`exclude_prefixes` in `study.toml`).

Editing a note or problem re-tags it (`retag_on_change`), but only once its notebook has been untouched for `settle_minutes` (default 5), so autosaves while you are still writing don't trigger LLM calls. Deleting a note or pset drops its tags. Notes under `min_chars` count as drafts and wait. If the LLM is off, the pages still build with default tags, and tagging resumes on the next run.

## Local LLM

Set it in `study.toml`. By default it uses Ollama's native API (`api = "ollama"`, `http://localhost:11434`), which lets `num_ctx` (context length) and `think` be set per request without touching the Ollama service. Any OpenAI-compatible server also works with `api = "openai"` (e.g. LM Studio `http://localhost:1234/v1`).
Override per run with `KB_LLM_URL`, `KB_LLM_MODEL`, or `KB_NO_LLM=1`. `./kb.sh status` checks the connection.

To correct a tag, edit it in `meta/tags.json` and add `"locked": true`. To force a re-tag, run `./kb.sh tag --retag <note-id or pset-id>`.

## Command line

```bash
./kb.sh next                         # study queue in the terminal
./kb.sh status                       # tagging + LLM status
./kb.sh tag --retag <id>             # force a re-tag
./kb.sh build [--no-tag]             # run the pipeline once without dev.sh
```

Every problem written in a pset counts as solved. Domain priorities go under `[goals]` in `study.toml`.

## Connections

After tagging, the local LLM suggests up to 3 related notes for every note (cached in `meta/insights.json`, incremental like the tags), preferably in other domains and not yet linked, with the reason. They appear in each note's row and under "Unexplored connections" on the Study Focus tab.

The **KB health** card lists broken links, orphan notes, stubs and titles to fix.

## How "Do next" is ranked

- Each note has a skill rating on the 1–5 difficulty scale, updated Elo-style by every problem that tests it. Its direct prerequisites get 30% credit.
- Coverage is the probability of solving a problem at the note's own level. It is low when no problem, or only easy ones, test a hard note. There is no time decay.
- `priority = importance (notes depending on it × goal weight) × gap (target − coverage) × readiness (prereqs)`
- The action is one of: practice an unattempted problem · climb to a harder problem · fix a foundation · needs (more) problems.
