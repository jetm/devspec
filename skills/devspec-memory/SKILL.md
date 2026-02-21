---
name: "devspec-memory"
description: |
  Generate or refresh Claude Code auto memory for the current project.
  Use when: "devspec memory", "generate memory", "refresh memory", "populate memory", "learn project".
  Reads CLAUDE.md, docs, and codebase structure to create optimized memory files. Runs inline at opus.
---

Generate or refresh Claude Code's auto memory for the current project.

**Input**: Optional focus area (e.g., "api patterns", "testing"). If omitted, generates full memory.

---

## What This Does

Claude Code has a persistent auto memory directory at `~/.claude/projects/<encoded-path>/memory/`.
The file `MEMORY.md` is loaded into every conversation automatically (first 200 lines).
Topic files provide deeper context that Claude can reference when relevant.

This skill reads the project's codebase and generates optimized memory files so Claude Code
starts every session with project-specific knowledge instead of rediscovering it each time.

---

## Steps

### 1. Resolve project paths

Find the project root by locating the `.devspec` marker file (walk parent directories from cwd).
Read the marker to get the project name.

Compute the Claude Code memory path:
- Take the absolute path to the project root directory
- Replace all `/` with `-`
- Drop the leading `-`
- Prefix with `~/.claude/projects/`
- Append `/memory/`

Example: `/home/user/repos/my-project` -> `~/.claude/projects/-home-user-repos-my-project/memory/`

Create the memory directory if it doesn't exist.

### 2. Read existing knowledge sources

Gather information from these sources (skip any that don't exist):

**Priority 1 - Project instructions:**
- `CLAUDE.md` in project root (and any `.claude/` directory)
- Any docs referenced by `file:` links in CLAUDE.md

**Priority 2 - Architecture docs:**
- `docs/` directory - scan for architecture, models, API docs
- `README.md`

**Priority 3 - Code structure:**
- Top-level directory layout
- Key file locations (models, views, routes, configs)
- Package manager files (pyproject.toml, package.json, Cargo.toml, go.mod, etc.)

**Priority 4 - Conventions:**
- Linter/formatter configs (ruff, eslint, prettier, etc.)
- Test configuration and structure
- CI/CD config files (.gitlab-ci.yml, .github/workflows/)

**Priority 5 - Existing memory:**
- Check for existing Serena memories (call `list_memories` if available)
- Check for existing auto memory files (to update rather than overwrite)

Do NOT read every file. Be surgical - read table of contents, READMEs, config files,
and skim key source files for patterns. The goal is to understand the project enough
to write useful memory, not to read the entire codebase.

### 3. Generate MEMORY.md

Write `MEMORY.md` to the memory directory. This is the high-value file - it loads every session.

**Hard constraints:**
- Maximum 190 lines (leave buffer under the 200-line truncation)
- Every line must earn its place - no filler, no obvious information
- Use code blocks and tables sparingly (they consume lines fast)

**Required sections (adapt headings to the project):**

```markdown
# <Project Name> - Claude Code Memory

## What This Project Is
<2-3 sentences: purpose, users, key tech>

## Tech Stack
<Bullet list of framework, language, DB, key libraries>

## Data Model / Architecture
<Core entities and relationships, compact format>

## Key Directories
<File paths that matter most, with one-line descriptions>

## Conventions
<Code style, naming, patterns - only what's non-obvious>

## Commands
<Essential dev commands in a code block>

## Workflow
<Git strategy, deployment, CI/CD - brief>

## Topic Files
<List of topic files with one-line descriptions>
```

**What NOT to include:**
- Anything already in CLAUDE.md (it's loaded too - don't duplicate)
- Generic knowledge (how Django works, what pytest does)
- Full API endpoint lists (put in a topic file)
- Deployment details (put in a topic file if complex)

**Key principle:** MEMORY.md answers "what do I need to know to start working?"
Topic files answer "what do I need to know to work on X specifically?"

### 4. Generate topic files

Create 2-5 topic files based on what's most useful for the project. Common patterns:

| Filename | When to create | Content |
|----------|----------------|---------|
| `api-patterns.md` | Web APIs exist | Endpoint structure, auth flow, pagination, viewset locations |
| `data-model.md` | Complex data model | Entity details, relationships, state machines, key fields |
| `testing.md` | Non-trivial test setup | Test structure, fixtures, markers, how to run subsets |
| `deployment.md` | Complex deployment | Environments, CI/CD, config management |
| `domain-concepts.md` | Domain-heavy project | Business logic, domain terms, workflow rules |

**Topic file guidelines:**
- No line limit, but keep under 100 lines each
- Include file paths with line numbers where practical
- Focus on "where is X" and "how does X work" patterns
- Include gotchas and edge cases

### 5. Cross-reference with CLAUDE.md

After generating memory files, quickly compare with CLAUDE.md:
- Remove anything from memory that duplicates CLAUDE.md content
- If CLAUDE.md references docs that aren't summarized in memory, consider adding key points
- Memory should complement CLAUDE.md, not repeat it

### 6. Report results

```
## Memory Generated

**Project:** <name>
**Memory path:** <full path>

### Files created/updated:
- MEMORY.md (<line count> lines)
- <topic-file>.md (<line count> lines)
- ...

### Sources used:
- CLAUDE.md
- <docs read>
- <configs read>

### Coverage:
- [x] Project overview and tech stack
- [x] Key directories and file locations
- [x] Code conventions
- [x] Development commands
- [ ] <anything skipped and why>

Run `/devspec-memory` again anytime to refresh after significant changes.
```

---

## Refresh Mode

When memory files already exist, this skill operates in refresh mode:

1. Read existing memory files first
2. Compare with current project state
3. Update sections that are stale (new files, changed structure, new patterns)
4. Preserve any manually-added notes (sections not matching generated patterns)
5. Report what changed

---

## Guardrails

- **Don't read the entire codebase** - Be surgical. Read configs, READMEs, key source files.
- **Don't duplicate CLAUDE.md** - Memory complements it, doesn't replace it.
- **Don't include secrets** - Skip .env files, credentials, API keys.
- **Don't over-generate** - 2-5 topic files is plenty. More files = more noise.
- **Don't be generic** - Every line should be specific to THIS project.
- **Do respect the 190-line limit** - MEMORY.md gets truncated at 200 lines. Count carefully.
- **Do include file paths** - "Models are in X" is more useful than "there's a models file somewhere."
- **Do note gotchas** - Edge cases, naming inconsistencies, non-obvious patterns save real time.
