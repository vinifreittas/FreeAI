# 🤖 FreeAI

> **API Gateway e LLM Router inteligente para provedores de IA gratuitos e freemium.**  
> Unifique Google Gemini, Groq e OpenRouter em um único endpoint local compatível com a API OpenAI, com fallback automático e interface web.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![uv](https://img.shields.io/badge/managed_by-uv-DE5FE9.svg?logo=astral&logoColor=white)](https://docs.astral.sh/uv/)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B.svg?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ⚡ Modos de Instalação e Uso

O **FreeAI** pode ser utilizado de duas formas: como **aplicação standalone** (servidor gateway REST + painel web) ou como **biblioteca/SDK leve** diretamente no código Python de outros projetos.

### 1. Modo Aplicação Completa (Standalone Gateway, CLI & Web UI)

Para rodar o painel visual Streamlit e o servidor REST OpenAI-compatível localmente, instale com o extra `[app]`:

```bash
# Como ferramenta global com uv (Recomendado)
uv tool install "freeai[app]"
freeai

# Ou com pip
pip install "freeai[app]"
freeai
```

Ao iniciar, o painel web abrirá automaticamente no navegador (`http://localhost:8501`) e o gateway de API estará ativo em segundo plano (`http://localhost:4000/v1`).

### 2. Modo Biblioteca / SDK Leve (In-Process)

Se você já possui um projeto Python (ex: agente com **Agno**, aplicação com **LangChain** ou bot) e quer apenas o roteamento inteligente com fallback **sem carregar dependências pesadas de servidor ou UI** (zero FastAPI, Uvicorn ou Streamlit):

```bash
# Instalação minimalista e rápida
uv add freeai
# ou: pip install freeai
```

Use os adaptadores nativos direto no código, sem precisar subir nenhum servidor HTTP:

```python
# Exemplo com Agno Agent
from agno.agent import Agent
from freeai import FreeAIChat

agent = Agent(model=FreeAIChat(id="chat"))
response = agent.run("Qual a capital da França?")
print(response.content)
```

```python
# Exemplo com LangChain
from freeai import ChatFreeAI

llm = ChatFreeAI(model="chat")
print(llm.invoke("Explique o que é Python").content)
```

---

## 🚀 Como Usar

1. **Configure suas chaves:** Abra a aba **Configurações** no painel web e insira suas chaves de API (Google Gemini, Groq ou OpenRouter). Suas credenciais são armazenadas de forma criptografada no seu cofre local (`~/.freeai/vault.json`).
2. **Conecte suas aplicações:** Aponte qualquer biblioteca, IDE ou ferramenta para o FreeAI:
   - **Base URL:** `http://localhost:4000/v1`
   - **API Key:** `sk-freeai-local` (ou o Bearer token configurado)
   - **Model:** `chat`, `coder` ou `embed` (com fallback automático se ocorrer rate limit)

### Exemplo Rápido (Python)

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:4000/v1", api_key="sk-freeai-local")

response = client.chat.completions.create(
    model="chat",
    messages=[{"role": "user", "content": "Olá, FreeAI!"}],
)

print(response.choices[0].message.content)
```

Compatível nativamente com **Cursor**, **VS Code (Cline / Continue)**, **LangChain**, **Agno** e qualquer ferramenta que suporte a API da OpenAI.

---

## 🛠️ Para Desenvolvedores & Contribuidores

Se você deseja rodar a partir do código-fonte, contribuir ou entender a arquitetura do projeto:

👉 Consulte o **[`AGENTS.md`](AGENTS.md)** 