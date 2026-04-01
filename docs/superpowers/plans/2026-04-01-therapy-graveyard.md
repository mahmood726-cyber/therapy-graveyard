# TherapyGraveyard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python pipeline that extracts CV drug/technique trial data from AACT, scores therapeutic attrition via peak-and-decline algorithm, and exports to a single-file interactive HTML graveyard timeline.

**Architecture:** Python pipeline (extract → normalize → score → export) queries AACT PostgreSQL for CV interventions 2005–2025, normalizes drug names via lookup + fuzzy match, applies peak-and-decline death classification, enriches with manually curated kill events, and exports JSON embedded into a single-file HTML app with three views (graveyard timeline, autopsy drill-down, statistics dashboard).

**Tech Stack:** Python 3 (psycopg2, python-Levenshtein), PostgreSQL (AACT), Vanilla JS, Plotly.js, single-file HTML.

**Spec:** `docs/superpowers/specs/2026-04-01-therapy-graveyard-design.md`

---

## File Map

### Python Pipeline
- **Create:** `C:\Models\TherapyGraveyard\pipeline\extract.py` — AACT query, raw intervention extraction
- **Create:** `C:\Models\TherapyGraveyard\pipeline\normalize.py` — Drug name normalization + class mapping
- **Create:** `C:\Models\TherapyGraveyard\pipeline\score.py` — Peak-and-decline algorithm
- **Create:** `C:\Models\TherapyGraveyard\pipeline\export.py` — Build JSON for HTML embedding
- **Create:** `C:\Models\TherapyGraveyard\pipeline\requirements.txt` — Dependencies

### Data Files
- **Create:** `C:\Models\TherapyGraveyard\data\drug_class_map.json` — Molecule → class → category hierarchy (~200 drugs, ~50 procedures)
- **Create:** `C:\Models\TherapyGraveyard\data\kill_events.json` — ~35 curated landmark events

### Tests
- **Create:** `C:\Models\TherapyGraveyard\tests\test_normalize.py` — Normalization unit tests
- **Create:** `C:\Models\TherapyGraveyard\tests\test_score.py` — Scoring algorithm unit tests

### HTML App
- **Create:** `C:\Models\TherapyGraveyard\TherapyGraveyard.html` — Single-file interactive app

---

## AACT Connection Pattern (reuse from CardioOracle)

```python
import os
import psycopg2

def connect_aact():
    return psycopg2.connect(
        host="aact-db.ctti-clinicaltrials.org",
        port=5432,
        dbname="aact",
        user=os.environ.get("AACT_USER"),
        password=os.environ.get("AACT_PASSWORD"),
        connect_timeout=30,
        sslmode="require",
    )
```

Credentials loaded from `.env` file (never committed). The `.env` backup is at `C:\Users\user\OneDrive\Backups\Archive\Backups\ctgov-search-strategies_backup_20260114-110157\.env`.

---

## Task 1: Project Setup + Data Files

**Files:**
- Create: `C:\Models\TherapyGraveyard\pipeline\requirements.txt`
- Create: `C:\Models\TherapyGraveyard\.env` (from backup, never committed)
- Create: `C:\Models\TherapyGraveyard\.gitignore`
- Create: `C:\Models\TherapyGraveyard\data\drug_class_map.json`
- Create: `C:\Models\TherapyGraveyard\data\kill_events.json`

- [ ] **Step 1: Create requirements.txt**

```
psycopg2-binary>=2.9
python-Levenshtein>=0.21
python-dotenv>=1.0
```

- [ ] **Step 2: Create .gitignore**

```
.env
__pycache__/
*.pyc
data/cv_interventions_raw.json
data/attrition_scores.json
data/training_data.json
```

- [ ] **Step 3: Create .env from backup**

```bash
cd C:/Models/TherapyGraveyard && cp "/c/Users/user/OneDrive/Backups/Archive/Backups/ctgov-search-strategies_backup_20260114-110157/.env" .env
```

If the backup doesn't exist, create `.env` with:
```
AACT_USER=ma6y
AACT_PASSWORD=<ask user>
```

- [ ] **Step 4: Install dependencies**

```bash
cd C:/Models/TherapyGraveyard && pip install -r pipeline/requirements.txt
```

- [ ] **Step 5: Create drug_class_map.json**

This is the curated molecule → class → category hierarchy. Create `data/drug_class_map.json` with ~200 CV drug entries and ~50 procedures. Structure:

