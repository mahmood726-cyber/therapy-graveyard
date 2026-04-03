"""
JSON export module for TherapyGraveyard.

Builds the final training data JSON used by the HTML frontend:
  - Molecule-level scored data (nct_ids stripped, count only)
  - Class-level roll-ups (aggregated across molecules in same class)

Functions:
  build_training_data(scored_path, kill_events_path, output_path) -> dict
"""

import json
import os
import sys
from datetime import datetime, timezone

try:
    from pipeline import ensure_utf8_stdout
    ensure_utf8_stdout()
except ImportError:
    import io
    if sys.platform == "win32" and not getattr(sys.stdout, "_tg_utf8", False):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stdout._tg_utf8 = True

# Import scoring functions for class-level re-scoring
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from score import score_all, link_kill_events, START_YEAR, END_YEAR, N_YEARS


def build_training_data(scored_path, kill_events_path, output_path):
    """
    Build the final export JSON for the HTML frontend.

    Steps:
      1. Load scored data, strip nct_ids (keep count only)
      2. Build class-level roll-ups
      3. Output combined JSON
    """
    with open(scored_path, "r", encoding="utf-8") as f:
        scored = json.load(f)
    print(f"Loaded {len(scored)} scored molecules")

    with open(kill_events_path, "r", encoding="utf-8") as f:
        kill_events = json.load(f)

    # ── 1. Strip nct_ids from molecule-level data ───────────────────
    molecules = []
    for entry in scored:
        mol = dict(entry)
        nct_ids = mol.pop("nct_ids", [])
        mol["trial_count_unique"] = len(nct_ids) if isinstance(nct_ids, list) else 0
        molecules.append(mol)

    # ── 2. Build class-level roll-ups ───────────────────────────────
    class_groups = {}
    for mol in molecules:
        cls = mol.get("drug_class", "unknown")
        cat = mol.get("category", "unknown")
        itype = mol.get("classified_type", mol.get("intervention_type", "unknown"))

        if cls == "unknown":
            continue

        if cls not in class_groups:
            class_groups[cls] = {
                "intervention": cls,
                "intervention_type": itype,
                "drug_class": cls,
                "category": cat,
                "classified_type": itype,
                "yearly_counts": [0] * N_YEARS,
                "yearly_enrollment": [0] * N_YEARS,
                "yearly_terminated": [0] * N_YEARS,
                "total_trials": 0,
                "total_enrollment": 0,
                "total_terminated": 0,
                "industry_count": 0,
                "max_phase": "Not Applicable",
                "member_molecules": [],
            }

        cg = class_groups[cls]
        for i in range(N_YEARS):
            cg["yearly_counts"][i] += mol.get("yearly_counts", [0] * N_YEARS)[i]
            cg["yearly_enrollment"][i] += mol.get("yearly_enrollment", [0] * N_YEARS)[i]
            cg["yearly_terminated"][i] += mol.get("yearly_terminated", [0] * N_YEARS)[i]

        cg["total_trials"] += mol.get("total_trials", 0)
        cg["total_enrollment"] += mol.get("total_enrollment", 0)
        cg["total_terminated"] += mol.get("total_terminated", 0)
        cg["industry_count"] += mol.get("industry_count", 0)
        cg["member_molecules"].append(mol.get("intervention", ""))

        # Keep highest phase
        cg["max_phase"] = _higher_phase(cg["max_phase"], mol.get("max_phase", "Not Applicable"))

    # Re-score class-level entries
    class_list = list(class_groups.values())
    class_scored = score_all(class_list)

    # Re-link kill events at class level
    link_kill_events(class_scored, kill_events)

    # ── 3. Build output JSON ────────────────────────────────────────
    output = {
        "generated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "start_year": START_YEAR,
        "end_year": END_YEAR,
        "molecule_count": len(molecules),
        "class_count": len(class_scored),
        "kill_events": kill_events,
        "molecules": molecules,
        "classes": class_scored,
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Also produce minified version safe for HTML <script> embedding
    min_path = output_path.replace(".json", ".min.json")
    min_json = json.dumps(output, ensure_ascii=False, separators=(",", ":"))
    # Sanitize </script> sequences that would break HTML embedding
    min_json = min_json.replace("</script>", r"<\/script>")
    with open(min_path, "w", encoding="utf-8") as f:
        f.write(min_json)

    size_kb = os.path.getsize(output_path) / 1024
    print(f"Exported {len(molecules)} molecules + {len(class_scored)} classes")
    print(f"Output: {output_path} ({size_kb:.1f} KB)")

    return output


# ── Phase comparison helper ─────────────────────────────────────────
_PHASE_RANK = {
    "Not Applicable": 0,
    "Early Phase 1": 1,
    "Phase 1": 2,
    "Phase 1/Phase 2": 3,
    "Phase 2": 4,
    "Phase 2/Phase 3": 5,
    "Phase 3": 6,
    "Phase 3/Phase 4": 7,
    "Phase 4": 8,
}


def _higher_phase(a, b):
    """Return the higher of two phase strings."""
    ra = _PHASE_RANK.get(a, 0)
    rb = _PHASE_RANK.get(b, 0)
    return a if ra >= rb else b


if __name__ == "__main__":
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    scored_path = os.path.join(base, "data", "cv_interventions_scored.json")
    ke_path = os.path.join(base, "data", "kill_events.json")
    out_path = os.path.join(base, "data", "therapy_graveyard_data.json")
    build_training_data(scored_path, ke_path, out_path)
    print("Done.")
