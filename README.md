# 🤖 FreeAI

> **API Gateway e LLM Router inteligente para provedores de IA gratuitos e freemium.**  
> Unifique Google Gemini, Groq e OpenRouter em um único endpoint local compatível com a API OpenAI, com fallback automático e interface web.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![uv](https://img.shields.io/badge/managed_by-uv-DE5FE9.svg?logo=astral&logoColor=white)](https://docs.astral.sh/uv/)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B.svg?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ⚡ Instalação e Execução

Você pode executar o **FreeAI** diretamente sem precisar clonar o repositório:

### Com `uv` (Recomendado)

```bash
uv tool install freeai
freeai
```

### Com `pip`

```bash
pip install freeai
freeai
```

Ao iniciar, o painel web abrirá automaticamente no navegador (`http://localhost:8501`) e o gateway de API estará ativo em segundo plano (`http://localhost:4000/v1`).

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