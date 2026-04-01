"""
Tests for pipeline/score.py -- 7 tests.
"""

import io
import os
import sys

if sys.platform == "win32" and not getattr(sys.stdout, "_tg_utf8", False):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stdout._tg_utf8 = True

# Add pipeline to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pipeline"))

from score import score_intervention, score_all, link_kill_events, START_YEAR, END_YEAR, N_YEARS


def _make_entry(yearly_counts, name="test_drug", drug_class="unknown"):
    """Helper to build a minimal entry dict."""
    return {
        "intervention": name,
        "intervention_type": "Drug",
        "drug_class": drug_class,
        "category": "unknown",
        "total_trials": sum(yearly_counts),
        "yearly_counts": yearly_counts,
        "yearly_enrollment": [0] * N_YEARS,
        "yearly_terminated": [0] * N_YEARS,
    }


def test_dead_intervention():
    """Peaked in 2008, no trials after 2012 -> DEAD."""
    counts = [0] * N_YEARS
    # 2008 = index 3, 2009 = 4, 2010 = 5, 2011 = 6, 2012 = 7
    counts[3] = 10  # 2008 peak
    counts[4] = 8
    counts[5] = 4
    counts[6] = 2
    counts[7] = 1
    # Nothing after 2012 -> years_silent >= 3 (2025 - 2012 = 13)

    entry = _make_entry(counts)
    score_intervention(entry)
    assert entry["status"] == "DEAD", f"Expected DEAD, got {entry['status']}"
    assert entry["years_silent"] >= 3, f"years_silent={entry['years_silent']}"
    assert entry["decline_ratio"] >= 0.9, f"decline_ratio={entry['decline_ratio']}"


def test_alive_intervention():
    """Steady/growing trials -> ALIVE."""
    counts = [0] * N_YEARS
    # Steady growth 2015-2025
    for i in range(10, N_YEARS):
        counts[i] = 5 + (i - 10)
    # Last 3 years: [18]=13, [19]=14, [20]=15 -> recent_count ~14
    # Peak is 15 (at index 20) -> decline = 1 - (14/15) = 0.067 < 0.5

    entry = _make_entry(counts)
    score_intervention(entry)
    assert entry["status"] == "ALIVE", f"Expected ALIVE, got {entry['status']}"


def test_declining_intervention():
    """Peaked in 2010, low recent -> DECLINING."""
    counts = [0] * N_YEARS
    # 2010 = index 5 -> peak
    counts[5] = 15
    counts[6] = 12
    counts[7] = 8
    counts[8] = 5
    counts[9] = 3
    counts[10] = 2
    counts[11] = 2
    counts[12] = 1
    counts[13] = 1
    counts[14] = 1
    counts[15] = 1
    # Last 3 years (indices 18,19,20): all 0 -> recent=0 -> decline=1.0
    # But years_silent = 2025 - 2020 = 5 >= 3 -> actually DEAD
    # Let's give 1 trial in 2022 (index 17) to keep it just DECLINING
    counts[17] = 1  # 2022: years_silent = 2025-2022 = 3
    # recent = 0, decline = 1.0, silent = 3 -> DEAD actually
    # Need a trial in last 3 but still have high decline
    # Let's put 1 trial at index 20 (2025) so it's not fully silent
    counts[20] = 1
    # recent = (0 + 0 + 1)/3 = 0.33
    # decline = 1 - (0.33/15) = 0.978 >= 0.9
    # years_silent = 0 (2025 has trial)
    # Silent < 3 so not DEAD. decline >= 0.5 and silent >= 0...
    # DECLINING requires silent >= 1, but silent = 0
    # Actually ZOMBIE check: decline >= 0.9, silent >= 3? Silent = 0 so no.
    # Just put it differently:
    counts = [0] * N_YEARS
    counts[5] = 15   # 2010 peak
    counts[6] = 12
    counts[7] = 8
    counts[8] = 5
    counts[9] = 3
    counts[10] = 2
    counts[11] = 1
    counts[12] = 1
    counts[15] = 1   # 2020
    counts[17] = 1   # 2022
    # last 3 (18,19,20) = 0,0,0 -> recent = 0
    # years_silent = 2025-2022 = 3
    # decline = 1.0 >= 0.9, silent = 3 >= 3 -> DEAD
    # For DECLINING: we need decline >= 0.5 but (decline < 0.9 OR silent < 3)
    # Let's try: moderate decline, some recent activity
    counts = [0] * N_YEARS
    counts[5] = 20   # 2010 peak
    counts[6] = 18
    counts[7] = 15
    counts[8] = 12
    counts[9] = 10
    counts[10] = 8
    counts[11] = 5
    counts[12] = 4
    counts[13] = 3
    counts[14] = 3
    counts[15] = 2
    counts[16] = 2
    counts[17] = 1   # 2022
    counts[18] = 1   # 2023
    # indices 18,19,20 = 1,0,0 -> recent = 0.33
    # decline = 1 - (0.33/20) = 0.983
    # years_silent = 2025-2023 = 2
    # decline >= 0.9 but silent < 3 -> not DEAD
    # decline >= 0.5 and silent >= 1 -> DECLINING

    entry = _make_entry(counts)
    score_intervention(entry)
    assert entry["status"] == "DECLINING", f"Expected DECLINING, got {entry['status']}"


