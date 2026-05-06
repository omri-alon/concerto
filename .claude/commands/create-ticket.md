# Create Ticket

Guide the user through creating a well-structured GUS work item with acceptance criteria and implementation context, ready for agent execution.

## Process

### Step 1: Get the work item

Ask the user:
> What's the GUS work item identifier? (e.g., W-12345678)
> If you haven't created one yet, create a blank work item in GUS first and give me the W-number.

Once you have the identifier, use the `sfcli:gus` skill (or `sf data query --target-org gus`) to fetch the current work item details:

```
sf data query --target-org gus --query "SELECT Id, Name, Subject__c, Status__c, Type__c, Priority__c, Details__c, Details_and_Steps_to_Reproduce__c, Description__c, Scrum_Team__r.Name, Sprint__r.Name FROM ADM_Work__c WHERE Name = 'W-XXXXXXXX'" --json
```

### Step 1.5: Load target repo context

**Critical:** the cwd is the Concerto orchestrator repo, not the repo the work item targets. Before reasoning about the work, load context for the actual target repo.

1. Read `workflow.yaml` from cwd (fall back to `workflow.example.yaml` only if `workflow.yaml` is missing — and warn the user). Parse it.

2. **Pick the project:**
   - Single-project YAML (top-level `tracker`/`workspace`/`hooks`): use that.
   - Multi-project YAML (`projects:` list): match the entry whose `tracker.scrum_team` equals the `Scrum_Team__r.Name` from Step 1 (or its Id). If none match, list the project names and ask the user which one applies.

3. **Locate the target repo on disk.** From the resolved project, expand `workspace.root` (`~` and `$VAR`). Look for any existing workspace subdirectory under it that is a git checkout of the target repo. Prefer one that is clean and on the default branch.
   - If at least one exists: pick one and read `README.md`, `CLAUDE.md`, `AGENTS.md` (whichever are present, up to a couple of thousand lines total). Note the repo URL from `git remote -v`.
   - If none exists: extract the clone URL from `hooks.after_create` (e.g. the `git clone …` line) and tell the user no workspace is checked out yet. Ask whether to (a) clone into a temp dir for context, or (b) have them point at an existing local checkout.

4. **State what you loaded.** Briefly tell the user: target repo, path used, and which docs you read. Anchor all subsequent research (Step 3) and implementation notes (Step 5) in *that* repo, not the orchestrator repo.

### Step 2: Understand the goal

If the work item already has a description (`Details__c`, `Details_and_Steps_to_Reproduce__c`, or `Description__c` — prefer in that order), read it and summarise your understanding back to the user. Ask if anything is missing.

If the work item has no description or a minimal one, ask these questions one at a time (wait for each answer before asking the next):

1. **What are we building?** — Describe the feature, fix, or change in one sentence.
2. **Why?** — What problem does this solve or what value does it add?
3. **Where in the codebase?** — Which areas, packages, or apps are affected?
4. **Are there designs?** — Figma links, screenshots, or visual references?
5. **Are there dependencies?** — Does this depend on other work items? Any API changes needed?
6. **What's out of scope?** — What is explicitly NOT included in this work item?

### Step 3: Research and context

Based on the answers, do targeted research **in the target repo loaded in Step 1.5** (not the orchestrator repo):
- Read relevant existing code that will be modified
- Check for related documentation, specs, or decision records
- Look at similar completed work for patterns to follow

If you have not loaded a target-repo checkout, stop and resolve Step 1.5 first — research against the wrong repo is worse than no research.

Summarise what you found and confirm the approach with the user.

### Step 4: Generate acceptance criteria

Based on the conversation, generate a structured acceptance criteria JSON block:

```json
{
  "criteria": [
    { "description": "Description of what must be true", "verified": false },
    { "description": "Another requirement", "verified": false }
  ]
}
```

Guidelines for good criteria:
- Each criterion is independently verifiable — one thing, not compound statements
- Include both functional requirements (what it does) and quality requirements (tests, types, architecture)
- Always include: typecheck/build passes with no errors
- Always include: all existing tests pass
- If UI changes: include design accuracy and accessibility criteria
- If new logic: include "Unit tests cover the new logic"
- Prefer "X renders correctly at mobile breakpoint" over "X looks good" — be specific

Present the criteria to the user for review. Add, remove, or modify based on feedback.

### Step 5: Generate the work item description

GUS description fields are HTML, not markdown. Compose the content as HTML; the agent reading it later understands either, but Lightning renders HTML cleanly.

Structure (HTML form):

```html
<h2>Summary</h2>
<p>[One paragraph describing what this work item delivers]</p>

<h2>Context</h2>
<p>[Why this is needed, any relevant background]</p>

<h2>Scope</h2>
<p><b>In scope:</b></p>
<ul>
  <li>[list of things included]</li>
</ul>
<p><b>Out of scope:</b></p>
<ul>
  <li>[list of things explicitly excluded]</li>
</ul>

<h2>Implementation Notes</h2>
<ul>
  <li>[Key files to modify]</li>
  <li>[Relevant patterns to follow]</li>
  <li>[Any technical considerations or gotchas]</li>
</ul>

<h2>Acceptance Criteria</h2>
<pre>
{
  "criteria": [
    { "description": "...", "verified": false }
  ]
}
</pre>

<h2>References</h2>
<ul>
  <li>[Links to Figma, docs, related work items, PRs]</li>
</ul>
```

### Step 6: Update the GUS work item

Show the user the complete description and ask for approval. Once approved:

1. Update the work item via the `sf` CLI. Bug records typically use `Details_and_Steps_to_Reproduce__c`; user stories typically use `Details__c`. Confirm the type from Step 1 and write to the appropriate field. Use a heredoc/file to keep the HTML intact:

   ```bash
   # Write the HTML to a temp file first, then reference it via --values-file
   sf data update record --target-org gus \
     --sobject ADM_Work__c \
     --where "Name='W-XXXXXXXX'" \
     --values "Details__c='<html-here-with-escaped-quotes>'"
   ```

   For long bodies, prefer building a JSON file and using `sf data update record` with `--values-file` to avoid quoting issues.

2. Confirm the update was successful by re-querying the record.
3. Report: "Work item [W-XXXXXXXX] is ready for agent execution. Move it to **New** when you want an agent to pick it up."

   (If your `workflow.yaml` configures a different `gus_statuses.todo` value than `New`, mention that one instead.)

## Tips

- Keep criteria atomic — one thing per criterion
- Reference specific files and components when possible
- If the user mentions something that should be a separate work item, note it but keep this one focused
- The acceptance criteria JSON block is machine-readable — Concerto agents are instructed to verify each criterion before moving the work item to **Ready for Review**
- GUS Type__c values: `Bug`, `User Story`, `Investigation`, `Test Failure`, `Todo` — make sure the work item's type matches the nature of the change before generating the description
