# AIT - Your AI Team and Personal Knowledge Base

A Claude Code plugin that gives you a personal AI team and knowledge base.

## What You Get

- **Chief of Staff** — An AI team lead that delegates tasks to the right team member (you name them during setup)
- **Senior Researcher** — Produces expertise briefs when new hires are needed (you name them during setup)
- **HR Director** — Hires new AI team members on demand (you name them during setup)
- **Knowledge Base** — A SQLite database with full-text search for storing and retrieving your notes, documents, bookmarks, and more

## Install

```bash
# Install directly from GitHub (marketplace + plugin bundled in one repo)
claude mcp add-plugin rappdw/ait
```

Or for local development:

```bash
claude --plugin-dir /path/to/ait
```

## Quick Start

```bash
# 1. Set up your project — you'll name your team during setup
/ait-setup Alice

# 2. Hire a specialist
/ait-hire frontend developer

# 3. View your team
/ait-team

# 4. Ingest files into the knowledge base
# Drop files in Team Inbox/, then:
/ait-ingest
```

## Skills

| Skill | Description |
|-------|-------------|
| `/ait-setup [name]` | Scaffold the AI team: directories, CLAUDE.md, agents, and knowledge base |
| `/ait-hire <expertise>` | Hire a new team member (runs the researcher → HR pipeline) |
| `/ait-team` | Display the current team roster |
| `/ait-ingest [path]` | Process files into the knowledge base |

## How It Works

1. **You talk to your Chief of Staff** (via CLAUDE.md). They never do work directly — they delegate.
2. **Your Chief of Staff picks the right team member** based on expertise, or hires a new one.
3. **Team members deliver** to your personal inbox (`{Name}'s Inbox/`).
4. **The knowledge base** stores and indexes everything for fast retrieval.

## Repository Structure

```
ait/
├── .claude-plugin/        # Plugin + marketplace metadata
│   ├── plugin.json
│   └── marketplace.json
├── skills/                # Claude Code skills (ait-setup, ait-hire, ait-team, ait-ingest)
├── pkb/                   # Personal Knowledge Base engine (Python)
├── demo_script.md         # Guide for demoing to non-technical users
└── README.md
```

### Project Structure (after running /ait-setup)

```
your-project/
├── .claude/agents/        # AI team member definitions
│   ├── {researcher}.md
│   └── {hr-director}.md
├── CLAUDE.md              # Chief of Staff's orchestrator identity
├── Team/                  # Shared workspace
├── Team Inbox/            # Your input channel: file drops, task requests, reference material
├── {Name}'s Inbox/        # Your personal inbox
└── kb/
    └── pka.db             # SQLite knowledge base
```

## Requirements

- Claude Code CLI
- SQLite 3 (for the knowledge base)

## License

MIT
