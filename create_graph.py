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
FINE_TAXONOMY = {
    "Real Analysis (Foundations & Sequences)": [
        "axiom-of-completeness.ipynb", "real-numbers.ipynb", "supremum-infimum.ipynb", "archimedean-property-of-R.ipynb",
        "def-dedekind-cuts.ipynb", "prop-dedekind-cuts.ipynb", "density-theorem-of-R.ipynb", "existence-of-decimal-expansion-in-R.ipynb",
        "existence-of-nth-roots-in-R.ipynb", "zero-squeeze-in-R.ipynb", "adding-inequalities.ipynb", "triangle-inequality.ipynb",
        "absolute-value.ipynb", "arithmetic-geometric-mean-inequality.ipynb", "ordered-field.ipynb", "ordered-set.ipynb", "order.ipynb", "field.ipynb",
        "pre-set-theory.ipynb", "pre-logic.ipynb", "cardinality.ipynb", "interval.ipynb", "sequence.ipynb", "sequence-limit.ipynb", "subsequences.ipynb",
        "geometric-sequence.ipynb", "composite-sequences-limit.ipynb", "squeeze-theorem-for-sequences.ipynb", "limsup-liminf.ipynb",
        "Cauchy-sequences.ipynb", "Bolzano-Weierstrass-theorem.ipynb", "nested-interval-property.ipynb", "cantor-set.ipynb"
    ],
    "Measure Theory & Integration": [
        "Lebesgue-measure.ipynb", "lebesgue-outer-measure.ipynb", "lebesgue-integral.ipynb", "Borel-sets-and-measurability.ipynb",
        "measurable-functions.ipynb", "measurable-sets.ipynb", "measurable-sets-algebra.ipynb", "measure.ipynb", "measure-properties-and-completion.ipynb",
        "limits-of-measurable-functions.ipynb", "fatous-lemma-and-convergence-theorems.ipynb", "continuity-of-measure.ipynb",
        "sigma-algebra.ipynb", "sigma-algebra-of-measurable-sets.ipynb"
    ],
    "Metric Spaces & Topology": [
        "metric-spaces.ipynb", "metric-space-topology.ipynb", "compactness.ipynb", "nests-of-compacts.ipynb", "continuity-and-compactness.ipynb",
        "homeomorphisms-compactness.ipynb", "relative-topology-inheritance.ipynb", "continuity-topology.ipynb", "function-continuity.ipynb",
        "uniform-continuity.ipynb", "sequences-metric-spaces.ipynb", "contractions.ipynb", "product-metrics-continuity.ipynb",
        "normed-vector-spaces.ipynb", "func-lim-seq-lim.ipynb", "limit.ipynb", "real-valued-functions.ipynb", "def-functions-mappings.ipynb", "completeness.ipynb"
    ],
    "Function Spaces & Fixed Points": [
        "function-spaces.ipynb", "banach-fp-thm.ipynb", "brouwer-fixed-point-theorem.ipynb", "equicontinuity-Arzela-Ascoli-Thm.ipynb",
        "ode-and-picards-thm.ipynb"
    ],
    "Probability Foundations & Combinatorics": [
        "probability.ipynb", "probability-naive-definition.ipynb", "probability-properties.ipynb", "sample-space.ipynb", "event.ipynb", "outcome.ipynb",
        "experiment.ipynb", "conditional-probability.ipynb", "law-of-total-probability.ipynb", "independence-of-events.ipynb", "inclusion-exclusion.ipynb",
        "adjusting-for-overcounting.ipynb", "sampling-with-replacement.ipynb", "sampling-without-replacement.ipynb", "multiplication-rule.ipynb",
        "binomial-coefficient.ipynb", "binomial-coefficient-formula.ipynb", "binomial-theorem.ipynb", "vandermonde’s-identity.ipynb", "story-proofs.ipynb",
        "partnerships.ipynb", "full-house.ipynb", "birthday-problem.ipynb", "monty-hall-problem.ipynb", "simpsons-paradox.ipynb", "newton-pepys-problem.ipynb",
        "de-montmorts-matching-problem.ipynb", "bose-einstein-problem.ipynb", "occupancy-problem.ipynb", "coupon-collector-problem.ipynb"
    ],
    "Random Variables & Distributions": [
        "random-variables.ipynb", "indicator-rv.ipynb", "probability-mass-function.ipynb", "cumulative-distribution-functions.ipynb",
        "bernoulli-and-binomial-distributions.ipynb", "hypergeometric-distribution.ipynb", "binomial-hypergeometric-connections.ipynb",
        "geometric-and-negative-binomial-dist.ipynb", "poisson-distribution.ipynb", "multinomial-distribution.ipynb", "expectation.ipynb",
        "expectations-of-discrete-distributions.ipynb", "variance.ipynb", "covariance-and-correlation.ipynb", "lotus.ipynb",
        "conditional-expectation.ipynb", "moment-generating-functions.ipynb", "joint-distribution.ipynb", "independence-of-rvs.ipynb",
        "functions-of-random-variables.ipynb", "transformations-and-convolutions.ipynb", "probability-density-function.ipynb",
        "uniform-distribution.ipynb", "exponential-distribution.ipynb", "gamma-function-and-distribution.ipynb", "beta-distribution.ipynb",
        "normal-distribution.ipynb", "multivariate-normal-distribution.ipynb", "Cauchy-distribution.ipynb", "student-t-distribution.ipynb",
        "chi-square-distribution.ipynb", "order-statistics.ipynb"
    ],
    "Inequalities & Limit Theorems": [
        "markovs-inequality.ipynb", "chebyshevs-inequality.ipynb", "jensens-inequality.ipynb", "Cauchy-Schwarz-inequality.ipynb",
        "law-of-large-numbers-and-central-limit-theorem.ipynb", "borel-cantelli-lemma.ipynb", "probabilistic-for-existence-proof.ipynb"
    ],
    "Stochastic Processes": [
        "stochastic-processes-foundations.ipynb", "gamblers-ruin.ipynb", "branching-process.ipynb", "brownian-motion.ipynb", "gaussian-processes.ipynb"
    ],
    "Mathematical Finance & Portfolio Theory": [
        "stochastic-models-in-finance.ipynb", "single-period-investment-model.ipynb", "markowitz-portfolio-theory-2-assets.ipynb",
        "risk-measures.ipynb", "cs-mab-signal-selection.ipynb", "cs-emh-btc-ma-model.ipynb"
    ],
    "Time Series Analysis": [
        "time-series-returns.ipynb", "autocorrelation-and-stationarity.ipynb", "autoregressive-models.ipynb", "moving-average-models.ipynb",
        "arma-models.ipynb", "arch-and-garch-models.ipynb", "vector-autoregressive-models.ipynb", "vector-moving-average.ipynb",
        "augmented-dickey-fuller-test.ipynb", "cointegration.ipynb", "multivariate-time-series.ipynb"
    ],
    "Difference Equations & Dynamics": [
        "intro-to-difference-equations.ipynb", "first-order-linear-difference-equations-and-equilibriums.ipynb",
        "second-order-linear-difference-equations.ipynb"
    ],
    "Optimization & Linear Programming": [
        "linear-programs.ipynb", "polyhedra-and-polytopes.ipynb", "convex-sets-and-convex-hulls.ipynb", "hyperplane-separation-theorems.ipynb",
        "lagrangian-and-kkt-conditions.ipynb"
    ],
    "Statistical Inference & Estimation": [
        "maximum-likelihood-estimation.ipynb", "statistical-inference.ipynb"
    ]
}

