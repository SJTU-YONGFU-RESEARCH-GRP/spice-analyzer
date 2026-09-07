# spice-analyzer

Validate analog SPICE netlists with small-signal analysis, ngspice, and LaTeX/PDF reports.

## Agent setup (multi-tool)

| File | Purpose |
|------|---------|
| [AGENTS.md](AGENTS.md) | Shared agent instructions (Codex, Cursor, …) |
| [CLAUDE.md](CLAUDE.md) | Claude Code adapter → imports `AGENTS.md` |
| [.agents/skills/spice-analyzer](.agents/skills/spice-analyzer) | Canonical skill |

Symlinks under `.cursor/skills`, `.claude/skills`, and `.codex/skills` point at the same skill directory.
