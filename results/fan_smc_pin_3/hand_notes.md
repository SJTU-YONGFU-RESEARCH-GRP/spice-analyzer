# Hand analysis notes — fan_smc_pin_3 (SMC + FF)

Source path: `Fan_SMC_Pin_3`. Topology inferred from netlist (not a suite label).

## Signal path (Step 4.0)

- **Stage 1 (gm1):** PMOS diff pair `xm8`/`xm9` (VINN/VINP), tail `xm4`, folded NMOS cascode stack `xm15`/`xm16`/`xm19`/`xm20`. Differential first-stage output folded through PMOS mirror `xm5`/`xm6` onto high-Z node **`net050`** (= \(v_1\)).
- **Stage 2 (gm2):** PMOS `xm10` (gate=`net050`) into diode NMOS `xm21` (`net043`), mirrored by `xm22` onto **`net049`** (= \(v_2\)).
- **Stage 3 (gm3):** NMOS `xm23` (gate=`net049`) to **`VOUT`**.
- **Feedforward (gmf):** PMOS `xm11` (gate=`net050`) to **`VOUT`**.
- **Compensation:** `C0` between `net050` and `VOUT` (Single Miller).
- **Load:** external `CLOAD` at `VOUT`.

## Bias map (Step 1 / 7.1) — ideal ratios from netlist `m`

Let \(I_b=\) `CURRENT_0_BIAS`, \(M_p=\) `MOSFET_0_8_M_BIASCM_PMOS`, \(M_n=\) `MOSFET_17_7_M_BIASCM_NMOS`.

PMOS diode `xm0` carries \(I_b\). Branches on gate `net013`:
- `xm1`,`xm2`,`xm3`,`xm7`: \(1\cdot M_p\) each (bias / aux)
- `xm4` tail: \(4\cdot M_p\) → \(I_{\mathrm{tail}}=4 I_b\) (each input leg \(\approx 2 I_b\) if balanced)
- `xm5`/`xm6`: \(1\cdot M_p\) (stage-1 PMOS mirror)

NMOS stack (gate `VB3`/`VB4` from `xm14`/`xm12`):
- Diff-leg bottoms `xm19`/`xm20`: \(8 M_n\) units relative to unit `xm14`
- Cascode folds `xm15`/`xm16`: \(4 M_n\)
- Bias ladder `xm17`/`xm18`/`xm13`/`xm12`: \(4 M_n\)

Stage-2/3/FF sized by separate `M` params (gm2/gm3/gmf devices) — currents from OP after fit.

## Small-signal model (4.1)

Retain: \(g_{m1}\) (diff-pair effective), \(R_1\) at \(v_1\), \(g_{m2}\), \(R_2\) at \(v_2\), \(g_{m3}\), \(R_3\) at \(v_{\mathrm{out}}\), \(g_{mf}\), \(C_c=C_0\), \(C_L\).

Neglect device \(C_{gs}/C_{gd}\) vs \(C_c,C_L\) near GBW (state in report after OP).

## KCL sketch (4.3)

\[
\begin{aligned}
v_1&: g_{m1}v_{\mathrm{id}}+\frac{v_1}{R_1}+s C_c(v_1-v_{\mathrm{out}})=0,\\
v_2&: g_{m2}v_1+\frac{v_2}{R_2}=0 \quad (\text{neglect }C_{\mathrm{par},2}\text{ at first}),\\
v_{\mathrm{out}}&: g_{m3}v_2+g_{mf}v_1+\frac{v_{\mathrm{out}}}{R_3}+s C_L v_{\mathrm{out}}+s C_c(v_{\mathrm{out}}-v_1)=0.
\end{aligned}
\]

With \(v_2=-g_{m2}R_2 v_1\), high-gain Miller approximations:
- \(A_0=g_{m1}R_1\cdot g_{m2}R_2\cdot g_{m3}R_3\) (FF adds parallel path at DC: small correction; quote product of three stages as primary)
- \(\omega_t\approx g_{m1}/C_c\)
- \(\omega_{p1}=\omega_t/A_0\)
- \(\omega_{p2}\approx g_{m2}/C_c\) (inner node / SMC second pole order — refine with OP)
- \(\omega_{p3}\approx g_{m3}/C_L\)
- \(\omega_z\approx g_{mf}/C_c\) (LHP FF zero)

Reduced:
\[
A(s)\approx A_0\frac{1+s/\omega_z}{(1+s/\omega_{p1})(1+s/\omega_{p2})(1+s/\omega_{p3})}.
\]

Numeric substitution waits for final OP \(g_m\) after §4b recovery.