# Dynamic topic discovery keywords for newly added notes (e.g. number theory, algebra, etc.)
DYNAMIC_PATTERNS = {
    "Number Theory": [r"\bprime\b", r"\bmodulo\b", r"\bcongruence\b", r"\bgcd\b", r"\bdivisib", r"\bdiophantine\b", r"\beuler-totient\b", r"\bnumber-theory\b", r"\bfermat\b", r"\bcoprime\b", r"\beuler\b"],
    "Complex Analysis": [r"\bcomplex\b", r"\bholomorphic\b", r"\banalytic\b", r"\bcauchy-riemann\b", r"\bresidue\b", r"\bcontour\b", r"\blaurent\b", r"\bmeromorphic\b"],
    "Abstract Algebra": [r"\bgroup\b", r"\bring\b", r"\bfield-theory\b", r"\bhomomorphism\b", r"\bisomorphism\b", r"\bideal\b", r"\bgalois\b", r"\bsubgroup\b", r"\bcoset\b"],
    "Linear Algebra": [r"\beigenvalue\b", r"\beigenvector\b", r"\bmatrix\b", r"\bdeterminant\b", r"\bvector-space\b", r"\blinear-transformation\b", r"\bsvd\b"],
    "Graph Theory": [r"\bgraph\b", r"\bvertex\b", r"\bvertices\b", r"\bedge\b", r"\badjacency\b", r"\btrees?\b", r"\bbipartite\b", r"\bchromatic\b"],
    "Differential Equations": [r"\bdifferential-equation\b", r"\bpde\b", r"\bode\b", r"\blaplace\b", r"\bfourier\b", r"\bboundary-value\b"]
}

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

