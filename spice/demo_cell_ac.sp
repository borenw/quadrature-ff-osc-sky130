* demo_cell_ac.sp -- smallest standalone reproduction of the headline result.
*
*   ngspice -b spice/demo_cell_ac.sp      (run from the repo root)
*
* Prints the frequency at which the feedforward cell and a plain buffer each
* reach -180 deg, and the gain each has left at that point. The cell still has
* gain above 1 there and the buffer does not -- which is why two cells can close
* a ring and two buffers cannot.
.lib "$PDK_ROOT/sky130A/libs.tech/ngspice/sky130.lib.spice" tt
.include spice/common.sp

Vdd vdd 0 1.8
Xtrip vb vdd tripgen          ; vb = inverter trip point, a stiff AC ground

* cell: both paths driven
Vin1 in1 vb DC 0 AC 1
X1 in1 in1 nx1 out1 vdd vb ffcell
* buffer path only: the direct inverter's gate is held at DC bias (AC 0), so its
* gm contributes nothing while its output device still loads OUT identically
Vin2 in2 vb DC 0 AC 1
X2 in2 vb nx2 out2 vdd vb ffcell

.ac dec 50 1k 100G
.control
run
let phc = 180/pi * cph(v(out1))
let phb = 180/pi * cph(v(out2))
meas ac f180_cell   when phc=-180 cross=1
meas ac f180_buffer when phb=-180 cross=1
meas ac gain_cell   find vdb(out1) when phc=-180 cross=1
meas ac gain_buffer find vdb(out2) when phb=-180 cross=1
.endc
.end
