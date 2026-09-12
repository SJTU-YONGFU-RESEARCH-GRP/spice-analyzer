#!/usr/bin/env bash
# Run nominal ACDC + extended specs for all backends; save nominal copies.
set -e
RUN=/mnt/d/proj/spice-analyzer-skill/results/fan_smc_pin_3
NG=/usr/local/bin/ngspice

run_one() {
  local be=$1
  echo "=== NOMINAL $be $(date) ==="
  cd "$RUN/$be/tb"
  $NG -b tb_acdc.sp > ../sim/acdc.log 2>&1 || echo "WARN acdc $be exit $?"
  # save nominal copies
  for f in adc ugf ph_at_ugf idd_raw vout_dc; do
    [[ -f ../sim/${f}.txt ]] && cp -f ../sim/${f}.txt ../sim/${f}_nom.txt || true
  done
  [[ -f ../figures/bode_mag.dat ]] && cp -f ../figures/bode_mag.dat ../figures/bode_mag_nom.dat || true
  [[ -f ../figures/bode_phase.dat ]] && cp -f ../figures/bode_phase.dat ../figures/bode_phase_nom.dat || true
  echo -n "adc="; cat ../sim/adc.txt 2>/dev/null | head -1
  echo -n "ugf="; cat ../sim/ugf.txt 2>/dev/null | head -1
  echo -n "vout="; grep -E '^vout ' ../sim/op_nodes.txt 2>/dev/null | head -1
  echo -n "idd="; grep 'vdd#branch' ../sim/op_nodes.txt 2>/dev/null | head -1

  for tb in tb_cmrr.sp tb_psrrp.sp tb_psrrn.sp tb_noise.sp; do
    echo "--- $be $tb ---"
    $NG -b "$tb" > ../sim/${tb%.sp}.log 2>&1 || echo "WARN $tb $be"
  done
  echo "=== DONE $be $(date) ==="
}

run_one cmos
run_one sky130
run_one ihp
run_one gf180

python3 "$RUN/_parse_metrics.py"
echo ALL_NOMINAL_DONE
