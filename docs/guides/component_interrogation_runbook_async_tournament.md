# Example Runbook: Async Tournament Component Interrogation

> Last updated: 2026-02-12
> Scope: Example of applying Component Interrogation mode to async tournament module surfaces

This runbook shows how to execute the interrogation pattern for the async tournament module.

## Target Component

Async tournament module (Discord-first workflow with web/API coupled review surfaces).

## Step Plan

1. Identify module surfaces:
   - Discord cog
   - Shared utility/scoring module
   - ORM models
   - Permission check helper
   - API/web routes
2. Trace race lifecycle states from creation to terminal outcomes.
3. Extract policy controls:
   - Eligibility gates
   - Timeouts
   - Owner/admin/mod boundaries
   - Reattempt handling
4. Ask intent questions for each policy lacking explicit rationale.
5. Produce design doc with confirmed-intent section.
6. Update docs index/context metadata.

## Example Intent Questions

- "I see a Discord account age gate plus whitelist override. Is this primarily anti-abuse against multi-account seed reconnaissance?"
- "I see pending auto-forfeit and long in-progress timeout policies. Are these for prompt commitment and abandoned-run cleanup?"
- "Owner-only async admin commands appear strict. Is this temporary operational control or long-term governance?"
- "Discord reattempt UI is disabled while web reattempt endpoints exist. Should web be considered canonical?"

## Expected Outputs

- Component workflow doc under `docs/design/`
- Updated `docs/MASTER_INDEX.md`
- Updated `docs/context/active_state.md`

## Notes

- Keep reasoning evidence-based and tied to file-level behavior.
- Preserve a strict distinction between code facts and author-confirmed rationale.
