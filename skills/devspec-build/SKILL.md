---
name: "devspec-build"
description: |
  Implement tasks from a devspec change using parallel agent teams.
  Use when: "build change", "implement tasks", "devspec build", "start implementing".
  Spawns parallel devspec-worker agents for 3+ tasks; sequential for 1-2 tasks.
allowed-tools: Read, Grep, Glob, Bash, Task, mcp__devspec__*, TaskCreate, TaskUpdate, TaskList, TeamCreate, TeamDelete, SendMessage
---

Implement tasks from a devspec change.

**Input**: A change name is required (passed as ``). If not provided, list changes and ask.

**Steps**

1. **Environment pre-flight**

   Call `mcp__devspec__devspec_preflight` to check environment readiness.
   - If errors: surface them to the user before proceeding
   - If warnings only: note them and continue
   - If all ok: proceed silently

2. **Select the change**

   If a name is provided, use it. Otherwise:
   - Call `mcp__devspec__devspec_list` to get available changes
   - Use the **AskUserQuestion tool** to let the user select

   Always announce: "Using change: <name>"

3. **Check status**

   Call `mcp__devspec__devspec_status` with the change name. Parse the result to understand:
   - `schemaName`: The workflow being used
   - Which artifact contains the tasks
   - Current artifact completion status

4. **Read context files**

   Read the tasks file and any other context artifacts (proposal, specs, design) from the change directory using the `devspec://changes/{name}/{artifact}` MCP resource. Understand the full picture before implementing.

5. **Show current progress**

   Display:
   - Schema being used
   - Progress: "N/M tasks complete"
   - Remaining tasks overview

6. **Decide: team vs sequential**

   Count pending tasks (marked `- [ ]` in tasks.md).

   **If 1-2 pending tasks**: implement sequentially (step 7a below).

   **If 3+ pending tasks**: use agent team orchestration (step 7b below).

7a. **Sequential implementation (1-2 tasks)**

   For each pending task:
   - Show which task is being worked on
   - Make the code changes required
   - Keep changes minimal and focused
   - Mark task complete in tasks.md: `- [ ]` -> `- [x]`
   - Continue to next task

   **Pause if:**
   - Task is unclear -> ask for clarification
   - Implementation reveals a design issue -> suggest updating artifacts
   - Error or blocker encountered -> report and wait for guidance
   - User interrupts

   After all tasks complete, proceed to Review & Refactor (step 8).

7b. **Agent team orchestration (3+ tasks)**

   **Phase 1: Analyze dependencies**

   Read tasks.md carefully. For each pending task, determine which other tasks must complete before it can start, based on semantic meaning:
   - If task B references output, files, or components produced by task A -> B depends on A
   - If tasks are in independent areas (different files, different capabilities) -> no dependency
   - If unsure, prefer adding a dependency (safer) over allowing false parallelism

   **Phase 2: Create task list**

   Create a Claude Code TaskList using TaskCreate for each pending task. Set `blockedBy` relationships according to your dependency analysis.

   **Phase 3: Create the team**

   Create an agent team using TeamCreate with a descriptive name (e.g., `build-<change-name>`).

   **Phase 4: Spawn workers**

   For each independent task (no blockedBy, or all blockedBy tasks complete):
   - Spawn a devspec-worker teammate using the Task tool
   - Assign the task to that worker via TaskUpdate
   - Pass each worker **minimal context only**: the change name and their specific task number + description. Do NOT inline artifacts (proposal, specs, design, full task list) in the worker prompt. Workers read their own context via `mcp__devspec__devspec_context('<change-name>')`.

   Workers implement their assigned task and mark it complete via TaskUpdate, then go idle.

   **Phase 5: Coordinate merges and unblock dependents**

   After each worker completes:
   - Merge that worker's worktree changes into the main working tree
   - Check TaskList for newly unblocked tasks
   - Spawn new workers for tasks that just became unblocked

   **Phase 6: Wait for all workers**

   Wait for all tasks to reach `completed` status. Track progress and handle worker failures by reassigning tasks or running them sequentially as fallback.

   **Phase 7: Shutdown the team**

   Send shutdown requests to all teammates via SendMessage with type `shutdown_request`. Delete the team via TeamDelete.

   After all workers complete, proceed to Review & Refactor (step 8).

