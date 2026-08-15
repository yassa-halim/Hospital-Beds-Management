"""
knowledge_graph.py
==================
Builds a directed Knowledge Graph (DiGraph) from hospital data and Expert
System results using networkx.

Node types:
    department   — the 4 hospital services (ICU, emergency, general_medicine, surgery)
    role         — doctor / nurse / nursing_assistant
    demographic  — Pediatric (<18) / Adult (18-64) / Geriatric (65+)
    event        — flu / strike / donation
    conclusion   — Expert System rule conclusions
    severity     — Critical / High / Medium / Low
    metric       — high_occupancy / high_refusal / low_morale / extreme_demand

Edge types:
    HAS_STAFF_ROLE      department → role
    SERVES_DEMOGRAPHIC  department → demographic
    EXPERIENCED_EVENT   department → event
    IMPACTS             event → department
    TRIGGERED           department → conclusion
    HAS_SEVERITY        conclusion → severity
    HAS_METRIC          department → metric

Public API:
    build_knowledge_graph(dataframes, expert_results) -> nx.DiGraph
    analyze_graph(graph) -> dict
    get_graph_insights(graph, expert_results) -> list[str]
    get_subgraph(graph, mode) -> nx.DiGraph
    draw_graph(graph, ax, mode) -> None
"""

from __future__ import annotations
import networkx as nx
import pandas as pd
from collections import defaultdict, Counter


# ---------------------------------------------------------------------------
# Colour palette for node types
# ---------------------------------------------------------------------------
NODE_COLORS: dict[str, str] = {
    "department":  "#4e9af1",   # vivid blue
    "role":        "#f1c94e",   # amber yellow
    "demographic": "#e879f9",   # soft magenta / purple
    "event":       "#4ecdc4",   # teal
    "conclusion":  "#f87171",   # coral red
    "severity":    "#c084fc",   # violet
    "metric":      "#34d399",   # emerald mint
}

SEVERITY_COLORS: dict[str, str] = {
    "Critical": "#ef4444",
    "High":     "#f97316",
    "Medium":   "#eab308",
    "Low":      "#22c55e",
}


def _nid(prefix: str, value: str) -> str:
    """Generate normalized unique node ID."""
    return f"{prefix}::{str(value).strip().lower().replace(' ', '_')}"


# ---------------------------------------------------------------------------
# Build Knowledge Graph
# ---------------------------------------------------------------------------

