"""
expert_system.py
================
Hospital Expert System / Rule Engine.

Pure-Python forward-chaining rule engine grounded in real hospital operational data:
  - Bed capacity, occupancy, and refusal dynamics
  - Staffing attendance rates, doctor coverage, and nurse-to-patient ratios
  - Epidemic flu surges, labour strikes, and resource donations
  - Patient demographics (geriatric/pediatric), length of stay, and satisfaction

Public API:
    run_expert_system(dataframes) -> list[dict]
"""

from __future__ import annotations
import pandas as pd
from dataclasses import dataclass
from typing import Any


# ---------------------------------------------------------------------------
# Severity ordering (for sorting / colour-coding)
# ---------------------------------------------------------------------------
SEVERITY_ORDER = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------
@dataclass
class RuleResult:
    service:    str
    rule_name:  str
    conclusion: str
    severity:   str
    week:       int | None = None
    detail:     str = ""

    def to_dict(self) -> dict:
        return {
            "service":    self.service,
            "rule_name":  self.rule_name,
            "conclusion": self.conclusion,
            "severity":   self.severity,
            "week":       self.week if self.week is not None else "—",
            "detail":     self.detail,
        }


# ---------------------------------------------------------------------------
# Rule Definitions
# ---------------------------------------------------------------------------

def rule_critical_overload(services_df: pd.DataFrame) -> list[RuleResult]:
    """
    Rule 1 — Critical Overload: Bed & Staff Morale Crisis
    Condition: bed_occupancy_rate > 0.90 AND staff_morale < 60
    Severity:  Critical
    """
    results = []
    mask = (services_df["bed_occupancy_rate"] > 0.90) & (services_df["staff_morale"] < 60)
    for _, row in services_df[mask].iterrows():
        results.append(RuleResult(
            service=row["service"],
            rule_name="Critical Overload",
            conclusion="Severe capacity crisis: bed occupancy exceeds 90% while staff morale is dangerously low.",
            severity="Critical",
            week=int(row["week"]),
            detail=f"Occupancy={row['bed_occupancy_rate']:.0%}, Morale={row['staff_morale']:.0f}/100",
        ))
    return results


def rule_emergency_crisis(services_df: pd.DataFrame) -> list[RuleResult]:
    """
    Rule 2 — Emergency Department Extreme Refusal
    Condition: service == 'emergency' AND refusal_rate > 0.75
    Severity:  Critical
    """
    results = []
    mask = (services_df["service"] == "emergency") & (services_df["refusal_rate"] > 0.75)
    for _, row in services_df[mask].iterrows():
        results.append(RuleResult(
            service=row["service"],
            rule_name="Emergency Access Crisis",
            conclusion="Emergency Department turning away over 75% of patients seeking urgent care.",
            severity="Critical",
            week=int(row["week"]),
            detail=f"Refusal={row['refusal_rate']:.0%} ({int(row['patients_refused'])} refused of {int(row['patients_request'])})",
        ))
    return results


def rule_doctor_shortage(staff_presence: pd.DataFrame, service_stats: pd.DataFrame) -> list[RuleResult]:
    """
    Rule 3 — Medical Doctor Shortage & Coverage Gaps
    Condition: role == 'doctor' AND avg_presence_rate < 0.60
    Severity:  Critical
    """
    results = []
    low_docs = staff_presence[(staff_presence["role"] == "doctor") & (staff_presence["avg_presence_rate"] < 0.60)]
    for _, row in low_docs.iterrows():
        results.append(RuleResult(
            service=row["service"],
            rule_name="Doctor Coverage Shortage",
            conclusion=f"Physician coverage in {row['service']} is critically below safe staffing thresholds.",
            severity="Critical",
            week=None,
            detail=f"Avg Doctor Presence={row['avg_presence_rate']:.0%}, Total Doctors={int(row['total_staff'])}",
        ))
    return results


