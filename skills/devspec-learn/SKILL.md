---
name: "devspec-learn"
description: |
  Capture lessons learned from a completed or archived devspec change.
  Use when: "capture lessons", "devspec learn", "what did we learn", "learning from change".
  Reads change artifacts, guides lesson extraction, writes to knowledge base. Runs inline at opus.
disable-model-invocation: true
allowed-tools: Read, Write, Glob, Bash, mcp__devspec__*
---

Capture lessons learned from a completed or archived change.

**Input**: Optionally specify a change name. If omitted, list recently archived changes and prompt for selection.

**Steps**

1. **Select the change**

   If a name is provided, use it. Otherwise:
   - Call `mcp__devspec__devspec_list` to get available changes
   - Also check the archive directory for recently archived changes (in the project's global data store under `changes/archive/`)
   - Use the **AskUserQuestion tool** to let the user select

   Always announce: "Capturing lessons from: <name>"

2. **Read change artifacts**

   Read all available artifacts for the change:
   - proposal.md, design.md, tasks.md
   - Delta specs at `specs/`
   - Any other artifacts present

   For archived changes, look in the project's `changes/archive/<timestamp>-<name>/` directory.

3. **Check for existing learnings**

   Use the `devspec://learnings/{category}` MCP resource to search categories, or read the project's `learnings/` directory for files where the `change` frontmatter field matches the change name.

   **If a learning already exists:**
   - Display the existing learning to the user
   - Use the **AskUserQuestion tool** to ask: "A learning already exists for this change. Update it, create a new one, or skip?"
   - If update: proceed with the existing file
   - If new: proceed with a new file
   - If skip: exit

4. **Guide lesson extraction**

   Based on the change artifacts, prompt the user through these questions:

   - "What was the hardest part of this change? What surprised you?"
   - "If you were doing this again, what would you do differently?"
   - "Did any decisions from the design or specs turn out to be wrong or need revision?"
   - "Are there patterns or anti-patterns worth remembering?"

   Don't ask all questions at once. Ask one at a time and follow up naturally based on the user's responses. Skip questions that don't apply.

5. **Determine category**

   Infer a category from the change content and discussion:
   - `architecture` - structural decisions, module boundaries, API design
   - `testing` - test strategy, coverage gaps, test patterns
   - `performance` - optimization, profiling, scaling
   - `process` - workflow, planning, estimation, communication
   - `tooling` - build systems, CI/CD, developer experience
   - `security` - auth, secrets, vulnerability patterns
   - `debugging` - root cause analysis, diagnostic techniques

   Present the inferred category to the user and let them confirm or change it.

6. **Write the learning file**

   Create the file at `learnings/<category>/<slug>.md` in the project's global data store.

   The slug should be derived from the lesson title in kebab-case.

   Create the category directory if it doesn't exist.

   **File format:**

   ```markdown
   ---
   title: "<concise lesson title>"
   date: <YYYY-MM-DD>
   tags: [<relevant keywords>]
   change: "<change-name>"
   category: "<category>"
   ---

   ## Problem

   <What went wrong or what was challenging -- the situation that led to the lesson>

   ## Lesson

   <The key insight or takeaway -- what was learned>

   ## Prevention

   <How to avoid the problem or apply the lesson in future changes -- optional, omit if not applicable>
   ```

7. **Confirm and summarize**

   ```
   ## Learning Captured

   **Title:** <title>
   **Category:** <category>
   **File:** learnings/<category>/<slug>.md
   **Tags:** <tags>

   This learning will be surfaced by `/devspec-explore` and `/devspec-plan` when
   working on related topics.
   ```

**Guardrails**
- Always read change artifacts before prompting for lessons - ground the conversation in what actually happened
- Don't auto-generate lessons without user input - this is a guided conversation, not an extraction pipeline
- Keep learning files concise - a learning should be readable in under a minute
- Tags should be specific enough to match future searches (e.g., "cli-validation" not just "validation")
- If the user has nothing to capture, that's fine - exit gracefully
