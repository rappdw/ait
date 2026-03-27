# AIT Demo Script

A guide for demoing AIT to a non-technical user. The goal: sit someone down, tell them they have an AI team, and watch what happens.

> **The Assignment:** Before writing any more code, find one non-technical business person and sit them in front of AIT's current MVP. Don't explain anything. Don't demo. Just say "tell it what you need help with" and watch what happens. The surprise — what they do that you didn't expect — will tell you more about what to build next than this entire design doc.

## Night Before: Prep (~10 minutes)

### 1. Install dependencies

```bash
pip install click>=8.0
```

Optional (improves experience but not required):
```bash
pip install sentence-transformers pdfplumber python-docx
```

### 2. Run setup

Use your test subject's first name. If their name is Sarah:

```
/ait-setup Sarah
```

Walk through the wizard — pick names for the team or accept defaults. This creates CLAUDE.md, the agent definitions, directories, and the knowledge base.

### 3. Seed the knowledge base

Drop 2-3 files into `Team Inbox/` that are relevant to this person — a report they wrote, meeting notes, a strategy doc, anything they'd recognize. Then:

```
/ait-ingest
```

### 4. Pre-hire a specialist

Hire one specialist that matches something they'd actually ask for. If Sarah is in marketing:

```
/ait-hire marketing strategist
```

This runs the full researcher -> HR pipeline and creates a real specialist agent.

### 5. Verify it works

Open a fresh Claude Code session in the project directory. Type something like "Hey Larry, what's on the team?" and confirm the Chief of Staff responds in character, knows the roster, and delegates properly.

### 6. Clear your conversation history

Close the session so the demo starts clean.

---

## The Demo

### What they see

A Claude Code window (desktop app or terminal) open to the project directory. Nothing else. No instructions on screen.

### What you say (verbatim)

> "This is your AI team. You have a Chief of Staff named [Name], and he manages a small team of specialists. You can just talk to him like you'd talk to a real chief of staff — tell him what you need, ask questions, give him work. Try it."

Then hand them the keyboard and shut up.

That's the whole script. Don't explain slash commands. Don't explain the knowledge base. Don't explain agents. The test is: does the Chief of Staff metaphor carry itself?

---

## What to Watch For

| Signal | What it means |
|--------|---------------|
| They type naturally ("Hey Larry, can you...") | The metaphor landed — they get it |
| They ask "what can you do?" | Good — the Chief of Staff should answer this well from CLAUDE.md |
| They ask for help with something real | Jackpot — watch if the Chief of Staff delegates or handles it directly |
| They ask about the files you seeded | Tests if the KB connection works via the Chief of Staff |
| They get confused and ask YOU what to type | The metaphor didn't carry — friction point to study |
| They type a slash command | They're thinking like a developer, not a user |
| The Chief of Staff does everything himself instead of delegating | Delegation guardrails in CLAUDE.md may need tuning |

### The delegation gap (watch carefully)

When the Chief of Staff delegates to a specialist, the specialist delivers output to `{Name}'s Inbox/`. The user won't know to look there unless the Chief of Staff tells them. The flow should be:

1. User asks for something ("Can you draft a social media plan for Q2?")
2. Chief of Staff delegates to the marketing strategist
3. Specialist writes output to the user's inbox
4. Chief of Staff reports back with what was done and where to find it

Step 4 is critical. If the Chief of Staff says "I've delegated this" but doesn't clearly tell the user where to find the output, the experience breaks.

---

## After the Demo: Debrief

Ask them three questions:

1. "What was that like?" (Open-ended — let them tell you)
2. "Was there a moment where you weren't sure what to do?"
3. "Would you use this again tomorrow? What would you use it for?"

The answers to those three questions are worth more than everything in the design doc.

---

## What You're Testing (and What You're Not)

**Testing:**
- Does the Chief of Staff metaphor work for non-technical users?
- Do they intuitively talk to it?
- Does delegation make sense?

**Not testing:**
- Learning/memory (not implemented yet)
- Knowledge base search through conversation (exists but not fully wired)
- The hiring flow (you pre-hired for them)

**Could break:**
If they ask for something that requires a specialist you didn't pre-hire, the Chief of Staff will try to hire one live. That's actually a great demo moment if it works, but it takes a few minutes. Decide in advance if you want that to happen or pre-hire enough specialists to cover likely requests.
