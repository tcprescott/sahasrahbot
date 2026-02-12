# SahasrahBot Documentation — Master Index

> Last updated: 2026-02-12

## Context (AI Agent Reference)

Machine-readable reference files for coding agents:

| File | Description |
|------|-------------|
| [Active State](context/active_state.md) | Current sprint focus, known issues, upcoming work |
| [System Patterns](context/system_patterns.md) | Architecture, data flow, design patterns, module layers |
| [Tech Stack](context/tech_stack.md) | All dependencies with versions, AWS services, external APIs |
| [Coding Standards](context/coding_standards.md) | Naming, async patterns, database patterns, project structure |

## Design Documents

Architectural analysis and domain documentation:

| File | Description |
|------|-------------|
| [Discord Bot Domain](design/discord_bot_domain.md) | Main bot & audit bot: cogs, commands, listeners, UI views, background tasks |
| [Async Tournament Discord Workflow](design/async_tournament_discord_workflow.md) | End-to-end async tournament module workflow: Discord lifecycle, scoring, permissions, and web-coupled review flow |
| [Tournament System](design/tournament_system_analysis.md) | Tournament framework: base classes, 20+ handlers, SpeedGaming integration, match lifecycle |
| [Tournament Module (Non-Async) Audit](design/tournament_module_non_async_audit.md) | Reliability-first audit of non-async tournament architecture, handler inventory, lifecycle, and risk profile |
| [Tournament Registry Config-Driven Design](design/tournament_registry_config_design.md) | Concrete migration design for replacing code-comment seasonal toggles with validated runtime config |
| [RaceTime & Web API](design/racetime_and_web_api.md) | RaceTime.gg integration architecture and race lifecycle; links to canonical split Web API/frontend docs |
| [Web API JSON Endpoints](design/web_api_json_endpoints.md) | Endpoint-level JSON API inventory: auth modes, request/response behavior, async tournament API details |
| [Web Frontend Route Map](design/web_frontend_routes.md) | HTML-rendered route inventory: OAuth-protected pages, blueprint flows, and DEBUG-only surfaces |
| [Core Library & Data Layer](design/core_library_data_layer.md) | Randomizer generation, Tortoise ORM models (50+), database layer, utilities, preset system, migrations |
| [Discord Daily Challenge Audit](design/discord_daily_challenge_audit.md) | Component-scoped audit of Discord `daily.py`: command flow, scheduler behavior, config contract, and resilience risks |
| [Seed Generation Component Audit](design/seed_generation_component_audit.md) | Cross-surface audit of seed generation architecture, provider adapters, reliability/logging risks, and stabilization backlog |
| [Seed Provider Reliability Contract](design/seed_provider_reliability_contract.md) | Concrete cross-provider contract for timeouts, retries, normalized errors, audit parity, and migration phases |

## Guides

Documentation standards and authoring references:

| File | Description |
|------|-------------|
| [Documentation Voice Guide](guides/documentation_voice.md) | Canonical tone, phrasing, and formatting rules for all docs under `docs/` |
| [Component Interrogation Agent Mode](guides/component_interrogation_agent_mode.md) | Reusable Copilot Agent workflow for component-level interrogation and intent capture |
| [Component Interrogation Checklist](guides/component_interrogation_checklist.md) | Execution checklist for policy/permission/workflow interrogation sessions |
| [Async Tournament Interrogation Runbook](guides/component_interrogation_runbook_async_tournament.md) | Example runbook showing interrogation workflow against the async tournament module |
| [Tournament Module (Non-Async) Runbook](guides/tournament_module_runbook.md) | Operator/developer runbook for non-async tournament lifecycle, troubleshooting, and safe change workflow |

## Plans

Execution plans and implementation checklists:

| File | Description |
|------|-------------|
| [Discord Refactor](plans/discord_refactor.md) | Modernization plan for `alttprbot_discord`: remove guild monkey-patching, normalize config, improve resilience |

## User Guide

End-user documentation (GitHub Pages site at sahasrahbot.synack.live):

| File | Description |
|------|-------------|
| [Index](user-guide/index.md) | Landing page |
| [Discord Commands](user-guide/discord.md) | Discord command reference |
| [Presets](user-guide/presets.md) | Preset usage guide |
| [Mystery](user-guide/mystery.md) | Mystery randomizer guide |
| [Mystery YAML](user-guide/mysteryyaml.md) | Mystery YAML format reference |
| [RaceTime.gg](user-guide/rtgg.md) | RaceTime.gg bot usage |
| [League Season 3 Mystery](user-guide/mystery/league_season3.md) | League-specific mystery settings |
