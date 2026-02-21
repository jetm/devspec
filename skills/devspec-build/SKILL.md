---
name: "devspec-build"
description: |
  Implement tasks from a devspec change.
  Use when: "build change", "implement tasks", "devspec build", "start implementing".
  Works through tasks sequentially, makes code changes, marks complete. Runs on sonnet via subagent.
context: fork
agent: sonnet-worker
---

Implement tasks from a devspec change.

**Input**: A change name is required (passed as `$1`). If not provided, list changes and ask.

**Steps**

1. **Select the change**

   If a name is provided, use it. Otherwise:
   - Run `devspec list --json` to get available changes
   - Use the **AskUserQuestion tool** to let the user select

   Always announce: "Using change: <name>"

2. **Check status**
   ```bash
   devspec status --change "<name>" --json
   ```
   Parse the JSON to understand:
   - `schemaName`: The workflow being used
   - Which artifact contains the tasks
   - Current artifact completion status

3. **Read context files**

   Read the tasks file and any other context artifacts (proposal, specs, design) listed in the change directory. Understand the full picture before implementing.

4. **Show current progress**

   Display:
   - Schema being used
   - Progress: "N/M tasks complete"
   - Remaining tasks overview

5. **Implement tasks (loop until done or blocked)**

   For each pending task (marked `- [ ]` in tasks.md):
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

6. **Review & Refactor (only when all tasks are complete)**

   Skip this phase if the build paused due to a blocker, unclear task, or incomplete work. Only run when every task in tasks.md is marked `- [x]`.

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

   If changes were made, produce a "Review & Refactor" section listing each trimmed item with a brief rationale:
   ```
   ### Review & Refactor
   - Inlined `_build_key()` at single call site in `lookup()` — removed helper
   - Removed unused `format_debug()` — no callers after task 3 refactored logging
   - Consolidated duplicate validation in `save()` and `update()` into shared path

   Trimmed 3 items. No tasks modified. No new code added.
   ```

   If no changes were needed:
   ```
   ### Review & Refactor
   No unnecessary code found. No changes made.
   ```

7. **On completion or pause, show status**

   Display:
   - Tasks completed this session
   - Overall progress: "N/M tasks complete"
   - If all done: suggest verify and archive
   - If paused: explain why and wait for guidance

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
- Inlined `_build_key()` at single call site in `lookup()` — removed helper
- Removed unused `format_debug()` — no callers after task 3 refactored logging

Trimmed 2 items. No tasks modified. No new code added.

All tasks complete! Run `/devspec-verify <name>` to check, then `/devspec-archive <name>`.
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
