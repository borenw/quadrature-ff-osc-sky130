#!/usr/bin/env python3
"""Emit one netlist holding every AC variant of the feedforward cell, plus a manifest.

Every variant is an independent circuit sharing only vdd and the bias node, so a
single .ac run characterises all of them -- important because loading the sky130
model library costs ~40 s per ngspice invocation.
"""
import json, sys

Z = "1e-21"   # "zero" cap


def variants():
    V = []
    # -- Analysis 2: path decomposition (aca, acb select which path is driven)
    V.append(("full",    {}, 1, 1))
    V.append(("buffer",  {}, 1, 0))
    V.append(("invonly", {}, 0, 1))
    # -- Analysis 3: one knob at a time
    for v in (4, 3, 2, 1):
        V.append((f"sz2={v}", {"SZ2": v}, 1, 1))
    for v in (2, 4, 8, 12, 16, 24):
        V.append((f"sz3={v}", {"SZ3": v}, 1, 1))
    for v in (2, 4, 8):
        V.append((f"sz1={v}", {"SZ1": v}, 1, 1))
    for v in (0, 1, 2, 5, 10):
        V.append((f"cx={v}f", {"CX": f"{v}f" if v else Z}, 1, 1))
    for v in (0, 0.5, 1, 2, 5):
        V.append((f"cff={v}f", {"CFF": f"{v}f" if v else Z}, 1, 1))
    for v in ("1T", "50k", "20k", "10k", "5k"):
        V.append((f"rlo={v}", {"RLO": v}, 1, 1))
    for v in ("1T", "50k", "20k", "10k", "5k"):
        V.append((f"rlx={v}", {"RLX": v}, 1, 1))
    # -- combined candidate: direct inverter up, buffer 2nd stage down
    for s2, s3 in ((2, 8), (1, 8), (1, 12), (1, 16), (1, 20), (2, 16), (2, 24), (1, 24)):
        V.append((f"opt sz2={s2} sz3={s3}", {"SZ2": s2, "SZ3": s3}, 1, 1))
    return V


def main(corner="tt", out=None):
    out = out or f"results/work/ac_all_{corner}.sp"
    V = variants()
    L = [
        f"* AC characterisation of the feedforward cell -- all variants, corner={corner}",
        f'.lib "$PDK_ROOT/sky130A/libs.tech/ngspice/sky130.lib.spice" {corner}',
        ".include spice/common.sp",
        "Vdd vdd 0 1.8",
        "Xtrip vb vdd tripgen",
        "",
    ]
    man = []
    for k, (name, kw, aca, acb) in enumerate(V):
        pa = " ".join(f"{a}={b}" for a, b in kw.items())
        if aca and acb:
            L.append(f"Vin{k} in{k} vb DC 0 AC 1")
            ina, inb = f"in{k}", f"in{k}"
        elif aca:
            L.append(f"Vin{k} in{k} vb DC 0 AC 1")
            ina, inb = f"in{k}", "vb"
        else:
            L.append(f"Vin{k} in{k} vb DC 0 AC 1")
            ina, inb = "vb", f"in{k}"
        L.append(f"X{k} {ina} {inb} nx{k} out{k} vdd vb ffcell {pa}")
        man.append({"i": k, "name": name, "params": {a: str(b) for a, b in kw.items()},
                    "aca": aca, "acb": acb})
    outs = " ".join(f"v(out{k})" for k in range(len(V)))
    nxs = " ".join(f"v(nx{k})" for k in range(len(V)))
    L += [
        "",
        ".ac dec 50 1k 100G",
        ".control",
        "op",
        f"print v(vb) > results/work/ac_vb_{corner}.txt",
        f"print {' '.join(f'v(out{k}) v(nx{k})' for k in range(len(V)))} > results/work/ac_op_{corner}.txt",
        "run",
        f"wrdata results/work/ac_out_{corner}.dat {outs}",
        f"wrdata results/work/ac_nx_{corner}.dat {nxs}",
        ".endc",
        ".end",
    ]
    open(out, "w").write("\n".join(L) + "\n")
    json.dump(man, open("results/work/ac_manifest.json", "w"), indent=1)
    print(f"{len(V)} variants -> {out}")


if __name__ == "__main__":
    main(*(sys.argv[1:] or ["tt"]))
