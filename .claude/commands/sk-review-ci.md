# Trimmed multi-agent PR review (CI)

CI-adapted multi-agent review, sized for on-request runs on a personal repo.
Two reviewers in parallel, then a reality-check pass, then post. Runs headless
in the Claude Code GitHub Action against a single PR.

The orchestrator (you) drives all git/gh access and all posting. The subagents
only read and report; they do not touch git or GitHub.

## Phase 1: Context (you, the orchestrator)

1. Identify the PR number and its base branch from the prompt. Do NOT assume
   `main` -- coregen integrates on `dev`.
2. Get the change set with `gh pr diff <number>` and `gh pr view <number>`.
   Scope the review to this PR's diff against its base branch only.
3. Read the code the diff touches and enough surrounding context to judge it.
   coregen is a Python code-generation CLI (`source/coregen/`, tests in
   `tests/`, Jinja templates, HCL/Terraform output). Pay attention to:
   - The documented CLI exit-code contract (input errors vs not-found vs
     success) -- regressions here are real bugs.
   - Filter/pattern semantics (`CG_FILTERS`, entity-scoped filters) and their
     error handling.
   - Template rendering and generated-output correctness / path handling.
4. Produce a short `CONTEXT_SUMMARY`: base branch, files in scope (with paths),
   key functions/classes changed, and any test coverage present in the diff.

## Phase 2: Parallel review (subagents)

Launch BOTH reviewers in a SINGLE message (parallel Task calls). Give each the
`CONTEXT_SUMMARY`, the diff, the changed-file list, and the reviewer
requirements below.

| Agent | Focus |
|-------|-------|
| `code-reviewer` | Security, logic errors, edge cases, exit-code/contract regressions, template + path handling |
| `code-quality-pragmatist` | Over-engineering, unnecessary abstraction, dead code, YAGNI on a personal-scale tool |

Reviewer requirements (pass these through):

- Cite specific `file_path:line_number` for every finding.
- Quote the actual code when making a claim.
- State a confidence level (high/medium/low).
- Prefix any speculation with `[UNVERIFIED]`.

## Phase 3: Reality check (subagent)

Hand the combined Critical + Important findings to `reality-check-manager`. It
verifies each against the real code, confirms cited locations, and returns the
verified / rejected / uncertain split. Drop everything it rejects.

## Phase 4: Post (you, the orchestrator)

- Post one inline comment per VERIFIED finding at its cited line, using
  `mcp__github_inline_comment__create_inline_comment`.
- Post one top-level summary comment with `gh pr comment` using the Output
  Format below. Include the count of rejected findings so the author sees the
  reality-check worked.
- If there are no verified findings, post a single top-level comment confirming
  the change looks good, with a one-line rationale.

## Output Format (summary comment)

```markdown
## Claude review

### Context
- Base: <base branch> · Files: <count> · Tests in diff: <yes/no>

### Critical (verified)
1. [Issue] — file:line — [evidence]

### Important (verified)
1. [Issue] — file:line — [evidence]

### Suggestions
1. [Suggestion] — [rationale]

### Reality check
- Verified: N · Rejected: M · Uncertain: K
```

## Anti-hallucination rules

1. No claims without citations — every issue references actual code in the diff.
2. No invented files or lines — only reference what exists in this PR.
3. Explicit uncertainty — prefix speculation with `[UNVERIFIED]`; never post an
   `[UNVERIFIED]` item as a verified finding.
4. Reality check is mandatory — Phase 3 is never skipped.
5. Severity requires evidence — a Critical claim must show the failure path, not
   a theoretical risk.
6. Respect defensive defaults — check for existing guards before claiming a gap.