def build_knowledge_graph(
    dataframes: dict,
    expert_results: list[dict],
) -> nx.DiGraph:
    """
    Build and return a comprehensive DiGraph integrating all 4 hospital datasets
    and the complete set of Expert System conclusions.
    """
    G = nx.DiGraph()

    services_df    = dataframes.get("services", pd.DataFrame())
    staff_df       = dataframes.get("staff", pd.DataFrame())
    staff_presence = dataframes.get("staff_presence", pd.DataFrame())
    patient_stats  = dataframes.get("patient_stats", pd.DataFrame())

    # 1. Department Nodes
    departments = sorted(staff_df["service"].unique().tolist()) if not staff_df.empty else ["ICU", "emergency", "general_medicine", "surgery"]
    for dept in departments:
        nid = _nid("dept", dept)
        G.add_node(nid, label=dept.title(), node_type="department",
                   color=NODE_COLORS["department"], base_size=900)

    # 2. Role Nodes + HAS_STAFF_ROLE edges
    if not staff_presence.empty:
        for _, row in staff_presence.iterrows():
            role_nid = _nid("role", row["role"])
            dept_nid = _nid("dept", row["service"])
            if not G.has_node(role_nid):
                G.add_node(role_nid, label=row["role"].replace("_", " ").title(),
                           node_type="role", color=NODE_COLORS["role"], base_size=750)
            G.add_edge(dept_nid, role_nid,
                       relation="HAS_STAFF_ROLE",
                       weight=int(row["total_staff"]),
                       avg_presence=float(row["avg_presence_rate"]))

    # 3. Demographic Nodes + SERVES_DEMOGRAPHIC edges
    if not patient_stats.empty:
        for _, row in patient_stats.iterrows():
            dept_nid = _nid("dept", row["service"])
            for demo_col, demo_label in [("pediatric_pct", "Pediatric (<18)"),
                                         ("adult_pct", "Adult (18-64)"),
                                         ("geriatric_pct", "Geriatric (65+)")]:
                if demo_col in row:
                    demo_nid = _nid("demo", demo_label)
                    if not G.has_node(demo_nid):
                        G.add_node(demo_nid, label=demo_label,
                                   node_type="demographic", color=NODE_COLORS["demographic"], base_size=700)
                    G.add_edge(dept_nid, demo_nid,
                               relation="SERVES_DEMOGRAPHIC",
                               percentage=float(row[demo_col]))

    # 4. Event Nodes + EXPERIENCED_EVENT / IMPACTS edges
    if not services_df.empty:
        events_by_dept = (
            services_df[services_df["event"] != "none"]
            .groupby(["service", "event"])
            .size()
            .reset_index(name="count")
        )
        for _, row in events_by_dept.iterrows():
            event_nid = _nid("event", row["event"])
            dept_nid  = _nid("dept", row["service"])
            if not G.has_node(event_nid):
                G.add_node(event_nid, label=row["event"].title(),
                           node_type="event", color=NODE_COLORS["event"], base_size=800)
            G.add_edge(dept_nid, event_nid, relation="EXPERIENCED_EVENT", count=int(row["count"]))
            G.add_edge(event_nid, dept_nid, relation="IMPACTS", count=int(row["count"]))

    # 5. Severity Nodes
    for sev in ("Critical", "High", "Medium", "Low"):
        sev_nid = _nid("sev", sev)
        G.add_node(sev_nid, label=sev, node_type="severity",
                   color=SEVERITY_COLORS[sev], base_size=850)

    # 6. Conclusion Nodes + TRIGGERED + HAS_SEVERITY edges
    seen_conclusions: set[str] = set()
    dept_trigger_counts = Counter((r["service"], r["rule_name"]) for r in expert_results)

    for res in expert_results:
        dept_nid = _nid("dept", res["service"])
        conc_key = res["rule_name"]
        conc_nid = _nid("conc", conc_key)
        sev_nid  = _nid("sev", res["severity"])

        if conc_nid not in seen_conclusions:
            seen_conclusions.add(conc_nid)
            G.add_node(
                conc_nid,
                label=conc_key,
                node_type="conclusion",
                color=SEVERITY_COLORS.get(res["severity"], NODE_COLORS["conclusion"]),
                severity=res["severity"],
                conclusion_text=res["conclusion"],
                base_size=650,
            )
            G.add_edge(conc_nid, sev_nid, relation="HAS_SEVERITY")

        trigger_count = dept_trigger_counts.get((res["service"], res["rule_name"]), 1)
        G.add_edge(dept_nid, conc_nid,
                   relation="TRIGGERED",
                   severity=res["severity"],
                   occurrences=trigger_count)

    # 7. Operational Metric Nodes
    if not services_df.empty:
        _add_metric_nodes(G, services_df)

    return G


def _add_metric_nodes(G: nx.DiGraph, services_df: pd.DataFrame) -> None:
    """Add hotspot operational metric nodes to the graph."""
    dept_metrics: dict[str, list[str]] = defaultdict(list)

    for _, row in services_df.iterrows():
        dept = row["service"]
        if row.get("bed_occupancy_rate", 0) >= 0.90:
            dept_metrics[dept].append("high_occupancy")
        if row.get("refusal_rate", 0) >= 0.60:
            dept_metrics[dept].append("high_refusal")
        if row.get("staff_morale", 100) < 60:
            dept_metrics[dept].append("low_morale")
        if row.get("demand_pressure", 0) >= 3.0:
            dept_metrics[dept].append("extreme_demand")

    for dept, metrics in dept_metrics.items():
        counter = Counter(metrics)
        dept_nid = _nid("dept", dept)
        for metric, cnt in counter.items():
            metric_nid = _nid("metric", metric)
            if not G.has_node(metric_nid):
                G.add_node(metric_nid, label=metric.replace("_", " ").title(),
                           node_type="metric", color=NODE_COLORS["metric"], base_size=650)
            G.add_edge(dept_nid, metric_nid, relation="HAS_METRIC", occurrence_weeks=cnt)


# ---------------------------------------------------------------------------
# Subgraph extraction for filtering
# ---------------------------------------------------------------------------

