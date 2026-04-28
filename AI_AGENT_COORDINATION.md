# AI Agent Coordination

Last updated: 2026-04-28
Repository: `C:\Users\CCSV\Desktop\Projects\Validation\Val`

## Purpose

This repository is worked on by multiple AI agents and tools.

This file is the shared coordination layer for all agents. It keeps the project intent, current state, remaining work, and handoff notes in one place so the next agent can continue without rediscovering context.

## What Every Agent Must Do

Every agent that starts work in this repository should read this file first.

Every agent should also inspect the repository state before making changes:

- `git status --short --branch`
- current file tree
- relevant source files and tests

Every agent that finishes work must update this file before stopping.

Maintain this file in two different ways:

1. `Current Task List` is forward-looking and must contain only work that still remains.
2. `Current Active Stage` is the compact history log of what agents already did.

When an agent completes a task, remove that completed item from `Current Task List`.

If new tasks are discovered, changed, split, merged, or removed, update `Current Task List` so it reflects the current forward plan only.

When an agent finishes work, add a short entry to `Current Active Stage` with:

1. Time
2. Commit hash or `uncommitted`
3. Agent name
4. One short line describing what was done
5. One line starting with `- Current place:` that marks the exact current place or next place in the workflow

The goal is:

- `Current Task List` = only what still needs to be done
- `Current Active Stage` = compact historical log of agent work

Do not keep history inside `Current Task List`.

## Project Overview

This project is intended to become a generic Root Cause Analysis platform based on an RLM/LLM-driven investigation agent.

The core idea is not to hard-code parsers, chunking rules, or regex searches for one customer. Instead, the system should inspect each customer's data, infer schemas and operational entities, generate small validated investigation tools, run those tools in a controlled environment, and produce an RCA report backed by structured evidence.

Expected long-term capabilities:

- Catalog customer data sources.
- Profile unknown logs, metrics, traces, events, topology, and configuration data.
- Generate customer-specific parsers and investigation tools.
- Validate generated tools before trusting their output.
- Detect impacted SLI/SLO windows.
- Rank suspicious entities and signals.
- Join evidence across logs, metrics, traces, events, and configuration.
- Build RCA hypotheses.
- Support or reject hypotheses using structured evidence.
- Produce concise RCA reports with confidence, timeline, alternatives, and data gaps.
- Preserve useful generated tools for controlled reuse.

Current repository state:

- `GENERIC_RLM_RCA_PLAN.md` contains the initial high-level generic architecture and phased build plan.
- `main.py` is the orchestration entry point and the only file importing `src/settings.py`.
- `src/settings.py` contains Pydantic Settings loaded from `.env`.
- `src/logger.py` contains the centralized application logger.
- `src/models.py` contains all Pydantic data structures currently used by the app.
- `src/anomalies.py` builds early anomaly candidates from numeric sample summaries.
- `src/anomalies.py` aligns numeric observations to the anomaly time by exact timestamp or minute-level timestamp prefix.
- `src/entities.py` extracts initial entities from observed entity fields and links them to source files and metrics.
- `src/intake.py` catalogs customer data files while ignoring repository/system folders.
- `src/profiler.py` creates a first structured profile from the data catalog.
- `src/schema.py` samples readable sources and infers basic field roles such as timestamp, entity, metric, latency, and status.
- `src/evidence.py` converts schema profiles into structured evidence, including detected timestamp/entity/metric/status fields, timestamp examples, numeric sample summaries, text severity counts, repeated message templates, and repeated-template bursts.
- `src/hypotheses.py` ranks anomaly candidates with time/entity/supporting-evidence context and records supporting evidence IDs on each hypothesis.
- `src/tools.py` generates, validates, and executes read-only investigation tool specs from the data profile, including focused line matches by anomaly time window or entity and first-pass structured extractions when readable source text is available.
- `src/reports.py` writes RCA reports as JSON and Markdown artifacts.
- `src/agent.py` wraps the RCA workflow, records bounded deterministic generate-validate-execute-update cycles, scopes cycle evidence IDs, and prepares optional Pydantic AI integration.
- `.gitignore` protects `.env`, `SA.json`, caches, virtual environments, and system files.
- The current runtime is deterministic when `LLM_PROVIDER=none`.
- Pydantic AI is only imported when an LLM provider is enabled.
- Tests use Python `unittest` so the suite can run without installing pytest.
- Git repository is connected to `origin/main`.

## Architecture Constraints

Follow the project-level instructions supplied by the owner:

- `main.py` is the only entry point allowed to import and access `settings.py` or config objects.
- Pass configuration values from `main.py` directly to class constructors.
- Every functional class must have a `__init__` method for configuration and a specific `.setup()` method for initialization logic.
- Use Pydantic extensively for validation and state management.
- All Pydantic models must reside in a dedicated `models.py` file.
- Never use raw dictionaries for structured data when a Pydantic model is appropriate.
- Agents must be wrapped using LangChain or Pydantic AI.
- Agent logic and wrappers must live in `agent.py`.
- Use `logger.py` for centralized logging.
- Do not use production `print()` statements; use the logger.
- Sensitive values must stay in `.env`.
- Ensure `.gitignore` includes `.env`, `__pycache__`, and system files.

Intended initial file layout:

- `main.py` — orchestration and dependency injection.
- `src/models.py` — all Pydantic data structures.
- `src/settings.py` — Pydantic BaseSettings for environment variables.
- `src/logger.py` — centralized logging.
- `src/agent.py` — RLM/RCA agent wrapper.
- `src/` additional modules as the implementation grows.
- `.env` — local secrets only, never committed.
- `.gitignore` — repository ignore rules.

