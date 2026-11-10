#!/usr/bin/env python3
"""
Parabola-vertex preamp alignment. Self-contained: needs only this directory.

    python3 auto_align_parabola.py          (from anywhere; it works inside this directory)

Secant search on the DAC_PREAMP_*_LIN registers (mapping from sensor_geometry.yaml) so that the
position of each geometry's Threshold-vs-delay curve matches the reference (smallest-area)
geometry: the next DAC is where the line through the last two (DAC, shift) points crosses zero,
with no search bounds (only a cap per step and the register limits). The position is the vertex of a parabola fitted around the lowest point (see parabola_fit.py). Each scan
is run by scurve_launch.py and analysed by scurve_graph_parabola.py, which writes positions.yaml.
A larger position means the curve sits later (higher delay).
"""
import os
import sys
import glob
import math
import subprocess
import yaml
from datetime import datetime

import timewalk_common as tw
import parabola_fit
from timewalk_common import (XML_CONFIG, Z_THRESHOLD, REQUIRE_Z_TEST, MAX_ABS_SHIFT,
                             MAX_ITERATIONS, DRIFT_SIGMA, DAC_HARD_MIN, DAC_HARD_MAX,
                             DEFAULT_SLOPE, MIN_SLOPE, MAX_DAC_STEP, NO_DIP_STEP, TARGET_CHIPS,
                             NUM_SCANS, RUNS_PER_DELAY, DELAY_STEP_SIZE, PIXEL_AREAS)

# ==========================================
# Configuration (the scan and convergence settings are in timewalk_common.py)
# ==========================================
LAUNCH_SCRIPT = os.path.join(tw.HERE, "scurve_launch.py")
GRAPH_SCRIPT = os.path.join(tw.HERE, "scurve_graph_parabola.py")
RUN_MAP_FILE = "scan_runs.yaml"   # run -> delay list written by scurve_launch.py
PLOT_DIR = "Plots_parabola"

# ==========================================
# Helpers
# ==========================================
def fit_ok(entry):
    return entry["err"] > 0.0

def compare(entry, ref):
    """Shift (target - reference) in delay units and its Z-score."""
    shift = entry["pos"] - ref["pos"]
    denom = math.hypot(entry["err"], ref["err"])
    return shift, (abs(shift) / denom if denom > 0 else float("inf"))

def is_aligned(shift, z):
    """Within MAX_ABS_SHIFT of the reference (and Z <= Z_THRESHOLD only if REQUIRE_Z_TEST)."""
    return abs(shift) <= MAX_ABS_SHIFT and (z <= Z_THRESHOLD or not REQUIRE_Z_TEST)

def within_noise(shift, err):
    """Just past MAX_ABS_SHIFT, but by no more than DRIFT_SIGMA error bars: noise, not drift."""
    return abs(shift) - MAX_ABS_SHIFT <= DRIFT_SIGMA * err

def record(state, entry, ref):
    """Store what the latest scan says about one geometry (shift, aligned or not, note).
    A geometry has to get within MAX_ABS_SHIFT to become aligned, but once aligned it stays
    aligned while it is past the limit by no more than DRIFT_SIGMA error bars (noise).
    Returns (shift, z), or None if the curve has no usable dip."""
    if not fit_ok(entry):
        state.update(last_shift=None, last_err=None, aligned=False,
                     note="no dip" if entry.get("edge") else "curve flat or too uncertain")
        return None
    shift, z = compare(entry, ref)
    err = math.hypot(entry["err"], ref["err"])
    aligned = is_aligned(shift, z) or (state["aligned"] and within_noise(shift, err))
    state.update(last_shift=shift, last_err=err, last_z=z,
                 aligned=aligned, note=f"last shift {shift:+.2f} delay units")
    return shift, z

def add_point(state, shift, z):
    """Store (DAC, shift) from a scan, remember the best DAC seen, converge if aligned."""
    state["history"].append((state["current"], shift))
    state["direction"] = None
    if state["best"] is None or abs(shift) < abs(state["best"][1]):
        state["best"] = (state["current"], shift)
    if is_aligned(shift, z):
        state["converged"] = True

def update_no_dip(state, edge):
    """No dip in the scan window, so no shift. "left": the curve is too early, so raise the DAC
    (+1); "right": too late, so lower it (-1)."""
    state["direction"] = -1 if edge == "right" else 1

def reopen(state):
    """A geometry that was aligned has clearly drifted out, or one whose search was abandoned
    after a rejected curve gives a usable reading again: search again from its current DAC.
    The earlier points are kept, so the search knows the slope right away (a drift moves the
    readings together, the slope stays). Only the old reading at the current DAC is dropped:
    the caller stores the new one."""
    state.update(converged=False, stuck="", direction=None, abandoned=False,
                 history=[p for p in state["history"] if p[0] != state["current"]])

