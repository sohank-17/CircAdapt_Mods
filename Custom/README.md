# SAS Database README

File: `SAS Database_multiple populations_for Amee Sangani.xlsx`
Location: `C:\Projects\CircAdapt\Custom\`

## Purpose

This workbook appears to be a combined hemodynamic and cardiopulmonary exercise dataset across multiple study populations, intended for analysis/modeling support.

## Workbook Structure

- Sheets: `1` (`Sheet1`)
- Total columns: `113`
- Data rows: `363` (excluding header)

## High-Level Column Groups

### A) Cohort and subject metadata
Examples:
- `study`, `Group`, `subjectid`, `condition`, `Condition_description`, `sex`, `age`
- Anthropometrics: `height`, `weight`, `BMI`, `BSA`

### B) Exercise and protocol context
Examples:
- `Predicted_HR`, `PercentMPHR`, `kp`, `watts`, `rpe`
- Gas exchange/exercise variables: `VO2Lmin`, `VO2mlkgmin`, `VCO2`, `VE`, `RER`, `ETCO2`, `RR`

### C) Invasive hemodynamics and derived metrics
Examples:
- Right heart/pulmonary: `RAP`, `Rvsys`, `Rvdias`, `RVEDP`, `PAS`, `PAD`, `mPAP`, `PCWP`, `PVR`, `PAPI`
- Systemic: `SBP`, `DBP`, `MAP`, `TPR`
- Oxygen transport: `Art O2 Content`, `Ven O2 Content`, `avo2`
- Cardiac output/index: `co_swan`, `CI_swan`, `SV_Swan`

### D) Pressure-volume / Millar-derived metrics
Examples:
- `Millar file`, `Loops evaluated`
- `dP/dt +`, `dP/dt -`, `EDP`, `EDV`, `ESP`, `ESV`, `ESPVR`, `EDPVR`, `SW`, `TAU`
- Additional derived indices: `PRSW`, `EES`, `EA`, `EESEA`, `SCI`, `PVA`

## Important Data Quality Notes

1. Duplicate column names exist:
- `HR` appears twice
- `V max` appears twice
- `V min` appears twice
- `SV` appears twice
- `PVA` appears twice

2. Three trailing columns are blank (`columns 111-113`, empty header and no values).

3. Type inconsistency in multiple columns:
- Some physiologic columns contain mixed numeric/text values (for example string placeholders in otherwise numeric fields).

4. Missingness is variable by column:
- Core subject columns are mostly populated (~350/363 rows).
- Some exercise/advanced indices are sparse (for example `eSW`, `predictedVO2`, `percentpredictedvo2`).

## Suggested Interpretation Workflow

1. Treat this as a **wide analysis table** where each row is likely a subject-condition observation.
2. Standardize headers (trim spaces, resolve duplicates with suffixes).
3. Coerce known physiologic columns to numeric with NA on parse failures.
4. Build a per-column missingness report before modeling.
5. Define a minimal analysis subset (for example demographics + invasive hemodynamics + selected PV metrics).

## Practical Caveats

- Units are implied by names for many fields but not formally documented in the workbook metadata.
- Because duplicate labels exist, downstream scripts should reference columns by explicit renamed headers, not positional assumptions.
- `Millar file` and `Loops evaluated` suggest part of this table is linked to external waveform/loop processing artifacts.

## Quick Takeaways

- This is a rich multi-domain cardiovascular table (demographics + exercise + invasive + PV-loop metrics).
- It is analysis-ready only after light cleaning (duplicate names, type coercion, blank column removal).
- The dataset is likely very useful for stratified comparisons by `study`, `Group`, and `condition`.
- The strongest immediate value is in integrated phenotype profiling (hemodynamics + effort + PV mechanics in one sheet).