def rule_strike_impact(services_df: pd.DataFrame) -> list[RuleResult]:
    """
    Rule 4 — Labour Strike Impact on Hospital Capacity
    Condition: event == 'strike' AND bed_occupancy_rate > 0.75
    Severity:  Critical
    """
    results = []
    mask = (services_df["event"] == "strike") & (services_df["bed_occupancy_rate"] > 0.75)
    for _, row in services_df[mask].iterrows():
        results.append(RuleResult(
            service=row["service"],
            rule_name="Strike Operational Disruption",
            conclusion="Active strike event coinciding with high bed occupancy — immediate patient safety risk.",
            severity="Critical",
            week=int(row["week"]),
            detail=f"Occupancy={row['bed_occupancy_rate']:.0%}, Morale={row['staff_morale']:.0f}, Event=strike",
        ))
    return results


def rule_bed_reallocation(service_stats: pd.DataFrame) -> list[RuleResult]:
    """
    Rule 5 — Chronic Bed Refusal (3+ consecutive weeks > 60%)
    Severity:  High
    """
    results = []
    triggered = service_stats[service_stats["consec_high_refusal"] >= 3]
    for _, row in triggered.iterrows():
        results.append(RuleResult(
            service=row["service"],
            rule_name="Bed Reallocation Needed",
            conclusion="Structural bed deficit: patient refusal rate exceeded 60% for 3+ consecutive weeks.",
            severity="High",
            week=int(row["week"]),
            detail=f"Refusal={row['refusal_rate']:.0%}, Consecutive Weeks={int(row['consec_high_refusal'])}",
        ))
    return results


def rule_flu_surge(services_df: pd.DataFrame) -> list[RuleResult]:
    """
    Rule 6 — Seasonal Flu Surge Demand Emergency
    Condition: event == 'flu' AND demand_pressure > 3.0
    Severity:  High
    """
    results = []
    mask = (services_df["event"] == "flu") & (services_df["demand_pressure"] > 3.0)
    for _, row in services_df[mask].iterrows():
        results.append(RuleResult(
            service=row["service"],
            rule_name="Flu Epidemic Surge Alert",
            conclusion="Seasonal flu outbreak driving extreme patient requests far exceeding normal capacity.",
            severity="High",
            week=int(row["week"]),
            detail=f"Demand={row['demand_pressure']:.1f}x bed capacity ({int(row['patients_request'])} requests for {int(row['available_beds'])} beds)",
        ))
    return results


def rule_demand_exceeds_supply(services_df: pd.DataFrame) -> list[RuleResult]:
    """
    Rule 7 — Demand Exceeds Supply
    Condition: patients_refused > patients_admitted
    Severity:  High
    """
    results = []
    mask = services_df["patients_refused"] > services_df["patients_admitted"]
    for _, row in services_df[mask].iterrows():
        results.append(RuleResult(
            service=row["service"],
            rule_name="Demand Exceeds Capacity",
            conclusion="Department turned away more patients than it was able to admit this week.",
            severity="High",
            week=int(row["week"]),
            detail=f"Refused={int(row['patients_refused'])}, Admitted={int(row['patients_admitted'])}",
        ))
    return results


def rule_nurse_workload_strain(service_stats: pd.DataFrame) -> list[RuleResult]:
    """
    Rule 8 — High Patient-to-Nurse Workload Ratio
    Condition: patients_per_nurse >= 3.0 (weekly admissions vs active nurses)
    Severity:  High
    """
    results = []
    if "patients_per_nurse" in service_stats.columns:
        mask = (service_stats["patients_per_nurse"] >= 3.0) & (service_stats["patients_per_nurse"] != float("inf"))
        for _, row in service_stats[mask].iterrows():
            results.append(RuleResult(
                service=row["service"],
                rule_name="Nursing Workload Strain",
                conclusion="High patient-to-nurse ratio — active nursing staff stretched beyond optimal ratio.",
                severity="High",
                week=int(row["week"]),
                detail=f"Admissions={int(row['patients_admitted'])}, Active Nurses={int(row.get('nurses_present', 0))}, Ratio={row['patients_per_nurse']:.1f}:1",
            ))
    return results