# Auto-classify any unmapped note (existing or newly added)
for f in files:
    if f not in file_to_domain:
        if f.startswith("pset-"):
            if "real-numbers" in f or "real" in f:
                file_to_domain[f] = "Real Analysis (Foundations & Sequences)"
            elif "topology" in f:
                file_to_domain[f] = "Metric Spaces & Topology"
            elif "function-spaces" in f:
                file_to_domain[f] = "Function Spaces & Fixed Points"
            elif "cond-prob" in f or "discrete-rvs" in f or "rvs" in f:
                file_to_domain[f] = "Probability Foundations & Combinatorics"
            elif "linear-programs" in f or "opt" in f:
                file_to_domain[f] = "Optimization & Linear Programming"
            elif "stat" in f:
                file_to_domain[f] = "Statistical Inference & Estimation"
            elif "time-series" in f:
                file_to_domain[f] = "Time Series Analysis"
            elif "stochastic" in f:
                file_to_domain[f] = "Stochastic Processes"
            else:
                # Inherit from first target
                targets = outgoing[f]
                if targets and targets[0] in file_to_domain:
                    file_to_domain[f] = file_to_domain[targets[0]]
                else:
                    file_to_domain[f] = "Problem Set"
        else:
            # Check frontmatter category/domain first
            content = file_contents.get(f, "")
            fm_match = re.search(r"category:\s*[\"']?(.*?)[\"']?\n", content) or re.search(r"domain:\s*[\"']?(.*?)[\"']?\n", content)
            if fm_match:
                file_to_domain[f] = fm_match.group(1).strip()
            else:
                # Pattern match across filename and content
                matched = False
                text_to_check = (f + " " + content[:2000]).lower()
                for topic, regex_list in DYNAMIC_PATTERNS.items():
                    for r in regex_list:
                        if re.search(r, text_to_check):
                            file_to_domain[f] = topic
                            matched = True
                            break
                    if matched:
                        break
                
                if not matched:
                    # Neighbor majority voting
                    neighbor_domains = [file_to_domain[t] for t in outgoing[f] if t in file_to_domain] + \
                                       [file_to_domain[s] for s in incoming[f] if s in file_to_domain]
                    if neighbor_domains:
                        file_to_domain[f] = max(set(neighbor_domains), key=neighbor_domains.count)
                    else:
                        file_to_domain[f] = "General Mathematics"

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

# ─────────────────────────────────────────────────────────────
# 7. GENERATE STUDY FOCUS & COVERAGE DASHBOARD (`coverage_output.html`)
# ─────────────────────────────────────────────────────────────
total_regular = len(regular_notes)
total_psets_count = len(psets)
num_direct = len(direct_covered)
num_transitive = len(distance_from_pset) - len(direct_covered)
num_uncovered = total_regular - len(distance_from_pset)
total_practiced = num_direct + num_transitive
overall_coverage_pct = (total_practiced / max(1, total_regular)) * 100
direct_coverage_pct = (num_direct / max(1, total_regular)) * 100