```json
{
  "drugs": {
    "torcetrapib": {"class": "cetp_inhibitor", "category": "lipid_lowering"},
    "dalcetrapib": {"class": "cetp_inhibitor", "category": "lipid_lowering"},
    "evacetrapib": {"class": "cetp_inhibitor", "category": "lipid_lowering"},
    "anacetrapib": {"class": "cetp_inhibitor", "category": "lipid_lowering"},
    "obicetrapib": {"class": "cetp_inhibitor", "category": "lipid_lowering"},
    "niacin": {"class": "niacin", "category": "lipid_lowering"},
    "atorvastatin": {"class": "statin", "category": "lipid_lowering"},
    "rosuvastatin": {"class": "statin", "category": "lipid_lowering"},
    "simvastatin": {"class": "statin", "category": "lipid_lowering"},
    "pravastatin": {"class": "statin", "category": "lipid_lowering"},
    "pitavastatin": {"class": "statin", "category": "lipid_lowering"},
    "fluvastatin": {"class": "statin", "category": "lipid_lowering"},
    "lovastatin": {"class": "statin", "category": "lipid_lowering"},
    "ezetimibe": {"class": "ezetimibe", "category": "lipid_lowering"},
    "evolocumab": {"class": "pcsk9i", "category": "lipid_lowering"},
    "alirocumab": {"class": "pcsk9i", "category": "lipid_lowering"},
    "inclisiran": {"class": "pcsk9i", "category": "lipid_lowering"},
    "bempedoic acid": {"class": "acl_inhibitor", "category": "lipid_lowering"},
    "lomitapide": {"class": "mtp_inhibitor", "category": "lipid_lowering"},
    "mipomersen": {"class": "apo_b_antisense", "category": "lipid_lowering"},
    "rosiglitazone": {"class": "thiazolidinedione", "category": "glucose_lowering"},
    "pioglitazone": {"class": "thiazolidinedione", "category": "glucose_lowering"},
    "empagliflozin": {"class": "sglt2i", "category": "glucose_lowering"},
    "dapagliflozin": {"class": "sglt2i", "category": "glucose_lowering"},
    "canagliflozin": {"class": "sglt2i", "category": "glucose_lowering"},
    "ertugliflozin": {"class": "sglt2i", "category": "glucose_lowering"},
    "sotagliflozin": {"class": "sglt2i", "category": "glucose_lowering"},
    "semaglutide": {"class": "glp1ra", "category": "glucose_lowering"},
    "liraglutide": {"class": "glp1ra", "category": "glucose_lowering"},
    "dulaglutide": {"class": "glp1ra", "category": "glucose_lowering"},
    "exenatide": {"class": "glp1ra", "category": "glucose_lowering"},
    "tirzepatide": {"class": "glp1ra", "category": "glucose_lowering"},
    "metformin": {"class": "biguanide", "category": "glucose_lowering"},
    "sitagliptin": {"class": "dpp4i", "category": "glucose_lowering"},
    "saxagliptin": {"class": "dpp4i", "category": "glucose_lowering"},
    "alogliptin": {"class": "dpp4i", "category": "glucose_lowering"},
    "linagliptin": {"class": "dpp4i", "category": "glucose_lowering"},
    "vildagliptin": {"class": "dpp4i", "category": "glucose_lowering"},
    "insulin glargine": {"class": "insulin", "category": "glucose_lowering"},
    "insulin lispro": {"class": "insulin", "category": "glucose_lowering"},
    "warfarin": {"class": "vka", "category": "anticoagulation"},
    "apixaban": {"class": "doac", "category": "anticoagulation"},
    "rivaroxaban": {"class": "doac", "category": "anticoagulation"},
    "edoxaban": {"class": "doac", "category": "anticoagulation"},
    "dabigatran": {"class": "doac", "category": "anticoagulation"},
    "enoxaparin": {"class": "lmwh", "category": "anticoagulation"},
    "fondaparinux": {"class": "factor_xa_indirect", "category": "anticoagulation"},
    "ximelagatran": {"class": "direct_thrombin", "category": "anticoagulation"},
    "clopidogrel": {"class": "p2y12i", "category": "antiplatelet"},
    "ticagrelor": {"class": "p2y12i", "category": "antiplatelet"},
    "prasugrel": {"class": "p2y12i", "category": "antiplatelet"},
    "ticlopidine": {"class": "p2y12i", "category": "antiplatelet"},
    "cangrelor": {"class": "p2y12i", "category": "antiplatelet"},
    "vorapaxar": {"class": "par1_antagonist", "category": "antiplatelet"},
    "aspirin": {"class": "aspirin", "category": "antiplatelet"},
    "abciximab": {"class": "gpiib_iiia", "category": "antiplatelet"},
    "eptifibatide": {"class": "gpiib_iiia", "category": "antiplatelet"},
    "tirofiban": {"class": "gpiib_iiia", "category": "antiplatelet"},
    "ramipril": {"class": "acei", "category": "raas"},
    "enalapril": {"class": "acei", "category": "raas"},
    "lisinopril": {"class": "acei", "category": "raas"},
    "captopril": {"class": "acei", "category": "raas"},
    "perindopril": {"class": "acei", "category": "raas"},
    "losartan": {"class": "arb", "category": "raas"},
    "valsartan": {"class": "arb", "category": "raas"},
    "irbesartan": {"class": "arb", "category": "raas"},
    "telmisartan": {"class": "arb", "category": "raas"},
    "candesartan": {"class": "arb", "category": "raas"},
    "olmesartan": {"class": "arb", "category": "raas"},
    "sacubitril": {"class": "arni", "category": "raas"},
    "aliskiren": {"class": "direct_renin", "category": "raas"},
    "spironolactone": {"class": "mra", "category": "raas"},
    "eplerenone": {"class": "mra", "category": "raas"},
    "finerenone": {"class": "ns_mra", "category": "raas"},
    "esaxerenone": {"class": "ns_mra", "category": "raas"},
    "metoprolol": {"class": "beta_blocker", "category": "anti_adrenergic"},
    "carvedilol": {"class": "beta_blocker", "category": "anti_adrenergic"},
    "bisoprolol": {"class": "beta_blocker", "category": "anti_adrenergic"},
    "nebivolol": {"class": "beta_blocker", "category": "anti_adrenergic"},
    "atenolol": {"class": "beta_blocker", "category": "anti_adrenergic"},
    "propranolol": {"class": "beta_blocker", "category": "anti_adrenergic"},
    "amlodipine": {"class": "ccb", "category": "vasodilator"},
    "nifedipine": {"class": "ccb", "category": "vasodilator"},
    "diltiazem": {"class": "ccb", "category": "vasodilator"},
    "verapamil": {"class": "ccb", "category": "vasodilator"},
    "felodipine": {"class": "ccb", "category": "vasodilator"},
    "hydralazine": {"class": "direct_vasodilator", "category": "vasodilator"},
    "nitroprusside": {"class": "direct_vasodilator", "category": "vasodilator"},
    "isosorbide dinitrate": {"class": "nitrate", "category": "vasodilator"},
    "nitroglycerin": {"class": "nitrate", "category": "vasodilator"},
    "bosentan": {"class": "era", "category": "pulmonary_hypertension"},
    "ambrisentan": {"class": "era", "category": "pulmonary_hypertension"},
    "macitentan": {"class": "era", "category": "pulmonary_hypertension"},
    "sildenafil": {"class": "pde5i", "category": "pulmonary_hypertension"},
    "tadalafil": {"class": "pde5i", "category": "pulmonary_hypertension"},
    "riociguat": {"class": "sgc_stimulator", "category": "pulmonary_hypertension"},
    "epoprostenol": {"class": "prostacyclin", "category": "pulmonary_hypertension"},
    "treprostinil": {"class": "prostacyclin", "category": "pulmonary_hypertension"},
    "selexipag": {"class": "ip_agonist", "category": "pulmonary_hypertension"},
    "amiodarone": {"class": "class_iii_antiarrhythmic", "category": "antiarrhythmic"},
    "dronedarone": {"class": "class_iii_antiarrhythmic", "category": "antiarrhythmic"},
    "sotalol": {"class": "class_iii_antiarrhythmic", "category": "antiarrhythmic"},
    "flecainide": {"class": "class_ic_antiarrhythmic", "category": "antiarrhythmic"},
    "propafenone": {"class": "class_ic_antiarrhythmic", "category": "antiarrhythmic"},
    "digoxin": {"class": "cardiac_glycoside", "category": "heart_failure"},
    "ivabradine": {"class": "if_inhibitor", "category": "heart_failure"},
    "vericiguat": {"class": "sgc_stimulator", "category": "heart_failure"},
    "omecamtiv mecarbil": {"class": "cardiac_myosin_activator", "category": "heart_failure"},
    "levosimendan": {"class": "calcium_sensitizer", "category": "heart_failure"},
    "milrinone": {"class": "pde3i", "category": "heart_failure"},
    "dobutamine": {"class": "inotrope", "category": "heart_failure"},
    "nesiritide": {"class": "bnp_analogue", "category": "heart_failure"},
    "serelaxin": {"class": "relaxin_analogue", "category": "heart_failure"},
    "ularitide": {"class": "anp_analogue", "category": "heart_failure"},
    "tolvaptan": {"class": "v2ra", "category": "heart_failure"},
    "hydroxychloroquine": {"class": "antimalarial", "category": "anti_inflammatory"},
    "colchicine": {"class": "colchicine", "category": "anti_inflammatory"},
    "canakinumab": {"class": "il1_inhibitor", "category": "anti_inflammatory"},
    "methotrexate": {"class": "antimetabolite", "category": "anti_inflammatory"},
    "ziltivekimab": {"class": "il6_inhibitor", "category": "anti_inflammatory"},
    "darapladib": {"class": "lp_pla2_inhibitor", "category": "anti_inflammatory"},
    "varespladib": {"class": "spla2_inhibitor", "category": "anti_inflammatory"},
    "losmapimod": {"class": "p38_mapk_inhibitor", "category": "anti_inflammatory"},
    "aprotinin": {"class": "serine_protease_inhibitor", "category": "surgical_adjunct"},
    "tranexamic acid": {"class": "antifibrinolytic", "category": "surgical_adjunct"},
    "alteplase": {"class": "thrombolytic", "category": "thrombolysis"},
    "tenecteplase": {"class": "thrombolytic", "category": "thrombolysis"},
    "reteplase": {"class": "thrombolytic", "category": "thrombolysis"},
    "streptokinase": {"class": "thrombolytic", "category": "thrombolysis"}
  },
  "procedures": {
    "percutaneous coronary intervention": {"class": "pci", "category": "revascularization"},
    "coronary angioplasty": {"class": "pci", "category": "revascularization"},
    "balloon angioplasty": {"class": "pci", "category": "revascularization"},
    "drug-eluting stent": {"class": "des", "category": "revascularization"},
    "bare metal stent": {"class": "bms", "category": "revascularization"},
    "bioresorbable scaffold": {"class": "brs", "category": "revascularization"},
    "drug-coated balloon": {"class": "dcb", "category": "revascularization"},
    "coronary artery bypass": {"class": "cabg", "category": "revascularization"},
    "surgical revascularization": {"class": "cabg", "category": "revascularization"},
    "catheter ablation": {"class": "ablation", "category": "electrophysiology"},
    "radiofrequency ablation": {"class": "ablation", "category": "electrophysiology"},
    "cryoablation": {"class": "ablation", "category": "electrophysiology"},
    "pulsed field ablation": {"class": "pfa", "category": "electrophysiology"},
    "cardiac resynchronization": {"class": "crt", "category": "device_therapy"},
    "implantable cardioverter": {"class": "icd", "category": "device_therapy"},
    "left ventricular assist": {"class": "lvad", "category": "device_therapy"},
    "intra-aortic balloon pump": {"class": "iabp", "category": "mechanical_support"},
    "impella": {"class": "impella", "category": "mechanical_support"},
    "extracorporeal membrane": {"class": "ecmo", "category": "mechanical_support"},
    "transcatheter aortic valve": {"class": "tavr", "category": "structural_heart"},
    "mitral clip": {"class": "teer", "category": "structural_heart"},
    "watchman": {"class": "laao", "category": "structural_heart"},
    "left atrial appendage": {"class": "laao", "category": "structural_heart"},
    "renal denervation": {"class": "renal_denervation", "category": "hypertension_device"},
    "baroreflex activation": {"class": "bat", "category": "hypertension_device"},
    "pulmonary artery catheter": {"class": "pac", "category": "monitoring"},
    "swan-ganz": {"class": "pac", "category": "monitoring"},
    "cardiac rehabilitation": {"class": "cardiac_rehab", "category": "rehabilitation"},
    "exercise training": {"class": "exercise", "category": "rehabilitation"},
    "stem cell therapy": {"class": "stem_cell", "category": "regenerative"},
    "bone marrow cell": {"class": "stem_cell", "category": "regenerative"},
    "mesenchymal stem cell": {"class": "stem_cell", "category": "regenerative"},
    "gene therapy": {"class": "gene_therapy", "category": "regenerative"},
    "enhanced external counterpulsation": {"class": "eecp", "category": "non_invasive"},
    "therapeutic hypothermia": {"class": "hypothermia", "category": "neuroprotection"},
    "remote ischemic conditioning": {"class": "ric", "category": "conditioning"}
  },
  "brand_to_generic": {
    "lipitor": "atorvastatin",
    "crestor": "rosuvastatin",
    "zocor": "simvastatin",
    "plavix": "clopidogrel",
    "brilinta": "ticagrelor",
    "effient": "prasugrel",
    "eliquis": "apixaban",
    "xarelto": "rivaroxaban",
    "pradaxa": "dabigatran",
    "entresto": "sacubitril",
    "jardiance": "empagliflozin",
    "farxiga": "dapagliflozin",
    "invokana": "canagliflozin",
    "ozempic": "semaglutide",
    "victoza": "liraglutide",
    "trulicity": "dulaglutide",
    "mounjaro": "tirzepatide",
    "repatha": "evolocumab",
    "praluent": "alirocumab",
    "leqvio": "inclisiran",
    "avandia": "rosiglitazone",
    "actos": "pioglitazone",
    "nexletol": "bempedoic acid",
    "corlanor": "ivabradine",
    "verquvo": "vericiguat",
    "multaq": "dronedarone",
    "kerendia": "finerenone",
    "norvasc": "amlodipine",
    "tekturna": "aliskiren",
    "natrecor": "nesiritide"
  }
}
```

- [ ] **Step 6: Create kill_events.json**

Create `data/kill_events.json`:

