import os
import re
import json
from collections import defaultdict

node_path = "nodes"
files = sorted([f for f in os.listdir(node_path) if f.endswith(".ipynb")])

# Build edges
links = []
incoming = defaultdict(list)
outgoing = defaultdict(list)

for f in files:
    with open(os.path.join(node_path, f), "r", encoding="utf-8") as file:
        content = file.read()
        extracted_links = re.findall(r"\]\((.*?\.ipynb)", content)
        
        for link in extracted_links:
            target = os.path.basename(link)
            if target in files:
                links.append({"source": f, "target": target})
                outgoing[f].append(target)
                incoming[target].append(f)

# Build nodes
nodes = []
for f in files:
    label = f.replace(".ipynb", "").replace("-", " ").title()
    url = f"nodes/{f.replace('.ipynb', '.html')}"
    
    # Swapped: Outgoing links are what this node uses (preliminaries)
    # Incoming links are the nodes that use this node (usages)
    prelims = [p.replace(".ipynb", "").replace("-", " ").title() for p in outgoing[f]]
    usages = [u.replace(".ipynb", "").replace("-", " ").title() for u in incoming[f]]
    
    nodes.append({
        "id": f,
        "name": label,
        "url": url,
        "prelims": prelims,
        "usages": usages
    })

graph_data = {"nodes": nodes, "links": links}
json_data = json.dumps(graph_data)

# Generate HTML
html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Knowledge Graph</title>
  <script src="https://unpkg.com/force-graph"></script>
  <style>
    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}
    body {{
      background-color: #f8f9fa;
      font-family: "Times New Roman", Times, serif;
      overflow: hidden;
    }}
    #graph-container {{
      width: 100vw;
      height: 100vh;
    }}

    /* ── Search bar overlay (LaTeX-book style) ── */
    #search-wrapper {{
      position: fixed;
      top: 16px;
      right: 18px;
      z-index: 1000;
      width: min(280px, 70vw);
      opacity: 0.35;
      transition: opacity 0.3s ease;
    }}
    #search-wrapper:hover,
    #search-wrapper.active {{
      opacity: 1;
    }}
    #search-label {{
      display: block;
      font-family: "Times New Roman", "CMU Serif", "Latin Modern Roman", Georgia, serif;
      font-size: 11px;
      font-variant: small-caps;
      letter-spacing: 0.06em;
      color: #444;
      margin-bottom: 3px;
      padding-left: 2px;
      user-select: none;
    }}
    #search-input {{
      width: 100%;
      padding: 7px 10px;
      font-size: 14px;
      font-family: "Times New Roman", "CMU Serif", "Latin Modern Roman", Georgia, serif;
      font-style: italic;
      color: #222;
      border: none;
      border-bottom: 1.2px solid #555;
      border-radius: 0;
      background: transparent;
      outline: none;
      transition: border-color 0.25s;
    }}
    #search-input::placeholder {{
      color: #999;
      font-style: italic;
    }}
    #search-input:focus {{
      border-bottom-color: #111;
    }}
    #search-results {{
      list-style: none;
      margin: 2px 0 0;
      padding: 0;
      background: rgba(255,255,253,0.95);
      border: 1px solid #bbb;
      border-top: none;
      max-height: 240px;
      overflow-y: auto;
      display: none;
    }}
    #search-results li {{
      padding: 7px 10px;
      cursor: pointer;
      font-size: 13px;
      font-family: "Times New Roman", "CMU Serif", Georgia, serif;
      color: #333;
      border-bottom: 0.5px solid #ddd;
      transition: background 0.15s, color 0.15s;
    }}
    #search-results li:last-child {{ border-bottom: none; }}
    #search-results li:hover,
    #search-results li.active {{
      background: rgba(0,0,0,0.06);
      color: #000;
    }}

    .node-tooltip {{
      background: rgba(255, 255, 255, 0.95);
      padding: 12px;
      border: 1px solid #ddd;
      border-radius: 4px;
      box-shadow: 0 4px 6px rgba(0,0,0,0.1);
      color: #333;
      max-width: 300px;
      font-size: 14px;
      line-height: 1.4;
      pointer-events: none;
    }}
    .node-tooltip h4 {{
      margin: 0 0 8px 0;
      font-size: 16px;
      border-bottom: 1px solid #eee;
      padding-bottom: 4px;
      color: #111;
    }}
    .node-tooltip .section-title {{
      font-weight: bold;
      color: #555;
      margin-top: 6px;
      display: block;
    }}
    .node-tooltip ul {{
      margin: 4px 0 0 0;
      padding-left: 20px;
    }}
    .node-tooltip li {{
      margin-bottom: 2px;
    }}
  </style>
