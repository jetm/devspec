---
name: "devspec-verify"
description: |
  Verify implementation matches devspec change artifacts.
  Use when: "verify change", "devspec verify", "check implementation", "ready to archive?".
  Checks completeness, correctness, and coherence. Generates verification report. Runs inline at opus.
---

Verify that an implementation matches the change artifacts (specs, tasks, design).

**Input**: Optionally specify a change name. If omitted, check if it can be inferred from conversation context. If vague or ambiguous you MUST prompt for available changes.

**Steps**

1. **If no change name provided, prompt for selection**

   Run `devspec list --json` to get available changes. Use the **AskUserQuestion tool** to let the user select.

   Show changes that have implementation tasks (tasks artifact exists).
   Mark changes with incomplete tasks as "(In Progress)".

   **IMPORTANT**: Do NOT guess or auto-select a change. Always let the user choose.

2. **Check status to understand the schema**
   ```bash
   devspec status --change "<name>" --json
   ```
   Parse the JSON to understand:
   - `schemaName`: The workflow being used
   - Which artifacts exist for this change

3. **Load all artifacts**

   Read all available artifacts from the change directory:
   - proposal.md, design.md, tasks.md
   - Delta specs at `devspec/changes/<name>/specs/`
   - Any other artifacts present

4. **Verify Completeness**

   **Task Completion**:
   - Parse tasks.md checkboxes: `- [ ]` (incomplete) vs `- [x]` (complete)
   - Count complete vs total tasks
   - If incomplete tasks exist: add CRITICAL issue for each

   **Spec Coverage**:
   - If delta specs exist, extract all requirements
   - For each requirement, search codebase for implementation evidence
   - If requirements appear unimplemented: add CRITICAL issue

5. **Verify Correctness**

   **Requirement Implementation Mapping**:
   - For each requirement from delta specs:
     - Search codebase for implementation evidence
     - Assess if implementation matches requirement intent
     - If divergence detected: add WARNING with file paths

   **Scenario Coverage**:
   - For each scenario in delta specs:
     - Check if conditions are handled in code
     - Check if tests exist covering the scenario
     - If scenario appears uncovered: add WARNING

6. **Verify Coherence**

   **Design Adherence**:
   - If design.md exists, extract key decisions
   - Verify implementation follows those decisions
   - If contradiction detected: add WARNING
   - If no design.md: skip, note it was skipped

   **Code Pattern Consistency**:
   - Review new code for consistency with project patterns
   - If significant deviations found: add SUGGESTION

7. **Generate Verification Report**

   ```
   ## Verification Report: <change-name>

   ### Summary
   | Dimension    | Status           |
   |--------------|------------------|
   | Completeness | X/Y tasks, N reqs|
   | Correctness  | M/N reqs covered |
   | Coherence    | Followed/Issues  |
   ```

   **Issues by Priority**:

   1. **CRITICAL** (Must fix before archive):
      - Incomplete tasks
      - Missing requirement implementations
      - Each with specific, actionable recommendation

   2. **WARNING** (Should fix):
      - Spec/design divergences
      - Missing scenario coverage
      - Each with specific recommendation

   3. **SUGGESTION** (Nice to fix):
      - Pattern inconsistencies
      - Minor improvements

   **Final Assessment**:
   - If CRITICAL issues: "X critical issue(s) found. Fix before archiving."
   - If only warnings: "No critical issues. Y warning(s) to consider. Ready for archive."
   - If all clear: "All checks passed. Ready for archive."

**Verification Heuristics**

- **Completeness**: Focus on objective checklist items (checkboxes, requirements list)
- **Correctness**: Use keyword search, file path analysis, reasonable inference -- don't require perfect certainty
- **Coherence**: Look for glaring inconsistencies, don't nitpick style
- **False Positives**: When uncertain, prefer SUGGESTION over WARNING, WARNING over CRITICAL
- **Actionability**: Every issue must have a specific recommendation with file/line references where applicable

**Graceful Degradation**

- If only tasks.md exists: verify task completion only, skip spec/design checks
- If tasks + specs exist: verify completeness and correctness, skip design
- If full artifacts: verify all three dimensions
- Always note which checks were skipped and why
