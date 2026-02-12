# Agent Mode: Component Interrogation

Use this mode when the task is to understand a specific component without guessing intent.

## Trigger Phrase

- "Use Component Interrogation mode on `<component>`"
- "Interrogate `<component>`"
- "Audit intent for `<component>`"

## Mission

For a single named component, produce a code-grounded workflow analysis and extract missing intent by asking targeted questions before finalizing documentation.

## Mandatory Behavior

1. Do not guess business or architectural intent.
2. Build findings from code paths, data models, and runtime transitions.
3. Ask focused why-questions for all policy/rule decisions that are not explicit in comments or existing docs.
4. Separate facts from assumptions in output.
5. Capture unresolved questions explicitly.

## Workflow

1. Scope the component boundary.
2. Trace call graph and entry points.
3. Identify actors, states, transitions, and permission gates.
4. Identify operational policies (timeouts, limits, retries, thresholds).
5. Ask user intent questions for each policy that lacks explicit rationale.
6. Draft documentation with:
   - Verified facts from code
   - Author-confirmed intent
   - Open questions
7. Update index/context docs as needed.

## Output Contract

Deliverables must include:

- Component scope (files/modules)
- Workflow/state-machine narrative
- Permission and policy matrix
- Confirmed intent section (from user answers)
- Open Why Questions section
- Risks/technical debt surfaced during interrogation

## Questioning Protocol

Questions must be:

- Specific to one policy/rule each
- Framed as intent choices, not syntax explanations
- Short enough to answer quickly

Preferred format:

- "I see `<rule>`. Is this for `<intent A>` or `<intent B>`?"

## Guardrails

- Do not modify runtime behavior unless explicitly requested.
- Do not fold assumptions into docs as facts.
- If policy has multiple plausible intents, ask instead of inferring.
- If context is stale, update docs/context files after work is complete.

## Reusable Prompt

Use the following prompt with Copilot Agent:

"""
Use Component Interrogation mode against `<component name>`.

Requirements:
1) Map the workflow from code only (no intent guessing).
2) Identify all policy decisions/thresholds/permissions.
3) Ask me targeted why-questions for missing intent before drafting docs.
4) Produce a workflow document under docs/design/.
5) Update docs/MASTER_INDEX.md and docs/context/active_state.md.
"""
