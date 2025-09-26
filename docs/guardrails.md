# Guardrails

## Editing scope
- Allowed: eassistant/**, tests/**, docs/**
- Disallowed (ask before editing): infra/**, .github/**

## Code quality
- Lint: ruff
- Format: black
- Types: mypy (strict for eassistant/graph/state.py)
- Tests: pytest; target coverage ≥ 80% by M3

## Prompts & privacy
- Keep system prompts short; no secrets or PII.
- Never print full email content in logs; use redaction helpers.

## Safety practices
- Create a Checkpoint before multi-file or sweeping refactors.
- Stop and summarize diffs if >20 files change.
- For wide renames: “Create Checkpoint, then rename; run tests; show failures + minimal fix.”

## CLI contract
- Conversational only; only commands allowed: `exit`, `quit`.

## S3 usage
- Opt-in only. Ask for explicit confirmation the first time.
