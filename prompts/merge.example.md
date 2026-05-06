# Merge Stage

You are merging the approved PR for **{{ issue.identifier }}**: {{ issue.title }}

**URL:** {{ issue.url }}

## Objective

Merge the PR and move the issue to its terminal state.  This is a short,
mechanical stage — no new code changes.

## Process

1. Set the GitHub host (Salesforce-internal):
   ```
   export GH_HOST=git.soma.salesforce.com
   ```
2. Find the open PR for this issue:
   ```
   gh pr list --head <branch-name>
   ```
3. Verify the PR is approved and CI is passing:
   ```
   gh pr view <number> --json reviewDecision,statusCheckRollup
   ```
4. If CI is failing, investigate briefly.  If it is a flaky test or transient
   failure, re-run the checks.  If it is a real failure, post a `FeedItem` on
   work item `{{ issue.id }}` describing the failure and stop (Concerto will
   route this back through rework).
5. Merge the PR using squash merge:
   ```
   gh pr merge <number> --squash --delete-branch
   ```
6. Post a `## Workpad` `FeedItem` with the merge confirmation (commit SHA,
   PR URL, timestamp).

Concerto moves the GUS work item to its terminal status itself once this
stage finishes — do not change `Status__c` from this prompt.

## Rework run

If this is a rework run (merge was attempted before but failed):

1. Check why the previous merge attempt failed (CI failure, merge conflict, etc.).
2. If there is a merge conflict:
   - Rebase the branch onto `origin/master` and resolve conflicts.
   - Push the updated branch.
   - Wait for CI to pass, then merge.
3. If CI failed:
   - Read the failure logs.
   - If it is a test failure caused by the PR's changes, post details as a
     `FeedItem` and stop (this needs to go back to implementation).
   - If it is a flaky or infrastructure issue, re-run and retry the merge.
4. Post a `## Workpad (rework N)` `FeedItem` with what happened.

## Do NOT

- Make code changes beyond conflict resolution.
- Open new PRs.
- Skip CI checks.
