#!/usr/bin/env python3
"""Reduce the raw ngspice sweeps to result tables (CSV) under results/."""
import csv, json, os
import numpy as np
from acmetrics import load_ac, phase_deg, cross_freq, notch_freq
from oscmetrics import rising_crossings

W = "results/work"


def ghz(x):
    return "" if x is None else f"{x/1e9:.3f}"


# ---------------------------------------------------------------- AC variants
def ac_table(corner="tt"):
    man = json.load(open(f"{W}/ac_manifest.json"))
    f, outs = load_ac(f"{W}/ac_out_{corner}.dat")
    _, nxs = load_ac(f"{W}/ac_nx_{corner}.dat")
    rows = []
    for m in man:
        H, X = outs[m["i"]], nxs[m["i"]]
        ph = phase_deg(H)
        fn, mn = notch_freq(f, H)
        mag_db = 20 * np.log10(np.abs(H))
        f180 = cross_freq(f, ph, -180.0)
        # gain AT the 180-deg crossing: a 2-stage ring needs |H| >= 1 there
        g180 = np.interp(np.log10(f180), np.log10(f), mag_db) if f180 else None
        rows.append({
            "variant": m["name"],
            "params": " ".join(f"{k}={v}" for k, v in m["params"].items()) or "nominal",
            "dc_gain_dB": f"{mag_db[0]:.2f}",
            "dc_gain": f"{np.abs(H[0]):.2f}",
            "dc_sign": "+" if H[0].real > 0 else "-",
            "Ax_dc_dB": f"{20*np.log10(np.abs(X[0])):.2f}",
            "f180_GHz": ghz(f180),
            "gain_at_f180_dB": "" if g180 is None else f"{g180:.2f}",
            "can_sustain_2stage": "" if g180 is None else ("yes" if g180 >= 0 else "no"),
            "f90_GHz": ghz(cross_freq(f, ph, -90.0)),
            "f_unity_GHz": ghz(cross_freq(f, mag_db, 0.0)),
            "f_notch_GHz": ghz(fn),
            "notch_mag_dB": "" if mn is None else f"{20*np.log10(mn):.2f}",
            "f_Ax_unity_GHz": ghz(cross_freq(f, 20 * np.log10(np.abs(X)), 0.0)),
        })
    return rows


# ------------------------------------------------------- oscillator variants
def osc_table(corner="tt", vmid=0.9, settle=0.5):
    man = json.load(open(f"{W}/osc_manifest.json"))
    dv = np.loadtxt(f"{W}/osc_v_{corner}.dat")
    di = np.loadtxt(f"{W}/osc_i_{corner}.dat")
    t = dv[:, 0]
    keep = t >= t[-1] * settle
    t2 = t[keep]
    rows = []
    for m in man:
        k = m["i"]
        sig = [dv[keep, 1 + 2 * (4 * k + j)] for j in range(4)]
        cur = di[keep, 1 + 2 * k]
        pwr = 1.8 * float(np.mean(np.abs(cur)))
        swing = [float(s.max() - s.min()) for s in sig]
        r = {"variant": m["name"], "kind": m["kind"],
             "params": " ".join(f"{a}={b}" for a, b in m["params"].items()),
             "min_swing_V": f"{min(swing):.3f}", "power_mW": f"{pwr*1e3:.3f}"}
        xs = [rising_crossings(t2, s, vmid) for s in sig]
        if min(swing) < 0.3 or min(len(x) for x in xs) < 3:
            r.update(osc="LATCH", f_GHz="", phases_deg="", gaps_deg="",
                     quad_err_deg="", quadrature="", jitter_pct="",
                     fom_GHz_per_mW="")
            rows.append(r)
            continue
        per = np.diff(xs[0])
        T = float(np.median(per))
        f0 = 1.0 / T
        # phase of each node at the fundamental, by single-bin DFT over an
        # integer number of periods (robust against edge-slope asymmetry)
        ncyc = max(1, int((t2[-1] - t2[0]) / T) - 1)
        wmask = (t2 >= t2[0]) & (t2 <= t2[0] + ncyc * T)
        tw = t2[wmask]
        k = np.exp(-2j * np.pi * f0 * tw)
        amp = [np.sum((s[wmask] - s[wmask].mean()) * k) for s in sig]
        ph = [float((np.angle(a / amp[0])) * 180 / np.pi % 360.0) for a in amp]
        sp = sorted(ph)
        gaps = [(sp[(j + 1) % 4] - sp[j]) % 360.0 for j in range(4)]
        quad_err = max(abs(g - 90.0) for g in gaps)
        r.update(osc="OSC", f_GHz=f"{f0/1e9:.3f}",
                 phases_deg="/".join(f"{x:.0f}" for x in ph),
                 gaps_deg="/".join(f"{g:.0f}" for g in gaps),
                 quad_err_deg=f"{quad_err:.1f}",
                 quadrature="yes" if quad_err <= 10 else "no",
                 jitter_pct=f"{100*np.std(per)/T:.3f}",
                 fom_GHz_per_mW=f"{(f0/1e9)/(pwr*1e3):.2f}" if pwr > 0 else "")
        rows.append(r)
    return rows


def write(rows, path):
    if not rows:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {path}  ({len(rows)} rows)")


if __name__ == "__main__":
    import sys
    corner = sys.argv[1] if len(sys.argv) > 1 else "tt"
    sfx = "" if corner == "tt" else f"_{corner}"
    if os.path.exists(f"{W}/ac_out_{corner}.dat"):
        r = ac_table(corner); write(r, f"results/cell_ac{sfx}.csv")
        for x in r:
            print(f"  {x['variant']:<22} DC={x['dc_gain_dB']:>7}dB({x['dc_sign']}) "
                  f"f180={x['f180_GHz']:>7}GHz  |H|@180={x['gain_at_f180_dB']:>7}dB "
                  f"sustain={x['can_sustain_2stage']:<4} notch={x['f_notch_GHz']}")
    if os.path.exists(f"{W}/osc_v_{corner}.dat"):
        r = osc_table(corner); write(r, f"results/osc{sfx}.csv")
        for x in r:
            print(f"  {x['variant']:<30} {x['osc']:<6} f={x['f_GHz']:>7} GHz "
                  f"gaps={x['gaps_deg']:<16} quadErr={x['quad_err_deg']:>5} "
                  f"P={x['power_mW']:>7} mW")
