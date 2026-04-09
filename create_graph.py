import os
import re
import json
from pyvis.network import Network

net = Network(
    height="100vh",
    width="100%",
    notebook=False,
    directed=True,
    cdn_resources="in_line",
    bgcolor="#ffffff",
    font_color="#111111",
)

node_path = "nodes"
files = sorted([f for f in os.listdir(node_path) if f.endswith(".ipynb")])

# --- Nodes ---
for f in files:
    label = f.replace(".ipynb", "").replace("-", " ").title()
    url = f"nodes/{f.replace('.ipynb', '.html')}"

    net.add_node(
        f,
        label=label,
        title=f"<b>{label}</b><br>Click to open",
        url=url,
    )

# --- Edges ---
for f in files:
    with open(os.path.join(node_path, f), "r", encoding="utf-8") as file:
        content = file.read()
        links = re.findall(r"\]\((.*?\.ipynb)", content)

        for link in links:
            target = os.path.basename(link)
            if target in files:
                net.add_edge(target, f)

# --- Styling (UPGRADED) ---
options = {
    "layout": {
        "improvedLayout": True
    },
    "nodes": {
        "shape": "dot",
        "size": 14,
        "borderWidth": 1.5,

        "color": {
            "border": "#2c2c2c",
            "background": "#ffffff",
            "highlight": {"border": "#000000", "background": "#f5f5f5"},
            "hover": {"border": "#000000", "background": "#f0f0f0"},
        },

        "font": {
            "size": 16,
            "color": "#111111",
            "face": "Times New Roman",
            "strokeWidth": 0,
        },
    },

    "edges": {
        "arrows": {
            "to": {"enabled": True, "scaleFactor": 0.6}
        },
        "width": 1,
        "color": {
            "color": "#999999",
            "highlight": "#000000",
            "hover": "#000000",
        },
        "smooth": {
            "type": "cubicBezier",
            "roundness": 0.2,
        },
    },

    "interaction": {
        "hover": True,
        "tooltipDelay": 120,
        "zoomView": True,
        "dragView": True,
    },
    "physics": {
        "stabilization": {
            "enabled": True,
            "iterations": 500
        },
        "barnesHut": {
            "gravitationalConstant": -150000,   # 🔥 much stronger repulsion
            "centralGravity": 0.1,            # ⬅️ reduce pull to center
            "springLength": 70,                # ⬅️ longer edges = more spread
            "springConstant": 0.015,
            "damping": 0.35,
            "avoidOverlap": 100                  # ✅ important
        },
        "minVelocity": 0.75
    }
}

net.set_options(json.dumps(options))
net.save_graph("graph_output.html")

# --- Post-process HTML ---
with open("graph_output.html", "r", encoding="utf-8") as f:
    html_content = f.read()

# ✅ Robust navigation fix
click_script = """
network.on("click", function (params) {
    if (params.nodes.length > 0) {
        var nodeId = params.nodes[0];
        var nodeData = nodes.get(nodeId);

        if (nodeData && nodeData.url) {
            // 🔥 always escape iframe / Quarto embedding
            window.top.location.href = nodeData.url;
        }
    }
});
"""

# ✅ Clean academic styling
css_tune = """
<style>
  html, body {
    margin: 0;
    padding: 0;
    background: #ffffff;
    font-family: "Times New Roman", serif;
  }

  #mynetwork {
    border: none !important;
  }

  canvas {
    background-color: #ffffff !important;
  }
</style>
"""

html_content = html_content.replace("</head>", css_tune + "\n</head>")
html_content = html_content.replace("</body>", f"<script>{click_script}</script></body>")

with open("graph_output.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("Clean math knowledge graph generated!")