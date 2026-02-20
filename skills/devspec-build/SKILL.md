---
name: "devspec-build"
description: |
  Implement tasks from a devspec change.
  Use when: "build change", "implement tasks", "devspec build", "start implementing".
  Works through tasks sequentially, makes code changes, marks complete. Runs on sonnet via subagent.
context: fork
agent: sonnet-worker
---

!`devspec context $1`

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

6. **On completion or pause, show status**

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
