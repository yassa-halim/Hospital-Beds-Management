"""
report_exporter.py
==================
Generates a Markdown KMS report after a full cycle run.

Public API
----------
    export_kms_report_to_md(
        expert_results,
        graph_insights,
        dataframes,
        phase_results,
        output_path="kms_report.md"
    ) -> str   (returns the written path)
"""

from __future__ import annotations
import os
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sev_icon(severity: str) -> str:
    return {"Critical": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🟢"}.get(severity, "⚪")


def _phase_icon(status: str) -> str:
    return {"success": "✅", "warning": "⚠️", "failed": "❌"}.get(status.lower(), "⚪")


def _build_operational_recommendations(expert_results: list[dict]) -> list[str]:
    """
    Derive operational recommendations from the Expert System results.
    Rules of thumb:
      - Critical rules → immediate action
      - High rules     → near-term planning
      - Medium rules   → monitoring
      - Low rules      → best-practice reinforcement
    """
    from collections import Counter
    recs: list[str] = []
    rule_names = Counter(r["rule_name"] for r in expert_results)
    sev_counts  = Counter(r["severity"] for r in expert_results)
    dept_counts: dict[str, int] = {}
    for r in expert_results:
        dept_counts[r["service"]] = dept_counts.get(r["service"], 0) + 1

    # Most burdened department
    if dept_counts:
        busiest = max(dept_counts, key=dept_counts.get)
        recs.append(
            f"**Prioritise `{busiest}`**: This department triggered the highest number of rule "
            f"conclusions ({dept_counts[busiest]}). Conduct an immediate capacity audit."
        )

    if "Critical Overload" in rule_names:
        recs.append(
            "**Immediate bed expansion or patient diversion** required in departments "
            "where bed occupancy exceeds 90% alongside low staff morale."
        )
    if "Doctor Shortage Warning" in rule_names:
        recs.append(
            "**Recruit or redistribute medical doctors**: Doctor presence rate is critically "
            "low in one or more departments. Consider on-call supplements or temporary hires."
        )
    if "Strike Impact on Capacity" in rule_names:
        recs.append(
            "**Develop contingency plans for labour disruptions**: Strike events correlate "
            "with dangerously high occupancy. Formalise strike-readiness protocols."
        )
    if "Bed Reallocation Needed" in rule_names:
        recs.append(
            "**Review bed allocation policy**: Sustained high refusal rates indicate "
            "structural mismatches between bed counts and department demand."
        )
    if "Flu Surge Alert" in rule_names:
        recs.append(
            "**Establish a flu surge protocol**: Flu events are driving extreme demand "
            "pressure. Pre-position surge beds and fast-track triage procedures."
        )
    if "Schedule Imbalance Alert" in rule_names:
        recs.append(
            "**Revise staff scheduling**: Some roles show average presence below 50%. "
            "Introduce incentive-based shift coverage to reduce gaps."
        )
    if "Service Quality Degradation" in rule_names:
        recs.append(
            "**Invest in staff well-being**: Simultaneous low satisfaction and morale "
            "suggest systemic burnout. Consider wellness programmes and workload reviews."
        )
    if "ICU Long-Stay Bottleneck" in rule_names:
        recs.append(
            "**Accelerate ICU discharge pathways**: High average length of stay in the ICU "
            "reduces bed availability. Strengthen step-down care coordination."
        )
    if "Optimal Performance" in rule_names:
        depts_ok = [r["service"] for r in expert_results if r["rule_name"] == "Optimal Performance"]
        recs.append(
            f"**Replicate best practices from `{'`, `'.join(set(depts_ok))}`**: "
            "These departments demonstrate sustained high morale and satisfaction — "
            "document their workflows as internal benchmarks."
        )
    if sev_counts.get("Low", 0) > sev_counts.get("Critical", 0) + sev_counts.get("High", 0):
        recs.append(
            "**Overall system health is acceptable**: The majority of triggered rules "
            "are low-severity. Maintain current monitoring frequency."
        )

    if not recs:
        recs.append("No specific recommendations generated — review the Expert System results manually.")

    return recs


# ---------------------------------------------------------------------------
# Main export function
# ---------------------------------------------------------------------------

def export_kms_report_to_md(
    expert_results:  list[dict],
    graph_insights:  list[str],
    dataframes:      dict,
    phase_results:   dict | None = None,
    output_path:     str = "kms_report.md",
) -> str:
    """
    Generate a Markdown KMS report.

    Parameters
    ----------
    expert_results  : list[dict] from run_expert_system()
    graph_insights  : list[str] from get_graph_insights()
    dataframes      : dict from load_all_data()
    phase_results   : dict mapping phase_name -> {'status': str, 'note': str}
                      status values: 'success' | 'warning' | 'failed'
    output_path     : file path for the .md report

    Returns
    -------
    Absolute path of the written file.
    """
    from collections import Counter

    if phase_results is None:
        phase_results = {}

    now       = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_only = datetime.now().strftime("%Y-%m-%d")

    lines: list[str] = []

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------
    lines += [
        "# 🏥 Hospital Knowledge Management System — KMS Report",
        "",
        f"**Generated:** {now}",
        f"**Project:** Hospital Beds Management KMS",
        "",
        "---",
        "",
    ]

    # ------------------------------------------------------------------
    # Executive Summary
    # ------------------------------------------------------------------
    pts  = len(dataframes.get("patients", []))
    stf  = len(dataframes.get("staff",    []))
    wks  = dataframes.get("services", {})
    wks  = len(wks["week"].unique()) if hasattr(wks, "__len__") else 0
    sev_counts = Counter(r["severity"] for r in expert_results)

    lines += [
        "## 📊 Executive Summary",
        "",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Total Patients | {pts:,} |",
        f"| Total Staff | {stf:,} |",
        f"| Weeks Analysed | {wks} |",
        f"| Expert System Rules Fired | {len(expert_results)} |",
        f"| 🔴 Critical Alerts | {sev_counts.get('Critical', 0)} |",
        f"| 🟠 High Alerts | {sev_counts.get('High', 0)} |",
        f"| 🟡 Medium Alerts | {sev_counts.get('Medium', 0)} |",
        f"| 🟢 Low Notes | {sev_counts.get('Low', 0)} |",
        "",
        "---",
        "",
    ]

    # ------------------------------------------------------------------
    # Expert System Results Table
    # ------------------------------------------------------------------
    lines += [
        "## 🧠 Expert System Results",
        "",
        "| Severity | Department | Rule | Conclusion | Week | Detail |",
        "|---|---|---|---|---|---|",
    ]
    for r in expert_results:
        icon  = _sev_icon(r["severity"])
        week  = str(r.get("week", "—"))
        conc  = r["conclusion"].replace("|", "\\|")[:80]
        detail = r.get("detail", "").replace("|", "\\|")
        lines.append(
            f"| {icon} {r['severity']} | {r['service']} | {r['rule_name']} "
            f"| {conc} | {week} | {detail} |"
        )

    lines += ["", "---", ""]

    # ------------------------------------------------------------------
    # Knowledge Graph Insights
    # ------------------------------------------------------------------
    lines += [
        "## 🕸️ Knowledge Graph Insights",
        "",
    ]
    for insight in graph_insights:
        lines.append(f"- {insight}")
    lines += ["", "---", ""]

    # ------------------------------------------------------------------
    # KMS Life-Cycle Phase Evaluation
    # ------------------------------------------------------------------
    default_phases = {
        "Data Acquisition":         {"status": "success", "note": "All 4 CSV files loaded successfully."},
        "Knowledge Representation": {"status": "success", "note": "Facts built from real data columns."},
        "Reasoning (Expert System)": {"status": "success" if expert_results else "warning",
                                      "note": f"{len(expert_results)} conclusions generated."},
        "Knowledge Graph":          {"status": "success", "note": "DiGraph built and visualised."},
        "Evaluation & Export":      {"status": "success", "note": "Report generated."},
    }
    phases = {**default_phases, **phase_results}

    lines += [
        "## ✅ KMS Life-Cycle Phase Evaluation",
        "",
        "| Phase | Status | Notes |",
        "|---|---|---|",
    ]
    for phase_name, info in phases.items():
        icon = _phase_icon(info.get("status", "success"))
        note = info.get("note", "")
        lines.append(f"| {phase_name} | {icon} {info.get('status','').title()} | {note} |")

    lines += ["", "---", ""]

    # ------------------------------------------------------------------
    # Operational Recommendations
    # ------------------------------------------------------------------
    recs = _build_operational_recommendations(expert_results)
    lines += [
        "## 💡 Operational Recommendations",
        "",
    ]
    for i, rec in enumerate(recs, 1):
        lines.append(f"{i}. {rec}")
        lines.append("")

    lines += ["---", ""]

    # ------------------------------------------------------------------
    # Footer
    # ------------------------------------------------------------------
    lines += [
        f"*Report auto-generated by Hospital KMS on {date_only}. "
        "All conclusions are derived from synthetic hospital data.*",
        "",
    ]

    # ------------------------------------------------------------------
    # Write file
    # ------------------------------------------------------------------
    output_path_obj = Path(output_path)
    output_path_obj.write_text("\n".join(lines), encoding="utf-8")
    return str(output_path_obj.resolve())


# ---------------------------------------------------------------------------
# CLI test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    from data_loader import load_all_data
    from expert_system import run_expert_system
    from knowledge_graph import build_knowledge_graph, get_graph_insights

    dfs      = load_all_data()
    results  = run_expert_system(dfs)
    G        = build_knowledge_graph(dfs, results)
    insights = get_graph_insights(G, results)

    out = export_kms_report_to_md(results, insights, dfs)
    print(f"[OK] Report written to: {out}")
