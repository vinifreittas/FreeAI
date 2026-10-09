import asyncio
import sys

import streamlit as st

from freeai.api.gateway_manager import (
    clear_gateway_cooldowns,
    get_gateway_info,
    get_gateway_router,
    restart_gateway,
    start_gateway,
    stop_gateway,
)
from freeai.core import build_router_catalog, get_settings, load_vault, reload_settings, save_vault
from freeai.ui_snippets import key_input_with_status, render_client_snippets


@st.cache_resource
def _get_cached_settings():
    return get_settings()


def run_ui() -> None:
    st.set_page_config(page_title="FreeAI — Gateway & Router", page_icon="⚡", layout="wide")

    # Automatically start Gateway in background
    if "gateway_auto_started" not in st.session_state:
        start_gateway()
        st.session_state["gateway_auto_started"] = True

    settings = _get_cached_settings()
    catalog = build_router_catalog(settings)
    info = get_gateway_info()

    # --- SIDEBAR ---
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

            router = get_gateway_router()
            cd_data = (
                router.get_cooldown_status()
                if router
                else {"cooldowns": {}, "disabled_models": [], "disabled_providers": []}
            )
            cd_count = len(cd_data["cooldowns"]) + len(cd_data["disabled_models"]) + len(cd_data["disabled_providers"])
            if cd_count > 0:
                st.warning(f"⚠️ {cd_count} modelo(s) em cooldown")
                if st.button("Zerar Cooldowns", icon=":material/restart_alt:"):
                    clear_gateway_cooldowns()
                    st.rerun()

    # --- MAIN TABS ---
    tab_overview, tab_settings, tab_playground = st.tabs(
        [":material/dashboard: Visão geral", ":material/key: Configurações & chaves", ":material/chat: Playground"],
        on_change="rerun",
    )

    if tab_overview.open:
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
            aliases_data = [
                {
                    "Alias": a.alias,
                    "Tipos": ", ".join(a.models_types_to_chain),
                    "Fallback Chain": " ➔ ".join(t.litellm_model for t in catalog.get_targets(a.alias))
                    or "Nenhum alvo ativo",
                }
                for a in settings.aliases
            ]
            st.dataframe(aliases_data, hide_index=True)
            render_client_snippets(info["url"], settings.FREEAI_API_KEY)

    if tab_settings.open:
        with tab_settings:
            st.subheader("Configurações persistentes protegidas")
            st.caption(
                "Salvo no cofre do usuário (~/.freeai/vault.json) com cifra derivada da máquina e permissão restrita 0600."
            )

            vault = load_vault()
            st.markdown("#### Chaves de API dos provedores")
            st.caption("Validadas automaticamente ao pressionar Enter. Salvas no cofre imediatamente.")
            key_input_with_status(
                "Google AI Studio Key", vault.get("GOOGLE_API_KEY", ""), "gemini", "GOOGLE_API_KEY", "g_key_input"
            )
            key_input_with_status(
                "Groq Cloud Key", vault.get("GROQ_API_KEY", ""), "groq", "GROQ_API_KEY", "groq_key_input"
            )
            key_input_with_status(
                "OpenRouter Key",
                vault.get("OPENROUTER_API_KEY", ""),
                "openrouter",
                "OPENROUTER_API_KEY",
                "or_key_input",
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

            if st.button("Salvar configurações de rede", icon=":material/save:"):
                vault.update({"HOST": host_val.strip(), "PORT": int(port_val), "FREEAI_API_KEY": token_val.strip()})
                save_vault(vault)
                reload_settings()
                _get_cached_settings.clear()
                restart_gateway(host=host_val.strip(), port=int(port_val))
                st.success("Configurações de rede salvas! Servidor recarregado.")
                st.rerun()

    if tab_playground.open:
        with tab_playground:
            st.subheader("Playground interativo de teste")
            chat_targets = [name for name, targets in catalog.routes.items() if any("chat" in t.types for t in targets)]
            available_targets = chat_targets or ["chat"]
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

                router_inst = get_gateway_router()

                with st.chat_message("assistant"):
                    response_box = st.empty()

                    if router_inst is None:
                        response_box.error("Gateway offline. Inicie o servidor antes de usar o playground.")
                    else:

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
    if st.runtime.exists():
        run_ui()
        return
    from streamlit.web import cli as stcli

    sys.argv = ["streamlit", "run", __file__, *sys.argv[1:]]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
