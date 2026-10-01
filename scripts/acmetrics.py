"""Post-process an ngspice AC wrdata file: unwrapped phase, 180-deg crossing, magnitude notch."""
import numpy as np


def load_ac(path, ncols_per_vec=3):
    """wrdata writes 'freq re im' per complex vector, columns concatenated."""
    d = np.loadtxt(path)
    f = d[:, 0]
    vecs = []
    for k in range(0, d.shape[1], ncols_per_vec):
        vecs.append(d[:, k + 1] + 1j * d[:, k + 2])
    return f, vecs


def phase_deg(H):
    """Continuous (unwrapped) phase in degrees, anchored so DC phase is 0 or 180."""
    ph = np.unwrap(np.angle(H)) * 180.0 / np.pi
    return ph - round(ph[0] / 180.0) * 180.0


def cross_freq(f, y, target):
    """Log-frequency interpolated first crossing of `target`."""
    s = np.sign(y - target)
    idx = np.where(np.diff(s) != 0)[0]
    if len(idx) == 0:
        return None
    i = idx[0]
    y0, y1 = y[i], y[i + 1]
    lf0, lf1 = np.log10(f[i]), np.log10(f[i + 1])
    t = (target - y0) / (y1 - y0)
    return 10 ** (lf0 + t * (lf1 - lf0))


def notch_freq(f, H):
    """Interpolated frequency and depth of the magnitude minimum (parabola in log-log)."""
    mag = np.abs(H)
    i = int(np.argmin(mag))
    if i == 0 or i == len(f) - 1:
        return None, None
    lf = np.log10(f[i - 1:i + 2])
    lm = np.log10(mag[i - 1:i + 2])
    a, b, c = np.polyfit(lf, lm, 2)
    if a <= 0:
        return f[i], mag[i]
    lfm = -b / (2 * a)
    return 10 ** lfm, 10 ** (a * lfm ** 2 + b * lfm + c)


def analyze(path):
    f, vecs = load_ac(path)
    H = vecs[0]
    ph = phase_deg(H)
    fn, mn = notch_freq(f, H)
    return {
        "f": f, "H": H, "phase": ph,
        "dc_gain": float(np.abs(H[0])),
        "dc_gain_db": float(20 * np.log10(np.abs(H[0]))),
        "f180": cross_freq(f, ph, -180.0),
        "f90": cross_freq(f, ph, -90.0),
        "f_notch": fn,
        "notch_mag": mn,
        "f_unity": cross_freq(f, 20 * np.log10(np.abs(H)), 0.0),
        "aux": vecs[1:],
    }


if __name__ == "__main__":
    import sys
    for p in sys.argv[1:]:
        r = analyze(p)
        print(f"{p}")
        print(f"  DC gain      : {r['dc_gain']:.2f} ({r['dc_gain_db']:.2f} dB)")
        print(f"  f(-90 deg)   : {r['f90']/1e9:.3f} GHz" if r['f90'] else "  f(-90): none")
        print(f"  f(-180 deg)  : {r['f180']/1e9:.3f} GHz" if r['f180'] else "  f(-180): none")
        if r['f_notch']:
            print(f"  notch        : {r['f_notch']/1e9:.3f} GHz, |H|={r['notch_mag']:.4f}")
        print(f"  unity-gain   : {r['f_unity']/1e9:.3f} GHz" if r['f_unity'] else "  unity: none")
