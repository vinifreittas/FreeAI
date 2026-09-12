# 🤖 AGENTS.md — AI Agent Guidelines for FreeAI

This document provides high-level architectural context, coding conventions, repository navigation, and operational rules for AI agents working in the **FreeAI** repository.

---

## 📌 1. Project Overview & Tech Stack

**FreeAI** is a pre-configured, intelligent API Gateway and LLM router designed for free and freemium AI model providers. It acts as a smart proxy with automatic type-matching fallback, route aliases (e.g., `chat`, `coder`, `embed`, `tts`, `stt`), custom in-memory cooldowns, and an OpenAI-compatible REST API interface.

* **Language:** Python >= 3.12 (managed via `uv`)
* **API Gateway & Framework:** [FastAPI](https://fastapi.tiangolo.com) + [Uvicorn](https://www.uvicorn.org)
* **LLM Engine:** Pure [LiteLLM](https://github.com/BerriAI/litellm) SDK (`litellm.acompletion`, `litellm.aembedding`, etc.)
* **CLI Framework:** [Typer](https://typer.tiangolo.com) + [Rich](https://rich.readthedocs.io)
* **Config & Settings:** [Pydantic](https://docs.pydantic.dev) (`pydantic-settings`) + `PyYAML`
* **Supported Providers:** Google Gemini, Groq, OpenRouter
* **Tooling:** `ruff` (linter/formatter), `pytest` / `anyio` (testing), `deadcode`, `pre-commit`

### Environment & Configuration Files
* **Settings Config:** `src/freeai/core/config.yaml` (overridable via `SETTINGS_CONFIG_PATH` or `MODELS_CONFIG_PATH`)
* **Environment File:** `.env` (`HOST`, `PORT`, `FREEAI_API_KEY`, provider API keys: `GOOGLE_API_KEY`, `GROQ_API_KEY`, `OPENROUTER_API_KEY`)

---

## 🏗️ 2. Architecture & System Data Flow

FreeAI strictly follows a modular, layered architecture:

```
src/freeai/
├── core/             # Configuration loading, Pydantic schemas, and Smart Fallback Topology resolution.
├── services/         # Resilient LLM Router engine managing in-memory cooldowns and LiteLLM SDK execution.
├── api/              # FastAPI server, OpenAI-compatible REST endpoints (/v1) & Bearer token auth.
└── cli.py            # Presentation layer: Typer CLI application (start, models, status, check, ping).
```

### ⚠️ The Golden Dependency Rule
```
core  ←  services  ←  api  ←  cli
```

### Data & Execution Flow Pattern
`HTTP Request / Agno Agent / CLI Ping` ➔ `FastAPI Gateway Route (/v1)` ➔ `Auth Middleware (verify_bearer_token)` ➔ `Router (services/llm_router.py)` ➔ `LiteLLM SDK (acompletion/aembedding)` ➔ `Remote Provider API (Gemini/Groq/OpenRouter)` ➔ `SSE Stream / JSON Response`

---

## 🗺️ 3. Repository Directory Map

```
src/freeai/
├── __init__.py                      # Package initialization
├── cli.py                           # Typer CLI subcommands (start, models, status, check, ping)
├── core/                            # Configuration & Settings module
│   ├── __init__.py                  # Exports get_settings, Settings, ResolvedCatalog, build_router_catalog
│   ├── config.py                    # Pydantic Settings, schemas & build_router_catalog resolution engine
│   └── config.yaml                  # Provider definitions, backend models, metadata, aliases & router settings
├── services/                        # LLM Routing & Resilience module
│   ├── __init__.py                  # Exports Router
│   └── llm_router.py                # Resilient Router managing in-memory cooldowns & LiteLLM execution
└── api/                             # API Gateway module (FastAPI)
    ├── __init__.py                  # Exports create_app
    ├── server.py                    # FastAPI app factory with lifespan router setup
    ├── auth.py                      # HTTP Bearer token verification dependency
    └── v1/                          # OpenAI specification v1 endpoints
        ├── __init__.py
        └── routes.py                # Endpoints /v1 (chat, embeddings, audio, models)
```

---

## ⚙️ 4. Subsystems Overview

1. **Configuration Subsystem (`core/`)**: `Settings` loads configuration from `config.yaml` and `.env` using `pydantic-settings`. `build_router_catalog()` filters providers missing API keys and builds the `ResolvedCatalog` applying strict type-matching for specific models and subset type-matching for route aliases.
2. **Routing Subsystem (`services/`)**: `Router` manages in-memory cooldown state (`minute_cooldown_seconds`, `daily_cooldown_seconds`), temporary model/provider disabling on 404/401 errors, and executes calls via pure LiteLLM SDK functions.
3. **Gateway Subsystem (`api/`)**: FastAPI application delivering OpenAI-compatible REST endpoints (`/v1/chat/completions` with SSE streaming, `/v1/embeddings`, `/v1/audio/speech`, `/v1/audio/transcriptions`, `/v1/models`). Optional HTTP Bearer authentication via `verify_bearer_token`.
4. **CLI Subsystem (`cli.py`)**: Typer command-line engine providing management subcommands:
   * `start`: Runs Uvicorn server hosting the FreeAI API Gateway.
   * `models`: Displays configured route aliases, fallback chains, and provider model mappings in Rich tables.
   * `status`: Shows server host/port, Bearer key status, config path, active route count.
   * `check`: Diagnoses environment variable readiness and API key presence across providers.
   * `ping`: Sends a test completion prompt via `Router` to verify endpoint responsiveness.

---

## 🛠️ 5. Development & Validation Commands

All commands must be executed using `uv`:

```bash
# Install dependencies
uv sync

# Start the FreeAI Gateway server
uv run freeai start

# Run CLI management commands
uv run freeai status
uv run freeai models
uv run freeai check
uv run freeai ping --alias chat

# Run linter and auto-fix code style (ALWAYS use --fix)
uv run ruff check --fix src/

# Format code
uv run ruff format src/

# Run test suite
uv run pytest

# Detect dead code
uv run deadcode
```

---

## 📍 6. Quick Extension Guide

* **Add a Provider, Model, or Alias:** Edit `src/freeai/core/config.yaml` and add corresponding API key definitions in `.env.example` / `.env`.
* **Add a CLI Command:** Add a new `@app.command()` in `src/freeai/cli.py`.
* **Add an API Endpoint:** Add a new route handler in `src/freeai/api/v1/routes.py`.
* **Modify Router Behavior / Fallback Rules:** Adjust `build_router_catalog()` in `src/freeai/core/config.py` or fallback execution in `src/freeai/services/llm_router.py`.

---

## 🎯 7. Non-Negotiable Operational Rules for Agents

Any AI agent working on FreeAI must strictly adhere to these 6 rules:

### 1. Pragmatic Simplicity (KISS)
* Solve problems with the minimum necessary code, abstraction, and complexity.
* Avoid over-engineering. NEVER create generic abstractions or unnecessary helper utilities for simple tasks.

### 2. Zero Tolerance for Ambiguity
* Never assume requirements, business logic, architectures, or unstated behaviors.
* If instructions or contracts are unclear, **STOP IMMEDIATELY** and ask for clarification.

### 3. Surgical Scope
* Keep focus strictly restricted to the requested task. Modify only target files and lines.
* NEVER perform peripheral refactoring, formatting edits in adjacent code, or modifications outside the target module.

### 4. Double-Check Verification Protocol
* Verify delivery before completing:
  1. Does the diff strictly address the requested scope?
  2. Are syntax, typing, and imports correct?
  3. Was static verification executed with `uv run ruff check --fix src/`?
  4. Were verification commands executed and verified to pass?

### 5. Short, Legible & Understandable Code Files
* Every code file must be short (up to 200 lines), easily understandable, and readable.

### 6. Continuous Documentation Maintenance (Keep AGENTS.md Updated)
* Always keep `AGENTS.md` updated whenever architectural patterns, conventions, commands, or workflows evolve.