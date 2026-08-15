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
# Result dataclass & Fact definitions
# ---------------------------------------------------------------------------
@dataclass
class ServiceFact:
    week: int
    month: int
    service: str
    available_beds: int
    patients_request: int
    patients_admitted: int
    patients_refused: int
    bed_occupancy_rate: float
    refusal_rate: float
    patient_satisfaction: float
    staff_morale: float
    event: str
    demand_pressure: float = 0.0
    unmet_demand: int = 0
    consec_high_refusal: int = 0
    doctors_present: int = 0
    nurses_present: int = 0
    assistants_present: int = 0
    total_active_staff: int = 0
    patients_per_nurse: float = 0.0


@dataclass
class StaffFact:
    service: str
    role: str
    total_staff: int
    avg_presence_rate: float
    total_shifts: int = 0
    attended_shifts: int = 0


@dataclass
class PatientFact:
    service: str
    total_patients: int
    avg_length_of_stay: float
    avg_satisfaction: float
    pediatric_pct: float = 0.0
    adult_pct: float = 0.0
    geriatric_pct: float = 0.0


@dataclass
class RuleResult:
    service:       str
    rule_name:     str
    conclusion:    str
    severity:      str
    week:          int | None = None
    detail:        str = ""
    action_plan:   str = ""
    confidence:    float = 1.0

    def to_dict(self) -> dict:
        return {
            "service":       self.service,
            "rule_name":     self.rule_name,
            "conclusion":    self.conclusion,
            "severity":      self.severity,
            "week":          self.week if self.week is not None else "—",
            "detail":        self.detail,
            "action_plan":   self.action_plan,
            "confidence":    self.confidence,
        }