8. **Review & Refactor (only when all tasks are complete)**

   Skip this phase if the build paused due to a blocker, unclear task, or incomplete work. Only run when every task in tasks.md is marked `- [x]`.

   ### 7a. Slop Detection

   Run before subtractive cleanup. Scan all files modified during the build phase.

   **Tool availability check:**
   ```bash
   command -v ast-grep && echo "ast-grep available" || echo "ast-grep unavailable - using regex fallback"
   ```

   **If ast-grep available:** run structural analysis on modified files:
   ```bash
   ast-grep scan <modified_py_files> <modified_c_files> <modified_sh_files>
   ```
   Collect findings from `ast-grep scan` output. Then also run regex patterns below for patterns not covered by AST rules.

   **If ast-grep unavailable:** run regex patterns only. Note "AST analysis unavailable - using regex fallback" in output.

   **Certainty grading:**

   | Grade | Meaning | Action |
   |-------|---------|--------|
   | HIGH | Deterministic match - safe to auto-remove | Auto-fix during this phase |
   | MEDIUM | Probable issue - needs context to confirm | List with recommendation |
   | LOW | Heuristic signal - may be intentional | Note only, no action |

   **Python regex patterns** (apply to `*.py` modified files):

   | Pattern | Regex | Certainty | Description |
   |---------|-------|-----------|-------------|
   | debug print | `^\s*print\s*\(` | HIGH | Debug print statement |
   | breakpoint | `^\s*breakpoint\s*\(\)` | HIGH | Debugger breakpoint |
   | pdb trace | `pdb\.set_trace\(\)` | HIGH | PDB debugger call |
   | icecream | `^\s*ic\s*\(` | HIGH | icecream debug call |
   | placeholder pass | `^\s*pass\s*$` | MEDIUM | Pass-only function body |
   | ellipsis body | `^\s*\.\.\.\s*$` | MEDIUM | Ellipsis-only function body |
   | NotImplementedError | `raise NotImplementedError` | MEDIUM | Unimplemented placeholder |
   | empty except | `except.*:\s*\n\s*pass` | MEDIUM | Swallowed exception |
   | TODO/FIXME/HACK | `#\s*(TODO\|FIXME\|HACK)\b` | LOW | Leftover marker |
   | commented code block | 3+ consecutive `#` lines with code-like syntax | MEDIUM | Dead commented code |
   | high comment ratio | >50% comment lines in file | LOW | Verbose/boilerplate comments |

   **C/C++ regex patterns** (apply to `*.c`, `*.cpp`, `*.h`, `*.hpp` modified files):

   | Pattern | Regex | Certainty | Description |
   |---------|-------|-----------|-------------|
   | printf debug | `fprintf\s*\(\s*stderr\|printf\s*\("DEBUG` | HIGH | Debug printf |
   | if-0 block | `#if\s+0\b` | HIGH | Disabled code block |
   | assert false | `assert\s*\(\s*false\s*\)` | HIGH | Unconditional assert placeholder |
   | TODO/FIXME | `//\s*(TODO\|FIXME\|HACK)\b` | LOW | Leftover marker |
   | commented block | 3+ consecutive `//` lines with code-like syntax | MEDIUM | Dead commented code |

   **Shell regex patterns** (apply to `*.sh`, `*.bash`, files with bash shebang):

   | Pattern | Regex | Certainty | Description |
   |---------|-------|-----------|-------------|
   | echo debug | `(?i)^\s*echo\s+["']?(DEBUG\|TRACE\|XXX\|FIXME)` | HIGH | Debug echo statement |
   | set -x left on | `^\s*set\s+-x\b` | HIGH | Trace mode left enabled |
   | hardcoded /home | `/home/[a-z]` | MEDIUM | Hardcoded home path |
   | hardcoded /tmp literal | `[^$]/tmp/[a-z]` (not `$TMPDIR`) | MEDIUM | Non-portable temp path |
   | missing shebang safety | First line is `#!/` but no `set -euo pipefail` in first 10 lines | MEDIUM | Missing safety flags |
   | TODO/FIXME | `#\s*(TODO\|FIXME\|HACK)\b` | LOW | Leftover marker |

   **Auto-fix behavior:**
   - HIGH findings: remove them automatically. Do not ask. Report each removal.
   - MEDIUM findings: list in output with specific recommendation. Do not auto-fix.
   - LOW findings: note in output. Take no action.

   **Slop Detection output format:**
   ```
   ### Slop Detection
   Tool: ast-grep + regex  [or: regex fallback (ast-grep unavailable)]

   **HIGH (auto-fixed):**
   - `src/foo.py:42` - debug print removed
   - `src/bar.py:17` - breakpoint() removed

   **MEDIUM (review recommended):**
   - `src/baz.py:88` - empty except block - add error handling or logging

   **LOW (noted):**
   - `src/foo.py` - comment ratio 62% - may indicate AI-generated boilerplate

   Auto-fixed 2 HIGH issues. 1 MEDIUM finding requires review.
   [or: No slop detected.]
   ```

   Only include sections that have findings. Omit empty sections.

   ### 7b. Subtractive Cleanup

   Read through all changes made during implementation. Look for unnecessary code introduced across tasks and trim it.

   **Allowed (subtractive only):**
   - Remove unused code (dead functions, unreachable branches, unused imports/variables)
   - Inline single-use helpers at their call site and remove the function definition
   - Simplify unnecessary abstractions (e.g., a class wrapping a single function, an interface with one implementor)
   - Clean up redundant error handling (e.g., duplicate try/catch, re-raising the same exception)
   - Consolidate duplication introduced across tasks

   **Forbidden:**
   - Add new functionality
   - Change observable behavior
   - Reinterpret specs or tasks
   - Add tests, documentation, or features not in tasks.md
   - Rename or restructure beyond what is needed to remove code

   For each change, preserve identical observable behavior -- same inputs produce same outputs, same errors raised, same side effects.

   **Output:**

   If changes were made, produce a "Review & Refactor" section with both sub-phases:
   ```
   ### Review & Refactor

   #### Slop Detection
   Tool: ast-grep + regex

   **HIGH (auto-fixed):**
   - `src/foo.py:42` - debug print removed

   **MEDIUM (review recommended):**
   - `src/baz.py:88` - empty except block - add error handling or logging

   Auto-fixed 1 HIGH issue. 1 MEDIUM finding requires review.

   #### Subtractive Cleanup
   - Inlined `_build_key()` at single call site in `lookup()` - removed helper
   - Removed unused `format_debug()` - no callers after task 3 refactored logging

   Trimmed 2 items. No tasks modified. No new code added.
   ```

   If no changes were needed in either sub-phase:
   ```
   ### Review & Refactor
   No slop detected. No unnecessary code found. No changes made.
   ```

