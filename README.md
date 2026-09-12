# 🚀 FreeAI — Smart API Gateway & LLM Router

**FreeAI** é um API Gateway e LLM Router inteligente, pré-configurado, projetado para centralizar o acesso a modelos de IA de provedores gratuitos e freemium (Google Gemini, Groq, OpenRouter, etc.) em um único proxy local compatível com a especificação OpenAI REST API (`/v1`).

---

## ✨ Diferenciais Chave (v1.0.0)

1. **Fallback Inteligente Automático:** Sem necessidade de tabelas estáticas manuais de fallback. O sistema constrói dinamicamente as filas de fallback com base nas capacidades e listas de **tipos** declaradas por cada modelo (`types: ["chat"]`, `["code"]`, `["embedding"]`, `["tts"]`, `["stt"]`).
2. **Aliases Virtuais:** Roteamento simplificado através de aliases como `chat`, `coder`, `embed`, `tts` e `stt`, agrupando automaticamente todos os modelos elegíveis por ordem sequencial de declaração.
3. **Resiliência Nativa em Memória:** Tratamento automático de Rate Limits (cooldown por minuto vs. diário), instabilidade de serviço (500/503) e desativação temporária por credenciais inválidas (401) ou modelos não encontrados (404).
4. **Interface CLI Integrada:** Gerenciamento simples do proxy via `freeai start`, `freeai status`, `freeai models`, `freeai check` e `freeai ping`.
5. **Compatibilidade Total OpenAI (`/v1`):** Funciona como um drop-in replacement para qualquer SDK compatível com OpenAI (Agno, Cursor, VS Code, LangChain, LlamaIndex, Python `openai`).

---

## ⚡ Guia Rápido de Instalação e Uso

### 1. Pré-requisitos
* Python >= 3.12
* [`uv`](https://github.com/astral-sh/uv) instalado

### 2. Instalação de Dependências
```bash
git clone https://github.com/vinifreittas/FreeAI.git
cd FreeAI
uv sync
```

### 3. Configuração do Arquivo `.env`
Copie o arquivo `.env.example` para `.env` e defina suas chaves de API dos provedores gratuitos:

```env
HOST=0.0.0.0
PORT=4000
FREEAI_API_KEY=sua-chave-bearer-opcional

# Chaves dos Provedores (Preencha as que desejar utilizar)
GEMINI_API_KEY=sua-chave-google-ai-studio
GROQ_API_KEY=sua-chave-groq-cloud
OPENROUTER_API_KEY=sua-chave-openrouter
```

### 4. Executando o Proxy Gateway
```bash
uv run freeai start
```
O servidor iniciará em `http://localhost:4000/v1`.

---

## 🛠️ Comandos da CLI (`freeai`)

| Comando | Descrição |
| :--- | :--- |
| `uv run freeai start` | Inicia o servidor HTTP API Gateway (opções: `--host`, `--port`, `--reload`) |
| `uv run freeai status` | Exibe o status da aplicação, host, porta, Bearer Token status e rotas do catálogo |
| `uv run freeai models` | Exibe tabelas Rich com aliases resolvidos, cadeias de fallback e modelos por provedor |
| `uv run freeai check` | Realiza diagnóstico de disponibilidade das variáveis de ambiente de cada provedor |
| `uv run freeai ping` | Envia uma requisição de teste para o modelo/alias desejado (`--alias chat`) |

---

## 💡 Exemplos de Integração

### Exemplo com SDK Oficial da OpenAI (Python)
```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:4000/v1",
    api_key="sk-freeai-local", # Ou sua FREEAI_API_KEY se configurada
)

response = client.chat.completions.create(
    model="chat",  # Usa o alias virtual 'chat' ou ID específico 'gemini-3.5-flash'
    messages=[{"role": "user", "content": "Explique o conceito de API Gateway em poucas palavras."}],
)

print(response.choices[0].message.content)
```

### Exemplo de Streaming SSE
```python
response = client.chat.completions.create(
    model="chat",
    messages=[{"role": "user", "content": "Escreva um poema curto sobre resiliência."}],
    stream=True,
)

for chunk in response:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
```

---

## 🏗️ Arquitetura em Camadas

```
src/freeai/
├── core/       # Configurações (config.yaml), Pydantic Settings & Algoritmo de Roteamento Inteligente
├── services/   # Engine Resiliente (Router) com LiteLLM SDK puro e cooldowns em memória
├── api/        # Servidor FastAPI e endpoints REST OpenAI (/v1)
└── cli.py      # Interface de linha de comando Typer (start, models, status, check, ping)
```

---

## 📄 Licença
Distribuído sob a licença MIT. Consulte `LICENSE` para mais detalhes.