## Current Task List

- Expand structured extraction beyond first-pass readable-line matches into source-specific metric, event, trace, config, and topology extraction models.
- Improve hypothesis ranking with topology/entity relationships beyond flat entity IDs.
- Turn bounded deterministic investigation cycles into an LLM/RLM-controlled loop with tool proposal validation.
- Add dependency documentation or packaging once the first executable workflow stabilizes.

## Current Active Stage

- `2026-04-27 13:55:00 -0700` | `uncommitted` | `Codex` | Created the initial coordination handoff document for the generic RLM/LLM RCA project.
- Current place: Coordination file initialized. Repository contains only the generic plan and this coordination document; implementation has not started yet.
- `2026-04-27 14:05:00 -0700` | `uncommitted` | `Codex` | Built the first runnable RCA scaffold with settings, logger, Pydantic models, data cataloging, profiling, and validated investigation tool specs.
- Current place: `python main.py` and `python -m compileall main.py src` pass. Next work should turn `src/tools.py` specs into executable read-only investigation tools and add tests.
- `2026-04-27 14:10:00 -0700` | `uncommitted` | `Codex` | Added executable read-only tool execution, JSON report writing, environment-driven investigation inputs, and unittest coverage for the pipeline.
- Current place: `python main.py`, `python -m unittest discover -s tests`, and `python -m compileall main.py src tests` pass. Next work should implement real sample/schema extraction and timestamp-aware evidence generation.
- `2026-04-28 01:45:00 -0700` | `uncommitted` | `Codex` | Added schema/sample profiling for readable sources and field-role inference for CSV/JSON data.
- Current place: Schema profiling is local and tests pass. Next work should turn schema profiles into timestamp-aware evidence and lightweight metric/log summaries.
- `2026-04-28 01:55:00 -0700` | `uncommitted` | `Codex` | Added schema-derived evidence, timestamp examples, numeric sample summaries, and Markdown report output.
- Current place: `python main.py`, `python -m unittest discover -s tests`, and `python -m compileall main.py src tests` pass. Next work should build early anomaly candidates from numeric summaries and user-provided SLI/time windows.
- `2026-04-28 02:00:00 -0700` | `uncommitted` | `Codex` | Added early numeric-spread anomaly candidates and full deterministic RCA agent workflow coverage.
- Current place: 8 unittest tests pass. Local branch has commits ahead of origin because `git push origin main` is timing out after commit creation.
- `2026-04-28 02:02:00 -0700` | `uncommitted` | `Codex` | Added initial RCA hypothesis generation from anomaly candidates and included hypotheses in JSON/Markdown reports.
- Current place: 9 unittest tests pass. Next work should make hypotheses time-window aware and add richer source-type classification based on inferred schemas.
- `2026-04-28 03:17:00 -0700` | `uncommitted` | `Codex` | Added numeric observations with timestamp/entity propagation and time-aligned anomaly candidate scoring.
- Current place: 10 unittest tests pass. Next work should infer source categories from schema roles and start building entity extraction beyond CSV headers.
- `2026-04-28 03:20:00 -0700` | `uncommitted` | `Codex` | Added schema-inferred source kinds and initial entity extraction from metric observations.
- Current place: 11 unittest tests pass. Next work should add log/message summarization and use extracted entities to strengthen hypothesis ranking.
- `2026-04-28 03:22:00 -0700` | `uncommitted` | `Codex` | Added text/log signal summaries with error, warning, and info counts plus evidence generation.
- Current place: 12 unittest tests pass. Next work should extract message templates and use entity/time-aligned evidence density to rank hypotheses.
- `2026-04-28 03:25:00 -0700` | `uncommitted` | `Codex` | Added repeated log message-template extraction, severity inference, and evidence generation.
- Current place: 13 unittest tests pass. Next work should add burst detection for repeated templates and then feed template/time/entity density into hypothesis ranking.
- `2026-04-28 03:27:00 -0700` | `uncommitted` | `Codex` | Added minute-level repeated message burst detection and supporting evidence.
- Current place: 14 unittest tests pass. Next work should use burst evidence and time-aligned metric candidates to improve hypothesis ranking and report confidence.
- `2026-04-28 03:30:00 -0700` | `uncommitted` | `Codex` | Added evidence-aware hypothesis ranking, supporting evidence IDs, minute-level anomaly alignment, and report confidence derivation.
- Current place: 15 unittest tests pass. Next work should extend executable tool execution into focused time-window/entity filtering and then start the first real generate-validate-execute RLM loop.
- `2026-04-28 03:33:00 -0700` | `uncommitted` | `Codex` | Added focused read-only tool execution for time-window/entity line matches with supporting evidence output.
- Current place: 16 unittest tests pass. Next work should add structured extraction outputs per source type and then build the first deterministic generate-validate-execute loop skeleton.
- `2026-04-28 03:35:00 -0700` | `uncommitted` | `Codex` | Added Pydantic investigation-cycle state for the deterministic generate-validate-execute-update workflow and exposed it in reports.
- Current place: 16 unittest tests pass. Next work should turn the deterministic cycle into a bounded LLM/RLM-controlled loop and add structured extraction outputs per source type.
- `2026-04-28 06:55:00 -0700` | `uncommitted` | `Codex` | Added configurable bounded investigation cycles, cycle-scoped evidence IDs, and first-pass structured extraction records from focused tool execution.
- Current place: `python main.py`, `python -m unittest discover -s tests`, and `python -m compileall main.py src tests` pass. Next work should deepen extraction models by source type and connect the bounded cycle to an LLM/RLM planner.
