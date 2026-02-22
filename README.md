# devspec

Spec-driven development workflow engine for Claude Code. Manages the full lifecycle of a change - explore, plan, build, verify, archive - through structured artifacts and multi-model routing. 8 Claude Code skills route each phase to the model that fits: opus for thinking, sonnet for implementation, haiku for cleanup.

Inspired by [OpenSpec](https://github.com/Fission-AI/OpenSpec) and GitHub's [spec-kit](https://github.com/github/spec-kit). Includes a migration tool to convert from OpenSpec's `openspec/` directory format.

## Install

```bash
# Requires Python 3.14+
uv pip install -e .
```

## Workflow

devspec manages a spec-driven development cycle:

```
explore -> plan -> build -> verify -> archive
```

Each change lives in the project's global data store (`~/.local/share/devspec/<project>/changes/<name>/`) and produces artifacts in dependency order:

```
proposal  -->  specs   -->  tasks
              design  --/
```

Specs use **delta format** (ADDED/MODIFIED/REMOVED/RENAMED sections) that get merged into persistent main specs at archive time.

## CLI

```bash
devspec init                                      # Initialize project + global data directory
devspec new <name>                                # Create a new change
devspec status [<name>] [--json]                  # Artifact completion status
devspec list [--json]                             # List active changes
devspec instructions <artifact> [<name>] [--json] # Enriched artifact template
devspec analyze <name> [--json]                   # Cross-artifact consistency analysis
devspec validate [<name>]                         # Validate specs or change deltas
devspec context <name> [--max-tokens N]           # Token-budgeted context dump
devspec handoff write <name>                      # Write context bridge (stdin)
devspec handoff read <name>                       # Read handoff + all artifacts
devspec archive <name> [--skip-specs] [--yes]     # Archive completed change
devspec migrate [--repo PATH]                     # Migrate from openspec/ layout
```

`--json` on `status`, `list`, `instructions`, and `analyze` outputs machine-readable JSON for skill consumption.

## MCP Server

devspec includes an MCP server (`devspec-mcp`) that exposes all operations as structured tool calls over stdio. This is how Claude Code skills interact with devspec.

```bash
devspec-mcp  # Starts MCP server on stdio
```

Add to `.claude/settings.json` to register:

```json
{
  "mcpServers": {
    "devspec": {
      "command": "devspec-mcp"
    }
  }
}
```

### Tools

| Tool | Description |
|------|-------------|
| `devspec_list` | List active changes |
| `devspec_new` | Create a new change |
| `devspec_status` | Artifact completion status |
| `devspec_instructions` | Enriched artifact template |
| `devspec_context` | Token-budgeted context dump |
| `devspec_validate` | Validate specs or change deltas |
| `devspec_analyze` | Cross-artifact consistency analysis |
| `devspec_handoff_read` | Read handoff + all artifacts |
| `devspec_handoff_write` | Write context bridge |
| `devspec_archive` | Archive completed change |
| `devspec_task_mark` | Mark task complete/incomplete by index (MCP-only) |

### Resources

| Resource | Description |
|----------|-------------|
| `devspec://changes/` | List active changes |
| `devspec://changes/{name}/{artifact}` | Read a change artifact |
| `devspec://changes/{name}/specs/{capability}` | Read a delta spec |
| `devspec://specs/{capability}` | Read a main spec |
| `devspec://learnings/{category}` | Read learnings for a category |
| `devspec://schema` | Read the workflow schema |

## Claude Code Skills

8 skills in `skills/` - symlink to `~/.claude/skills/` to activate:

```bash
ln -s $(pwd)/skills/devspec-* ~/.claude/skills/
```

### Core pipeline

| Skill | Model | Purpose |
|-------|-------|---------|
| `/devspec-explore` | opus | Thinking partner. Investigates problems, writes handoff |
| `/devspec-plan` | opus | Create artifacts (proposal, specs, design, tasks) |
| `/devspec-build` | sonnet | Implement tasks from tasks.md |
| `/devspec-verify` | opus | Check implementation against specs |
| `/devspec-archive` | haiku | Archive change, sync delta specs to main |

### Utility skills

| Skill | Model | Purpose |
|-------|-------|---------|
| `/devspec-auto` | opus | Run full pipeline autonomously from a handoff |
| `/devspec-learn` | opus | Capture lessons learned from a change |
| `/devspec-memory` | opus | Generate Claude Code auto memory for a project |

Skills bridge context through `.handoff.md` files: explore writes decisions, plan reads them, and build gets full context via `devspec context`.

---

## Development

```bash
uv run pytest tests/ -v       # Tests
uv run ruff check src/ tests/ # Lint
```

## Architecture

```
src/devspec/
├── core/
│   ├── schema.py          # YAML schema loader + validation
│   ├── graph.py           # Artifact dependency graph (Kahn's toposort)
│   ├── state.py           # Completion detection (file existence + glob)
│   ├── resolve.py         # Change/project name resolution
│   ├── change.py          # Change creation + task checkbox toggling
│   ├── delta_parser.py    # Parse ADDED/MODIFIED/REMOVED/RENAMED sections
│   ├── spec_merge.py      # Apply deltas to main specs
│   ├── analyzer.py        # Cross-artifact semantic consistency checks
│   ├── validator.py       # SHALL/MUST, scenario, cross-section validation
│   ├── instructions.py    # Template enrichment with context/rules
│   ├── archive.py         # Validate -> sync specs -> move to archive
│   └── handoff.py         # Context bridge for skill transitions
├── commands/              # Click CLI commands
├── mcp/
│   ├── server.py          # MCP server entry point (stdio transport)
│   ├── tools.py           # Tool handlers for all devspec operations
│   └── resources.py       # Resource handlers for read-only access
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

## REMOVED Requirements

### Requirement: Legacy auth endpoint

## RENAMED Requirements

- FROM: `### Requirement: Old Name`
- TO: `### Requirement: New Name`
```

Merge order: RENAMED -> REMOVED -> MODIFIED -> ADDED.

## License

MIT