9. **On completion or pause**

   **If paused**: display progress and explain why. Wait for guidance.

   **If all tasks complete**: run verification automatically.

   Spawn a verification sub-agent using the Task tool:
   - `subagent_type`: `"general-purpose"`
   - `prompt`: `"Read the verification skill at <skills-dir>/devspec-verify/SKILL.md and execute it for change '<change-name>'. Return the full verification report."`

   Where `<skills-dir>` is the same directory this build skill was loaded from (its parent directory).

   Display the verification report to the user. Based on the results:
   - All clear: suggest `/devspec-archive <name>`
   - Issues found: present them for the user to address

**Output During Implementation**

```
## Implementing: <change-name>

Working on task 3/7: <task description>
[...implementation happening...]
Task complete

Working on task 4/7: <task description>
[...implementation happening...]
Task complete
```

**Output On Completion**

```
## Implementation Complete

**Change:** <change-name>
**Progress:** 7/7 tasks complete

### Completed This Session
- [x] Task 1
- [x] Task 2
...

### Review & Refactor

#### Slop Detection
Tool: regex fallback (ast-grep unavailable)
No slop detected.

#### Subtractive Cleanup
- Inlined `_build_key()` at single call site in `lookup()` - removed helper
- Removed unused `format_debug()` - no callers after task 3 refactored logging

Trimmed 2 items. No tasks modified. No new code added.

Running verification...

### Verification Report
<report from verify sub-agent>

Ready for `/devspec-archive <name>`.
```

**Output On Pause**

```
## Implementation Paused

**Change:** <change-name>
**Progress:** 4/7 tasks complete

### Issue Encountered
<description of the issue>

**Options:**
1. <option 1>
2. <option 2>

What would you like to do?
```

**Guardrails**
- Keep going through tasks until done or blocked
- Always read context artifacts before starting
- If task is ambiguous, pause and ask before implementing
- If implementation reveals issues, pause and suggest artifact updates
- Keep code changes minimal and scoped to each task
- Update task checkbox immediately after completing each task
- Pause on errors, blockers, or unclear requirements -- don't guess
- For agent teams: fall through to sequential if team creation fails
