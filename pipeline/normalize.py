"""
Drug name normalization and yearly time-series builder for TherapyGraveyard.

Functions:
  normalize_name(raw_name) -> str
  classify_intervention(normalized_name, intervention_type) -> dict
  build_timeseries(records) -> list[dict]
  normalize_raw_file(input_path, output_path) -> list[dict]
"""

import io
import json
import os
import re
import sys

if sys.platform == "win32" and not getattr(sys.stdout, "_tg_utf8", False):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stdout._tg_utf8 = True

try:
    from Levenshtein import distance as lev_distance
except ImportError:
    # Fallback: no fuzzy matching
    lev_distance = None

# ── Constants ───────────────────────────────────────────────────────────
START_YEAR = 2005
END_YEAR = 2025
N_YEARS = END_YEAR - START_YEAR + 1  # 21

# ── Data loading ────────────────────────────────────────────────────────
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MAP_PATH = os.path.join(_BASE, "data", "drug_class_map.json")

_class_map = None


def _load_class_map():
    """Load drug_class_map.json once (lazy)."""
    global _class_map
    if _class_map is None:
        with open(_MAP_PATH, "r", encoding="utf-8") as f:
            _class_map = json.load(f)
    return _class_map


# ── Procedure aliases ──────────────────────────────────────────────────
PROCEDURE_ALIASES = {
    "cabg": "coronary artery bypass",
    "ptca": "percutaneous coronary intervention",
    "swan-ganz": "pulmonary artery catheter",
    "swan ganz": "pulmonary artery catheter",
}

# ── Regex patterns for stripping dosage/formulation ────────────────────
# Matches things like: 40mg, 10 mg, 97/103 mg, 200mg/5ml, tablets, capsules, etc.
_RE_DOSAGE = re.compile(
    r"\s*\d+(?:\.\d+)?(?:\s*/\s*\d+(?:\.\d+)?)?\s*"
    r"(?:mg|mcg|ug|g|ml|iu|units?|mmol|meq|%)\b",
    re.IGNORECASE,
)
_RE_FORMULATION = re.compile(
    r"\b(?:tablets?|capsules?|injection|infusion|solution|suspension|"
    r"oral|iv|subcutaneous|intramuscular|topical|cream|gel|patch|"
    r"extended[- ]release|immediate[- ]release|modified[- ]release|"
    r"sustained[- ]release|controlled[- ]release|delayed[- ]release|"
    r"er|xr|sr|cr|hcl|hydrochloride|besylate|mesylate|tartrate|"
    r"succinate|fumarate|maleate|calcium|sodium|potassium)\b",
    re.IGNORECASE,
)
_RE_PARENS = re.compile(r"\([^)]*\)")
_RE_SALT = re.compile(
    r"\b(?:hydrochloride|hcl|besylate|mesylate|tartrate|succinate|"
    r"fumarate|maleate|calcium|sodium|potassium|sulfate|acetate|"
    r"phosphate|citrate|bromide|chloride|nitrate|oxide)\b",
    re.IGNORECASE,
)
_RE_MULTI_SPACE = re.compile(r"\s+")


def normalize_name(raw_name):
    """
    Normalize a raw intervention name:
      1. Lowercase
      2. Strip parentheticals
      3. Strip dosage/formulation
      4. Strip salt forms
      5. Brand -> generic lookup
      6. Procedure aliases
      7. Clean whitespace
    """
    if not raw_name:
        return ""

    name = raw_name.strip()

    # Brand -> generic (case-insensitive lookup, try original casing first)
    cm = _load_class_map()
    b2g = cm.get("brand_to_generic", {})
    # Try exact match on original
    if name in b2g:
        name = b2g[name]
    else:
        # Try title-case match
        for brand, generic in b2g.items():
            if name.lower().startswith(brand.lower()):
                name = generic
                break

    name = name.lower()

    # Strip parentheticals
    name = _RE_PARENS.sub("", name)

    # Strip dosage patterns
    name = _RE_DOSAGE.sub("", name)

    # Strip formulation words
    name = _RE_FORMULATION.sub("", name)

    # Strip salt forms
    name = _RE_SALT.sub("", name)

    # Clean whitespace
    name = _RE_MULTI_SPACE.sub(" ", name).strip()

    # Procedure aliases
    if name in PROCEDURE_ALIASES:
        name = PROCEDURE_ALIASES[name]

    return name


def classify_intervention(normalized_name, intervention_type):
    """
    Classify a normalized intervention name.
    Returns {class, category, type}.
    Lookup order: exact match -> substring -> Levenshtein (distance <= 2) -> unknown.
    """
    cm = _load_class_map()
    itype = (intervention_type or "").strip()

    # Decide which dictionary to search first based on type
    if itype in ("Drug",):
        search_order = [("drugs", "drug"), ("procedures", "procedure")]
    elif itype in ("Procedure", "Device"):
        search_order = [("procedures", "procedure"), ("drugs", "drug")]
    else:
        search_order = [("drugs", "drug"), ("procedures", "procedure")]

    for dict_key, type_label in search_order:
        db = cm.get(dict_key, {})

        # 1. Exact match
        if normalized_name in db:
            info = db[normalized_name]
            return {"class": info["class"], "category": info["category"], "type": type_label}

        # Also try underscore variant (e.g., "bempedoic acid" -> "bempedoic_acid")
        underscore_name = normalized_name.replace(" ", "_")
        if underscore_name in db:
            info = db[underscore_name]
            return {"class": info["class"], "category": info["category"], "type": type_label}

        # 2. Substring matching
        for key, info in db.items():
            key_readable = key.replace("_", " ")
            if key_readable in normalized_name or normalized_name in key_readable:
                return {"class": info["class"], "category": info["category"], "type": type_label}

        # 3. Levenshtein fallback (distance <= 2)
        if lev_distance is not None:
            best_dist = 999
            best_info = None
            best_type = None
            for key, info in db.items():
                key_readable = key.replace("_", " ")
                d = lev_distance(normalized_name, key_readable)
                if d <= 2 and d < best_dist:
                    best_dist = d
                    best_info = info
                    best_type = type_label
            if best_info is not None:
                return {"class": best_info["class"], "category": best_info["category"], "type": best_type}

    return {"class": "unknown", "category": "unknown", "type": itype.lower() if itype else "unknown"}


