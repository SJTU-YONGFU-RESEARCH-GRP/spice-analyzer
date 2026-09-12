#!/usr/bin/env python3
"""Patch ACDC control blocks to print OP vectors that ngspice can write."""
from pathlib import Path

RUN = Path("/mnt/d/proj/spice-analyzer-skill/results/fan_smc_pin_3")

OLD = """op
let idd_op = -vdd#branch
let vout_op = v(vout)
let power_op = idd_op * {vdd}
print idd_op > ../sim/idd.txt
print vout_op > ../sim/vout_dc.txt
print power_op > ../sim/power.txt
print all > ../sim/op_nodes.txt
show m > ../sim/op_devices.txt
"""

# Use echo + meas-like approach: print vectors after op by name
NEW_TEMPLATE = """op
print all > ../sim/op_nodes.txt
show m > ../sim/op_devices.txt
* OP idd/vout captured via op_nodes; also try direct print
print vout > ../sim/vout_dc.txt
print vdd#branch > ../sim/idd_raw.txt
"""

END_OLD = """print idd_op > ../sim/idd.txt
print power_op > ../sim/power.txt
print vout_op > ../sim/vout_dc.txt
quit
"""

END_NEW = """quit
"""

for p in RUN.rglob("tb_acdc*.sp"):
    t = p.read_text()
    # detect vdd from power_op line
    import re

    m = re.search(r"let power_op = idd_op \* ([0-9.]+)", t)
    vdd = m.group(1) if m else "1.8"
    old = OLD.format(vdd=vdd)
    # also handle -i(VDD) variant if still present
    old2 = old.replace("let idd_op = -vdd#branch", "let idd_op = -i(VDD)")
    if "print all > ../sim/op_nodes.txt" in t and "print vdd#branch" not in t:
        # replace the op capture block flexibly
        t2 = re.sub(
            r"op\nlet idd_op = .*\nlet vout_op = .*\nlet power_op = .*\nprint idd_op > ../sim/idd\.txt\nprint vout_op > ../sim/vout_dc\.txt\nprint power_op > ../sim/power\.txt\nprint all > ../sim/op_nodes\.txt\nshow m > ../sim/op_devices\.txt\n",
            NEW_TEMPLATE,
            t,
        )
        t2 = t2.replace(END_OLD, END_NEW)
        if t2 != t:
            p.write_text(t2)
            print("patched", p.relative_to(RUN), "vdd", vdd)
        else:
            print("NOCHANGE", p)
    else:
        print("already?", p)