# Domain breakdown objects
domain_breakdown = []
for dom, stats in domain_counts.items():
    tot = stats["total"]
    d = stats["direct"]
    t = stats["transitive"]
    u = stats["uncovered"]
    cov_pct = ((d + t) / max(1, tot)) * 100
    dir_pct = (d / max(1, tot)) * 100
    domain_breakdown.append({
        "domain": dom,
        "total": tot,
        "direct": d,
        "transitive": t,
        "uncovered": u,
        "coverage_pct": round(cov_pct, 1),
        "direct_pct": round(dir_pct, 1)
    })
domain_breakdown.sort(key=lambda x: (x["coverage_pct"], -x["total"]))

dashboard_json_data = json.dumps({
    "kpis": {
        "total_notes": total_regular,
        "total_psets": total_psets_count,
        "direct_count": num_direct,
        "transitive_count": num_transitive,
        "uncovered_count": num_uncovered,
        "overall_coverage_pct": round(overall_coverage_pct, 1),
        "direct_coverage_pct": round(direct_coverage_pct, 1)
    },
    "domains": domain_breakdown,
    "priorities": priority_list[:20],
    "all_notes": priority_list
})

html_coverage_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Study Focus & Knowledge Coverage</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Source+Sans+3:ital,wght@0,300;0,400;0,600;0,700;1,400&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #ffffff;
      --card-bg: #ffffff;
      --text-main: #212529;
      --text-muted: #6c757d;
      --border-color: #dee2e6;
      --border-light: #e9ecef;
      --purple: #8e44ad;
      --green: #27ae60;
      --amber: #d35400;
      --red: #c0392b;
      --blue: #2980b9;
      --font-kb: "Source Sans 3", "Source Sans Pro", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }}
    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}
    body, html, input, select, button, table, td, th {{
      font-family: var(--font-kb);
    }}
    body {{
      background-color: var(--bg);
      color: var(--text-main);
      line-height: 1.5;
      padding: 12px 16px;
    }}
    .dashboard-container {{
      max-width: 1220px;
      margin: 0 auto;
    }}

    /* KPI Cards */
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 14px;
      margin-bottom: 24px;
    }}
    .kpi-card {{
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 6px;
      padding: 14px 18px;
      box-shadow: 0 1px 2px rgba(0,0,0,0.02);
      position: relative;
      overflow: hidden;
    }}
    .kpi-card::before {{
      content: "";
      position: absolute;
      top: 0;
      left: 0;
      width: 4px;
      height: 100%;
    }}
    .kpi-card.purple::before {{ background: var(--purple); }}
    .kpi-card.green::before {{ background: var(--green); }}
    .kpi-card.amber::before {{ background: var(--amber); }}
    .kpi-card.red::before {{ background: var(--red); }}
    .kpi-card.blue::before {{ background: var(--blue); }}

    .kpi-label {{
      font-family: var(--font-kb);
      font-size: 11.5px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
      margin-bottom: 4px;
    }}
    .kpi-value {{
      font-size: 24px;
      font-family: var(--font-kb);
      font-weight: bold;
      color: #111;
    }}
    .kpi-subtext {{
      font-family: var(--font-kb);
      font-size: 11.5px;
      color: var(--text-muted);
      margin-top: 3px;
    }}

    /* Main Grid Sections */
    .dashboard-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
      margin-bottom: 24px;
    }}
    @media (max-width: 900px) {{
      .dashboard-grid {{
        grid-template-columns: 1fr;
      }}
    }}

    .section-card {{
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 6px;
      padding: 18px;
      box-shadow: 0 1px 2px rgba(0,0,0,0.02);
    }}
    .section-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 14px;
      padding-bottom: 8px;
      border-bottom: 1px solid var(--border-light);
    }}
    .section-title {{
      font-family: var(--font-kb);
      font-size: 17px;
      font-weight: 600;
      color: #222;
    }}
    .section-badge {{
      font-family: var(--font-kb);
      font-size: 11px;
      background: #f8f9fa;
      color: #495057;
      border: 1px solid var(--border-light);
      padding: 2px 8px;
      border-radius: 12px;
      font-weight: 500;
    }}

    /* Topic Progress Bars */
    .domain-list {{
      display: flex;
      flex-direction: column;
      gap: 11px;
      max-height: 420px;
      overflow-y: auto;
      padding-right: 4px;
    }}
    .domain-row {{
      cursor: pointer;
      padding: 3px 6px;
      border-radius: 4px;
      transition: background 0.15s;
    }}
    .domain-row:hover {{
      background: #f8f9fa;
    }}
    .domain-info {{
      display: flex;
      justify-content: space-between;
      font-size: 13px;
      margin-bottom: 4px;
    }}
    .domain-name {{
      font-weight: 600;
      color: #2c3e50;
      font-family: var(--font-kb);
    }}
    .domain-pct {{
      font-family: var(--font-kb);
      color: #111;
      font-weight: bold;
      font-size: 12.5px;
    }}
    .progress-bar-container {{
      height: 8px;
      background: #e9ecef;
      border-radius: 4px;
      overflow: hidden;
      display: flex;
    }}
    .bar-direct {{
      background: var(--green);
      height: 100%;
      transition: width 0.3s;
    }}
    .bar-transitive {{
      background: var(--amber);
      height: 100%;
      transition: width 0.3s;
    }}
    .bar-uncovered {{
      background: #e9ecef;
      height: 100%;
    }}
    .progress-legend {{
      display: flex;
      gap: 14px;
      font-family: var(--font-kb);
      font-size: 11px;
      color: var(--text-muted);
      margin-top: 12px;
      padding-top: 8px;
      border-top: 0.5px dashed var(--border-light);
    }}
    .legend-dot-inline {{
      width: 8px;
      height: 8px;
      border-radius: 50%;
      display: inline-block;
      margin-right: 4px;
    }}

    /* Priority Practice Queue */
    .priority-list {{
      display: flex;
      flex-direction: column;
      gap: 9px;
      max-height: 420px;
      overflow-y: auto;
      padding-right: 4px;
    }}
    .priority-item {{
      border: 1px solid var(--border-light);
      border-radius: 5px;
      padding: 9px 12px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: #fff;
      transition: border-color 0.15s, background 0.15s;
    }}
    .priority-item:hover {{
      border-color: #ced4da;
      background: #fdfdfd;
    }}
    .priority-item-left {{
      flex: 1;
      min-width: 0;
    }}
    .priority-name {{
      font-family: var(--font-kb);
      font-weight: 600;
      font-size: 14px;
      color: #1e293b;
      text-decoration: none;
      display: block;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .priority-name:hover {{
      color: var(--blue);
      text-decoration: underline;
    }}
    .priority-meta {{
      font-family: var(--font-kb);
      display: flex;
      gap: 8px;
      font-size: 11px;
      color: var(--text-muted);
      margin-top: 2px;
    }}
    .priority-item-right {{
      display: flex;
      align-items: center;
      margin-left: 10px;
    }}
    .score-badge {{
      font-family: var(--font-kb);
      font-size: 11.5px;
      font-weight: bold;
      background: #fff5f5;
      color: var(--red);
      padding: 1px 7px;
      border-radius: 10px;
      border: 1px solid #fed7d7;
    }}

    /* Table Explorer Section */
    .table-section {{
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 6px;
      padding: 18px;
      box-shadow: 0 1px 2px rgba(0,0,0,0.02);
    }}
    .table-controls {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-bottom: 14px;
      justify-content: space-between;
      align-items: center;
    }}
    .filter-tabs {{
      display: flex;
      gap: 5px;
      flex-wrap: wrap;
    }}
    .tab-btn {{
      font-family: var(--font-kb);
      background: #f8f9fa;
      border: 1px solid var(--border-light);
      padding: 4px 10px;
      border-radius: 5px;
      font-size: 12px;
      cursor: pointer;
      color: #495057;
      transition: all 0.15s;
    }}
    .tab-btn:hover {{
      background: #e9ecef;
    }}
    .tab-btn.active {{
      background: #212529;
      color: #fff;
      border-color: #212529;
      font-weight: 500;
    }}
    .filter-inputs {{
      display: flex;
      gap: 8px;
    }}
    .search-input {{
      font-family: var(--font-kb);
      font-style: italic;
      padding: 5px 10px;
      border: 1px solid var(--border-color);
      border-radius: 5px;
      font-size: 12.5px;
      outline: none;
      width: 200px;
    }}
    .search-input:focus {{
      border-color: #495057;
    }}
    .domain-select {{
      font-family: var(--font-kb);
      padding: 5px 8px;
      border: 1px solid var(--border-color);
      border-radius: 5px;
      font-size: 12.5px;
      background: #fff;
      outline: none;
    }}

    /* Note Table */
    .table-responsive {{
      overflow-x: auto;
      max-height: 500px;
    }}
    table.notes-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      text-align: left;
    }}
    table.notes-table th {{
      position: sticky;
      top: 0;
      background: #f8f9fa;
      padding: 8px 10px;
      font-family: var(--font-kb);
      font-weight: 600;
      color: #333;
      border-bottom: 1.5px solid var(--border-color);
      font-size: 12px;
      letter-spacing: 0.02em;
    }}
    table.notes-table td {{
      padding: 7px 10px;
      border-bottom: 1px solid #f1f3f5;
      color: #212529;
    }}
    table.notes-table tr:hover td {{
      background: #f8f9fa;
    }}
    .note-link {{
      font-weight: 600;
      color: #212529;
      text-decoration: none;
      font-family: var(--font-kb);
    }}
    .note-link:hover {{
      color: var(--blue);
      text-decoration: underline;
    }}
    .status-pill {{
      font-family: var(--font-kb);
      display: inline-block;
      padding: 1px 7px;
      border-radius: 10px;
      font-size: 10.5px;
      font-weight: 600;
    }}
    .status-pill.direct {{
      background: #d4edda;
      color: #155724;
    }}
    .status-pill.transitive {{
      background: #fff3cd;
      color: #856404;
    }}
    .status-pill.uncovered {{
      background: #f8d7da;
      color: #721c24;
    }}
    .psets-tag-list {{
      display: flex;
      flex-wrap: wrap;
      gap: 3px;
    }}
    .pset-tag {{
      font-family: var(--font-kb);
      background: #f3e8ff;
      color: #6b21a8;
      font-size: 10px;
      padding: 1px 5px;
      border-radius: 3px;
    }}
  </style>
