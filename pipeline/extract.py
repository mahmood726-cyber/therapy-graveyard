"""
AACT extraction module for TherapyGraveyard.

Queries the AACT PostgreSQL database for all cardiovascular interventions
from 2005-2025. Outputs raw records to data/cv_interventions_raw.json.
"""

import io
import json
import os
import sys

# Windows UTF-8 fix (guard against double-wrapping)
if sys.platform == "win32" and not getattr(sys.stdout, "_tg_utf8", False):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stdout._tg_utf8 = True

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # .env must be sourced manually

import psycopg2

# ── CV condition pattern for SIMILAR TO matching ────────────────────────
CV_PATTERN = (
    "%(heart failure|coronary artery disease|myocardial infarction"
    "|atrial fibrillation|atrial flutter|stroke|hypertension"
    "|cardiovascular|cardiac arrest|angina|atherosclerosis"
    "|peripheral artery disease|peripheral arterial disease"
    "|cardiomyopathy|aortic stenosis|aortic valve|mitral valve"
    "|mitral regurgitation|pulmonary hypertension"
    "|pulmonary arterial hypertension|chronic kidney disease"
    "|diabetic nephropathy|diabetes mellitus|type 2 diabetes"
    "|acute coronary syndrome|venous thromboembolism"
    "|deep vein thrombosis|pulmonary embolism|arrhythmia"
    "|tachycardia|cardiac surgery|coronary bypass"
    "|heart transplant|cardiogenic shock)%"
)

# ── SQL ─────────────────────────────────────────────────────────────────
QUERY = """
SELECT
    s.nct_id,
    i.name            AS intervention_name,
    i.intervention_type,
    s.brief_title     AS title,
    s.overall_status  AS status,
    s.phase,
    s.enrollment,
    s.start_date,
    s.primary_completion_date,
    s.source          AS sponsor_name,
    s.source_class    AS sponsor_class
FROM ctgov.studies s
JOIN ctgov.interventions i ON i.nct_id = s.nct_id
WHERE s.study_type = 'INTERVENTIONAL'
  AND s.start_date >= '2005-01-01'
  AND i.intervention_type IN ('Drug', 'Procedure', 'Device', 'Behavioral', 'Radiation')
  AND EXISTS (
      SELECT 1 FROM ctgov.conditions c
      WHERE c.nct_id = s.nct_id
        AND LOWER(c.name) SIMILAR TO %(cv_pattern)s
  )
"""


def _date_to_iso(val):
    """Convert a date/datetime to ISO string, or None."""
    if val is None:
        return None
    return val.isoformat() if hasattr(val, "isoformat") else str(val)


def extract_cv_interventions():
    """Query AACT and return list of dicts."""
    user = os.environ.get("AACT_USER")
    pwd = os.environ.get("AACT_PASSWORD")
    if not user or not pwd:
        raise RuntimeError("AACT_USER and AACT_PASSWORD must be set in environment or .env")

    conn = psycopg2.connect(
        host="aact-db.ctti-clinicaltrials.org",
        port=5432,
        dbname="aact",
        user=user,
        password=pwd,
        connect_timeout=30,
        sslmode="require",
    )
    try:
        cur = conn.cursor()
        print("Querying AACT for CV interventions 2005-2025 ...")
        cur.execute(QUERY, {"cv_pattern": CV_PATTERN})
        cols = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        print(f"  Retrieved {len(rows):,} rows")
    finally:
        conn.close()

    records = []
    for row in rows:
        rec = dict(zip(cols, row))
        # Convert dates to ISO strings
        for key in ("start_date", "primary_completion_date"):
            rec[key] = _date_to_iso(rec.get(key))
        records.append(rec)

    return records


def save_raw(records, path):
    """Save records list to JSON file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    size_kb = os.path.getsize(path) / 1024
    print(f"  Saved {len(records):,} records to {path} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_path = os.path.join(base, "data", "cv_interventions_raw.json")
    records = extract_cv_interventions()
    save_raw(records, out_path)
    print("Done.")
