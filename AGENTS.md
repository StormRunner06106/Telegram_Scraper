# Repository instructions

## Automatic commit and push

- At the end of every user prompt that changes this repository, commit the task's
  changes and push them before sending the final response. The user has provided
  standing authorization; do not ask for confirmation each time.
- Review the diff and run checks appropriate to the changes before committing.
  Fix task-related failures before publishing the work.
- Stage only changes belonging to the current task. Preserve unrelated existing
  edits and staged changes. Honor `.gitignore`; do not force-add credentials,
  lead exports, backups, or other ignored runtime data.
- Use a concise commit message describing the completed change.
- Push the current branch to its configured upstream. If it has no upstream,
  use `git push -u origin <current-branch>` when `origin` is configured.
- Do not force-push, rewrite existing commits, or discard work to make a push
  succeed. If a commit or push cannot be completed, preserve the work and report
  the exact blocker in the final response.
- If the prompt produces no repository changes, do not create an empty commit.
- Include the commit hash and push outcome in the final response.
