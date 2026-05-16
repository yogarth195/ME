import json
import pickle
from pathlib import Path

from flask import Blueprint, render_template_string

ontology_bp = Blueprint("ontology", __name__)

ONTOLOGY_PATH = Path(__file__).parent.parent.parent / "ontology" / "skill_ontology.gpickle"

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>ExplainHire — Ontology Explorer</title>
<script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', sans-serif; background: #0f1117; color: #e0e0e0; }

  header {
    padding: 16px 24px;
    background: #1a1d27;
    border-bottom: 1px solid #2a2d3e;
    display: flex;
    align-items: center;
    gap: 16px;
  }
  header h1 { font-size: 1.2rem; color: #7c83fd; }
  header span { font-size: 0.85rem; color: #888; }

  .controls {
    padding: 12px 24px;
    background: #13151f;
    border-bottom: 1px solid #2a2d3e;
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    align-items: center;
  }
  .controls input {
    padding: 7px 12px;
    background: #1e2130;
    border: 1px solid #3a3d52;
    border-radius: 6px;
    color: #e0e0e0;
    font-size: 0.9rem;
    width: 220px;
  }
  .controls select {
    padding: 7px 12px;
    background: #1e2130;
    border: 1px solid #3a3d52;
    border-radius: 6px;
    color: #e0e0e0;
    font-size: 0.9rem;
  }
  .controls label { font-size: 0.85rem; color: #aaa; }
  .btn {
    padding: 7px 16px;
    border-radius: 6px;
    border: none;
    cursor: pointer;
    font-size: 0.85rem;
    font-weight: 600;
  }
  .btn-primary { background: #7c83fd; color: #fff; }
  .btn-secondary { background: #2a2d3e; color: #ccc; }

  .stats {
    display: flex;
    gap: 24px;
    padding: 10px 24px;
    background: #13151f;
    border-bottom: 1px solid #2a2d3e;
    flex-wrap: wrap;
  }
  .stat { font-size: 0.82rem; color: #888; }
  .stat strong { color: #7c83fd; }

  #network {
    width: 100%;
    height: calc(100vh - 160px);
  }

  #tooltip {
    position: fixed;
    background: #1e2130;
    border: 1px solid #3a3d52;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 0.82rem;
    pointer-events: none;
    display: none;
    max-width: 260px;
    z-index: 999;
    line-height: 1.6;
  }
  #tooltip .skill-name { font-weight: 700; color: #7c83fd; font-size: 0.95rem; }
  #tooltip .domain-tag {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.75rem;
    margin-top: 4px;
  }
</style>
</head>
<body>

<header>
  <h1>ExplainHire — Ontology Explorer</h1>
  <span id="filter-label">Showing all {{ total_nodes }} skill nodes</span>
</header>

<div class="controls">
  <div>
    <label>Search skill</label><br>
    <input type="text" id="search" placeholder="e.g. pytorch, docker...">
  </div>
  <div>
    <label>Filter by domain</label><br>
    <select id="domain-filter">
      <option value="all">All domains</option>
      {% for d in domains %}
      <option value="{{ d }}">{{ d }}</option>
      {% endfor %}
    </select>
  </div>
  <div style="align-self:flex-end">
    <button class="btn btn-primary" onclick="applyFilters()">Apply</button>
    <button class="btn btn-secondary" onclick="resetFilters()">Reset</button>
  </div>
</div>

<div class="stats">
  <div class="stat">Skill nodes: <strong>{{ total_nodes }}</strong></div>
  <div class="stat">Alias nodes: <strong>{{ alias_nodes }}</strong></div>
  <div class="stat">CHILD_OF edges: <strong>{{ child_edges }}</strong></div>
  <div class="stat">IS_ALIAS_OF edges: <strong>{{ alias_edges }}</strong></div>
  <div class="stat">Domains: <strong>{{ domains|length }}</strong></div>
</div>

<div id="network"></div>
<div id="tooltip"></div>

<script>
const graphData = {{ graph_json | safe }};

const DOMAIN_COLORS = {
  ml_ds:       { bg: "#3b2f6e", border: "#7c83fd", text: "#b8bcff" },
  web:         { bg: "#1e3a2f", border: "#4ade80", text: "#86efac" },
  devops:      { bg: "#3a2a1a", border: "#fb923c", text: "#fdba74" },
  cloud:       { bg: "#1a2e3a", border: "#38bdf8", text: "#7dd3fc" },
  mobile:      { bg: "#2e1a3a", border: "#c084fc", text: "#d8b4fe" },
  security:    { bg: "#3a1a1a", border: "#f87171", text: "#fca5a5" },
  data_eng:    { bg: "#1a3a2a", border: "#34d399", text: "#6ee7b7" },
  databases:   { bg: "#2a2a1a", border: "#fbbf24", text: "#fde68a" },
  systems:     { bg: "#1a2a3a", border: "#60a5fa", text: "#93c5fd" },
  languages:   { bg: "#3a1a2e", border: "#f472b6", text: "#fbcfe8" },
  qa_testing:  { bg: "#1a3a3a", border: "#2dd4bf", text: "#99f6e4" },
  blockchain:  { bg: "#2e2a1a", border: "#f59e0b", text: "#fcd34d" },
  game_dev:    { bg: "#2a1a3a", border: "#a78bfa", text: "#c4b5fd" },
  embedded_iot:{ bg: "#3a2a1a", border: "#d97706", text: "#fde68a" },
  research:    { bg: "#1a2a2a", border: "#a3e635", text: "#d9f99d" },
  unknown:     { bg: "#2a2a2a", border: "#888",    text: "#ccc"    },
};

function buildNetwork(nodes, edges) {
  const visNodes = nodes.map(n => {
    const c = DOMAIN_COLORS[n.domain] || DOMAIN_COLORS.unknown;
    return {
      id: n.id,
      label: n.id.replace(/_/g, " "),
      title: `${n.id}\nDomain: ${n.domain}`,
      color: { background: c.bg, border: c.border, highlight: { background: c.border, border: "#fff" } },
      font: { color: c.text, size: 12 },
      shape: "dot",
      size: n.degree > 5 ? 14 : n.degree > 2 ? 10 : 7,
    };
  });

  const visEdges = edges.map(e => ({
    from: e.from,
    to: e.to,
    color: { color: e.relation === "CHILD_OF" ? "#3a3d52" : "#2a3a2a", opacity: 0.7 },
    arrows: e.relation === "CHILD_OF" ? { to: { enabled: true, scaleFactor: 0.5 } } : {},
    dashes: e.relation === "IS_ALIAS_OF",
    width: 1,
  }));

  const container = document.getElementById("network");
  const network = new vis.Network(container,
    { nodes: new vis.DataSet(visNodes), edges: new vis.DataSet(visEdges) },
    {
      physics: { solver: "forceAtlas2Based", forceAtlas2Based: { gravitationalConstant: -60, springLength: 120 }, stabilization: { iterations: 200 } },
      interaction: { hover: true, tooltipDelay: 100 },
    }
  );

  const tooltip = document.getElementById("tooltip");
  network.on("hoverNode", params => {
    const node = visNodes.find(n => n.id === params.node);
    if (!node) return;
    const c = DOMAIN_COLORS[graphData.nodes.find(n=>n.id===params.node)?.domain] || DOMAIN_COLORS.unknown;
    tooltip.innerHTML = `
      <div class="skill-name">${params.node.replace(/_/g," ")}</div>
      <span class="domain-tag" style="background:${c.bg};color:${c.text};border:1px solid ${c.border}">
        ${graphData.nodes.find(n=>n.id===params.node)?.domain || "unknown"}
      </span>
    `;
    tooltip.style.display = "block";
    tooltip.style.left = (params.event.clientX + 14) + "px";
    tooltip.style.top  = (params.event.clientY - 10) + "px";
  });
  network.on("blurNode", () => tooltip.style.display = "none");
  return network;
}

let currentNetwork = buildNetwork(graphData.nodes, graphData.edges);

function applyFilters() {
  const search = document.getElementById("search").value.toLowerCase();
  const domain = document.getElementById("domain-filter").value;

  let nodes = graphData.nodes.filter(n => {
    const matchDomain = domain === "all" || n.domain === domain;
    const matchSearch = !search || n.id.includes(search);
    return matchDomain && matchSearch;
  });

  const nodeIds = new Set(nodes.map(n => n.id));
  const edges = graphData.edges.filter(e => nodeIds.has(e.from) && nodeIds.has(e.to));

  document.getElementById("filter-label").textContent =
    `Showing ${nodes.length} of {{ total_nodes }} skill nodes`;

  currentNetwork.destroy();
  currentNetwork = buildNetwork(nodes, edges);
}

function resetFilters() {
  document.getElementById("search").value = "";
  document.getElementById("domain-filter").value = "all";
  document.getElementById("filter-label").textContent = "Showing all {{ total_nodes }} skill nodes";
  currentNetwork.destroy();
  currentNetwork = buildNetwork(graphData.nodes, graphData.edges);
}
</script>
</body>
</html>
"""


@ontology_bp.route("/ontology")
def ontology_view():
    with open(ONTOLOGY_PATH, "rb") as f:
        import networkx as nx
        G = pickle.load(f)

    real_nodes = [n for n, d in G.nodes(data=True) if not n.startswith("_alias_")]
    alias_nodes = [n for n in G.nodes if n.startswith("_alias_")]
    child_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get("relation") == "CHILD_OF"]
    alias_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get("relation") == "IS_ALIAS_OF"]

    domains = sorted(set(
        d.get("domain", "unknown")
        for n, d in G.nodes(data=True)
        if not n.startswith("_alias_") and d.get("domain") != "unknown"
    ))

    degree = dict(G.degree())

    nodes_json = [
        {
            "id": n,
            "domain": G.nodes[n].get("domain", "unknown"),
            "degree": degree.get(n, 0),
        }
        for n in real_nodes
    ]

    edges_json = [
        {"from": u, "to": v, "relation": G[u][v].get("relation", "")}
        for u, v in G.edges()
        if not u.startswith("_alias_") and not v.startswith("_alias_")
    ]

    graph_json = json.dumps({"nodes": nodes_json, "edges": edges_json})

    return render_template_string(
        HTML,
        graph_json=graph_json,
        total_nodes=len(real_nodes),
        alias_nodes=len(alias_nodes),
        child_edges=len(child_edges),
        alias_edges=len(alias_edges),
        domains=domains,
    )
