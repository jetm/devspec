---
name: "devspec-verify"
description: |
  Verify implementation matches devspec change artifacts.
  Use when: "verify change", "devspec verify", "check implementation", "ready to archive?".
  Checks completeness, correctness, and coherence. Generates verification report. Runs inline at opus.
allowed-tools: Read, Grep, Glob, Bash, Task, mcp__devspec__*
---

Verify that an implementation matches the change artifacts (specs, tasks, design).

**Input**: Optionally specify a change name. If omitted, check if it can be inferred from conversation context. If vague or ambiguous you MUST prompt for available changes.

**Steps**

1. **If no change name provided, prompt for selection**

   Call `mcp__devspec__devspec_list` to get available changes. Use the **AskUserQuestion tool** to let the user select.

   Show changes that have implementation tasks (tasks artifact exists).
   Mark changes with incomplete tasks as "(In Progress)".

   **IMPORTANT**: Do NOT guess or auto-select a change. Always let the user choose.

2. **Check status to understand the schema**

   Call `mcp__devspec__devspec_status` with the change name. Parse the result to understand:
   - `schemaName`: The workflow being used
   - Which artifacts exist for this change

3. **Load all artifacts**

   Read all available artifacts from the change directory:
   - proposal.md, design.md, tasks.md
   - Delta specs in the change's `specs/` directory
   - Any other artifacts present

4. **Pre-Flight Checks**

   Run deterministic checks before LLM analysis. If a tool fails or exceeds 60s, skip it and note in results - never block LLM analysis.

   **Test Runner** - detect and run in order:
   - `pyproject.toml` + `uv` available → `uv run pytest` (capture pass/fail count + exit code)
   - `pytest` on PATH → `pytest` (capture pass/fail count + exit code)
   - `Makefile` with `test` target → `make test` (capture exit code)
   - `Cargo.toml` exists → `cargo test` (capture exit code + summary)
   - `go.mod` exists → `go test ./...` (capture exit code + summary)
   - None found → note "No test runner detected"

   **Linter** - run only linters already configured in the project, on modified files only:
   - `[tool.ruff]` in `pyproject.toml` or `ruff.toml` exists → `ruff check <modified .py files>`
   - Modified files include `.sh` or `.bash` and `shellcheck` on PATH → `shellcheck <each file>`
   - Modified files include `.c`, `.cpp`, `.h`, `.hpp` and `gcc`/`clang` available → syntax-only check (`-fsyntax-only`)

   **AST Structural Checks** - run when ast-grep is available:
   - Verify ast-grep: `sg --version 2>&1 | grep -q ast-grep` (note: `/usr/bin/sg` on Linux is `newgrp`, not ast-grep)
   - Detect modified file languages; find matching rule files in `src/devspec/data/patterns/<lang>/`
   - Run each rule file individually: `for rule in src/devspec/data/patterns/<lang>/*.yml; do sg scan --rule "$rule" <modified files>; done`
   - If `sg` is not ast-grep or not on PATH → skip and note "AST checks skipped (ast-grep not available)"

   **Certainty Grading** - apply to all findings:
   - **HIGH**: definitive failure - test suite exits non-zero, syntax error, linter error
   - **MEDIUM**: warning or probable issue - linter warning, ast-grep warning-level match
   - **LOW**: heuristic suggestion - pattern-based, needs context to confirm

5. **Verify Completeness**

   **Task Completion**:
   - Parse tasks.md checkboxes: `- [ ]` (incomplete) vs `- [x]` (complete)
   - Count complete vs total tasks
   - If incomplete tasks exist: add CRITICAL issue for each

   **Spec Coverage**:
   - If delta specs exist, extract all requirements
   - For each requirement, search codebase for implementation evidence
   - If requirements appear unimplemented: add CRITICAL issue

6. **Verify Correctness**

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

7. **Verify Coherence**

   **Design Adherence**:
   - If design.md exists, extract key decisions
   - Verify implementation follows those decisions
   - If contradiction detected: add WARNING
   - If no design.md: skip, note it was skipped

   **Code Pattern Consistency**:
   - Review new code for consistency with project patterns
   - If significant deviations found: add SUGGESTION

8. **Domain Review**

   Dispatch specialized review agents for domain-specific analysis (security, performance, architecture).

   **Discovery**:
   - Glob `.claude/agents/review/*.md` to find review agent files
   - If the directory does not exist or is empty, skip this phase and note it was skipped in the report

   **Prepare context for agents**:
   - Generate a code diff for the change (files modified during implementation)
   - Summarize the change's artifacts (proposal, specs, design) into a brief context block

   **Dispatch agents in parallel**:
   - For each agent file found, dispatch it as a parallel Task sub-agent using the Task tool
   - Pass each agent: the code diff and artifact summary as input
   - Each agent file contains its own system prompt defining what to look for and how to report

   **Collect results**:
   - Wait for all agents to complete
   - If an agent fails or times out, log a WARNING with the agent name and continue with remaining agents

   **Note**: Agent findings are integrated into the report in step 9.

9. **Generate Verification Report**

   ```
   ## Verification Report: <change-name>

   ### Pre-Flight Results
   | Check         | Status  | Certainty | Details          |
   |---------------|---------|-----------|------------------|
   | Tests         | PASS/FAIL/SKIP | HIGH | <summary> |
   | Linter        | PASS/FAIL/SKIP | HIGH/MEDIUM | <findings> |
   | AST Checks    | PASS/FAIL/SKIP | MEDIUM/LOW | <findings> |
   ```

   Notes for skipped checks: "Skipped - <tool> not available" or "Skipped - <tool> timed out (>60s)".

   ```
   ### Summary
   | Dimension     | Status           |
   |---------------|------------------|
   | Completeness  | X/Y tasks, N reqs|
   | Correctness   | M/N reqs covered |
   | Coherence     | Followed/Issues  |
   | Domain Review | N agents, M findings |
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

   ### Domain Review

   For each review agent that ran, include a subsection:

   ```
   #### <agent-name>
   <findings or "No issues found. Agent ran cleanly.">
   ```

   If an agent failed, note it:
   ```
   #### <agent-name>
   WARNING: Agent failed to complete. Error: <reason>
   ```

   If no agents were found:
   ```
   #### Domain Review
   Skipped - no review agents found in `.claude/agents/review/`.
   ```

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
