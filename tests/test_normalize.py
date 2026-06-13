"""
Tests for pipeline/normalize.py — 7 tests.
"""

import io
import os
import sys

if (
    "pytest" not in sys.modules
    and sys.platform == "win32"
    and not getattr(sys.stdout, "_tg_utf8", False)
):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stdout._tg_utf8 = True

# Add pipeline to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pipeline"))

from normalize import normalize_name, classify_intervention, build_timeseries


def test_lowercase_strip_dosage():
    """Normalize should lowercase and strip dosage info."""
    assert normalize_name("Atorvastatin 40mg tablets") == "atorvastatin", \
        f"Got: {normalize_name('Atorvastatin 40mg tablets')}"
    assert normalize_name("EMPAGLIFLOZIN 10 MG") == "empagliflozin", \
        f"Got: {normalize_name('EMPAGLIFLOZIN 10 MG')}"


def test_brand_to_generic():
    """Brand names should map to their generic equivalents."""
    assert normalize_name("Lipitor") == "atorvastatin", \
        f"Got: {normalize_name('Lipitor')}"
    assert normalize_name("Plavix 75mg") == "clopidogrel", \
        f"Got: {normalize_name('Plavix 75mg')}"
    assert normalize_name("Entresto 97/103 mg") == "sacubitril/valsartan", \
        f"Got: {normalize_name('Entresto 97/103 mg')}"


def test_procedure_normalization():
    """Procedures with parentheticals should be cleaned."""
    result = normalize_name("Percutaneous Coronary Intervention (PCI)")
    assert result == "percutaneous coronary intervention", \
        f"Got: {result}"


def test_classify_known_drug():
    """Known drugs should classify correctly."""
    result = classify_intervention("atorvastatin", "Drug")
    assert result["class"] == "statin", f"Got class: {result['class']}"
    assert result["category"] == "lipid_lowering", f"Got category: {result['category']}"


def test_classify_known_procedure():
    """Known procedures should classify correctly."""
    result = classify_intervention("catheter ablation", "Procedure")
    assert result["class"] == "electrophysiology", f"Got class: {result['class']}"
    assert result["category"] == "electrophysiology", f"Got category: {result['category']}"


def test_classify_unknown():
    """Unknown interventions should return class='unknown'."""
    result = classify_intervention("xyznotadrug", "Drug")
    assert result["class"] == "unknown", f"Got class: {result['class']}"


def test_build_timeseries():
    """
    3 records for atorvastatin: 2 in 2010, 1 in 2012.
    Verify counts, enrollment, deduplication.
    """
    records = [
        {
            "nct_id": "NCT001",
            "intervention_name": "Atorvastatin 40mg",
            "intervention_type": "Drug",
            "start_date": "2010-03-15",
            "enrollment": 500,
            "status": "Completed",
            "phase": "Phase 3",
            "sponsor_class": "INDUSTRY",
        },
        {
            "nct_id": "NCT002",
            "intervention_name": "atorvastatin 80mg tablets",
            "intervention_type": "Drug",
            "start_date": "2010-08-01",
            "enrollment": 300,
            "status": "Completed",
            "phase": "Phase 3",
            "sponsor_class": "NIH",
        },
        {
            "nct_id": "NCT003",
            "intervention_name": "ATORVASTATIN",
            "intervention_type": "Drug",
            "start_date": "2012-01-10",
            "enrollment": 200,
            "status": "Terminated",
            "phase": "Phase 2",
            "sponsor_class": "INDUSTRY",
        },
        # Duplicate NCT001 should be ignored
        {
            "nct_id": "NCT001",
            "intervention_name": "Atorvastatin 40mg",
            "intervention_type": "Drug",
            "start_date": "2010-03-15",
            "enrollment": 500,
            "status": "Completed",
            "phase": "Phase 3",
            "sponsor_class": "INDUSTRY",
        },
    ]

    ts = build_timeseries(records)
    assert len(ts) == 1, f"Expected 1 intervention, got {len(ts)}"

    entry = ts[0]
    assert entry["intervention"] == "atorvastatin", f"Got: {entry['intervention']}"
    assert entry["total_trials"] == 3, f"Expected 3 trials, got {entry['total_trials']}"

    # 2010 is index 5 (2010 - 2005), 2012 is index 7
    assert entry["yearly_counts"][5] == 2, f"Expected 2 in 2010, got {entry['yearly_counts'][5]}"
    assert entry["yearly_counts"][7] == 1, f"Expected 1 in 2012, got {entry['yearly_counts'][7]}"

    # Enrollment: 500 + 300 = 800 in 2010, 200 in 2012
    assert entry["yearly_enrollment"][5] == 800, f"Expected 800, got {entry['yearly_enrollment'][5]}"
    assert entry["yearly_enrollment"][7] == 200, f"Expected 200, got {entry['yearly_enrollment'][7]}"

    # Terminated: 1 in 2012
    assert entry["yearly_terminated"][7] == 1, f"Expected 1 terminated, got {entry['yearly_terminated'][7]}"

    # Industry count: 2 (NCT001 + NCT003)
    assert entry["industry_count"] == 2, f"Expected 2 industry, got {entry['industry_count']}"

    # Deduplication: NCT001 duplicate should not be counted
    assert len(entry["nct_ids"]) == 3, f"Expected 3 unique NCTs, got {len(entry['nct_ids'])}"


