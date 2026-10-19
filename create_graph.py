import os
import re
import json
from collections import defaultdict, deque

node_path = "nodes"
files = sorted([f for f in os.listdir(node_path) if f.endswith(".ipynb")])
psets = [f for f in files if f.startswith("pset-")]
regular_notes = [f for f in files if not f.startswith("pset-")]

# ─────────────────────────────────────────────────────────────
# 1. FINE-GRAINED SUBJECT TAXONOMY & DYNAMIC DISCOVERY
# ─────────────────────────────────────────────────────────────
from pipeline.taxonomy import FINE_TAXONOMY  # noqa: E402
from pipeline import extract as _extract, mastery as _mastery, tagger as _tagger  # noqa: E402

_NOTES, _PROBLEMS = _extract.load(node_path)
_TAGS = _tagger.load_tags()
_DOMAIN_BY_ID = _mastery.domains(_NOTES, _TAGS)

# Inverted mapping: filename -> domain
file_to_domain = {}
for domain, file_list in FINE_TAXONOMY.items():
    for fn in file_list:
        file_to_domain[fn] = domain

# ─────────────────────────────────────────────────────────────
# 2. GRAPH EDGES & LINK PARSING
# ─────────────────────────────────────────────────────────────
links = []
incoming = defaultdict(list)
outgoing = defaultdict(list)
file_contents = {}

for f in files:
    with open(os.path.join(node_path, f), "r", encoding="utf-8") as file:
        content = file.read()
        file_contents[f] = content
        extracted_links = re.findall(r"\]\((.*?\.ipynb)", content)

        unique_targets = set()
        for link in extracted_links:
            target = os.path.basename(link)
            if target in files and target != f:
                unique_targets.add(target)

        for target in unique_targets:
            links.append({"source": f, "target": target})
            outgoing[f].append(target)
            incoming[target].append(f)

# Domains: curated taxonomy > LLM tag (meta/tags.json) > neighbour vote  (see pipeline/mastery.py)
for f in files:
    file_to_domain[f] = _DOMAIN_BY_ID.get(f[:-6], "Unsorted")

# Problems also "cover" the notes the LLM says they test (meta/tags.json), not only explicit links
for _pid, _t in _TAGS["problems"].items():
    _pset = _pid.split("#")[0] + ".ipynb"
    if _pset in files:
        for _nid in _t.get("tests", []):
            _target = _nid + ".ipynb"
            if _target in files and _target not in outgoing[_pset]:
                outgoing[_pset].append(_target)
                incoming[_target].append(_pset)
                links.append({"source": _pset, "target": _target})

# ─────────────────────────────────────────────────────────────
# 3. MULTI-TIERED COVERAGE ENGINE (BFS)
# ─────────────────────────────────────────────────────────────
direct_covered = set()
pset_covering_map = defaultdict(set)

for p in psets:
    for target in outgoing[p]:
        direct_covered.add(target)
        pset_covering_map[target].add(p)

distance_from_pset = {}
queue = deque()
for p in psets:
    for target in outgoing[p]:
        if target not in distance_from_pset:
            distance_from_pset[target] = 1
            queue.append((target, 1))

while queue:
    curr, dist = queue.popleft()
    for prereq in outgoing[curr]:
        if prereq not in distance_from_pset:
            distance_from_pset[prereq] = dist + 1
            queue.append((prereq, dist + 1))
        for p in pset_covering_map[curr]:
            pset_covering_map[prereq].add(p)

# Determine status for each note
coverage_status = {}
for f in files:
    if f.startswith("pset-"):
        coverage_status[f] = "pset"
    elif f in direct_covered:
        coverage_status[f] = "direct"
    elif f in distance_from_pset:
        coverage_status[f] = "transitive"
    else:
        coverage_status[f] = "uncovered"

# ─────────────────────────────────────────────────────────────
# 4. FOCUS & PRIORITY RANKING ENGINE
# ─────────────────────────────────────────────────────────────
domain_counts = defaultdict(lambda: {"total": 0, "direct": 0, "transitive": 0, "uncovered": 0})
for f in regular_notes:
    dom = file_to_domain[f]
    st = coverage_status[f]
    domain_counts[dom]["total"] += 1
    domain_counts[dom][st] += 1

