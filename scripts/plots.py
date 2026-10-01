#!/usr/bin/env python3
"""Figures for the README. Palette: dataviz reference instance (slots 1-3 are
documented all-pairs validated; the blue ordinal ramp respects the light-surface
2:1 floor by starting at step 250)."""
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from acmetrics import load_ac, phase_deg, cross_freq
from oscmetrics import rising_crossings

W, DOC = "results/work", "docs"
SURF, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#d8d7d2"
S1, S2, S3 = "#2a78d6", "#eb6834", "#1baf7a"            # categorical slots 1-3
ORD4 = ["#86b6ef", "#3987e5", "#256abf", "#104281"]      # ordinal blue ramp

plt.rcParams.update({
    "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
    "text.color": INK, "axes.labelcolor": INK, "axes.edgecolor": GRID,
    "xtick.color": INK2, "ytick.color": INK2, "font.size": 9,
    "axes.titlesize": 10, "axes.titleweight": "bold", "lines.linewidth": 1.8,
    "grid.color": GRID, "grid.linewidth": 0.6, "legend.frameon": False,
})


def style(ax):
    ax.grid(True, which="major", alpha=0.9)
    ax.grid(True, which="minor", alpha=0.35)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def ac_data():
    man = json.load(open(f"{W}/ac_manifest.json"))
    f, outs = load_ac(f"{W}/ac_out_tt.dat")
    _, nxs = load_ac(f"{W}/ac_nx_tt.dat")
    d = {}
    for m in man:
        H = outs[m["i"]]
        ph = phase_deg(H)
        d[m["name"]] = {"H": H, "ph": ph, "X": nxs[m["i"]],
                        "f180": cross_freq(f, ph, -180.0)}
    return f, d


# ---- fig 1: Bode of the cell and its two paths -----------------------------
def fig_bode():
    f, d = ac_data()
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(7.6, 6.0), sharex=True,
                                 gridspec_kw={"hspace": 0.16})
    series = [("full cell (buffer \u2225 inverter)", "full", S1),
              ("buffer path alone", "buffer", S2),
              ("direct inverter alone", "invonly", S3)]
    lo, hi = 1e8, 1e11
    for lab, key, c in series:
        if key not in d:
            continue
        a1.semilogx(f, 20 * np.log10(np.abs(d[key]["H"])), color=c, label=lab)
        a2.semilogx(f, d[key]["ph"], color=c, label=lab)

    # mark where each path hits -180 deg, and how much gain is left there
    for lab, key, c in series:
        fx = d.get(key, {}).get("f180")
        if not fx:
            continue
        mag = 20 * np.log10(np.abs(d[key]["H"]))
        g = np.interp(np.log10(fx), np.log10(f), mag)
        a1.plot([fx], [g], "o", ms=8, color=c, mec=SURF, mew=1.4, zorder=5)
        a2.plot([fx], [-180], "o", ms=8, color=c, mec=SURF, mew=1.4, zorder=5)
        for ax in (a1, a2):
            ax.axvline(fx, color=c, lw=0.8, ls="--", alpha=0.55, zorder=1)
        right = fx > 1e10
        a1.annotate(f"{g:+.1f} dB at {fx/1e9:.1f} GHz",
                    xy=(fx, g), xytext=(-8 if right else 8, 11 if g > 0 else -20),
                    textcoords="offset points", color=INK, fontsize=8.5,
                    fontweight="bold", ha="right" if right else "left")
    a1.axhline(0, color=INK2, lw=0.9, ls=":")
    a1.annotate("unity gain", xy=(lo * 1.15, 0), xytext=(0, 4),
                textcoords="offset points", color=INK2, fontsize=8)
    a1.set_ylabel("magnitude  (dB)")
    a1.set_xlim(lo, hi)
    a1.set_ylim(-28, 44)
    a1.set_title("Why the parallel inverter helps: 180\u00b0 of lag while gain is still above 1",
                 loc="left")
    a1.legend(loc="lower left", fontsize=8.5)

    a2.axhline(-180, color=INK2, lw=0.9, ls=":")
    a2.annotate("\u2212180\u00b0", xy=(lo * 1.15, -180), xytext=(0, 5),
                textcoords="offset points", color=INK2, fontsize=8)
    a2.set_ylabel("phase  (degrees)")
    a2.set_xlabel("frequency  (Hz)")
    a2.set_yticks([0, -90, -180, -270, -360])
    a2.set_ylim(-375, 18)
    for a in (a1, a2):
        style(a)
    fig.savefig(f"{DOC}/fig1_bode.png", dpi=170, bbox_inches="tight")
    plt.close(fig)
    print("fig1_bode.png")


