# AI Agent Coordination

Last updated: 2026-04-27
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
- `src/intake.py` catalogs customer data files while ignoring repository/system folders.
- `src/profiler.py` creates a first structured profile from the data catalog.
- `src/tools.py` generates, validates, and executes initial read-only investigation tool specs from the data profile.
- `src/reports.py` writes RCA reports as JSON artifacts.
- `src/agent.py` wraps the RCA workflow and prepares optional Pydantic AI integration.
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

- Expand executable tools beyond source availability into real schema inference, sample extraction, timestamp detection, and metric/log summaries.
- Add automated tests for full agent report generation and report writing.
- Add Markdown report output alongside JSON.
- Implement the first real RLM loop: profile data, generate a tool, validate it, execute it, store evidence, then update hypotheses.
- Add dependency documentation or packaging once the first executable workflow stabilizes.

## Current Active Stage

- `2026-04-27 13:55:00 -0700` | `uncommitted` | `Codex` | Created the initial coordination handoff document for the generic RLM/LLM RCA project.
- Current place: Coordination file initialized. Repository contains only the generic plan and this coordination document; implementation has not started yet.
- `2026-04-27 14:05:00 -0700` | `uncommitted` | `Codex` | Built the first runnable RCA scaffold with settings, logger, Pydantic models, data cataloging, profiling, and validated investigation tool specs.
- Current place: `python main.py` and `python -m compileall main.py src` pass. Next work should turn `src/tools.py` specs into executable read-only investigation tools and add tests.
- `2026-04-27 14:10:00 -0700` | `uncommitted` | `Codex` | Added executable read-only tool execution, JSON report writing, environment-driven investigation inputs, and unittest coverage for the pipeline.
- Current place: `python main.py`, `python -m unittest discover -s tests`, and `python -m compileall main.py src tests` pass. Next work should implement real sample/schema extraction and timestamp-aware evidence generation.
