---
name: "devspec-archive"
description: |
  Archive a completed devspec change.
  Use when: "archive change", "devspec archive", "finalize change", "done with change".
  Checks completion, prompts for spec sync, archives. Runs inline.
disable-model-invocation: true
allowed-tools: Read, Bash, Glob, mcp__devspec__*
---

Archive a completed change.

**Input**: Optionally specify a change name. If omitted, prompt for selection.

**Steps**

1. **If no change name provided, prompt for selection**

   Call `mcp__devspec__devspec_list` to get available changes.

   Show only active changes (not already archived). Include the schema and status for each.

   **IMPORTANT**: Do NOT guess or auto-select a change. Always let the user choose.

2. **Check completion status**

   Call `mcp__devspec__devspec_status` with the change name.

   Parse the result:
   - `schemaName`: The workflow being used
   - `isComplete`: Whether all artifacts are done
   - `artifacts`: List with each artifact's `id` and `status`

   **If `isComplete` is false:**
   - List the incomplete artifacts by name
   - Warn the user and ask if they want to proceed anyway
   - If they confirm, pass `force=True` to the archive call

3. **Ask about spec sync**

   The `devspec_archive` tool syncs delta specs to main specs by default.
   Ask the user if they want to sync specs or skip.

   - If sync: call `devspec_archive` with default `skip_specs=False`
   - If skip: call `devspec_archive` with `skip_specs=True`
   - If no delta specs exist in the change: skip this question, use default

   To check for delta specs, glob `specs/` under the change directory in the project's global data store (`~/.local/share/devspec/<project>/changes/<name>/specs/`).

4. **Perform the archive**

   Call `mcp__devspec__devspec_archive` with the change name and the `skip_specs`/`force` flags determined above.

5. **Display summary and offer next steps**

   ```
   ## Archive Complete

   **Change:** <change-name>
   **Schema:** <schema-name>
   **Archived to:** <archivePath from response>
   **Specs:** Synced / No delta specs / Sync skipped

   All done. Optional next step: `/devspec-learn <change-name>` to capture lessons.
   ```

**Guardrails**
- Always prompt for change selection if not provided
- Use `devspec_status` for all completion checking - don't read files manually
- Don't block archive on warnings - inform, confirm, then proceed with `force=True`
- Show clear summary of what happened
- Suggest `/devspec-learn` as a follow-up, don't inline the learning flow
