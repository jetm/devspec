---
name: "devspec-plan"
description: |
  Plan a change by creating devspec artifacts (proposal, specs, design, tasks).
  Use when: "plan change", "devspec plan", "create artifacts", "spec out", "new change".
  Creates artifacts in dependency order using templates and instructions from CLI. Runs inline at opus.
---

Plan a change -- create all artifacts needed before implementation.

**Input**: Optionally specify a change name (kebab-case) or a description of what to build. If a handoff exists, read it for context.

**Steps**

1. **Check for handoff context**

   If the user mentions a name or one can be inferred from conversation:
   ```bash
   devspec handoff read <name>
   ```
   If a handoff exists, use it as the starting context. If not, proceed with what the user provided.

   Also check if Claude Code auto memory exists for this project (see `/devspec-memory` skill for path computation). If `MEMORY.md` is missing, briefly suggest: "Consider running `/devspec-memory` to populate project memory for future sessions." Don't block on this.

2. **Create the change**

   If no change exists yet:
   ```bash
   devspec new <name>
   ```
   This scaffolds a change directory in the project's global data store.

   If a change already exists, confirm the user wants to continue it.

3. **Get the artifact build order**
   ```bash
   devspec status "<name>" --json
   ```
   Parse the JSON to understand:
   - `applyRequires`: artifacts needed before implementation
   - `artifacts`: list of all artifacts with status and dependencies

4. **Check for relevant learnings**

   Check the project's learnings directory for relevant prior lessons. The learnings are stored in the global data store under the `learnings/` subdirectory.

   Search YAML frontmatter `tags` and `title` fields for keyword matches against the change's topic.

   If relevant learnings are found, read them and use their insights as additional context when creating artifacts. For example, if a prior learning says "always define error contracts for CLI commands", factor that into the specs.

   Don't force learnings into artifacts if they aren't relevant. If no learnings directory exists, skip this step silently.

5. **Create artifacts in dependency order**

   Loop through artifacts (those with no pending dependencies first):

   a. **For each artifact that is `ready`**:
      - Get instructions:
        ```bash
        devspec instructions <artifact-id> "<name>" --json
        ```
      - The instructions JSON includes:
        - `context`: Project background (constraints for you -- do NOT include in output)
        - `rules`: Artifact-specific rules (constraints for you -- do NOT include in output)
        - `template`: The structure to use for your output file
        - `instruction`: Schema-specific guidance for this artifact type
        - `outputPath`: Where to write the artifact
        - `dependencies`: Completed artifacts to read for context
      - Read any completed dependency files for context
      - Create the artifact file using `template` as the structure
      - Apply `context` and `rules` as constraints -- but do NOT copy them into the file
      - Show brief progress: "Created <artifact-id>"

   b. **Continue until all `applyRequires` artifacts are complete**
      - After creating each artifact, re-run `devspec status "<name>" --json`
      - Check if every artifact ID in `applyRequires` has `status: "done"`
      - Stop when all required artifacts are done

   c. **If an artifact requires user input** (unclear context):
      - Use **AskUserQuestion tool** to clarify
      - Then continue with creation

   For independent artifacts, you may delegate writing to a sonnet subagent via the Task tool to speed things up.

6. **Validate the change**
   ```bash
   devspec validate <name>
   ```
   Fix any issues reported by validation.

7. **Show final status**
   ```bash
   devspec status "<name>"
   ```

**Output**

After completing all artifacts, summarize:
- Change name and location
- List of artifacts created with brief descriptions
- What's ready: "All artifacts created! Ready for implementation."
- Prompt: "Run `/devspec-build <name>` to start implementing."

**Artifact Creation Guidelines**

- Follow the `instruction` field from `devspec instructions` for each artifact type
- The schema defines what each artifact should contain -- follow it
- Read dependency artifacts for context before creating new ones
- Use `template` as the structure for your output file -- fill in its sections
- **IMPORTANT**: `context` and `rules` are constraints for YOU, not content for the file
  - Do NOT copy `<context>`, `<rules>`, `<project_context>` blocks into the artifact
  - These guide what you write, but should never appear in the output

**Guardrails**
- Create ALL artifacts needed for implementation (as defined by schema's `apply.requires`)
- Always read dependency artifacts before creating a new one
- If context is critically unclear, ask the user -- but prefer making reasonable decisions to keep momentum
- If a change with that name already exists, suggest continuing that change instead
- Verify each artifact file exists after writing before proceeding to next