def get_subgraph(graph: nx.DiGraph, mode: str = "all") -> nx.DiGraph:
    """
    Extract a focused subgraph based on viewing mode:
      - 'all'            : full graph
      - 'vulnerability'  : departments, critical/high conclusions, and severities
      - 'staffing'       : departments, roles, and staffing metrics
      - 'events'         : departments, events, and metrics
      - 'demographics'   : departments and patient age groups
    """
    if mode == "all" or len(graph) == 0:
        return graph

    keep_nodes = set()
    if mode == "vulnerability":
        for n, d in graph.nodes(data=True):
            ntype = d.get("node_type", "")
            sev = d.get("severity", "")
            if ntype in ("department", "severity") or (ntype == "conclusion" and sev in ("Critical", "High")):
                keep_nodes.add(n)

    elif mode == "staffing":
        for n, d in graph.nodes(data=True):
            ntype = d.get("node_type", "")
            if ntype in ("department", "role") or "morale" in d.get("label", "").lower():
                keep_nodes.add(n)

    elif mode == "events":
        for n, d in graph.nodes(data=True):
            ntype = d.get("node_type", "")
            if ntype in ("department", "event", "metric"):
                keep_nodes.add(n)

    elif mode == "demographics":
        for n, d in graph.nodes(data=True):
            ntype = d.get("node_type", "")
            if ntype in ("department", "demographic"):
                keep_nodes.add(n)
    else:
        return graph

    subG = graph.subgraph(keep_nodes).copy()
    return subG if len(subG) > 0 else graph


# ---------------------------------------------------------------------------
# Graph Analytics & Insights
# ---------------------------------------------------------------------------

def analyze_graph(graph: nx.DiGraph) -> dict:
    """
    Compute multi-dimensional graph metrics: degree, betweenness centrality,
    and department vulnerability indices.
    """
    if len(graph) == 0:
        return {}

    deg_centrality = nx.degree_centrality(graph)
    try:
        bet_centrality = nx.betweenness_centrality(graph)
    except Exception:
        bet_centrality = deg_centrality

    # Top nodes by degree centrality
    top_nodes = sorted(deg_centrality.items(), key=lambda x: x[1], reverse=True)[:8]
    top_nodes_labeled = [
        (graph.nodes[n].get("label", n), round(c, 4))
        for n, c in top_nodes
        if n in graph.nodes
    ]

    # Department statistics
    dept_conc: dict[str, int] = defaultdict(int)
    dept_critical: dict[str, int] = defaultdict(int)
    dept_high: dict[str, int] = defaultdict(int)
    dept_vulnerability_index: dict[str, int] = defaultdict(int)

    for u, v, data in graph.edges(data=True):
        if data.get("relation") == "TRIGGERED":
            dept_label = graph.nodes[u].get("label", u)
            dept_conc[dept_label] += 1
            sev = data.get("severity", "")
            if sev == "Critical":
                dept_critical[dept_label] += 1
                dept_vulnerability_index[dept_label] += 4
            elif sev == "High":
                dept_high[dept_label] += 1
                dept_vulnerability_index[dept_label] += 3
            elif sev == "Medium":
                dept_vulnerability_index[dept_label] += 2
            else:
                dept_vulnerability_index[dept_label] += 1

    most_critical_dept = (
        max(dept_vulnerability_index, key=dept_vulnerability_index.get)
        if dept_vulnerability_index else "N/A"
    )

    return {
        "top_nodes_by_degree":        top_nodes_labeled,
        "dept_conclusion_counts":     dict(dept_conc),
        "dept_critical_counts":       dict(dept_critical),
        "dept_high_counts":           dict(dept_high),
        "dept_vulnerability_index":   dict(dept_vulnerability_index),
        "most_critical_dept":         most_critical_dept,
        "degree_centrality":          deg_centrality,
        "betweenness_centrality":     bet_centrality,
        "total_nodes":                graph.number_of_nodes(),
        "total_edges":                graph.number_of_edges(),
    }


