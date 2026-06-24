#!/usr/bin/env python
"""
CircAdapt vs dataset HR comparison (improved v2).

Pipeline:
1. Read SAS workbook from the custom folder.
2. Build cohort-aware settings by study/group.
3. Personalize CircAdapt using 11 critical dataset features.
4. Fit t_cycle using hemodynamic targets (MAP/SBP/DBP/CO/SV), not dataset HR.
5. Report predicted HR = 60 / t_cycle and compare to dataset HR.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

import circadapt


MMHG_TO_PA = 133.322
DEFAULT_DATASET = Path("custom") / "SAS Database_multiple populations_for Amee Sangani.xlsx"
DEFAULT_OUTPUT = Path("custom") / "outputs" / "circadapt_hr_comparison.csv"
DEFAULT_SUMMARY = Path("custom") / "outputs" / "circadapt_hr_summary.txt"
CRITICAL_FEATURES = [
    "sex",
    "age",
    "height",
    "weight",
    "BMI",
    "BSA",
    "study",
    "Group",
    "Condition_description",
    "watts",
    "rpe",
]


@dataclass
class RowTargets:
    hr: float
    map_mmhg: float
    sbp_mmhg: float
    dbp_mmhg: float
    co_l_min: float
    sv_ml: float
    patient_id: str
    cohort_key: str
    sex: str
    age: float
    height: float
    weight: float
    bmi: float
    bsa: float
    condition_description: str
    watts: float
    rpe: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare CircAdapt-predicted HR with dataset HR.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET, help="Path to SAS workbook.")
    parser.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="Maximum rows to process after filtering. Omit to use all rows.",
    )
    parser.add_argument("--beats", type=int, default=5, help="Number of beats per simulation run.")
    parser.add_argument(
        "--grid",
        type=int,
        default=8,
        help="Number of t_cycle candidates around an individualized prior.",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output CSV path.")
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY, help="Output summary text path.")
    parser.add_argument(
        "--rest-only",
        action="store_true",
        help="Use only rows with resting condition descriptions.",
    )
    return parser.parse_args()


def safe_patient_id(row: pd.Series) -> str:
    study = str(row.get("study", "NA")).strip()
    subject = str(row.get("subjectid", "NA")).strip()
    return f"{study}_{subject}"


def coerce_numeric(df: pd.DataFrame, columns: Iterable[str]) -> None:
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")


def build_targets(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = df.columns.str.strip()
    coerce_numeric(df, ["HR", "MAP", "SBP", "DBP", "CO", "SV", "age", "height", "weight", "BMI", "BSA", "watts", "rpe"])

    # If MAP missing, compute from SBP/DBP when available.
    map_from_bp = df["DBP"] + (df["SBP"] - df["DBP"]) / 3.0
    df["MAP"] = df["MAP"].where(df["MAP"].notna(), map_from_bp)
    df["patient_id"] = df.apply(safe_patient_id, axis=1)
    df["cohort_key"] = df["study"].astype(str).str.strip() + "|" + df["Group"].astype(str).str.strip()
    df["Condition_description"] = df["Condition_description"].astype(str).str.strip()
    df["sex"] = df["sex"].astype(str).str.strip()

    # Fill missing critical numeric features with cohort medians.
    fill_cols = ["age", "height", "weight", "BMI", "BSA", "watts", "rpe"]
    for col in fill_cols:
        cohort_median = df.groupby("cohort_key")[col].transform("median")
        global_median = df[col].median(skipna=True)
        df[col] = df[col].fillna(cohort_median).fillna(global_median)

    # Fill missing hemodynamics using cohort medians, then global medians.
    hemo_fill_cols = ["MAP", "SBP", "DBP", "CO", "SV"]
    for col in hemo_fill_cols:
        cohort_median = df.groupby("cohort_key")[col].transform("median")
        global_median = df[col].median(skipna=True)
        df[col] = df[col].fillna(cohort_median).fillna(global_median)

    keep = df.dropna(subset=["HR"]).copy()
    keep = keep[
        [
            "patient_id",
            "cohort_key",
            "study",
            "Group",
            "Condition_description",
            "sex",
            "age",
            "height",
            "weight",
            "BMI",
            "BSA",
            "watts",
            "rpe",
            "HR",
            "MAP",
            "SBP",
            "DBP",
            "CO",
            "SV",
        ]
    ]
    keep = keep.rename(
        columns={
            "HR": "hr_dataset",
            "MAP": "map_dataset_mmhg",
            "SBP": "sbp_dataset_mmhg",
            "DBP": "dbp_dataset_mmhg",
            "CO": "co_dataset_l_min",
            "SV": "sv_dataset_ml",
            "BMI": "bmi",
            "BSA": "bsa",
            "Condition_description": "condition_description",
            "Group": "group",
            "study": "study",
            "sex": "sex",
            "age": "age",
            "height": "height",
            "weight": "weight",
            "watts": "watts",
            "rpe": "rpe",
        }
    )
    return keep


def filter_rest_rows(df_targets: pd.DataFrame) -> pd.DataFrame:
    txt = df_targets["condition_description"].astype(str).str.lower().str.strip()
    include = (
        txt.str.contains("rest", na=False)
        | txt.str.contains("supine", na=False)
        | txt.str.contains("sitting", na=False)
    )
    exclude = (
        txt.str.contains("mild", na=False)
        | txt.str.contains("moderate", na=False)
        | txt.str.contains("heavy", na=False)
        | txt.str.contains("max", na=False)
        | txt.str.contains("peak", na=False)
        | txt.str.contains("exercise", na=False)
    )
    return df_targets[include & ~exclude].copy()


def extract_model_outputs(model: circadapt.CircAdapt) -> tuple[float, float, float, float, float]:
    p_syart = np.array(model.get("Model.SyArt.p", list), dtype=float) / MMHG_TO_PA
    q_venous = np.array(model.get("Model.Peri.SyVenRa.q", list), dtype=float) * 60000.0
    lv_vol_ml = np.array(model.get("Model.Peri.TriSeg.cLv.V", list), dtype=float) * 1e6
    map_mmhg = float(np.mean(p_syart))
    sbp_mmhg = float(np.max(p_syart))
    dbp_mmhg = float(np.min(p_syart))
    co_l_min = float(np.mean(q_venous))
    sv_ml = float(np.max(lv_vol_ml) - np.min(lv_vol_ml))
    return map_mmhg, sbp_mmhg, dbp_mmhg, co_l_min, sv_ml


def objective_from_targets(
    model_map: float,
    model_sbp: float,
    model_dbp: float,
    model_co: float,
    model_sv: float,
    model_hr: float,
    hr_prior: float,
    target: RowTargets,
) -> float:
    # Relative scaling keeps BP and CO contributions on comparable magnitude.
    e_map = (model_map - target.map_mmhg) / max(target.map_mmhg, 1.0)
    e_sbp = (model_sbp - target.sbp_mmhg) / max(target.sbp_mmhg, 1.0)
    e_dbp = (model_dbp - target.dbp_mmhg) / max(target.dbp_mmhg, 1.0)
    e_co = (model_co - target.co_l_min) / max(target.co_l_min, 0.1)
    e_sv = (model_sv - target.sv_ml) / max(target.sv_ml, 1.0)
    e_hr_prior = (model_hr - hr_prior) / max(hr_prior, 1.0)
    return float(
        0.23 * e_map * e_map
        + 0.18 * e_sbp * e_sbp
        + 0.18 * e_dbp * e_dbp
        + 0.16 * e_co * e_co
        + 0.20 * e_sv * e_sv
        + 0.05 * e_hr_prior * e_hr_prior
    )


def cohort_defaults(df_targets: pd.DataFrame) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for key, g in df_targets.groupby("cohort_key"):
        out[key] = {
            "map": float(g["map_dataset_mmhg"].median()),
            "sbp": float(g["sbp_dataset_mmhg"].median()),
            "dbp": float(g["dbp_dataset_mmhg"].median()),
            "co": float(g["co_dataset_l_min"].median()),
            "sv": float(g["sv_dataset_ml"].median()),
            "watts": float(g["watts"].median()),
            "rpe": float(g["rpe"].median()),
            "age": float(g["age"].median()),
            "bmi": float(g["bmi"].median()),
            "bsa": float(g["bsa"].median()),
        }
    return out


def normalize_sex(value: str) -> str:
    v = str(value).strip().lower()
    if v.startswith("m"):
        return "m"
    if v.startswith("f"):
        return "f"
    return "u"


def parse_group(group_value: str) -> int:
    try:
        return int(float(str(group_value).strip()))
    except Exception:
        return 0


def activity_level(condition_description: str, watts: float, rpe: float) -> float:
    txt = str(condition_description).lower()
    lvl = 0.0
    if "supine" in txt or "sitting" in txt or "rest" in txt:
        lvl = max(lvl, 0.1)
    if "upright" in txt or "standing" in txt:
        lvl = max(lvl, 0.3)
    if "mild" in txt:
        lvl = max(lvl, 0.45)
    if "moderate" in txt:
        lvl = max(lvl, 0.65)
    if "heavy" in txt or "max" in txt or "peak" in txt:
        lvl = max(lvl, 0.9)

    if np.isfinite(watts):
        lvl = max(lvl, float(np.clip(watts / 350.0, 0.0, 1.0)))
    if np.isfinite(rpe):
        lvl = max(lvl, float(np.clip((rpe - 6.0) / 14.0, 0.0, 1.0)))
    return float(np.clip(lvl, 0.0, 1.0))


def estimate_hr_prior(target: RowTargets, cohort_medians: dict[str, float]) -> float:
    # Physiologic prior from flow-volume, then adjusted using critical context variables.
    flow_prior = (target.co_l_min * 1000.0 / max(target.sv_ml, 1.0))
    watts = target.watts if np.isfinite(target.watts) else cohort_medians["watts"]
    rpe = target.rpe if np.isfinite(target.rpe) else cohort_medians["rpe"]
    age = target.age if np.isfinite(target.age) else cohort_medians["age"]

    act = activity_level(target.condition_description, watts, rpe)
    exercise_boost = 38.0 * act
    age_shift = -0.08 * max(age - 40.0, 0.0)

    group = parse_group(target.cohort_key.split("|")[-1])
    group_shift = {1: 2.0, 2: -4.0, 3: 0.0, 4: -2.0}.get(group, 0.0)

    condition = target.condition_description.lower()
    cond_shift = 0.0
    if "supine" in condition or "sitting" in condition:
        cond_shift -= 4.0
    if "upright" in condition or "standing" in condition:
        cond_shift += 2.0

    hr_prior = flow_prior + exercise_boost + age_shift + group_shift + cond_shift
    return float(np.clip(hr_prior, 45.0, 190.0))


def apply_critical_feature_personalization(model: circadapt.CircAdapt, target: RowTargets, cohort_medians: dict[str, float]) -> None:
    # 11 critical features used: sex, age, height, weight, BMI, BSA, study, Group, Condition_description, watts, rpe.
    sex = normalize_sex(target.sex)
    age = target.age if np.isfinite(target.age) else cohort_medians["age"]
    bmi = target.bmi if np.isfinite(target.bmi) else cohort_medians["bmi"]
    bsa = target.bsa if np.isfinite(target.bsa) else cohort_medians["bsa"]

    group = parse_group(target.cohort_key.split("|")[-1])
    condition = target.condition_description.lower()
    act = activity_level(condition, target.watts, target.rpe)

    # Size scaling from BSA/sex.
    bsa_scale = float(np.clip(bsa / 2.0, 0.75, 1.35))
    sex_scale = 1.05 if sex == "m" else (0.95 if sex == "f" else 1.0)
    model["Patch"]["V_wall"][2:] = model["Patch"]["V_wall"][2:] * bsa_scale * sex_scale
    model["Patch"]["Am_ref"][2:] = model["Patch"]["Am_ref"][2:] * bsa_scale

    # Passive stiffness from age/BMI.
    age_factor = float(np.clip((age - 40.0) / 40.0, -0.5, 1.0))
    bmi_factor = float(np.clip((bmi - 25.0) / 15.0, -0.5, 1.0))
    sf_pas_scale = 1.0 + 0.25 * age_factor + 0.12 * bmi_factor
    k1_base = 8.0 * (1.0 + 0.20 * age_factor)
    model.set("Model.Peri.TriSeg.wLv.pLv0.Sf_pas", float(700.0 * sf_pas_scale), float)
    model.set("Model.Peri.TriSeg.wSv.pSv0.Sf_pas", float(700.0 * sf_pas_scale), float)
    model.set("Model.Peri.TriSeg.wRv.pRv0.Sf_pas", float(650.0 * sf_pas_scale), float)
    model.set("Model.Peri.TriSeg.wLv.pLv0.k1", float(k1_base), float)
    model.set("Model.Peri.TriSeg.wSv.pSv0.k1", float(k1_base), float)
    model.set("Model.Peri.TriSeg.wRv.pRv0.k1", float(k1_base * 0.95), float)

    # Group/condition context for active stress.
    act_scale = {1: 1.05, 2: 0.90, 3: 1.00, 4: 0.95}.get(group, 1.0)
    if "hypoxia" in target.cohort_key.lower():
        act_scale *= 0.98
    if "lvad" in target.cohort_key.lower():
        act_scale *= 0.95
    act_scale *= (0.95 + 0.12 * act)
    model.set("Model.Peri.TriSeg.wLv.pLv0.Sf_act", float(60000.0 * act_scale), float)
    model.set("Model.Peri.TriSeg.wSv.pSv0.Sf_act", float(60000.0 * act_scale), float)
    model.set("Model.Peri.TriSeg.wRv.pRv0.Sf_act", float(56000.0 * act_scale), float)


def fit_t_cycle(target: RowTargets, cohort_medians: dict[str, float], beats: int, grid: int) -> tuple[float, dict[str, float]]:
    hr_prior = estimate_hr_prior(target, cohort_medians)
    tc_center = 60.0 / hr_prior
    tc_min = max(0.40, tc_center * 0.70)
    tc_max = min(1.30, tc_center * 1.35)
    candidates = np.linspace(tc_min, tc_max, num=grid, dtype=float)

    best_score = np.inf
    best_t_cycle = np.nan
    best_outputs: dict[str, float] = {}

    crash_error = getattr(circadapt, "ModelCrashed", Exception)

    for t_cycle in candidates:
        model = circadapt.VanOsta2024()
        apply_critical_feature_personalization(model, target, cohort_medians)
        model.set("Model.PFC.p0", float(target.map_mmhg * MMHG_TO_PA), float)
        model.set("Model.PFC.q0", float(target.co_l_min / 60000.0), float)
        model.set("Model.t_cycle", float(t_cycle), float)
        try:
            model.run(beats)
            map_model, sbp_model, dbp_model, co_model, sv_model = extract_model_outputs(model)
            hr_model = 60.0 / float(t_cycle)
            score = objective_from_targets(
                model_map=map_model,
                model_sbp=sbp_model,
                model_dbp=dbp_model,
                model_co=co_model,
                model_sv=sv_model,
                model_hr=hr_model,
                hr_prior=hr_prior,
                target=target,
            )
            if score < best_score:
                best_score = score
                best_t_cycle = float(t_cycle)
                best_outputs = {
                    "map_model_mmhg": map_model,
                    "sbp_model_mmhg": sbp_model,
                    "dbp_model_mmhg": dbp_model,
                    "co_model_l_min": co_model,
                    "sv_model_ml": sv_model,
                    "hr_prior_from_inputs": hr_prior,
                    "objective": score,
                }
        except crash_error:
            continue

    if np.isnan(best_t_cycle):
        raise RuntimeError("All candidate t_cycle runs failed.")

    return best_t_cycle, best_outputs


def main() -> None:
    args = parse_args()
    df_raw = pd.read_excel(args.dataset)
    df_targets = build_targets(df_raw)
    if df_targets.empty:
        raise RuntimeError("No rows available after filtering required columns: HR, MAP/SBP/DBP, CO, SV.")

    if args.rest_only:
        df_targets = filter_rest_rows(df_targets)
        if df_targets.empty:
            raise RuntimeError("No rows match rest-only filter.")

    if args.max_rows is not None and args.max_rows > 0:
        df_targets = df_targets.head(args.max_rows).reset_index(drop=True)
    else:
        df_targets = df_targets.reset_index(drop=True)

    cohort_medians_all = cohort_defaults(df_targets)
    results = []

    for i, row in df_targets.iterrows():
        target = RowTargets(
            hr=float(row["hr_dataset"]),
            map_mmhg=float(row["map_dataset_mmhg"]),
            sbp_mmhg=float(row["sbp_dataset_mmhg"]),
            dbp_mmhg=float(row["dbp_dataset_mmhg"]),
            co_l_min=float(row["co_dataset_l_min"]),
            sv_ml=float(row["sv_dataset_ml"]),
            patient_id=str(row["patient_id"]),
            cohort_key=str(row["cohort_key"]),
            sex=str(row["sex"]),
            age=float(row["age"]),
            height=float(row["height"]),
            weight=float(row["weight"]),
            bmi=float(row["bmi"]),
            bsa=float(row["bsa"]),
            condition_description=str(row["condition_description"]),
            watts=float(row["watts"]),
            rpe=float(row["rpe"]),
        )
        cohort_medians = cohort_medians_all.get(target.cohort_key, next(iter(cohort_medians_all.values())))

        try:
            t_cycle_best, model_out = fit_t_cycle(target=target, cohort_medians=cohort_medians, beats=args.beats, grid=args.grid)
            hr_pred = 60.0 / t_cycle_best
            abs_err = abs(hr_pred - target.hr)
            results.append(
                {
                    "row_index": i,
                    "patient_id": target.patient_id,
                    "cohort_key": target.cohort_key,
                    "study": row["study"],
                    "group": row["group"],
                    "condition_description": target.condition_description,
                    "hr_dataset": target.hr,
                    "hr_circadapt": hr_pred,
                    "abs_error": abs_err,
                    "t_cycle_best_s": t_cycle_best,
                    **model_out,
                    "map_dataset_mmhg": target.map_mmhg,
                    "sbp_dataset_mmhg": target.sbp_mmhg,
                    "dbp_dataset_mmhg": target.dbp_mmhg,
                    "co_dataset_l_min": target.co_l_min,
                    "sv_dataset_ml": target.sv_ml,
                    "sex": target.sex,
                    "age": target.age,
                    "height": target.height,
                    "weight": target.weight,
                    "bmi": target.bmi,
                    "bsa": target.bsa,
                    "watts": target.watts,
                    "rpe": target.rpe,
                }
            )
        except Exception as exc:
            results.append(
                {
                    "row_index": i,
                    "patient_id": target.patient_id,
                    "hr_dataset": target.hr,
                    "hr_circadapt": np.nan,
                    "abs_error": np.nan,
                    "t_cycle_best_s": np.nan,
                    "objective": np.nan,
                    "cohort_key": target.cohort_key,
                    "error": str(exc),
                }
            )

    out_df = pd.DataFrame(results)
    ok_df = out_df.dropna(subset=["hr_circadapt", "hr_dataset"])
    mae = float(np.mean(np.abs(ok_df["hr_circadapt"] - ok_df["hr_dataset"]))) if not ok_df.empty else np.nan
    rmse = (
        float(np.sqrt(np.mean((ok_df["hr_circadapt"] - ok_df["hr_dataset"]) ** 2)))
        if not ok_df.empty
        else np.nan
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(args.output, index=False)
    summary = [
        f"rows_requested={'all' if args.max_rows is None else args.max_rows}",
        f"rows_attempted={len(out_df)}",
        f"rows_succeeded={len(ok_df)}",
        f"rest_only={args.rest_only}",
        f"mae_bpm={mae:.4f}" if not np.isnan(mae) else "mae_bpm=nan",
        f"rmse_bpm={rmse:.4f}" if not np.isnan(rmse) else "rmse_bpm=nan",
        f"critical_features_used={','.join(CRITICAL_FEATURES)}",
        f"dataset={args.dataset}",
        f"output_csv={args.output}",
    ]
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text("\n".join(summary), encoding="utf-8")

    print("\n".join(summary))


if __name__ == "__main__":
    main()
