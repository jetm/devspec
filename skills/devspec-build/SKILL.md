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

1. **Select the change**

   If a name is provided, use it. Otherwise:
   - Call `mcp__devspec__devspec_list` to get available changes
   - Use the **AskUserQuestion tool** to let the user select

   Always announce: "Using change: <name>"

2. **Check status**

   Call `mcp__devspec__devspec_status` with the change name. Parse the result to understand:
   - `schemaName`: The workflow being used
   - Which artifact contains the tasks
   - Current artifact completion status

3. **Read context files**

   Read the tasks file and any other context artifacts (proposal, specs, design) from the change directory using the `devspec://changes/{name}/{artifact}` MCP resource. Understand the full picture before implementing.

4. **Show current progress**

   Display:
   - Schema being used
   - Progress: "N/M tasks complete"
   - Remaining tasks overview

5. **Decide: team vs sequential**

   Count pending tasks (marked `- [ ]` in tasks.md).

   **If 1-2 pending tasks**: implement sequentially (step 6a below).

   **If 3+ pending tasks**: use agent team orchestration (step 6b below).

6a. **Sequential implementation (1-2 tasks)**

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

   After all tasks complete, proceed to Review & Refactor (step 7).

6b. **Agent team orchestration (3+ tasks)**

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

   After all workers complete, proceed to Review & Refactor (step 7).

7. **Review & Refactor (only when all tasks are complete)**

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
   - Inlined `_build_key()` at single call site in `lookup()` - removed helper
   - Removed unused `format_debug()` - no callers after task 3 refactored logging
   - Consolidated duplicate validation in `save()` and `update()` into shared path

   Trimmed 3 items. No tasks modified. No new code added.
   ```

   If no changes were needed:
   ```
   ### Review & Refactor
   No unnecessary code found. No changes made.
   ```

8. **On completion or pause**

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
