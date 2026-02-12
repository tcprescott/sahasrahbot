ALWAYS load and strictly follow the rules defined in .github/AGENTS.MD before planning any task.

# Global Instructions for GitHub Copilot

## CRITICAL: Context Loading
Before performing any task, you MUST check the following files for context:
1.  `docs/context/active_state.md`: For the current sprint focus and immediate goals.
2.  `docs/context/system_patterns.md`: For architecture and design patterns.
3.  `docs/context/tech_stack.md`: For allowed libraries and versions.
4.  `docs/context/coding_standards.md`: For style and syntax constraints.

You must adhere to the following constraints for every request in this repository.

## File Organization & Storage
- **MANDATORY:** All *Documentation* Markdown files (except `README.md`) must be stored in the `docs/` directory. Never create *Documentation* markdown files in the root.
- **Plans vs Designs:**
  - **Plans (`docs/plans/`)**: "The How". Execution steps, phase breakdowns, and implementation checklists. Move to `docs/plans/done/` when fully implemented.
  - **Designs (`docs/design/`)**: "The What". Architecture, data models, UI mockups, and trade-off analysis. These persist as reference material.
- **AI Agent Context (`docs/context/`)**: Machine-readable reference files consumed by coding agents. Contains:
  - `active_state.md` — Current sprint focus, known issues, upcoming work. **Update after every significant task completion or goal change.**
  - `system_patterns.md` — Architecture, data flow, design patterns, module layers.
  - `tech_stack.md` — All dependencies with exact versions, AWS services, platform support.
  - `coding_standards.md` — Import order, naming, type hints, testing patterns, linter config.
- If I ask you to create a new documentation file, automatically assume it belongs in `docs/`.
- Organize documentation files into subdirectories based on their purpose (e.g., `guides/`, `dev/`, `design/`, `plans/`, `context/`).
- When referencing documentation files, always use relative links (e.g., `[API Guide](guides/API.md)`).
- For any new documentation file, create a corresponding entry in the `Master Index` (`MASTER_INDEX.md`) with a brief description.

## Documentation Strategy & Updates
- **Prioritize Public Interfaces:** Focus documentation updates on exported functions, classes, and API endpoints. Do not clutter comments with updates for trivial internal variables unless the logic is complex.
- **Intent Over Syntax:** When updating docstrings or markdown, describe *why* the code exists and *how* to use it. Avoid "code-to-text" translation (e.g., do not write "Increments X by 1"; instead write "Increments retry counter to prevent API flooding").
- **Signature Changes:** If you modify a function signature or API schema, you **MUST** update the corresponding docstring/TypeHint immediately.
- **Significant Logic Changes:** If a change alters the system architecture or business logic, explicitly ask me for the context/reasoning before generating the documentation update to ensure the "Why" is captured accurately.

### Context Document Maintenance (MANDATORY)
The `docs/context/` files are the primary knowledge base for all coding agents. You **MUST** keep them current:
- **New dependency added or removed?** → Update `docs/context/tech_stack.md` with the library, version constraint, and purpose.
- **Architecture or data flow changed?** → Update `docs/context/system_patterns.md` (add/modify the affected subsystem, pattern, or diagram).
- **New coding convention established?** → Update `docs/context/coding_standards.md` with the rule and a code example.
- **Sprint focus shifted, task completed, or new issue discovered?** → Update `docs/context/active_state.md`.
- **New design or plan document created?** → Update both `docs/MASTER_INDEX.md` and the relevant context file if it affects architecture or tech stack.
- **When in doubt, update.** Stale context documents cause agents to generate incorrect code. Err on the side of over-updating.
- **Never delete context files.** If a section becomes irrelevant, mark it as deprecated with a date and reason rather than removing it.

## Behavior & Output Style
- Do not apologize ("I'm sorry", "I apologize"). Just correct the issue and move on.
- Do not wrap markdown in code blocks unless explicitly requested.
- Be concise. Avoid fluff.

## Python Environment & Dependencies
- **MANDATORY:** Use Poetry for all Python virtual environment and dependency management.
- **Command Execution:** Always use `poetry run python` instead of bare `python` or `python3` commands.
- When running Python scripts, tests, or code snippets, prefix with `poetry run python`.
- For examples or documentation, reference `poetry run python` as the standard command.

# Behavioral Override: The Socratic Auditor

You have a special mode called "Auditor Mode." When I ask you to "audit this code," "review for intent," or "ask me why," you must switch to this mode.

## Auditor Mode Rules:
1.  **Suppress Explanations:** Do NOT explain *what* the syntax does (e.g., "This is a for loop"). I know how to code.
2.  **Seek Intent:** Analyze the selected code for architectural decisions, magic numbers, complex logic branches, or non-standard patterns.
3.  **Interrogate:** Instead of fixing the code, generate 3-5 probing questions to extract the *business reason* or *architectural goal* behind the implementation.
    * *Example:* "Why was a hardcoded timeout of 30s used here instead of a config variable?"
    * *Example:* "This logic bypasses the standard authentication middleware. What is the specific use case requiring this exception?"
4.  **Synthesize:** After I answer your questions, offer to generate an Architecture Decision Record (ADR) or a comprehensive Docstring block that captures this context permanently.