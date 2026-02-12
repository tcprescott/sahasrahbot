# Component Interrogation Checklist

> Last updated: 2026-02-12
> Scope: Checklist for running component-level interrogation with Copilot Agent

Use this checklist during an interrogation session.

## 1) Scope & Inventory

- [ ] Component name is explicit.
- [ ] Primary files are identified.
- [ ] Cross-layer dependencies are identified (Discord/API/models/util/etc.).

## 2) Workflow Mapping

- [ ] Entry points captured (commands, routes, tasks, listeners).
- [ ] State transitions captured.
- [ ] Error/timeout/forfeit/fallback paths captured.
- [ ] Background automation paths captured.

## 3) Policies & Permissions

- [ ] Eligibility rules listed.
- [ ] Thresholds/timeouts listed.
- [ ] Role/user permission checks listed.
- [ ] Owner-only safeguards listed.

## 4) Intent Interrogation

- [ ] Each unexplained policy has a targeted why-question.
- [ ] Answers are captured verbatim or precisely paraphrased.
- [ ] Unanswered items are tracked in "Open Why Questions".

## 5) Documentation Output

- [ ] Scope is explicit and file-backed.
- [ ] Facts are separated from confirmed intent.
- [ ] Policy matrix is included.
- [ ] Risks/technical debt are listed without speculative claims.

## 6) Repository Hygiene

- [ ] New docs added under `docs/` only.
- [ ] [docs/MASTER_INDEX.md](../MASTER_INDEX.md) updated.
- [ ] [docs/context/active_state.md](../context/active_state.md) updated.