# ---------------------------------------------------------------------------
# Knowledge Engine
# ---------------------------------------------------------------------------
class HospitalExpertSystem:
    """
    Expert System Knowledge Engine coordinating facts and forward-chaining rules.
    """
    def __init__(self, dataframes: dict[str, pd.DataFrame]):
        self.dataframes = dataframes
        self.facts: dict[str, list[Any]] = self._extract_facts()

    def _extract_facts(self) -> dict[str, list[Any]]:
        facts: dict[str, list[Any]] = {
            "services": [],
            "staff": [],
            "patients": [],
        }
        if "service_stats" in self.dataframes:
            for _, r in self.dataframes["service_stats"].iterrows():
                facts["services"].append(ServiceFact(
                    week=int(r.get("week", 0)),
                    month=int(r.get("month", 0)),
                    service=str(r.get("service", "")),
                    available_beds=int(r.get("available_beds", 0)),
                    patients_request=int(r.get("patients_request", 0)),
                    patients_admitted=int(r.get("patients_admitted", 0)),
                    patients_refused=int(r.get("patients_refused", 0)),
                    bed_occupancy_rate=float(r.get("bed_occupancy_rate", 0.0)),
                    refusal_rate=float(r.get("refusal_rate", 0.0)),
                    patient_satisfaction=float(r.get("patient_satisfaction", 0.0)),
                    staff_morale=float(r.get("staff_morale", 0.0)),
                    event=str(r.get("event", "none")),
                    demand_pressure=float(r.get("demand_pressure", 0.0)),
                    unmet_demand=int(r.get("unmet_demand", 0)),
                    consec_high_refusal=int(r.get("consec_high_refusal", 0)),
                    doctors_present=int(r.get("doctors_present", 0)),
                    nurses_present=int(r.get("nurses_present", 0)),
                    patients_per_nurse=float(r.get("patients_per_nurse", 0.0)),
                ))
        if "staff_presence" in self.dataframes:
            for _, r in self.dataframes["staff_presence"].iterrows():
                facts["staff"].append(StaffFact(
                    service=str(r.get("service", "")),
                    role=str(r.get("role", "")),
                    total_staff=int(r.get("total_staff", 0)),
                    avg_presence_rate=float(r.get("avg_presence_rate", 0.0)),
                    total_shifts=int(r.get("total_shifts", 0)),
                    attended_shifts=int(r.get("attended_shifts", 0)),
                ))
        if "patient_stats" in self.dataframes:
            for _, r in self.dataframes["patient_stats"].iterrows():
                facts["patients"].append(PatientFact(
                    service=str(r.get("service", "")),
                    total_patients=int(r.get("total_patients", 0)),
                    avg_length_of_stay=float(r.get("avg_length_of_stay", 0.0)),
                    avg_satisfaction=float(r.get("avg_satisfaction", 0.0)),
                    pediatric_pct=float(r.get("pediatric_pct", 0.0)),
                    adult_pct=float(r.get("adult_pct", 0.0)),
                    geriatric_pct=float(r.get("geriatric_pct", 0.0)),
                ))
        return facts

    def run(self) -> list[dict]:
        return run_expert_system(self.dataframes)


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
        occ = row["bed_occupancy_rate"]
        morale = row["staff_morale"]
        conf = min(1.0, round(0.70 + (occ - 0.90) * 2.0 + (60 - morale) / 100 * 0.4, 2))
        results.append(RuleResult(
            service=row["service"],
            rule_name="Critical Overload",
            conclusion="Severe capacity crisis: bed occupancy exceeds 90% while staff morale is dangerously low.",
            severity="Critical",
            week=int(row["week"]),
            detail=f"Occupancy={occ:.0%}, Morale={morale:.0f}/100",
            action_plan="Activate emergency surge protocol; freeze elective admissions and deploy temporary float staff.",
            confidence=conf,
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
        ref_rate = row["refusal_rate"]
        conf = min(1.0, round(0.75 + (ref_rate - 0.75) * 1.0, 2))
        results.append(RuleResult(
            service=row["service"],
            rule_name="Emergency Access Crisis",
            conclusion="Emergency Department turning away over 75% of patients seeking urgent care.",
            severity="Critical",
            week=int(row["week"]),
            detail=f"Refusal={ref_rate:.0%} ({int(row['patients_refused'])} refused of {int(row['patients_request'])})",
            action_plan="Establish rapid step-down discharge pathways in general wards to open emergency intake beds.",
            confidence=conf,
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
        presence = row["avg_presence_rate"]
        conf = min(1.0, round(0.80 + (0.60 - presence) * 0.6, 2))
        results.append(RuleResult(
            service=row["service"],
            rule_name="Doctor Coverage Shortage",
            conclusion=f"Physician coverage in {row['service']} is critically below safe staffing thresholds.",
            severity="Critical",
            week=None,
            detail=f"Avg Doctor Presence={presence:.0%}, Total Doctors={int(row['total_staff'])}",
            action_plan="Initiate locum physician recruitment and authorize shift incentive premiums for on-call doctors.",
            confidence=conf,
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
        occ = row["bed_occupancy_rate"]
        conf = min(1.0, round(0.85 + (occ - 0.75) * 0.6, 2))
        results.append(RuleResult(
            service=row["service"],
            rule_name="Strike Operational Disruption",
            conclusion="Active strike event coinciding with high bed occupancy — immediate patient safety risk.",
            severity="Critical",
            week=int(row["week"]),
            detail=f"Occupancy={occ:.0%}, Morale={row['staff_morale']:.0f}, Event=strike",
            action_plan="Enact labor contingency framework; establish formal minimum emergency staffing agreements.",
            confidence=conf,
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
        consec = int(row["consec_high_refusal"])
        conf = min(1.0, round(0.75 + (consec - 3) * 0.08, 2))
        results.append(RuleResult(
            service=row["service"],
            rule_name="Bed Reallocation Needed",
            conclusion="Structural bed deficit: patient refusal rate exceeded 60% for 3+ consecutive weeks.",
            severity="High",
            week=int(row["week"]),
            detail=f"Refusal={row['refusal_rate']:.0%}, Consecutive Weeks={consec}",
            action_plan="Conduct executive bed reallocation audit; transfer surplus beds from low-utilization departments.",
            confidence=conf,
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
        press = row["demand_pressure"]
        conf = min(1.0, round(0.80 + (press - 3.0) * 0.05, 2))
        results.append(RuleResult(
            service=row["service"],
            rule_name="Flu Epidemic Surge Alert",
            conclusion="Seasonal flu outbreak driving extreme patient requests far exceeding normal capacity.",
            severity="High",
            week=int(row["week"]),
            detail=f"Demand={press:.1f}x bed capacity ({int(row['patients_request'])} requests for {int(row['available_beds'])} beds)",
            action_plan="Pre-position surge beds, set up dedicated respiratory triage, and authorize nursing overtime.",
            confidence=conf,
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
        diff = row["patients_refused"] - row["patients_admitted"]
        conf = min(1.0, round(0.70 + (diff / max(1, row["patients_request"])) * 0.3, 2))
        results.append(RuleResult(
            service=row["service"],
            rule_name="Demand Exceeds Capacity",
            conclusion="Department turned away more patients than it was able to admit this week.",
            severity="High",
            week=int(row["week"]),
            detail=f"Refused={int(row['patients_refused'])}, Admitted={int(row['patients_admitted'])}",
            action_plan="Accelerate daily discharge readiness rounds and expand temporary admissions quota.",
            confidence=conf,
        ))
    return results


def rule_nurse_workload_strain(service_stats: pd.DataFrame) -> list[RuleResult]:
    """
    Rule 8 — High Patient-to-Nurse Workload Ratio
    Condition: patients_per_nurse >= 3.0 or 0 active nurses with admitted patients
    Severity:  High
    """
    results = []
    if "patients_per_nurse" in service_stats.columns:
        mask = (service_stats["patients_per_nurse"] >= 3.0) | (
            (service_stats["nurses_present"] == 0) & (service_stats["patients_admitted"] > 0)
        )
        for _, row in service_stats[mask].iterrows():
            n_pres = int(row.get("nurses_present", 0))
            ratio_val = row["patients_per_nurse"]
            if n_pres == 0:
                ratio_str = "Critical (0 Active Nurses)"
                conf = 0.98
            else:
                ratio_str = f"{ratio_val:.1f}:1"
                conf = min(1.0, round(0.75 + (ratio_val - 3.0) * 0.08, 2))
            results.append(RuleResult(
                service=row["service"],
                rule_name="Nursing Workload Strain",
                conclusion="High patient-to-nurse ratio — active nursing staff stretched beyond optimal ratio.",
                severity="High",
                week=int(row["week"]),
                detail=f"Admissions={int(row['patients_admitted'])}, Active Nurses={n_pres}, Ratio={ratio_str}",
                action_plan="Deploy float pool nurses immediately to restore safe nurse-to-patient monitoring ratios.",
                confidence=conf,
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
        sat = row["patient_satisfaction"]
        mor = row["staff_morale"]
        conf = min(1.0, round(0.70 + (65 - sat) / 100 * 0.5 + (60 - mor) / 100 * 0.5, 2))
        results.append(RuleResult(
            service=row["service"],
            rule_name="Quality & Morale Drop",
            conclusion="Simultaneous breakdown in patient satisfaction and staff morale indicates systemic strain.",
            severity="Medium",
            week=int(row["week"]),
            detail=f"Patient Satisfaction={sat:.0f}/100, Staff Morale={mor:.0f}/100",
            action_plan="Conduct clinical leadership listening tours and implement targeted staff wellness initiatives.",
            confidence=conf,
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
        los = row["avg_length_of_stay"]
        conf = min(1.0, round(0.75 + (los - 7.5) * 0.08, 2))
        results.append(RuleResult(
            service=row["service"],
            rule_name="ICU Bed Turnover Bottleneck",
            conclusion="ICU average length of stay is prolonged, slowing bed turnover for incoming acute cases.",
            severity="Medium",
            week=None,
            detail=f"Avg Length of Stay={los:.1f} days, Total Patients={int(row['total_patients'])}",
            action_plan="Formalize daily multidisciplinary step-down rounds to transition stable patients to intermediate care.",
            confidence=conf,
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
            ger_pct = row["geriatric_pct"]
            conf = min(1.0, round(0.75 + (ger_pct - 28.0) * 0.03, 2))
            results.append(RuleResult(
                service=row["service"],
                rule_name="Geriatric Care Profile",
                conclusion="Department has a high proportion of elderly patients (65+) with extended stays requiring multidisciplinary care.",
                severity="Medium",
                week=None,
                detail=f"Geriatric Patients={ger_pct:.1f}%, Avg LOS={row['avg_length_of_stay']:.1f} days",
                action_plan="Assign dedicated geriatric clinical nurse specialists and initiate early rehabilitation discharge planning.",
                confidence=conf,
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
            morale = row["staff_morale"]
            conf = min(1.0, round(0.80 + (morale - 80) / 100 * 0.5, 2))
            results.append(RuleResult(
                service=row["service"],
                rule_name="Donation Resource Uplift",
                conclusion="Equipment/resource donation produced positive staff morale uplift and operational support.",
                severity="Low",
                week=int(row["week"]),
                detail=f"Morale={morale:.0f}/100, Satisfaction={row['patient_satisfaction']:.0f}/100, Event=donation",
                action_plan="Deploy newly donated equipment to bottlenecked clinical areas to sustain throughput gains.",
                confidence=conf,
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
            occ = row["bed_occupancy_rate"]
            conf = min(1.0, round(0.75 + (0.40 - occ) * 0.6, 2))
            results.append(RuleResult(
                service=row["service"],
                rule_name="Low Bed Utilisation",
                conclusion="Department experienced periods of under-utilized bed capacity without any patient refusals.",
                severity="Low",
                week=int(row["week"]),
                detail=f"Occupancy={occ:.0%}, Beds={int(row['available_beds'])}",
                action_plan="Designate surplus beds as hospital-wide flex beds to relieve adjacent high-demand wards.",
                confidence=conf,
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
            morale = row["staff_morale"]
            sat = row["patient_satisfaction"]
            conf = min(1.0, round(0.85 + (morale - 90) / 100 * 0.5 + (sat - 90) / 100 * 0.5, 2))
            results.append(RuleResult(
                service=row["service"],
                rule_name="Operational Excellence",
                conclusion="Department demonstrated peak operational harmony with high staff morale and patient satisfaction.",
                severity="Low",
                week=int(row["week"]),
                detail=f"Morale={morale:.0f}/100, Satisfaction={sat:.0f}/100",
                action_plan="Document shift scheduling and leadership workflows as internal hospital best-practice benchmarks.",
                confidence=conf,
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