def zero_of_line(history):
    """(slope, DAC, shift) of the line to follow: a point of the line and its slope. A higher
    preamp DAC moves the curve later, so the slope is positive. Points on both sides of zero
    (a bracket) use the nearest one on each side, so the zero lies between them; otherwise the
    last two points with different DACs. A missing, flat or negative slope (noise) becomes
    DEFAULT_SLOPE through the latest point."""
    below = [p for p in history if p[1] < 0]
    above = [p for p in history if p[1] > 0]
    pts = []
    if below and above:
        pts = [max(below, key=lambda p: p[1]), min(above, key=lambda p: p[1])]
        if pts[0][0] == pts[1][0]:                     # same DAC on both sides: no slope from them
            pts = []
    if not pts:
        pts = []
        for p in reversed(history):
            if all(p[0] != q[0] for q in pts):
                pts.append(p)
            if len(pts) == 2:
                break
    if len(pts) == 2:
        (d1, s1), (d2, s2) = pts
        slope = (s2 - s1) / (d2 - d1)
        if slope >= MIN_SLOPE:
            return slope, d1, s1
    return DEFAULT_SLOPE, history[-1][0], history[-1][1]

def next_dac(state):
    """(new DAC, how it was chosen), or (None, why) if the DAC cannot move any further. The step
    is capped at MAX_DAC_STEP; only the register limits bound the DAC."""
    current = state["current"]
    if state["direction"] is not None:                     # no dip: no shift to go on
        step, how, sign = state["direction"] * NO_DIP_STEP, "no dip", state["direction"]
    else:
        slope, dac0, shift0 = zero_of_line(state["history"])
        step = dac0 - shift0 / slope - current
        sign = -1 if state["history"][-1][1] > 0 else 1    # shift > 0 (too late) needs a lower DAC
        how = f"slope {slope:.4f}"
    step = max(-MAX_DAC_STEP, min(MAX_DAC_STEP, step))
    step = int(round(step)) or sign                         # always move at least one DAC step
    new = max(DAC_HARD_MIN, min(DAC_HARD_MAX, current + step))
    if new == current:
        return None, f"already at the DAC limit {current}"
    return new, how

def geometry_line(p_type, entry, st, note):
    """One log line: position, shift to the reference, DAC, OK, note."""
    if fit_ok(entry):
        txt = f"pos {entry['pos']:6.2f} +- {entry['err']:.2f}"
        if st and st["last_shift"] is not None:
            txt += f"   shift {st['last_shift']:+.2f} +- {st['last_err']:.2f}"
            if REQUIRE_Z_TEST:
                txt += f" (Z {st['last_z']:.1f})"
    elif entry.get("edge"):
        txt = f"no dip, too {'early' if entry['edge'] == 'left' else 'late'}"
    else:
        txt = "rejected (flat or too uncertain)"
    line = f"{p_type:13s} {txt:<42}"
    if st:
        line += f"DAC {st['current']:>4}" + ("   OK" if st["aligned"] else "")
    return (line + (f"   {note}" if note else "")).rstrip()

def report(positions_all, search_state, reference_map, notes):
    """Per chip: the reference position, then one line per target geometry."""
    for chip_id in TARGET_CHIPS:
        positions = positions_all.get(f"chip_{chip_id}")
        if not positions or chip_id not in reference_map:
            print(f"  Chip {chip_id}: no data")
            continue
        ref_type = reference_map[chip_id]
        ref = positions[ref_type]
        ref_txt = f"{ref['pos']:.2f} +- {ref['err']:.2f}" if fit_ok(ref) else "no usable dip"
        print(f"  Chip {chip_id}: {ref_type} {ref_txt}")
        for p_type, entry in positions.items():
            if p_type != ref_type:
                st = search_state.get(chip_id, {}).get(p_type)
                print("    " + geometry_line(p_type, entry, st, notes.get((chip_id, p_type), "")))

def run_quiet(cmd):
    """Run a script; log only its warnings, or all of its output if it fails."""
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in proc.stdout.splitlines():
        if proc.returncode or "[!]" in line or "ERROR" in line:
            print(line)
    if proc.returncode:
        raise subprocess.CalledProcessError(proc.returncode, cmd)

