# ast-grep Pattern Rules

Structural pattern matching rules for [ast-grep](https://ast-grep.github.io/) (`sg` CLI). Used by devspec skills to detect code quality issues before LLM analysis.

## Directory Structure

```
patterns/
  python/        Python rules
    debug.yml      print, breakpoint, pdb, ic
    placeholder.yml  pass-only functions, ellipsis bodies, NotImplementedError
    dead-code.yml    empty except blocks, bare except
  c/             C/C++ rules
    debug.yml      printf, fprintf(stderr), cout/cerr
    placeholder.yml  assert(false), TODO throws
    dead-code.yml    #if 0 blocks, empty catch
  shell/         Shell/Bash rules
    debug.yml      echo debug, set -x, set -v
    quality.yml    unquoted variables, unquoted command substitution
```

## Rule File Format

Each `.yml` file contains a `rules` list. Each rule has:

```yaml
rules:
  - id: unique-rule-id          # Unique identifier
    language: Python             # Python | C | Cpp | Bash
    rule:
      pattern: print($$$ARGS)   # Pattern match (or kind/has for structural)
    message: "Human-readable description"
    severity: error | warning    # error = HIGH certainty, warning = MEDIUM
    note: |                      # Optional explanation
      Additional context for the developer.
```

### Pattern Types

- **`pattern:`** - Match code syntax directly (e.g., `print($$$ARGS)` matches any print call)
- **`kind:` + `has:`** - Match AST node types structurally (e.g., function with only `pass` body)
- **`any:`** - Match any of multiple patterns
- **`regex:`** - Match node text against a regex

Use `$$$` for variadic arguments (zero or more), `$` for single captures.

## How to Add New Rules

1. Create or edit a `.yml` file in the appropriate language directory
2. Follow the format above. Use `pattern:` for simple matches, `kind:`/`has:` for structural
3. Set `severity: error` for definitive issues (HIGH certainty), `severity: warning` for probable issues (MEDIUM)
4. Test with: `sg scan --rule <file.yml> <target_files>`

## How Skills Consume Rules

Skills invoke `sg scan` via Bash during review phases:

```bash
# Check if ast-grep is available (note: /usr/bin/sg on Linux is newgrp, not ast-grep)
which sg && echo "available" || echo "unavailable"

# Run all rules for a language on modified files
for rule in src/devspec/data/patterns/python/*.yml; do sg scan --rule "$rule" modified_file.py; done

# Run a specific rule file
sg scan --rule src/devspec/data/patterns/python/debug.yml src/
```

When `sg` is not available, skills fall back to regex-based pattern matching defined inline in the skill prompt.
