"""
Peak-and-decline scoring module for TherapyGraveyard.

Assigns each intervention a status:
  DEAD     - decline >= 0.9 AND years_silent >= 3
  ZOMBIE   - would be DEAD but has trial in 2024 or 2025
  DECLINING - decline >= 0.5 AND years_silent >= 1
  ALIVE    - everything else that qualifies
  SKIPPED  - peak_count < 3

Functions:
  score_intervention(entry) -> dict (adds scoring fields)
  score_all(interventions) -> list[dict]
  link_kill_events(scored, kill_events) -> list[dict]
  score_file(input_path, kill_events_path, output_path) -> list[dict]
"""

import io
import json
import os
import sys

if sys.platform == "win32" and not getattr(sys.stdout, "_tg_utf8", False):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stdout._tg_utf8 = True

START_YEAR = 2005
END_YEAR = 2025
N_YEARS = END_YEAR - START_YEAR + 1  # 21

# Status severity for sorting (lower = more severe)
_STATUS_SEVERITY = {
    "DEAD": 0,
    "ZOMBIE": 1,
    "DECLINING": 2,
    "ALIVE": 3,
    "SKIPPED": 4,
}


def _rolling_avg(counts, window=3):
    """
    Compute rolling average with edge padding.
    For positions near edges, the window is reduced to available data.
    """
    n = len(counts)
    smoothed = [0.0] * n
    half = window // 2
    for i in range(n):
        lo = max(0, i - half)
        hi = min(n - 1, i + half)
        span = counts[lo:hi + 1]
        smoothed[i] = sum(span) / len(span) if span else 0.0
    return smoothed


def score_intervention(entry):
    """
    Score a single intervention entry.
    Mutates and returns the entry with added fields:
      smoothed_counts, peak_year, peak_count, recent_count,
      decline_ratio, years_silent, status, half_life, lifespan
    """
    counts = entry.get("yearly_counts", [0] * N_YEARS)

    # 1. Smooth with rolling average
    smoothed = _rolling_avg(counts, window=3)
    entry["smoothed_counts"] = [round(s, 2) for s in smoothed]

    # 2. Find peak
    peak_val = max(smoothed) if smoothed else 0
    peak_idx = smoothed.index(peak_val) if peak_val > 0 else 0
    peak_year = START_YEAR + peak_idx
    # Use raw count at peak index for peak_count
    peak_count = max(counts) if counts else 0

    entry["peak_year"] = peak_year
    entry["peak_count"] = peak_count

    # 3. Skip if peak_count < 3
    if peak_count < 3:
        entry["status"] = "SKIPPED"
        entry["recent_count"] = 0
        entry["decline_ratio"] = 0
        entry["years_silent"] = 0
        entry["half_life"] = None
        entry["lifespan"] = 0
        return entry

    # 4. Recent count = mean of last 3 years (indices 18, 19, 20)
    last3 = counts[N_YEARS - 3:N_YEARS]
    recent_count = sum(last3) / len(last3) if last3 else 0
    entry["recent_count"] = round(recent_count, 2)

    # 5. Decline ratio = 1 - (recent / peak), clamped [0, 1]
    if peak_count > 0:
        decline = 1.0 - (recent_count / peak_count)
        decline = max(0.0, min(1.0, decline))
    else:
        decline = 0.0
    entry["decline_ratio"] = round(decline, 3)

    # 6. Years silent = years since last year with count >= 1
    last_active_idx = -1
    for i in range(N_YEARS - 1, -1, -1):
        if counts[i] >= 1:
            last_active_idx = i
            break
    if last_active_idx >= 0:
        last_active_year = START_YEAR + last_active_idx
        years_silent = END_YEAR - last_active_year
    else:
        years_silent = N_YEARS
    entry["years_silent"] = years_silent

    # 7. Status assignment
    # Check for recent activity (2024 or 2025)
    has_recent = (counts[N_YEARS - 2] >= 1) or (counts[N_YEARS - 1] >= 1)  # 2024 or 2025

    # For ZOMBIE detection: compute years_silent EXCLUDING last 2 years
    # to see if the intervention *would have been* dead before recent resurrection
    last_active_before_recent = -1
    for i in range(N_YEARS - 3, -1, -1):  # up to index 18 (year 2023)
        if counts[i] >= 1:
            last_active_before_recent = i
            break
    if last_active_before_recent >= 0:
        gap_before_recent = (END_YEAR - 2) - (START_YEAR + last_active_before_recent)
    else:
        gap_before_recent = N_YEARS

    if decline >= 0.9 and years_silent >= 3:
        entry["status"] = "DEAD"
    elif decline >= 0.9 and has_recent and gap_before_recent >= 3:
        entry["status"] = "ZOMBIE"
    elif decline >= 0.5 and years_silent >= 1:
        entry["status"] = "DECLINING"
    else:
        entry["status"] = "ALIVE"

    # 8. Half-life: years from peak to first smoothed < peak/2
    half_target = peak_val / 2.0
    half_life = None
    for i in range(peak_idx + 1, len(smoothed)):
        if smoothed[i] < half_target:
            half_life = i - peak_idx
            break
    entry["half_life"] = half_life

    # 9. Lifespan = last active year - first active year + 1
    first_active_idx = -1
    for i in range(N_YEARS):
        if counts[i] >= 1:
            first_active_idx = i
            break
    if first_active_idx >= 0 and last_active_idx >= 0:
        entry["lifespan"] = (START_YEAR + last_active_idx) - (START_YEAR + first_active_idx) + 1
    else:
        entry["lifespan"] = 0

    return entry