def rule_service_quality_degradation(services_df: pd.DataFrame) -> list[RuleResult]:
    """
    Rule 9 — Service Quality & Burnout Degradation
    Condition: patient_satisfaction < 65 AND staff_morale < 60
    Severity:  Medium
    """
    results = []
    mask = (services_df["patient_satisfaction"] < 65) & (services_df["staff_morale"] < 60)
    for _, row in services_df[mask].iterrows():
        results.append(RuleResult(
            service=row["service"],
            rule_name="Quality & Morale Drop",
            conclusion="Simultaneous breakdown in patient satisfaction and staff morale indicates systemic strain.",
            severity="Medium",
            week=int(row["week"]),
            detail=f"Patient Satisfaction={row['patient_satisfaction']:.0f}/100, Staff Morale={row['staff_morale']:.0f}/100",
        ))
    return results


def rule_icu_long_stay(patient_stats: pd.DataFrame) -> list[RuleResult]:
    """
    Rule 10 — ICU Prolonged Stay Turnover Bottleneck
    Condition: service == 'ICU' AND avg_length_of_stay > 7.5 days
    Severity:  Medium
    """
    results = []
    icu = patient_stats[(patient_stats["service"] == "ICU") & (patient_stats["avg_length_of_stay"] > 7.5)]
    for _, row in icu.iterrows():
        results.append(RuleResult(
            service=row["service"],
            rule_name="ICU Bed Turnover Bottleneck",
            conclusion="ICU average length of stay is prolonged, slowing bed turnover for incoming acute cases.",
            severity="Medium",
            week=None,
            detail=f"Avg Length of Stay={row['avg_length_of_stay']:.1f} days, Total Patients={int(row['total_patients'])}",
        ))
    return results


def rule_geriatric_care_complexity(patient_stats: pd.DataFrame) -> list[RuleResult]:
    """
    Rule 11 — Geriatric Care High-Demand Profile
    Condition: geriatric_pct > 28.0% AND avg_length_of_stay > 7.5 days
    Severity:  Medium
    """
    results = []
    if "geriatric_pct" in patient_stats.columns:
        high_ger = patient_stats[(patient_stats["geriatric_pct"] > 28.0) & (patient_stats["avg_length_of_stay"] > 7.5)]
        for _, row in high_ger.iterrows():
            results.append(RuleResult(
                service=row["service"],
                rule_name="Geriatric Care Profile",
                conclusion="Department has a high proportion of elderly patients (65+) with extended stays requiring multidisciplinary care.",
                severity="Medium",
                week=None,
                detail=f"Geriatric Patients={row['geriatric_pct']:.1f}%, Avg LOS={row['avg_length_of_stay']:.1f} days",
            ))
    return results


def rule_donation_uplift(services_df: pd.DataFrame) -> list[RuleResult]:
    """
    Rule 12 — Resource Donation Positive Impact
    Condition: event == 'donation' AND staff_morale >= 80
    Severity:  Low (Positive Milestone)
    """
    results = []
    mask = (services_df["event"] == "donation") & (services_df["staff_morale"] >= 80)
    seen = set()
    for _, row in services_df[mask].iterrows():
        if row["service"] not in seen:
            seen.add(row["service"])
            results.append(RuleResult(
                service=row["service"],
                rule_name="Donation Resource Uplift",
                conclusion="Equipment/resource donation produced positive staff morale uplift and operational support.",
                severity="Low",
                week=int(row["week"]),
                detail=f"Morale={row['staff_morale']:.0f}/100, Satisfaction={row['patient_satisfaction']:.0f}/100, Event=donation",
            ))
    return results


def rule_low_bed_utilisation(services_df: pd.DataFrame) -> list[RuleResult]:
    """
    Rule 13 — Low Bed Utilisation & Surplus
    Condition: bed_occupancy_rate < 0.40 AND patients_refused == 0
    Severity:  Low (Opportunity for reallocation)
    """
    results = []
    mask = (services_df["bed_occupancy_rate"] < 0.40) & (services_df["patients_refused"] == 0)
    seen = set()
    for _, row in services_df[mask].iterrows():
        if row["service"] not in seen:
            seen.add(row["service"])
            results.append(RuleResult(
                service=row["service"],
                rule_name="Low Bed Utilisation",
                conclusion="Department experienced periods of under-utilized bed capacity without any patient refusals.",
                severity="Low",
                week=int(row["week"]),
                detail=f"Occupancy={row['bed_occupancy_rate']:.0%}, Beds={int(row['available_beds'])}",
            ))
    return results


