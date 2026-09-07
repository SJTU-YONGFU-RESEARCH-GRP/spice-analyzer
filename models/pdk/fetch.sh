#!/usr/bin/env bash
# Fetch open PDK SPICE / primitive model trees into models/pdk/
# Usage (WSL or Git Bash): ./fetch.sh [--sky130] [--gf180] [--ihp] [--all]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

fetch_sparse() {
  local name="$1" url="$2" branch="$3"
  shift 3
  local paths=("$@")
  local dest="$ROOT/$name"
  local force_refresh=0
  # Re-fetch sky130 if models exist but cells/ are missing (needed by corners/*.spice)
  if [[ "$name" == "sky130_fd_pr" && -d "$dest/.git" && ! -d "$dest/cells" ]]; then
    echo "[refresh] $name — adding sparse paths for cells/"
    force_refresh=1
  fi
  if [[ -d "$dest/.git" && $force_refresh -eq 0 ]]; then
    echo "[skip] $name already present"
    return 0
  fi
  echo "[clone] $name from $url ($branch) sparse: ${paths[*]}"
  if [[ $force_refresh -eq 0 ]]; then
    rm -rf "$dest"
    mkdir -p "$dest"
    git -C "$dest" init
    git -C "$dest" remote add origin "$url"
  fi
  git -C "$dest" config core.sparseCheckout true
  printf '%s\n' "${paths[@]}" > "$dest/.git/info/sparse-checkout"
  if ! git -C "$dest" fetch --depth 1 origin "$branch"; then
    git -C "$dest" fetch origin "$branch"
  fi
  git -C "$dest" checkout -B "$branch" FETCH_HEAD
  echo "[done] $name"
}

do_sky130=0 do_gf180=0 do_ihp=0
if [[ $# -eq 0 ]] || [[ "${1:-}" == "--all" ]]; then
  do_sky130=1 do_gf180=1 do_ihp=1
fi
for a in "$@"; do
  case "$a" in
    --sky130) do_sky130=1 ;;
    --gf180) do_gf180=1 ;;
    --ihp) do_ihp=1 ;;
    --all) do_sky130=1 do_gf180=1 do_ihp=1 ;;
  esac
done

# SkyWater SKY130: models + FET cells referenced by corners/tt.spice
if [[ $do_sky130 -eq 1 ]]; then
  fetch_sparse sky130_fd_pr \
    https://github.com/google/skywater-pdk-libs-sky130_fd_pr.git \
    main \
    /models/ \
    /cells/nfet_01v8/ \
    /cells/nfet_01v8_lvt/ \
    /cells/pfet_01v8/ \
    /cells/pfet_01v8_lvt/ \
    /cells/pfet_01v8_hvt/ \
    /cells/nfet_g5v0d10v5/ \
    /cells/pfet_g5v0d10v5/ \
    /cells/nfet_03v3_nvt/ \
    /cells/esd_nfet_01v8/ \
    /cells/esd_pfet_g5v0d10v5/ \
    /cells/esd_nfet_g5v0d10v5/ \
    /cells/nfet_g5v0d16v0/ \
    /cells/pfet_g5v0d16v0/ \
    /cells/nfet_20v0/ \
    /cells/pfet_20v0/ \
    /cells/nfet_20v0_nvt/ \
    /cells/nfet_05v0_nvt/ \
    /README* \
    /LICENSE* \
    /AUTHORS*
fi

# GlobalFoundries GF180MCU primitives
if [[ $do_gf180 -eq 1 ]]; then
  fetch_sparse gf180mcu_fd_pr \
    https://github.com/google/globalfoundries-pdk-libs-gf180mcu_fd_pr.git \
    main \
    /models/ \
    /README* \
    /LICENSE* \
    /AUTHORS*
fi

# IHP SG13G2 Open PDK (dev branch — ngspice + Verilog-A for OpenVAF)
if [[ $do_ihp -eq 1 ]]; then
  dest="$ROOT/ihp-sg13g2"
  # Refresh if models exist but Verilog-A / compile script missing (needed for OSDI).
  if [[ -d "$dest/.git" && ! -f "$dest/ihp-sg13g2/libs.tech/verilog-a/openvaf-compile-va.sh" ]]; then
    echo "[refresh] ihp-sg13g2 — adding sparse paths for verilog-a/"
    rm -rf "$dest"
  fi
  fetch_sparse ihp-sg13g2 \
    https://github.com/IHP-GmbH/IHP-Open-PDK.git \
    dev \
    /ihp-sg13g2/libs.tech/ngspice/ \
    /ihp-sg13g2/libs.tech/verilog-a/ \
    /ihp-sg13g2/libs.tech/spice/ \
    /ihp-sg13g2/libs.ref/sg13g2_pr/ \
    /ihp-sg13g2/README* \
    /LICENSE* \
    /README*

  # Compile PSP / resistor / cap Verilog-A → OSDI (once; openvaf on PATH).
  va_dir="$ROOT/ihp-sg13g2/ihp-sg13g2/libs.tech/verilog-a"
  osdi="$ROOT/ihp-sg13g2/ihp-sg13g2/libs.tech/ngspice/osdi/psp103.osdi"
  if [[ -f "$va_dir/openvaf-compile-va.sh" && ! -f "$osdi" ]]; then
    echo "[openvaf] compiling IHP Verilog-A → osdi/ (this can take a few minutes)"
    if command -v openvaf-r >/dev/null 2>&1 || command -v openvaf >/dev/null 2>&1; then
      # Prefer openvaf-r (OSDI 0.4). Stock openvaf 23.5 crashes on --target_cpu /
      # --compile-model-generic — call openvaf without those flags.
      if command -v openvaf-r >/dev/null 2>&1; then
        (cd "$va_dir" && bash ./openvaf-compile-va.sh --compile-model-generic) \
          || (cd "$va_dir" && bash ./openvaf-compile-va.sh)
      else
        mkdir -p "$(dirname "$osdi")"
        (
          cd "$va_dir"
          openvaf -D__NGSPICE__ -o ../ngspice/osdi/psp103.osdi psp103/psp103.va
          openvaf -D__NGSPICE__ -o ../ngspice/osdi/psp103_nqs.osdi psp103/psp103_nqs.va
          openvaf -D__NGSPICE__ -o ../ngspice/osdi/r3_cmc.osdi r3_cmc/r3_cmc.va
          openvaf -D__NGSPICE__ -o ../ngspice/osdi/mosvar.osdi mosvar/mosvar.va
          openvaf -D__NGSPICE__ -o ../ngspice/osdi/cap_cmomi.osdi cap_cmomi/cap_cmomi.va
          openvaf -D__NGSPICE__ -o ../ngspice/osdi/cap_cmomf.osdi cap_cmomf/cap_cmomf.va
        )
      fi
    else
      echo "[warn] openvaf not on PATH — install OpenVAF then re-run: cd $va_dir && ./openvaf-compile-va.sh"
    fi
  elif [[ -f "$osdi" ]]; then
    echo "[skip] IHP OSDI already present: $osdi"
  fi
fi

echo "All requested PDK fetches finished under $ROOT"
ls -la "$ROOT"
