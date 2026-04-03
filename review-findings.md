# Multi-Persona Review: TherapyGraveyard
### Date: 2026-04-01
### Summary: 8 P0, 14 P1, 13 P2

Reviewers: Statistical Methodologist, Security Auditor, UX/Accessibility, Software Engineer, CV Domain Expert

---

## P0 -- Critical

- **P0-1** [Domain]: 5 kill event dates are wrong — KE008 (aliskiren: 2014→2012), KE019 (serelaxin: 2013→2017), KE020 (nesiritide: 2005→2011), KE029 (losmapimod: 2014→2016), KE033 (TTM: 2010→2013). Wrong dates break kill event linkage.
  - Fix: Correct years in `data/kill_events.json`

- **P0-2** [Domain]: Sacubitril/valsartan fragmented into 4 entries: "lcz696" (37 trials, DEAD), "sacubitril/valsartan" (30, ALIVE), "sacubitril-valsartan" (17, ALIVE), "sacubitril" (8, ZOMBIE). LCZ696 classified as DEAD with unknown class — clinically absurd.
  - Fix: Add synonyms map in normalize.py; merge all into "sacubitril/valsartan" (ARNI)

- **P0-3** [Domain]: Ezetimibe classified as DEAD despite rehabilitation by IMPROVE-IT (2015). Algorithm gives DEAD because 2023-2025 have 0 trials, but it had 5 trials in 2020. Should be ZOMBIE at minimum.
  - Fix: Add IMPROVE-IT positive kill event; review ZOMBIE logic for mid-period activity

- **P0-4** [Stats]: `peak_count` uses `max(counts)` (raw) but spec says it should use smoothed peak. Inconsistency between peak_year (smoothed argmax) and peak_count (raw max) — may refer to different years.
  - Fix: Align to spec — use `peak_val` (smoothed peak) for `peak_count`

- **P0-5** [Stats]: Kaplan-Meier survival curve does not handle censoring — ALIVE/DECLINING items stay in risk set forever, overestimating survival probability. With 332 non-DEAD items, bias is substantial.
  - Fix: Censor non-DEAD items at their observed lifespan

- **P0-6** [Security]: CSV export lacks formula injection protection (cells starting with `=+@\t\r` not sanitized)
  - Fix: Add `if (/^[=+@\t\r]/.test(v)) v = "'" + v;` in exportCSV()

- **P0-7** [A11y]: No skip-nav link — keyboard user must tab through 20+ toolbar controls
  - Fix: Add visually-hidden skip link as first child of body

- **P0-8** [A11y]: No focus management on view switch — focus stays on toolbar when content changes; no `aria-live` region for filter result announcements
  - Fix: Call `.focus()` on view container after switch; add `aria-live="polite"` to info elements

## P1 -- Important

- **P1-1** [Domain]: CV condition filter missing dyslipidemia/hyperlipidemia/hypercholesterolemia — explains why niacin and many lipid trials are absent
  - Fix: Add to CV_PATTERN in extract.py

- **P1-2** [Domain]: "comparator: placebo" appears as a DEAD intervention (39 trials) — normalization doesn't strip prefix
  - Fix: Add regex to strip "comparator:", "active comparator:", "experimental:" prefixes

- **P1-3** [Engineer]: `.gitignore` lists wrong filenames — tracks ~36MB of regenerable data (cv_interventions_normalized.json, cv_interventions_scored.json, therapy_graveyard_data.json)
  - Fix: Update .gitignore to match actual generated filenames

- **P1-4** [Engineer]: `classify_intervention` type check is case-sensitive ("Drug") but AACT data is uppercase ("DRUG")
  - Fix: Normalize to uppercase before comparison

- **P1-5** [Security]: Unescaped values in innerHTML — `sib.status`, `evt.year`, metric values not passed through `escapeHtml()`
  - Fix: Apply escapeHtml() to all innerHTML-injected values

- **P1-6** [Security]: Inline onclick handler with fragile quoting chain for molecule badges
  - Fix: Replace with data-attribute + event delegation

- **P1-7** [Stats]: CSV formula injection (duplicate of P0-6, already captured)

- **P1-8** [Engineer]: No `__init__.py` in pipeline/ — import relies on sys.path hacks
  - Fix: Create empty `pipeline/__init__.py`

- **P1-9** [Engineer]: Duplicate constants (START_YEAR, END_YEAR, N_YEARS) in normalize.py and score.py
  - Fix: Define once in shared location

- **P1-10** [Engineer]: Sparkline Plotly charts never purged — memory leak on repeated autopsy navigation
  - Fix: Call Plotly.purge() on sparkline divs before replacing innerHTML

- **P1-11** [Engineer]: `datetime.utcnow()` deprecated in Python 3.12+
  - Fix: Use `datetime.now(datetime.timezone.utc)`

- **P1-12** [A11y]: Plotly charts have no text alternative — screen readers encounter raw SVG
  - Fix: Add aria-label to chart container divs

- **P1-13** [A11y]: Member molecule badges are keyboard-inaccessible (no role/tabindex/keydown)
  - Fix: Add role="button" tabindex="0" + keydown handler

- **P1-14** [A11y]: Heatmap drill-down is mouse-only — no keyboard equivalent
  - Fix: Add search-then-enter pattern or keyboard-navigable list alternative

## P2 -- Minor

- **P2-1** [Domain]: Missing kill events: CIRT (methotrexate, 2018), VERTIS-CV (ertugliflozin, 2020)
- **P2-2** [Domain]: Niaspan brand alias missing from brand_to_generic
- **P2-3** [Domain]: Missing drugs in class map: mavacamten, tafamidis, patisiran, tirzepatide
- **P2-4** [Domain]: Missing CV conditions: pericarditis, myocarditis, aortic aneurysm, cardiac amyloidosis
- **P2-5** [Stats]: Unicode mojibake in embedded kill event descriptions (UTF-8/cp1252 double-encoding)
- **P2-6** [Security]: No Content Security Policy meta tag
- **P2-7** [Security]: Export pipeline doesn't sanitize JSON for `</script>` sequences
- **P2-8** [Engineer]: 483KB JSON on single line — hard to diff
- **P2-9** [Engineer]: No Python type hints
- **P2-10** [Engineer]: Windows UTF-8 wrapper duplicated in all pipeline files
- **P2-11** [A11y]: Orange status color (#fd7e14) fails WCAG contrast in light mode (2.9:1)
- **P2-12** [A11y]: No prefers-reduced-motion media query
- **P2-13** [A11y]: No table `<caption>` or `scope="col"` on th elements

## False Positive Watch

- Rolling average edge-padding by shrinking window at boundaries is intentional
- Comparing smoothed peak to raw recent is an acknowledged design choice (see P0-4 for resolution)
- ZOMBIE detection logic with gap_before_recent is correct (confirmed by Stats reviewer)
- `escapeHtml()` does escape both `"` and `'` — confirmed working correctly
- Blob URL cleanup is correct (revokeObjectURL called immediately)
- SQL queries use parameterized statements — no injection risk
- No ReDoS risk in regex patterns (confirmed by Security reviewer)
