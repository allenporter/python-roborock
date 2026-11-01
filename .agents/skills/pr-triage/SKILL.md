---
name: pr-triage
description: >-
  Assess open pull requests and review queue state in python-roborock, optionally syncing the local workspace with upstream/main. Use when asked what needs to be reviewed, to triage open PRs, or to sync and check the review backlog.
---

# PR Triage & Review Queue Skill

Use this skill when assessing open pull requests, checking which PRs need initial review or re-review, or syncing the workspace before starting a review session.

Once the user selects a specific PR to review, switch to the [Code Review Skill](../code-review/SKILL.md).

---

## Workflow

1. **Optional Workspace Sync**:
   If the user asks to sync (e.g., "sync and check reviews") or the workspace is a clean review branch behind `upstream/main`:
   - Verify clean working tree (`git status --short`). Do **not** fast-forward or rebase if uncommitted local changes exist unless asked.
   - Fetch remotes (`git fetch --all --prune`).
   - Fast-forward the local tracking branch to `upstream/main` (or `origin/main` if `upstream` is absent): `git merge --ff-only upstream/main`.

2. **Query Open PR & Review Metadata**:
   Identify the current GitHub user and fetch open PR state in a single `gh` pass so no per-PR polling is needed:
   ```bash
   REVIEWER=$(gh api user --jq .login)
   gh pr list --repo Python-roborock/python-roborock --state open --limit 30 \
     --json number,title,author,isDraft,createdAt,updatedAt,additions,deletions,mergeable,reviewDecision,reviews,commits,comments \
     | jq --arg me "$REVIEWER" '
       sort_by(.number) | reverse | .[] | {
         number,
         title,
         author: .author.login,
         isDraft,
         mergeable,
         size: "+\(.additions)/-\(.deletions)",
         reviewDecision,
         lastCommit: (.commits | last | .committedDate),
         myLastReview: ([.reviews[] | select(.author.login == $me)] | last | {state, submittedAt}),
         otherLastReview: ([.reviews[] | select(.author.login != $me and .author.login != "copilot-pull-request-reviewer")] | last | {author: .author.login, state, submittedAt}),
         lastComment: ([.comments[] | select(.author.login != "codecov")] | last | {author: .author.login, createdAt})
       }'
   ```

3. **Classify PRs into Actionable Buckets**:
   Group open PRs in priority order for the reviewer (`$REVIEWER`):
   - **1. New PRs Awaiting Initial Review**:
     Non-draft PRs not authored by `$REVIEWER` where `myLastReview.submittedAt == null`. Flag competing/overlapping PRs targeting the same module/issue and note if another maintainer already commented/approved.
   - **2. Re-reviews Needed (Updated Since Last Review)**:
     Non-draft PRs not authored by `$REVIEWER` where `myLastReview.submittedAt != null` AND (`lastCommit > myLastReview.submittedAt` OR a new author reply `lastComment.createdAt > myLastReview.submittedAt`).
   - **3. Reviewer's Own PRs Ready / Updated**:
     PRs authored by `$REVIEWER` that are `APPROVED` and ready to merge, or have new feedback/conflicts.
   - **4. Waiting on Author / Drafts (Compact Summary)**:
     - Non-draft PRs with `CHANGES_REQUESTED` or `COMMENTED` where no commits or author replies have arrived since `myLastReview.submittedAt`.
     - Draft PRs (`isDraft == true`), summarized compactly on 1–2 lines unless a draft has notable recent maintainer discussion.
     - Conflicting (`mergeable == "CONFLICTING"`) or stale backlog items.

4. **Present Concise Triage Report**:
   - Report sync status in one line if a sync was performed (commit hash + any new release tags).
   - List actionable PRs (`#number`, title, `@author`, `+additions/-deletions`, and why it needs attention—e.g., *opened Oct 31* or *updated Oct 22 after your Oct 17 review*).
   - Keep "Waiting on Author / Drafts" brief so actionable reviews stand out.
   - Ask which PR the user wants to review first.