# ---- fig 2: knob sweeps, f180 vs each knob --------------------------------
def fig_knobs():
    f, d = ac_data()
    groups = [("sz2", "buffer 2nd stage size  (units)", "sz2=", float, True),
              ("sz3", "direct inverter size  (units)", "sz3=", float, False),
              ("sz1", "buffer 1st stage size  (units)", "sz1=", float, False),
              ("cx", "added cap at node X  (fF)", "cx=", lambda s: float(s.rstrip("f")), False),
              ("cff", "feedforward cap across 2nd stage  (fF)", "cff=", lambda s: float(s.rstrip("f")), False),
              ("rlo", "load resistance at OUT  (Ω)", "rlo=", None, False)]
    fig, axes = plt.subplots(2, 3, figsize=(10.6, 5.6))
    for ax, (key, xlab, pre, conv, _) in zip(axes.ravel(), groups):
        pts = []
        for name, v in d.items():
            if not name.startswith(pre) or v["f180"] is None:
                continue
            raw = name[len(pre):]
            if conv is None:
                mult = {"T": 1e12, "G": 1e9, "k": 1e3}.get(raw[-1], 1)
                x = float(raw[:-1]) * mult if mult != 1 else float(raw)
            else:
                x = conv(raw)
            pts.append((x, v["f180"] / 1e9))
        pts.sort()
        if not pts:
            ax.axis("off"); continue
        xs, ys = zip(*pts)
        ax.plot(xs, ys, color=S1, marker="o", ms=5, mew=0)
        if key == "rlo":
            ax.set_xscale("log")
        ax.set_xlabel(xlab, fontsize=8)
        ax.set_ylabel("180° crossing  (GHz)", fontsize=8)
        style(ax)
    fig.suptitle("One knob at a time: what moves the 180° crossing",
                 x=0.012, ha="left", fontweight="bold", fontsize=10)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(f"{DOC}/fig2_knobs.png", dpi=170, bbox_inches="tight")
    plt.close(fig)
    print("fig2_knobs.png")


# ---- fig 3: quadrature waveforms ------------------------------------------
def fig_osc(picks):
    man = json.load(open(f"{W}/osc_manifest.json"))
    dv = np.loadtxt(f"{W}/osc_v_tt.dat")
    t = dv[:, 0]
    fig, axes = plt.subplots(len(picks), 1, figsize=(8.0, 2.9 * len(picks)))
    axes = np.atleast_1d(axes)
    for ax, (title, idx) in zip(axes, picks):
        m = man[idx]
        sig = [dv[:, 1 + 2 * (4 * idx + j)] for j in range(4)]
        xs = rising_crossings(t, sig[0], 0.9)
        if len(xs) > 4:
            T = float(np.median(np.diff(xs)))
            t0 = xs[-4]
            win = (t >= t0) & (t <= t0 + 3 * T)
        else:
            win = t >= t[-1] * 0.9
        # label the actual taps, not an assumed phase order
        names = ["q1", "q2", "q3", "q4"] if m["kind"] == "ring8" else \
                ["a  (cell 1 out)", "x1  (cell 1 internal)",
                 "b  (cell 2 out)", "x2  (cell 2 internal)"]
        for j, s in enumerate(sig):
            ax.plot((t[win] - t[win][0]) * 1e12, s[win], color=ORD4[j], label=names[j])
        ax.set_title(title, loc="left", pad=24)
        ax.set_ylabel("volts")
        ax.set_xlabel("time  (ps)", fontsize=8)
        ax.set_ylim(-0.12, 2.18)
        ax.legend(fontsize=8, ncol=4, loc="lower left", bbox_to_anchor=(0, 1.0),
                  borderaxespad=0, columnspacing=1.3, handlelength=1.5)
        style(ax)
    fig.tight_layout()
    fig.savefig(f"{DOC}/fig3_osc.png", dpi=170, bbox_inches="tight")
    plt.close(fig)
    print("fig3_osc.png")


