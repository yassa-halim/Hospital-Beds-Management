"""
data_loader.py
==============
Loads and preprocesses the four hospital CSV files.
All column names are read dynamically from the actual files — no assumptions.

Features & Analytics computed here:
  services:
    - bed_occupancy_rate   = patients_admitted / available_beds
    - refusal_rate         = patients_refused  / patients_request  (0 if request==0)
    - demand_pressure      = patients_request  / available_beds
    - unmet_demand         = patients_request - patients_admitted
    - weekly active staff counts by role merged directly with weekly service metrics
  patients:
    - length_of_stay       = (departure_date - arrival_date).days
    - age_group            = Pediatric (<18) | Adult (18-64) | Geriatric (65+)
  schedule & staff:
    - presence aggregated per (service, week), per (role, service, week), and per staff member
    - nurse-to-admitted-patient ratio and doctor availability per week
  department KPIs & event impact summaries
"""

from __future__ import annotations
import os
import pandas as pd
import numpy as np
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants — file names relative to the data directory
# ---------------------------------------------------------------------------
_FILE_MAP = {
    "patients": "patients.csv",
    "services": "services_weekly.csv",
    "staff":    "staff.csv",
    "schedule": "staff_schedule.csv",
}


class DataLoadError(Exception):
    """Raised when a required CSV file or column is missing."""


def _locate_data_dir(data_dir: str | None) -> Path:
    """Return the directory that contains the CSV files."""
    if data_dir is not None:
        p = Path(data_dir)
        if not p.is_dir():
            raise DataLoadError(f"Data directory not found: {data_dir}")
        return p
    # Default: dataset subfolder if it exists, else same folder as this script
    script_dir = Path(__file__).parent
    dataset_sub = script_dir / "dataset"
    if dataset_sub.is_dir() and (dataset_sub / "patients.csv").exists():
        return dataset_sub
    return script_dir


def _check_columns(df: pd.DataFrame, required: list[str], file_label: str) -> None:
    """Raise DataLoadError if any required column is missing."""
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise DataLoadError(
            f"[{file_label}] Missing columns: {missing}\n"
            f"  Found: {list(df.columns)}"
        )


# ---------------------------------------------------------------------------
# Individual loaders
# ---------------------------------------------------------------------------

def _load_patients(path: Path) -> pd.DataFrame:
    """Load patients.csv and add length_of_stay and age_group columns."""
    df = pd.read_csv(path)
    _check_columns(df, ["patient_id", "name", "age", "arrival_date", "departure_date", "service", "satisfaction"], "patients")

    df["arrival_date"]   = pd.to_datetime(df["arrival_date"],   errors="coerce")
    df["departure_date"] = pd.to_datetime(df["departure_date"], errors="coerce")
    df["length_of_stay"] = (df["departure_date"] - df["arrival_date"]).dt.days
    df["length_of_stay"] = df["length_of_stay"].clip(lower=0)

    # Demographic age grouping
    df["age_group"] = pd.cut(
        df["age"],
        bins=[-1, 17, 64, 150],
        labels=["Pediatric (<18)", "Adult (18-64)", "Geriatric (65+)"]
    )
    return df


def _load_services(path: Path) -> pd.DataFrame:
    """Load services_weekly.csv and add occupancy / refusal / demand derived columns."""
    df = pd.read_csv(path)
    _check_columns(
        df,
        ["week", "month", "service", "available_beds",
         "patients_request", "patients_admitted", "patients_refused",
         "patient_satisfaction", "staff_morale", "event"],
        "services_weekly"
    )

    # Derived rates
    df["bed_occupancy_rate"] = df.apply(
        lambda r: r["patients_admitted"] / r["available_beds"]
        if r["available_beds"] > 0 else 0.0,
        axis=1
    ).round(4)

    df["refusal_rate"] = df.apply(
        lambda r: r["patients_refused"] / r["patients_request"]
        if r["patients_request"] > 0 else 0.0,
        axis=1
    ).round(4)

    df["demand_pressure"] = df.apply(
        lambda r: r["patients_request"] / r["available_beds"]
        if r["available_beds"] > 0 else 0.0,
        axis=1
    ).round(4)

    df["unmet_demand"] = (df["patients_request"] - df["patients_admitted"]).clip(lower=0)

    return df


def _load_staff(path: Path) -> pd.DataFrame:
    """Load staff.csv."""
    df = pd.read_csv(path)
    _check_columns(df, ["staff_id", "staff_name", "role", "service"], "staff")
    return df


def _load_schedule(path: Path) -> pd.DataFrame:
    """Load staff_schedule.csv."""
    df = pd.read_csv(path)
    _check_columns(df, ["week", "staff_id", "staff_name", "role", "service", "present"], "staff_schedule")
    df["present"] = df["present"].astype(int)
    return df


# ---------------------------------------------------------------------------
# Aggregated helpers used by Expert System & GUI
# ---------------------------------------------------------------------------