priority_list = []
for f in regular_notes:
    st = coverage_status[f]
    dom = file_to_domain[f]
    usages_count = len(incoming[f])
    prelims_count = len(outgoing[f])
    
    dom_stats = domain_counts[dom]
    dom_cov_rate = (dom_stats["direct"] + dom_stats["transitive"]) / max(1, dom_stats["total"])
    domain_urgency_bonus = int((1.0 - dom_cov_rate) * 25)

    status_multiplier = 3 if st == "uncovered" else (1 if st == "transitive" else 0)
    score = status_multiplier * (usages_count * 3 + prelims_count + 1 + domain_urgency_bonus)

    label = f.replace(".ipynb", "").replace("-", " ").title()
    priority_list.append({
        "id": f,
        "name": label,
        "domain": dom,
        "status": st,
        "score": score,
        "usages": usages_count,
        "prelims": prelims_count,
        "distance": distance_from_pset.get(f, None),
        "covering_psets": [p.replace(".ipynb", "").replace("-", " ").title() for p in pset_covering_map.get(f, [])]
    })

priority_list.sort(key=lambda x: (x["score"], x["usages"], x["prelims"]), reverse=True)

# ─────────────────────────────────────────────────────────────
# 5. BUILD GRAPH DATA OBJECTS
# ─────────────────────────────────────────────────────────────
STATUS_COLORS = {
    "pset": "#8e44ad",        # Vibrant Amethyst Purple
    "direct": "#27ae60",      # Emerald Green
    "transitive": "#d35400",  # Amber Gold / Burnt Orange
    "uncovered": "#c0392b"    # Crimson Red
}

STATUS_LABELS = {
    "pset": "Problem Set",
    "direct": "Directly Practiced",
    "transitive": "Prerequisite Concept",
    "uncovered": "Uncovered"
}

nodes = []
for f in files:
    label = f.replace(".ipynb", "").replace("-", " ").title()
    url = f"nodes/{f.replace('.ipynb', '.html')}"
    st = coverage_status[f]
    dom = file_to_domain.get(f, "General")
    
    prelims = [p.replace(".ipynb", "").replace("-", " ").title() for p in outgoing[f]]
    usages = [u.replace(".ipynb", "").replace("-", " ").title() for u in incoming[f]]
    covering_ps = [p.replace(".ipynb", "").replace("-", " ").title() for p in pset_covering_map.get(f, [])]
    
    nodes.append({
        "id": f,
        "name": label,
        "url": url,
        "domain": dom,
        "status": st,
        "status_label": STATUS_LABELS[st],
        "color": STATUS_COLORS[st],
        "distance": distance_from_pset.get(f, 0 if st == "pset" else -1),
        "prelims": prelims,
        "usages": usages,
        "covering_psets": covering_ps
    })

graph_data = {"nodes": nodes, "links": links}
json_graph_data = json.dumps(graph_data)

