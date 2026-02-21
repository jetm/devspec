# devspec

Spec-driven development workflow engine for Claude Code. Python rewrite of [OpenSpec](https://github.com/Fission-AI/OpenSpec)'s core engine — artifact graph, delta spec parser, spec merge engine, validator, and archive — in ~1,200 lines vs. OpenSpec's 17,000. Ships with 5 Claude Code skills for multi-model routing.

Zero migration: reads and writes the existing `openspec/` directory format, so all your specs and archived changes work as-is.

## Why fork?

OpenSpec's core workflow is sound — artifact graphs, delta specs, and structured validation work well. But the project accumulated weight that made it harder to use than the problem it solves:

- **17,000 lines for a 1,200-line problem.** 20+ tool adapters, shell completions for 4 shells, PostHog telemetry, an interactive TUI, and 3,400 lines of skill template generation. Most of it unused in a Claude Code workflow.
- **Broken context flow.** When OpenSpec migrated from CLI commands to Claude Code skills, the `context: fork` model severed context between phases. The explore phase produces decisions and constraints, but forked skills (plan, build) start with a blank slate. No mechanism existed to bridge that gap.
- **Tool-agnostic generality.** OpenSpec supports multiple AI coding tools. That flexibility costs complexity. devspec targets Claude Code only, which unlocks features that a generic tool can't use.
- **No multi-model routing.** OpenSpec runs every phase on the same model. But spec-driven development has phases with fundamentally different demands — exploration and verification need deep reasoning, implementation needs fast code generation at volume, and archival is mechanical. Running opus for a `git mv` wastes money; running haiku for architectural decisions wastes quality. devspec routes each skill to the model that fits: opus for thinking (explore, plan, verify), sonnet for execution (build), haiku for cleanup (archive). This isn't just cost optimization — it's better results at each phase, with the Task tool enabling opus skills to delegate bulk work to sonnet subagents within a single phase.

devspec keeps the parts that work — the artifact dependency graph, delta spec parser, spec merge engine, validator, and archive pipeline — and replaces everything else. The handoff system (`.handoff.md` files bridging context between skill phases) is new and solves the core pain point that prompted the fork.

### Beyond OpenSpec

Several features are new to devspec, inspired by GitHub's [spec-kit](https://github.com/github/spec-kit):

- **Cross-artifact analysis** (`devspec analyze`) — Semantic consistency checks across proposal, specs, design, and tasks: coverage gaps, capability alignment, ambiguity detection, terminology drift, and task format validation. OpenSpec's `validate` only checks structural rules within individual specs.
- **`[NEEDS CLARIFICATION]` markers** — A convention in spec and proposal templates for flagging explicit uncertainty instead of silently guessing. The analyzer detects unresolved markers before implementation.
- **Taxonomy-aware gap checking** — The explore skill scans against a lightweight taxonomy (functional scope, data model, edge cases, non-functional, terminology, dependencies) before writing a handoff, surfacing gaps that would cause rework.

## Install

```bash
# Requires Python 3.14+
uv pip install -e .
```

## Workflow

devspec manages a **spec-driven development cycle**:

```
explore → proposal → specs → design → tasks → implement → verify → archive
```

Each change lives in `openspec/changes/<name>/` and produces artifacts in dependency order:

```
proposal  ──→  specs   ──→  tasks
              design  ──↗
```

Specs use **delta format** (ADDED/MODIFIED/REMOVED/RENAMED sections) that get merged into persistent main specs at archive time.

## CLI

```bash
devspec analyze <name> [--json]                   # Cross-artifact consistency analysis
devspec init                                    # Scaffold openspec/ directory
devspec new <name>                              # Create a new change
devspec status --change <name> [--json]         # Artifact completion status
devspec list [--json]                           # List active changes
devspec instructions <artifact> --change <name> [--json]  # Enriched artifact template
devspec validate [<name>]                       # Validate specs or change deltas
devspec archive <name> [--skip-specs] [--yes]   # Archive completed change
devspec context <name> [--max-tokens N]         # Token-budgeted context dump
devspec handoff write <name>                    # Write context bridge (stdin)
devspec handoff read <name>                     # Read handoff + all artifacts
```

### JSON output

`--json` on `status`, `list`, and `instructions` outputs machine-readable JSON for skill consumption:

```bash
$ devspec status --change add-auth --json
{
  "schemaName": "spec-driven-custom",
  "isComplete": false,
  "artifacts": [
    {"id": "proposal", "status": "done", "requiresIds": []},
    {"id": "specs", "status": "ready", "requiresIds": ["proposal"]},
    {"id": "design", "status": "ready", "requiresIds": ["proposal"]},
    {"id": "tasks", "status": "blocked", "requiresIds": ["specs", "design"]}
  ],
  "applyRequires": ["tasks"]
}
```

## Claude Code Skills

Five skills in `skills/` — symlink to `~/.claude/skills/` to activate:

```bash
ln -s $(pwd)/skills/devspec-* ~/.claude/skills/
```

| Skill | Model | Context | Purpose |
|-------|-------|---------|---------|
| `/devspec-explore` | opus | inline | Thinking partner. Writes handoff on transition |
| `/devspec-plan` | opus | inline | Create artifacts in dependency order |
| `/devspec-build` | sonnet | fork | Implement tasks from tasks.md |
| `/devspec-verify` | opus | inline | Verify implementation matches spec |
| `/devspec-archive` | haiku | fork | Archive completed change |

### Skill workflow

```
explore (opus) → plan (opus) → build (sonnet) → verify (opus) → archive (haiku)
 thinking         artifacts      implementation    checking        finalizing
```

Different models for different demands: exploration and verification need deep reasoning (opus), implementation needs fast code generation (sonnet), archival is mechanical (haiku).

### When to use each skill

- **`/devspec-explore`** — You have a vague idea, want to investigate a problem, or need to think through tradeoffs before committing to a plan. Read-only — no code changes. Writes a `.handoff.md` when insights crystallize.
- **`/devspec-plan`** — You know what to build and need formal artifacts (proposal, specs, design, tasks). Can start from a handoff left by explore, or from scratch.
- **`/devspec-build`** — All planning artifacts are done. Time to write code. Works through tasks sequentially, marking each complete.
- **`/devspec-verify`** — Implementation is done (or mostly done). Checks completeness, correctness, and coherence against specs before archiving.
- **`/devspec-archive`** — Verification passed. Syncs delta specs to main specs and moves the change to archive.

### Handoff system

Skills bridge context through `.handoff.md` files:

1. `/devspec-explore` writes a handoff summarizing decisions made during exploration
2. `/devspec-plan` reads the handoff to inform artifact creation
3. `/devspec-build` gets full context via `devspec context <name>` (handoff + all artifacts)

## Architecture

```
src/devspec/
├── core/
│   ├── schema.py          # YAML schema loader + validation
│   ├── graph.py           # Artifact dependency graph (Kahn's toposort)
│   ├── state.py           # Completion detection (file existence + glob)
│   ├── delta_parser.py    # Parse ADDED/MODIFIED/REMOVED/RENAMED sections
│   ├── spec_merge.py      # Apply deltas to main specs
│   ├── analyzer.py        # Cross-artifact semantic consistency checks
│   ├── validator.py       # SHALL/MUST, scenario, cross-section validation
│   ├── instructions.py    # Template enrichment with context/rules
│   ├── archive.py         # Validate → sync specs → move to archive
│   └── handoff.py         # Context bridge for skill transitions
├── commands/              # Click CLI commands (10 commands)
└── data/
    ├── schema.yaml        # Hardcoded spec-driven workflow schema
    └── templates/         # Artifact templates (proposal, spec, design, tasks)
```

### Delta spec format

Changes describe modifications to main specs using delta sections:

```markdown
## ADDED Requirements

### Requirement: User authentication
The system SHALL authenticate users via OAuth2.

#### Scenario: Successful login
- **WHEN** user provides valid credentials
- **THEN** system issues a session token

## MODIFIED Requirements

### Requirement: Rate limiting
The system SHALL enforce rate limits per API key (updated from per-IP).

#### Scenario: Rate limit exceeded
- **WHEN** client exceeds 100 requests/minute
- **THEN** system returns 429

## REMOVED Requirements

### Requirement: Legacy auth endpoint

## RENAMED Requirements

- FROM: `### Requirement: Old Name`
- TO: `### Requirement: New Name`
```

Merge order: RENAMED → REMOVED → MODIFIED → ADDED.

## Development

```bash
uv run pytest tests/ -v       # 198 tests, ~0.2s
uv run devspec --version      # CLI smoke test
uv run ruff check src/ tests/ # Lint
```

## License

MIT
