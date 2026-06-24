# CircAdapt + Custom HR Personalization Runbook

This document captures the workflow we followed and what we planned to do next when running CircAdapt from notebooks.

## 1) Installation Steps We Used

### What happened
1. We first tried a direct pip install of CircAdapt (`pip install circadapt`).
2. That direct path did not work in our environment.
3. We then checked the official CircAdapt distribution/download sources and used a prebuilt wheel (`.whl`) that matched our Python version and platform.
4. Installing from that compatible wheel worked, and we were able to import/use `circadapt` in Python.

### Practical install approach for Colab
1. Confirm the Python version in the runtime.
2. Use the CircAdapt wheel that matches that Python version and Linux platform.
3. Install the wheel with pip.
4. Verify by importing `circadapt` and instantiating `circadapt.VanOsta2024()`.

Notes:
- I am intentionally leaving this as a description (not code-heavy) per your request.
- The exact wheel filename used earlier is not recorded in the local project files, so use the matching wheel from the official CircAdapt source for your runtime.

## 2) What We Did in the Python Script

Primary script: `Custom/circadapt_hr_compare.py`

High-level flow:
1. Loaded the SAS workbook (`SAS Database_multiple populations_for Amee Sangani.xlsx`).
2. Cleaned/coerced core fields (HR, MAP, SBP, DBP, CO, SV, demographics, workload).
3. Filled missing hemodynamic and feature values using cohort medians, then global medians.
4. Built per-row targets and cohort context (`study|Group`).
5. Used 11 critical features for personalization context:
   - `sex`, `age`, `height`, `weight`, `BMI`, `BSA`, `study`, `Group`, `Condition_description`, `watts`, `rpe`
6. For each row:
   - Created `circadapt.VanOsta2024()`
   - Applied feature-informed parameter personalization (size, passive stiffness, active stress)
   - Set pressure-flow control targets (`Model.PFC.p0`, `Model.PFC.q0`)
   - Fit `t_cycle` by bounded candidate search
   - Ran model beats and extracted model MAP/SBP/DBP/CO/SV
7. Optimized against a weighted objective and reported:
   - Predicted HR (`60 / t_cycle`)
   - Absolute HR error vs dataset
   - Fit quality metrics
8. Saved outputs in `Custom/outputs` (CSV + summary text).

## 3) Our Notebook Plan Moving Forward

Primary notebook direction: `Custom/CircAdapt_HR_Personalization.ipynb`, with Colab as execution environment.

Planned workflow:
1. Keep the workflow staged and interpretable (not one-shot):
   - data cleaning -> group/activity mapping -> model mapping -> calibration -> evaluation
2. Move from only fitting `t_cycle` to multi-parameter bounded calibration:
   - `t_cycle`, `sf_mult`, `q_mult`, `p_mult`
3. Preserve explicit group logic:
   - Group 1 healthy
   - Group 2 HFrEF
   - Group 3 hypoxia
   - Group 4 LVAD proxy profile
4. Evaluate results at multiple levels:
   - overall MAE/RMSE
   - by group
   - by activity bin
5. Export notebook outputs to `outputs/` for reproducibility and downstream review.
6. Use Colab primarily as a stable runtime for installation and notebook execution.

## 4) VanOsta Model Notes (Reference for Our Custom Build)

Reference directory:
`circadapt/VanOsta2024NumericalCredibilityAssessment`

How it informed our custom work:
1. Core simulator interface: `circadapt.VanOsta2024()` became the baseline model object in our script/notebook.
2. Stability mindset: VanOsta scripts test solver/stability behavior across many runs; we mirrored this mindset by:
   - guarding model runs for crash handling
   - using bounded candidate searches rather than unconstrained fitting
3. Beat-based evaluation pattern: we also run fixed beats and then extract summary hemodynamic outputs.
4. Numerical pragmatism: we use compact candidate grids suitable for notebook-scale repeated simulation.

Useful VanOsta script context:
- `stability_single_beat.py`
- `stability_single_beat_TriSeg_accuracy.py`
- `stability_multi-beat.py`
- `stability_multi_reproducibility.py`
- `figure1.py`

Caveat noted in the local VanOsta README:
- Some multi-beat scripts reference `_benchmark_functions` that is not present in this checkout.

## Current Directory Mapping (for clarity)

- VanOsta reference model: `circadapt/VanOsta2024NumericalCredibilityAssessment`
- Custom work area: `Custom/`
- Generated outputs: `Custom/outputs/`
