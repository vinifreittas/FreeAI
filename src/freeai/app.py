import asyncio
import sys

import streamlit as st

from freeai.api.gateway_manager import (
    get_gateway_info,
    restart_gateway,
    start_gateway,
    stop_gateway,
)
from freeai.core import build_router_catalog, get_settings, load_vault, reload_settings, save_vault
from freeai.services import Router


def run_ui() -> None:
    st.set_page_config(page_title="FreeAI — Gateway & Router", page_icon="⚡", layout="wide")

    # Inicialização automática do Gateway em segundo plano
    if "gateway_auto_started" not in st.session_state:
        start_gateway()
        st.session_state["gateway_auto_started"] = True

    settings = get_settings()
    catalog = build_router_catalog(settings)
    info = get_gateway_info()

    # --- BARRA LATERAL ---
    with st.sidebar:
        st.title("⚡ FreeAI Gateway")
        with st.container(border=True):
            status_color = "green" if info["running"] else "red"
            status_text = "Online" if info["running"] else "Offline"
            st.markdown(f"**Status:** :{status_color}[● {status_text}]")
            st.caption(f"Endpoint: `{info['url']}`")
            st.link_button("Documentação OpenAPI", info["docs_url"], icon=":material/api:")

            col1, col2 = st.columns(2)
            if info["running"]:
                if col1.button("Reiniciar", icon=":material/refresh:"):
                    restart_gateway()
                    st.rerun()
                if col2.button("Parar", icon=":material/stop:"):
                    stop_gateway()
                    st.rerun()
            elif st.button("Iniciar Servidor", icon=":material/play_arrow:"):
                start_gateway()
                st.rerun()

        with st.container(border=True):
            st.subheader("Provedores Ativos")
            for p in settings.providers:
                icon = "check_circle" if p.api_key else "cancel"
                color = "green" if p.api_key else "gray"
                st.markdown(f":{color}[:material/{icon}:] **{p.display_name}** ({len(p.models)} modelos)")

    # --- ABAS PRINCIPAIS ---
    tab_overview, tab_settings, tab_playground = st.tabs(
        [":material/dashboard: Visão geral", ":material/key: Configurações & chaves", ":material/chat: Playground"]
    )

    with tab_overview:
        m1, m2, m3, m4 = st.columns(4)
        active_routes = len(catalog.routes)
        active_providers = sum(1 for p in settings.providers if p.api_key)
        bearer_status = "Protegido" if settings.FREEAI_API_KEY else "Acesso livre"

        m1.metric("Status do gateway", status_text)
        m2.metric("Provedores ativos", f"{active_providers} / {len(settings.providers)}")
        m3.metric("Rotas mapeadas", active_routes)
        m4.metric("Autenticação Bearer", bearer_status)

        st.subheader("Aliases e cadeias de fallback")
        aliases_data = []
        for alias in settings.aliases:
            targets = catalog.get_targets(alias.alias)
            chain = " ➔ ".join(t.litellm_model for t in targets) if targets else "Nenhum alvo ativo"
            aliases_data.append(
                {"Alias": alias.alias, "Tipos": ", ".join(alias.models_types_to_chain), "Fallback Chain": chain}
            )
        st.dataframe(aliases_data, hide_index=True)

    with tab_settings:
        st.subheader("Configurações persistentes protegidas")
        st.caption(
            "Salvo no cofre do usuário (~/.freeai/vault.json) com cifra derivada da máquina e permissão restrita 0600."
        )

        vault = load_vault()
        with st.form("vault_form"):
            st.markdown("#### Chaves de API dos provedores")
            g_key = st.text_input(
                "Google AI Studio Key",
                value=vault.get("GOOGLE_API_KEY", ""),
                type="password",
                help="Chave de api do Google AI Studio",
            )
            groq_key = st.text_input(
                "Groq Cloud Key", value=vault.get("GROQ_API_KEY", ""), type="password", help="Chave de api da Groq"
            )
            or_key = st.text_input(
                "OpenRouter Key",
                value=vault.get("OPENROUTER_API_KEY", ""),
                type="password",
                help="Chave de api do OpenRouter",
            )

            st.markdown("#### Configurações da API Gateway")
            c1, c2 = st.columns(2)
            host_val = c1.text_input("Host de vinculação", value=str(vault.get("HOST", settings.HOST)))
            port_val = c2.number_input("Porta HTTP", value=int(vault.get("PORT", settings.PORT)), step=1)
            token_val = st.text_input(
                "FreeAI Bearer Token (opcional)",
                value=vault.get("FREEAI_API_KEY", settings.FREEAI_API_KEY),
                type="password",
                help="Deixe vazio para acesso aberto no localhost",
            )

            if st.form_submit_button("Salvar configurações", icon=":material/save:"):
                new_vault = {
                    "GOOGLE_API_KEY": g_key.strip(),
                    "GROQ_API_KEY": groq_key.strip(),
                    "OPENROUTER_API_KEY": or_key.strip(),
                    "HOST": host_val.strip(),
                    "PORT": int(port_val),
                    "FREEAI_API_KEY": token_val.strip(),
                }
                save_vault(new_vault)
                reload_settings()
                restart_gateway(host=host_val.strip(), port=int(port_val))
                st.success("Configurações criptografadas e salvas no vault! Servidor recarregado.")
                st.rerun()

    with tab_playground:
        st.subheader("Playground interativo de teste")
        available_targets = list(catalog.routes.keys()) if catalog.routes else ["chat"]
        col_sel, _ = st.columns([2, 2])
        selected_target = col_sel.selectbox("Selecione o alias ou modelo", options=available_targets)

        if "chat_history" not in st.session_state:
            st.session_state["chat_history"] = []

        for msg in st.session_state["chat_history"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if user_prompt := st.chat_input("Digite uma mensagem de teste para o modelo..."):
            st.session_state["chat_history"].append({"role": "user", "content": user_prompt})
            with st.chat_message("user"):
                st.markdown(user_prompt)

            router_inst = Router(
                catalog=catalog,
                minute_cooldown_seconds=settings.router_settings.minute_cooldown_seconds,
                daily_cooldown_seconds=settings.router_settings.daily_cooldown_seconds,
                num_retries=settings.router_settings.num_retries,
            )

            with st.chat_message("assistant"):
                response_box = st.empty()

                async def _call() -> str:
                    res = await router_inst.acompletion(
                        model=selected_target,
                        messages=[{"role": "user", "content": user_prompt}],
                        max_tokens=256,
                    )
                    return res.choices[0].message.content or ""

                try:
                    reply = asyncio.run(_call())
                    response_box.markdown(reply)
                    st.session_state["chat_history"].append({"role": "assistant", "content": reply})
                except Exception as err:
                    response_box.error(f"Erro ao consultar '{selected_target}': {err}")


def main() -> None:
    """Ponto de entrada principal do FreeAI para inicialização do Streamlit."""
    if st.runtime.exists():
        run_ui()
        return

    from streamlit.web import cli as stcli

    sys.argv = ["streamlit", "run", __file__, *sys.argv[1:]]
    sys.exit(stcli.main())


if __name__ == "__main__":
    if st.runtime.exists():
        run_ui()
    else:
        main()