def test_sacubitril_valsartan_synonyms():
    """All sacubitril/valsartan variants should merge to canonical name (P0-2)."""
    assert normalize_name("lcz696") == "sacubitril/valsartan", \
        f"Got: {normalize_name('lcz696')}"
    assert normalize_name("sacubitril-valsartan") == "sacubitril/valsartan", \
        f"Got: {normalize_name('sacubitril-valsartan')}"
    assert normalize_name("sacubitril valsartan") == "sacubitril/valsartan", \
        f"Got: {normalize_name('sacubitril valsartan')}"
    assert normalize_name("Sacubitril") == "sacubitril/valsartan", \
        f"Got: {normalize_name('Sacubitril')}"


def test_sacubitril_valsartan_classifies_as_arni():
    """Canonical sacubitril/valsartan should classify as ARNI (P0-2)."""
    result = classify_intervention("sacubitril/valsartan", "Drug")
    assert result["class"] == "arni", f"Got class: {result['class']}"
    assert result["category"] == "raas", f"Got category: {result['category']}"


def test_strip_comparator_prefix():
    """Arm-label prefixes should be stripped (P1-2)."""
    assert normalize_name("comparator: placebo") == "placebo", \
        f"Got: {normalize_name('comparator: placebo')}"
    assert normalize_name("active comparator: metoprolol") == "metoprolol", \
        f"Got: {normalize_name('active comparator: metoprolol')}"
    assert normalize_name("experimental: empagliflozin") == "empagliflozin", \
        f"Got: {normalize_name('experimental: empagliflozin')}"


def test_classify_case_insensitive_type():
    """classify_intervention should handle AACT uppercase types (P1-4)."""
    result_upper = classify_intervention("atorvastatin", "DRUG")
    result_title = classify_intervention("atorvastatin", "Drug")
    assert result_upper["class"] == result_title["class"], \
        f"DRUG got {result_upper['class']}, Drug got {result_title['class']}"
    assert result_upper["class"] == "statin", \
        f"Expected statin, got {result_upper['class']}"


def test_niaspan_brand_alias():
    """Niaspan should map to niacin (P2-2)."""
    assert normalize_name("Niaspan") == "niacin", \
        f"Got: {normalize_name('Niaspan')}"


def test_new_drugs_in_class_map():
    """mavacamten, tafamidis, patisiran, tirzepatide should be in drug_class_map (P2-3)."""
    result_mav = classify_intervention("mavacamten", "Drug")
    assert result_mav["class"] == "cardiac_myosin_inhibitor", \
        f"Got class: {result_mav['class']}"
    result_taf = classify_intervention("tafamidis", "Drug")
    assert result_taf["class"] == "transthyretin_stabilizer", \
        f"Got class: {result_taf['class']}"
    result_pat = classify_intervention("patisiran", "Drug")
    assert result_pat["class"] == "transthyretin_silencer", \
        f"Got class: {result_pat['class']}"
    result_tir = classify_intervention("tirzepatide", "Drug")
    assert result_tir["class"] == "gip_glp1_receptor_agonist", \
        f"Got class: {result_tir['class']}"


def test_new_kill_events_exist():
    """CIRT (KE036) and VERTIS-CV (KE037) should be in kill_events.json (P2-1)."""
    import json
    ke_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "data", "kill_events.json")
    with open(ke_path, "r", encoding="utf-8") as f:
        events = json.load(f)
    event_ids = {e["id"] for e in events}
    assert "KE036" in event_ids, "CIRT kill event KE036 not found"
    assert "KE037" in event_ids, "VERTIS-CV kill event KE037 not found"
    cirt = [e for e in events if e["id"] == "KE036"][0]
    assert "methotrexate" in cirt["interventions"]
    assert cirt["year"] == 2018
    vertis = [e for e in events if e["id"] == "KE037"][0]
    assert "ertugliflozin" in vertis["interventions"]
    assert vertis["year"] == 2020


# ── Test runner ─────────────────────────────────────────────────────
if __name__ == "__main__":
    tests = [(name, fn) for name, fn in sorted(globals().items())
             if name.startswith("test_") and callable(fn)]

    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS  {name}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {name}: {e}")
            failed += 1

    print(f"\n{passed}/{passed + failed} tests passed")
    if failed > 0:
        sys.exit(1)
