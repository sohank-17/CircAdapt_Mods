# CircAdapt Data README

This document summarizes the data currently present in `C:\Projects\CircAdapt`, what each dataset likely represents, and how it is used by the repository code.

## Data At A Glance

- The project mainly contains **simulation state data** (`.mat`) and **result figures** (`.svg`) tied to CircAdapt studies.
- There is one **external spreadsheet** in `Custom/` that appears to be a broader population database.
- No large raw time-series CSV datasets were found in the current checkout.

## Data Inventory

### 1) Koopsen2024ParameterSubsetReduction (parameter screening/personalization)

Location: `circadapt/Koopsen2024ParameterSubsetReduction/`

Files:
- `PRefHF.mat` (~0.64 MB)
- `PRef_AHA18.mat` (~0.94 MB)
- `PRef_AHA18_CPP.mat` (~0.94 MB)

What this data is:
- Reference CircAdapt `P` structures used as starting states for Morris/Sobol/DMS-PSO pipelines.

What it is doing:
- Seeds baseline physiology before perturbing parameters.
- Supports 18-segment LV setups and C++/MEX solver workflows.

Used by:
- `MorrisScreening_input.m`, `SobolSamples.m`, `RunSobolSimulation.m`, `DMSPSO_main.m`, and `RunCPP*.m`.

---

### 2) Munneke2023 (perfusion/flow reserve under dyssynchrony)

Location: `circadapt/Munneke2023/Source Code/CircAdapt/`

Files:
- `PRef.mat` (~24.51 MB)
- `PRef_Hyp.mat` (~24.50 MB)
- `PRef_acuteLBBB.mat` (~24.77 MB)
- `PRef_acuteLBBB_Hyp.mat` (~24.76 MB)
- `PRef_chronicLBBB.mat` (~24.79 MB)
- `PRef_chronicLBBB_Hyp.mat` (~24.77 MB)
- `CorTerDat.xlsx` (~17 KB)

What this data is:
- Precomputed/reference model states for baseline, hyperemia, acute LBBB, and chronic LBBB scenarios.
- Coronary territory lookup/input table (`CorTerDat.xlsx`) used by coronary modeling scripts.

What it is doing:
- Allows direct comparison of perfusion and reserve across synchronous/asynchronous conditions.
- Drives figure reconstruction workflows without needing to rebuild every scenario from scratch.

Used by:
- `CircAdaptMain.m`, `plotFigures.m`, and coronary flow scripts (`CorFC*.m`, `CorArtVenV2p.m`, etc.).

---

### 3) Munneke2023 exported results (visual outputs)

Location: `circadapt/Munneke2023/Source Code/Results/`

Files (examples):
- `FlowRest_*.svg`, `FlowHyp_*.svg`
- `MFR_*.svg`, `IMP_*.svg`, `VO2_*.svg`, `WT_*.svg`, `StressStrain_*.svg`

What this data is:
- Static vector graphics of key manuscript-like outputs.

What it is doing:
- Serves as ready-to-share output artifacts and quick visual QC of model behavior by scenario.

---

### 4) Munneke2023 supplement

Location: `circadapt/Munneke2023/Supplemental Material.pdf` (~1.04 MB)

What this data is:
- Supplemental manuscript material describing context/method details.

What it is doing:
- Provides methodological interpretation for the simulation data and figures.

---

### 5) Custom external spreadsheet

Location: `Custom/SAS Database_multiple populations_for Amee Sangani.xlsx` (~0.24 MB)

What this data is:
- A standalone spreadsheet likely containing multi-population database content.

What it is doing:
- Not directly referenced by the currently scanned CircAdapt scripts; likely intended for custom analysis or future integration.

## Data Flow Across Repos

- **Reference states (`PRef*.mat`)** are the core reusable data assets.
- MATLAB/Python scripts mutate parameters, run CircAdapt solvers, and produce derived outputs.
- Derived outputs are either saved as arrays/structs during runs or exported as static figure files (`.svg`).

## Practical Takeaways

1. Most data here is **model-state data**, not raw clinical acquisition data.
2. `PRef*.mat` files are the key dependency for reproducible simulation starts.
3. Munneke2023 holds the richest scenario-state dataset (baseline, acute/chronic LBBB, hyperemia).
4. Koopsen2024 data is compact but essential for sensitivity and optimization pipelines.
5. The `Custom` spreadsheet is currently separate from automated repo workflows.
6. If you want a unified data pipeline, first decision should be whether to standardize all outputs into one format (for example `.mat` + metadata table).

## Suggested Next Step

If you want, I can add a second file `DATA_DICTIONARY.md` that maps the most important `P`-structure fields (for example pressures, volumes, stress/strain, coronary outputs) to plain-English meanings for faster onboarding.
