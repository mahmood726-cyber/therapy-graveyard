# therapy-graveyard

An attrition map of cardiovascular drugs and techniques: which interventions
peaked in clinical-trial activity and then declined or were abandoned.

## What this is

- A Python pipeline (`pipeline/`) that extracts cardiovascular interventions
  from AACT (2005-2025), normalizes drug/procedure names, builds yearly
  trial-count time series, and scores each intervention's peak-and-decline
  trajectory (DEAD / ZOMBIE / DECLINING / ALIVE).
- A single-file interactive HTML dashboard (`TherapyGraveyard.html` /
  `index.html`) that renders the scored data offline.

## Pipeline

| Stage | Module | Output |
|-------|--------|--------|
| Extract | `pipeline/extract.py` | raw AACT records |
| Normalize | `pipeline/normalize.py` | canonical names + yearly time series |
| Score | `pipeline/score.py` | peak/decline status + linked kill events |
| Export | `pipeline/export.py` | training JSON for the dashboard |

Scoring is a deterministic rule-based classifier (rolling-average smoothing,
decline ratio, years-silent, kill-event linkage). It is not a meta-analysis or
inferential model.

## Run

```
pip install -r pipeline/requirements.txt
python -m pytest -q          # 28 tests
python pipeline/score.py     # re-score normalized data
```

Extraction (`extract.py`) requires AACT database credentials; see
`.env.example`.

## Data

`data/` holds the normalized, scored, and exported JSON plus the drug-class map
and kill-event records.

## License

MIT — see `LICENSE`.