```json
[
  {"id": "KE001", "year": 2006, "event": "ILLUMINATE trial terminated — excess CV mortality with torcetrapib", "category": "landmark_negative_trial", "interventions": ["torcetrapib"], "classes": ["cetp_inhibitor"], "source": "NEJM 2007;357:2109-22", "doi": "10.1056/NEJMoa0706628", "impact": "Killed torcetrapib; cast doubt on entire CETP inhibitor class"},
  {"id": "KE002", "year": 2007, "event": "Nissen meta-analysis — rosiglitazone increases MI risk", "category": "fda_safety_action", "interventions": ["rosiglitazone"], "classes": ["thiazolidinedione"], "source": "NEJM 2007;356:2457-71", "doi": "10.1056/NEJMoa072761", "impact": "FDA REMS; sales collapsed; drove CV outcome trial mandates for all diabetes drugs"},
  {"id": "KE003", "year": 2006, "event": "BART trial — aprotinin excess mortality vs tranexamic acid", "category": "fda_safety_action", "interventions": ["aprotinin"], "classes": ["serine_protease_inhibitor"], "source": "NEJM 2008;358:2319-31", "doi": "10.1056/NEJMoa0802395", "impact": "FDA withdrew aprotinin from market in 2007"},
  {"id": "KE004", "year": 2011, "event": "AIM-HIGH — niacin + statin no better than statin alone", "category": "landmark_negative_trial", "interventions": ["niacin"], "classes": ["niacin"], "source": "NEJM 2011;365:2255-67", "doi": "10.1056/NEJMoa1107579", "impact": "First major blow to raise-HDL hypothesis"},
  {"id": "KE005", "year": 2013, "event": "HPS2-THRIVE — niacin + laropiprant no benefit + excess harm", "category": "landmark_negative_trial", "interventions": ["niacin"], "classes": ["niacin"], "source": "NEJM 2014;371:203-12", "doi": "10.1056/NEJMoa1300955", "impact": "Final nail for niacin in CV prevention"},
  {"id": "KE006", "year": 2012, "event": "dal-OUTCOMES — dalcetrapib futility in ACS patients", "category": "landmark_negative_trial", "interventions": ["dalcetrapib"], "classes": ["cetp_inhibitor"], "source": "NEJM 2012;367:2089-99", "doi": "10.1056/NEJMoa1206797", "impact": "Second CETP failure; class-wide skepticism deepened"},
  {"id": "KE007", "year": 2015, "event": "ACCELERATE — evacetrapib no CV benefit despite massive HDL increase", "category": "landmark_negative_trial", "interventions": ["evacetrapib"], "classes": ["cetp_inhibitor"], "source": "NEJM 2017;376:1933-43", "doi": "10.1056/NEJMoa1609581", "impact": "Third CETP failure; raise-HDL hypothesis largely abandoned"},
  {"id": "KE008", "year": 2014, "event": "ALTITUDE — aliskiren + ACEI/ARB causes harm in diabetic CKD", "category": "landmark_negative_trial", "interventions": ["aliskiren"], "classes": ["direct_renin"], "source": "NEJM 2012;367:2204-13", "doi": "10.1056/NEJMoa1208799", "impact": "FDA contraindicated dual RAAS blockade; killed aliskiren market"},
  {"id": "KE009", "year": 2016, "event": "SCIPIO retraction + multiple cardiac stem cell fraud investigations", "category": "paradigm_shift", "interventions": ["stem cell therapy", "bone marrow cell"], "classes": ["stem_cell"], "source": "Lancet 2014 retraction; Nature 2018 investigation", "doi": null, "impact": "Entire cardiac regeneration field discredited; Harvard investigations"},
  {"id": "KE010", "year": 2017, "event": "ORBITA — PCI no better than sham for stable angina symptoms", "category": "landmark_negative_trial", "interventions": ["percutaneous coronary intervention"], "classes": ["pci"], "source": "Lancet 2018;391:31-40", "doi": "10.1016/S0140-6736(17)32714-9", "impact": "Challenged PCI for stable CAD; reduced elective PCI volumes"},
  {"id": "KE011", "year": 2019, "event": "ISCHEMIA — invasive strategy no hard-endpoint benefit in stable CAD", "category": "landmark_negative_trial", "interventions": ["percutaneous coronary intervention"], "classes": ["pci"], "source": "NEJM 2020;382:1395-1407", "doi": "10.1056/NEJMoa1915922", "impact": "Confirmed ORBITA; stable CAD revascularization declined further"},
  {"id": "KE012", "year": 2020, "event": "RECOVERY — hydroxychloroquine no benefit for COVID-19", "category": "landmark_negative_trial", "interventions": ["hydroxychloroquine"], "classes": ["antimalarial"], "source": "NEJM 2020;383:2030-40", "doi": "10.1056/NEJMoa2022926", "impact": "Rapid death of HCQ for COVID; trial registrations collapsed"},
  {"id": "KE013", "year": 2007, "event": "DES superiority over BMS established — multiple trials", "category": "competitor_displacement", "interventions": ["bare metal stent"], "classes": ["bms"], "source": "Multiple RCTs 2005-2007", "doi": null, "impact": "BMS displaced by DES in majority of PCI cases"},
  {"id": "KE014", "year": 2012, "event": "Second-gen DES (Xience, Resolute) superiority over first-gen (Cypher, Taxus)", "category": "competitor_displacement", "interventions": ["drug-eluting stent"], "classes": ["des"], "source": "Multiple RCTs", "doi": null, "impact": "First-gen DES withdrawn from most markets"},
  {"id": "KE015", "year": 2008, "event": "PAC-Man + ESCAPE — PA catheter no benefit in HF/ICU management", "category": "landmark_negative_trial", "interventions": ["pulmonary artery catheter", "swan-ganz"], "classes": ["pac"], "source": "JAMA 2005;294:1625-33; NEJM 2006;354:2213-24", "doi": null, "impact": "Swan-Ganz catheter use declined >80% over next decade"},
  {"id": "KE016", "year": 2014, "event": "SYMPLICITY HTN-3 — renal denervation failed sham-controlled trial", "category": "landmark_negative_trial", "interventions": ["renal denervation"], "classes": ["renal_denervation"], "source": "NEJM 2014;370:1393-401", "doi": "10.1056/NEJMoa1402670", "impact": "Renal denervation field collapsed; later partially resurrected (SPYRAL)"},
  {"id": "KE017", "year": 2016, "event": "PCSK9i availability displaced lomitapide/mipomersen for FH", "category": "competitor_displacement", "interventions": ["lomitapide", "mipomersen"], "classes": ["mtp_inhibitor", "apo_b_antisense"], "source": "Market shift post-FOURIER/ODYSSEY", "doi": null, "impact": "Niche therapies with poor side-effect profile displaced by PCSK9i"},
  {"id": "KE018", "year": 2010, "event": "DOAC era begins — DOACs displace warfarin for AF", "category": "competitor_displacement", "interventions": ["warfarin"], "classes": ["vka"], "source": "RE-LY, ROCKET-AF, ARISTOTLE, ENGAGE AF-TIMI 48", "doi": null, "impact": "Warfarin research volume declined as DOACs became standard"},
  {"id": "KE019", "year": 2013, "event": "RELAX-AHF-2 failed — serelaxin no mortality benefit in acute HF", "category": "landmark_negative_trial", "interventions": ["serelaxin"], "classes": ["relaxin_analogue"], "source": "NEJM 2019;381:716-26", "doi": "10.1056/NEJMoa1902292", "impact": "Novartis abandoned serelaxin development"},
  {"id": "KE020", "year": 2005, "event": "ASCEND-HF — nesiritide no benefit in acute HF, safety concerns", "category": "landmark_negative_trial", "interventions": ["nesiritide"], "classes": ["bnp_analogue"], "source": "NEJM 2011;365:32-43", "doi": "10.1056/NEJMoa1100171", "impact": "Nesiritide use collapsed after earlier safety concerns confirmed as null"},
  {"id": "KE021", "year": 2014, "event": "TRUE-AHF — ularitide no benefit in acute HF", "category": "landmark_negative_trial", "interventions": ["ularitide"], "classes": ["anp_analogue"], "source": "NEJM 2017;376:1956-64", "doi": "10.1056/NEJMoa1601895", "impact": "Natriuretic peptide analogue approach for acute HF abandoned"},
  {"id": "KE022", "year": 2014, "event": "STABILITY — darapladib no CV benefit despite Lp-PLA2 inhibition", "category": "landmark_negative_trial", "interventions": ["darapladib"], "classes": ["lp_pla2_inhibitor"], "source": "NEJM 2014;370:1702-11", "doi": "10.1056/NEJMoa1315878", "impact": "Lp-PLA2 inhibition abandoned as anti-inflammatory CV strategy"},
  {"id": "KE023", "year": 2012, "event": "VISTA-16 — varespladib increases CV events (stopped for harm)", "category": "landmark_negative_trial", "interventions": ["varespladib"], "classes": ["spla2_inhibitor"], "source": "JAMA 2014;311:498-506", "doi": "10.1001/jama.2013.284711", "impact": "sPLA2 inhibition abandoned; caused harm rather than benefit"},
  {"id": "KE024", "year": 2005, "event": "Ximelagatran withdrawn — hepatotoxicity", "category": "fda_safety_action", "interventions": ["ximelagatran"], "classes": ["direct_thrombin"], "source": "AstraZeneca voluntary withdrawal 2006", "doi": null, "impact": "First oral direct thrombin inhibitor killed by liver toxicity; paved way for dabigatran"},
  {"id": "KE025", "year": 2009, "event": "GPIIb/IIIa inhibitors declining — bleeding risk vs P2Y12i", "category": "competitor_displacement", "interventions": ["abciximab", "eptifibatide", "tirofiban"], "classes": ["gpiib_iiia"], "source": "ACCOAST, EARLY-ACS, multiple trials", "doi": null, "impact": "Routine upstream GPIIb/IIIa use abandoned; now bailout only"},
  {"id": "KE026", "year": 2017, "event": "ABSORB III long-term — bioresorbable scaffold higher thrombosis vs DES", "category": "landmark_negative_trial", "interventions": ["bioresorbable scaffold"], "classes": ["brs"], "source": "Lancet 2017;390:1799-1808", "doi": "10.1016/S0140-6736(17)32503-5", "impact": "Abbott pulled Absorb from market 2017; BRS concept shelved"},
  {"id": "KE027", "year": 2012, "event": "IABP-SHOCK II — IABP no benefit in cardiogenic shock", "category": "landmark_negative_trial", "interventions": ["intra-aortic balloon pump"], "classes": ["iabp"], "source": "NEJM 2012;367:1287-96", "doi": "10.1056/NEJMoa1208410", "impact": "IABP downgraded from Class I to IIb; usage declined sharply"},
  {"id": "KE028", "year": 2019, "event": "DAPA-HF — dapagliflozin benefit in HFrEF regardless of diabetes", "category": "competitor_displacement", "interventions": ["digoxin"], "classes": ["cardiac_glycoside"], "source": "NEJM 2019;381:1995-2008", "doi": "10.1056/NEJMoa1911303", "impact": "SGLT2i displaced digoxin from HF treatment algorithms"},
  {"id": "KE029", "year": 2014, "event": "LOSMAPIMOD — p38 MAPK inhibition no CV benefit post-MI", "category": "landmark_negative_trial", "interventions": ["losmapimod"], "classes": ["p38_mapk_inhibitor"], "source": "JAMA 2016;315:1591-99", "doi": "10.1001/jama.2016.2986", "impact": "p38 MAPK pathway for CV inflammation abandoned"},
  {"id": "KE030", "year": 2008, "event": "ENHANCE — ezetimibe + statin no IMT benefit vs statin alone", "category": "landmark_negative_trial", "interventions": ["ezetimibe"], "classes": ["ezetimibe"], "source": "NEJM 2008;358:1431-43", "doi": "10.1056/NEJMoa0800742", "impact": "Ezetimibe questioned until IMPROVE-IT 2015 partially rescued it (ZOMBIE)"},
  {"id": "KE031", "year": 2018, "event": "Renal denervation resurrected — SPYRAL HTN-OFF MED positive", "category": "landmark_negative_trial", "interventions": ["renal denervation"], "classes": ["renal_denervation"], "source": "Lancet 2018;391:2346-55", "doi": "10.1016/S0140-6736(18)30951-6", "impact": "Partial resurrection of renal denervation with better patient selection (ZOMBIE)"},
  {"id": "KE032", "year": 2011, "event": "EECP declined — limited evidence, insurance coverage dropped", "category": "guideline_downgrade", "interventions": ["enhanced external counterpulsation"], "classes": ["eecp"], "source": "AHA/ACC guideline updates", "doi": null, "impact": "EECP use became marginal; few new trials registered"},
  {"id": "KE033", "year": 2010, "event": "Therapeutic hypothermia scope narrowed — TTM trial showed 33C not better than 36C", "category": "landmark_negative_trial", "interventions": ["therapeutic hypothermia"], "classes": ["hypothermia"], "source": "NEJM 2013;369:2197-2206", "doi": "10.1056/NEJMoa1310519", "impact": "Aggressive cooling abandoned; targeted temperature management replaced it"},
  {"id": "KE034", "year": 2012, "event": "Dronedarone — PALLAS stopped for harm in permanent AF", "category": "fda_safety_action", "interventions": ["dronedarone"], "classes": ["class_iii_antiarrhythmic"], "source": "NEJM 2011;365:2268-76", "doi": "10.1056/NEJMoa1109867", "impact": "Dronedarone restricted to paroxysmal AF only; market share collapsed"}
]
```

