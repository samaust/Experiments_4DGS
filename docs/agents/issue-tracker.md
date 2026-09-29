# Issue tracker

Issues and specs for this repository live in GitHub Issues at
`samaust/Experiments_4DGS`. Use the `gh` CLI from this repository.

- Create: `gh issue create --title "..." --body-file <file>`
- Read: `gh issue view <number> --comments`
- List: `gh issue list --state open --json number,title,body,labels`
- Comment: `gh issue comment <number> --body-file <file>`
- Label: `gh issue edit <number> --add-label "..."` or `--remove-label "..."`
- Close: `gh issue close <number> --comment "..."`

When a skill says to publish an issue or fetch a ticket, use this tracker.

## Pull requests as a triage surface

**PRs as a request surface: no.** Change this to `yes` only if external pull
requests should enter the issue triage queue.
