#!/bin/sh
# Reproduce every result in this repo from scratch.
#   PDK_ROOT must point at the directory CONTAINING sky130A (e.g. ~/.volare)
#
# Each analysis packs all of its variants into ONE netlist: loading the sky130
# model library costs ~40 s per ngspice invocation, so this is 6 invocations
# rather than ~250.
set -e
: "${PDK_ROOT:=$HOME/.volare}"
export PDK_ROOT
cd "$(dirname "$0")/.."
mkdir -p results/work docs

for c in tt ss ff; do
  echo "== corner $c : generating netlists =="
  python3 scripts/gen_ac.py  "$c"
  python3 scripts/gen_osc.py "$c"

  echo "== corner $c : AC characterisation (44 cell variants) =="
  ngspice -b "results/work/ac_all_$c.sp"  > "results/work/ac_$c.log" 2>&1

  echo "== corner $c : ring-oscillator sweep (37 variants) =="
  ngspice -b "results/work/osc_all_$c.sp" > "results/work/osc_$c.log" 2>&1

  echo "== corner $c : reducing to tables =="
  PYTHONPATH=scripts python3 scripts/analyze.py "$c"
done

echo "== figures and README =="
PYTHONPATH=scripts python3 scripts/plots.py
python3 scripts/make_readme.py
echo "done -- see README.md, results/ and docs/"
