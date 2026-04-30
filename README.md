# brain-code

Daily-notes automation pipeline for the Brain vault.

```
Telegram → n8n (server) → SSH over Tailscale → brain-note CLI (Mac Mini) → vault
```

## Commands

- `brain-note append --text "..."` — real-time light pass: clean text, resolve `[[wikilinks]]`, append a single Arabic bullet to today's daily note (or yesterday's if before 04:00 Asia/Riyadh).
- `brain-note synthesize` — nightly synthesis: rewrite yesterday's auto-region as polished narrative in user's voice using Claude Sonnet 4.6 with prompt caching.

## Setup

```bash
uv sync
cp .env.example .env  # fill in ANTHROPIC_API_KEY
uv run pytest
```

## Layout

- `src/brain_code/` — Python modules
- `prompts/` — LLM prompts as `.md` / `.md.tmpl` files (loaded at runtime, edit without touching code)
- `tests/` — unit tests

See plan: `~/.claude/plans/1-let-s-have-both-typed-lemur.md`