def evaluate_positions(label, is_initial=False):
    if os.path.exists(RUN_MAP_FILE):
        os.remove(RUN_MAP_FILE)                     # never read a stale list from an earlier scan
    subprocess.run([sys.executable, LAUNCH_SCRIPT, "--xml_filename", XML_CONFIG,
                    "--num_scans", str(NUM_SCANS), "--runs_per_delay", str(RUNS_PER_DELAY),
                    "--step_size", str(DELAY_STEP_SIZE)], check=True)

    # scurve_launch.py writes which run belongs to which delay, so a failed run is just a
    # missing point; only a scan with no runs at all stops the alignment.
    with open(RUN_MAP_FILE) as f:
        run_map = yaml.safe_load(f) or {}
    if not run_map:
        raise RuntimeError("[!] scurve_launch.py finished, but no run produced a ROOT file")
    start_run = min(run_map)
    delays = list(range(0, NUM_SCANS, DELAY_STEP_SIZE))
    print(f"\n{label}: runs {start_run}-{max(run_map)} ({len(delays)} delays x {RUNS_PER_DELAY} repeats)")
    expected = len(delays) * RUNS_PER_DELAY
    if len(run_map) < expected:
        counts = {d: list(run_map.values()).count(d) for d in delays}
        missing = ", ".join(f"delay {d} ({RUNS_PER_DELAY - n} of {RUNS_PER_DELAY})"
                            for d, n in counts.items() if n < RUNS_PER_DELAY)
        print(f"  [!] {len(run_map)} of {expected} runs, missing: {missing}; those points are skipped")

    run_quiet([sys.executable, "-u", GRAPH_SCRIPT, "--start_run", str(start_run),
                "--run_map", RUN_MAP_FILE,
                "--num_scans", str(NUM_SCANS), "--runs_per_delay", str(RUNS_PER_DELAY),
                "--step_size", str(DELAY_STEP_SIZE)])

    if is_initial and os.path.exists(PLOT_DIR):  # keep first-pass plots from being overwritten
        for path in glob.glob(f"{PLOT_DIR}/*.png"):
            base, ext = os.path.splitext(path)
            if not base.endswith("_initial"):
                os.rename(path, f"{base}_initial{ext}")

    with open("positions.yaml") as f:
        return yaml.safe_load(f)