def compute_staff_presence(schedule_df: pd.DataFrame) -> pd.DataFrame:
    """
    Return aggregated presence stats per (service, role):
        service, role, total_staff, avg_presence_rate, total_shifts, attended_shifts
    """
    per_staff = (
        schedule_df
        .groupby(["staff_id", "staff_name", "role", "service"])["present"]
        .agg(presence_rate="mean", total_shifts="count", attended_shifts="sum")
        .reset_index()
    )

    agg = (
        per_staff
        .groupby(["service", "role"])
        .agg(
            total_staff=("staff_id", "count"),
            avg_presence_rate=("presence_rate", "mean"),
            total_shifts=("total_shifts", "sum"),
            attended_shifts=("attended_shifts", "sum"),
        )
        .reset_index()
    )
    agg["avg_presence_rate"] = agg["avg_presence_rate"].round(4)
    return agg


def compute_weekly_staff_presence(schedule_df: pd.DataFrame) -> pd.DataFrame:
    """
    Return weekly staff counts by role per (week, service):
        week, service, doctors_present, nurses_present, assistants_present, total_active_staff
    """
    # Pivot presence by role
    grouped = schedule_df.groupby(["week", "service", "role"])["present"].sum().unstack(fill_value=0).reset_index()
    
    # Ensure all roles exist
    for role in ("doctor", "nurse", "nursing_assistant"):
        if role not in grouped.columns:
            grouped[role] = 0

    grouped = grouped.rename(columns={
        "doctor": "doctors_present",
        "nurse": "nurses_present",
        "nursing_assistant": "assistants_present"
    })
    grouped["total_active_staff"] = (
        grouped["doctors_present"] + grouped["nurses_present"] + grouped["assistants_present"]
    )
    return grouped


def compute_service_weekly_stats(services_df: pd.DataFrame, schedule_df: pd.DataFrame | None = None) -> pd.DataFrame:
    """
    Return services_df enriched with:
      - 'consec_high_refusal': consecutive weeks where refusal_rate > 0.60
      - 'doctors_present', 'nurses_present', 'total_active_staff' (if schedule provided)
      - 'patients_per_nurse': ratio of admitted patients to active nurses
    """
    df = services_df.copy().sort_values(["service", "week"]).reset_index(drop=True)

    consec_col = [0] * len(df)
    for service in df["service"].unique():
        mask = df["service"] == service
        indices = df.index[mask].tolist()
        count = 0
        for idx in indices:
            if df.at[idx, "refusal_rate"] > 0.60:
                count += 1
            else:
                count = 0
            consec_col[idx] = count

    df["consec_high_refusal"] = consec_col

    if schedule_df is not None:
        weekly_staff = compute_weekly_staff_presence(schedule_df)
        df = pd.merge(df, weekly_staff, on=["week", "service"], how="left")
        df["doctors_present"] = df["doctors_present"].fillna(0).astype(int)
        df["nurses_present"] = df["nurses_present"].fillna(0).astype(int)
        df["total_active_staff"] = df["total_active_staff"].fillna(0).astype(int)

        df["patients_per_nurse"] = df.apply(
            lambda r: round(r["patients_admitted"] / r["nurses_present"], 2)
            if r["nurses_present"] > 0 else float("inf"),
            axis=1
        )

    return df


def compute_patient_stats(patients_df: pd.DataFrame) -> pd.DataFrame:
    """
    Return comprehensive per-service patient statistics:
        service, total_patients, avg_length_of_stay, avg_satisfaction,
        pediatric_pct, adult_pct, geriatric_pct
    """
    base_stats = (
        patients_df
        .groupby("service")
        .agg(
            total_patients=("patient_id", "count"),
            avg_length_of_stay=("length_of_stay", "mean"),
            avg_satisfaction=("satisfaction", "mean"),
        )
        .reset_index()
    )
    base_stats["avg_length_of_stay"] = base_stats["avg_length_of_stay"].round(2)
    base_stats["avg_satisfaction"]   = base_stats["avg_satisfaction"].round(2)

    # Demographic breakdown
    demo = pd.crosstab(patients_df["service"], patients_df["age_group"], normalize="index") * 100
    demo = demo.round(1).reset_index()
    demo = demo.rename(columns={
        "Pediatric (<18)": "pediatric_pct",
        "Adult (18-64)": "adult_pct",
        "Geriatric (65+)": "geriatric_pct",
    })

    merged = pd.merge(base_stats, demo, on="service", how="left")
    return merged


