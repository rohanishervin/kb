"""Render coverage_output.html (the Study Focus tab) from coverage results."""
import json
from collections import defaultdict


def build_data(res, tags, notes, problems, cfg, ins=None):
    ins = ins or {}
    rows = res["notes"]
    P = res["problems"]
    regular = [r for r in rows.values()]
    for nid, r in rows.items():
        e = ins.get(nid, {})
        r["connections"] = [c for c in e.get("connections", []) if c["id"] in rows]
    doms = defaultdict(lambda: {"levels": defaultdict(list), "ladder": defaultdict(lambda: [0, 0, 0])})
    for r in regular:
        doms[r["domain"]]["levels"][r["level"]].append(r["current"])
    for p in P.values():
        lad = doms[p["domain"]]["ladder"][p["difficulty"]]
        lad[0] += 1
        if p["attempts"]:
            lad[1] += 1
            if max(a["grade"] for a in p["attempts"]) >= 2:
                lad[2] += 1
    domain_rows = []
    for d, v in doms.items():
        cur = [c for l in v["levels"].values() for c in l]
        domain_rows.append({
            "domain": d, "n": len(cur), "avg": round(sum(cur) / len(cur), 3) if cur else 0,
            "lvl": _avg([r["level"] for r in regular if r["domain"] == d]),
            "diff": _avg([p["difficulty"] for p in P.values() if p["domain"] == d]),
            "levels": {str(k): {"n": len(l), "avg": round(sum(l) / len(l), 3)} for k, l in v["levels"].items()},
            "ladder": {str(k): l for k, l in v["ladder"].items()},
            "prio": round(sum(rows[x]["priority"] for x in rows if rows[x]["domain"] == d), 2)})
    domain_rows.sort(key=lambda d: -d["prio"])
    blind = sorted((r for r in regular if not r["problems"]), key=lambda r: -r["importance"] * (1 + r["level"] / 5))
    from .tagger import pending
    pn, pp, _ = pending(notes, problems, tags, cfg)
    return {
        "today": res["today"], "target": cfg["practice"]["target"], "model": cfg["llm"]["model"],
        "kpi": {
            "notes": len(regular), "problems": len(P),
            "avg": round(sum(r["current"] for r in regular) / max(1, len(regular)), 3),
            "at_target": sum(1 for r in regular if r["current"] >= cfg["practice"]["target"]),
            "covered": sum(1 for r in regular if r["problems"]),
            "no_problems": sum(1 for r in regular if not r["problems"]),
            "pending_notes": len(pn), "pending_problems": len(pp),
            "logged": res["attempts_explicit"],
        },
        "queue": res["queue"], "notes": rows, "health": _health(notes, rows),
        "connections": _connections(ins, rows), "n_insights": sum(1 for k in ins if k in rows),
        "problems": {k: {kk: v[kk] for kk in ("id", "pset", "number", "title", "difficulty", "type",
                                               "est_minutes", "tests", "attempts", "tagged", "domain")}
                     for k, v in P.items()},
        "domains": domain_rows, "blind": [r["id"] for r in blind[:15]], "surprises": res["surprises"],
        "review": [k for k, v in tags["notes"].items() if v.get("needs_review")] +
                  [k for k, v in tags["problems"].items() if v.get("needs_review")],
    }


def _avg(xs):
    return round(sum(xs) / len(xs), 1) if xs else None


def _health(notes, rows):
    """Maintenance list for a long-lived KB (deterministic, no LLM)."""
    import re
    from .config import excluded
    cfg_ex = {"study": {"exclude_prefixes": ["index-", "cs-"]}}
    linked_to = {t for n in notes.values() if not excluded(n.id, cfg_ex) for t in n.links}
    return {
        "broken": [[n.id, b] for n in notes.values() for b in n.broken][:60],
        "orphans": sorted(nid for nid, r in rows.items() if not notes[nid].links and nid not in linked_to),
        "stubs": sorted(nid for nid, r in rows.items() if r["completeness"] == "stub"),
        "titles": sorted(nid for nid, r in rows.items()
                         if re.search(r"not sure|todo|tbd|\?\s*\)?$", r["title"], re.I)),
    }


