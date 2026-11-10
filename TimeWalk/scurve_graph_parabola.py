#!/usr/bin/env python3
"""
Parabola-vertex SCurve analysis. Self-contained: needs only this directory.

    python3 scurve_graph_parabola.py --start_run N --num_scans 32 --runs_per_delay 2 --step_size 2

Reads the SCurve ROOT files written by scurve_launch.py / CMSITminiDAQ, finds the position of the
Threshold-vs-delay curve of each pixel geometry from the vertex of a parabola fitted around its
lowest point (see parabola_fit.py)
and writes
  - positions.yaml : {chip_N: {Geometry: {pos, err, edge}}}
                     delay units; err == 0.0 means failed curve
  - Plots_parabola/*.png

Point errors are the real scatter between the repeat runs (pooled over the delays of a curve,
divided by sqrt(number of repeats)); --noise_errors switches to mean noise / sqrt(N).
With --curves_only it only saves the averaged curves to curves/curves_<start_run>.yaml
({chip_N: {Geometry: {x, y, err}}}); --from_curves reads such a file instead of the ROOT files
(offline, no Results/ needed). With --run_map scan_runs.yaml (written by scurve_launch.py) the
runs are taken from that run -> delay list, so a failed run is just a missing point; without it
the runs are counted from --start_run.
"""
import os
import sys
import argparse
import numpy as np
import pandas as pd
import yaml
import matplotlib.pyplot as plt

import parabola_fit
import timewalk_common as tw

# ==========================================
# Configuration
# ==========================================
PLOT_DIR = "Plots_parabola"
CURVES_DIR = "curves"
CHIP_MAPPING = {0: 0, 1: 1, 2: 2, 3: 3}  # {Hardware_ID : Logical_ID}
DELAYS_TO_SKIP = []

PIXEL_TYPES = {
    "Macro_Corner": "Big Pixels (87.5 x 225 $\\mu m^2$)",
    "Long_Row": "Row Pixels (25 x 225 $\\mu m^2$)",
    "Long_Col": "Column Pixels (87.5 x 100 $\\mu m^2$)",
    "Standard": "Regular Pixels (25 x 100 $\\mu m^2$)",
}
COLORS = {"Macro_Corner": "tab:red", "Long_Row": "tab:blue",
          "Long_Col": "tab:green", "Standard": "tab:purple"}

# ==========================================
# Data extraction
# ==========================================
def run_list(start_run, num_scans, runs_per_delay, step_size, run_map=None):
    """[(run, delay, rep)]. From the launch script's run -> delay map if given (a failed run is
    then just a missing point), else by counting from start_run (only right if no run failed)."""
    if run_map:
        with open(run_map) as f:
            mapping = yaml.safe_load(f) or {}
        out, seen = [], {}
        for run in sorted(mapping):
            delay = mapping[run]
            out.append((int(run), delay, seen.get(delay, 0)))
            seen[delay] = seen.get(delay, 0) + 1
        return out
    delays = list(range(0, num_scans, step_size))
    return [(start_run + i * runs_per_delay + rep, delay, rep)
            for i, delay in enumerate(delays) for rep in range(runs_per_delay)]

def build_master_df(start_run, num_scans, runs_per_delay, step_size, run_map=None):
    geo = tw.GeometryManager(tw.YAML_GEO)
    masks = {}
    for log_id in CHIP_MAPPING.values():
        masks[log_id] = tw.parse_mask_file(tw.mask_for_chip(log_id))

    frames = []
    for run, delay, rep in run_list(start_run, num_scans, runs_per_delay, step_size, run_map):
        if delay in DELAYS_TO_SKIP:
            continue
        root_file = f"Results/Run{run:06d}_SCurve.root"
        for hw_id, log_id in CHIP_MAPPING.items():
            try:
                df = tw.extract_pixel_data(root_file, masks[log_id], geo, delay, hw_id, log_id)
            except Exception as e:
                print(f" [!] Error loading chip {hw_id} from run {run}: {e}")
                continue
            if not df.empty:
                frames.append(df.assign(Rep=rep))
    if not frames:
        return pd.DataFrame()

    # One row per pixel, delay and repeat run (repeats are kept apart to measure the real scatter)
    return pd.concat(frames, ignore_index=True)