# ---- fig 4: frequency vs power across the whole sweep ---------------------
def fig_fp(rows, base=None, head=None):
    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    for kind, c, lab in (("ring8", S2, "8-inverter ring (cross-coupling size swept)"),
                         ("ring6", S1, "6-inverter feedforward ring (size ratio swept)")):
        pts = [(float(r["power_mW"]), float(r["f_GHz"])) for r in rows
               if r["kind"] == kind and r["osc"] == "OSC"]
        if pts:
            xs, ys = zip(*pts)
            ax.scatter(xs, ys, s=56, color=c, label=lab, zorder=3,
                       edgecolors=SURF, linewidths=1.2)
    # call out the two designs in the headline table
    for idx, c, lab, dx, dy, ha in ((base, S2, "baseline\n(one size fits all)", -16, -34, "right"),
                                    (head, S1, "proposed\n(headline)", 16, 14, "left")):
        if idx is None:
            continue
        r = rows[idx]
        x, y = float(r["power_mW"]), float(r["f_GHz"])
        ax.scatter([x], [y], s=190, facecolors="none", edgecolors=c,
                   linewidths=1.8, zorder=4)
        ax.annotate(lab, xy=(x, y), xytext=(dx, dy), textcoords="offset points",
                    fontsize=8.5, color=INK, fontweight="bold", ha=ha,
                    arrowprops=dict(arrowstyle="->", color=c, lw=1.1))
    ax.set_xlabel("power  (mW)")
    ax.set_ylabel("oscillation frequency  (GHz)")
    ax.set_title("Frequency vs power across every oscillating variant", loc="left")
    ax.legend(fontsize=8, loc="lower right")
    style(ax)
    fig.savefig(f"{DOC}/fig4_freq_power.png", dpi=170, bbox_inches="tight")
    plt.close(fig)
    print("fig4_freq_power.png")


def pick(rows):
    """Same headline rule as make_readme.py: best efficiency among the
    6-inverter rings whose phase spread is usable."""
    base = next(i for i, r in enumerate(rows) if r["variant"].startswith("ring8 baseline"))
    r6 = [(i, r) for i, r in enumerate(rows) if r["kind"] == "ring6" and r["osc"] == "OSC"]
    if not r6:
        return base, None, None
    usable = [x for x in r6 if float(x[1]["quad_err_deg"]) <= 25] or r6
    headline = max(usable, key=lambda x: float(x[1]["fom_GHz_per_mW"]))[0]
    fast = max(r6, key=lambda x: float(x[1]["f_GHz"]))[0]
    return base, headline, fast


if __name__ == "__main__":
    os.makedirs(DOC, exist_ok=True)
    if os.path.exists(f"{W}/ac_out_tt.dat"):
        fig_bode(); fig_knobs()
    if os.path.exists(f"{W}/osc_v_tt.dat"):
        import sys
        sys.path.insert(0, "scripts")
        from analyze import osc_table
        rows = osc_table("tt")
        base, bestq, fast = pick(rows)
        picks = [(f"Baseline: 8 inverters, one size \u2014 {rows[base]['f_GHz']} GHz, "
                  f"taps {rows[base]['gaps_deg']}\u00b0 apart", base)]
        if bestq is not None:
            r = rows[bestq]
            pp = dict(kv.split("=") for kv in r["params"].split())
            picks.append((f"Proposed: 6 inverters, feedforward cell "
                          f"({pp['SZ1']}u/{pp['SZ2']}u/{pp['SZ3']}u) \u2014 "
                          f"{r['f_GHz']} GHz, taps {r['gaps_deg']}\u00b0 apart", bestq))
        fig_osc(picks)
        fig_fp(rows, base, bestq)