def test_zombie_intervention():
    """Was dead but has 1 trial in 2024 -> ZOMBIE."""
    counts = [0] * N_YEARS
    # Peak in 2008, dead by 2012, but zombie trial in 2024
    counts[3] = 10  # 2008
    counts[4] = 8
    counts[5] = 4
    counts[6] = 2
    counts[7] = 1   # 2012
    counts[19] = 1  # 2024 -> zombie resurrection

    entry = _make_entry(counts)
    score_intervention(entry)
    assert entry["status"] == "ZOMBIE", f"Expected ZOMBIE, got {entry['status']}"


def test_skip_low_volume():
    """Peak < 3 -> SKIPPED."""
    counts = [0] * N_YEARS
    counts[5] = 2
    counts[6] = 1

    entry = _make_entry(counts)
    score_intervention(entry)
    assert entry["status"] == "SKIPPED", f"Expected SKIPPED, got {entry['status']}"


def test_half_life():
    """Peak 20, drops to <10 -> measurable half_life."""
    counts = [0] * N_YEARS
    counts[5] = 20   # 2010 peak
    counts[6] = 18
    counts[7] = 14
    counts[8] = 9    # First year smoothed drops below 10
    counts[9] = 5
    counts[10] = 3

    entry = _make_entry(counts)
    score_intervention(entry)
    assert entry["half_life"] is not None, "Expected non-None half_life"
    assert entry["half_life"] > 0, f"Expected positive half_life, got {entry['half_life']}"


def test_kill_event_linkage():
    """Torcetrapib peak 2006 + KE001 year 2006 -> linked."""
    counts = [0] * N_YEARS
    counts[1] = 8  # 2006 peak
    counts[2] = 5
    counts[3] = 2

    entry = _make_entry(counts, name="torcetrapib", drug_class="cetp_inhibitor")
    score_intervention(entry)

    kill_events = [
        {
            "id": "KE001",
            "year": 2006,
            "event": "ILLUMINATE trial terminated",
            "category": "landmark_negative_trial",
            "interventions": ["torcetrapib"],
            "classes": ["cetp_inhibitor"],
        }
    ]

    link_kill_events([entry], kill_events)
    assert entry["probable_cause"] is not None, "Expected kill event linkage"
    assert len(entry["probable_cause"]) == 1, f"Expected 1 event, got {len(entry['probable_cause'])}"
    assert entry["probable_cause"][0]["id"] == "KE001"


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
