---
name: ait-team
description: Display the current AI team roster with each member's name, role, and expertise.
user-invocable: true
allowed-tools:
  - Read
  - Glob
  - Grep
---

# /ait-team — Show Team Roster

Display the current AI team roster by reading the project state.

## Process

1. Read `CLAUDE.md` and extract the team roster section (Founding Members / Team Roster).
2. Read each agent file in `.claude/agents/` to get their full role descriptions.
3. Display a formatted roster:

```
## Your AI Team

| Name | Role | Status |
|------|------|--------|
| {COS_NAME} | Chief of Staff | Built into CLAUDE.md |
| {Researcher} | Senior Researcher | .claude/agents/{name}.md |
| {HR Director} | HR Director | .claude/agents/{name}.md |
| ... | ... | ... |
```

For each team member beyond the table, show a one-line description of their expertise pulled from their agent file's `description` frontmatter field.

If no CLAUDE.md exists, tell the user to run `/ait-setup` first.