- [ ] **Step 7: Commit**

```bash
cd C:/Models/TherapyGraveyard && git add pipeline/requirements.txt .gitignore data/drug_class_map.json data/kill_events.json && git commit -m "feat: project setup — drug class map (200+ drugs, 50 procedures) + 34 kill events"
```

---

## Task 2: Extraction Module (AACT Query)

**Files:**
- Create: `C:\Models\TherapyGraveyard\pipeline\extract.py`

- [ ] **Step 1: Write extract.py**

```python
"""Extract CV drug and procedure interventions from AACT database."""

import os
import json
import sys
import io
from datetime import datetime

# Windows UTF-8 console fix
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

try:
    import psycopg2
except ImportError:
    print("pip install psycopg2-binary")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # .env vars can be set manually

CV_CONDITION_PATTERN = (
    "%(heart failure"
    "|coronary artery disease"
    "|myocardial infarction"
    "|atrial fibrillation"
    "|atrial flutter"
    "|stroke"
    "|hypertension"
    "|cardiovascular"
    "|cardiac arrest"
    "|angina"
    "|atherosclerosis"
    "|peripheral artery disease"
    "|peripheral arterial disease"
    "|heart attack"
    "|cardiomyopathy"
    "|aortic stenosis"
    "|aortic valve"
    "|mitral valve"
    "|mitral regurgitation"
    "|pulmonary hypertension"
    "|pulmonary arterial hypertension"
    "|chronic kidney disease"
    "|diabetic nephropathy"
    "|diabetic kidney disease"
    "|diabetes mellitus"
    "|type 2 diabetes"
    "|acute coronary syndrome"
    "|venous thromboembolism"
    "|deep vein thrombosis"
    "|pulmonary embolism"
    "|arrhythmia"
    "|tachycardia"
    "|cardiac surgery"
    "|coronary bypass"
    "|heart transplant"
    "|cardiogenic shock)%"
)

SQL_INTERVENTIONS = """
SELECT
    s.nct_id,
    i.name                AS intervention_name,
    i.intervention_type,
    s.brief_title         AS title,
    s.overall_status      AS status,
    s.phase,
    s.enrollment,
    s.start_date,
    s.primary_completion_date,
    s.source              AS sponsor_name,
    s.source_class        AS sponsor_class,
    s.study_type
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
ORDER BY s.start_date, s.nct_id
"""


def connect_aact():
    """Connect to AACT PostgreSQL database."""
    user = os.environ.get("AACT_USER")
    pw = os.environ.get("AACT_PASSWORD")
    if not user or not pw:
        raise RuntimeError("Set AACT_USER and AACT_PASSWORD environment variables")
    return psycopg2.connect(
        host="aact-db.ctti-clinicaltrials.org",
        port=5432,
        dbname="aact",
        user=user,
        password=pw,
        connect_timeout=30,
        sslmode="require",
    )


def extract_cv_interventions():
    """Query AACT for all CV intervention records 2005+."""
    print("Connecting to AACT...")
    conn = connect_aact()
    cur = conn.cursor()

    print("Querying CV interventions (this may take 1-2 minutes)...")
    cur.execute(SQL_INTERVENTIONS, {"cv_pattern": CV_CONDITION_PATTERN})

    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    print(f"Fetched {len(rows)} intervention records.")

    records = []
    for row in rows:
        rec = dict(zip(columns, row))
        # Convert dates to ISO strings
        for key in ("start_date", "primary_completion_date"):
            val = rec.get(key)
            if val is not None:
                rec[key] = val.isoformat() if isinstance(val, datetime) else str(val)
        records.append(rec)

    cur.close()
    conn.close()
    return records


def save_raw(records, path="data/cv_interventions_raw.json"):
    """Save raw extraction to JSON."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"extracted_at": datetime.utcnow().isoformat(), "count": len(records), "records": records}, f, indent=2, default=str)
    print(f"Saved {len(records)} records to {path}")


if __name__ == "__main__":
    records = extract_cv_interventions()
    save_raw(records)
```

- [ ] **Step 2: Test the AACT connection (dry run)**

```bash
cd C:/Models/TherapyGraveyard && python -c "from pipeline.extract import connect_aact; c = connect_aact(); print('Connected!'); c.close()"
```

Expected: `Connected!` (if credentials are set)

- [ ] **Step 3: Run the full extraction**

```bash
cd C:/Models/TherapyGraveyard && python -m pipeline.extract
```

Expected: Fetches 30,000-80,000 intervention records, saves to `data/cv_interventions_raw.json`.

- [ ] **Step 4: Commit**

```bash
cd C:/Models/TherapyGraveyard && git add pipeline/extract.py && git commit -m "feat: AACT extraction — CV drug + procedure interventions 2005-2025"
```

---

## Task 3: Normalization Module

**Files:**
- Create: `C:\Models\TherapyGraveyard\pipeline\normalize.py`
- Create: `C:\Models\TherapyGraveyard\tests\test_normalize.py`

- [ ] **Step 1: Write test_normalize.py**

