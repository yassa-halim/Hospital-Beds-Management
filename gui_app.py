"""
gui_app.py
==========
Hospital KMS — Comprehensive Tkinter GUI Application.

Implements an interactive sidebar-navigation interface covering the 5 KMS life-cycle phases:
  1. Data Acquisition & Dataset Explorer
  2. Knowledge Representation & Fact Extraction
  3. Reasoning & Expert System Rule Engine
  4. Knowledge Graph Visualization & Subgraph Analytics
  5. System Evaluation, Department KPI Dashboard & Action Plan
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import traceback
from pathlib import Path
from datetime import datetime

# Matplotlib embedded in tkinter
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

# Our modules
from data_loader import (
    load_all_data, get_summary, DataLoadError,
    compute_department_kpis, compute_event_impacts
)
from expert_system import run_expert_system, SEVERITY_ORDER
from knowledge_graph import (
    build_knowledge_graph, analyze_graph, get_graph_insights,
    get_subgraph, draw_graph, NODE_COLORS, SEVERITY_COLORS
)


# ---------------------------------------------------------------------------
# Theme & Color Palette
# ---------------------------------------------------------------------------
BG_DARK      = "#0f0e17"
BG_PANEL     = "#1a1a2e"
BG_CARD      = "#16213e"
BG_SIDEBAR   = "#0f3460"
ACCENT_BLUE  = "#4e9af1"
ACCENT_TEAL  = "#4ecdc4"
ACCENT_PURP  = "#6c47ff"
TEXT_PRIMARY = "#fffffe"
TEXT_MUTED   = "#a7a9be"
TEXT_HEADING = "#eaeaea"

SEV_COLORS = {
    "Critical": "#ff4444",
    "High":     "#ff8c00",
    "Medium":   "#ffcc00",
    "Low":      "#44cc44",
}
SEV_BG = {
    "Critical": "#3d0000",
    "High":     "#3d2000",
    "Medium":   "#3d3000",
    "Low":      "#003d00",
}

FONT_HEADING  = ("Segoe UI", 18, "bold")
FONT_SUBHEAD  = ("Segoe UI", 12, "bold")
FONT_BODY     = ("Segoe UI", 10)
FONT_MONO     = ("Consolas", 9)
FONT_SMALL    = ("Segoe UI", 8)
FONT_SIDEBAR  = ("Segoe UI", 10, "bold")
FONT_BADGE    = ("Segoe UI", 9, "bold")


# ---------------------------------------------------------------------------
# Widget Helpers
# ---------------------------------------------------------------------------

def styled_button(parent, text, command, bg=ACCENT_BLUE, fg="white",
                  font=FONT_BODY, padx=14, pady=6, **kw):
    btn = tk.Button(
        parent, text=text, command=command,
        bg=bg, fg=fg, font=font,
        activebackground=ACCENT_TEAL, activeforeground="white",
        relief="flat", cursor="hand2",
        padx=padx, pady=pady, **kw
    )
    btn.bind("<Enter>", lambda e: btn.config(bg=ACCENT_TEAL))
    btn.bind("<Leave>", lambda e: btn.config(bg=bg))
    return btn


def separator(parent, bg=ACCENT_BLUE):
    return tk.Frame(parent, height=1, bg=bg)


# ---------------------------------------------------------------------------
# Main Application Class
# ---------------------------------------------------------------------------

class HospitalKMSApp:
    """Main tkinter application window for Hospital KMS."""

    _dataframes:     dict | None = None
    _expert_results: list[dict] | None = None
    _graph:          object | None = None
    _graph_insights: list[str] | None = None
    _phase_results:  dict = {}
    _data_dir:       str | None = None

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🏥 Hospital Knowledge Management System")
        self.root.geometry("1340x840")
        self.root.minsize(1100, 720)
        self.root.configure(bg=BG_DARK)

        self._setup_ttk_style()
        self._build_header()
        self._build_main_area()

        # Start on Phase 1
        self._show_phase(0)

    # ------------------------------------------------------------------
    # TTK Style
    # ------------------------------------------------------------------

    def _setup_ttk_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                        background=BG_CARD,
                        foreground=TEXT_PRIMARY,
                        fieldbackground=BG_CARD,
                        rowheight=26,
                        font=FONT_BODY)
        style.configure("Treeview.Heading",
                        background=BG_SIDEBAR,
                        foreground=TEXT_HEADING,
                        font=("Segoe UI", 9, "bold"),
                        relief="flat")
        style.map("Treeview",
                  background=[("selected", ACCENT_BLUE)],
                  foreground=[("selected", "white")])

        style.configure("TScrollbar",
                        background=BG_PANEL,
                        troughcolor=BG_CARD,
                        bordercolor=BG_CARD)

        style.configure("TCombobox",
                        fieldbackground=BG_CARD,
                        background=BG_SIDEBAR,
                        foreground=TEXT_PRIMARY)

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    def _build_header(self):
        hdr = tk.Frame(self.root, bg=BG_SIDEBAR, height=64)
        hdr.pack(fill="x", side="top")
        hdr.pack_propagate(False)

        title_frame = tk.Frame(hdr, bg=BG_SIDEBAR)
        title_frame.pack(side="left", padx=20, pady=10)

        tk.Label(title_frame, text="🏥", font=("Segoe UI", 22),
                 bg=BG_SIDEBAR, fg=ACCENT_TEAL).pack(side="left")
        tk.Label(title_frame, text="  Hospital KMS",
                 font=("Segoe UI", 16, "bold"),
                 bg=BG_SIDEBAR, fg=TEXT_PRIMARY).pack(side="left")
        tk.Label(title_frame, text="  Knowledge Management System",
                 font=("Segoe UI", 10),
                 bg=BG_SIDEBAR, fg=TEXT_MUTED).pack(side="left", padx=(4, 0))

        btn_frame = tk.Frame(hdr, bg=BG_SIDEBAR)
        btn_frame.pack(side="right", padx=16, pady=10)

        styled_button(btn_frame, "▶  Run Full KMS Cycle",
                      self._run_full_cycle,
                      bg=ACCENT_PURP, padx=16, pady=7,
                      font=("Segoe UI", 10, "bold")).pack(side="left", padx=4)

        styled_button(btn_frame, "📂 Set Data Folder",
                      self._set_data_folder,
                      bg="#555577", padx=12, pady=7).pack(side="left", padx=4)

        # Status bar
        self.status_var = tk.StringVar(value="Ready — click 'Load Data' or 'Run Full KMS Cycle' to begin.")
        status_bar = tk.Label(self.root,
                              textvariable=self.status_var,
                              font=FONT_SMALL, bg=BG_DARK, fg=ACCENT_TEAL,
                              anchor="w", padx=12)
        status_bar.pack(fill="x", side="bottom")
        self._status_bar = status_bar

    # ------------------------------------------------------------------
    # Main Area: Sidebar + Content
    # ------------------------------------------------------------------

    def _build_main_area(self):
        main = tk.Frame(self.root, bg=BG_DARK)
        main.pack(fill="both", expand=True)

        # Sidebar
        sidebar = tk.Frame(main, bg=BG_SIDEBAR, width=220)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="KMS Life-Cycle",
                 font=("Segoe UI", 10, "bold"),
                 bg=BG_SIDEBAR, fg=TEXT_MUTED).pack(pady=(18, 8), padx=14, anchor="w")

        separator(sidebar, BG_CARD).pack(fill="x", padx=12)

        phases = [
            ("📥", "Data Acquisition"),
            ("🗂️", "Knowledge Representation"),
            ("🧠", "Reasoning (Rules)"),
            ("🕸️", "Knowledge Graph"),
            ("📊", "Evaluation & Analytics"),
        ]
        self._phase_buttons = []
        for i, (icon, name) in enumerate(phases):
            btn = tk.Button(
                sidebar,
                text=f"  {icon}  {name}",
                font=FONT_SIDEBAR,
                bg=BG_SIDEBAR, fg=TEXT_MUTED,
                activebackground=BG_CARD,
                activeforeground=TEXT_PRIMARY,
                relief="flat", anchor="w",
                padx=12, pady=12,
                cursor="hand2",
                command=lambda idx=i: self._show_phase(idx),
            )
            btn.pack(fill="x")
            self._phase_buttons.append(btn)

        # Content area
        self._content = tk.Frame(main, bg=BG_DARK)
        self._content.pack(side="left", fill="both", expand=True)

        self._phases: list[tk.Frame] = []
        self._phases.append(self._build_phase_acquisition())
        self._phases.append(self._build_phase_representation())
        self._phases.append(self._build_phase_reasoning())
        self._phases.append(self._build_phase_graph())
        self._phases.append(self._build_phase_evaluation())

    def _show_phase(self, idx: int):
        for i, (frame, btn) in enumerate(zip(self._phases, self._phase_buttons)):
            if i == idx:
                frame.pack(fill="both", expand=True)
                btn.config(bg=BG_CARD, fg=TEXT_PRIMARY)
            else:
                frame.pack_forget()
                btn.config(bg=BG_SIDEBAR, fg=TEXT_MUTED)
        self._current_phase = idx

    # ------------------------------------------------------------------
    # Phase 1 — Data Acquisition & Interactive Dataset Explorer
    # ------------------------------------------------------------------

    def _build_phase_acquisition(self) -> tk.Frame:
        frame = tk.Frame(self._content, bg=BG_DARK)
        self._phase_title(frame, "📥 Data Acquisition & Dataset Explorer",
                          "Load, inspect summary metrics, and explore the raw hospital datasets.")

        top_bar = tk.Frame(frame, bg=BG_DARK)
        top_bar.pack(fill="x", padx=20, pady=(0, 10))

        styled_button(top_bar, "📥 Load Data", self._load_data,
                      padx=18, pady=7, font=("Segoe UI", 10, "bold")).pack(side="left")

        self._acq_info_var = tk.StringVar(value="Click 'Load Data' to import CSV datasets.")
        tk.Label(top_bar, textvariable=self._acq_info_var,
                 font=FONT_SMALL, bg=BG_DARK, fg=ACCENT_TEAL).pack(side="left", padx=14)

        # Container split: Dataset Selector + Interactive Table Explorer
        explorer_frame = tk.Frame(frame, bg=BG_DARK)
        explorer_frame.pack(fill="both", expand=True, padx=20, pady=4)

        # Top cards bar
        self._acq_cards_frame = tk.Frame(explorer_frame, bg=BG_DARK)
        self._acq_cards_frame.pack(fill="x", pady=(0, 8))

        # Table explorer controls
        ctrl_bar = tk.Frame(explorer_frame, bg=BG_PANEL, padx=10, pady=6)
        ctrl_bar.pack(fill="x")

        tk.Label(ctrl_bar, text="Explore Dataset:", font=("Segoe UI", 9, "bold"),
                 bg=BG_PANEL, fg=TEXT_HEADING).pack(side="left", padx=(0, 8))

        self._selected_dataset = tk.StringVar(value="patients")
        for key, lbl in [("patients", "Patients (1k)"),
                         ("services", "Services Weekly (208)"),
                         ("staff", "Staff (110)"),
                         ("schedule", "Schedule (6.5k)")]:
            rb = tk.Radiobutton(
                ctrl_bar, text=lbl, variable=self._selected_dataset,
                value=key, command=self._refresh_dataset_table,
                bg=BG_PANEL, fg=TEXT_PRIMARY, selectcolor=BG_SIDEBAR,
                activebackground=BG_PANEL, activeforeground=ACCENT_TEAL,
                font=FONT_SMALL, cursor="hand2"
            )
            rb.pack(side="left", padx=6)

        # Search filter
        tk.Label(ctrl_bar, text="  🔍 Search:", font=FONT_SMALL,
                 bg=BG_PANEL, fg=TEXT_MUTED).pack(side="left", padx=(14, 4))
        self._acq_search_var = tk.StringVar()
        self._acq_search_var.trace_add("write", lambda *args: self._refresh_dataset_table())
        tk.Entry(ctrl_bar, textvariable=self._acq_search_var,
                 bg=BG_CARD, fg=TEXT_PRIMARY, insertbackground=ACCENT_TEAL,
                 width=18, relief="flat", font=FONT_SMALL).pack(side="left")

        self._table_count_lbl = tk.Label(ctrl_bar, text="", font=FONT_SMALL, bg=BG_PANEL, fg=ACCENT_TEAL)
        self._table_count_lbl.pack(side="right", padx=8)

        # Treeview table
        tv_frame = tk.Frame(explorer_frame, bg=BG_CARD)
        tv_frame.pack(fill="both", expand=True, pady=(6, 12))

        self._acq_tree = ttk.Treeview(tv_frame, show="headings", height=15)
        vsb = ttk.Scrollbar(tv_frame, orient="vertical", command=self._acq_tree.yview)
        hsb = ttk.Scrollbar(tv_frame, orient="horizontal", command=self._acq_tree.xview)
        self._acq_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self._acq_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tv_frame.grid_rowconfigure(0, weight=1)
        tv_frame.grid_columnconfigure(0, weight=1)

        return frame

    def _load_data(self):
        self._set_status("Loading hospital CSV datasets…")

        def _task():
            try:
                dfs = load_all_data(self._data_dir)
                self._dataframes = dfs
                self.root.after(0, self._on_data_loaded)
            except DataLoadError as e:
                self.root.after(0, lambda: self._show_error(str(e)))
            except Exception:
                self.root.after(0, lambda: self._show_error(traceback.format_exc()))

        threading.Thread(target=_task, daemon=True).start()

    def _on_data_loaded(self):
        if self._dataframes is None:
            return
        dfs = self._dataframes
        summary = get_summary(dfs)

        # Clear old summary cards
        for w in self._acq_cards_frame.winfo_children():
            w.destroy()

        cards_row = tk.Frame(self._acq_cards_frame, bg=BG_DARK)
        cards_row.pack(fill="x")

        for s in summary:
            card = tk.Frame(cards_row, bg=BG_CARD, padx=12, pady=8)
            card.pack(side="left", expand=True, fill="x", padx=4)
            tk.Label(card, text=s["name"], font=("Segoe UI", 9, "bold"),
                     bg=BG_CARD, fg=ACCENT_BLUE).pack(anchor="w")
            tk.Label(card, text=f"{s['rows']:,} rows × {s['cols']} cols",
                     font=("Segoe UI", 11, "bold"),
                     bg=BG_CARD, fg=TEXT_PRIMARY).pack(anchor="w", pady=(2, 0))

        total_rows = sum(s["rows"] for s in summary)
        self._acq_info_var.set(f"✅ Loaded {total_rows:,} total rows across 4 datasets.")
        self._set_status("Data loaded successfully.")
        self._phase_results["Data Acquisition"] = {
            "status": "success",
            "note":   f"4 CSV datasets loaded ({total_rows:,} records)."
        }

        self._refresh_dataset_table()

    def _refresh_dataset_table(self):
        if self._dataframes is None:
            return
        key = self._selected_dataset.get()
        df = self._dataframes.get(key)
        if df is None:
            return

        query = self._acq_search_var.get().strip().lower()

        # Clear treeview
        for col in self._acq_tree["columns"]:
            self._acq_tree.heading(col, text="")
        for row in self._acq_tree.get_children():
            self._acq_tree.delete(row)

        cols = list(df.columns)
        self._acq_tree["columns"] = cols
        for c in cols:
            self._acq_tree.heading(c, text=c.replace("_", " ").title())
            self._acq_tree.column(c, width=max(85, len(c) * 9), anchor="center")

        filtered_df = df
        if query:
            mask = df.astype(str).apply(lambda row: row.str.lower().str.contains(query).any(), axis=1)
            filtered_df = df[mask]

        count = 0
        for _, row in filtered_df.head(200).iterrows():
            vals = [str(v)[:30] for v in row.tolist()]
            self._acq_tree.insert("", "end", values=vals)
            count += 1

        total = len(filtered_df)
        self._table_count_lbl.config(
            text=f"Showing {count} of {total:,} rows" if total > 200 else f"{total:,} rows"
        )

    # ------------------------------------------------------------------
    # Phase 2 — Knowledge Representation & Fact Extraction
    # ------------------------------------------------------------------

    def _build_phase_representation(self) -> tk.Frame:
        frame = tk.Frame(self._content, bg=BG_DARK)
        self._phase_title(frame, "🗂️ Knowledge Representation & Facts",
                          "Transform raw tabular records into formal Facts for the Expert System.")

        btn_row = tk.Frame(frame, bg=BG_DARK)
        btn_row.pack(fill="x", padx=20, pady=(0, 10))

        styled_button(btn_row, "⚙️ Build Facts", self._build_facts,
                      padx=18, pady=7, font=("Segoe UI", 10, "bold")).pack(side="left")

        self._repr_info_var = tk.StringVar(value="Click 'Build Facts' to populate knowledge base facts.")
        tk.Label(btn_row, textvariable=self._repr_info_var,
                 font=FONT_SMALL, bg=BG_DARK, fg=ACCENT_TEAL).pack(side="left", padx=14)

        self._repr_text = self._scrolled_text(frame, height=30)
        return frame

    def _build_facts(self):
        if not self._check_data_loaded():
            return
        dfs = self._dataframes
        lines = []

        lines.append("╔══════════════════════════════════════════════════════════════════════════════════╗")
        lines.append("║                   🗂️ HOSPITAL KMS — EXTRACTED FACT BASE                           ║")
        lines.append("╚══════════════════════════════════════════════════════════════════════════════════╝\n")

        # ServiceFact
        n_service = len(dfs["services"])
        lines.append(f"═══ 1. ServiceFact (from services_weekly.csv) ═══")
        lines.append(f"  • Total Facts Extracted : {n_service} (52 weeks × 4 hospital services)")
        lines.append(f"  • Attributes            : week, month, service, available_beds, patients_request,")
        lines.append(f"                            patients_admitted, patients_refused, bed_occupancy_rate,")
        lines.append(f"                            refusal_rate, patient_satisfaction, staff_morale, event,")
        lines.append(f"                            unmet_demand, doctors_present, nurses_present")
        lines.append(f"  • Departments Monitored : {sorted(dfs['services']['service'].unique().tolist())}")
        lines.append(f"  • Events Categorized    : {sorted(dfs['services']['event'].unique().tolist())}\n")

        # StaffFact
        n_staff_facts = len(dfs["staff_presence"])
        lines.append(f"═══ 2. StaffFact (aggregated from staff.csv + staff_schedule.csv) ═══")
        lines.append(f"  • Total Facts Extracted : {n_staff_facts} (service × role staffing profiles)")
        lines.append(f"  • Attributes            : service, role, total_staff, avg_presence_rate, attended_shifts")
        for _, row in dfs["staff_presence"].iterrows():
            lines.append(
                f"    - {row['service']:18s} │ Role: {row['role']:18s} │ Staff: {int(row['total_staff']):2d} │ "
                f"Avg Presence: {row['avg_presence_rate']:.0%} │ Shifts: {int(row['attended_shifts'])}/{int(row['total_shifts'])}"
            )
        lines.append("")

        # PatientFact & Demographics
        n_patient_facts = len(dfs["patient_stats"])
        lines.append(f"═══ 3. PatientFact & Demographic Aggregates (from patients.csv) ═══")
        lines.append(f"  • Total Facts Extracted : {n_patient_facts} (per-service cohort statistics)")
        lines.append(f"  • Attributes            : service, total_patients, avg_length_of_stay, avg_satisfaction,")
        lines.append(f"                            pediatric_pct, adult_pct, geriatric_pct")
        for _, row in dfs["patient_stats"].iterrows():
            lines.append(
                f"    - {row['service']:18s} │ Patients: {int(row['total_patients']):3d} │ "
                f"Avg LOS: {row['avg_length_of_stay']:.1f}d │ Sat: {row['avg_satisfaction']:.1f}/100 │ "
                f"Pediatric: {row.get('pediatric_pct', 0):.1f}% │ Geriatric: {row.get('geriatric_pct', 0):.1f}%"
            )
        lines.append("")

        total_facts = n_service + n_staff_facts + n_patient_facts
        lines.append(f"──────────────────────────────────────────────────────────────────────────────────")
        lines.append(f"✅ Total Verified Facts in Knowledge Base: {total_facts:,}")

        self._set_text(self._repr_text, "\n".join(lines))
        self._repr_info_var.set(f"✅ Extracted {total_facts:,} verified facts into Knowledge Base.")
        self._set_status(f"Facts built — {total_facts:,} total facts available for reasoning.")
        self._phase_results["Knowledge Representation"] = {
            "status": "success",
            "note":   f"{total_facts:,} facts built across services, staffing, and patient demographics."
        }

    # ------------------------------------------------------------------
    # Phase 3 — Reasoning (Expert System)
    # ------------------------------------------------------------------

    def _build_phase_reasoning(self) -> tk.Frame:
        frame = tk.Frame(self._content, bg=BG_DARK)
        self._phase_title(frame, "🧠 Reasoning — Expert System Rule Engine",
                          "Evaluate forward-chaining rules against facts and inspect conclusions.")

        ctrl = tk.Frame(frame, bg=BG_DARK)
        ctrl.pack(fill="x", padx=20, pady=(0, 8))

        styled_button(ctrl, "▶  Run Expert System", self._run_expert_system_gui,
                      bg=ACCENT_PURP, padx=18, pady=7,
                      font=("Segoe UI", 10, "bold")).pack(side="left")

        # Badges row
        self._badge_crit = tk.Label(ctrl, text="🔴 Critical: 0", font=FONT_BADGE, bg="#3d0000", fg="#ff4444", padx=6, pady=2)
        self._badge_crit.pack(side="left", padx=4)

        self._badge_high = tk.Label(ctrl, text="🟠 High: 0", font=FONT_BADGE, bg="#3d2000", fg="#ff8c00", padx=6, pady=2)
        self._badge_high.pack(side="left", padx=4)

        self._badge_med = tk.Label(ctrl, text="🟡 Medium: 0", font=FONT_BADGE, bg="#3d3000", fg="#ffcc00", padx=6, pady=2)
        self._badge_med.pack(side="left", padx=4)

        self._badge_low = tk.Label(ctrl, text="🟢 Low: 0", font=FONT_BADGE, bg="#003d00", fg="#44cc44", padx=6, pady=2)
        self._badge_low.pack(side="left", padx=4)

        # Filters toolbar
        filter_bar = tk.Frame(frame, bg=BG_PANEL, padx=10, pady=6)
        filter_bar.pack(fill="x", padx=20, pady=(0, 6))

        tk.Label(filter_bar, text="Filter Severity:", font=FONT_SMALL, bg=BG_PANEL, fg=TEXT_MUTED).pack(side="left", padx=(0, 4))
        self._es_sev_filter = tk.StringVar(value="All")
        sev_cb = ttk.Combobox(filter_bar, textvariable=self._es_sev_filter,
                              values=["All", "Critical", "High", "Medium", "Low"],
                              state="readonly", width=10)
        sev_cb.pack(side="left", padx=4)
        sev_cb.bind("<<ComboboxSelected>>", lambda e: self._filter_es_tree())

        tk.Label(filter_bar, text="  Department:", font=FONT_SMALL, bg=BG_PANEL, fg=TEXT_MUTED).pack(side="left", padx=(10, 4))
        self._es_dept_filter = tk.StringVar(value="All")
        dept_cb = ttk.Combobox(filter_bar, textvariable=self._es_dept_filter,
                               values=["All", "emergency", "general_medicine", "surgery", "ICU"],
                               state="readonly", width=14)
        dept_cb.pack(side="left", padx=4)
        dept_cb.bind("<<ComboboxSelected>>", lambda e: self._filter_es_tree())

        tk.Label(filter_bar, text="  🔍 Search:", font=FONT_SMALL, bg=BG_PANEL, fg=TEXT_MUTED).pack(side="left", padx=(10, 4))
        self._es_search_var = tk.StringVar()
        self._es_search_var.trace_add("write", lambda *args: self._filter_es_tree())
        tk.Entry(filter_bar, textvariable=self._es_search_var,
                 bg=BG_CARD, fg=TEXT_PRIMARY, insertbackground=ACCENT_TEAL,
                 width=18, relief="flat", font=FONT_SMALL).pack(side="left")

        self._es_count_lbl = tk.Label(filter_bar, text="", font=FONT_SMALL, bg=BG_PANEL, fg=ACCENT_TEAL)
        self._es_count_lbl.pack(side="right", padx=6)

        # Treeview
        tv_frame = tk.Frame(frame, bg=BG_DARK)
        tv_frame.pack(fill="both", expand=True, padx=20, pady=(0, 12))

        cols = ("severity", "confidence", "service", "rule_name", "week", "action_plan", "detail")
        self._es_tree = ttk.Treeview(tv_frame, columns=cols, show="headings", height=20)

        widths = {
            "severity": 90,
            "confidence": 85,
            "service": 120,
            "rule_name": 180,
            "week": 60,
            "action_plan": 340,
            "detail": 280,
        }
        for c in cols:
            self._es_tree.heading(c, text=c.replace("_", " ").title())
            self._es_tree.column(c, width=widths.get(c, 120), anchor="center")

        for sev, color in SEV_BG.items():
            self._es_tree.tag_configure(sev, background=color, foreground=SEV_COLORS[sev])

        vsb = ttk.Scrollbar(tv_frame, orient="vertical", command=self._es_tree.yview)
        hsb = ttk.Scrollbar(tv_frame, orient="horizontal", command=self._es_tree.xview)
        self._es_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self._es_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tv_frame.grid_rowconfigure(0, weight=1)
        tv_frame.grid_columnconfigure(0, weight=1)

        return frame

    def _run_expert_system_gui(self):
        if not self._check_data_loaded():
            return
        self._set_status("Executing Expert System forward-chaining rules…")

        def _task():
            try:
                results = run_expert_system(self._dataframes)
                self._expert_results = results
                self.root.after(0, lambda: self._on_es_completed(results))
            except Exception:
                self.root.after(0, lambda: self._show_error(traceback.format_exc()))

        threading.Thread(target=_task, daemon=True).start()

    def _on_es_completed(self, results: list[dict]):
        from collections import Counter
        sev_count = Counter(r["severity"] for r in results)

        self._badge_crit.config(text=f"🔴 Critical: {sev_count.get('Critical', 0)}")
        self._badge_high.config(text=f"🟠 High: {sev_count.get('High', 0)}")
        self._badge_med.config(text=f"🟡 Medium: {sev_count.get('Medium', 0)}")
        self._badge_low.config(text=f"🟢 Low: {sev_count.get('Low', 0)}")

        self._filter_es_tree()
        self._set_status(f"Expert System finished: {len(results)} conclusions generated.")
        self._phase_results["Reasoning (Expert System)"] = {
            "status": "success",
            "note":   f"{len(results)} conclusions. Critical={sev_count.get('Critical', 0)}, High={sev_count.get('High', 0)}."
        }

    def _filter_es_tree(self):
        if self._expert_results is None:
            return

        sev_filter = self._es_sev_filter.get()
        dept_filter = self._es_dept_filter.get()
        query = self._es_search_var.get().strip().lower()

        for row in self._es_tree.get_children():
            self._es_tree.delete(row)

        count = 0
        for r in self._expert_results:
            if sev_filter != "All" and r["severity"] != sev_filter:
                continue
            if dept_filter != "All" and r["service"] != dept_filter:
                continue
            if query:
                combined = f"{r['service']} {r['rule_name']} {r['conclusion']} {r.get('detail','')} {r.get('action_plan','')}".lower()
                if query not in combined:
                    continue

            conf_val = r.get("confidence", 1.0)
            conf_str = f"{conf_val:.0%}" if isinstance(conf_val, (int, float)) else str(conf_val)

            self._es_tree.insert(
                "", "end",
                values=(
                    r["severity"],
                    conf_str,
                    r["service"],
                    r["rule_name"],
                    r.get("week", "—"),
                    r.get("action_plan", ""),
                    r.get("detail", ""),
                ),
                tags=(r["severity"],),
            )
            count += 1

        self._es_count_lbl.config(text=f"Showing {count} of {len(self._expert_results)} conclusions")

    # ------------------------------------------------------------------
    # Phase 4 — Knowledge Graph Visualization & Subgraphs
    # ------------------------------------------------------------------

    def _build_phase_graph(self) -> tk.Frame:
        frame = tk.Frame(self._content, bg=BG_DARK)
        self._phase_title(frame, "🕸️ Knowledge Graph Visualization",
                          "Multi-dimensional semantic network connecting departments, staffing, demographics, and rules.")

        ctrl = tk.Frame(frame, bg=BG_DARK)
        ctrl.pack(fill="x", padx=20, pady=(0, 6))

        styled_button(ctrl, "🔨 Build & Render Graph", self._build_graph_gui,
                      bg=ACCENT_TEAL, fg="black", padx=16, pady=7,
                      font=("Segoe UI", 10, "bold")).pack(side="left")

        # Subgraph view selector
        tk.Label(ctrl, text="  View Subgraph:", font=FONT_SMALL, bg=BG_DARK, fg=TEXT_MUTED).pack(side="left", padx=(10, 4))
        self._graph_view_mode = tk.StringVar(value="all")
        for mode, label in [("all", "🌐 Full Network"),
                            ("vulnerability", "⚠️ Vulnerabilities"),
                            ("staffing", "👥 Staffing"),
                            ("events", "⚡ Events"),
                            ("demographics", "👶 Demographics")]:
            rb = tk.Radiobutton(
                ctrl, text=label, variable=self._graph_view_mode,
                value=mode, command=self._replot_graph,
                bg=BG_DARK, fg=TEXT_PRIMARY, selectcolor=BG_SIDEBAR,
                activebackground=BG_DARK, activeforeground=ACCENT_TEAL,
                font=FONT_SMALL, cursor="hand2"
            )
            rb.pack(side="left", padx=4)

        # Split: graph canvas left, insights right
        split = tk.Frame(frame, bg=BG_DARK)
        split.pack(fill="both", expand=True, padx=20, pady=4)

        graph_container = tk.Frame(split, bg=BG_PANEL)
        graph_container.pack(side="left", fill="both", expand=True)

        self._fig = Figure(figsize=(8.5, 5.5), facecolor=BG_PANEL)
        self._ax  = self._fig.add_subplot(111)
        self._ax.set_facecolor(BG_PANEL)
        self._canvas = FigureCanvasTkAgg(self._fig, master=graph_container)
        self._canvas.get_tk_widget().pack(fill="both", expand=True)

        toolbar_frame = tk.Frame(graph_container, bg=BG_PANEL)
        toolbar_frame.pack(fill="x")
        self._toolbar = NavigationToolbar2Tk(self._canvas, toolbar_frame)
        self._toolbar.config(bg=BG_PANEL)
        self._toolbar.update()

        # Insights & Legend side panel
        side_panel = tk.Frame(split, bg=BG_CARD, width=300)
        side_panel.pack(side="right", fill="y", padx=(8, 0))
        side_panel.pack_propagate(False)

        tk.Label(side_panel, text="Graph Insights", font=("Segoe UI", 11, "bold"),
                 bg=BG_CARD, fg=ACCENT_TEAL).pack(pady=(10, 4), padx=10, anchor="w")
        separator(side_panel).pack(fill="x", padx=10)

        self._insight_text = self._scrolled_text(side_panel, height=18, width=32,
                                                 font=FONT_SMALL, bg=BG_CARD)

        # Legend container
        leg_frame = tk.Frame(side_panel, bg=BG_CARD)
        leg_frame.pack(fill="x", padx=10, pady=(6, 10))
        tk.Label(leg_frame, text="Node Palette:", font=("Segoe UI", 8, "bold"),
                 bg=BG_CARD, fg=TEXT_MUTED).pack(anchor="w")

        legend_items = [
            ("#4e9af1", "Department"),
            ("#f1c94e", "Staff Role"),
            ("#e879f9", "Demographic Cohort"),
            ("#4ecdc4", "Hospital Event"),
            ("#f87171", "Rule Conclusion"),
            ("#c084fc", "Severity Rank"),
            ("#34d399", "Operational Metric"),
        ]
        for color, label in legend_items:
            row = tk.Frame(leg_frame, bg=BG_CARD)
            row.pack(fill="x", pady=1)
            tk.Label(row, text="●", font=FONT_SMALL, bg=color, fg=color, width=2).pack(side="left")
            tk.Label(row, text=f"  {label}", font=FONT_SMALL, bg=BG_CARD, fg=TEXT_MUTED).pack(side="left")

        return frame

    def _build_graph_gui(self):
        if not self._check_data_loaded():
            return
        if self._expert_results is None:
            self._show_error("Please run Reasoning (Phase 3) before building the Knowledge Graph.")
            return
        self._set_status("Constructing Knowledge Graph…")

        def _task():
            try:
                G = build_knowledge_graph(self._dataframes, self._expert_results)
                insights = get_graph_insights(G, self._expert_results)
                self._graph = G
                self._graph_insights = insights
                self.root.after(0, lambda: self._on_graph_built(G, insights))
            except Exception:
                self.root.after(0, lambda: self._show_error(traceback.format_exc()))

        threading.Thread(target=_task, daemon=True).start()

    def _on_graph_built(self, G, insights):
        self._replot_graph()
        self._set_text(self._insight_text, "\n\n".join(f"• {i}" for i in insights))
        analysis = analyze_graph(G)
        self._set_status(f"Graph constructed — {analysis.get('total_nodes')} nodes, {analysis.get('total_edges')} edges.")
        self._phase_results["Knowledge Graph"] = {
            "status": "success",
            "note":   f"{analysis.get('total_nodes')} nodes, {analysis.get('total_edges')} edges. Most vulnerable: {analysis.get('most_critical_dept', 'N/A')}."
        }

    def _replot_graph(self):
        if self._graph is None:
            return
        mode = self._graph_view_mode.get()
        self._ax.clear()
        self._ax.set_facecolor(BG_PANEL)
        self._fig.set_facecolor(BG_PANEL)
        draw_graph(self._graph, self._ax, mode=mode)
        self._canvas.draw()

    # ------------------------------------------------------------------
    # Phase 5 — System Evaluation & Executive KPI Dashboard
    # ------------------------------------------------------------------

    def _build_phase_evaluation(self) -> tk.Frame:
        frame = tk.Frame(self._content, bg=BG_DARK)
        self._phase_title(frame, "📊 Evaluation & Executive Dashboard",
                          "Comprehensive synthesis of hospital operations, department risk matrix, and action plans.")

        ctrl = tk.Frame(frame, bg=BG_DARK)
        ctrl.pack(fill="x", padx=20, pady=(0, 10))
        styled_button(ctrl, "🔄 Refresh Dashboard", self._refresh_eval,
                      padx=16, pady=7, font=("Segoe UI", 10, "bold")).pack(side="left")

        self._eval_text = self._scrolled_text(frame, height=30)
        return frame

    def _refresh_eval(self):
        self._phase_results["Evaluation"] = {
            "status": "success",
            "note": "Evaluation dashboard and operational recommendations compiled."
        }

        lines = [
            "╔══════════════════════════════════════════════════════════════════════════════════════════════╗",
            "║                   🏥 HOSPITAL KMS — EXECUTIVE EVALUATION & ANALYTICS DASHBOARD               ║",
            "╚══════════════════════════════════════════════════════════════════════════════════════════════╝",
            "",
            "📊 1. EXECUTIVE SUMMARY & HOSPITAL CAPACITY OVERVIEW",
            "──────────────────────────────────────────────────────────────────────────────────────────────",
        ]

        if self._dataframes is not None:
            pts = len(self._dataframes.get("patients", []))
            stf = len(self._dataframes.get("staff", []))
            srv = self._dataframes.get("services", {})
            total_req = srv["patients_request"].sum() if "patients_request" in srv else 0
            total_adm = srv["patients_admitted"].sum() if "patients_admitted" in srv else 0
            total_ref = srv["patients_refused"].sum() if "patients_refused" in srv else 0
            avg_occ = srv["bed_occupancy_rate"].mean() if "bed_occupancy_rate" in srv else 0

            lines.append(f"  • Total Patients Recorded  : {pts:,}")
            lines.append(f"  • Medical Staff Monitored  : {stf:,}")
            lines.append(f"  • Total Patient Requests   : {total_req:,}")
            lines.append(f"  • Total Patients Admitted  : {total_adm:,} ({total_adm/max(1,total_req):.1%})")
            lines.append(f"  • Total Patients Refused   : {total_ref:,} ({total_ref/max(1,total_req):.1%})")
            lines.append(f"  • Overall Hospital Occupancy: {avg_occ:.1%}")
        else:
            lines.append("  • Datasets not yet loaded.")

        if self._expert_results:
            from collections import Counter
            sev_counts = Counter(r["severity"] for r in self._expert_results)
            lines.append(f"  • Expert Rules Fired       : {len(self._expert_results):,}")
            lines.append(f"    - 🔴 Critical Alerts     : {sev_counts.get('Critical', 0)}")
            lines.append(f"    - 🟠 High Warnings       : {sev_counts.get('High', 0)}")
            lines.append(f"    - 🟡 Medium Notes        : {sev_counts.get('Medium', 0)}")
            lines.append(f"    - 🟢 Low / Benchmarks    : {sev_counts.get('Low', 0)}")
        lines.append("")

        # 2. Department KPI Matrix
        lines.append("🏢 2. DEPARTMENT PERFORMANCE & CAPACITY MATRIX")
        lines.append("──────────────────────────────────────────────────────────────────────────────────────────────")
        if self._dataframes and "department_kpis" in self._dataframes:
            kpis = self._dataframes["department_kpis"]
            lines.append(f"  {'Department':<18s} │ {'Beds':<5s} │ {'Requests':<8s} │ {'Admitted':<8s} │ {'Refused':<8s} │ {'Occupancy':<9s} │ {'Refusal Rate':<12s} │ {'Morale':<6s} │ {'Staff':<5s}")
            lines.append("  " + "─"*18 + "─┼─" + "─"*5 + "─┼─" + "─"*8 + "─┼─" + "─"*8 + "─┼─" + "─"*8 + "─┼─" + "─"*9 + "─┼─" + "─"*12 + "─┼─" + "─"*6 + "─┼─" + "─"*5)
            for _, r in kpis.iterrows():
                lines.append(
                    f"  {r['service']:<18s} │ {r['avg_available_beds']:<5.1f} │ {int(r['total_requests']):<8,d} │ "
                    f"{int(r['total_admitted']):<8,d} │ {int(r['total_refused']):<8,d} │ {r['avg_occupancy']:<9.1%} │ "
                    f"{r['overall_refusal_rate']:<12.1%} │ {r['avg_morale']:<6.1f} │ {int(r['total_staff']):<5d}"
                )
        lines.append("")

        # 3. Event Impact Analysis
        lines.append("⚡ 3. EVENT OPERATIONAL IMPACT ANALYSIS")
        lines.append("──────────────────────────────────────────────────────────────────────────────────────────────")
        if self._dataframes and "event_impacts" in self._dataframes:
            evts = self._dataframes["event_impacts"]
            lines.append(f"  {'Event Type':<12s} │ {'Weeks':<5s} │ {'Avg Requests':<12s} │ {'Avg Admitted':<12s} │ {'Avg Refused':<11s} │ {'Occupancy':<9s} │ {'Staff Morale':<12s}")
            lines.append("  " + "─"*12 + "─┼─" + "─"*5 + "─┼─" + "─"*12 + "─┼─" + "─"*12 + "─┼─" + "─"*11 + "─┼─" + "─"*9 + "─┼─" + "─"*12)
            for _, r in evts.iterrows():
                lines.append(
                    f"  {r['event']:<12s} │ {int(r['weeks_count']):<5d} │ {r['avg_requests']:<12.1f} │ "
                    f"{r['avg_admitted']:<12.1f} │ {r['avg_refused']:<11.1f} │ {r['avg_occupancy']:<8.1f}% │ {r['avg_morale']:<12.1f}"
                )
        lines.append("")

        # 4. KMS Life-Cycle Audit
        lines.append("🔄 4. KMS LIFE-CYCLE PHASE AUDIT")
        lines.append("──────────────────────────────────────────────────────────────────────────────────────────────")
        icon_map = {"success": "✅", "warning": "⚠️", "failed": "❌"}
        phases = [
            "Data Acquisition",
            "Knowledge Representation",
            "Reasoning (Expert System)",
            "Knowledge Graph",
            "Evaluation",
        ]
        for p in phases:
            info = self._phase_results.get(p)
            if info:
                icon = icon_map.get(info["status"], "⚪")
                lines.append(f"  {icon}  {p:<28s} │ Status: {info['status'].title():<8s} │ {info['note']}")
            else:
                lines.append(f"  ⚪  {p:<28s} │ Status: Not yet run")
        lines.append("")

        # 5. Knowledge Graph Findings
        lines.append("🕸️ 5. KNOWLEDGE GRAPH INTELLIGENCE")
        lines.append("──────────────────────────────────────────────────────────────────────────────────────────────")
        if self._graph_insights:
            for g_ins in self._graph_insights:
                lines.append(f"  • {g_ins}")
        else:
            lines.append("  • Knowledge Graph has not been constructed yet.")
        lines.append("")

        # 6. Operational Recommendations & Action Plan
        lines.append("💡 6. PRIORITIZED OPERATIONAL ACTION PLAN")
        lines.append("──────────────────────────────────────────────────────────────────────────────────────────────")
        if self._expert_results:
            recs = self._derive_recommendations(self._expert_results)
            for i, rec in enumerate(recs, 1):
                lines.append(f"  {i}. {rec}\n")
        else:
            lines.append("  • Run Expert System (Phase 3) to synthesize operational recommendations.")
        lines.append("")

        self._set_text(self._eval_text, "\n".join(lines))

    def _derive_recommendations(self, expert_results: list[dict]) -> list[str]:
        """Derive actionable recommendations grouped by priority."""
        from collections import Counter
        recs: list[str] = []
        rule_names = Counter(r["rule_name"] for r in expert_results)
        dept_counts: dict[str, int] = {}
        for r in expert_results:
            dept_counts[r["service"]] = dept_counts.get(r["service"], 0) + 1

        if dept_counts:
            busiest = max(dept_counts, key=dept_counts.get)
            recs.append(
                f"[Immediate] Prioritise Capacity Expansion in '{busiest}': "
                f"Generated the highest volume of alert triggers ({dept_counts[busiest]}). "
                f"Requires an immediate bed reallocation audit and rapid patient triage diversion."
            )

        if "Emergency Access Crisis" in rule_names or "Critical Overload" in rule_names:
            recs.append(
                "[Immediate] Emergency Department Fast-Track & Bed Reserve: "
                "Emergency refusal exceeds 75% under peak pressure. Pre-allocate dedicated step-down surge beds "
                "in general wards to accelerate emergency admissions."
            )

        if "Doctor Coverage Shortage" in rule_names:
            recs.append(
                "[Staffing] Physician Deployment & On-Call Rotation: "
                "Physician attendance is critically low in key services. Introduce on-call compensation incentives "
                "and cross-department doctor rotations to eliminate coverage gaps."
            )

        if "Flu Epidemic Surge Alert" in rule_names:
            recs.append(
                "[Preparedness] Seasonal Flu Surge Protocol: "
                "Historical data proves flu events drive requests up to 161+ (3.0x normal). "
                "Trigger automated pre-positioning of surge beds and vaccination drives before peak winter months."
            )

        if "Strike Operational Disruption" in rule_names:
            recs.append(
                "[Risk Mitigation] Labour Disruption Contingency Framework: "
                "Strike events severely depress staff morale (53.7/100) while occupancy remains high. "
                "Establish formal agreements for minimum emergency staffing during labour disputes."
            )

        if "Nursing Workload Strain" in rule_names:
            recs.append(
                "[Staffing] Nursing Shift Rebalancing: "
                "High admitted patient-to-nurse ratios detected. Rebalance nurse rosters from lower-occupancy "
                "departments to support heavy admission shifts."
            )

        if "ICU Bed Turnover Bottleneck" in rule_names:
            recs.append(
                "[Clinical Workflow] Accelerate ICU Step-Down Discharge: "
                "Prolonged ICU length of stay blocks incoming critical patients. Formalize daily multi-disciplinary "
                "rounds to transition stabilized patients to intermediate care."
            )

        if "Operational Excellence" in rule_names:
            depts_ok = sorted(set(r["service"] for r in expert_results if r["rule_name"] == "Operational Excellence"))
            recs.append(
                f"[Benchmarking] Replicate Workflows from [{', '.join(depts_ok)}]: "
                f"These services demonstrated sustained operational harmony. Document their scheduling and leadership "
                f"practices as internal hospital standards."
            )

        if not recs:
            recs.append("Hospital operations are stable. Maintain routine continuous monitoring.")

        return recs

    # ------------------------------------------------------------------
    # Pipeline Orchestration
    # ------------------------------------------------------------------

    def _run_full_cycle(self):
        """Execute the entire 5-phase KMS life-cycle sequentially."""
        self._set_status("Executing Full KMS Life-Cycle…")

        def _worker():
            try:
                # 1. Load Data
                self.root.after(0, lambda: self._set_status("Step 1/5: Loading hospital datasets…"))
                if self._dataframes is None:
                    dfs = load_all_data(self._data_dir)
                    self._dataframes = dfs
                    self.root.after(0, self._on_data_loaded)
                else:
                    dfs = self._dataframes

                # 2. Build Facts
                self.root.after(0, lambda: self._set_status("Step 2/5: Extracting knowledge base facts…"))
                self.root.after(0, self._build_facts)

                # 3. Run Expert System
                self.root.after(0, lambda: self._set_status("Step 3/5: Reasoning with Expert System rules…"))
                results = run_expert_system(dfs)
                self._expert_results = results
                self.root.after(0, lambda: self._on_es_completed(results))

                # 4. Build Knowledge Graph
                self.root.after(0, lambda: self._set_status("Step 4/5: Constructing Knowledge Graph…"))
                G = build_knowledge_graph(dfs, results)
                insights = get_graph_insights(G, results)
                self._graph = G
                self._graph_insights = insights
                self.root.after(0, lambda: self._on_graph_built(G, insights))

                # 5. Refresh Evaluation Dashboard
                self.root.after(0, lambda: self._set_status("Step 5/5: Compiling evaluation dashboard…"))
                self.root.after(0, self._refresh_eval)

                def _finish():
                    self._show_phase(4)
                    self._set_status("🌟 Full KMS Life-Cycle completed successfully!")

                self.root.after(0, _finish)

            except Exception:
                self.root.after(0, lambda: self._show_error(traceback.format_exc()))

        threading.Thread(target=_worker, daemon=True).start()

    def _set_data_folder(self):
        folder = filedialog.askdirectory(title="Select folder containing CSV files")
        if folder:
            self._data_dir = folder
            self._set_status(f"Data folder set: {folder}")
            self._load_data()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _phase_title(self, parent, title: str, subtitle: str = ""):
        header = tk.Frame(parent, bg=BG_DARK)
        header.pack(fill="x", padx=20, pady=(16, 6))
        tk.Label(header, text=title, font=FONT_HEADING,
                 bg=BG_DARK, fg=TEXT_PRIMARY).pack(anchor="w")
        if subtitle:
            tk.Label(header, text=subtitle, font=("Segoe UI", 9),
                 bg=BG_DARK, fg=TEXT_MUTED).pack(anchor="w")
        separator(header).pack(fill="x", pady=(6, 0))

    def _scrolled_text(self, parent, height=20, width=80,
                       font=FONT_MONO, bg=BG_CARD) -> tk.Text:
        frame = tk.Frame(parent, bg=bg)
        frame.pack(fill="both", expand=True, padx=20, pady=(4, 12))

        text = tk.Text(frame, height=height, width=width, font=font,
                       bg=bg, fg=TEXT_PRIMARY,
                       insertbackground=ACCENT_BLUE,
                       relief="flat", wrap="none",
                       state="disabled")
        vsb = ttk.Scrollbar(frame, orient="vertical",   command=text.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=text.xview)
        text.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        text.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        return text

    @staticmethod
    def _set_text(widget: tk.Text, content: str):
        widget.config(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", content)
        widget.config(state="disabled")

    def _set_status(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.status_var.set(f"[{ts}]  {msg}")

    def _show_error(self, msg: str):
        self._set_status("⚠️ Error occurred.")
        messagebox.showerror("KMS Error", msg)

    def _check_data_loaded(self, auto_load: bool = False) -> bool:
        if self._dataframes is not None:
            return True
        if auto_load:
            self._load_data()
            return False
        self._show_error(
            "Data not loaded yet.\n"
            "Please click 'Load Data' on the Data Acquisition tab first,\n"
            "or use 'Set Data Folder' in the header."
        )
        return False

    def run(self):
        self.root.mainloop()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app = HospitalKMSApp()
    app.run()
