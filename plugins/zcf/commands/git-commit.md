---
description: Analyze changes with Git only and auto-generate conventional commit messages with optional emoji; suggests splitting commits when needed, runs local Git hooks by default (use --no-verify to skip)
allowed-tools: Read(**), Exec(git status, git diff, git log, git add, git restore --staged, git commit, git rev-parse, git config), AskUserQuestion
argument-hint: [--no-verify] [--all] [--amend] [--signoff] [--emoji] [--scope <scope>] [--type <type>]
# examples:
#   - /git-commit                           # Analyze current changes, generate commit message
#   - /git-commit --all                     # Stage all changes and commit
#   - /git-commit --no-verify               # Skip Git hooks
#   - /git-commit --emoji                   # Include emoji in commit message
#   - /git-commit --scope ui --type feat    # Specify scope and type
#   - /git-commit --amend --signoff         # Amend last commit with signature
---

# Claude Command: Commit (Git-only)

This command works **without any package manager/build tools**, using only **Git** to:

- Read changes (staged/unstaged)
- Analyze recent commit history to match repository style (language, emoji usage)
- Determine if changes should be **split into multiple commits**
- Generate **Conventional Commits** style messages with optional emoji for each commit
- Present messages for **user confirmation** before executing any commit
- Execute `git add` and `git commit` as needed (runs local Git hooks by default; use `--no-verify` to skip)

---

## Usage

```bash
/git-commit
/git-commit --no-verify
/git-commit --emoji
/git-commit --all --signoff
/git-commit --amend
/git-commit --scope ui --type feat --emoji
```

### Options

- `--no-verify`: Skip local Git hooks (`pre-commit`/`commit-msg` etc.).
- `--all`: When staging area is empty, automatically `git add -A` to include all changes in the commit.
- `--amend`: **Amend** the last commit without creating a new one (preserves author and timestamp unless local Git config specifies otherwise).
- `--signoff`: Add `Signed-off-by` line (use when following DCO process).
- `--emoji`: Include emoji prefix in commit message (omit for plain text).
- `--scope <scope>`: Specify commit scope (e.g., `ui`, `docs`, `api`), written to message header.
- `--type <type>`: Force commit type (e.g., `feat`, `fix`, `docs`), overrides automatic detection.

> Note: If the framework doesn't support interactive confirmation, enable `confirm: true` in front-matter to avoid mistakes.

---

## What This Command Does

1. **Repository/Branch Validation**
   - Check if in a Git repository using `git rev-parse --is-inside-work-tree`.
   - Read current branch/HEAD status; if in rebase/merge conflict state, prompt to resolve conflicts first.

2. **Change Detection**
   - Get staged and unstaged changes using `git status --porcelain` and `git diff`.
   - If staged files = 0:
     - If `--all` is passed → Execute `git add -A`.
     - Otherwise prompt choice: continue analyzing unstaged changes for **suggestions**, or cancel to manually group staging.

3. **Commit Style Analysis**
   - Run `git log --oneline -n 20` to analyze the repository's recent commit history.
   - Detect the dominant language pattern (English, Chinese, or mixed).
   - Detect whether emoji prefixes are commonly used in recent commits.
   - Store the detected style (language + emoji preference) and apply it to all generated messages for this session.
   - If `--emoji` is explicitly passed, force emoji usage regardless of detected style.

4. **Split Suggestions (Split Heuristics)**
   - Cluster by **concerns**, **file modes**, **change types** (e.g., source code vs docs/tests; different directories/packages; additions vs deletions).
   - If **multiple independent changesets** or large diff detected (e.g., > 300 lines / across multiple top-level directories), suggest splitting commits with pathspecs for each group.
   - **For split scenarios**: Present the proposed split plan to the user and ask for confirmation before proceeding. If the user rejects the split, fall back to a single commit.

5. **Commit Message Generation (Conventional with Optional Emoji)**
   - Auto-infer `type` (`feat`/`fix`/`docs`/`refactor`/`test`/`chore`/`perf`/`style`/`ci`/`revert`...) and optional `scope`.
   - Generate message header: `[<emoji>] <type>(<scope>)?: <subject>` (first line ≤ 72 chars, imperative mood, emoji included only with `--emoji` flag or if detected style uses emoji).
   - Generate message body: bullet points (motivation, implementation details, impact scope, BREAKING CHANGE if any).
   - **Language matching**: Use the language detected in Step 3 for all descriptive text (subject, body). Technical identifiers (file names, command names, API names) remain in English.