```python
"""Tests for drug name normalization."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.normalize import normalize_name, classify_intervention, build_timeseries

def test_lowercase_strip_dosage():
    assert normalize_name("Atorvastatin 40mg tablets") == "atorvastatin"
    assert normalize_name("EMPAGLIFLOZIN 10 MG") == "empagliflozin"
    assert normalize_name("Clopidogrel 75mg oral") == "clopidogrel"

def test_brand_to_generic():
    assert normalize_name("Lipitor") == "atorvastatin"
    assert normalize_name("Plavix 75mg") == "clopidogrel"
    assert normalize_name("Entresto 97/103 mg") == "sacubitril"
    assert normalize_name("Jardiance 25mg") == "empagliflozin"

def test_procedure_normalization():
    assert normalize_name("Percutaneous Coronary Intervention (PCI)") == "percutaneous coronary intervention"
    assert normalize_name("CABG surgery") == "coronary artery bypass"

def test_classify_known_drug():
    result = classify_intervention("atorvastatin", "Drug")
    assert result["class"] == "statin"
    assert result["category"] == "lipid_lowering"
    assert result["type"] == "drug"

def test_classify_known_procedure():
    result = classify_intervention("catheter ablation", "Procedure")
    assert result["class"] == "ablation"
    assert result["category"] == "electrophysiology"
    assert result["type"] == "procedure"

def test_classify_unknown():
    result = classify_intervention("xyznotadrug", "Drug")
    assert result["class"] == "unknown"
    assert result["category"] == "unknown"

def test_build_timeseries():
    records = [
        {"intervention_name": "atorvastatin", "start_date": "2010-03-01", "nct_id": "NCT001", "status": "COMPLETED", "phase": "PHASE3", "enrollment": 500, "sponsor_class": "INDUSTRY", "intervention_type": "Drug"},
        {"intervention_name": "atorvastatin", "start_date": "2010-09-15", "nct_id": "NCT002", "status": "COMPLETED", "phase": "PHASE3", "enrollment": 300, "sponsor_class": "OTHER", "intervention_type": "Drug"},
        {"intervention_name": "atorvastatin", "start_date": "2012-06-01", "nct_id": "NCT003", "status": "TERMINATED", "phase": "PHASE2", "enrollment": 100, "sponsor_class": "INDUSTRY", "intervention_type": "Drug"},
    ]
    ts = build_timeseries(records)
    assert "atorvastatin" in ts
    entry = ts["atorvastatin"]
    # 2010 should have 2 trials, 2012 should have 1
    assert entry["yearly_counts"][2010 - 2005] == 2
    assert entry["yearly_counts"][2012 - 2005] == 1
    assert entry["total_trials"] == 3
    assert entry["total_enrollment"] == 900

if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS {name}")
            except AssertionError as e:
                print(f"  FAIL {name}: {e}")
    print("Done.")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd C:/Models/TherapyGraveyard && python tests/test_normalize.py
```

