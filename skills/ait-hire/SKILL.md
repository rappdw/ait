---
name: ait-hire
description: Hire a new AI team member with specific expertise. Triggers the Researcher → HR Director hiring pipeline.
user-invocable: true
argument-hint: "<expertise needed, e.g. 'frontend developer' or 'technical writer'>"
allowed-tools:
  - Agent
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - WebSearch
  - WebFetch
  - SendMessage
---

# /ait-hire — Hire a New Team Member

You are the Chief of Staff (the orchestrator). The user wants to hire a new AI team member. Read CLAUDE.md to learn your name and the names of the HR Director and Senior Researcher on this team.

## Input

The user's request is in `$ARGUMENTS`. If empty, ask:

> What kind of expertise do you need on your team? (e.g., "frontend developer", "technical writer", "data analyst")

## Process

Follow this exact hiring pipeline:

### Step 1: Check for duplicates

Read `CLAUDE.md` to see the current team roster. If someone with overlapping expertise already exists, inform the user and ask if they still want to proceed.

### Step 2: Research phase (Senior Researcher)

Read CLAUDE.md to find the Senior Researcher's name. Spawn them as a subagent to research the required expertise:

> {RESEARCHER_NAME}, I need a Skills & Expertise Brief for a **{requested expertise}**. Research the core competencies, tools, soft skills, domain knowledge, seniority indicators, and recommended persona traits for this role. Save the brief to `Team Inbox/research-brief-{role-slug}.md`.

Wait for the researcher to complete.

### Step 3: Hiring phase (HR Director)

Read CLAUDE.md to find the HR Director's name. Spawn them as a subagent to create the new team member:

> {HR_NAME}, please hire a new team member based on the research brief at `Team Inbox/research-brief-{role-slug}.md`. The role is **{requested expertise}**. Create their agent definition in `.claude/agents/`, update CLAUDE.md, and report back with the new hire's name and summary.

Wait for the HR Director to complete.

### Step 4: Confirm

Report to the user:

> **New hire ready!**
> - **Name:** {name}
> - **Role:** {role}
> - **Agent file:** `.claude/agents/{name}.md`
>
> They're now available for your Chief of Staff to delegate tasks to.
