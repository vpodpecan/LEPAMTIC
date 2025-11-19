########################################################################################
# Script: Filter and Harmonize Rows Based on Multiple Columns                          #
# Author: Luis Cunha (extended by ChatGPT)                                             #
# Version: v3.16                                                                       #
# Project/Task: BENCHMARKS, Task 2.3                                                   #
#                                                                                      #
# Description:                                                                         #
# This script filters and harmonizes data rows based on single-category entries,       #
# expected values, valid driver-contrast combinations, and deduplication.              #
# It includes eight harmonization steps across multiple columns.                       #
#                                                                                      #
# Output layout:                                                                       #
# - Output root: <output_stem>_outputs/                                                #
#   retained/  -> final filtered CSV(s)                                                #
#   discarded/ -> per-step discarded CSVs                                              #
#   stages/    -> per-step kept CSVs (after each step)                                 #
#   logs/      -> text and CSV logs (summary, loss breakdown)                          #
#   figures/   -> generated figures                                                    #
########################################################################################

import pandas as pd
import argparse
import os
import csv

def normalize_effect(effect):
    effect = str(effect).strip().lower()
    if "increase" in effect:
        return "increase"
    elif "decrease" in effect:
        return "decrease"
    elif "no effect" in effect:
        return "no effect"
    return None

def invert_effect(effect):
    if effect == "increase":
        return "decrease"
    elif effect == "decrease":
        return "increase"
    return effect

def load_contrast_list(filepath):
    df = pd.read_csv(filepath)
    return set(tuple(map(str.strip, row.split(";"))) for row in df.iloc[:, 0].dropna())

