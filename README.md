# devspec

Spec-driven development workflow engine for Claude Code.

A Python rewrite of OpenSpec's core engine: artifact graph, delta spec parser, spec merge engine, validator, and archive logic. Ships with Claude Code skills for multi-model routing.

## Install

```bash
uv pip install -e .
```

## Usage

```bash
devspec init                          # Scaffold openspec/ directory
devspec new <name>                    # Create a new change
devspec status --change <name>        # Check artifact completion
devspec list                          # List active changes
devspec validate [<name>]             # Validate specs or change
devspec archive <name>                # Archive completed change
devspec instructions <artifact>       # Get enriched artifact instructions
devspec context <name>                # Token-budgeted context dump
devspec handoff write/read <name>     # Context bridge between skills
```

## License

MIT