def score_all(interventions):
    """
    Score all interventions. Filter out SKIPPED. Sort by status severity
    then total_trials descending.
    """
    scored = []
    for entry in interventions:
        score_intervention(entry)
        if entry.get("status") != "SKIPPED":
            scored.append(entry)

    scored.sort(key=lambda x: (
        _STATUS_SEVERITY.get(x.get("status", "ALIVE"), 99),
        -x.get("total_trials", 0),
    ))
    return scored


def link_kill_events(scored, kill_events):
    """
    Match kill events to scored interventions by name or class.
    Sets probable_cause if event year is within +/-2 of peak_year.
    """
    for entry in scored:
        name = entry.get("intervention", "").lower().replace(" ", "_")
        drug_class = entry.get("drug_class", "").lower()
        peak_year = entry.get("peak_year", 0)

        matched_events = []
        for ke in kill_events:
            # Check intervention name match
            ke_interventions = [iv.lower() for iv in ke.get("interventions", [])]
            ke_classes = [cl.lower() for cl in ke.get("classes", [])]
            ke_year = ke.get("year", 0)

            name_match = name in ke_interventions or entry.get("intervention", "").lower() in ke_interventions
            class_match = drug_class in ke_classes and drug_class != "unknown"

            if name_match or class_match:
                # Check year proximity
                if abs(ke_year - peak_year) <= 2:
                    matched_events.append({
                        "id": ke["id"],
                        "year": ke_year,
                        "event": ke["event"],
                        "category": ke.get("category", ""),
                    })

        if matched_events:
            entry["probable_cause"] = matched_events
        else:
            entry["probable_cause"] = None

    return scored


def score_file(input_path, kill_events_path, output_path):
    """
    Load normalized data, score, link kill events, save.
    Returns scored list.
    """
    with open(input_path, "r", encoding="utf-8") as f:
        interventions = json.load(f)
    print(f"Loaded {len(interventions)} interventions from {input_path}")

    with open(kill_events_path, "r", encoding="utf-8") as f:
        kill_events = json.load(f)
    print(f"Loaded {len(kill_events)} kill events")

    scored = score_all(interventions)
    print(f"Scored {len(scored)} interventions (excluded SKIPPED)")

    link_kill_events(scored, kill_events)

    # Print status breakdown
    status_counts = {}
    for entry in scored:
        st = entry.get("status", "UNKNOWN")
        status_counts[st] = status_counts.get(st, 0) + 1

    print("\nStatus breakdown:")
    for st in ["DEAD", "ZOMBIE", "DECLINING", "ALIVE"]:
        count = status_counts.get(st, 0)
        print(f"  {st:>10}: {count}")

    linked = sum(1 for e in scored if e.get("probable_cause"))
    print(f"\n  Kill events linked: {linked}")

    # Save
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(scored, f, indent=2, ensure_ascii=False)
    size_kb = os.path.getsize(output_path) / 1024
    print(f"\nSaved to {output_path} ({size_kb:.1f} KB)")

    return scored


if __name__ == "__main__":
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    inp = os.path.join(base, "data", "cv_interventions_normalized.json")
    ke = os.path.join(base, "data", "kill_events.json")
    out = os.path.join(base, "data", "cv_interventions_scored.json")
    score_file(inp, ke, out)
    print("Done.")
