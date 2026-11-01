# 🤖 FreeAI

> **Smart API Gateway and LLM Router for free and freemium AI providers.**  
> Unify Google Gemini, Groq, and OpenRouter behind a single local OpenAI-compatible endpoint with automatic fallback and a web interface.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![uv](https://img.shields.io/badge/managed_by-uv-DE5FE9.svg?logo=astral&logoColor=white)](https://docs.astral.sh/uv/)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B.svg?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ⚡ Installation and Usage Modes

**FreeAI** can be used in two ways: as a **standalone application** (REST gateway server + web dashboard) or as a **lightweight library/SDK** directly in other Python projects.

### 1. Full Application Mode (Standalone Gateway, CLI & Web UI)

To run the Streamlit dashboard and local OpenAI-compatible REST server, install with the `[app]` extra:

```bash
# As a global tool with uv (Recommended)
uv tool install "freeai[app]"
freeai

# Or with pip
pip install "freeai[app]"
freeai
```

When started, the web dashboard opens automatically in your browser (`http://localhost:8501`) and the API gateway runs in the background (`http://localhost:4000/v1`).

### 2. Lightweight Library / SDK Mode (In-Process)

If you already have a Python project (e.g., an **Agno** agent, **LangChain** app, or bot) and only need smart fallback routing **without heavy server/UI dependencies** (no FastAPI, Uvicorn, or Streamlit):

```bash
# Minimal and fast install
uv add freeai
# or: pip install freeai
```

Use the native adapters directly in code, without starting any HTTP server:

```python
# Agno Agent example
from agno.agent import Agent
from freeai import FreeAIChat

agent = Agent(model=FreeAIChat(id="chat"))
response = agent.run("What is the capital of France?")
print(response.content)
```

```python
# LangChain example
from freeai import ChatFreeAI

llm = ChatFreeAI(model="chat")
print(llm.invoke("Explain what Python is").content)
```

---

## 🚀 How to Use

1. **Configure your keys:** Open the **Settings** tab in the web dashboard and enter your API keys (Google Gemini, Groq, or OpenRouter). Credentials are stored encrypted in your local vault (`~/.freeai/vault.json`).
2. **Connect your apps:** Point any library, IDE, or tool to FreeAI:
   - **Base URL:** `http://localhost:4000/v1`
   - **API Key:** `sk-freeai-local` (or your configured token)
   - **Model:** `chat`, `coder`, or `embed` (with automatic fallback on rate limit)

### Quick Example (Python)

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:4000/v1", api_key="sk-freeai-local")

response = client.chat.completions.create(
    model="chat",
    messages=[{"role": "user", "content": "Hello, FreeAI!"}],
)

print(response.choices[0].message.content)
```

Natively compatible with **Cursor**, **VS Code (Cline / Continue)**, **LangChain**, **Agno**, and any tool that supports the OpenAI API.

---

## 🛠️ For Developers & Contributors

If you want to run from source, contribute, or understand the project architecture:

👉 See **[`AGENTS.md`](AGENTS.md)**
