import json
import pickle
from pathlib import Path

from flask import Blueprint, render_template_string

ontology_bp = Blueprint("ontology", __name__)

ONTOLOGY_PATH = Path(__file__).parent.parent.parent / "ontology" / "skill_ontology.gpickle"

HTML = """<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ExplainHire — Skill Ontology</title>
<script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
<style>
  :root[data-theme="dark"] {
    --bg:         #0d0f18;
    --surface:    #13161f;
    --surface2:   #1a1e2e;
    --border:     #262a3e;
    --text:       #e2e4f0;
    --text-muted: #6b7080;
    --accent:     #6c6fff;
    --accent-s:   rgba(108,111,255,0.12);
    --shadow:     0 4px 24px rgba(0,0,0,0.55);
    --input-bg:   #1a1e2e;
  }
  :root[data-theme="light"] {
    --bg:         #f2f3fb;
    --surface:    #ffffff;
    --surface2:   #eef0fa;
    --border:     #dde0f0;
    --text:       #1a1c2e;
    --text-muted: #7a7f9a;
    --accent:     #5254d4;
    --accent-s:   rgba(82,84,212,0.10);
    --shadow:     0 4px 24px rgba(0,0,0,0.10);
    --input-bg:   #eef0fa;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Segoe UI', system-ui, sans-serif;
    background: var(--bg);
    color: var(--text);
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    transition: background 0.2s, color 0.2s;
  }

  /* Header */
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 24px;
    height: 54px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
    box-shadow: var(--shadow);
    z-index: 10;
  }
  .h-left { display: flex; align-items: center; gap: 10px; }
  .logo-dot {
    width: 9px; height: 9px; border-radius: 50%;
    background: var(--accent);
    box-shadow: 0 0 8px var(--accent);
  }
  header h1 { font-size: 0.92rem; font-weight: 600; }
  header h1 span { color: var(--accent); }
  .h-right { display: flex; align-items: center; gap: 20px; }

  .stats-row { display: flex; gap: 18px; }
  .stat { display: flex; flex-direction: column; align-items: center; font-size: 0.68rem; color: var(--text-muted); line-height: 1.3; }
  .stat strong { font-size: 0.88rem; font-weight: 700; color: var(--accent); }

  /* Theme toggle */
  .theme-toggle { display: flex; align-items: center; gap: 7px; cursor: pointer; user-select: none; }
  .t-label { font-size: 0.75rem; color: var(--text-muted); }
  .t-track {
    width: 38px; height: 20px;
    background: var(--surface2); border: 1px solid var(--border);
    border-radius: 10px; position: relative; transition: background 0.2s;
  }
  .t-track.on { background: var(--accent); border-color: var(--accent); }
  .t-thumb {
    width: 14px; height: 14px; background: var(--text-muted);
    border-radius: 50%; position: absolute; top: 2px; left: 2px; transition: left 0.2s;
  }
  .t-track.on .t-thumb { left: 20px; background: #fff; }

  /* Toolbar */
  .toolbar {
    display: flex; align-items: center; gap: 10px;
    padding: 9px 24px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
  }
  .search-wrap { position: relative; flex: 1; max-width: 380px; }
  .search-wrap input {
    width: 100%; padding: 8px 12px 8px 32px;
    background: var(--input-bg); border: 1px solid var(--border);
    border-radius: 8px; color: var(--text); font-size: 0.84rem; outline: none;
    transition: border-color 0.15s;
  }
  .search-wrap input:focus { border-color: var(--accent); }
  .search-wrap input::placeholder { color: var(--text-muted); }
  .s-icon { position: absolute; left: 10px; top: 50%; transform: translateY(-50%); color: var(--text-muted); font-size: 0.85rem; pointer-events: none; }
  .rcount { font-size: 0.76rem; color: var(--text-muted); white-space: nowrap; }
  .rcount strong { color: var(--accent); }
  .btn {
    padding: 7px 14px; border-radius: 8px; border: 1px solid var(--border);
    cursor: pointer; font-size: 0.8rem; font-weight: 600;
    background: var(--surface2); color: var(--text);
    transition: background 0.15s, border-color 0.15s;
    white-space: nowrap;
  }
  .btn:hover { background: var(--accent-s); border-color: var(--accent); color: var(--accent); }
  .btn-accent { background: var(--accent); color: #fff; border-color: var(--accent); }
  .btn-accent:hover { opacity: 0.85; color: #fff; }

  /* Legend */
  .legend {
    display: flex; align-items: center; gap: 14px;
    padding: 6px 24px;
    background: var(--surface); border-bottom: 1px solid var(--border);
    flex-wrap: wrap; flex-shrink: 0;
  }
  .leg-label { font-size: 0.68rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); }
  .leg-items { display: flex; gap: 14px; flex-wrap: wrap; }
  .leg-item { display: flex; align-items: center; gap: 6px; font-size: 0.74rem; color: var(--text-muted); }
  .leg-dot { width: 11px; height: 11px; border-radius: 50%; flex-shrink: 0; border: 2px solid transparent; }
  .leg-line { width: 22px; height: 0; flex-shrink: 0; border-top: 2px solid; }
  .leg-line.dashed { border-top-style: dashed; }

  /* Canvas */
  #network { flex: 1; width: 100%; background: var(--bg); min-height: 0; }

  /* Tooltip */
  #tooltip {
    position: fixed; background: var(--surface); border: 1px solid var(--border);
    border-radius: 10px; padding: 11px 15px; font-size: 0.8rem;
    pointer-events: none; display: none; max-width: 260px; z-index: 999;
    line-height: 1.7; box-shadow: var(--shadow);
  }
  .tt-name { font-weight: 700; font-size: 0.95rem; margin-bottom: 3px; }
  .tt-row { color: var(--text-muted); font-size: 0.76rem; }
  .tt-row strong { color: var(--text); }
  .tt-badge {
    display: inline-block; margin-top: 6px; padding: 2px 10px;
    border-radius: 20px; font-size: 0.7rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.05em;
  }

  /* Side panel */
  #node-panel {
    position: absolute; bottom: 20px; right: 20px;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 12px; padding: 16px 20px; max-width: 300px;
    display: none; box-shadow: var(--shadow); z-index: 50;
  }
  .np-name { font-size: 1.05rem; font-weight: 700; margin-bottom: 6px; }
  .np-badge {
    display: inline-block; padding: 2px 10px; border-radius: 20px;
    font-size: 0.7rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.05em; margin-bottom: 8px;
  }
  .np-row { font-size: 0.79rem; color: var(--text-muted); margin-bottom: 3px; }
  .np-row strong { color: var(--text); }
  .np-skills { margin-top: 8px; }
  .np-tag {
    display: inline-block; margin: 3px 3px 0 0; padding: 2px 8px;
    background: var(--accent-s); border: 1px solid var(--accent);
    border-radius: 4px; font-size: 0.71rem; color: var(--accent); cursor: pointer;
  }
  .np-tag:hover { background: var(--accent); color: #fff; }
  .np-close {
    position: absolute; top: 10px; right: 12px;
    cursor: pointer; background: none; border: none;
    color: var(--text-muted); font-size: 1rem;
  }
  .np-close:hover { color: var(--text); }
</style>
</head>
<body>

<header>
  <div class="h-left">
    <div class="logo-dot"></div>
    <h1>ExplainHire &mdash; <span>Skill Ontology</span></h1>
  </div>
  <div class="h-right">
    <div class="stats-row">
      <div class="stat"><strong>{{ total_nodes }}</strong>Skills</div>
      <div class="stat"><strong>{{ alias_count }}</strong>Aliases</div>
      <div class="stat"><strong>{{ child_edges }}</strong>Hierarchy</div>
      <div class="stat"><strong>{{ root_count }}</strong>Roots</div>
    </div>
    <div class="theme-toggle" onclick="toggleTheme()">
      <span class="t-label" id="t-label">Dark</span>
      <div class="t-track" id="t-track"><div class="t-thumb"></div></div>
    </div>
  </div>
</header>

<div class="toolbar">
  <div class="search-wrap">
    <span class="s-icon">&#128269;</span>
    <input id="search" type="text" placeholder="Search skill — e.g. pytorch, docker, react..." oninput="onSearch(this.value)">
  </div>
  <div class="rcount" id="rcount">Showing <strong>{{ total_nodes }}</strong> nodes</div>
  <button class="btn" onclick="resetAll()">Reset</button>
  <button class="btn btn-accent" onclick="fitGraph()">Fit view</button>
</div>

<div class="legend">
  <span class="leg-label">Node role</span>
  <div class="leg-items">
    <div class="leg-item">
      <div class="leg-dot" style="background:#b4530944;border-color:#b45309"></div>Root
    </div>
    <div class="leg-item">
      <div class="leg-dot" style="background:#1d4ed844;border-color:#1d4ed8"></div>Parent
    </div>
    <div class="leg-item">
      <div class="leg-dot" style="background:#15803d44;border-color:#15803d"></div>Leaf
    </div>
    <div class="leg-item">
      <div class="leg-dot" style="background:#b91c1c44;border-color:#b91c1c"></div>Alias
    </div>
    <div class="leg-item">
      <div class="leg-dot" style="background:#4b556344;border-color:#4b5563"></div>Isolated
    </div>
    <div class="leg-item" style="margin-left:10px">
      <div class="leg-line" style="border-color:#5a5e78"></div>Child-of
    </div>
    <div class="leg-item">
      <div class="leg-line dashed" style="border-color:#4a6a4a"></div>Alias-of
    </div>
  </div>
</div>

<div style="position:relative;flex:1;min-height:0;display:flex;">
  <div id="network"></div>

  <div id="node-panel">
    <button class="np-close" onclick="closePanel()">&#10005;</button>
    <div class="np-name" id="np-name"></div>
    <div id="np-badge" class="np-badge"></div>
    <div class="np-row">Connections: <strong id="np-degree"></strong></div>
    <div class="np-skills">
      <div class="np-row" style="margin-bottom:4px">Connected skills:</div>
      <div id="np-neighbors"></div>
    </div>
  </div>
</div>

<div id="tooltip"></div>

<script>
const RAW = {{ graph_json | safe }};

// ── Build role lookup ──────────────────────────────────────────────────────
// For each node, determine: root | parent | leaf | alias | isolated
// CHILD_OF: child→parent (outgoing = "I am a child of X")
// IS_ALIAS_OF: alias→canonical

const hasChildOfOut  = new Set(); // nodes that have outgoing CHILD_OF (they are children)
const hasChildOfIn   = new Set(); // nodes that have incoming CHILD_OF (they are parents)
const hasAliasOut    = new Set(); // nodes that have outgoing IS_ALIAS_OF (they are aliases)

RAW.edges.forEach(e => {
  if (e.relation === "CHILD_OF") {
    hasChildOfOut.add(e.from); // e.from is a child
    hasChildOfIn.add(e.to);    // e.to is a parent
  } else if (e.relation === "IS_ALIAS_OF") {
    hasAliasOut.add(e.from);   // e.from is an alias
  }
});

function getRole(nodeId) {
  if (hasAliasOut.has(nodeId))  return "alias";
  const isChild  = hasChildOfOut.has(nodeId);
  const isParent = hasChildOfIn.has(nodeId);
  if (!isChild && !isParent)    return "isolated";
  if (!isChild && isParent)     return "root";     // top of hierarchy, nothing above it
  if (isChild && isParent)      return "parent";   // mid-hierarchy
  return "leaf";                                    // has parents, no children
}

// Role → visual config  { dark color, light color }
const ROLE_DEF = {
  root:     { dark: "#fbbf24", light: "#b45309", label: "Root",     size: 18 },
  parent:   { dark: "#60a5fa", light: "#1d4ed8", label: "Parent",   size: 13 },
  leaf:     { dark: "#4ade80", light: "#15803d", label: "Leaf",     size: 8  },
  alias:    { dark: "#f47272", light: "#b91c1c", label: "Alias",    size: 7  },
  isolated: { dark: "#888888", light: "#4b5563", label: "Isolated", size: 7  },
};

function ROLE(role) {
  const d = ROLE_DEF[role] || ROLE_DEF.isolated;
  return { color: isDark ? d.dark : d.light, label: d.label, size: d.size };
}

// ── Adjacency ──────────────────────────────────────────────────────────────
const adjacency = {};
RAW.nodes.forEach(n => { adjacency[n.id] = []; });
RAW.edges.forEach(e => {
  if (adjacency[e.from]) adjacency[e.from].push({ id: e.to,   rel: e.relation });
  if (adjacency[e.to])   adjacency[e.to].push(  { id: e.from, rel: e.relation });
});

function hexAlpha(hex, a) {
  const r = parseInt(hex.slice(1,3),16);
  const g = parseInt(hex.slice(3,5),16);
  const b = parseInt(hex.slice(5,7),16);
  return `rgba(${r},${g},${b},${a})`;
}

// ── Build vis datasets ─────────────────────────────────────────────────────
let visNodes, visEdges, network;

function makeVisNode(n, highlighted) {
  const role = getRole(n.id);
  const cfg  = ROLE(role);
  const c    = cfg.color;
  const hl   = highlighted && highlighted.has(n.id);
  // In light mode, use a stronger fill so nodes are visible on the white canvas
  const bgAlpha = isDark ? 0.22 : 0.35;
  const hlBorder = isDark ? "#ffffff" : "#111111";
  const fontColor = hl ? (isDark ? "#ffffff" : "#111111") : c;
  return {
    id:    n.id,
    label: n.id.replace(/_/g, " "),
    shape: "dot",
    size:  hl ? cfg.size + 5 : cfg.size,
    borderWidth: hl ? 3 : 2,
    color: {
      background: hl ? c : hexAlpha(c, bgAlpha),
      border:     hl ? hlBorder : c,
      highlight:  { background: c, border: hlBorder },
      hover:      { background: hexAlpha(c, 0.50), border: c },
    },
    font: { color: fontColor, size: hl ? 13 : 11, face: "Segoe UI" },
  };
}

function makeVisEdge(e) {
  const isChild = e.relation === "CHILD_OF";
  // Darker edges in light mode so they're visible on white background
  const childColor = isDark ? "#7074a0" : "#5a5e9a";
  const aliasColor = isDark ? "#4a8a4a" : "#2a6a2a";
  return {
    from: e.from, to: e.to,
    color: { color: isChild ? childColor : aliasColor, opacity: isDark ? 0.75 : 0.9 },
    arrows: isChild ? { to: { enabled: true, scaleFactor: 0.4 } } : {},
    dashes: !isChild,
    width: isDark ? 1 : 1.5,
    smooth: { type: "continuous" },
  };
}

function initNetwork(nodes, edges, highlighted) {
  const vn = nodes.map(n => makeVisNode(n, highlighted));
  const ve = edges.map(e => makeVisEdge(e));

  visNodes = new vis.DataSet(vn);
  visEdges = new vis.DataSet(ve);

  const container = document.getElementById("network");
  network = new vis.Network(container, { nodes: visNodes, edges: visEdges }, {
    physics: {
      solver: "forceAtlas2Based",
      forceAtlas2Based: { gravitationalConstant: -55, centralGravity: 0.005, springLength: 130, springConstant: 0.08, damping: 0.4 },
      stabilization: { iterations: 300, updateInterval: 25 },
    },
    interaction: { hover: true, tooltipDelay: 80, zoomView: true, dragView: true },
    layout: { improvedLayout: false },
  });

  // Tooltip
  const tooltip = document.getElementById("tooltip");
  network.on("hoverNode", params => {
    const n    = RAW.nodes.find(x => x.id === params.node);
    if (!n) return;
    const role = getRole(n.id);
    const cfg  = ROLE(role);
    tooltip.innerHTML = `
      <div class="tt-name" style="color:${cfg.color}">${params.node.replace(/_/g," ")}</div>
      <div class="tt-row">Connections: <strong>${n.degree}</strong></div>
      <div class="tt-badge" style="background:${hexAlpha(cfg.color,0.18)};border:1px solid ${cfg.color};color:${cfg.color}">${cfg.label}</div>
    `;
    tooltip.style.display = "block";
    tooltip.style.left = (params.event.clientX + 16) + "px";
    tooltip.style.top  = (params.event.clientY - 10) + "px";
  });
  network.on("blurNode",  () => tooltip.style.display = "none");
  network.on("dragStart", () => tooltip.style.display = "none");

  network.on("click", params => {
    if (params.nodes.length === 1) openPanel(params.nodes[0]);
    else closePanel();
  });

  network.on("stabilizationIterationsDone", () => {
    network.setOptions({ physics: false }); // freeze — no more jiggling
    network.fit({ animation: { duration: 600, easingFunction: "easeInOutQuad" } });
  });
}

// ── Side panel ─────────────────────────────────────────────────────────────
function openPanel(nodeId) {
  const n    = RAW.nodes.find(x => x.id === nodeId);
  if (!n) return;
  const role = getRole(nodeId);
  const cfg  = ROLE(role);

  document.getElementById("np-name").textContent  = nodeId.replace(/_/g, " ");
  document.getElementById("np-name").style.color  = cfg.color;
  const badge = document.getElementById("np-badge");
  badge.textContent   = cfg.label;
  badge.style.background  = hexAlpha(cfg.color, 0.18);
  badge.style.border      = `1px solid ${cfg.color}`;
  badge.style.color       = cfg.color;
  document.getElementById("np-degree").textContent = n.degree;

  const neighbors = adjacency[nodeId] || [];
  const wrap = document.getElementById("np-neighbors");
  wrap.innerHTML = neighbors.length
    ? neighbors.map(nb =>
        `<span class="np-tag" onclick="searchNode('${nb.id}')">${nb.id.replace(/_/g," ")}</span>`
      ).join("")
    : `<span style="color:var(--text-muted);font-size:0.77rem">No connections</span>`;

  document.getElementById("node-panel").style.display = "block";
}

function closePanel() { document.getElementById("node-panel").style.display = "none"; }

function searchNode(id) {
  document.getElementById("search").value = id;
  onSearch(id);
}

// ── Search ─────────────────────────────────────────────────────────────────
function onSearch(query) {
  const q = query.trim().toLowerCase();
  if (!q) { resetAll(); return; }

  const matched = RAW.nodes.filter(n => n.id.includes(q));
  if (!matched.length) {
    document.getElementById("rcount").innerHTML = `<strong style="color:#f87171">No matches</strong>`;
    return;
  }

  const matchedIds  = new Set(matched.map(n => n.id));
  const neighborIds = new Set();
  matchedIds.forEach(id => (adjacency[id] || []).forEach(nb => neighborIds.add(nb.id)));

  const visibleIds   = new Set([...matchedIds, ...neighborIds]);
  const visibleNodes = RAW.nodes.filter(n => visibleIds.has(n.id));
  const visibleEdges = RAW.edges.filter(e => visibleIds.has(e.from) && visibleIds.has(e.to));

  if (network) network.destroy();
  initNetwork(visibleNodes, visibleEdges, matchedIds);

  document.getElementById("rcount").innerHTML =
    `Showing <strong>${visibleNodes.length}</strong> nodes (<strong>${matchedIds.size}</strong> matched + neighbors)`;
}

function resetAll() {
  document.getElementById("search").value = "";
  document.getElementById("rcount").innerHTML = `Showing <strong>${RAW.nodes.length}</strong> nodes`;
  closePanel();
  if (network) network.destroy();
  initNetwork(RAW.nodes, RAW.edges, null);
}

function fitGraph() {
  if (network) network.fit({ animation: { duration: 500, easingFunction: "easeInOutQuad" } });
}

// ── Theme ──────────────────────────────────────────────────────────────────
let isDark = true;
function toggleTheme() {
  isDark = !isDark;
  document.documentElement.setAttribute("data-theme", isDark ? "dark" : "light");
  document.getElementById("t-track").classList.toggle("on", !isDark);
  document.getElementById("t-label").textContent = isDark ? "Dark" : "Light";

  // Rebuild with theme-correct colors; preserve current search state
  const query = document.getElementById("search").value.trim();
  if (query) onSearch(query);
  else {
    if (network) network.destroy();
    initNetwork(RAW.nodes, RAW.edges, null);
  }
}

// ── Boot ───────────────────────────────────────────────────────────────────
initNetwork(RAW.nodes, RAW.edges, null);
</script>
</body>
</html>
"""


