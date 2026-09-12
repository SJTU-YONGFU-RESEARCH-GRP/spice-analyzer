# Agentic provenance

- Skill: spice-analyzer (`.agents/skills/spice-analyzer`)
- Run id: leung_nmcf_pin_3
- Date: 2026-09-12

| Role | Host | Model | Scope | Notes |
|------|------|-------|-------|-------|
| Primary orchestrator | Cursor | Composer (slug unknown) | ingest--report | skill spice-analyzer; IHP backend completed after PDK fetch |
| Simulation / recovery (IHP) | Cursor | Composer (slug unknown) | §3--4e ihp | OpenVAF OSDI + cornerMOSlv |
| Delivery / re-validation | Cursor | Composer (slug unknown) | stage results + sky130 ACDC recheck | single `results/leung_nmcf_pin_3/` |

Toolchain: ngspice-46+; plots via Python matplotlib (skill `plotting/`).
