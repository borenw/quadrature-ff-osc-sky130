* common.sp -- shared primitives for the feedforward-cell study (sky130A)
*
* SIZING MODEL -- two traps in sky130 that this works around:
*  1) The sky130 FET models are *width-binned to discrete values*; an arbitrary W
*     (e.g. 0.35u) fails with "could not find a valid modelname". So W is pinned
*     to a legal bin and sizing is done with the device multiplier m, which was
*     verified to scale drain current exactly (m=4 -> 4.000x, m=12 -> 12.000x).
*  2) The knob is named SZ, never M: on a subcircuit instance line SPICE reserves
*     `m` as the multiplicity factor, so a user parameter called M is silently
*     swallowed and never reaches the devices.
* SZ is therefore an INTEGER count of unit devices -- directly realisable as
* parallel fingers. Scaling both devices together keeps the trip point invariant.
.param WN=0.502 WP=1.002 LL=0.15 SZNOM=4

.subckt inv in out vdd vgnd SZ=4
XMN out in vgnd vgnd sky130_fd_pr__nfet_01v8 W={WN} L={LL} nf=1 m={SZ}
XMP out in vdd  vdd  sky130_fd_pr__pfet_01v8 W={WP} L={LL} nf=1 m={SZ}
.ends

* Feedforward cell: buffer (X1->X2) in parallel with single inverter (X3).
* Separate ina/inb ports let either path be "broken" for the decomposition run by
* tying that port to the bias node (DC only, AC 0) while BOTH output devices stay
* connected to OUT -- so Z_out is identical in every configuration.
* RLX/RLO return to vb (an AC ground at the trip point): they load the node in
* small signal without moving its DC bias.
.subckt ffcell ina inb nx out vdd vb SZ1=4 SZ2=4 SZ3=4 CX=1e-21 CFF=1e-21 RLX=1T RLO=1T
X1  ina nx  vdd 0 inv SZ={SZ1}
X2  nx  out vdd 0 inv SZ={SZ2}
X3  inb out vdd 0 inv SZ={SZ3}
CX  nx  0   {CX}
CFF nx  out {CFF}
RX  nx  vb  {RLX}
RO  out vb  {RLO}
* load on OUT = input gates of an identical following stage
XL1 out nl1 vdd 0 inv SZ={SZ1}
XL3 out nl3 vdd 0 inv SZ={SZ3}
.ends

* Self-biased inverter: output tied to input sits exactly at the trip point, so
* the AC bias tracks the process corner automatically. Eb makes a stiff copy.
.subckt tripgen vb vdd
Xt vt vt vdd 0 inv SZ={SZNOM}
Eb vb 0  vt 0 1
.ends

* ---------------------------------------------------------------------------
* Ring oscillators under comparison
* ---------------------------------------------------------------------------
* PROPOSED: 6 inverters = two feedforward cells in a loop.
* Quadrature taps are a, x1, b, x2.
.subckt ring6 a x1 b x2 vdd SZ1=4 SZ2=4 SZ3=4
X1 a  x1 vdd 0 inv SZ={SZ1}
X2 x1 b  vdd 0 inv SZ={SZ2}
X3 a  b  vdd 0 inv SZ={SZ3}
X4 b  x2 vdd 0 inv SZ={SZ1}
X5 x2 a  vdd 0 inv SZ={SZ2}
X6 b  a  vdd 0 inv SZ={SZ3}
.ends

* BASELINE: 8 inverters, all one size. Four forward inverters form a 4-ring
* (bistable on its own); four cross-coupled inverters between antipodal nodes
* enforce the 180-deg antiphase and destabilise the latch, giving 4 phases
* nominally 90 deg apart.
.subckt ring8 q1 q2 q3 q4 vdd SZF=4 SZC=4
XF1 q1 q2 vdd 0 inv SZ={SZF}
XF2 q2 q3 vdd 0 inv SZ={SZF}
XF3 q3 q4 vdd 0 inv SZ={SZF}
XF4 q4 q1 vdd 0 inv SZ={SZF}
XC1 q1 q3 vdd 0 inv SZ={SZC}
XC2 q3 q1 vdd 0 inv SZ={SZC}
XC3 q2 q4 vdd 0 inv SZ={SZC}
XC4 q4 q2 vdd 0 inv SZ={SZC}
.ends
