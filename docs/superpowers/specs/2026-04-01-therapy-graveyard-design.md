# TherapyGraveyard — Design Spec

**Date:** 2026-04-01
**Concept:** First systematic data-driven map of drug and technique attrition in cardiovascular medicine using 20 years of ClinicalTrials.gov registry data.
**Output:** Python extraction pipeline + single-file interactive HTML app + Zenodo dataset + BMJ/Lancet Digital Health manuscript.

---

## 1. Data Extraction Pipeline

**Data source:** AACT remote database (aact-db.ctti-clinicaltrials.org:5432) — full CT.gov mirror.

### Query Strategy — Two Passes

**Pass 1: Drug interventions**
- Query `interventions` table where `intervention_type = 'Drug'` joined with `studies` table.
- Filter: `study_first_submitted_date >= 2005-01-01`.
- Filter: CV conditions via `conditions` table keyword match (heart failure, coronary, atrial fibrillation, hypertension, stroke, cardiomyopathy, valve, aortic, pulmonary hypertension, peripheral artery disease, etc.).
- Extract: `nct_id`, `intervention_name`, `study_first_submitted_date`, `overall_status`, `phase`, `enrollment`, `sponsor_type`.

**Pass 2: Procedure/Device interventions**
- Same join but `intervention_type IN ('Procedure', 'Device', 'Behavioral', 'Radiation')`.
- Same CV condition filter.
- Same fields.

### Normalization

Raw intervention names are messy ("Atorvastatin 40mg tablets" vs "atorvastatin calcium" vs "Lipitor"). Pipeline uses:
1. Lowercase + strip dosage/formulation with regex.
2. Lookup table mapping brand names to generic names (top 500 CV drugs).
3. Fuzzy matching (Levenshtein distance < 3) for remaining variants.
4. Manual review file for ambiguous mappings.

### Class Hierarchy

A curated JSON mapping file (`data/drug_class_map.json`):
```json
{
  "torcetrapib": { "class": "cetp_inhibitor", "category": "lipid_lowering" },
  "niacin": { "class": "niacin", "category": "lipid_lowering" },
  "empagliflozin": { "class": "sglt2i", "category": "glucose_lowering" },
  "balloon_angioplasty": { "class": "pci", "category": "revascularization" }
}
```

Pre-seeded with ~200 CV drugs and ~50 procedures. Unknown interventions flagged for manual classification.

### Output

`data/cv_interventions_timeseries.json` — one record per intervention per year, with trial count, total enrollment, phase breakdown, and termination rate.

Estimated scope: ~15,000-30,000 unique CV trials, ~500-1,000 distinct normalized interventions.

---

## 2. Peak-and-Decline Scoring Engine

### Algorithm (per normalized intervention)

```
1. Build array T[2005..2025] of new trial registrations per year
2. Apply 3-year rolling average to smooth noise: S[y] = mean(T[y-1], T[y], T[y+1])
3. Find peak: peak_year = argmax(S), peak_count = S[peak_year]
4. Skip if peak_count < 3 (insufficient evidence of real adoption)
5. Compute recent activity: recent = mean(T[2023], T[2024], T[2025])
6. Compute decline ratio: decline = 1 - (recent / peak_count)
7. Compute years_silent: years since last year with T[y] >= 1
8. Assign status:
     DEAD      = decline >= 0.90 AND years_silent >= 3
     DECLINING = decline >= 0.50 AND years_silent >= 1
     ALIVE     = decline < 0.50
     ZOMBIE    = was DEAD (decline >= 0.90) but T[2024] or T[2025] >= 1
9. Compute half-life: years from peak to first year where S[y] < peak_count / 2
```

### Class-Level Roll-Up

