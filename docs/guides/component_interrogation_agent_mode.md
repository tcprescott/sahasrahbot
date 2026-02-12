# Component Interrogation Agent Mode

> Last updated: 2026-02-12
> Scope: Repeatable Copilot Agent workflow for intent-first analysis of one application component

This guide defines a reusable way to run Copilot Agent against a single component while preventing undocumented intent assumptions.

## Purpose

Use this mode when you need workflow documentation for a component whose behavior is spread across multiple files and layers.

## Invocation

Use one of these prompts:

- "Use Component Interrogation mode on `<component>`"
- "Interrogate `<component>` and document the workflow"
- "Audit `<component>` for intent and workflow"

## Required Outcomes

- Workflow and state transitions are traced from code.
- Permission boundaries and policy thresholds are identified.
- Unknown intent is clarified via targeted questions.
- Final docs contain a clear split between code facts and confirmed rationale.

## Operating Procedure

1. Define component boundaries (files, cogs, utilities, API surfaces, models).
2. Trace lifecycle from entry points to terminal states.
3. Extract policy rules (timeouts, limits, eligibility, retries, score formulas).
4. Ask intent questions for each policy without explicit rationale.
5. Draft documentation using confirmed answers.
6. Capture open questions that remain unresolved.
7. Update documentation index/context files.

## Deliverable Structure

A completed component workflow document should contain:

- Scope
- Actors
- Data model overview
- End-to-end workflow
- State transitions
- Permission model
- Verified intent (author-confirmed)
- Open why questions
- Operational notes / technical debt

## Constraints

- No behavior changes unless explicitly requested.
- No guessed rationale in "intent" sections.
- If ambiguity exists, ask before documenting rationale.

## References

- Canonical mode prompt: [GitHub Agent Mode Source](../../.github/agent-modes/component-interrogation.md)
- Checklist template: [Component Interrogation Checklist](component_interrogation_checklist.md)
- Example runbook: [Async Tournament Interrogation Runbook](component_interrogation_runbook_async_tournament.md)