6. **User Confirmation via AskUserQuestion**
   - Display the generated commit message(s) to the user.
   - Use `AskUserQuestion` with the following options:
     - **Confirm Commit** — proceed with the commit.
     - **Cancel** — abort without committing.
     - **Edit Message** — user provides custom text via the "Other" free-form input.
   - If the user selects **Edit Message** (or enters custom text via "Other"):
     - Replace the commit message with the user's input.
     - Display the updated message and present the same three options again.
     - Repeat this loop until the user selects **Confirm Commit** or **Cancel**.
   - **For split scenarios**: After confirming the split plan (Step 4), process each commit group sequentially. For each group, generate its message and run through the same confirmation loop individually.

7. **Execute Commit**
   - Single commit scenario: `git commit [-S] [--no-verify] [-s] -F - <<'EOF'` with the confirmed message via HEREDOC.
   - Multiple commit scenario (split accepted and confirmed): Execute `git add <paths> && git commit -F - <<'EOF' ...` per group sequentially.

8. **Safe Rollback**
   - If mistakenly staged, use `git restore --staged <paths>` to unstage (command provides instructions, doesn't modify file contents).

---

## Best Practices for Commits

- **Atomic commits**: One commit does one thing, easier to trace and review.
- **Group before committing**: Split by directory/module/feature.
- **Clear subject**: First line ≤ 72 chars, imperative mood (e.g., "add... / fix...").
- **Body with context**: Explain motivation, solution, impact scope, risks, and next steps.
- **Follow Conventional Commits**: `<type>(<scope>): <subject>`.
- **Match repository style**: Generated messages should blend in with the project's existing commit history.

---

## Type to Emoji Mapping (When --emoji is Used)

- ✨ `feat`: New feature
- 🐛 `fix`: Bug fix (includes 🔥 remove code/files, 🚑️ hotfix, 👽️ adapt to external API changes, 🔒️ security fix, 🚨 fix warnings, 💚 fix CI)
- 📝 `docs`: Documentation and comments
- 🎨 `style`: Code style/formatting (no semantic changes)
- ♻️ `refactor`: Refactoring (no new features, no bug fixes)
- ⚡️ `perf`: Performance improvements
- ✅ `test`: Add/fix tests, snapshots
- 🔧 `chore`: Build/tools/misc tasks (merge branches, update configs, release tags, pin dependencies, .gitignore, etc.)
- 👷 `ci`: CI/CD configuration and scripts
- ⏪️ `revert`: Revert commits
- 💥 `feat`: Breaking changes (explained in `BREAKING CHANGE:` section)

> If `--type`/`--scope` is passed, it will **override** auto-detection.
> Emoji is only included when `--emoji` flag is specified or the repository style commonly uses emoji.

---

## Guidelines for Splitting Commits

1. **Different concerns**: Unrelated feature/module changes should be split.
2. **Different types**: Don't mix `feat`, `fix`, `refactor` in the same commit.
3. **File modes**: Source code vs docs/tests/configs should be grouped separately.
4. **Size threshold**: Large diffs (e.g., >300 lines or across multiple top-level directories) should be split.
5. **Revertability**: Ensure each commit can be independently reverted.

---

## Examples

**Good (with --emoji)**

- ✨ feat(ui): add user authentication flow
- 🐛 fix(api): handle token refresh race condition
- 📝 docs: update API usage examples
- ♻️ refactor(core): extract retry logic into helper
- ✅ test: add unit tests for rate limiter
- 🔧 chore: update git hooks and repository settings
- ⏪️ revert: revert "feat(core): introduce streaming API"

**Good (without --emoji)**

- feat(ui): add user authentication flow
- fix(api): handle token refresh race condition
- docs: update API usage examples
- refactor(core): extract retry logic into helper
- test: add unit tests for rate limiter
- chore: update git hooks and repository settings
- revert: revert "feat(core): introduce streaming API"

**Split Example**

- `feat(types): add new type defs for payment method`
- `docs: update API docs for new types`
- `test: add unit tests for payment types`
- `fix: address linter warnings in new files` ← (if your repo has hook errors)

---

## Important Notes

- **Git only**: No package manager/build commands (`pnpm`/`npm`/`yarn` etc.).
- **Respects hooks**: Executes local Git hooks by default; use `--no-verify` to skip.
- **No source code changes**: Command only reads staging area and passes commit message via HEREDOC; doesn't directly edit working directory files.
- **Safety prompts**: In rebase/merge conflicts, detached HEAD states, prompts to handle/confirm before continuing.
- **Auditable and controllable**: If `confirm: true` is enabled, each actual `git add`/`git commit` step requires confirmation.
- **Style consistency**: Always analyze `git log` first to ensure generated messages match the repository's language and formatting conventions.