def build_timeseries(records):
    """
    Group records by normalized intervention name and build yearly time-series.

    Each record must have: nct_id, intervention_name, intervention_type,
    start_date, enrollment, status, phase, sponsor_class.

    Returns list of dicts sorted by total_trials desc.
    """
    # Group by normalized name
    groups = {}
    for rec in records:
        raw_name = rec.get("intervention_name", "")
        norm = normalize_name(raw_name)
        if not norm:
            continue

        if norm not in groups:
            groups[norm] = {
                "intervention": norm,
                "intervention_type": rec.get("intervention_type", ""),
                "nct_ids": set(),
                "yearly_counts": [0] * N_YEARS,
                "yearly_enrollment": [0] * N_YEARS,
                "yearly_terminated": [0] * N_YEARS,
                "phases": set(),
                "industry_count": 0,
            }

        entry = groups[norm]
        nct_id = rec.get("nct_id", "")

        # Deduplicate by nct_id
        if nct_id in entry["nct_ids"]:
            continue
        entry["nct_ids"].add(nct_id)

        # Parse year from start_date
        start_date = rec.get("start_date")
        year = None
        if start_date:
            try:
                year = int(str(start_date)[:4])
            except (ValueError, TypeError):
                pass

        if year is not None and START_YEAR <= year <= END_YEAR:
            idx = year - START_YEAR
            entry["yearly_counts"][idx] += 1

            enrollment = rec.get("enrollment")
            if enrollment is not None:
                try:
                    entry["yearly_enrollment"][idx] += int(enrollment)
                except (ValueError, TypeError):
                    pass

            status = (rec.get("status") or "").lower()
            if "terminated" in status or "withdrawn" in status or "suspended" in status:
                entry["yearly_terminated"][idx] += 1

        # Track phases
        phase = rec.get("phase")
        if phase:
            entry["phases"].add(phase)

        # Track industry sponsorship
        sponsor_class = (rec.get("sponsor_class") or "").upper()
        if sponsor_class == "INDUSTRY":
            entry["industry_count"] += 1

    # Convert to list
    result = []
    for norm, entry in groups.items():
        total = sum(entry["yearly_counts"])
        if total == 0:
            continue

        # Determine max phase
        phases = entry["phases"]
        max_phase = _max_phase(phases)

        result.append({
            "intervention": entry["intervention"],
            "intervention_type": entry["intervention_type"],
            "total_trials": total,
            "total_enrollment": sum(entry["yearly_enrollment"]),
            "total_terminated": sum(entry["yearly_terminated"]),
            "yearly_counts": entry["yearly_counts"],
            "yearly_enrollment": entry["yearly_enrollment"],
            "yearly_terminated": entry["yearly_terminated"],
            "max_phase": max_phase,
            "industry_count": entry["industry_count"],
            "nct_ids": sorted(entry["nct_ids"]),
        })

    # Sort by total_trials descending
    result.sort(key=lambda x: x["total_trials"], reverse=True)
    return result


def _max_phase(phases):
    """Extract the maximum phase number from a set of phase strings."""
    phase_order = {
        "Early Phase 1": 0.5,
        "Phase 1": 1,
        "Phase 1/Phase 2": 1.5,
        "Phase 2": 2,
        "Phase 2/Phase 3": 2.5,
        "Phase 3": 3,
        "Phase 3/Phase 4": 3.5,
        "Phase 4": 4,
        "Not Applicable": 0,
    }
    best = -1
    best_label = "Not Applicable"
    for p in phases:
        val = phase_order.get(p, -1)
        if val > best:
            best = val
            best_label = p
    return best_label


def normalize_raw_file(input_path, output_path):
    """
    Load raw extraction, build timeseries, classify, save.
    Returns the list of intervention entries.
    """
    with open(input_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    print(f"Loaded {len(records):,} raw records from {input_path}")

    timeseries = build_timeseries(records)
    print(f"Built time-series for {len(timeseries)} unique interventions")

    # Classify each intervention
    for entry in timeseries:
        cls = classify_intervention(entry["intervention"], entry["intervention_type"])
        entry["drug_class"] = cls["class"]
        entry["category"] = cls["category"]
        entry["classified_type"] = cls["type"]

    # Sort by total_trials descending
    timeseries.sort(key=lambda x: x["total_trials"], reverse=True)

    # Save
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(timeseries, f, indent=2, ensure_ascii=False)
    size_kb = os.path.getsize(output_path) / 1024
    print(f"Saved {len(timeseries)} interventions to {output_path} ({size_kb:.1f} KB)")

    return timeseries


if __name__ == "__main__":
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    inp = os.path.join(base, "data", "cv_interventions_raw.json")
    out = os.path.join(base, "data", "cv_interventions_normalized.json")
    normalize_raw_file(inp, out)
    print("Done.")