Expected: FAIL (normalize module doesn't exist yet).

- [ ] **Step 3: Write normalize.py**

```python
"""Normalize drug/procedure names and build yearly time-series."""

import json
import os
import re

_CLASS_MAP = None
_BRAND_MAP = None

# Patterns to strip from drug names
_DOSAGE_RE = re.compile(
    r'\s*\d+[\./]?\d*\s*(mg|mcg|ug|g|ml|units?|iu|mmol|%|tablets?|capsules?|oral|iv|sc|im|injection|solution|film|coated|extended|release|modified|delayed|patch|inhaler|spray|cream|gel|ointment|powder|suspension|vial|prefilled|syringe|pen|daily|bid|tid|qd|qid|prn|twice|once)\b.*',
    re.IGNORECASE
)
_PAREN_RE = re.compile(r'\s*\([^)]*\)\s*')
_TRAILING_SALT_RE = re.compile(r'\s+(calcium|sodium|potassium|hydrochloride|hcl|mesylate|maleate|fumarate|tartrate|besylate|succinate|sulfate|phosphate|acetate|citrate|bromide)\b.*', re.IGNORECASE)


def _load_class_map():
    global _CLASS_MAP, _BRAND_MAP
    if _CLASS_MAP is not None:
        return
    path = os.path.join(os.path.dirname(__file__), "..", "data", "drug_class_map.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    _CLASS_MAP = {}
    for key, val in data.get("drugs", {}).items():
        _CLASS_MAP[key.lower()] = val
    for key, val in data.get("procedures", {}).items():
        _CLASS_MAP[key.lower()] = val
    _BRAND_MAP = {}
    for brand, generic in data.get("brand_to_generic", {}).items():
        _BRAND_MAP[brand.lower()] = generic.lower()


def normalize_name(raw_name):
    """Normalize an intervention name to a canonical form."""
    _load_class_map()
    name = raw_name.strip().lower()

    # Remove parenthetical content
    name = _PAREN_RE.sub(' ', name).strip()

    # Remove dosage/formulation
    name = _DOSAGE_RE.sub('', name).strip()

    # Remove trailing salt forms
    name = _TRAILING_SALT_RE.sub('', name).strip()

    # Remove trailing whitespace and non-alpha
    name = re.sub(r'[,;:]+$', '', name).strip()

    # Brand → generic lookup
    if name in _BRAND_MAP:
        name = _BRAND_MAP[name]

    # Check first word for brand match (e.g., "Lipitor 40mg" → first word "lipitor")
    first_word = name.split()[0] if name else name
    if first_word in _BRAND_MAP:
        name = _BRAND_MAP[first_word]

    # Procedure aliases
    procedure_aliases = {
        "cabg": "coronary artery bypass",
        "cabg surgery": "coronary artery bypass",
        "ptca": "percutaneous coronary intervention",
        "angioplasty": "percutaneous coronary intervention",
        "swan-ganz catheter": "pulmonary artery catheter",
        "swan ganz": "pulmonary artery catheter",
    }
    if name in procedure_aliases:
        name = procedure_aliases[name]

    return name


def classify_intervention(normalized_name, intervention_type):
    """Classify a normalized intervention into class/category."""
    _load_class_map()

    # Direct lookup
    if normalized_name in _CLASS_MAP:
        info = _CLASS_MAP[normalized_name]
        itype = "procedure" if intervention_type in ("Procedure", "Device") else "drug"
        return {"class": info["class"], "category": info["category"], "type": itype}

    # Fuzzy match: check if any key is a substring of the name or vice versa
    for key, info in _CLASS_MAP.items():
        if key in normalized_name or normalized_name in key:
            itype = "procedure" if intervention_type in ("Procedure", "Device") else "drug"
            return {"class": info["class"], "category": info["category"], "type": itype}

    # Try Levenshtein if available
    try:
        from Levenshtein import distance
        best_dist = 999
        best_info = None
        for key, info in _CLASS_MAP.items():
            d = distance(normalized_name, key)
            if d < best_dist and d <= 2:
                best_dist = d
                best_info = info
        if best_info:
            itype = "procedure" if intervention_type in ("Procedure", "Device") else "drug"
            return {"class": best_info["class"], "category": best_info["category"], "type": itype}
    except ImportError:
        pass

    itype = "procedure" if intervention_type in ("Procedure", "Device") else "drug"
    return {"class": "unknown", "category": "unknown", "type": itype}


START_YEAR = 2005
END_YEAR = 2025
N_YEARS = END_YEAR - START_YEAR + 1


def build_timeseries(records):
    """Build yearly trial-count time-series per normalized intervention.

    Args:
        records: list of dicts with keys: intervention_name, start_date, nct_id,
                 status, phase, enrollment, sponsor_class, intervention_type

    Returns:
        dict mapping normalized_name -> {
            yearly_counts: [int]*N_YEARS,
            yearly_enrollment: [int]*N_YEARS,
            total_trials: int, total_enrollment: int,
            terminated_count: int, max_phase: str,
            industry_count: int, nct_ids: [str],
            intervention_type: str
        }
    """
    timeseries = {}

    for rec in records:
        raw_name = rec.get("intervention_name", "")
        if not raw_name:
            continue

        name = normalize_name(raw_name)
        if not name or len(name) < 2:
            continue

        # Parse year
        start = rec.get("start_date", "")
        if not start:
            continue
        try:
            year = int(str(start)[:4])
        except (ValueError, TypeError):
            continue
        if year < START_YEAR or year > END_YEAR:
            continue

        idx = year - START_YEAR
        enrollment = rec.get("enrollment") or 0
        if not isinstance(enrollment, (int, float)):
            try:
                enrollment = int(enrollment)
            except (ValueError, TypeError):
                enrollment = 0

        nct_id = rec.get("nct_id", "")
        status = (rec.get("status") or "").upper()
        phase = rec.get("phase") or ""
        sponsor_class = (rec.get("sponsor_class") or "").upper()
        itype = rec.get("intervention_type") or "Drug"

        if name not in timeseries:
            timeseries[name] = {
                "yearly_counts": [0] * N_YEARS,
                "yearly_enrollment": [0] * N_YEARS,
                "total_trials": 0,
                "total_enrollment": 0,
                "terminated_count": 0,
                "max_phase": "",
                "industry_count": 0,
                "nct_ids": [],
                "intervention_type": itype,
            }

        entry = timeseries[name]

        # Deduplicate: skip if this NCT already counted for this intervention
        if nct_id and nct_id in entry["nct_ids"]:
            continue

        entry["yearly_counts"][idx] += 1
        entry["yearly_enrollment"][idx] += enrollment
        entry["total_trials"] += 1
        entry["total_enrollment"] += enrollment
        if nct_id:
            entry["nct_ids"].append(nct_id)

        if status in ("TERMINATED", "WITHDRAWN"):
            entry["terminated_count"] += 1

        if sponsor_class == "INDUSTRY":
            entry["industry_count"] += 1

        # Track max phase
        phase_order = {"PHASE1": 1, "PHASE1/PHASE2": 1.5, "PHASE2": 2,
                       "PHASE2/PHASE3": 2.5, "PHASE3": 3, "PHASE3/PHASE4": 3.5, "PHASE4": 4}
        current_rank = phase_order.get(entry["max_phase"], 0)
        new_rank = phase_order.get(phase, 0)
        if new_rank > current_rank:
            entry["max_phase"] = phase

    return timeseries


def normalize_raw_file(input_path="data/cv_interventions_raw.json", output_path="data/cv_interventions_timeseries.json"):
    """Load raw extraction, normalize, build time-series, classify, and save."""
    with open(input_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    records = raw["records"]
    print(f"Loaded {len(records)} raw records.")

    timeseries = build_timeseries(records)
    print(f"Built time-series for {len(timeseries)} unique interventions.")

    # Classify each intervention
    output = []
    for name, ts in timeseries.items():
        info = classify_intervention(name, ts["intervention_type"])
        output.append({
            "intervention": name,
            "class": info["class"],
            "category": info["category"],
            "type": info["type"],
            "yearly_counts": ts["yearly_counts"],
            "yearly_enrollment": ts["yearly_enrollment"],
            "total_trials": ts["total_trials"],
            "total_enrollment": ts["total_enrollment"],
            "terminated_count": ts["terminated_count"],
            "termination_rate": round(ts["terminated_count"] / ts["total_trials"], 3) if ts["total_trials"] > 0 else 0,
            "max_phase": ts["max_phase"],
            "industry_rate": round(ts["industry_count"] / ts["total_trials"], 3) if ts["total_trials"] > 0 else 0,
            "nct_ids": ts["nct_ids"],
        })

    # Sort by total_trials descending
    output.sort(key=lambda x: x["total_trials"], reverse=True)

    classified_count = sum(1 for o in output if o["class"] != "unknown")
    print(f"Classified {classified_count}/{len(output)} interventions ({100*classified_count//len(output)}%).")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"Saved to {output_path}")
    return output


if __name__ == "__main__":
    normalize_raw_file()
```

- [ ] **Step 4: Run tests**

```bash
cd C:/Models/TherapyGraveyard && python tests/test_normalize.py
```

Expected: All 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd C:/Models/TherapyGraveyard && git add pipeline/normalize.py tests/test_normalize.py && git commit -m "feat: normalization module — drug name cleanup, class mapping, time-series builder"
```

---

## Task 4: Scoring Module (Peak-and-Decline Algorithm)

**Files:**
- Create: `C:\Models\TherapyGraveyard\pipeline\score.py`
- Create: `C:\Models\TherapyGraveyard\tests\test_score.py`

- [ ] **Step 1: Write test_score.py**

```python
"""Tests for peak-and-decline scoring algorithm."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.score import score_intervention, score_all, link_kill_events

N = 21  # 2005-2025

def _make_entry(yearly_counts, **kwargs):
    defaults = {
        "intervention": "test_drug",
        "class": "test_class",
        "category": "test_cat",
        "type": "drug",
        "yearly_counts": yearly_counts,
        "yearly_enrollment": [c * 100 for c in yearly_counts],
        "total_trials": sum(yearly_counts),
        "total_enrollment": sum(c * 100 for c in yearly_counts),
        "terminated_count": 0,
        "termination_rate": 0,
        "max_phase": "PHASE3",
        "industry_rate": 0.5,
        "nct_ids": [],
    }
    defaults.update(kwargs)
    return defaults

def test_dead_intervention():
    """Drug peaked in 2008, no trials after 2012."""
    counts = [0]*N
    counts[2] = 5   # 2007
    counts[3] = 10  # 2008 peak
    counts[4] = 8   # 2009
    counts[5] = 3   # 2010
    counts[6] = 1   # 2011
    counts[7] = 1   # 2012
    entry = _make_entry(counts)
    result = score_intervention(entry)
    assert result["status"] == "DEAD", f"Expected DEAD, got {result['status']}"
    assert result["peak_year"] == 2008
    assert result["decline_ratio"] >= 0.9
    assert result["years_silent"] >= 3

def test_alive_intervention():
    """Drug with steady or growing trials."""
    counts = [0]*N
    for i in range(N):
        counts[i] = 3 + i  # Growing
    entry = _make_entry(counts)
    result = score_intervention(entry)
    assert result["status"] == "ALIVE", f"Expected ALIVE, got {result['status']}"

def test_declining_intervention():
    """Drug peaked then declining but still active."""
    counts = [0]*N
    counts[5] = 15   # 2010 peak
    counts[6] = 12
    counts[7] = 10
    counts[8] = 8
    counts[9] = 6
    counts[10] = 5
    counts[11] = 4
    counts[12] = 3
    counts[13] = 3
    counts[14] = 2
    counts[15] = 2
    counts[16] = 2
    counts[17] = 1
    counts[18] = 1  # 2023
    counts[19] = 1  # 2024
    counts[20] = 1  # 2025
    entry = _make_entry(counts)
    result = score_intervention(entry)
    assert result["status"] in ("DECLINING", "DEAD"), f"Expected DECLINING or DEAD, got {result['status']}"

def test_zombie_intervention():
    """Drug was dead but has 1 recent trial."""
    counts = [0]*N
    counts[2] = 8   # 2007 peak
    counts[3] = 5
    counts[4] = 1
    # Silent 2010-2023
    counts[19] = 1  # 2024 — comeback
    entry = _make_entry(counts)
    result = score_intervention(entry)
    assert result["status"] == "ZOMBIE", f"Expected ZOMBIE, got {result['status']}"

def test_skip_low_volume():
    """Intervention with peak < 3 should be skipped."""
    counts = [0]*N
    counts[5] = 2
    counts[6] = 1
    entry = _make_entry(counts)
    result = score_intervention(entry)
    assert result["status"] == "SKIPPED"

def test_half_life():
    """Drug with clear peak and decline should have computable half-life."""
    counts = [0]*N
    counts[3] = 20  # 2008 peak
    counts[4] = 15
    counts[5] = 10
    counts[6] = 8   # half-life reached here (< 10)
    counts[7] = 3
    entry = _make_entry(counts)
    result = score_intervention(entry)
    assert result["half_life"] is not None
    assert result["half_life"] >= 1

def test_kill_event_linkage():
    """Kill event within +-2 years of peak should link as probable cause."""
    scored = [{
        "intervention": "torcetrapib",
        "peak_year": 2006,
        "status": "DEAD",
    }]
    events = [{"id": "KE001", "year": 2006, "interventions": ["torcetrapib"], "classes": []}]
    linked = link_kill_events(scored, events)
    assert len(linked[0]["kill_events"]) == 1
    assert linked[0]["kill_events"][0] == "KE001"
    assert linked[0]["probable_cause"] == "KE001"

if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS {name}")
            except AssertionError as e:
                print(f"  FAIL {name}: {e}")
    print("Done.")
```

- [ ] **Step 2: Write score.py**

```python
"""Peak-and-decline scoring algorithm for therapeutic attrition."""

import json
import os

START_YEAR = 2005
END_YEAR = 2025
N_YEARS = END_YEAR - START_YEAR + 1


def _rolling_avg(counts, window=3):
    """3-year rolling average, edge-padded."""
    n = len(counts)
    smoothed = [0.0] * n
    half = window // 2
    for i in range(n):
        lo = max(0, i - half)
        hi = min(n, i + half + 1)
        smoothed[i] = sum(counts[lo:hi]) / (hi - lo)
    return smoothed


def score_intervention(entry):
    """Score a single intervention's attrition status.

    Args:
        entry: dict with 'yearly_counts' (list of ints, length N_YEARS),
               'intervention', 'total_trials', 'total_enrollment', etc.

    Returns:
        dict with all original fields plus: status, peak_year, peak_count,
        recent_count, decline_ratio, years_silent, half_life, lifespan,
        smoothed_counts
    """
    counts = entry["yearly_counts"]
    smoothed = _rolling_avg(counts)

    # Find peak
    peak_idx = 0
    peak_val = smoothed[0]
    for i in range(1, N_YEARS):
        if smoothed[i] > peak_val:
            peak_val = smoothed[i]
            peak_idx = i
    peak_year = START_YEAR + peak_idx
    peak_count = peak_val

    result = dict(entry)
    result["smoothed_counts"] = [round(s, 2) for s in smoothed]
    result["peak_year"] = peak_year
    result["peak_count"] = round(peak_count, 2)

    # Skip if peak too low
    if peak_count < 3:
        result["status"] = "SKIPPED"
        result["recent_count"] = 0
        result["decline_ratio"] = 0
        result["years_silent"] = 0
        result["half_life"] = None
        result["lifespan"] = 0
        result["kill_events"] = []
        result["probable_cause"] = None
        return result

    # Recent activity: mean of last 3 years (2023-2025)
    recent_indices = [N_YEARS - 3, N_YEARS - 2, N_YEARS - 1]
    recent_count = sum(counts[i] for i in recent_indices) / len(recent_indices)

    # Decline ratio
    decline_ratio = 1 - (recent_count / peak_count) if peak_count > 0 else 0
    decline_ratio = max(0, min(1, decline_ratio))

    # Years silent: years since last trial registration
    years_silent = 0
    for i in range(N_YEARS - 1, -1, -1):
        if counts[i] >= 1:
            years_silent = (END_YEAR) - (START_YEAR + i)
            break
    else:
        years_silent = N_YEARS

    # Status classification
    if decline_ratio >= 0.90 and years_silent >= 3:
        # Check for zombie: dead but recent comeback
        has_recent = any(counts[i] >= 1 for i in [N_YEARS - 2, N_YEARS - 1])
        status = "ZOMBIE" if has_recent else "DEAD"
    elif decline_ratio >= 0.50 and years_silent >= 1:
        status = "DECLINING"
    else:
        status = "ALIVE"

    # Half-life: years from peak to first year where smoothed < peak/2
    half_life = None
    half_threshold = peak_count / 2
    for i in range(peak_idx + 1, N_YEARS):
        if smoothed[i] < half_threshold:
            half_life = i - peak_idx
            break

    # Lifespan: first trial to last trial
    first_year = None
    last_year = None
    for i in range(N_YEARS):
        if counts[i] >= 1:
            if first_year is None:
                first_year = START_YEAR + i
            last_year = START_YEAR + i
    lifespan = (last_year - first_year + 1) if first_year and last_year else 0

    result["recent_count"] = round(recent_count, 2)
    result["decline_ratio"] = round(decline_ratio, 3)
    result["years_silent"] = years_silent
    result["half_life"] = half_life
    result["lifespan"] = lifespan
    result["status"] = status
    result["kill_events"] = []
    result["probable_cause"] = None

    return result


def score_all(interventions):
    """Score all interventions and return sorted by status severity."""
    scored = [score_intervention(entry) for entry in interventions]
    # Remove SKIPPED
    scored = [s for s in scored if s["status"] != "SKIPPED"]
    # Sort: DEAD first, then ZOMBIE, DECLINING, ALIVE
    order = {"DEAD": 0, "ZOMBIE": 1, "DECLINING": 2, "ALIVE": 3}
    scored.sort(key=lambda x: (order.get(x["status"], 9), -x.get("total_trials", 0)))
    return scored


def link_kill_events(scored, kill_events):
    """Link kill events to scored interventions.

    A kill event links if:
    1. The intervention name matches an entry in the event's 'interventions' list, OR
    2. The intervention's class matches an entry in the event's 'classes' list
    AND the event year is within +-2 years of the intervention's peak_year.
    """
    for entry in scored:
        name = entry.get("intervention", "")
        cls = entry.get("class", "")
        peak = entry.get("peak_year", 0)
        matched = []

        for ev in kill_events:
            ev_year = ev.get("year", 0)
            ev_interventions = [i.lower() for i in ev.get("interventions", [])]
            ev_classes = [c.lower() for c in ev.get("classes", [])]

            name_match = name.lower() in ev_interventions
            class_match = cls.lower() in ev_classes if cls else False

            if name_match or class_match:
                matched.append(ev["id"])

        entry["kill_events"] = matched

        # Probable cause: kill event closest to peak year
        if matched:
            ev_map = {ev["id"]: ev for ev in kill_events}
            closest = None
            closest_dist = 999
            for eid in matched:
                ev = ev_map.get(eid)
                if ev:
                    dist = abs(ev["year"] - peak)
                    if dist <= 2 and dist < closest_dist:
                        closest = eid
                        closest_dist = dist
            entry["probable_cause"] = closest

    return scored


def score_file(input_path="data/cv_interventions_timeseries.json",
               kill_events_path="data/kill_events.json",
               output_path="data/attrition_scores.json"):
    """Load time-series, score, link kill events, save."""
    with open(input_path, "r", encoding="utf-8") as f:
        interventions = json.load(f)
    print(f"Loaded {len(interventions)} interventions.")

    scored = score_all(interventions)
    print(f"Scored {len(scored)} interventions (skipped {len(interventions) - len(scored)} low-volume).")

    # Load kill events
    with open(kill_events_path, "r", encoding="utf-8") as f:
        kill_events = json.load(f)
    scored = link_kill_events(scored, kill_events)

    counts = {}
    for s in scored:
        counts[s["status"]] = counts.get(s["status"], 0) + 1
    print(f"Status breakdown: {counts}")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(scored, f, indent=2)
    print(f"Saved to {output_path}")
    return scored


if __name__ == "__main__":
    score_file()
```

- [ ] **Step 3: Run tests**

```bash
cd C:/Models/TherapyGraveyard && python tests/test_score.py
```

Expected: All 7 tests PASS.

- [ ] **Step 4: Commit**

```bash
cd C:/Models/TherapyGraveyard && git add pipeline/score.py tests/test_score.py && git commit -m "feat: peak-and-decline scoring — DEAD/DECLINING/ALIVE/ZOMBIE classification + kill event linkage"
```

---

## Task 5: Export Module

**Files:**
- Create: `C:\Models\TherapyGraveyard\pipeline\export.py`

- [ ] **Step 1: Write export.py**

```python
"""Export scored attrition data as embeddable JSON for the HTML app."""

import json
import os


def build_training_data(scored_path="data/attrition_scores.json",
                        kill_events_path="data/kill_events.json",
                        output_path="data/training_data.json"):
    """Build the final JSON blob for HTML embedding.

    Strips nct_ids to save space (keep only counts).
    Adds class-level roll-up entries.
    """
    with open(scored_path, "r", encoding="utf-8") as f:
        scored = json.load(f)

    with open(kill_events_path, "r", encoding="utf-8") as f:
        kill_events = json.load(f)

    # Strip nct_ids (keep trial count only) for space
    for entry in scored:
        entry["nct_id_count"] = len(entry.get("nct_ids", []))
        entry.pop("nct_ids", None)

    # Build class-level roll-ups
    from pipeline.score import score_all, link_kill_events, START_YEAR, N_YEARS

    class_agg = {}
    for entry in scored:
        cls = entry.get("class", "unknown")
        if cls == "unknown":
            continue
        if cls not in class_agg:
            class_agg[cls] = {
                "intervention": cls + " (class)",
                "class": cls,
                "category": entry.get("category", "unknown"),
                "type": entry.get("type", "drug"),
                "yearly_counts": [0] * N_YEARS,
                "yearly_enrollment": [0] * N_YEARS,
                "total_trials": 0,
                "total_enrollment": 0,
                "terminated_count": 0,
                "max_phase": "",
                "industry_count": 0,
                "nct_ids": [],
                "intervention_type": entry.get("type", "Drug"),
                "_is_class_rollup": True,
                "molecules": [],
            }
        agg = class_agg[cls]
        for i in range(N_YEARS):
            agg["yearly_counts"][i] += entry["yearly_counts"][i]
            agg["yearly_enrollment"][i] += entry.get("yearly_enrollment", [0]*N_YEARS)[i]
        agg["total_trials"] += entry["total_trials"]
        agg["total_enrollment"] += entry["total_enrollment"]
        agg["terminated_count"] += entry.get("terminated_count", 0)
        agg["molecules"].append(entry["intervention"])

    class_entries = list(class_agg.values())
    for ce in class_entries:
        ce["termination_rate"] = round(ce["terminated_count"] / ce["total_trials"], 3) if ce["total_trials"] > 0 else 0

    class_scored = score_all(class_entries)
    class_scored = link_kill_events(class_scored, kill_events)

    # Clean up class entries for export
    for cs in class_scored:
        cs.pop("nct_ids", None)
        cs["nct_id_count"] = 0

    output = {
        "generated": __import__("datetime").datetime.utcnow().isoformat(),
        "start_year": START_YEAR,
        "end_year": START_YEAR + N_YEARS - 1,
        "molecule_count": len(scored),
        "class_count": len(class_scored),
        "kill_events": kill_events,
        "molecules": scored,
        "classes": class_scored,
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    size_kb = os.path.getsize(output_path) / 1024
    print(f"Exported {len(scored)} molecules + {len(class_scored)} classes to {output_path} ({size_kb:.0f} KB)")
    return output


if __name__ == "__main__":
    build_training_data()
```

- [ ] **Step 2: Commit**

```bash
cd C:/Models/TherapyGraveyard && git add pipeline/export.py && git commit -m "feat: export module — build training_data.json with class roll-ups for HTML embedding"
```

---

## Task 6: Run Full Pipeline

**Files:** None (pipeline execution only)

- [ ] **Step 1: Run extraction from AACT**

```bash
cd C:/Models/TherapyGraveyard && python -m pipeline.extract
```

Expected: Fetches 30,000-80,000 records, saves `data/cv_interventions_raw.json`.

- [ ] **Step 2: Run normalization**

```bash
cd C:/Models/TherapyGraveyard && python -m pipeline.normalize
```

Expected: Normalizes to ~500-1,000 unique interventions, saves `data/cv_interventions_timeseries.json`.

- [ ] **Step 3: Run scoring**

```bash
cd C:/Models/TherapyGraveyard && python -m pipeline.score
```

Expected: Scores and classifies, outputs status breakdown (DEAD/DECLINING/ALIVE/ZOMBIE), saves `data/attrition_scores.json`.

- [ ] **Step 4: Run export**

```bash
cd C:/Models/TherapyGraveyard && python -m pipeline.export
```

Expected: Builds `data/training_data.json` (~200-400 KB) with molecules + class roll-ups + kill events.

- [ ] **Step 5: Verify pipeline output**

```bash
cd C:/Models/TherapyGraveyard && python -c "
import json
d = json.load(open('data/training_data.json'))
print(f'Molecules: {d[\"molecule_count\"]}')
print(f'Classes: {d[\"class_count\"]}')
print(f'Kill events: {len(d[\"kill_events\"])}')
statuses = {}
for m in d['molecules']:
    statuses[m['status']] = statuses.get(m['status'], 0) + 1
print(f'Status breakdown: {statuses}')
# Print top 5 dead interventions
dead = [m for m in d['molecules'] if m['status'] == 'DEAD']
dead.sort(key=lambda x: x['total_trials'], reverse=True)
print('Top 5 dead (by trial count):')
for m in dead[:5]:
    print(f'  {m[\"intervention\"]} ({m[\"class\"]}) — {m[\"total_trials\"]} trials, peak {m[\"peak_year\"]}, cause: {m.get(\"probable_cause\", \"unknown\")}')
"
```

- [ ] **Step 6: Run all tests**

```bash
cd C:/Models/TherapyGraveyard && python tests/test_normalize.py && python tests/test_score.py
```

Expected: All 14 tests PASS.

- [ ] **Step 7: Commit pipeline output verification**

```bash
cd C:/Models/TherapyGraveyard && git add -A && git commit -m "feat: full pipeline verified — extract + normalize + score + export"
```

---

## Task 7: HTML App — CSS + Structure + Data Loading

**Files:**
- Create: `C:\Models\TherapyGraveyard\TherapyGraveyard.html`

This task creates the HTML skeleton with CSS, tab/view switching, data loading, and filter toolbar. The data from `training_data.json` will be embedded directly.

- [ ] **Step 1: Create TherapyGraveyard.html skeleton**

Create the file with: DOCTYPE, CSS variables (light/dark), Plotly.js CDN, tab bar with 3 view buttons (Graveyard, Autopsy, Statistics), filter toolbar, data embedding placeholder, dark mode toggle, and view-switching JS.

The HTML app should follow the patterns from `.claude/rules/html-apps.md`:
- Single-file HTML
- CSS variables for theming
- `tg-` prefix for all element IDs
- `tg_` prefix for localStorage keys
- Plotly.js for charts
- Accessibility: ARIA labels, keyboard navigation, skip-nav

The file will be large (~2,000-3,000 lines). Build it incrementally:
- This task: skeleton + CSS + data loading + view switching (~500 lines)
- Task 8: Graveyard Timeline view (~600 lines)
- Task 9: Autopsy view (~400 lines)
- Task 10: Statistics dashboard (~500 lines)

The full HTML content for this step is too large to inline here. The implementer should:
1. Create the HTML file with standard boilerplate (DOCTYPE, head, Plotly CDN)
2. Add CSS variables matching CardioOracle's pattern (`:root` light, `[data-theme="dark"]` dark)
3. Add `.tg-*` CSS classes for layout, toolbar, badges, tables, charts
4. Add the header with title "TherapyGraveyard" and dark mode toggle
5. Add 3 view buttons: "Graveyard Timeline", "Autopsy", "Statistics"
6. Add filter toolbar: status (Dead/Declining/Alive/Zombie checkboxes), type (Drug/Procedure), category dropdown, level toggle (Molecule/Class)
7. Add empty view containers: `tg-graveyard-view`, `tg-autopsy-view`, `tg-stats-view`
8. Add `<script>` block with:
   - `const TG_DATA = /* EMBED training_data.json here */;`
   - View switching function
   - Filter state management
   - Dark mode toggle (localStorage `tg_theme`)
   - `tgFilterData()` function that returns filtered interventions based on current filter state
9. Read `data/training_data.json` and embed it as the `TG_DATA` constant

- [ ] **Step 2: Verify the file opens in a browser with view switching working**

- [ ] **Step 3: Commit**

```bash
cd C:/Models/TherapyGraveyard && git add TherapyGraveyard.html && git commit -m "feat: HTML app skeleton — CSS, view switching, filters, data embedded"
```

---

## Task 8: HTML App — Graveyard Timeline View

**Files:**
- Modify: `C:\Models\TherapyGraveyard\TherapyGraveyard.html`

Add the Graveyard Timeline view — a Plotly heatmap showing interventions (rows) x years (columns) with trial counts as intensity, color-coded by status, and kill event markers.

- [ ] **Step 1: Implement `tgRenderGraveyard()` function**

The function should:
1. Get filtered interventions from `tgFilterData()`
2. Sort by peak year (ascending), then by status
3. Build a Plotly heatmap with:
   - X-axis: years 2005-2025
   - Y-axis: intervention names (truncated to 25 chars)
   - Z-values: trial counts per year
   - Custom colorscale: low=transparent, high=blue
4. Overlay status indicators: color-code the y-axis labels (green/amber/red/purple)
5. Add kill event markers as red diamond scatter points
6. Add click handler: clicking a row switches to Autopsy view for that intervention
7. Use Plotly.newPlot/react pattern with dark mode support
8. Set `tg-graveyard-view` as the target div

- [ ] **Step 2: Wire the view button to call `tgRenderGraveyard()` on view switch**

- [ ] **Step 3: Verify the heatmap renders with test data**

- [ ] **Step 4: Commit**

```bash
cd C:/Models/TherapyGraveyard && git add TherapyGraveyard.html && git commit -m "feat: graveyard timeline — heatmap with status colors + kill event markers"
```

---

## Task 9: HTML App — Autopsy View

**Files:**
- Modify: `C:\Models\TherapyGraveyard\TherapyGraveyard.html`

Add the Autopsy drill-down view showing a single intervention's rise and fall.

- [ ] **Step 1: Implement `tgRenderAutopsy(interventionName)` function**

The function should:
1. Find the intervention in `TG_DATA.molecules` (or `.classes`)
2. Render a trial count line chart (Plotly) with peak annotated
3. Show kill event panel: event description, DOI link, category badge
4. Show metrics card: lifespan, total trials, total enrollment, max phase, termination rate, half-life, status badge
5. Show class context: if molecule view, show small-multiples sparklines of sibling molecules in the same class
6. Show trial list placeholder (NCT ID count — full list would require re-querying AACT)
7. Add "Back to Graveyard" button

- [ ] **Step 2: Wire click handler from Graveyard heatmap to switch to Autopsy view**

- [ ] **Step 3: Commit**

```bash
cd C:/Models/TherapyGraveyard && git add TherapyGraveyard.html && git commit -m "feat: autopsy view — intervention drill-down with kill events + class context"
```

---

## Task 10: HTML App — Statistics Dashboard

**Files:**
- Modify: `C:\Models\TherapyGraveyard\TherapyGraveyard.html`

Add the Statistics Dashboard view.

- [ ] **Step 1: Implement `tgRenderStats()` function**

The function should render 6 charts/tables:
1. **Death toll summary**: Pie chart of DEAD/DECLINING/ALIVE/ZOMBIE counts
2. **Deadliest period**: Bar chart — which 5-year period (2005-09, 2010-14, 2015-19, 2020-25) killed the most interventions
3. **Kill cause breakdown**: Horizontal bar chart of kill categories
4. **Survival curve**: Kaplan-Meier style — X=years from first trial, Y=proportion still alive. Step function.
5. **Class mortality table**: Table sorted by attrition rate (dead/total molecules in class)
6. **Top 10 wasted investment**: Table of dead interventions sorted by total_enrollment descending (most patients enrolled in ultimately abandoned research)

All charts use Plotly with dark mode support. Tables use `.tg-table` CSS class.

- [ ] **Step 2: Wire the Statistics view button**

- [ ] **Step 3: Commit**

```bash
cd C:/Models/TherapyGraveyard && git add TherapyGraveyard.html && git commit -m "feat: statistics dashboard — 6 charts including survival curve + wasted investment"
```

---

## Task 11: HTML App — CSV Export + Final Polish

**Files:**
- Modify: `C:\Models\TherapyGraveyard\TherapyGraveyard.html`

- [ ] **Step 1: Add CSV export function**

Implement `tgExportCSV()`:
- Exports all molecule-level data as CSV
- Columns: intervention, class, category, type, status, peak_year, peak_count, decline_ratio, years_silent, half_life, lifespan, total_trials, total_enrollment, termination_rate, max_phase, probable_cause, yearly counts (2005-2025)
- Blob download with `URL.revokeObjectURL()` after use
- Filename: `therapy_graveyard_YYYY-MM-DD.csv`

- [ ] **Step 2: Add Export CSV button to toolbar**

- [ ] **Step 3: Final verification**

Open in browser, verify:
- All 3 views render correctly
- Filters work (status, type, category, level toggle)
- Autopsy click-through works
- Dark mode works
- CSV export downloads correctly
- No console errors

- [ ] **Step 4: Commit**

```bash
cd C:/Models/TherapyGraveyard && git add TherapyGraveyard.html && git commit -m "feat: CSV export + final polish — TherapyGraveyard complete"
```

---

## Task 12: Full Test Suite + Smoke Test

**Files:** None (testing only)

- [ ] **Step 1: Run all Python tests**

```bash
cd C:/Models/TherapyGraveyard && python tests/test_normalize.py && python tests/test_score.py
```

Expected: All 14 tests PASS.

- [ ] **Step 2: Browser smoke test**

Open `TherapyGraveyard.html` in Chrome:
1. Graveyard Timeline loads with interventions visible
2. Click an intervention → Autopsy view opens with trial curve
3. Switch to Statistics → all 6 charts render
4. Toggle dark mode → all views render correctly
5. Toggle Class/Molecule level → heatmap updates
6. Filter by status (Dead only) → heatmap filters correctly
7. Export CSV → file downloads
8. No console errors

- [ ] **Step 3: Final commit**

```bash
cd C:/Models/TherapyGraveyard && git add -A && git commit -m "feat: TherapyGraveyard v1.0 — CV therapeutic attrition map complete"
```

---

## Spec Coverage Verification

| Spec Section | Task(s) | Status |
|-------------|---------|--------|
| 1. Data Extraction Pipeline | Tasks 2, 6 | Covered |
| 2. Peak-and-Decline Scoring | Task 4 | Covered |
| 3. Kill Event Enrichment | Tasks 1, 4 | Covered |
| 4a. Graveyard Timeline View | Task 8 | Covered |
| 4b. Autopsy View | Task 9 | Covered |
| 4c. Statistics Dashboard | Task 10 | Covered |
| 4d. Data & Technical (dark mode, CSV) | Tasks 7, 11 | Covered |
| 5. Project Structure | Task 1 | Covered |
| Normalization | Task 3 | Covered |
| Class roll-up | Task 5 | Covered |
| Full pipeline run | Task 6 | Covered |
| Browser smoke test | Task 12 | Covered |