def harmonize_data(df, contrast_list, orientation_list):
    results = {}
    loss_records = []  # collect NA/multiplex/invalid/dedup losses
    
    stages_kept = {}   # kept df at each step
    discards = {}      # discarded per step

    def record_loss(step, column, loss_type, count):
        loss_records.append({"step": step, "column": column, "type": loss_type, "count": int(count)})

    def split_single_multi_na(df_in, col, step_name):
        na = df_in[df_in[col].isna()]
        multi = df_in[df_in[col].astype(str).str.contains(",", na=False)]
        single = df_in[~df_in.index.isin(na.index) & ~df_in.index.isin(multi.index)]
        record_loss(step_name, col, "NA", len(na))
        record_loss(step_name, col, "multiplex", len(multi))
        return single.copy(), multi.copy(), na.copy()

    # Step 1
    step = "Step1"
    kept1, multi1, na1 = split_single_multi_na(df, "land_management_practice_unified", step)
    results[step] = (len(kept1), len(multi1), len(na1))
    stages_kept[step] = kept1
    discards["step1_combined"] = multi1
    discards["step1_na"] = na1

    # Step 2
    step = "Step2"
    df2 = kept1.copy()
    df2.loc[:, "effect_normalized"] = df2["effect"].apply(normalize_effect)
    valid_effects = ["increase", "decrease", "no effect"]
    invalid2 = df2[df2["effect_normalized"].isna()]
    kept2 = df2[df2["effect_normalized"].isin(valid_effects)].copy()
    results[step] = (len(kept2), len(invalid2))
    stages_kept[step] = kept2
    discards["step2_invalid"] = invalid2
    record_loss(step, "effect", "invalid/NA", len(invalid2))

    # Step 3
    step = "Step3"
    kept3, multi3, na3 = split_single_multi_na(kept2, "property_unified", step)
    results[step] = (len(kept3), len(multi3), len(na3))
    stages_kept[step] = kept3
    discards["step3_combined"] = multi3
    discards["step3_na"] = na3

    # Step 4
    step = "Step4"
    kept4, multi4, na4 = split_single_multi_na(kept3, "actor_unified", step)
    results[step] = (len(kept4), len(multi4), len(na4))
    stages_kept[step] = kept4
    discards["step4_combined"] = multi4
    discards["step4_na"] = na4

    # Step 5
    step = "Step5"
    kept5, multi5, na5 = split_single_multi_na(kept4, "contrasting_land_management_practice_unified", step)
    results[step] = (len(kept5), len(multi5), len(na5))
    stages_kept[step] = kept5
    discards["step5_combined"] = multi5
    discards["step5_na"] = na5

    # Step 6
    step = "Step6"
    tmp = kept5.copy()
    tmp.loc[:, "pair"] = list(zip(
        tmp["land_management_practice_unified"].astype(str).str.strip(),
        tmp["contrasting_land_management_practice_unified"].astype(str).str.strip()
    ))
    kept6 = tmp[tmp["pair"].isin(contrast_list)].copy()
    removed6 = tmp[~tmp["pair"].isin(contrast_list)].copy()
    results[step] = len(kept6)
    stages_kept[step] = kept6.drop(columns=["pair"])
    discards["step6_removed"] = removed6.drop(columns=["pair"])
    record_loss(step, "(practice,contrast)", "removed (invalid pair)", len(removed6))

    # Step 7
    step = "Step7"
    def apply_swap(row):
        pair = (str(row["land_management_practice_unified"]).strip(),
                str(row["contrasting_land_management_practice_unified"]).strip())
        if pair in orientation_list:
            return row
        row = row.copy()
        row["land_management_practice_unified"], row["contrasting_land_management_practice_unified"] = \
            row["contrasting_land_management_practice_unified"], row["land_management_practice_unified"]
        row["effect_normalized"] = invert_effect(row["effect_normalized"])
        return row

    kept7 = kept6.apply(apply_swap, axis=1)
    results[step] = len(kept7)
    stages_kept[step] = kept7

    # Step 8 (dedup)
    step = "Step8"
    default_cols = [
        "land_management_practice_unified",
        "effect_normalized",
        "property_unified",
        "actor_unified",
        "contrasting_land_management_practice_unified"
    ]
    dedup_columns = (["UT (Unique ID)"] + default_cols) if "UT (Unique ID)" in kept7.columns else default_cols
    before = len(kept7)
    kept8 = kept7.drop_duplicates(subset=dedup_columns).copy()
    deduped = before - len(kept8)
    results[step] = len(kept8)
    stages_kept[step] = kept8
    record_loss(step, "+".join(dedup_columns), "deduped", deduped)

    return stages_kept, discards, results, pd.DataFrame(loss_records, columns=["step","column","type","count"])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Harmonize and filter CSV based on unified categories and valid contrasts.",
        epilog="Example: python filter_LLMs_output_v3.16.py extraction_table.csv --contrast_list list.csv "
               "--orientation_list orientation.csv -o filtered.csv",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("input_file", help="Path to the input CSV file.")
    parser.add_argument("--contrast_list", required=True, help="Path to driver_contrasts_list.csv")
    parser.add_argument("--orientation_list", required=True, help="Path to driver_contrasts_orientation.csv")
    parser.add_argument("-o", "--output", default="filtered_output_v3.15.csv", help="Filtered output CSV file name (basename ok).")

    args = parser.parse_args()

    # Ensure output filename ends with .csv (auto-fix if missing)
    if not args.output.lower().endswith(".csv"):
        args.output = args.output + ".csv"

    # Load inputs
    df = pd.read_csv(args.input_file)
    contrast_list = load_contrast_list(args.contrast_list)
    orientation_list = load_contrast_list(args.orientation_list)

    # Run pipeline
    stages_kept, discards, summary, loss_breakdown = harmonize_data(df, contrast_list, orientation_list)

    # === OUTPUT LAYOUT ===
    # Root output folder
    output_stem = os.path.splitext(os.path.basename(args.output))[0]
    out_root = f"{output_stem}_outputs"
    os.makedirs(out_root, exist_ok=True)

    # Subfolders
    retained_dir  = os.path.join(out_root, "retained")
    discarded_dir = os.path.join(out_root, "discarded")
    stages_dir    = os.path.join(out_root, "stages")
    logs_dir      = os.path.join(out_root, "logs")
    figures_dir   = os.path.join(out_root, "figures")
    for d in [retained_dir, discarded_dir, stages_dir, logs_dir, figures_dir]:
        os.makedirs(d, exist_ok=True)

    # Final CSV (retained): use Step8 kept, rename effect_normalized -> effect
    df_final = stages_kept["Step8"].copy()
    df_final["effect"] = df_final["effect_normalized"]
    if "effect_normalized" in df_final.columns:
        df_final = df_final.drop(columns=["effect_normalized"])

    final_csv_path = os.path.join(retained_dir, os.path.basename(args.output))
    df_final.to_csv(final_csv_path, index=False)
    print(f"Final filtered CSV saved to: {final_csv_path}")

    # Save per-stage kept CSVs
    for step, kept_df in stages_kept.items():
        out_path = os.path.join(stages_dir, f"{step.lower()}_kept.csv")
        kept_df.to_csv(out_path, index=False)

    # Save per-step discards
    for key, rej_df in discards.items():
        if not rej_df.empty:
            out_path = os.path.join(discarded_dir, f"{key}.csv")
            rej_df.to_csv(out_path, index=False)

    # Text summary log
    summary_lines = []
    summary_lines.append("=== Harmonization Summary ===")
    summary_lines.append("Step 1: Filter land_management_practice_unified → (single, combined, NA)")
    summary_lines.append(f"  Result: {summary['Step1']}")
    summary_lines.append("Step 2: Normalize and filter effect → (valid, invalid/NA)")
    summary_lines.append(f"  Result: {summary['Step2']}")
    summary_lines.append("Step 3: Filter property_unified → (single, combined, NA)")
    summary_lines.append(f"  Result: {summary['Step3']}")
    summary_lines.append("Step 4: Filter actor_unified → (single, combined, NA)")
    summary_lines.append(f"  Result: {summary['Step4']}")
    summary_lines.append("Step 5: Filter contrasting_land_management_practice_unified → (single, combined, NA)")
    summary_lines.append(f"  Result: {summary['Step5']}")
    summary_lines.append("Step 6: Filter valid (practice, contrast) combinations")
    summary_lines.append(f"  Result: {summary['Step6']}")
    summary_lines.append("Step 7: Swap & invert if pair not in orientation list")
    summary_lines.append(f"  Result: {summary['Step7']}")
    summary_lines.append("Step 8: Remove duplicates based on UT (Unique ID) + 5-column combo")
    summary_lines.append(f"  Result: {summary['Step8']}")
    summary_lines.append(f"Final output written to: {final_csv_path}")

    log_txt = os.path.join(logs_dir, f"{output_stem}_log.txt")
    with open(log_txt, "w", encoding="utf-8") as f:
        for line in summary_lines:
            f.write(line + "\n")
    print(f"Summary log saved to: {log_txt}")

    # CSV summary
    summary_csv_path = os.path.join(logs_dir, f"{output_stem}_summary.csv")
    with open(summary_csv_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Step", "Description", "Kept", "Removed"])
        writer.writerow(["Step1", "land_management_practice_unified", summary["Step1"][0], summary["Step1"][1] + summary["Step1"][2]])
        writer.writerow(["Step2", "effect", summary["Step2"][0], summary["Step2"][1]])
        writer.writerow(["Step3", "property_unified", summary["Step3"][0], summary["Step3"][1] + summary["Step3"][2]])
        writer.writerow(["Step4", "actor_unified", summary["Step4"][0], summary["Step4"][1] + summary["Step4"][2]])
        writer.writerow(["Step5", "contrasting_land_management_practice_unified", summary["Step5"][0], summary["Step5"][1] + summary["Step5"][2]])
        writer.writerow(["Step6", "valid driver contrasts", summary["Step6"], summary["Step5"][0] - summary["Step6"]])
        writer.writerow(["Step7", "swaps + effect inversion", summary["Step7"], 0])
        writer.writerow(["Step8", "deduplication", summary["Step8"], summary["Step7"] - summary["Step8"]])
    print(f"Summary CSV saved to: {summary_csv_path}")

    # Loss breakdown CSV (logs only)
    loss_csv_path = os.path.join(logs_dir, f"{output_stem}_loss_breakdown.csv")
    loss_breakdown_sorted = loss_breakdown.sort_values(by=["step","column","type"]).reset_index(drop=True)
    loss_breakdown_sorted.to_csv(loss_csv_path, index=False)
    print(f"Loss breakdown CSV saved to: {loss_csv_path}")

    # Figure(s)
    try:
        import matplotlib.pyplot as plt
        step_labels = ["Step1","Step2","Step3","Step4","Step5","Step6","Step7","Step8"]
        kept_values = [
            summary["Step1"][0],
            summary["Step2"][0],
            summary["Step3"][0],
            summary["Step4"][0],
            summary["Step5"][0],
            summary["Step6"],
            summary["Step7"],
            summary["Step8"]
        ]
        discarded_values = [
            summary["Step1"][1] + summary["Step1"][2],
            summary["Step2"][1],
            summary["Step3"][1] + summary["Step3"][2],
            summary["Step4"][1] + summary["Step4"][2],
            summary["Step5"][1] + summary["Step5"][2],
            summary["Step5"][0] - summary["Step6"],
            0,
            summary["Step7"] - summary["Step8"]
        ]
        x = range(len(step_labels))
        width = 0.35
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(x, kept_values, width, label='Kept')
        ax.bar(x, discarded_values, width, bottom=kept_values, label='Discarded')
        ax.set_ylabel('Rows')
        ax.set_title('Harmonization Steps: Kept vs Discarded')
        ax.set_xticks(list(x))
        ax.set_xticklabels(step_labels)
        ax.legend()
        fig.tight_layout()
        chart_file = os.path.join(figures_dir, f"{output_stem}_summary.png")
        plt.savefig(chart_file)
        print(f"Summary chart saved to: {chart_file}")
    except Exception as e:
        print(f"Warning: Failed to generate summary chart. {e}")