def get_graph_insights(graph: nx.DiGraph, expert_results: list[dict]) -> list[str]:
    """
    Generate structured, high-value Knowledge Graph insights.
    """
    analysis = analyze_graph(graph)
    if not analysis:
        return ["No graph data available."]

    insights = []
    insights.append(
        f"Network Scale: Graph integrates {analysis['total_nodes']} semantic entities "
        f"and {analysis['total_edges']} directed relational edges."
    )

    if analysis["top_nodes_by_degree"]:
        top_label, top_c = analysis["top_nodes_by_degree"][0]
        insights.append(f"Primary Central Hub: '{top_label}' exhibits highest degree centrality ({top_c:.3f}).")

    if analysis["most_critical_dept"] != "N/A":
        crit_dept = analysis["most_critical_dept"]
        vuln_score = analysis["dept_vulnerability_index"].get(crit_dept, 0)
        crit_count = analysis["dept_critical_counts"].get(crit_dept, 0)
        insights.append(
            f"Most Vulnerable Unit: '{crit_dept}' ranks #1 in operational risk (Vulnerability Index: {vuln_score}, Critical Triggers: {crit_count})."
        )

    # Department ranking
    ranked = sorted(analysis["dept_vulnerability_index"].items(), key=lambda x: x[1], reverse=True)
    if ranked:
        rank_str = " > ".join(f"{d} ({v})" for d, v in ranked)
        insights.append(f"Department Risk Hierarchy: {rank_str}.")

    # Severity distribution
    sev_count: Counter = Counter(r["severity"] for r in expert_results)
    parts = ", ".join(f"{k}: {v}" for k, v in sorted(sev_count.items(), key=lambda x: -x[1]))
    insights.append(f"Rule Firing Severity Distribution: {parts}.")

    return insights


# ---------------------------------------------------------------------------
# Drawing Helper (Embedded in GUI)
# ---------------------------------------------------------------------------

def draw_graph(graph: nx.DiGraph, ax, mode: str = "all") -> None:
    """
    Draw the DiGraph onto a matplotlib Axes object with enhanced aesthetics.
    """
    subG = get_subgraph(graph, mode)

    if len(subG) == 0:
        ax.text(0.5, 0.5, "No graph data to display", ha="center", va="center",
                fontsize=13, color="#a7a9be")
        ax.axis("off")
        return

    try:
        pos = nx.spring_layout(subG, k=1.8, seed=42, iterations=70)
    except Exception:
        pos = nx.circular_layout(subG)

    # Node rendering by type
    type_groups: dict[str, list] = defaultdict(list)
    for node, data in subG.nodes(data=True):
        ntype = data.get("node_type", "unknown")
        type_groups[ntype].append(node)

    for ntype, nodes in type_groups.items():
        color = NODE_COLORS.get(ntype, "#a7a9be")
        sizes = [subG.nodes[n].get("base_size", 700) for n in nodes]
        nx.draw_networkx_nodes(
            subG, pos, nodelist=nodes, node_color=color,
            node_size=sizes, alpha=0.92, ax=ax,
            edgecolors="#ffffff", linewidths=1.2
        )

    # Edge rendering
    edge_colors = []
    for u, v, data in subG.edges(data=True):
        sev = data.get("severity", "")
        edge_colors.append(SEVERITY_COLORS.get(sev, "#4b5563"))

    nx.draw_networkx_edges(
        subG, pos, edge_color=edge_colors,
        arrows=True, arrowsize=14,
        connectionstyle="arc3,rad=0.08",
        alpha=0.75, ax=ax, width=1.4
    )

    # Labels
    labels = {n: subG.nodes[n].get("label", n)[:16] for n in subG.nodes}
    nx.draw_networkx_labels(
        subG, pos, labels=labels,
        font_size=7.5, font_color="#ffffff",
        font_weight="bold", ax=ax
    )

    ax.axis("off")
    ax.set_facecolor("#1a1a2e")


# ---------------------------------------------------------------------------
# CLI test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    from data_loader import load_all_data
    from expert_system import run_expert_system

    dfs     = load_all_data()
    results = run_expert_system(dfs)
    G       = build_knowledge_graph(dfs, results)
    analysis = analyze_graph(G)

    print(f"[OK] Knowledge Graph built with {analysis['total_nodes']} nodes, {analysis['total_edges']} edges")
    print(f"\nMost vulnerable department: {analysis['most_critical_dept']}")
    print("\nInsights:")
    for i in get_graph_insights(G, results):
        print(f"  • {i}")