def rule_optimal_performance(services_df: pd.DataFrame) -> list[RuleResult]:
    """
    Rule 14 — Optimal Performance Benchmark
    Condition: staff_morale > 90 AND patient_satisfaction > 90
    Severity:  Low (Best Practice Benchmark)
    """
    results = []
    mask = (services_df["staff_morale"] > 90) & (services_df["patient_satisfaction"] > 90)
    seen = set()
    for _, row in services_df[mask].iterrows():
        if row["service"] not in seen:
            seen.add(row["service"])
            results.append(RuleResult(
                service=row["service"],
                rule_name="Operational Excellence",
                conclusion="Department demonstrated peak operational harmony with high staff morale and patient satisfaction.",
                severity="Low",
                week=int(row["week"]),
                detail=f"Morale={row['staff_morale']:.0f}/100, Satisfaction={row['patient_satisfaction']:.0f}/100",
            ))
    return results


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

def run_expert_system(dataframes: dict) -> list[dict]:
    """
    Run all 14 clinical and operational rules against the loaded DataFrames.

    Parameters
    ----------
    dataframes : dict returned by data_loader.load_all_data()

    Returns
    -------
    list of dicts sorted by severity (Critical first) then service and week.
    """
    services_df    = dataframes["services"]
    service_stats  = dataframes["service_stats"]
    staff_presence = dataframes["staff_presence"]
    patient_stats  = dataframes["patient_stats"]

    all_results: list[RuleResult] = []

    # Run every rule
    all_results.extend(rule_critical_overload(services_df))
    all_results.extend(rule_emergency_crisis(services_df))
    all_results.extend(rule_doctor_shortage(staff_presence, service_stats))
    all_results.extend(rule_strike_impact(services_df))
    all_results.extend(rule_bed_reallocation(service_stats))
    all_results.extend(rule_flu_surge(services_df))
    all_results.extend(rule_demand_exceeds_supply(services_df))
    all_results.extend(rule_nurse_workload_strain(service_stats))
    all_results.extend(rule_service_quality_degradation(services_df))
    all_results.extend(rule_icu_long_stay(patient_stats))
    all_results.extend(rule_geriatric_care_complexity(patient_stats))
    all_results.extend(rule_donation_uplift(services_df))
    all_results.extend(rule_low_bed_utilisation(services_df))
    all_results.extend(rule_optimal_performance(services_df))

    # Sort: Critical (4) > High (3) > Medium (2) > Low (1), then service, then week
    all_results.sort(
        key=lambda r: (
            -SEVERITY_ORDER.get(r.severity, 0),
            r.service,
            r.week if (r.week is not None and isinstance(r.week, int)) else 0,
        )
    )

    return [r.to_dict() for r in all_results]


# ---------------------------------------------------------------------------
# CLI test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    from collections import Counter
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    from data_loader import load_all_data

    try:
        dfs = load_all_data()
        results = run_expert_system(dfs)
        counts = Counter(r["severity"] for r in results)
        print(f"[OK] Expert System generated {len(results)} conclusions:")
        print(f"     🔴 Critical: {counts.get('Critical', 0)}")
        print(f"     🟠 High:     {counts.get('High', 0)}")
        print(f"     🟡 Medium:   {counts.get('Medium', 0)}")
        print(f"     🟢 Low:      {counts.get('Low', 0)}\n")

        print("Sample conclusions:")
        for r in results[:10]:
            print(f"  [{r['severity']:8s}] {r['service']:18s} | {r['rule_name']:30s} | Wk: {r['week']}")
    except Exception as e:
        print(f"[ERROR] {e}")