def compute_department_kpis(services_df: pd.DataFrame, patients_df: pd.DataFrame, staff_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute high-level executive KPIs for each department across the 52 weeks.
    """
    srv_agg = (
        services_df
        .groupby("service")
        .agg(
            avg_available_beds=("available_beds", "mean"),
            total_requests=("patients_request", "sum"),
            total_admitted=("patients_admitted", "sum"),
            total_refused=("patients_refused", "sum"),
            avg_occupancy=("bed_occupancy_rate", "mean"),
            avg_morale=("staff_morale", "mean"),
            avg_service_satisfaction=("patient_satisfaction", "mean"),
        )
        .reset_index()
    )
    srv_agg["overall_refusal_rate"] = (srv_agg["total_refused"] / srv_agg["total_requests"]).round(4)
    srv_agg["avg_occupancy"] = srv_agg["avg_occupancy"].round(4)
    srv_agg["avg_available_beds"] = srv_agg["avg_available_beds"].round(1)
    srv_agg["avg_morale"] = srv_agg["avg_morale"].round(1)
    srv_agg["avg_service_satisfaction"] = srv_agg["avg_service_satisfaction"].round(1)

    staff_counts = staff_df.groupby("service")["staff_id"].count().reset_index().rename(columns={"staff_id": "total_staff"})
    patient_counts = patients_df.groupby("service")["patient_id"].count().reset_index().rename(columns={"patient_id": "total_patients_recorded"})

    kpi_df = pd.merge(srv_agg, staff_counts, on="service", how="left")
    kpi_df = pd.merge(kpi_df, patient_counts, on="service", how="left")
    return kpi_df


def compute_event_impacts(services_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute operational comparison across event types: flu, strike, donation, none.
    """
    evt = (
        services_df
        .groupby("event")
        .agg(
            weeks_count=("week", "count"),
            avg_requests=("patients_request", "mean"),
            avg_admitted=("patients_admitted", "mean"),
            avg_refused=("patients_refused", "mean"),
            avg_occupancy=("bed_occupancy_rate", "mean"),
            avg_refusal_rate=("refusal_rate", "mean"),
            avg_morale=("staff_morale", "mean"),
            avg_satisfaction=("patient_satisfaction", "mean"),
        )
        .reset_index()
    )
    for col in ("avg_requests", "avg_admitted", "avg_refused", "avg_morale", "avg_satisfaction"):
        evt[col] = evt[col].round(1)
    for col in ("avg_occupancy", "avg_refusal_rate"):
        evt[col] = (evt[col] * 100).round(1)
    return evt


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

def load_all_data(data_dir: str | None = None) -> dict[str, pd.DataFrame]:
    """
    Load all four CSV files from *data_dir* (defaults to the script's folder or dataset subfolder).

    Returns
    -------
    dict with keys:
        'patients'         — raw patients DataFrame (+ length_of_stay, age_group)
        'services'         — services_weekly DataFrame (+ derived rates)
        'staff'            — staff DataFrame
        'schedule'         — staff_schedule DataFrame
        'staff_presence'   — aggregated presence stats per service/role
        'weekly_staff'     — weekly active staff counts by role
        'service_stats'    — services enriched with consecutive refusal and weekly staff
        'patient_stats'    — per-service patient demographics and length of stay
        'department_kpis'  — executive KPI matrix per department
        'event_impacts'    — operational comparison across event types
    """
    base = _locate_data_dir(data_dir)

    results = {}
    for key, fname in _FILE_MAP.items():
        fpath = base / fname
        if not fpath.exists():
            raise DataLoadError(f"File not found: {fpath}")

    # Load raw frames
    results["patients"] = _load_patients(base / _FILE_MAP["patients"])
    results["services"] = _load_services(base / _FILE_MAP["services"])
    results["staff"]    = _load_staff(base / _FILE_MAP["staff"])
    results["schedule"] = _load_schedule(base / _FILE_MAP["schedule"])

    # Derived aggregates
    results["staff_presence"] = compute_staff_presence(results["schedule"])
    results["weekly_staff"]   = compute_weekly_staff_presence(results["schedule"])
    results["service_stats"]  = compute_service_weekly_stats(results["services"], results["schedule"])
    results["patient_stats"]  = compute_patient_stats(results["patients"])
    results["department_kpis"] = compute_department_kpis(results["services"], results["patients"], results["staff"])
    results["event_impacts"]   = compute_event_impacts(results["services"])

    return results


def get_summary(dataframes: dict[str, pd.DataFrame]) -> list[dict]:
    """
    Return a list of summary dicts for the GUI Data Acquisition tab.
    Each dict: {name, rows, cols, columns, sample}
    """
    summary = []
    for key in ("patients", "services", "staff", "schedule"):
        df = dataframes[key]
        summary.append({
            "name":    _FILE_MAP[key],
            "rows":    len(df),
            "cols":    len(df.columns),
            "columns": list(df.columns),
            "sample":  df.head(5),
        })
    return summary


# ---------------------------------------------------------------------------
# CLI test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        dfs = load_all_data()
        print("[OK] All files loaded successfully!")
        for s in get_summary(dfs):
            print(f"  {s['name']:35s} -- {s['rows']} rows x {s['cols']} cols")
        print("\nDepartment KPIs:")
        print(dfs["department_kpis"].to_string(index=False))
        print("\nEvent Impacts:")
        print(dfs["event_impacts"].to_string(index=False))
        print("\nPatient Stats:")
        print(dfs["patient_stats"].to_string(index=False))
    except DataLoadError as e:
        print(f"[Error] {e}")
