# Implementation Stage

You are implementing the solution for **{{ issue.identifier }}**: {{ issue.title }}

**Current status:** {{ issue.state }}
**Labels:** {{ issue.labels }}
**URL:** {{ issue.url }}

## Issue description

{% if issue.description %}
{{ issue.description }}
{% else %}
No description provided.
{% endif %}

## Objective

Implement the solution, create a PR on Salesforce-internal GitHub
(`git.soma.salesforce.com`), and ensure it passes all quality checks.

## First run

1. Read the `## Investigation` summary from the GUS Chatter feed (see global
   instructions — query `FeedItem` by `ParentId`).
2. Read the relevant source files identified in the investigation.
3. Create a feature branch from `master` (this repo's default branch is
   `master`, not `main`):
   ```
   git checkout -b {{ issue.identifier | lower }}-<short-description> origin/master
   ```
4. Implement the changes with clean, logical commits.
5. Run the full quality suite:
   - Build / type-check (`mvn install` or equivalent)
   - All tests (`mvn test` or equivalent)
   - Lint, if defined
6. Fix any failures before proceeding.
7. Push the branch and create a PR on Salesforce-internal GitHub:
   ```
   export GH_HOST=git.soma.salesforce.com
   git push -u origin HEAD
   cat > /tmp/pr-body.md <<'EOF'
   <PR description: what changed, why, how it was tested, link back to GUS>
   EOF
   gh pr create --title "@{{ issue.identifier }} <concise title>" \
                --body-file /tmp/pr-body.md \
                --base master
   ```
   The title MUST start with `@{{ issue.identifier }}` per the project's CLAUDE.md.
8. Post a `FeedItem` on work item `{{ issue.id }}` linking the PR (URL from
   `gh pr view <number> --json url -q .url`) so reviewers can find it.
9. Post a `## Workpad` FeedItem with: what was done, what was tested, any
   known limitations.

## Rework run

If this is a rework run (a branch and PR already exist):

1. Make sure `GH_HOST` is set:
   ```
   export GH_HOST=git.soma.salesforce.com
   ```
2. Find the existing PR:
   ```
   gh pr list --head <branch-name>
   ```
3. Read review comments and requested changes — both on GitHub:
   ```
   gh pr view <number> --comments
   ```
   and on the GUS work item Chatter feed (most recent `FeedItem` records that
   are not Concerto tracking markers).
4. Address each piece of feedback specifically.
5. Run the full quality suite again.
6. Push new commits to the existing branch (do not force-push).
7. Post a comment on the GitHub PR summarising the rework:
   - Which review comments were addressed
   - What was modified
   - Any decisions or trade-offs
8. Post a `## Workpad (rework N)` FeedItem describing what changed.

## Quality bar

Before finishing, verify:

- [ ] All tests pass
- [ ] Build / type-check is clean
- [ ] No lint errors
- [ ] All acceptance criteria from the GUS work item description met
- [ ] PR created (or updated) on `git.soma.salesforce.com` with the
      `@{{ issue.identifier }}` prefix in the title
- [ ] PR URL posted as a Chatter `FeedItem` on this work item
- [ ] `## Workpad` Chatter `FeedItem` posted with completion summary