def chip_curves(df_chip, noise_errors=False):
    """
    ({geometry: (delay, mean threshold, error)}, {geometry: info}) for one chip.

    The point is the average over pixels and repeats at each delay. Its error is the real
    scatter between the repeat runs: the pixels are averaged within each run, the variance
    between repeats is pooled over all delays of the curve (sigma_run), and
    error = sigma_run / sqrt(number of repeats at that delay).
    The formula mean noise / sqrt(pixel-runs) is used if noise_errors is set, or as a
    fallback when there is only one repeat or no scatter between repeats.
    """
    curves, info = {}, {}
    for p_type, df in df_chip.groupby("Type"):
        per_run = df.groupby(["Delay", "Rep"]).agg(
            Thr=("Threshold", "mean"), Noise=("Noise", "mean"), N=("Threshold", "count")).reset_index()
        by_delay = per_run.groupby("Delay")
        x = by_delay["Thr"].mean().index.to_numpy(float)
        y = by_delay["Thr"].mean().to_numpy(float)
        n_rep = by_delay["Thr"].count().to_numpy(float)
        noise_err = (by_delay["Noise"].mean() / np.sqrt(by_delay["N"].sum())).to_numpy(float)

        var = by_delay["Thr"].var(ddof=1).dropna()   # variance between repeats, delays with >= 2
        sigma_run = float(np.sqrt(var.mean())) if len(var) else 0.0
        use_repeats = not noise_errors and sigma_run > 0.0
        err = sigma_run / np.sqrt(n_rep) if use_repeats else noise_err
        curves[p_type] = (x, y, err)
        info[p_type] = {"mode": "repeats" if use_repeats else "noise",
                        "sigma_run": sigma_run, "err_mean": float(np.mean(err)),
                        "noise_err_mean": float(np.mean(noise_err))}
    return curves, info

def dump_curves(master, start_run, noise_errors=False):
    os.makedirs(CURVES_DIR, exist_ok=True)
    out = {}
    for chip_id in master["Chip"].unique():
        curves, _ = chip_curves(master[master["Chip"] == chip_id], noise_errors)
        out[f"chip_{chip_id}"] = {g: {"x": x.tolist(), "y": y.tolist(), "err": e.tolist()}
                                  for g, (x, y, e) in curves.items()}
    path = os.path.join(CURVES_DIR, f"curves_{start_run}.yaml")
    with open(path, "w") as f:
        yaml.dump(out, f, default_flow_style=None)
    print(f"Saved averaged curves to '{path}'.")

def load_curves(path):
    """{chip_id: {geometry: (x, y, err)}} from a curves/curves_<run>.yaml file."""
    with open(path) as f:
        raw = yaml.safe_load(f)
    return {int(k.split("_")[1]): {g: (np.array(c["x"], float), np.array(c["y"], float),
                                       np.array(c["err"], float)) for g, c in v.items()}
            for k, v in raw.items()}

# ==========================================
# Plots
# ==========================================
def draw_curve(ax, p_type, curve, res):
    x, y, yerr = curve
    ax.errorbar(x, y, yerr=yerr, color=COLORS[p_type], marker="o", linewidth=1.5,
                capsize=3, label=PIXEL_TYPES[p_type])
    if res and res["ok"]:
        xf = np.linspace(res["x_lo"], res["x_hi"], 200)
        ax.plot(xf, np.polyval(res["coef"], xf), color=COLORS[p_type], linestyle=":", alpha=0.9)
        ax.axvline(res["pos"], color=COLORS[p_type], linestyle="--", alpha=0.6)

def style(ax, title):
    ax.set_title(title)
    ax.set_xlabel("CAL_EDGE_FINE_DELAY [DAC units]")
    ax.set_ylabel("Threshold [VCAL units]")
    ax.grid(axis="y", linestyle="--", alpha=0.7)