</head>
<body>
  <!-- Search bar -->
  <div id="search-wrapper">
    <input id="search-input" type="text" placeholder="search\u2026" autocomplete="off" />
    <ul id="search-results"></ul>
  </div>

  <div id="graph-container"></div>
  <script>
    const gData = {json_data};

    // Cross-link node objects for highlighting
    gData.links.forEach(link => {{
      const a = gData.nodes.find(n => n.id === link.source);
      const b = gData.nodes.find(n => n.id === link.target);
      if(!a) return;
      if(!b) return;
      
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
    const highlightNodes = new Set();
    const highlightLinks = new Set();

    const container = document.getElementById('graph-container');
    const Graph = ForceGraph()(container)
      .width(container.offsetWidth)
      .height(container.offsetHeight)
      .graphData(gData)
      .backgroundColor('transparent')
      .nodeLabel(node => {{
        let html = '<div class="node-tooltip">';
        html += '<h4>' + node.name + '</h4>';
        
        if (node.prelims && node.prelims.length > 0) {{
            html += '<span class="section-title">Preliminaries:</span><ul>';
            node.prelims.forEach(p => {{ html += '<li>' + p + '</li>'; }});
            html += '</ul>';
        }}
        
        if (node.usages && node.usages.length > 0) {{
            html += '<span class="section-title">Usage:</span><ul>';
            node.usages.forEach(u => {{ html += '<li>' + u + '</li>'; }});
            html += '</ul>';
        }}
        
        html += '<br><small><i>Click to open</i></small>';
        html += '</div>';
        return html;
      }})
      .nodeCanvasObject((node, ctx, globalScale) => {{
          const isHighlighted = highlightNodes.has(node);
          const isFaded = hoverNode && !isHighlighted;
          const label = node.name;
          
          const fontSize = 4;
          ctx.font = `${{fontSize}}px "Times New Roman"`;

          ctx.beginPath();
          ctx.arc(node.x, node.y, 4, 0, 2 * Math.PI, false);
          ctx.fillStyle = isHighlighted ? '#3498db' : '#2c3e50';
          if(isFaded) ctx.fillStyle = 'rgba(44, 62, 80, 0.1)';
          ctx.fill();

          if (!isFaded || isHighlighted) {{
              ctx.textAlign = 'center';
              ctx.textBaseline = 'middle';
              ctx.fillStyle = isHighlighted ? '#2980b9' : '#333333';
              if(isFaded) ctx.fillStyle = 'rgba(51, 51, 51, 0.2)';
              ctx.fillText(label, node.x, node.y + 7);
          }}
      }})
      .nodePointerAreaPaint((node, color, ctx) => {{
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.arc(node.x, node.y, 6, 0, 2 * Math.PI, false);
          ctx.fill();
      }})
      .linkWidth(link => highlightLinks.has(link) ? 2 : 0.5)
      .linkColor(link => highlightLinks.has(link) ? '#3498db' : (hoverNode ? 'rgba(170, 183, 196, 0.1)' : 'rgba(170, 183, 196, 0.5)'))
      .linkDirectionalParticles(link => highlightLinks.has(link) ? 3 : 0)
      .linkDirectionalParticleWidth(3)
      .linkDirectionalArrowLength(3.5)
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
      
      // Physics tuning
      Graph.d3Force('charge').strength(-250);
      Graph.d3Force('link').distance(40);

      // Fit entire graph into view — called either when engine stops OR after a timeout
      let fitted = false;
      const doFit = () => {{
        if (!fitted) {{
          fitted = true;
          Graph.zoomToFit(400, 40);
        }}
      }};
      Graph.onEngineStop(doFit);
      // Fallback: if engine never fires (already settled), fit after 1.5s
      setTimeout(doFit, 1500);

      // Keep canvas sized to its container on resize
      window.addEventListener('resize', () => {{
        const w = container.clientWidth;
        const h = container.clientHeight;
        Graph.width(w).height(h);
        doFit();
      }});

      // ── Search bar logic ──
      const searchInput  = document.getElementById('search-input');
      const searchResults = document.getElementById('search-results');
      const searchWrapper = document.getElementById('search-wrapper');
      let activeIdx = -1;

      // Keep wrapper fully opaque while the input is focused
      searchInput.addEventListener('focus', () => searchWrapper.classList.add('active'));
      searchInput.addEventListener('blur', () => {{
        // Small delay so click events on results can fire first
        setTimeout(() => {{ if (document.activeElement !== searchInput) searchWrapper.classList.remove('active'); }}, 150);
      }});

      function renderResults(matches) {{
        searchResults.innerHTML = '';
        activeIdx = -1;
        if (matches.length === 0) {{ searchResults.style.display = 'none'; return; }}
        searchResults.style.display = 'block';
        matches.forEach((node, i) => {{
          const li = document.createElement('li');
          li.textContent = node.name;
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
        // Clear search UI
        searchInput.value = '';
        searchResults.style.display = 'none';
        searchInput.blur();

        // Highlight selected node + neighbors
        highlightNodes.clear();
        highlightLinks.clear();
        highlightNodes.add(node);
        if (node.neighbors) node.neighbors.forEach(n => highlightNodes.add(n));
        if (node.links) node.links.forEach(l => highlightLinks.add(l));
        hoverNode = node;

        // Zoom to the node
        Graph.centerAt(node.x, node.y, 600);
        Graph.zoom(6, 600);
      }}

      searchInput.addEventListener('input', () => {{
        const q = searchInput.value.trim().toLowerCase();
        if (!q) {{ searchResults.style.display = 'none'; return; }}
        const matches = gData.nodes.filter(n => n.name.toLowerCase().includes(q)).slice(0, 15);
        renderResults(matches);
      }});

      searchInput.addEventListener('keydown', (e) => {{
        const items = searchResults.querySelectorAll('li');
        if (e.key === 'ArrowDown')  {{ e.preventDefault(); activeIdx = Math.min(activeIdx + 1, items.length - 1); updateActive(); }}
        if (e.key === 'ArrowUp')    {{ e.preventDefault(); activeIdx = Math.max(activeIdx - 1, 0); updateActive(); }}
        if (e.key === 'Enter' && activeIdx >= 0) {{
          e.preventDefault();
          const q = searchInput.value.trim().toLowerCase();
          const matches = gData.nodes.filter(n => n.name.toLowerCase().includes(q)).slice(0, 15);
          if (matches[activeIdx]) selectNode(matches[activeIdx]);
        }}
        if (e.key === 'Escape') {{ searchResults.style.display = 'none'; searchInput.blur(); }}
      }});

      // Dismiss dropdown when clicking outside
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
    f.write(html_content)

print("Classy 2D math knowledge graph generated with responsive container and tighter edges!")