@ontology_bp.route("/ontology")
def ontology_view():
    with open(ONTOLOGY_PATH, "rb") as f:
        import networkx as nx
        G = pickle.load(f)

    # Classify nodes by role
    has_child_of_out = set()  # nodes that are children (outgoing CHILD_OF)
    has_child_of_in  = set()  # nodes that are parents  (incoming CHILD_OF)
    has_alias_out    = set()  # nodes that are aliases   (outgoing IS_ALIAS_OF)

    for u, v, d in G.edges(data=True):
        rel = d.get("relation", "")
        if rel == "CHILD_OF":
            has_child_of_out.add(u)
            has_child_of_in.add(v)
        elif rel == "IS_ALIAS_OF":
            has_alias_out.add(u)

    def get_role(n):
        if n in has_alias_out:   return "alias"
        is_child  = n in has_child_of_out
        is_parent = n in has_child_of_in
        if not is_child and not is_parent: return "isolated"
        if not is_child and is_parent:     return "root"
        if is_child and is_parent:         return "parent"
        return "leaf"

    real_nodes  = [n for n in G.nodes if not n.startswith("_alias_")]
    alias_nodes = [n for n in G.nodes if n.startswith("_alias_")]
    child_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get("relation") == "CHILD_OF"]
    alias_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get("relation") == "IS_ALIAS_OF"]

    degree    = dict(G.degree())
    root_count = sum(1 for n in real_nodes if get_role(n) == "root")

    nodes_json = [
        {"id": n, "role": get_role(n), "degree": degree.get(n, 0)}
        for n in real_nodes
    ]

    edges_json = [
        {"from": u, "to": v, "relation": G[u][v].get("relation", "")}
        for u, v in G.edges()
        if not u.startswith("_alias_") and not v.startswith("_alias_")
    ]

    return render_template_string(
        HTML,
        graph_json=json.dumps({"nodes": nodes_json, "edges": edges_json}),
        total_nodes=len(real_nodes),
        alias_count=len(alias_nodes),
        child_edges=len(child_edges),
        root_count=root_count,
    )
