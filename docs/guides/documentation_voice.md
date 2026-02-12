# Documentation Voice Guide

> Last updated: 2026-02-12
> Scope: All Markdown documentation under `docs/`

## Voice Profile

Use a clear, technical, and direct voice.

- Prefer short declarative sentences.
- Describe current behavior first, then constraints or caveats.
- Keep tone neutral and professional; avoid jokes and conversational asides.
- Use consistent terms for the same concepts (for example, "RaceTime.gg", "Discord OAuth", "Tortoise ORM").

## Writing Rules

1. Lead each document with a one- or two-line purpose statement.
2. Prefer active voice ("The bot validates..." rather than "...is validated").
3. Avoid speculative or subjective language unless clearly labeled as intent or open question.
4. Keep command and endpoint descriptions action-oriented and explicit.
5. Preserve factual content; voice unification should not change behavior or architecture meaning.

## Formatting Conventions

- Use sentence case in paragraph text and title case in headings.
- Use consistent metadata labels near the top of docs:
  - `Last updated`
  - `Scope`
- Use bullet lists for operational steps and concise tables for inventories.
- Keep links descriptive and relative for internal docs.

## Scope-Specific Guidance

- **User guide docs:** Instructional, concise, task-oriented.
- **Design docs:** Analytical, structured, implementation-focused.
- **Context docs:** Operational status language, explicit action items.
- **Plan docs:** Phase-based execution language with clear deliverables.

## Review Checklist

Before finalizing documentation edits:

- Confirm tone matches this guide.
- Confirm terminology is consistent with `docs/context/system_patterns.md`.
- Confirm links remain valid and relative.
- Confirm no behavior was changed while rewording.