# ─────────────────────────────────────────────────────────────
# 6. GENERATE COLOR-CODED KNOWLEDGE GRAPH (`graph_output.html`)
# ─────────────────────────────────────────────────────────────
html_graph_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Knowledge Graph & Practice Coverage</title>
  <script src="https://unpkg.com/force-graph"></script>
  <style>
    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}
    body {{
      background-color: #f8f9fa;
      font-family: "CMU Serif", "Times New Roman", "Latin Modern Roman", Georgia, serif;
      overflow: hidden;
    }}
    #graph-container {{
      width: 100vw;
      height: 100vh;
    }}

    /* Search bar overlay */
    #search-wrapper {{
      position: fixed;
      top: 16px;
      right: 18px;
      z-index: 1000;
      width: min(280px, 70vw);
      opacity: 0.85;
      transition: opacity 0.3s ease;
    }}
    #search-wrapper:hover,
    #search-wrapper.active {{
      opacity: 1;
    }}
    #search-input {{
      width: 100%;
      padding: 7px 10px;
      font-size: 13px;
      font-family: "CMU Serif", "Times New Roman", Georgia, serif;
      font-style: italic;
      color: #222;
      border: none;
      border-bottom: 1.2px solid #555;
      border-radius: 0;
      background: rgba(255, 255, 253, 0.8);
      outline: none;
      transition: border-color 0.25s, background 0.25s;
    }}
    #search-input::placeholder {{
      color: #777;
      font-style: italic;
    }}
    #search-input:focus {{
      border-bottom-color: #111;
      background: rgba(255, 255, 253, 0.98);
    }}
    #search-results {{
      list-style: none;
      margin: 2px 0 0;
      padding: 0;
      background: rgba(255,255,253,0.97);
      border: 1px solid #bbb;
      border-top: none;
      max-height: 240px;
      overflow-y: auto;
      display: none;
      box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }}
    #search-results li {{
      padding: 7px 10px;
      cursor: pointer;
      font-size: 13px;
      font-family: "CMU Serif", "Times New Roman", Georgia, serif;
      color: #333;
      border-bottom: 0.5px solid #eee;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    #search-results li:last-child {{ border-bottom: none; }}
    #search-results li:hover,
    #search-results li.active {{
      background: rgba(0,0,0,0.06);
      color: #000;
    }}

    /* Interactive Legend & Filters */
    #legend-wrapper {{
      position: fixed;
      bottom: 18px;
      left: 18px;
      z-index: 1000;
      background: rgba(255, 255, 253, 0.94);
      border: 1px solid #ccc;
      border-radius: 6px;
      padding: 10px 14px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.08);
      max-width: 320px;
      font-size: 12px;
      line-height: 1.4;
      backdrop-filter: blur(4px);
    }}
    #legend-title {{
      font-weight: bold;
      font-variant: small-caps;
      letter-spacing: 0.05em;
      margin-bottom: 6px;
      color: #222;
      font-size: 13px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .legend-item {{
      display: flex;
      align-items: center;
      margin-bottom: 5px;
      cursor: pointer;
      padding: 2px 4px;
      border-radius: 3px;
      transition: background 0.15s;
      user-select: none;
    }}
    .legend-item:hover {{
      background: rgba(0,0,0,0.05);
    }}
    .legend-item.dimmed {{
      opacity: 0.35;
    }}
    .legend-dot {{
      width: 10px;
      height: 10px;
      border-radius: 50%;
      margin-right: 8px;
      flex-shrink: 0;
    }}
    .legend-dot.square {{
      border-radius: 2px;
    }}
    .legend-count {{
      margin-left: auto;
      color: #666;
      font-size: 11px;
      font-style: italic;
    }}

    /* Tooltip Styling */
    .node-tooltip {{
      background: rgba(255, 255, 255, 0.98);
      padding: 12px 14px;
      border: 1px solid #ccc;
      border-radius: 6px;
      box-shadow: 0 6px 16px rgba(0,0,0,0.12);
      color: #222;
      max-width: 320px;
      font-size: 13px;
      line-height: 1.4;
      pointer-events: none;
      font-family: "CMU Serif", "Times New Roman", Georgia, serif;
    }}
    .node-tooltip h4 {{
      margin: 0 0 4px 0;
      font-size: 15px;
      color: #111;
    }}
    .tooltip-badge {{
      display: inline-block;
      padding: 2px 7px;
      border-radius: 10px;
      font-size: 11px;
      font-weight: bold;
      color: #fff;
      margin-bottom: 6px;
    }}
    .tooltip-domain {{
      display: block;
      font-size: 11px;
      color: #666;
      font-style: italic;
      margin-bottom: 6px;
    }}
    .node-tooltip .section-title {{
      font-weight: bold;
      color: #444;
      margin-top: 6px;
      display: block;
      font-size: 12px;
    }}
    .node-tooltip ul {{
      margin: 2px 0 0 0;
      padding-left: 18px;
    }}
    .node-tooltip li {{
      margin-bottom: 2px;
      font-size: 12px;
    }}
  </style>
