# 🤖 AGENTS.md — AI Agent Guidelines for FreeAI

This document provides high-level architectural context, coding conventions, repository navigation, and operational rules for AI agents working in the **FreeAI** repository.

---

## 📌 1. Project Overview & Tech Stack

**FreeAI** is a pre-configured, intelligent API Gateway and LLM router designed for free and freemium AI model providers. It acts as a smart proxy with model similarity fallback, route aliases (e.g., `chat`, `coder`), custom cooldowns, and an OpenAI-compatible REST API interface.

* **Language:** Python >= 3.12 (managed via `uv`)
* **API Gateway & Framework:** [FastAPI](https://fastapi.tiangolo.com) + [Uvicorn](https://www.uvicorn.org)
* **LLM Routing Engine:** [LiteLLM](https://github.com/BerriAI/litellm) (`litellm.Router`)
* **CLI Framework:** [Typer](https://typer.tiangolo.com) + [Rich](https://rich.readthedocs.io)
* **Config & Settings:** [Pydantic](https://docs.pydantic.dev) (`pydantic-settings`) + `PyYAML`
* **Supported Providers:** Google Gemini, Groq, OpenRouter, Cloudflare Workers AI, Nvidia NIM
* **Tooling:** `ruff` (linter/formatter), `pytest` / `anyio` (testing), `deadcode`, `pre-commit`

### Environment & Configuration Files
* **Models Config:** `src/freeai/config/models.yaml` (overridable via `MODELS_CONFIG_PATH`)
* **Environment File:** `.env` (`HOST`, `PORT`, `FREEAI_API_KEY`, provider API keys like `GEMINI_API_KEY`, `GROQ_API_KEY`, `OPENROUTER_API_KEY`, `CLOUDFLARE_API_KEY`, `NVIDIA_NIM_API_KEY`)

---

## 🏗️ 2. Architecture & System Data Flow

FreeAI strictly follows a modular, layered architecture:

```
src/freeai/
├── config/           # Settings management, Pydantic schemas, YAML loader & fallback resolution logic.
├── routing/          # LiteLLM Router instantiation, provider parameter mapping & fallback matrices.
├── gateway/          # FastAPI server, OpenAI-compatible REST endpoints (/v1) & Bearer token auth.
└── cli/              # Presentation layer: Typer CLI application (start, models, status, check, ping).
```

### ⚠️ The Golden Dependency Rule
```
config  ←  routing  ←  gateway  ←  cli
```

### Data & Execution Flow Pattern
`HTTP Request / Agno Agent / CLI Ping` ➔ `FastAPI Gateway Route (/v1)` ➔ `Auth Middleware (verify_bearer_token)` ➔ `LiteLLM Router (build_router)` ➔ `Remote Provider API (Gemini/Groq/OpenRouter/Nvidia/Cloudflare)` ➔ `SSE Stream / JSON Response`

---

## 🗺️ 3. Repository Directory Map

```
src/freeai/
├── __init__.py                      # Package initialization
├── __main__.py                      # CLI entry point (python -m freeai)
├── config/                          # Configuration & Settings module
│   ├── __init__.py                  # Exports get_settings, Settings, domain models
│   ├── settings.py                  # Pydantic Settings, provider/model/alias schemas & fallback resolver
│   └── models.yaml                  # Provider definitions, backend models, aliases & fallbacks
├── routing/                         # LLM Routing module
│   ├── __init__.py                  # Exports build_router
│   └── router.py                    # Constructs litellm.Router instance with model list & fallbacks
├── gateway/                         # API Gateway module (FastAPI)
│   ├── __init__.py                  # Exports create_app
│   ├── server.py                    # FastAPI app factory with lifespan router setup
│   ├── routes.py                    # OpenAI-compatible /v1 endpoints (chat, embeddings, audio, models)
│   └── auth.py                      # HTTP Bearer token verification dependency
└── cli/                             # Presentation layer (Typer CLI)
    ├── __init__.py                  # Exports main CLI app
    └── main.py                      # Typer subcommands (start, models, status, check, ping)
```

---

## ⚙️ 4. Subsystems Overview

1. **Configuration Subsystem (`config/`)**: `Settings` loads configuration from `models.yaml` and `.env` using `pydantic-settings`. Manages provider/model mapping, dynamic alias resolution (`resolve_alias`), and similarity/capability-matched fallback discovery (`get_fallbacks_for`).
2. **Routing Subsystem (`routing/`)**: `build_router()` configures a `litellm.Router` instance with target backend models and aliases (`model_list`), usage-based routing strategies, retry/cooldown policies, and automatic fallback matrices.
3. **Gateway Subsystem (`gateway/`)**: FastAPI application delivering OpenAI-compatible REST endpoints (`/v1/chat/completions` with SSE streaming, `/v1/embeddings`, `/v1/audio/speech`, `/v1/audio/transcriptions`, `/v1/models`). Optional HTTP Bearer authentication via `verify_bearer_token`.
4. **CLI Subsystem (`cli/`)**: Typer command-line engine providing management subcommands:
   * `start`: Runs Uvicorn server hosting the FreeAI API Gateway.
   * `models`: Displays configured route aliases and provider model mappings in Rich tables.
   * `status`: Shows server host/port, Bearer key status, config path, loaded provider count.
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

* **Add a Provider, Model, or Alias:** Edit `src/freeai/config/models.yaml` and add corresponding API key definitions in `.env.example` / `.env`.
* **Add a CLI Command:** Add a new `@app.command()` in `src/freeai/cli/main.py`.
* **Add an API Endpoint:** Add a new route handler in `src/freeai/gateway/routes.py`.
* **Modify Router Behavior / Fallback Rules:** Adjust `build_router()` in `src/freeai/routing/router.py` or fallback generation in `src/freeai/config/settings.py`.

---

## 🎯 7. Non-Negotiable Operational Rules for Agents

Any AI agent working on FreeAI must strictly adhere to these 5 rules:

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
  4. Were tests executed with `uv run pytest` and verified to pass?

### 5. Continuous Documentation Maintenance (Keep AGENTS.md Updated)
* Always keep `AGENTS.md` updated whenever architectural patterns, conventions, commands, or workflows evolve.

