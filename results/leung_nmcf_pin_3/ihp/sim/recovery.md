# IHP recovery (§4b)

## Problem
Iter0 (sky130 sizes @ VDD=1.2 V, C0=20p, CL=100p): OP healthy mid-rail but
open-loop UGF≈2.60 MHz with phase_at_ugf≈-43° → negative PM.

Root cause: IHP LV OP gm1≈382 µS vs sky130≈42 µS (~9×), so GBW≈gm1/(2πC0)
lands far above non-dominant poles with the sky130 compensation set.

## Actions
1. Raise outer Miller/NMC cap C0 20p→80p.
2. Trim C1 3p→2p; reduce CL 100p→50p (gf180-proven recipe for this topology).
3. Keep VDD=1.2 V, VCM=0.6 V, device W/L/M unchanged.

## Outcome
Healthy OP retained; Adc≈102.6 dB, UGF≈640 kHz, PM≈81.4°. Corners tt/ff/ss
all healthy with similar PM. No further device-width retarget needed.