</head>
<body>
  <!-- Search bar -->
  <div id="search-wrapper">
    <input id="search-input" type="text" placeholder="Search knowledge graph\u2026" autocomplete="off" />
    <ul id="search-results"></ul>
  </div>

  <!-- Legend & Filter overlay -->
  <div id="legend-wrapper">
    <div id="legend-title">
      <span>Practice Coverage</span>
      <span style="font-size:10px; font-weight:normal; color:#666; cursor:pointer;" onclick="resetFilter()">[Reset]</span>
    </div>
    <div class="legend-item" id="filter-pset" onclick="toggleStatusFilter('pset')">
      <span class="legend-dot square" style="background: #8e44ad;"></span>
      <span>Problem Sets</span>
      <span class="legend-count">{len(psets)}</span>
    </div>
    <div class="legend-item" id="filter-direct" onclick="toggleStatusFilter('direct')">
      <span class="legend-dot" style="background: #27ae60;"></span>
      <span>Directly Practiced</span>
      <span class="legend-count">{len(direct_covered)}</span>
    </div>
    <div class="legend-item" id="filter-transitive" onclick="toggleStatusFilter('transitive')">
      <span class="legend-dot" style="background: #d35400;"></span>
      <span>Prerequisites (Transitive)</span>
      <span class="legend-count">{len(distance_from_pset) - len(direct_covered)}</span>
    </div>
    <div class="legend-item" id="filter-uncovered" onclick="toggleStatusFilter('uncovered')">
      <span class="legend-dot" style="background: #c0392b;"></span>
      <span>Uncovered</span>
      <span class="legend-count">{len(regular_notes) - len(distance_from_pset)}</span>
    </div>
  </div>

  <div id="graph-container"></div>
  <script>
    const gData = {json_graph_data};

    gData.links.forEach(link => {{
      const a = gData.nodes.find(n => n.id === link.source);
      const b = gData.nodes.find(n => n.id === link.target);
      if(!a || !b) return;
      
      if(!a.neighbors) a.neighbors = [];
      if(!b.neighbors) b.neighbors = [];
      a.neighbors.push(b);
      b.neighbors.push(a);
      
      if(!a.links) a.links = [];
      if(!b.links) b.links = [];
      a.links.push(link);
      b.links.push(link);
    }});

    let hoverNode = null;
    let activeFilter = null;
    const highlightNodes = new Set();
    const highlightLinks = new Set();

    const container = document.getElementById('graph-container');
    const Graph = ForceGraph()(container)
      .width(container.offsetWidth)
      .height(container.offsetHeight)
      .graphData(gData)
      .backgroundColor('transparent')
      .nodeLabel(node => {{
        let badgeBg = node.color;
        let html = '<div class="node-tooltip">';
        html += '<h4>' + node.name + '</h4>';
        html += '<span class="tooltip-badge" style="background:' + badgeBg + '">' + (node.status === 'pset' ? 'Problem Set' : node.status_label) + '</span>';
        html += '<span class="tooltip-domain">Topic: ' + node.domain + '</span>';
        
        if (node.covering_psets && node.covering_psets.length > 0) {{
            html += '<span class="section-title">Tested in Problem Sets:</span><ul>';
            node.covering_psets.slice(0, 4).forEach(p => {{ html += '<li>' + p + '</li>'; }});
            if(node.covering_psets.length > 4) html += '<li>...and ' + (node.covering_psets.length - 4) + ' more</li>';
            html += '</ul>';
        }}
        
        if (node.prelims && node.prelims.length > 0) {{
            html += '<span class="section-title">Prerequisites / Uses:</span><ul>';
            node.prelims.slice(0, 5).forEach(p => {{ html += '<li>' + p + '</li>'; }});
            if(node.prelims.length > 5) html += '<li>...and ' + (node.prelims.length - 5) + ' more</li>';
            html += '</ul>';
        }}
        
        if (node.usages && node.usages.length > 0) {{
            html += '<span class="section-title">Used by (' + node.usages.length + ' nodes):</span><ul>';
            node.usages.slice(0, 4).forEach(u => {{ html += '<li>' + u + '</li>'; }});
            if(node.usages.length > 4) html += '<li>...and ' + (node.usages.length - 4) + ' more</li>';
            html += '</ul>';
        }}
        
        html += '<br><small style="color:#888;"><i>Click node to open notebook</i></small>';
        html += '</div>';
        return html;
      }})
      .nodeCanvasObject((node, ctx, globalScale) => {{
          const isHighlighted = highlightNodes.has(node);
          const isFilterMatch = !activeFilter || node.status === activeFilter;
          const isFaded = (hoverNode && !isHighlighted) || (!hoverNode && activeFilter && !isFilterMatch);
          const label = node.name;
          
          const fontSize = node.status === 'pset' ? 4.5 : 3.8;
          ctx.font = `${{fontSize}}px "CMU Serif", "Times New Roman"`;

          ctx.beginPath();
          if (node.status === 'pset') {{
              const size = 7;
              ctx.fillStyle = isHighlighted ? '#a569bd' : (isFaded ? 'rgba(142, 68, 173, 0.12)' : '#8e44ad');
              ctx.fillRect(node.x - size/2, node.y - size/2, size, size);
              ctx.strokeStyle = '#5b2c6f';
              ctx.lineWidth = 0.6;
              ctx.strokeRect(node.x - size/2, node.y - size/2, size, size);
          }} else {{
              const radius = isHighlighted ? 5 : (node.status === 'direct' ? 4.5 : (node.status === 'transitive' ? 4 : 3.5));
              ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
              ctx.fillStyle = isHighlighted ? '#3498db' : (isFaded ? 'rgba(180, 180, 180, 0.12)' : node.color);
              ctx.fill();
              if (isHighlighted) {{
                  ctx.strokeStyle = '#2980b9';
                  ctx.lineWidth = 1;
                  ctx.stroke();
              }}
          }}

          if (!isFaded || isHighlighted) {{
              ctx.textAlign = 'center';
              ctx.textBaseline = 'middle';
              ctx.fillStyle = isHighlighted ? '#1a5276' : (node.status === 'pset' ? '#4a235a' : '#333333');
              ctx.fillText(label, node.x, node.y + (node.status === 'pset' ? 8 : 7));
          }}
      }})
      .nodePointerAreaPaint((node, color, ctx) => {{
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.arc(node.x, node.y, 6, 0, 2 * Math.PI, false);
          ctx.fill();
      }})
      .linkWidth(link => highlightLinks.has(link) ? 2 : 0.4)
      .linkColor(link => highlightLinks.has(link) ? '#2980b9' : (hoverNode ? 'rgba(180, 190, 200, 0.08)' : 'rgba(170, 183, 196, 0.4)'))
      .linkDirectionalParticles(link => highlightLinks.has(link) ? 3 : 0)
      .linkDirectionalParticleWidth(2.5)
      .linkDirectionalArrowLength(3.2)
      .linkDirectionalArrowRelPos(1)
      .onNodeHover(node => {{
        if ((!node && !highlightNodes.size) || (node && hoverNode === node)) return;

        highlightNodes.clear();
        highlightLinks.clear();
        if (node) {{
          highlightNodes.add(node);
          if (node.neighbors) node.neighbors.forEach(neighbor => highlightNodes.add(neighbor));
          if (node.links) node.links.forEach(link => highlightLinks.add(link));
        }}

        hoverNode = node || null;
      }})
      .onNodeClick(node => {{
        if (node.url) {{
           window.top.location.href = node.url;
        }}
      }});
      
    Graph.d3Force('charge').strength(-240);
    Graph.d3Force('link').distance(45);

    let fitted = false;
    const doFit = () => {{
      if (!fitted) {{
        fitted = true;
        Graph.zoomToFit(400, 40);
      }}
    }};
    Graph.onEngineStop(doFit);
    setTimeout(doFit, 1500);

    window.addEventListener('resize', () => {{
      const w = container.clientWidth;
      const h = container.clientHeight;
      Graph.width(w).height(h);
      doFit();
    }});

    function toggleStatusFilter(status) {{
      if (activeFilter === status) {{
        resetFilter();
      }} else {{
        activeFilter = status;
        ['pset', 'direct', 'transitive', 'uncovered'].forEach(s => {{
          const el = document.getElementById('filter-' + s);
          if (el) el.classList.toggle('dimmed', s !== status);
        }});
      }}
    }}

    function resetFilter() {{
      activeFilter = null;
      ['pset', 'direct', 'transitive', 'uncovered'].forEach(s => {{
        const el = document.getElementById('filter-' + s);
        if (el) el.classList.remove('dimmed');
      }});
    }}

    const searchInput  = document.getElementById('search-input');
    const searchResults = document.getElementById('search-results');
    const searchWrapper = document.getElementById('search-wrapper');
    let activeIdx = -1;

    searchInput.addEventListener('focus', () => searchWrapper.classList.add('active'));
    searchInput.addEventListener('blur', () => {{
      setTimeout(() => {{ if (document.activeElement !== searchInput) searchWrapper.classList.remove('active'); }}, 150);
    }});

    function renderResults(matches) {{
      searchResults.innerHTML = '';
      activeIdx = -1;
      if (matches.length === 0) {{ searchResults.style.display = 'none'; return; }}
      searchResults.style.display = 'block';
      matches.forEach((node, i) => {{
        const li = document.createElement('li');
        li.innerHTML = '<span>' + node.name + '</span><span style="font-size:10px; color:' + node.color + ';">● ' + node.status.toUpperCase() + '</span>';
        li.addEventListener('mouseenter', () => {{
          activeIdx = i;
          updateActive();
        }});
        li.addEventListener('click', () => selectNode(node));
        searchResults.appendChild(li);
      }});
    }}

    function updateActive() {{
      const items = searchResults.querySelectorAll('li');
      items.forEach((li, i) => li.classList.toggle('active', i === activeIdx));
    }}

    function selectNode(node) {{
      searchInput.value = '';
      searchResults.style.display = 'none';
      searchInput.blur();

      highlightNodes.clear();
      highlightLinks.clear();
      highlightNodes.add(node);
      if (node.neighbors) node.neighbors.forEach(n => highlightNodes.add(n));
      if (node.links) node.links.forEach(l => highlightLinks.add(l));
      hoverNode = node;

      Graph.centerAt(node.x, node.y, 600);
      Graph.zoom(5.5, 600);
    }}

    searchInput.addEventListener('input', () => {{
      const q = searchInput.value.trim().toLowerCase();
      if (!q) {{ searchResults.style.display = 'none'; return; }}
      const matches = gData.nodes.filter(n => n.name.toLowerCase().includes(q) || n.domain.toLowerCase().includes(q)).slice(0, 15);
      renderResults(matches);
    }});

    searchInput.addEventListener('keydown', (e) => {{
      const items = searchResults.querySelectorAll('li');
      if (e.key === 'ArrowDown')  {{ e.preventDefault(); activeIdx = Math.min(activeIdx + 1, items.length - 1); updateActive(); }}
      if (e.key === 'ArrowUp')    {{ e.preventDefault(); activeIdx = Math.max(activeIdx - 1, 0); updateActive(); }}
      if (e.key === 'Enter' && activeIdx >= 0) {{
        e.preventDefault();
        const q = searchInput.value.trim().toLowerCase();
        const matches = gData.nodes.filter(n => n.name.toLowerCase().includes(q) || n.domain.toLowerCase().includes(q)).slice(0, 15);
        if (matches[activeIdx]) selectNode(matches[activeIdx]);
      }}
      if (e.key === 'Escape') {{ searchResults.style.display = 'none'; searchInput.blur(); }}
    }});

    document.addEventListener('click', (e) => {{
      if (!document.getElementById('search-wrapper').contains(e.target)) {{
        searchResults.style.display = 'none';
      }}
    }});
  </script>
</body>
</html>
"""

with open("graph_output.html", "w", encoding="utf-8") as f:
    f.write(html_graph_content)

print(f"Knowledge graph generated: {len(files)} notebooks, {len(links)} links -> graph_output.html")
