---
name: ait-ingest
description: Process files from Team Inbox (the user's input channel) into the PKA knowledge base. Extracts text, metadata, and tags, then indexes for search.
user-invocable: true
argument-hint: "[file or folder path, defaults to Team Inbox/]"
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
---

# /ait-ingest — Ingest Files into Knowledge Base

Process files and add them to the PKA SQLite knowledge base using the Python CLI.

## Step 0: Locate the plugin directory

Before anything else, find where the AIT plugin is installed:

```bash
AIT_PLUGIN_DIR=""
for d in ~/.claude/plugins/marketplaces/*/; do
  if [ -f "$d/.claude-plugin/plugin.json" ] && grep -q '"ait"' "$d/.claude-plugin/plugin.json" 2>/dev/null; then
    AIT_PLUGIN_DIR="$d"
    break
  fi
done
[ -z "$AIT_PLUGIN_DIR" ] && [ -f ".claude-plugin/plugin.json" ] && AIT_PLUGIN_DIR="$(pwd)"
[ -z "$AIT_PLUGIN_DIR" ] && [ -d "pkb" ] && AIT_PLUGIN_DIR="$(pwd)"
echo "AIT_PLUGIN_DIR=$AIT_PLUGIN_DIR"
```

All `python -m pkb.cli` commands below must be run with `PYTHONPATH="$AIT_PLUGIN_DIR"` prepended. Also ensure click is available:

```bash
python3 -c "import click" 2>/dev/null || pip install click>=8.0 2>/dev/null || pip3 install click>=8.0 2>/dev/null
```

## Input

If `$ARGUMENTS` is provided, process that specific file or directory. Otherwise, process all files in `Team Inbox/`.

## Process

### Step 1: Find the knowledge base

Look for `kb/pka.db` in the project root. If it doesn't exist, tell the user to run `/ait-setup` first.

### Step 2: Ingest

Use the Python CLI for all database operations. **Never** use raw `sqlite3` commands with string interpolation — file content and titles commonly contain characters that break SQL.

**To add a single file:**
```bash
PYTHONPATH="$AIT_PLUGIN_DIR" python3 -m pkb.cli add --db kb/pka.db "path/to/file"
```

**To ingest an entire directory (default: Team Inbox/):**
```bash
PYTHONPATH="$AIT_PLUGIN_DIR" python3 -m pkb.cli ingest --db kb/pka.db "Team Inbox/"
```

**To ingest recursively:**
```bash
PYTHONPATH="$AIT_PLUGIN_DIR" python3 -m pkb.cli ingest --db kb/pka.db -r "path/to/directory"
```

**To add tags during ingestion:**
```bash
PYTHONPATH="$AIT_PLUGIN_DIR" python3 -m pkb.cli add --db kb/pka.db -t "tag1" -t "tag2" "path/to/file"
```

The CLI automatically:
- Detects file type from extension
- Extracts title from content or filename
- Computes content hash for deduplication
- Skips duplicate files
- Auto-tags based on content type

### Step 3: Report results

Display a summary:

> **Ingestion complete**
> - Files processed: {N}
> - New items added: {N}
> - Duplicates skipped: {N}
>
> Search the knowledge base with: `python -m pkb.cli search --db kb/pka.db "your query"`