# ==========================================
# Main
# ==========================================
def main():
    tw.configure_target_chips(XML_CONFIG, TARGET_CHIPS)
    positions_all = evaluate_positions("Scan 1 (baseline)", is_initial=True)

    search_state, reference_map, skipped, notes = {}, {}, [], {}
    for chip_id in TARGET_CHIPS:
        positions = positions_all.get(f"chip_{chip_id}")
        if not positions:
            skipped.append((chip_id, "all geometries", "no data"))
            continue
        dac_map = tw.get_dac_mappings(chip_id)
        ref_type = min(positions, key=lambda k: PIXEL_AREAS.get(k, float("inf")))
        reference_map[chip_id] = ref_type
        ref = positions[ref_type]
        if not fit_ok(ref):
            skipped.append((chip_id, "all geometries", f"reference {ref_type} has no usable dip"))
            continue

        search_state[chip_id] = {}
        for p_type in (p for p in positions if p != ref_type and p in dac_map):
            entry = positions[p_type]
            if not fit_ok(entry) and not entry.get("edge"):
                skipped.append((chip_id, p_type, "curve flat or too uncertain, DAC not touched"))
                notes[(chip_id, p_type)] = "skipped"
                continue
            reg = dac_map[p_type]
            state = {"reg": reg, "current": tw.get_xml_register(XML_CONFIG, reg, chip_id),
                     "history": [], "best": None, "direction": None, "converged": False,
                     "aligned": False, "note": "", "stuck": "", "last_shift": None, "last_err": None}
            result = record(state, entry, ref)
            if result:
                add_point(state, *result)
            else:
                update_no_dip(state, entry["edge"])
            search_state[chip_id][p_type] = state
    report(positions_all, search_state, reference_map, notes)

    if not search_state:
        print("\nNo targets to align. Exiting.")
        return

    for iteration in range(1, MAX_ITERATIONS + 1):
        multi_updates, moves = {}, []
        for chip_id, targets in search_state.items():
            for p_type, state in targets.items():
                if state["converged"]:
                    continue
                new_dac, how = next_dac(state)
                if new_dac is None:
                    moves.append(f"  Chip {chip_id} {p_type:13s} {how}, search stopped")
                    state["converged"] = True
                    state["stuck"] = ("no dip even at the DAC limit" if state["direction"] is not None
                                      else "DAC limit reached")
                    continue
                moves.append(f"  Chip {chip_id} {p_type:13s} {state['reg']} {state['current']} -> {new_dac}"
                             + (" (no dip)" if how == "no dip" else ""))
                state["current"] = new_dac
                multi_updates.setdefault(chip_id, {})[state["reg"]] = new_dac

        if moves:
            print("\nNext DACs:\n" + "\n".join(moves))
        if not multi_updates:
            print("\nNo more DAC changes are possible or needed.")
            break

        tw.update_xml_registers(XML_CONFIG, multi_updates)
        positions_all = evaluate_positions(f"Scan {iteration + 1}")
        # Look at EVERY geometry of every chip: one that was aligned before can drift out while
        # its DAC stays the same, and only the last scan tells the truth about the final DACs.
        notes = {}
        for chip_id, targets in search_state.items():
            positions = positions_all.get(f"chip_{chip_id}")
            if not positions:
                continue
            ref = positions[reference_map[chip_id]]
            if not fit_ok(ref):
                for p_type, state in targets.items():
                    state.update(converged=True, aligned=False, stuck="reference lost its dip")
                    notes[(chip_id, p_type)] = "reference lost its dip, DAC kept"
                continue
            for p_type, state in targets.items():
                entry = positions[p_type]
                changed = state["reg"] in multi_updates.get(chip_id, {})
                was_aligned = state["aligned"]
                result = record(state, entry, ref)
                if changed:
                    if result:
                        add_point(state, *result)
                    elif entry.get("edge"):
                        update_no_dip(state, entry["edge"])
                    else:
                        notes[(chip_id, p_type)] = "search abandoned"
                        state.update(converged=True, abandoned=True,
                                     stuck="curve flat or too uncertain, search abandoned")
                elif state.get("abandoned") and (result or entry.get("edge")):
                    # One rejected scan is not proof the curve is dead: if a later scan at the same
                    # DAC shows a dip or an edge direction, carry on with the search.
                    notes[(chip_id, p_type)] = "rejected before, search re-opened"
                    reopen(state)
                    if result:
                        add_point(state, *result)
                    else:
                        update_no_dip(state, entry["edge"])
                elif was_aligned and not state["aligned"] and (result or entry.get("edge")):
                    notes[(chip_id, p_type)] = "drifted out, search re-opened"
                    reopen(state)
                    if result:
                        add_point(state, *result)
                    else:
                        update_no_dip(state, entry["edge"])
                elif result and state["aligned"] and abs(result[0]) > MAX_ABS_SHIFT:
                    notes[(chip_id, p_type)] = f"just past {MAX_ABS_SHIFT:g}, within noise"
        report(positions_all, search_state, reference_map, notes)

    def reason(st):
        shift = st["last_shift"]
        if shift is None:
            why = "no dip in the scan window" if st["note"] == "no dip" else st["note"] or "no usable dip"
        elif abs(shift) > MAX_ABS_SHIFT:
            why = f"shift {shift:+.2f} is outside +-{MAX_ABS_SHIFT}"
        else:
            why = f"shift {shift:+.2f} is inside the limit but the Z-score is above {Z_THRESHOLD}"
        best = f"; best seen: DAC {st['best'][0]}, shift {st['best'][1]:+.2f}" if st["best"] else ""
        return (f"{st['stuck']} ({why}{best})" if st["stuck"]
                else f"{why} (iteration limit {MAX_ITERATIONS} reached{best})")

    print("\nFinal (last scan):")
    print(f"  {'chip':<5}{'geometry':<14}{'register':<20}{'DAC':>5}   {'shift (+- err)':<18}status")
    for chip_id, targets in search_state.items():
        for p_type, st in targets.items():
            shift_txt = (f"{st['last_shift']:+.2f} +- {st['last_err']:.2f}"
                         if st["last_shift"] is not None else "no dip")
            print(f"  {chip_id:<5}{p_type:<14}{st['reg']:<20}{st['current']:>5}   {shift_txt:<18}"
                  f"{'OK' if st['aligned'] else 'NOT ALIGNED'}")

    not_aligned = [(c, p, reason(st)) for c, t in search_state.items()
                   for p, st in t.items() if not st["aligned"]] + skipped
    if not not_aligned:
        print("\nSUCCESS: all geometries aligned.")
    else:
        print(f"\nNOT ALIGNED ({len(not_aligned)}):")
        for chip_id, p_type, why in not_aligned:
            print(f"  Chip {chip_id} {p_type}: {why}")

if __name__ == "__main__":
    tw.enter_workdir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"auto_align_parabola_{timestamp}.log"
    sys.stdout = tw.Logger(log_filename)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Parabola alignment, log {log_filename}")
    print(f"Parabola over {parabola_fit.PARABOLA_POINTS} points, aligned if |shift| <= {MAX_ABS_SHIFT}"
          f"{f' and Z <= {Z_THRESHOLD}' if REQUIRE_Z_TEST else ''}, max {MAX_ITERATIONS} iterations")
    t0 = datetime.now()
    try:
        main()
    finally:  # also logged if the run stops early (error or Ctrl+C)
        elapsed = str(datetime.now() - t0).split(".")[0]
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Done in {elapsed}")
