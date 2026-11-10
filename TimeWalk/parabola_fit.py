#!/usr/bin/env python3
"""
Parabola-vertex position of Threshold-vs-CAL_EDGE_FINE_DELAY curves. Pure numpy: no ROOT, no hardware.

A parabola is fitted (least squares) to PARABOLA_POINTS points centred on the lowest point of the
curve (moved inward when the lowest point is near an end). The position of the curve is the
vertex of that parabola. A curve that sits later (higher delay) has a larger position.

Why a wide window: the bottom of the dip is flat, so a parabola through only the few lowest points
pins its vertex down badly. With 9 points the flanks hold the vertex in place: on the saved curves
it is as precise as the flank midpoint for the big geometries and about 2x more precise for the
2-pixel Macro_Corner. The curves are lopsided (steep left flank, slow right flank), so the vertex
is pulled a little toward the slow flank; this is the same for every scan as long as the window
stays the same.

The error of the position is a Monte Carlo: every point is jiggled by its own error N_MC times,
the recipe (flat check, lowest point, window, fit) is rerun on each fake curve,
and the spread of the vertices is the error. err == 0.0 marks a failed curve.

Curves without a dip: the fit needs at least EDGE_POINTS points on each side of the lowest point.
When the lowest point is closer than that to an end of the scan, the dip is (mostly) outside the
window, so no position is given. Instead "edge" says which way the curve is off,
so the DAC search can still move it: "left" = too early (raise the DAC), "right" = too late (lower
it). A falling curve (highest point at the left end, lowest at the right end) is "right";
everything else without a dip is "left", since every target seen so far starts earlier than
Standard. (The flank method also had a "stub" rule for a lowest point a little inside the window
with one side that barely rises; with EDGE_POINTS = 3 every such case seen so far is already caught
here, so it was dropped.)

Flat curves (highest - lowest < MIN_AMPLITUDE) are rejected: no position and no edge, so the DAC
is not moved. A flat Standard makes auto_align_parabola skip the whole chip.
"""
import numpy as np

# ==========================================
# Configuration
# ==========================================
PARABOLA_POINTS = 9        # points in the fit window, centred on the lowest point
MIN_AMPLITUDE = 2.0        # [VCAL]; highest - lowest below this: curve is flat, rejected
MAX_POS_ERR = 3.0          # [delay units]; a position known only to +-3 is rejected
EDGE_POINTS = 3            # points needed on each side of the lowest point; fewer: "no dip"
N_MC = 200                 # fake measurements per curve for the error bar
MC_MAX_FAIL = 0.2          # more than this fraction of fake curves failing: curve is unstable

# ==========================================
# Checks on one curve
# ==========================================
def _flat(y):
    """True if highest - lowest is below MIN_AMPLITUDE: no usable curve."""
    return np.max(y) - np.min(y) < MIN_AMPLITUDE

def _edge(y):
    """None if the dip is inside the window; else "left" (too early, raise the DAC) or "right"
    (too late, lower the DAC). y is sorted by delay and not flat."""
    n = len(y)
    imin, imax = int(np.argmin(y)), int(np.argmax(y))
    if EDGE_POINTS <= imin < n - EDGE_POINTS:
        return None
    return "right" if (imax < EDGE_POINTS and imin >= n - EDGE_POINTS) else "left"

# ==========================================
# Position of one curve
# ==========================================
def _vertex(x, y):
    """(vertex, (a, b, c), x_lo, x_hi) of the parabola through the window around the lowest
    point, or None if it opens downward or its vertex falls outside the window."""
    k = min(PARABOLA_POINTS, len(y))
    lo = max(0, min(int(np.argmin(y)) - k // 2, len(y) - k))
    xs, ys = x[lo:lo + k], y[lo:lo + k]
    a, b, c = np.polyfit(xs, ys, 2)
    if a <= 0:
        return None
    v = -b / (2 * a)
    if not xs[0] <= v <= xs[-1]:
        return None
    return v, (a, b, c), xs[0], xs[-1]

def curve_position(x, y, yerr):
    """
    Position of one curve: vertex of the parabola around its lowest point.

    Returns {"pos", "err", "ok", "edge", "coef", "x_lo", "x_hi"}. The error is the spread of the
    vertex over N_MC fake curves (each point jiggled by its own error).
    ok=False (and err = 0.0 in positions()) means a flat curve, no dip, a failed fit, an error
    above MAX_POS_ERR, or more than MC_MAX_FAIL of the fake curves failing (a fake fails if it is
    flat or its fit fails; the edge rule only decides whether the real curve has a dip). "edge" is None for a curve with a dip and "left" / "right"
    for a curve whose dip is outside the window (see the module docstring).
    """
    order = np.argsort(x)
    x = np.asarray(x, float)[order]
    y = np.asarray(y, float)[order]
    yerr = np.asarray(yerr, float)[order]
    yerr = np.where(yerr <= 0, 1e-3, yerr)

    bad = {"pos": 0.0, "err": 0.0, "ok": False, "edge": None,
           "coef": [0.0, 0.0, 0.0], "x_lo": 0.0, "x_hi": 0.0}
    if len(x) < 5 or _flat(y):
        return bad
    edge = _edge(y)
    if edge:
        return {**bad, "edge": edge}
    base = _vertex(x, y)
    if base is None:
        return bad
    pos, coef, x_lo, x_hi = base

    # Monte Carlo: jiggle every point by its own error, rerun the whole recipe, take the spread
    rng = np.random.default_rng(0)                   # fixed seed: same data, same error bar
    vertices = []
    for _ in range(N_MC):
        fy = y + rng.normal(0.0, yerr)
        if _flat(fy):                                # the edge rule is for the real curve only:
            continue                                 # a fake whose minimum moves 1 point still fits
        fake = _vertex(x, fy)
        if fake is not None:
            vertices.append(fake[0])
    failed = 1.0 - len(vertices) / N_MC
    if len(vertices) < 2:
        return bad
    err = float(np.std(vertices, ddof=1))
    ok = bool(np.isfinite(err) and 0.0 < err <= MAX_POS_ERR and failed <= MC_MAX_FAIL)
    return {"pos": float(pos), "err": err, "ok": ok, "edge": None,
            "coef": [float(c) for c in coef], "x_lo": float(x_lo), "x_hi": float(x_hi)}

# ==========================================
# All curves of one chip
# ==========================================
def positions(curves):
    """
    curves: {geometry: (x, y, yerr)} for ONE chip.
    Returns {geometry: {"pos", "err", "edge"}}; err == 0.0 marks a failed curve. "edge"
    ("left" / "right" / None) tells a consumer which way a curve without a dip is off.
    """
    out = {}
    for g, r in positions_full(curves).items():
        out[g] = {"pos": r["pos"] if r["ok"] else 0.0, "err": r["err"] if r["ok"] else 0.0,
                  "edge": r["edge"]}
    return out

def positions_full(curves):
    return {g: curve_position(*c) for g, c in curves.items()}
