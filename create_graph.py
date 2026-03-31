import os

import re

import json

from pyvis.network import Network



net = Network(

    height="700px",

    width="100%",

    notebook=False,

    directed=True,

    cdn_resources="in_line",

    bgcolor="#ffffff",      # white background

    font_color="#111111",   # dark text

)



node_path = "nodes"

files = sorted([f for f in os.listdir(node_path) if f.endswith(".ipynb")])



for f in files:

    label = f.replace(".ipynb", "").replace("-", " ").title()

    url = f"nodes/{f.replace('.ipynb', '.html')}"

    net.add_node(

        f,

        label=label,

        title=f"Click to open {label}",

        url=url,

    )



for f in files:

    with open(os.path.join(node_path, f), "r", encoding="utf-8") as file:

        content = file.read()

        links = re.findall(r"\]\((.*?\.ipynb)", content)

        for link in links:

            target = os.path.basename(link)

            if target in files:

                net.add_edge(target, f, color="#444444")



options = {

    "layout": {"improvedLayout": True},

    "nodes": {

        "shape": "dot",

        "size": 16,

        "borderWidth": 2,

        "color": {

            "border": "#111111",

            "background": "#ffffff",

            "highlight": {"border": "#111111", "background": "#f2f2f2"},

            "hover": {"border": "#111111", "background": "#f2f2f2"},

        },

        "font": {

            "size": 15,

            "color": "#111111",

            "face": "Times New Roman",

        },

    },

    "edges": {

        "arrows": {"to": {"enabled": True, "scaleFactor": 0.7}},

        "width": 1.2,

        "color": {

            "color": "#444444",

            "highlight": "#111111",

            "hover": "#111111",

        },

        "smooth": {"type": "continuous"},

    },

    "interaction": {

        "hover": True,

        "tooltipDelay": 150,

        "navigationButtons": False,  # remove bottom navigation buttons

    },

    "physics": {

        "stabilization": {"iterations": 250},

        "barnesHut": {

            "gravitationalConstant": -6000,

            "springLength": 150,

            "springConstant": 0.02,

            "damping": 0.25,

        },

    },

}





net.set_options(json.dumps(options))

net.save_graph("graph_output.html")



with open("graph_output.html", "r", encoding="utf-8") as f:

    html_content = f.read()



# KEEP your click behavior exactly as-is

click_script = """

    network.on("click", function (params) {

        if (params.nodes.length > 0) {

            var nodeId = params.nodes[0];

            var nodeData = nodes.get(nodeId);

            if (nodeData && nodeData.url) {

                window.parent.location.href = nodeData.url;

            }

        }

    });

"""



# Optional: make the embed cleaner in Quarto by removing margins (style-only)

css_tune = """

<style>

  html, body { margin: 0; padding: 0; background: #fff; }

  #mynetwork { border: 0 !important; }

</style>

"""



if "</head>" in html_content:

    html_content = html_content.replace("</head>", css_tune + "\n</head>")

else:

    html_content = css_tune + html_content



html_content = html_content.replace("</body>", f"<script>{click_script}</script></body>")



with open("graph_output.html", "w", encoding="utf-8") as f:

    f.write(html_content)