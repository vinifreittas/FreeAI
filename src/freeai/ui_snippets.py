import asyncio

import streamlit as st

from freeai.api.gateway_manager import reload_gateway_catalog
from freeai.core import reload_settings
from freeai.core.storage import load_vault, save_vault
from freeai.services.key_validator import validate_provider_key


def _run_key_check(provider_id: str, key: str, status_key: str, msg_key: str, api_key_env: str) -> None:
    vault = load_vault()
    if not key or not key.strip():
        vault[api_key_env] = ""
        vault[f"{api_key_env}_VALIDATED"] = False
        save_vault(vault)
        reload_settings()
        st.cache_resource.clear()
        reload_gateway_catalog()
        st.session_state[status_key] = None
        st.session_state[msg_key] = ""
        return
    ok, msg = asyncio.run(validate_provider_key(provider_id, key.strip()))
    vault[api_key_env] = key.strip()
    vault[f"{api_key_env}_VALIDATED"] = ok
    save_vault(vault)
    reload_settings()
    st.cache_resource.clear()
    reload_gateway_catalog()
    st.session_state[status_key] = ok
    st.session_state[msg_key] = msg


def key_input_with_status(label: str, vault_val: str, provider_id: str, api_key_env: str, input_key: str) -> str:
    """Password text_input with inline validation status and descriptive feedback."""
    status_key = f"_key_status_{input_key}"
    msg_key = f"_key_msg_{input_key}"

    # Restore initial state from vault on page reload
    if status_key not in st.session_state and vault_val:
        vault = load_vault()
        validated = vault.get(f"{api_key_env}_VALIDATED")
        if validated is not None:
            st.session_state[status_key] = validated

    def _on_change() -> None:
        _run_key_check(provider_id, st.session_state[input_key], status_key, msg_key, api_key_env)

    col_input, col_status = st.columns([10, 1])
    with col_input:
        val = st.text_input(label, value=vault_val, type="password", key=input_key, on_change=_on_change)
    with col_status:
        status = st.session_state.get(status_key)
        st.write("")
        if status is True:
            st.markdown(":green[✔]")
        elif status is False:
            st.markdown(":red[✘]")

    msg = st.session_state.get(msg_key)
    if msg:
        color = "green" if status is True else "red"
        st.caption(f":{color}[{msg}]")

    return val


def render_client_snippets(base_url: str, api_key: str) -> None:
    """Renders ready-to-use client integration snippets (Python, cURL, Open WebUI)."""
    bearer_val = api_key or "freeai"
    exp = st.expander("🔌 Exemplos de Integração (Python, cURL, Cursor / Open WebUI)", on_change="rerun")
    if exp.open:
        with exp:
            t1, t2, t3 = st.tabs(["Python (OpenAI SDK)", "cURL", "Cursor / Open WebUI"])
            with t1:
                code_py = (
                    f"from openai import OpenAI\n\n"
                    f'client = OpenAI(base_url="{base_url}/v1", api_key="{bearer_val}")\n'
                    f"response = client.chat.completions.create(\n"
                    f'    model="chat",\n'
                    f'    messages=[{{"role": "user", "content": "Olá!"}}],\n'
                    f")\n"
                    f"print(response.choices[0].message.content)"
                )
                st.code(code_py, language="python")
            with t2:
                auth_flag = f'-H "Authorization: Bearer {bearer_val}" ' if api_key else ""
                code_curl = (
                    f'curl -X POST "{base_url}/v1/chat/completions" \\\n'
                    f'  -H "Content-Type: application/json" \\\n'
                    f"  {auth_flag}\\\n"
                    f'  -d \'{{"model": "chat", "messages": [{{"role": "user", "content": "Olá!"}}]}}\''
                )
                st.code(code_curl, language="bash")
            with t3:
                st.markdown(
                    f"- **Base URL:** `{base_url}/v1`\n"
                    f"- **API Key:** `{bearer_val}`\n"
                    f"- **Modelos e Aliases:** `chat`, `coder`, `embed`, `tts`, `stt`\n"
                )
