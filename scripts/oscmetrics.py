"""Measure ring-oscillator frequency and inter-node phase spacing from an ngspice .tran wrdata file."""
import numpy as np


def rising_crossings(t, v, level):
    """Linearly interpolated rising-edge crossing times of `level`."""
    s = v - level
    idx = np.where((s[:-1] < 0) & (s[1:] >= 0))[0]
    if len(idx) == 0:
        return np.array([])
    frac = -s[idx] / (s[idx + 1] - s[idx])
    return t[idx] + frac * (t[idx + 1] - t[idx])


def analyze(path, nsig=4, vmid=0.9, settle=0.5):
    d = np.loadtxt(path)
    t = d[:, 0]
    sig = [d[:, 1 + 2 * k] for k in range(nsig)]
    m = t >= t[-1] * settle          # discard startup transient
    t2 = t[m]
    sig = [s[m] for s in sig]

    swing = [float(s.max() - s.min()) for s in sig]
    if min(swing) < 0.2:                       # latched, not oscillating
        return {"osc": False, "swing": swing, "final": [float(s[-1]) for s in sig]}

    xs = [rising_crossings(t2, s, vmid) for s in sig]
    if min(len(x) for x in xs) < 3:
        return {"osc": False, "swing": swing, "final": [float(s[-1]) for s in sig]}

    per = np.diff(xs[0])
    T = float(np.median(per))
    f = 1.0 / T

    # phase of each node relative to node 0, in degrees, folded to [0,360)
    ph = [0.0]
    for k in range(1, nsig):
        dt = xs[k][0] - xs[0][xs[0] < xs[k][0]][-1] if np.any(xs[0] < xs[k][0]) else xs[k][0] - xs[0][0]
        ph.append(float((dt / T * 360.0) % 360.0))

    return {
        "osc": True, "f": f, "T": T,
        "swing": swing,
        "period_jitter_pct": float(100 * np.std(per) / T),
        "phases_deg": ph,
        "phase_steps_deg": [round(((ph[(k + 1) % nsig] - ph[k]) % 360.0), 1) for k in range(nsig)],
    }


if __name__ == "__main__":
    import sys
    for p in sys.argv[1:]:
        r = analyze(p)
        if not r["osc"]:
            print(f"{p}: LATCHED  final={[round(x,3) for x in r['final']]}")
        else:
            print(f"{p}: f={r['f']/1e9:.3f} GHz  swing={[round(s,2) for s in r['swing']]}")
            print(f"   phases={[round(p,1) for p in r['phases_deg']]}  steps={r['phase_steps_deg']}  jitter={r['period_jitter_pct']:.2f}%")