def generate_plots(chip_id, curves, full):
    os.makedirs(PLOT_DIR, exist_ok=True)

    fig, ax = plt.subplots(figsize=(12, 8))
    for p_type in PIXEL_TYPES:
        if p_type in curves:
            draw_curve(ax, p_type, curves[p_type], full.get(p_type))
    style(ax, f"Chip {chip_id} - Threshold vs Injection Delay "
              f"(dotted = parabola over {parabola_fit.PARABOLA_POINTS} points, dashed = its vertex)")
    ax.legend(title="Pixel Geometry", loc="best")
    fig.savefig(os.path.join(PLOT_DIR, f"Chip{chip_id}_Threshold_vs_Delay_Combined.png"),
                dpi=300, bbox_inches="tight")
    plt.close(fig)

    for p_type in PIXEL_TYPES:
        if p_type not in curves:
            continue
        fig, ax = plt.subplots(figsize=(10, 6))
        res = full.get(p_type)
        draw_curve(ax, p_type, curves[p_type], res)
        if res and res["ok"]:
            style(ax, f"Chip {chip_id} - {p_type}\nposition = {res['pos']:.2f} +- {res['err']:.2f} "
                      f"(parabola over delays {res['x_lo']:g}-{res['x_hi']:g})")
        else:
            if res and res.get("edge"):
                way = "early" if res["edge"] == "left" else "late"
                style(ax, f"Chip {chip_id} - {p_type}\nno dip in the window: curve too {way} "
                          f"(lowest point at the {res['edge']} edge)")
            else:
                style(ax, f"Chip {chip_id} - {p_type}\nrejected (curve too flat or position too uncertain)")
        fig.savefig(os.path.join(PLOT_DIR, f"Chip{chip_id}_Threshold_vs_Delay_{p_type}.png"),
                    dpi=300, bbox_inches="tight")
        plt.close(fig)

# ==========================================
# Master
# ==========================================
def main():
    parser = argparse.ArgumentParser(description="Parabola-vertex SCurve timewalk analysis.")
    parser.add_argument("--start_run", type=int, help="Starting run number")
    parser.add_argument("--num_scans", type=int, default=32, help="Number of delay steps")
    parser.add_argument("--runs_per_delay", type=int, default=4, help="Runs per step")
    parser.add_argument("--step_size", type=int, default=2, help="Step size for delay injection")
    parser.add_argument("--curves_only", action="store_true",
                        help="Only save the averaged curves to curves/curves_<start_run>.yaml")
    parser.add_argument("--run_map", help="run -> delay yaml written by scurve_launch.py "
                        "(scan_runs.yaml); a failed run is then just a missing point")
    parser.add_argument("--from_curves", help="Read a curves/curves_<run>.yaml file instead of the ROOT files")
    parser.add_argument("--noise_errors", action="store_true",
                        help="Use mean noise / sqrt(N) instead of the scatter between the repeat runs")
    args = parser.parse_args()
    if not args.from_curves and args.start_run is None:
        parser.error("--start_run is required unless --from_curves is given")

    if args.from_curves:
        chip_data = {chip: (curves, {}) for chip, curves in load_curves(args.from_curves).items()}
    else:
        master = build_master_df(args.start_run, args.num_scans, args.runs_per_delay, args.step_size,
                                 args.run_map)
        if master.empty:
            print("\nERROR: No data was extracted. Please check the paths and the number of Start Runs.")
            sys.exit(1)
        if args.curves_only:
            dump_curves(master, args.start_run, args.noise_errors)
            return
        chip_data = {int(c): chip_curves(master[master["Chip"] == c], args.noise_errors)
                     for c in master["Chip"].unique()}

    all_positions = {}
    for chip_id, (curves, _) in chip_data.items():
        full = parabola_fit.positions_full(curves)
        chip_pos = parabola_fit.positions(curves)

        print(f"Chip {chip_id}:")
        for p_type, r in full.items():
            if r["ok"]:
                print(f"  {p_type:13s} pos {r['pos']:6.2f} +- {r['err']:.2f}")
            elif r.get("edge"):
                print(f"  {p_type:13s} no dip, too {'early' if r['edge'] == 'left' else 'late'}")
            else:
                print(f"  {p_type:13s} rejected (flat or too uncertain)")

        generate_plots(chip_id, curves, full)
        all_positions[f"chip_{chip_id}"] = chip_pos

    with open("positions.yaml", "w") as f:
        yaml.dump(all_positions, f, default_flow_style=False)

if __name__ == "__main__":
    tw.enter_workdir()
    main()
