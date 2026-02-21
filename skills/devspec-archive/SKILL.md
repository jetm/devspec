---
name: "devspec-archive"
description: |
  Archive a completed devspec change.
  Use when: "archive change", "devspec archive", "finalize change", "done with change".
  Checks completion, prompts for spec sync, archives. Runs on haiku via subagent.
context: fork
agent: haiku-worker
---

Archive a completed change.

**Input**: Optionally specify a change name. If omitted, prompt for selection.

**Steps**

1. **If no change name provided, prompt for selection**

   Run `devspec list --json` to get available changes. Use the **AskUserQuestion tool** to let the user select.

   Show only active changes (not already archived).
   Include the schema used for each change if available.

   **IMPORTANT**: Do NOT guess or auto-select a change. Always let the user choose.

2. **Check artifact completion status**

   Run `devspec status --change "<name>" --json` to check artifact completion.

   Parse the JSON to understand:
   - `schemaName`: The workflow being used
   - `artifacts`: List of artifacts with their status (`done` or other)

   **If any artifacts are not `done`:**
   - Display warning listing incomplete artifacts
   - Use **AskUserQuestion tool** to confirm user wants to proceed
   - Proceed if user confirms

3. **Check task completion status**

   Read the tasks file to check for incomplete tasks.

   Count tasks marked with `- [ ]` (incomplete) vs `- [x]` (complete).

   **If incomplete tasks found:**
   - Display warning showing count of incomplete tasks
   - Use **AskUserQuestion tool** to confirm user wants to proceed
   - Proceed if user confirms

   **If no tasks file exists:** Proceed without task-related warning.

4. **Prompt for spec sync**

   Check for delta specs in the change's `specs/` directory. If none exist, skip to archive.

   **If delta specs exist:**
   - Note their presence to the user
   - Ask if they want to sync specs to main before archiving
   - If yes, prompt user to run sync manually or proceed without
   - Proceed to archive regardless of choice

5. **Perform the archive**

   ```bash
   devspec archive <name>
   ```

6. **Offer learning capture**

   After a successful archive, prompt the user to capture lessons from the change.

   Use the **AskUserQuestion tool** to ask: "Capture lessons from this change? (This saves insights to the project's learnings directory for future reference)"

   **If the user accepts:**
   - Run the learning capture flow inline (same as `/devspec-learn`):
     - Read the archived change's artifacts from the archive directory
     - Guide the user through lesson extraction (see `/devspec-learn` skill for the full flow)
     - Write the learning file to the project's `learnings/<category>/<slug>.md` directory
   - Then proceed to the summary

   **If the user declines:**
   - Proceed directly to the summary

7. **Display summary**

   ```
   ## Archive Complete

   **Change:** <change-name>
   **Schema:** <schema-name>
   **Archived to:** changes/archive/YYYY-MM-DD-<name>/
   **Specs:** Synced / No delta specs / Sync skipped
   **Learnings:** Captured / Skipped

   All artifacts complete. All tasks complete.
   ```

**Guardrails**
- Always prompt for change selection if not provided
- Use artifact status from CLI for completion checking
- Don't block archive on warnings -- just inform and confirm
- Show clear summary of what happened
- Learning capture is optional -- don't pressure, just offer