</head>
<body>
  <div class="dashboard-container">
    <!-- Hero KPIs -->
    <div class="kpi-grid">
      <div class="kpi-card purple">
        <div class="kpi-label">Problem Sets Active</div>
        <div class="kpi-value">{total_psets_count}</div>
        <div class="kpi-subtext">{num_direct} direct nodes tested</div>
      </div>
      <div class="kpi-card green">
        <div class="kpi-label">Direct Practice Rate</div>
        <div class="kpi-value">{direct_coverage_pct:.1f}%</div>
        <div class="kpi-subtext">{num_direct} / {total_regular} notes tested directly</div>
      </div>
      <div class="kpi-card amber">
        <div class="kpi-label">Prerequisites Touched</div>
        <div class="kpi-value">{num_transitive}</div>
        <div class="kpi-subtext">Foundational concepts in problem paths</div>
      </div>
      <div class="kpi-card red">
        <div class="kpi-label">Uncovered Notes</div>
        <div class="kpi-value">{num_uncovered}</div>
        <div class="kpi-subtext">{(num_uncovered/total_regular)*100:.1f}% of KB requires problem coverage</div>
      </div>
      <div class="kpi-card blue">
        <div class="kpi-label">Total Knowledge Nodes</div>
        <div class="kpi-value">{total_regular}</div>
        <div class="kpi-subtext">Across {len(domain_counts)} fine-resolution topics</div>
      </div>
    </div>

    <!-- 2-Column Analytics Grid -->
    <div class="dashboard-grid">
      <!-- Domain Breakdown Progress -->
      <div class="section-card">
        <div class="section-header">
          <h2 class="section-title">Topic Practice Coverage</h2>
          <span class="section-badge">Sorted by Practice Urgency</span>
        </div>
        <div class="domain-list" id="domain-list-container">
          <!-- Rendered via JS -->
        </div>
        <div class="progress-legend">
          <span><span class="legend-dot-inline" style="background:var(--green)"></span>Directly Tested</span>
          <span><span class="legend-dot-inline" style="background:var(--amber)"></span>Prerequisites</span>
          <span><span class="legend-dot-inline" style="background:#e9ecef"></span>Uncovered</span>
        </div>
      </div>

      <!-- Priority Queue: Where to Focus Next -->
      <div class="section-card">
        <div class="section-header">
          <h2 class="section-title">Where to Focus Next</h2>
          <span class="section-badge" style="background:#fff5f5; color:#c53030;">High Impact Targets</span>
        </div>
        <div class="priority-list" id="priority-queue-container">
          <!-- Rendered via JS -->
        </div>
      </div>
    </div>

    <!-- Interactive Note Explorer Table -->
    <div class="table-section">
      <div class="section-header">
        <h2 class="section-title">Note Coverage Matrix</h2>
        <span class="section-badge" id="table-count-badge">Showing {total_regular} Notes</span>
      </div>

      <div class="table-controls">
        <div class="filter-tabs">
          <button class="tab-btn active" onclick="setFilterStatus('all')">All Notes ({total_regular})</button>
          <button class="tab-btn" onclick="setFilterStatus('uncovered')">Uncovered ({num_uncovered})</button>
          <button class="tab-btn" onclick="setFilterStatus('transitive')">Prerequisites ({num_transitive})</button>
          <button class="tab-btn" onclick="setFilterStatus('direct')">Directly Practiced ({num_direct})</button>
        </div>
        <div class="filter-inputs">
          <select id="domain-filter-select" class="domain-select" onchange="onFilterChange()">
            <option value="all">All Topics</option>
          </select>
          <input type="text" id="note-search-input" class="search-input" placeholder="Search notes..." oninput="onFilterChange()" />
        </div>
      </div>

      <div class="table-responsive">
        <table class="notes-table">
          <thead>
            <tr>
              <th>Note Name</th>
              <th>Topic</th>
              <th>Status</th>
              <th style="text-align:center;">Usages</th>
              <th style="text-align:center;">Prerequisites</th>
              <th>Problem Sets Covering Concept</th>
            </tr>
          </thead>
          <tbody id="notes-table-body">
            <!-- Rendered via JS -->
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <script>
    const data = {dashboard_json_data};
    let currentStatusFilter = 'all';

    // 1. Populate Domain Progress Bars
    function renderDomainBars() {{
      const container = document.getElementById('domain-list-container');
      const select = document.getElementById('domain-filter-select');
      container.innerHTML = '';
      
      data.domains.forEach(d => {{
        const opt = document.createElement('option');
        opt.value = d.domain;
        opt.textContent = d.domain;
        select.appendChild(opt);

        const directW = (d.direct / d.total) * 100;
        const transW = (d.transitive / d.total) * 100;
        const uncovW = (d.uncovered / d.total) * 100;

        const row = document.createElement('div');
        row.className = 'domain-row';
        row.onclick = () => {{
          select.value = d.domain;
          onFilterChange();
        }};
        row.innerHTML = `
          <div class="domain-info">
            <span class="domain-name">${{d.domain}}</span>
            <span class="domain-pct">${{d.coverage_pct}}% <span style="font-weight:normal; font-size:11px; color:#777;">(${{d.direct + d.transitive}}/${{d.total}})</span></span>
          </div>
          <div class="progress-bar-container">
            <div class="bar-direct" style="width: ${{directW}}%" title="Direct: ${{d.direct}} (${{directW.toFixed(1)}}%)"></div>
            <div class="bar-transitive" style="width: ${{transW}}%" title="Prerequisites: ${{d.transitive}} (${{transW.toFixed(1)}}%)"></div>
            <div class="bar-uncovered" style="width: ${{uncovW}}%" title="Uncovered: ${{d.uncovered}} (${{uncovW.toFixed(1)}}%)"></div>
          </div>
        `;
        container.appendChild(row);
      }});
    }}

    // 2. Populate Priority Queue
    function renderPriorityQueue() {{
      const container = document.getElementById('priority-queue-container');
      container.innerHTML = '';

      data.priorities.forEach((p, idx) => {{
        const item = document.createElement('div');
        item.className = 'priority-item';
        item.innerHTML = `
          <div class="priority-item-left">
            <a href="nodes/${{p.id.replace('.ipynb', '.html')}}" target="_top" class="priority-name">
              #${{idx + 1}}. ${{p.name}}
            </a>
            <div class="priority-meta">
              <span><b>${{p.domain}}</b></span>
              <span>•</span>
              <span>Used by <b>${{p.usages}}</b> notes</span>
              <span>•</span>
              <span><b>${{p.prelims}}</b> prerequisites</span>
            </div>
          </div>
          <div class="priority-item-right">
            <span class="score-badge">${{p.score}} pts</span>
          </div>
        `;
        container.appendChild(item);
      }});
    }}

    // 3. Populate Notes Table with Dynamic Filtering
    function renderNotesTable() {{
      const tbody = document.getElementById('notes-table-body');
      const badge = document.getElementById('table-count-badge');
      const query = document.getElementById('note-search-input').value.trim().toLowerCase();
      const domainFilter = document.getElementById('domain-filter-select').value;

      tbody.innerHTML = '';

      const filtered = data.all_notes.filter(n => {{
        if (currentStatusFilter !== 'all' && n.status !== currentStatusFilter) return false;
        if (domainFilter !== 'all' && n.domain !== domainFilter) return false;
        if (query && !n.name.toLowerCase().includes(query) && !n.domain.toLowerCase().includes(query)) return false;
        return true;
      }});

      badge.textContent = `Showing ${{filtered.length}} / ${{data.all_notes.length}} Notes`;

      if (filtered.length === 0) {{
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:#888; padding:20px; font-style:italic;">No notes match the selected filters.</td></tr>';
        return;
      }}

      filtered.forEach(n => {{
        const tr = document.createElement('tr');
        
        let statusBadge = '';
        if (n.status === 'direct') {{
          statusBadge = '<span class="status-pill direct">Direct</span>';
        }} else if (n.status === 'transitive') {{
          statusBadge = `<span class="status-pill transitive">Prerequisite</span>`;
        }} else {{
          statusBadge = '<span class="status-pill uncovered">Uncovered</span>';
        }}

        let psetsHtml = '-';
        if (n.covering_psets && n.covering_psets.length > 0) {{
          psetsHtml = '<div class="psets-tag-list">' + n.covering_psets.map(p => `<span class="pset-tag">${{p}}</span>`).join('') + '</div>';
        }}

        tr.innerHTML = `
          <td><a href="nodes/${{n.id.replace('.ipynb', '.html')}}" target="_top" class="note-link">${{n.name}}</a></td>
          <td style="font-size:12px; color:#555;">${{n.domain}}</td>
          <td>${{statusBadge}}</td>
          <td style="text-align:center;">${{n.usages}}</td>
          <td style="text-align:center;">${{n.prelims}}</td>
          <td>${{psetsHtml}}</td>
        `;
        tbody.appendChild(tr);
      }});
    }}

    function setFilterStatus(status) {{
      currentStatusFilter = status;
      document.querySelectorAll('.filter-tabs .tab-btn').forEach(btn => {{
        btn.classList.remove('active');
      }});
      event.target.classList.add('active');
      renderNotesTable();
    }}

    function onFilterChange() {{
      renderNotesTable();
    }}

    // Init
    renderDomainBars();
    renderPriorityQueue();
    renderNotesTable();
  </script>
</body>
</html>
"""

with open("coverage_output.html", "w", encoding="utf-8") as f:
    f.write(html_coverage_content)

print(f"Coverage & Knowledge Graph generated successfully!")
print(f"  • Fine topics count: {len(domain_counts)}")
for item in domain_breakdown:
    print(f"    - {item['domain']}: {item['total']} notes ({item['coverage_pct']}% covered)")