def _connections(ins, rows):
    """New (not yet linked) connections suggested by the LLM, cross-domain first."""
    out, seen = [], set()
    for nid, e in ins.items():
        if nid not in rows:
            continue
        for c in e.get("connections", []):
            key = tuple(sorted((nid, c["id"])))
            if c.get("new") and c["id"] in rows and key not in seen:
                seen.add(key)
                out.append({"a": nid, "b": c["id"], "why": c["why"],
                            "cross": rows[nid]["domain"] != rows[c["id"]]["domain"]})
    out.sort(key=lambda x: (not x["cross"], -(rows[x["a"]]["dependents"] + rows[x["b"]]["dependents"])))
    return out[:40]


def write(data, path="coverage_output.html"):
    html = TEMPLATE.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Study Focus</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"></script>
<style>
:root{
  --bg:#f7f7f5; --card:#ffffff; --ink:#1d1d1f; --muted:#6b6b70; --line:#e6e4df;
  --accent:#2f5d8a; --accent-soft:#e8eff7;
  --m0:#f3e3df; --m1:#f1d9b8; --m2:#e8e2b0; --m3:#cfe2bd; --m4:#a9d3a4;
  --practice:#2f5d8a; --practice-bg:#e8eff7;
  --climb:#2e6b3f; --climb-bg:#e3f1e6; --foundation:#9b2c2c; --foundation-bg:#fbe5e5;
  --write:#5b4b8a; --write-bg:#eeeaf7;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--ink);font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;padding:20px 16px 48px}
.wrap{max-width:1180px;margin:0 auto}
h1{font-family:Georgia,"CMU Serif","Times New Roman",serif;font-weight:500;font-size:28px;letter-spacing:-.01em}
h2{font-size:15px;font-weight:650;margin-bottom:2px}
.sub{color:var(--muted);font-size:13px}
a{color:var(--accent);text-decoration:none} a:hover{text-decoration:underline}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:18px 0 22px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.kpi .v{font-size:24px;font-weight:600;font-variant-numeric:tabular-nums}
.kpi .l{color:var(--muted);font-size:12px}
.grid{display:grid;grid-template-columns:minmax(0,1.35fr) minmax(0,1fr);gap:16px}
@media (max-width:900px){.grid{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 16px 12px;margin-bottom:16px;min-width:0}
.card-h{display:flex;justify-content:space-between;align-items:baseline;gap:8px;margin-bottom:10px;flex-wrap:wrap}
.q{border-top:1px solid var(--line);padding:11px 0;display:grid;grid-template-columns:22px 1fr;gap:8px}
.q:first-of-type{border-top:none}
.q .n{color:var(--muted);font-variant-numeric:tabular-nums;padding-top:1px}
.q .t{font-weight:600}
.q .meta{color:var(--muted);font-size:12.5px}
.q .why{font-size:13px;margin-top:3px}
.q .do{margin-top:6px;display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-size:13px}
.badge{display:inline-block;font-size:11px;font-weight:600;letter-spacing:.02em;text-transform:uppercase;border-radius:5px;padding:1px 7px;margin-right:6px;vertical-align:1px}
.b-practice{color:var(--practice);background:var(--practice-bg)}
.b-climb{color:var(--climb);background:var(--climb-bg)} .b-foundation{color:var(--foundation);background:var(--foundation-bg)}
.b-write{color:var(--write);background:var(--write-bg)}
.chip{display:inline-block;border:1px solid var(--line);border-radius:5px;padding:0 6px;font-size:12px;color:var(--muted);background:#fbfbfa}
.lv{display:inline-block;border-radius:5px;padding:0 6px;font-size:12px;font-weight:600;white-space:nowrap}
.lv1{background:#eef3f8;color:#3c5a78}.lv2{background:#dde8f3;color:#2f5d8a}.lv3{background:#c9daec;color:#244c74}
.lv4{background:#e9dcf0;color:#5b3a7a}.lv5{background:#f3d9dc;color:#8a2c3a}
.drow td{background:#fbfaf7;padding:10px 12px 14px}
.detail .ptbl{margin-top:8px;font-size:12.5px}
.detail .ptbl th{font-size:10.5px}
tr.nrow{cursor:pointer} tr.nrow:hover td{background:#fbfaf7}
.chev{color:var(--muted);width:14px;display:inline-block;transition:transform .15s}
tr.open .chev{transform:rotate(90deg)}
details.probs{margin-top:6px} details.probs summary{font-size:12.5px}
.qa{border-top:1px solid #efede8;padding:6px 0}.qa summary{font-size:13px;cursor:pointer}.qa .ans{font-size:13px;margin:4px 0 2px 14px;color:#333}
.sect{font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);margin:12px 0 2px;font-weight:600}
.con{font-size:13px;padding:3px 0}.con .why{color:#444}
.gap{font-size:11.5px;white-space:nowrap}.gap.bad{color:#9b2c2c;font-weight:600}
.health li{display:block}.health .cnt{font-weight:600}
.keyline{font-size:12px;color:var(--muted);margin:-4px 0 10px;display:flex;flex-wrap:wrap;gap:6px 14px;align-items:center}
code,.cmd{font:12px/1.4 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
.cmd{background:#f2f1ee;border:1px solid var(--line);border-radius:6px;padding:2px 8px;cursor:pointer;user-select:all}
.cmd:hover{border-color:#c9c6bf}
.copied{color:var(--climb);font-size:12px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{font-weight:600;color:var(--muted);font-size:11.5px;text-transform:uppercase;letter-spacing:.03em;text-align:left;padding:6px 6px;border-bottom:1px solid var(--line);white-space:nowrap}
td{padding:6px 6px;border-bottom:1px solid #f0eee9;vertical-align:middle}
th.c,td.c{text-align:center} td.num{text-align:right;font-variant-numeric:tabular-nums}
.heat td.cell{text-align:center;font-variant-numeric:tabular-nums;border:2px solid var(--card);border-radius:6px;min-width:38px;font-size:12px;cursor:pointer}
.heat td.cell.empty{background:#fafaf8;color:#c4c1b9;cursor:default}
.heat td.dom{max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ladder{display:flex;gap:2px}
.ladder span{width:16px;height:14px;border-radius:3px;font-size:9.5px;line-height:14px;text-align:center;color:#555}
.bar{height:6px;border-radius:3px;background:#eeece7;position:relative;min-width:60px}
.bar i{position:absolute;left:0;top:0;bottom:0;border-radius:3px;background:var(--accent)}
.bar b{position:absolute;top:-3px;bottom:-3px;width:2px;background:#999}
.legend{display:flex;gap:10px;align-items:center;font-size:12px;color:var(--muted);flex-wrap:wrap;margin-top:8px}
.legend .sw{display:inline-block;width:12px;height:12px;border-radius:3px;vertical-align:-2px;margin-right:3px}
.list li{list-style:none;padding:6px 0;border-top:1px solid #f0eee9;display:flex;justify-content:space-between;gap:10px}
.list li:first-child{border-top:none}
.controls{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}
select,input[type=text]{font:inherit;font-size:13px;padding:5px 8px;border:1px solid var(--line);border-radius:7px;background:#fff;color:var(--ink)}
input[type=text]{flex:1;min-width:160px}
.tbl-wrap{overflow-x:auto;max-height:560px;overflow-y:auto}
th.sort{cursor:pointer} th.sort:hover{color:var(--ink)}
.muted{color:var(--muted)} .small{font-size:12px}
.notice{background:#fff8e6;border:1px solid #f0dfb3;border-radius:10px;padding:10px 14px;font-size:13px;margin-bottom:16px}
details summary{cursor:pointer;color:var(--muted);font-size:13px}
.help p{margin:6px 0;font-size:13px}
</style>
</head>
<body>
<div class="wrap">
  <h1>Study Focus</h1>
  <div class="sub" id="sub"></div>
  <div class="kpis" id="kpis"></div>
  <div id="notice"></div>
  <div class="grid">
    <div>
      <div class="card">
        <div class="card-h"><h2>Do next</h2><span class="sub">ranked by importance × gap × readiness</span></div>
        <div id="queue"></div>
      </div>
      <div class="card">
        <div class="card-h"><h2>Coverage map</h2><span class="sub">domains × note level (1 basic → 5 graduate)</span></div>
        <div class="tbl-wrap" style="max-height:none"><table class="heat" id="heat"></table></div>
        <div class="legend" id="heat-legend"></div>
      </div>
    </div>
    <div>
      <div class="card">
        <div class="card-h"><h2>Blind spots</h2><span class="sub">important notes no problem tests</span></div>
        <ul class="list" id="blind"></ul>
      </div>
      <div class="card">
        <div class="card-h"><h2>Unexplored connections</h2><span class="sub">related notes you haven't linked</span></div>
        <ul class="list" id="connections"></ul>
      </div>
      <div class="card">
        <div class="card-h"><h2>KB health</h2><span class="sub">things to fix in the notes</span></div>
        <ul class="list health" id="health"></ul>
      </div>
    </div>
  </div>
  <div class="card">
    <div class="card-h"><h2>All notes</h2><span class="sub" id="count"></span></div>
    <div class="keyline" id="keyline"></div>
    <div class="controls">
      <input type="text" id="search" placeholder="Search notes…">
      <select id="fdom"><option value="">All domains</option></select>
      <select id="flevel"><option value="">All levels</option><option>1</option><option>2</option><option>3</option><option>4</option><option>5</option></select>
      <select id="fact"><option value="">All actions</option><option>practice</option><option>climb</option><option>foundation</option><option>write</option></select>
    </div>
    <div class="tbl-wrap"><table id="tbl"></table></div>
  </div>
</div>
<script>
const D = __DATA__;
const N = D.notes, P = D.problems;
const pct = x => Math.round(x * 100) + '%';
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const noteUrl = id => 'nodes/' + encodeURIComponent(id) + '.html';
const link = id => `<a href="${noteUrl(id)}" target="_parent">${esc(N[id] ? N[id].title : id)}</a>`;
const heatColor = v => `var(--m${Math.max(0, Math.min(4, Math.floor(v / D.target * 4)))})`;
const LBL = {practice:'Practice', climb:'Climb', foundation:'Fix foundation', write:'Needs problems'};
const LEVEL = {1:'Basic', 2:'Elementary', 3:'Core', 4:'Advanced', 5:'Graduate'};
const LEVEL_DESC = {1:'vocabulary / basic definition', 2:'elementary result, short proofs', 3:'core undergraduate theorem with proof',
  4:'advanced undergraduate / early graduate', 5:'graduate / research level'};
const DIFF = {1:'Recall', 2:'Routine', 3:'Standard', 4:'Hard', 5:'Challenge'};
const DIFF_DESC = {1:'plug into a definition or formula', 2:'one standard technique, few steps', 3:'standard proof combining 2-3 results',
  4:'non-obvious construction or multi-stage argument', 5:'starred / qualifying-exam level'};
const lvlChip = r => `<span class="lv lv${r.level}" title="Level ${r.level}: ${LEVEL_DESC[r.level]}${r.level_tagged ? '' : ' (not tagged yet)'}">L${r.level} ${LEVEL[r.level]}${r.level_tagged ? '' : '?'}</span>`;
const diffChip = p => `<span class="lv lv${p.difficulty}" title="Difficulty ${p.difficulty}: ${DIFF_DESC[p.difficulty]}${p.tagged ? '' : ' (not tagged yet)'}">d${p.difficulty} ${DIFF[p.difficulty]}${p.tagged ? '' : '?'}</span>`;
function problemsTable(id) {
  const ps = N[id].problems.map(x => P[x]).filter(Boolean).sort((a, b) => b.difficulty - a.difficulty || a.id.localeCompare(b.id));
  if (!ps.length) return '<p class="muted small" style="margin-top:6px">No problem tests this note yet.</p>';
  return `<table class="ptbl"><tr><th>Problem</th><th>Difficulty</th><th>Type</th><th>Time</th><th>Also tests</th></tr>` +
    ps.map(p => `<tr><td><a href="${noteUrl(p.pset)}" target="_parent">${esc(p.pset)} #${p.number}</a> <span class="muted">${esc(p.title)}</span></td>
      <td>${diffChip(p)}</td><td class="small">${esc(p.type || '—')}</td><td class="small num">${p.est_minutes ? '~' + p.est_minutes + 'm' : '—'}</td>
      <td class="small">${p.tests.filter(t => t !== id && N[t]).map(link).join(', ') || '—'}</td></tr>`).join('') + `</table>`;
}
function detail(id) {
  const r = N[id];
  return `<div class="detail"><div>${lvlChip(r)} ${r.kind ? `<span class="chip">${esc(r.kind)}</span>` : ''} <span class="small">${esc(r.summary)}</span></div>
    <div class="small muted" style="margin-top:4px">${r.problems.length} problem(s) · coverage ${pct(r.current)} · ${r.dependents} notes depend on it</div>
    ${problemsTable(id)}
    ${r.connections.length ? `<div class="sect">Connections</div>` + r.connections.map(c =>
      `<div class="con">${link(c.id)} <span class="muted small">${esc(N[c.id].domain)}</span>${c.new ? ' <span class="chip">not linked yet</span>' : ''}<br><span class="why">${esc(c.why)}</span></div>`).join('') : ''}
    </div>`;
}

document.getElementById('sub').textContent = `Updated ${D.today} · target coverage ${pct(D.target)} · tags by ${D.model}`;
const k = D.kpi;
document.getElementById('kpis').innerHTML = [
  [pct(k.avg), 'average coverage'],
  [`${k.at_target}<span class="muted" style="font-size:15px"> / ${k.notes}</span>`, 'notes at target'],
  [`${k.covered}<span class="muted" style="font-size:15px"> / ${k.notes}</span>`, 'notes tested by a problem'],
  [k.no_problems, 'notes with no problems'],
  [`${k.problems}`, 'problems'],
].map(([v, l]) => `<div class="kpi"><div class="v">${v}</div><div class="l">${l}</div></div>`).join('');

const untN = k.pending_notes, untP = k.pending_problems;
if (untN || untP || D.review.length) {
  document.getElementById('notice').innerHTML = `<div class="notice">` +
    (untN || untP ? `${untP} problems and ${untN} notes are not tagged yet (defaults used: level 3 / difficulty 3). They are tagged automatically the next time <code>dev.sh</code> runs with the local LLM up. ` : '') +
    (D.review.length ? `${D.review.length} tags had unstable LLM ratings; check <code>meta/tags.json</code> (set <code>"locked": true</code> after correcting).` : '') + `</div>`;
}

function problemLine(pid) {
  const p = P[pid]; if (!p) return '';
  return `<a href="${noteUrl(p.pset)}" target="_parent">${esc(p.pset)} · #${p.number}</a> <span class="muted">${esc(p.title)}</span>
    ${diffChip(p)}${p.type ? ` <span class="chip">${esc(p.type)}${p.est_minutes ? ' · ~' + p.est_minutes + 'm' : ''}</span>` : ''}`;
}
document.getElementById('queue').innerHTML = D.queue.map((id, i) => {
  const r = N[id];
  return `<div class="q"><div class="n">${i + 1}</div><div>
    <div><span class="badge b-${r.action}">${LBL[r.action]}</span><span class="t">${link(id)}</span></div>
    <div class="meta">${lvlChip(r)} · ${esc(r.domain)} · coverage ${pct(r.current)} · ${r.dependents} dependents</div>
    <div class="why">${esc(r.reason)}</div>
    ${r.suggest ? `<div class="do">${problemLine(r.suggest)}</div>` : ''}
    ${r.problems.length ? `<details class="probs"><summary>Problems testing this note (${r.problems.length})</summary>${problemsTable(id)}</details>` : ''}
  </div></div>`;
}).join('') || '<p class="muted">Nothing to do: everything is at target.</p>';

document.addEventListener('click', e => {
  const c = e.target.closest('.cmd'); if (!c) return;
  const txt = c.dataset.cmd || c.textContent;
  try { navigator.clipboard.writeText(txt); } catch (_) {}
  const s = document.createElement('span'); s.className = 'copied'; s.textContent = ' copied';
  c.after(s); setTimeout(() => s.remove(), 1200);
});

// heat map
const heat = document.getElementById('heat');
heat.innerHTML = `<tr><th>Domain</th>${[1,2,3,4,5].map(l => `<th class="c">L${l}</th>`).join('')}<th>Coverage</th><th title="average note level vs average problem difficulty">Level · difficulty</th><th>Problems d1–d5</th></tr>` +
  D.domains.map(d => `<tr><td class="dom" title="${esc(d.domain)}">${esc(d.domain)} <span class="muted small">${d.n}</span></td>` +
    [1,2,3,4,5].map(l => { const c = d.levels[l];
      return c ? `<td class="cell" style="background:${heatColor(c.avg)}" data-dom="${esc(d.domain)}" data-level="${l}" title="${c.n} notes · avg ${pct(c.avg)}">${c.n}</td>` : `<td class="cell empty">·</td>`; }).join('') +
    `<td><div class="bar" title="${pct(d.avg)}"><i style="width:${Math.min(100, d.avg * 100)}%"></i><b style="left:${D.target * 100}%"></b></div></td>` +
    `<td class="gap${d.lvl && (d.diff == null || d.lvl - d.diff >= 0.75) ? ' bad' : ''}" title="notes average level ${d.lvl ?? '—'}, problems average difficulty ${d.diff ?? '—'}">L${d.lvl ?? '—'} · d${d.diff ?? '—'}</td>` +
    `<td><div class="ladder">${[1,2,3,4,5].map(l => { const x = d.ladder[l] || [0,0,0];
       const bg = !x[0] ? '#f4f3f0' : x[2] === x[0] ? 'var(--m4)' : x[1] ? 'var(--m2)' : 'var(--m0)';
       return `<span style="background:${bg}" title="difficulty ${l}: ${x[0]} problems, ${x[1]} attempted, ${x[2]} solved (≥2)">${x[0] || ''}</span>`; }).join('')}</div></td></tr>`).join('');
document.getElementById('heat-legend').innerHTML = `<span>Cell = number of notes, colour = average coverage:</span>` +
  [0,1,2,3].map(i => `${pct(i * D.target / 4)}–${pct((i + 1) * D.target / 4)}`).concat(['≥ target']).map((t, i) => `<span><span class="sw" style="background:var(--m${i})"></span>${t}</span>`).join('') +
  `<span>· click a cell to filter the table</span>`;
heat.addEventListener('click', e => { const c = e.target.closest('td.cell[data-dom]'); if (!c) return;
  fdom.value = c.dataset.dom; flevel.value = c.dataset.level; render(); document.getElementById('tbl').scrollIntoView({behavior:'smooth'}); });

document.getElementById('blind').innerHTML = D.blind.map(id => `<li><span>${link(id)}<br>${lvlChip(N[id])} <span class="muted small">${esc(N[id].domain)}</span></span><span class="muted small" style="white-space:nowrap">${N[id].dependents} dependents</span></li>`).join('') || '<li class="muted">None. Every note is tested by at least one problem.</li>';


// table
const fdom = document.getElementById('fdom'), flevel = document.getElementById('flevel'), fact = document.getElementById('fact'), search = document.getElementById('search');
[...new Set(Object.values(N).map(r => r.domain))].sort().forEach(d => fdom.insertAdjacentHTML('beforeend', `<option>${esc(d)}</option>`));
let sortKey = 'priority', sortDir = -1;
const COLS = [['title','Note'],['domain','Domain'],['level','Level'],['current','Coverage'],['problems','Probs'],['dependents','Deps'],['priority','Priority'],['action','Next']];
function render() {
  const q = search.value.toLowerCase();
  let rows = Object.values(N).filter(r => (!fdom.value || r.domain === fdom.value) && (!flevel.value || r.level == flevel.value) &&
    (!fact.value || r.action === fact.value) && (!q || (r.title + ' ' + r.id + ' ' + r.summary).toLowerCase().includes(q)));
  const val = r => sortKey === 'problems' ? r.problems.length : (r[sortKey] ?? '');
  rows.sort((a, b) => (val(a) > val(b) ? 1 : val(a) < val(b) ? -1 : 0) * sortDir);
  document.getElementById('count').textContent = `${rows.length} of ${Object.keys(N).length}`;
  document.getElementById('tbl').innerHTML = `<tr>${COLS.map(([k, l]) => `<th class="sort" data-k="${k}">${l}${sortKey === k ? (sortDir > 0 ? ' ↑' : ' ↓') : ''}</th>`).join('')}</tr>` +
    rows.map(r => `<tr class="nrow${openRows.has(r.id) ? ' open' : ''}" data-id="${esc(r.id)}"><td title="${esc(r.summary)}"><span class="chev">▸</span> ${link(r.id)}${r.completeness === 'stub' ? ' <span class="chip">stub</span>' : ''}</td><td class="small muted">${esc(r.domain)}</td>
      <td>${lvlChip(r)}</td>
      <td><div style="display:flex;align-items:center;gap:6px"><div class="bar" style="flex:1"><i style="width:${r.current * 100}%"></i><b style="left:${D.target * 100}%"></b></div><span class="small num" style="width:34px">${pct(r.current)}</span></div></td>
            <td class="num">${r.problems.length}</td><td class="num">${r.dependents}</td><td class="num">${r.priority.toFixed(2)}</td>
      <td><span class="badge b-${r.action}">${LBL[r.action]}</span></td></tr>` +
      (openRows.has(r.id) ? `<tr class="drow"><td colspan="${COLS.length}">${detail(r.id)}</td></tr>` : '')).join('');
}
const openRows = new Set();
document.getElementById('keyline').innerHTML = 'Note level: ' + [1,2,3,4,5].map(l => lvlChip({level: l, level_tagged: true})).join(' ') +
  ' <span>·</span> Problem difficulty: ' + [1,2,3,4,5].map(d => diffChip({difficulty: d, tagged: true})).join(' ') +
  ' <span>·</span> <span>click a row to see the problems that test it</span>';
document.getElementById('tbl').addEventListener('click', e => {
  const tr = e.target.closest('tr.nrow');
  if (tr && !e.target.closest('a')) { const id = tr.dataset.id; openRows.has(id) ? openRows.delete(id) : openRows.add(id); render(); return; }
  const th = e.target.closest('th.sort'); if (!th) return;
  if (sortKey === th.dataset.k) sortDir *= -1; else { sortKey = th.dataset.k; sortDir = ['title','domain','action'].includes(sortKey) ? 1 : -1; } render(); });
[search, fdom, flevel, fact].forEach(el => el.addEventListener('input', render));

// connections + health
document.getElementById('connections').innerHTML = D.connections.slice(0, 12).map(c =>
  `<li style="display:block"><div>${link(c.a)} ↔ ${link(c.b)}${c.cross ? ' <span class="chip">cross-domain</span>' : ''}</div><div class="small muted">${esc(c.why)}</div></li>`).join('') ||
  `<li class="muted small">${D.n_insights ? 'No unlinked connections suggested.' : 'Generated by the local LLM after tagging finishes.'}</li>`;
const H = D.health;
const hItem = (label, ids, fmt) => ids.length ? `<li><details><summary><span class="cnt">${ids.length}</span> ${label}</summary><div class="small" style="margin-top:4px">${ids.map(fmt).join(', ')}</div></details></li>` : '';
document.getElementById('health').innerHTML =
  hItem('broken links (target notebook missing)', H.broken, ([a, b]) => `${link(a)} → <code>${esc(b)}</code>`) +
  hItem('orphan notes (no links in or out)', H.orphans, link) +
  hItem('stub notes (under 1,500 characters)', H.stubs, link) +
  hItem('titles to fix', H.titles, link) || '<li class="muted small">Nothing to fix.</li>';

function typeset(el) {
  if (window.renderMathInElement) renderMathInElement(el, {delimiters: [{left: '$$', right: '$$', display: true},
    {left: '$', right: '$', display: false}], throwOnError: false});
}
const _render = render;
render = function () { _render(); typeset(document.getElementById('tbl')); };
render();
typeset(document.body);
</script>
</body>
</html>
"""
