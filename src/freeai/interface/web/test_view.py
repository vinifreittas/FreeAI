import asyncio
from datetime import datetime

import streamlit as st

from freeai.core import Settings
from freeai.services.model_tester import ModelTestResult, test_all_models


def render_test_view(settings: Settings) -> None:
    """Renderiza a aba interativa de teste de conectividade dos modelos conectados."""
    st.subheader("Diagnóstico e Teste de Conexão dos Modelos")
    st.caption(
        "Verificação em tempo real de latência e disponibilidade dos modelos conectados com provedores aprovados."
    )

    active_providers = [p for p in settings.providers if p.api_key]
    if not active_providers:
        st.warning(
            "⚠️ Nenhum provedor ativo com chave configurada. Configure suas chaves na aba **Configurações & chaves**."
        )
        return

    col_filter, col_btn = st.columns([3, 2])
    options = {"all": "Todos os provedores ativos"}
    for p in active_providers:
        options[p.id] = f"{p.display_name} ({len(p.models)} modelos)"

    with col_filter:
        selected_key = st.selectbox(
            "Filtrar por provedor",
            options=list(options.keys()),
            format_func=lambda k: options[k],
        )

    with col_btn:
        st.write("")
        st.write("")
        run_clicked = st.button(
            "Executar Teste de Conexão",
            icon=":material/play_circle:",
            type="primary",
        )

    provider_id = None if selected_key == "all" else selected_key

    if run_clicked:
        with st.spinner("Testando conectividade e latência dos modelos conectados..."):
            results = asyncio.run(
                test_all_models(
                    settings=settings,
                    provider_id=provider_id,
                    max_concurrency=5,
                    timeout=12.0,
                )
            )
            st.session_state["model_test_results"] = results
            st.session_state["model_test_timestamp"] = datetime.now().strftime("%H:%M:%S")

    results: list[ModelTestResult] | None = st.session_state.get("model_test_results")
    if not results:
        st.info("Clique em **Executar Teste de Conexão** para iniciar o diagnóstico de todos os modelos.")
        return

    ts = st.session_state.get("model_test_timestamp", "")
    st.caption(f"Última verificação executada às **{ts}**")

    # Resumo
    ok_count = sum(1 for r in results if r.status == "OK")
    rl_count = sum(1 for r in results if r.status == "Rate Limit")
    err_count = sum(1 for r in results if r.status not in ("OK", "Rate Limit"))

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Testados", len(results))
    m2.metric("Operacionais (✔)", ok_count)
    m3.metric("Rate Limit (⚠️)", rl_count)
    m4.metric("Falhas (✘)", err_count)

    # Tabela detalhada
    status_icons = {"OK": "✔ Operacional", "Rate Limit": "⚠️ Rate Limit", "Erro": "✘ Falha", "Timeout": "⏱ Timeout"}
    table_data = [
        {
            "Provedor": r.provider_id,
            "Modelo": r.model_id,
            "Tipos": ", ".join(r.types),
            "Status": status_icons.get(r.status, r.status),
            "Latência": f"{r.latency_ms} ms" if r.latency_ms > 0 else "—",
            "Detalhes": r.details,
        }
        for r in results
    ]

    st.dataframe(table_data, hide_index=True)
