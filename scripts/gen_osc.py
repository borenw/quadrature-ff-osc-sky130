#!/usr/bin/env python3
"""Emit one netlist holding every ring-oscillator variant, plus a manifest.

Startup is modelled honestly: each variant has its OWN supply, ramped 0 -> 1.8 V
over 100 ps, and a single 10 ps / 20 uA current pulse at 150 ps to break symmetry
(a real ring starts on noise). Nothing is forced with .ic, so a variant only
"oscillates" here if it genuinely self-starts. Separate supplies also let each
variant's power be measured independently.
"""
import json, sys


def variants():
    V = [("ring8 baseline (8 inv, one size)", "ring8", {"SZF": 4, "SZC": 4})]
    for szc in (1, 2, 3, 5, 6, 8):
        V.append((f"ring8 szf=4 szc={szc}", "ring8", {"SZF": 4, "SZC": szc}))

    def r6(s1, s2, s3):
        V.append((f"ring6 sz1={s1} sz2={s2} sz3={s3}", "ring6",
                  {"SZ1": s1, "SZ2": s2, "SZ3": s3}))

    # map 1: the sz3/sz2 ratio sets both the oscillation window and the phase split
    for s3 in (4, 5, 6, 7, 8, 10, 12, 16):
        r6(4, 4, s3)
    # map 2: finer ratios just above the latch boundary, where quadrature is best
    for s1 in (4, 8):
        for s3 in (9, 10, 11, 12):
            r6(s1, 8, s3)
    for s1 in (8, 16):
        for s3 in (17, 18, 20):
            r6(s1, 16, s3)
    # map 3: buffer first-stage size at the two most promising ratios
    for s1 in (1, 2, 3, 6, 8):
        r6(s1, 4, 5)
    for s1 in (1, 2, 8):
        r6(s1, 4, 8)
    return V


def main(corner="tt", out=None, tstop="10n", tstep="0.5p"):
    out = out or f"results/work/osc_all_{corner}.sp"
    V = variants()
    L = [f"* Ring-oscillator comparison -- all variants, corner={corner}",
         f'.lib "$PDK_ROOT/sky130A/libs.tech/ngspice/sky130.lib.spice" {corner}',
         ".include spice/common.sp", ""]
    man, vnodes, inodes = [], [], []
    for k, (name, kind, kw) in enumerate(V):
        pa = " ".join(f"{a}={b}" for a, b in kw.items())
        n = [f"q{k}_{j}" for j in range(1, 5)]
        L.append(f"Vd{k} vd{k} 0 PWL(0 0 100p 1.8)")
        L.append(f"Ik{k} 0 {n[0]} PULSE(0 20u 150p 1p 1p 10p 1)")
        L.append(f"X{k} {' '.join(n)} vd{k} {kind} {pa}")
        vnodes += [f"v({x})" for x in n]
        inodes.append(f"i(Vd{k})")
        man.append({"i": k, "name": name, "kind": kind,
                    "params": {a: str(b) for a, b in kw.items()}, "nodes": n})
    L += ["", f".tran {tstep} {tstop}",
          ".control", "run",
          f"wrdata results/work/osc_v_{corner}.dat {' '.join(vnodes)}",
          f"wrdata results/work/osc_i_{corner}.dat {' '.join(inodes)}",
          ".endc", ".end"]
    open(out, "w").write("\n".join(L) + "\n")
    json.dump(man, open("results/work/osc_manifest.json", "w"), indent=1)
    print(f"{len(V)} oscillator variants -> {out}")


if __name__ == "__main__":
    main(*(sys.argv[1:] or ["tt"]))
