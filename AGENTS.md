# 🤖 AGENTS.md — Agent Guidelines for FreeAI

This document provides high-level architectural context, coding conventions, repository navigation, and operational rules for agents working in the **FreeAI** repository.

---

## 📌 1. Project Overview & Tech Stack

**FreeAI** is a pre-configured, intelligent API Gateway, LLM router, and In-Process SDK designed for free and freemium AI model providers. It acts as a smart proxy and library with automatic type-matching fallback, route aliases (e.g., `chat`, `coder`, `embed`, `tts`, `stt`), custom in-memory cooldowns, OpenAI-compatible REST API interface, and native adapters for agent frameworks (**Agno** and **LangChain**).

* **Language:** Python >= 3.12 (managed via `uv`)
* **API Gateway & Framework:** [FastAPI](https://fastapi.tiangolo.com) + [Uvicorn](https://www.uvicorn.org)
* **LLM Engine:** Pure [LiteLLM](https://github.com/BerriAI/litellm) SDK (`litellm.completion`, `litellm.acompletion`, `litellm.aembedding`, etc.)
* **CLI Framework:** [Typer](https://typer.tiangolo.com) (Commands: `serve`, `setup`/`config`, `status`, `ui`)
* **Web UI Dashboard:** [Streamlit](https://streamlit.io)
* **Framework Adapters:** [Agno](https://github.com/agno-agi/agno) (`FreeAIChat`), [LangChain](https://www.langchain.com) (`ChatFreeAI`)
* **Config & Settings:** [Pydantic](https://docs.pydantic.dev) (`pydantic-settings`) + `PyYAML`
* **Supported Providers:** Google Gemini, Groq, OpenRouter
* **Tooling:** `ruff` (linter/formatter), `pytest` / `pytest-asyncio` (testing), `deadcode`, `pre-commit`

### Environment & Configuration Files
* **Settings Config:** `src/freeai/core/config.yaml` (overridable via `SETTINGS_CONFIG_PATH` or `MODELS_CONFIG_PATH`)
* **Protected Secrets Vault:** `~/.freeai/vault.json` (cifrado localmente via machine-derived keystream, pasta 0700 e permissão estrita `chmod 600`)

---

## 🏗️ 2. Architecture & System Data Flow

FreeAI strictly follows Clean Layered Architecture:

```
src/freeai/
├── core/             # Configuration loading, Pydantic schemas, vault storage & Smart Fallback Topology.
├── services/         # Resilient LLM Router engine managing in-memory cooldowns and LiteLLM SDK execution (sync & async).
├── adapters/         # In-Process framework adapters for Agno and LangChain (zero HTTP server required).
├── api/              # FastAPI server, background gateway manager & OpenAI REST endpoints (/v1).
├── interface/        # Presentation layer: Typer CLI commands and Streamlit Web UI.
└── main.py           # Application Composition Root & Launcher.
```

### ⚠️ The Golden Dependency Rule
```
core  ←  services  ←  adapters
                    ←  api
                    ←  interface (cli, web)
                    ←  main.py
```

### Data & Execution Flow Patterns
* **Server Mode:** `Client (cURL / OpenAI SDK)` ➔ `FastAPI Gateway (/v1)` ➔ `Auth Middleware` ➔ `Router (services/llm_router.py)` ➔ `LiteLLM SDK` ➔ `Provider API` ➔ `SSE / JSON`
* **Direct Import Mode (In-Process):** `Agno / LangChain / Script` ➔ `FreeAI Adapter (adapters/agno.py | langchain.py)` ➔ `Router (services/llm_router.py)` ➔ `LiteLLM SDK` ➔ `Provider API`

---

## 🗺️ 3. Repository Directory Map

```
src/freeai/
├── __init__.py                               # Package exports (FreeAIChat, ChatFreeAI, Router, Settings, get_settings)
├── __main__.py                               # Entry point delegating to main.py (`python -m freeai`)
├── main.py                                   # Composition Root: Typer CLI App & Streamlit default launcher
│
├── core/                                     # Domain Configuration & Storage module
│   ├── __init__.py                           # Exports get_settings, reload_settings, load_vault, save_vault
│   ├── config.py                             # Pydantic Settings, schemas & build_router_catalog resolution engine
│   ├── config.yaml                           # Provider definitions, backend models, metadata, aliases & router settings
│   └── storage.py                            # Protected local secrets persistence (0600, machine-derived keystream)
│
├── services/                                 # LLM Routing & Resilience engine
│   ├── __init__.py                           # Exports Router, validate_provider_key, test_all_models, ping_model
│   ├── key_validator.py                      # Multi-model connection health-check testing provider key validity
│   ├── model_tester.py                       # Concurrent health and latency diagnostic tester for connected models
│   └── llm_router.py                         # Resilient Router with sync (completion) and async (acompletion)
│
├── adapters/                                 # Direct In-Process Framework Adapters
│   ├── __init__.py                           # Exports FreeAIChat, ChatFreeAI
│   ├── agno.py                               # FreeAIChat drop-in model for Agno Agent
│   └── langchain.py                          # ChatFreeAI BaseChatModel for LangChain
│
├── api/                                      # API Gateway module (FastAPI)
│   ├── __init__.py                           # Exports create_app, start_gateway, stop_gateway, restart_gateway
│   ├── server.py                             # FastAPI app factory with lifespan router setup
│   ├── gateway_manager.py                    # Thread-based background Uvicorn server lifecycle manager
│   ├── auth.py                               # HTTP Bearer token verification dependency
│   └── v1/                                   # OpenAI specification v1 endpoints
│       ├── __init__.py
│       └── routes.py                         # Endpoints /v1 with diagnostic headers (chat, embeddings, audio, models)
│
└── interface/                                # Presentation Layer
    ├── cli/
    │   ├── __init__.py
    │   └── commands/
    │       ├── __init__.py                   # register_commands(cli: typer.Typer)
    │       ├── serve.py                      # Subcommand: Headless Gateway server
    │       ├── setup.py                      # Subcommand: Interactive terminal key & network setup wizard
    │       ├── status.py                     # Subcommand: Provider, model, and cooldown diagnostics
    │       ├── test.py                       # Subcommand: Diagnostic connection test for connected models
    │       └── ui.py                         # Subcommand: Explicitly launch Streamlit Web UI
    └── web/
        ├── __init__.py                       # Exports main, run_ui
        ├── app.py                            # Unified Streamlit dashboard, playground & tabs
        ├── test_view.py                      # Live connection test panel for active provider models
        └── snippets.py                       # Key inputs with status and integration snippets
```

---

## ⚙️ 4. Subsystems Overview

1. **Configuration & Storage Subsystem (`core/`)**: `Settings` loads configuration from `config.yaml` and `~/.freeai/vault.json` (via `storage.py`). `build_router_catalog()` filters providers missing API keys and builds the `ResolvedCatalog` applying strict type-matching for specific models and subset type-matching for route aliases.
2. **Routing & Diagnostics Subsystem (`services/`)**: `Router` manages in-memory cooldown state (`minute_cooldown_seconds`, `daily_cooldown_seconds`), temporary model/provider disabling on 404/401 errors, and executes calls via pure LiteLLM SDK functions. `model_tester.py` and `key_validator.py` provide resilient multi-candidate health-checks and concurrent connectivity diagnostics.
3. **Adapters Subsystem (`adapters/`)**: Drop-in models for agent frameworks operating in-process without any background HTTP server:
   * `FreeAIChat(id="chat")` for Agno.
   * `ChatFreeAI(model="chat")` for LangChain.
4. **Gateway Subsystem (`api/`)**: FastAPI application delivering OpenAI-compatible REST endpoints (`/v1/chat/completions` with SSE streaming, `/v1/embeddings`, `/v1/audio/speech`, `/v1/audio/transcriptions`, `/v1/models`). Controlled in background via `gateway_manager.py` or foreground via CLI `freeai serve`.
5. **Presentation Layer (`interface/` & `main.py`)**:
   * **Typer CLI (`interface/cli/commands/`)**: Modular commands (`serve`, `setup`, `status`, `test`, `ui`).
   * **Streamlit UI (`interface/web/app.py`, `test_view.py`)**: Dashboard visual, métricas, teste de modelos em tempo real, playground e cofre.
   * **Composition Root (`main.py`)**: Execução padrão sem subcomandos dispara o Streamlit automaticamente.

---

## 🛠️ 5. Development & Validation Commands

All commands must be executed using `uv`:

```bash
# Install dependencies
uv sync --all-groups

# Start FreeAI (inicia a UI Streamlit por padrão ou use subcomandos)
uv run freeai
uv run freeai status
uv run freeai test
uv run freeai serve
uv run freeai setup


# Run test suite
uv run python -m pytest

# Run linter and auto-fix code style (when code is modified)
uv run ruff check --fix src/

# Format code (when code is modified)
uv run ruff format src/

# Detect dead code
uv run deadcode
```

---

## 📍 6. Quick Extension Guide

* **Add a Provider, Model, or Alias:** Edit `src/freeai/core/config.yaml` and add corresponding API key definitions in `.env.example` / `.env`.
* **Add a CLI Subcommand:** Create a new command module in `src/freeai/interface/cli/commands/` and register it in `src/freeai/interface/cli/commands/__init__.py`.
* **Add a Framework Adapter:** Add a new adapter in `src/freeai/adapters/` and export it in `src/freeai/adapters/__init__.py`.
* **Add an API Endpoint:** Add a new route handler in `src/freeai/api/v1/routes.py`.
* **Modify Router Behavior / Fallback Rules:** Adjust `build_router_catalog()` in `src/freeai/core/config.py` or fallback execution in `src/freeai/services/llm_router.py`.

---

## 🎯 7. Non-Negotiable Operational Rules for Agents

Any AI agent working on FreeAI must strictly adhere to these 6 rules:

### 1. Pragmatic Simplicity (KISS & YAGNI)
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
  3. If Python/source code was modified or added, execute static verification (`uv run ruff check --fix src/`), formatting (`uv run ruff format src/`), and test suite (`uv run python -m pytest`).
  4. NEVER force running formatters, linters, or test suites if no Python code was modified.

### 5. Short, Legible & Understandable Code Files
* Every code file must be short (up to 200 lines), easily understandable, and readable.

### 6. Continuous Documentation Maintenance (Keep AGENTS.md Updated)
* Always keep `AGENTS.md` updated whenever architectural patterns, conventions, commands, or workflows evolve.