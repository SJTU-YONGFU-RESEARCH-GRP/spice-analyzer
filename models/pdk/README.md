# Open PDK models (journal multi-PDK evidence)

Educational Level-1 cards stay in [`../cmos.lib`](../cmos.lib). This folder holds **open foundry** SPICE / primitive trees for robustness benches (see [`../../publications/PAPER.md`](../../publications/PAPER.md)).

| Directory | Process | `--pdk` | Status with `python -m src` |
| --- | --- | --- | --- |
| (edu) | `models/cmos.lib` | `edu` | Default discovery / sizing |
| `gf180mcu_fd_pr/` | GlobalFoundries GF180MCU | `gf180` | **Working** |
| `sky130_fd_pr/` | SkyWater SKY130 | `sky130` | **Working** (loads `parameters/invariant.spice` + `typical.spice` + FET `*.pm3.spice`) |
| `ihp-sg13g2/` | IHP SG13G2 (~130 nm) | `ihp` | **Working** after `./fetch.sh --ihp` (compiles OpenVAF → `osdi/psp103*.osdi`) |

## Fetch

```bash
cd models/pdk && ./fetch.sh --all    # or --sky130 / --gf180 / --ihp
```

Sky130 needs `cells/` (FET primitives) — `fetch.sh --sky130` refreshes sparse checkout if cells were missing.

IHP needs **OpenVAF** (`openvaf` or `openvaf-r` on PATH) and ngspice ≥41. `fetch.sh --ihp` pulls `libs.tech/verilog-a/` and compiles OSDI into `ihp-sg13g2/.../ngspice/osdi/`. Stock OpenVAF 23.5 crashes on `--compile-model-generic`; the script falls back to plain `openvaf -D__NGSPICE__ …`.

## Bench usage

```bash
# Educational (default)
python3 -m src run netlists/<stem>.sp -o results --quick

# After Level-1 smoke PASS — multi-PDK robustness
python3 -m src run netlists/<stem>.sp -o results --pdk edu,gf180,sky130,ihp
python3 -m src run netlists/<stem>.sp -o results --pdk all
```

Outputs:

| Path | Backend |
| --- | --- |
| `results/<stem>/` | `edu` (back-compat) |
| `results/<stem>/gf180/` | GF180MCU |
| `results/<stem>/sky130/` | SKY130 |
| `results/<stem>/ihp/` | IHP SG13G2 |
| `results/BENCHMARK.md` | PDK column |

Remapping + prelude: [`../../src/pdk.py`](../../src/pdk.py). GF180 stages `sm141064.ngspice` into the work dir for nested `.lib` lookup.

## Notes

- Same topology / educational W/L is used across PDKs for a first robustness check; **retarget W/L per process** for fair journal tables.
- GF180 maps `nmos_dep`/`nmos_nat` → `nmos_3p3` (native 6 V needs L≥1.8 µm); tox→3p3 proxy for short edu L.
- IHP loads OSDI via a **work-dir** `.spiceinit` (does not touch `~/.spiceinit`). BJTs use Level-1 proxy cards.
- Educational LOT MC (`mc=1`) runs only for `edu`; open PDKs skip it for now.