Sum trial counts across all molecules in a class, then re-run the same algorithm. A class can be DEAD even if one molecule is ALIVE (if that molecule's volume is negligible vs the class peak).

### Additional Metrics Per Intervention

- **Lifespan**: Years from first trial to last trial.
- **Total trials**: Cumulative trial count across all years.
- **Total enrollment**: Sum of planned enrollment across all trials.
- **Termination rate**: Proportion of trials with status Terminated or Withdrawn.
- **Phase reached**: Highest phase achieved (1, 2, 3, or 4).
- **Sponsor profile**: Proportion industry vs academic.

### Output

`data/attrition_scores.json` — one record per intervention:
```json
{
  "intervention": "torcetrapib",
  "class": "cetp_inhibitor",
  "category": "lipid_lowering",
  "type": "drug",
  "status": "DEAD",
  "peak_year": 2006,
  "peak_count": 8.3,
  "recent_count": 0,
  "decline_ratio": 1.0,
  "years_silent": 18,
  "half_life": 1,
  "lifespan": 3,
  "total_trials": 12,
  "total_enrollment": 19450,
  "termination_rate": 0.42,
  "max_phase": "PHASE3",
  "timeseries": [0, 0, 8, 5, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  "kill_events": ["KE001"]
}
```

---

## 3. Kill Event Enrichment

### Structure

Manually curated JSON file (`data/kill_events.json`):
```json
{
  "id": "KE001",
  "year": 2006,
  "event": "ILLUMINATE trial terminated — excess CV mortality",
  "category": "landmark_negative_trial",
  "interventions": ["torcetrapib"],
  "classes": ["cetp_inhibitor"],
  "source": "NEJM 2007;357:2109-22",
  "doi": "10.1056/NEJMoa0706628",
  "impact": "Killed torcetrapib development; cast doubt on entire CETP class"
}
```

### Six Kill Categories

1. `landmark_negative_trial` — Major RCT that showed harm or futility.
2. `fda_safety_action` — Black box warning, REMS, market withdrawal.
3. `guideline_downgrade` — Major society downgraded recommendation.
4. `competitor_displacement` — Superior therapy made it obsolete.
5. `commercial_withdrawal` — Manufacturer decision (not safety-driven).
6. `paradigm_shift` — Underlying scientific rationale discredited.

### Pre-Seeded CV Kill Events (~30-40)

| Year | Intervention | Event | Category |
|------|-------------|-------|----------|
| 2006 | Torcetrapib | ILLUMINATE — excess mortality | landmark_negative_trial |
| 2006 | Aprotinin | BART trial — excess mortality, FDA withdrawal 2007 | fda_safety_action |
| 2007 | Rosiglitazone | Nissen meta-analysis — MI risk, FDA REMS | fda_safety_action |
| 2011 | Niacin (+statin) | AIM-HIGH — no benefit | landmark_negative_trial |
| 2012 | Dalcetrapib | dal-OUTCOMES — futility | landmark_negative_trial |
| 2013 | Niacin (+statin) | HPS2-THRIVE — no benefit + harm | landmark_negative_trial |
| 2014 | Aliskiren | ALTITUDE — harm in diabetics | landmark_negative_trial |
| 2015 | Evacetrapib | ACCELERATE — futility | landmark_negative_trial |
| 2016 | Cardiac stem cells | SCIPIO retraction + CONCERT-HF negative | paradigm_shift |
| 2017 | Routine PCI (stable) | ORBITA — no angina benefit vs sham | landmark_negative_trial |
| 2019 | Routine PCI (stable) | ISCHEMIA — no hard endpoint benefit | landmark_negative_trial |
| 2020 | Hydroxychloroquine (CV) | RECOVERY — no COVID benefit | landmark_negative_trial |
| 2007 | Bare metal stents | DES superiority established | competitor_displacement |
| 2012 | First-gen DES | Second-gen DES superiority | competitor_displacement |
| 2008 | Pulmonary artery catheter | PAC-Man + ESCAPE — no benefit in HF/ICU | landmark_negative_trial |
| 2012 | Renal denervation | SYMPLICITY HTN-3 — negative | landmark_negative_trial |
| 2016 | Lomitapide/Mipomersen | PCSK9i displacement | competitor_displacement |

### Kill Event Linkage

When a kill event year aligns with the start of decline (within +/-2 years of peak), it is flagged as "probable cause" in the output data.

---

## 4. Interactive HTML App

### Single-file HTML (`TherapyGraveyard.html`)

Uses Plotly.js, CSS variables for dark mode, `tg-` prefix for all element IDs, localStorage for user preferences.

### View 1: Graveyard Timeline (default)

- **X-axis**: Year (2005-2025).
- **Y-axis**: Interventions sorted by peak year, grouped by category.
- **Heatmap cells**: Color intensity = trial count that year. Row color-coded by status: green (ALIVE), amber (DECLINING), red (DEAD), purple (ZOMBIE).
- **Kill event markers**: Red diamond on the cell where the kill event occurred.
- **Toolbar filters**: Status (Dead/Declining/Alive/Zombie), Type (Drug/Procedure/Device), Category (lipid/glucose/anticoag/revascularization/...), Class level vs molecule level toggle.

### View 2: Autopsy (click any intervention row)

- **Trial count curve**: Plotly line chart showing the rise and fall, with peak annotated.
- **Kill event panel**: What killed it — linked to DOI/source.
- **Trial list**: Table of all CT.gov trials for this intervention, sortable by year/phase/status/enrollment.
- **Class context**: Small multiples showing sibling molecules in the same class.
- **Metrics card**: Lifespan, total trials, total enrollment, max phase, termination rate, half-life.

### View 3: Statistics Dashboard

- **Death toll summary**: Total dead, declining, alive, zombie counts + pie chart.
- **Deadliest decade**: Which 5-year period killed the most interventions.
- **Kill cause breakdown**: Bar chart of kill categories.
- **Survival analysis**: Kaplan-Meier style curve showing intervention survival from first trial to death.
- **Class mortality table**: Which drug classes have the highest attrition rate.
- **Top 10 biggest graveyards**: Interventions with the most trials/enrollment before death (wasted research investment).

### Data & Technical

- Training data embedded as JSON in HTML (~200KB for 500-1,000 interventions).
- Plotly.js for all charts.
- localStorage for user preferences (filters, dark mode) with `tg_` prefix.
- Dark mode via CSS variables.
- CSV export of full dataset.
- Accessibility: keyboard navigation, ARIA labels, skip-nav, screen reader support.

---

## 5. Project Structure & Publication

### Directory Layout

```
C:\Models\TherapyGraveyard\
├── TherapyGraveyard.html
├── pipeline/
│   ├── extract.py
│   ├── normalize.py
│   ├── score.py
│   ├── export.py
│   └── requirements.txt
├── data/
│   ├── drug_class_map.json
│   ├── kill_events.json
│   ├── cv_interventions_raw.json
│   ├── attrition_scores.json
│   └── training_data.json
├── tests/
│   └── test_pipeline.py
├── paper/
│   └── therapy_graveyard_manuscript.md
├── figures/
└── docs/
    └── superpowers/
```

### Publication

- **Target**: BMJ or Lancet Digital Health.
- **Title**: "The Therapeutic Graveyard: 20 Years of Drug and Technique Attrition in Cardiovascular Medicine"
- **Angle**: First systematic quantification of therapeutic attrition using registry data.
- **Key figures**: (1) Graveyard heatmap, (2) Survival curve of interventions, (3) Kill cause breakdown, (4) Top 10 wasted-investment table.
- **Dataset deposit**: Zenodo.

### Scope Boundaries (MVP)

- **In scope**: CV drugs + procedures, 2005-2025, AACT data.
- **Out of scope for MVP**: Non-CV therapeutic areas, automated kill event detection from literature, guideline scraping, FDA label change API integration.
- **Expandable later**: Other disease areas use the same pipeline with different condition filters.

---

## Implementation Constraints

- **Python**: Use `python` not `python3` on Windows.
- **AACT credentials**: Load from `.env` file, never commit.
- **Encoding**: UTF-8 throughout; sanitize Unicode for Windows cp1252 console output.
- **HTML app**: Follow rules from `.claude/rules/html-apps.md` and `.claude/rules/lessons.md`.
- **No `</script>` in JS**: Use `${'<'}/script>` pattern.
- **Seeded PRNG**: xoshiro128** for any bootstrap/sampling.
- **`?? fallback`**: Never use `|| fallback` for numeric values.
- **Div balance**: Verify after structural HTML edits.
- **ID uniqueness**: All element IDs prefixed `tg-`.
- **Blob cleanup**: `URL.revokeObjectURL()` after downloads.
