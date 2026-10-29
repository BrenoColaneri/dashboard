"""CTI Global | Plataforma Analítica de Planejamento Financeiro.

Sistema corporativo de análise financeira, Business Intelligence, modelagem econométrica
e governança de dados da CTI Global.
Integra as camadas Raw -> Staging -> Processed com validação contábil 100% reconciliada,
análise estatística descritiva/inferencial, regressão linear múltipla (OLS),
análise de sensibilidade em memória, metas configuráveis e relatórios gerenciais (CSV, XLSX, PDF).
"""

from __future__ import annotations

import streamlit as st

from src.config import KPI_CATALOG, format_period_label
from src.data_loader import (
    build_synthetic_demo_bundle,
    compute_bytes_fingerprint,
    discover_excel_path,
    load_excel_workbook,
)
from src.data_processing import ProcessedDataStore, process_dataset
from src.data_validation import ValidationSummary, run_full_validation
from src.ui_components import inject_corporate_css, render_callout
from src.views.datascience_quality_exports import (
    render_page_analise_estatistica,
    render_page_governanca_qualidade,
    render_page_modelos_analiticos,
    render_page_relatorios_gerenciais,
)
from src.views.executive_and_statements import (
    render_page_balanco,
    render_page_dfc,
    render_page_dre,
    render_page_visao_executiva,
)
from src.views.kpis_scenarios_evolution import (
    render_page_cenarios_rankings,
    render_page_evolucao,
    render_page_indicadores,
)
from src.views.planning_simulation_goals import (
    render_page_metas,
    render_page_sensibilidade,
    render_page_ticket_simulados,
)

st.set_page_config(
    page_title="CTI Global | Plataforma Analítica de Planejamento Financeiro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource(show_spinner="Carregando, tipando e validando a base corporativa oficial da CTI Global...")
def load_and_validate_local_store(resolved_path_str: str) -> tuple[ProcessedDataStore, ValidationSummary]:
    """Carrega planilha local (usando cache Parquet staging verificado por SHA-256) e executa validações."""
    bundle = load_excel_workbook(excel_source=resolved_path_str, use_staging_cache=True)
    store = process_dataset(bundle, persist_processed=True)
    val = run_full_validation(store)
    return store, val


@st.cache_resource(show_spinner="Validando e processando a planilha Excel corporativa enviada via upload...")
def load_and_validate_uploaded_store(
    raw_bytes: bytes,
    filename: str,
    _fp: str,
) -> tuple[ProcessedDataStore, ValidationSummary]:
    """Processa em memória arquivo Excel enviado pelo usuário (ideal para deploy em nuvem)."""
    bundle = load_excel_workbook(excel_source=raw_bytes, source_filename=filename, use_staging_cache=False)
    store = process_dataset(bundle, persist_processed=False)
    val = run_full_validation(store)
    return store, val


@st.cache_resource(show_spinner="Preparando base sintética de demonstração corporativa...")
def load_synthetic_demo_store() -> tuple[ProcessedDataStore, ValidationSummary]:
    """Gera base sintética explicitamente rotulada apenas quando solicitada pelo usuário."""
    bundle = build_synthetic_demo_bundle(n_scenarios=30)
    store = process_dataset(bundle, persist_processed=False)
    val = run_full_validation(store)
    return store, val


PAGES: list[str] = [
    "1. Visão Executiva",
    "2. DRE — Demonstração do Resultado",
    "3. Balanço Patrimonial",
    "4. Fluxo de Caixa",
    "5. Indicadores Financeiros",
    "6. Cenários e Rankings",
    "7. Evolução Financeira",
    "8. Análise de Sensibilidade",
    "9. Metas Financeiras",
    "10. Ticket Médio e Unit Economics",
    "11. Análise Estatística",
    "12. Modelos Analíticos",
    "13. Qualidade e Governança de Dados",
    "14. Relatórios Gerenciais",
]


def _resolve_datastore() -> tuple[ProcessedDataStore, ValidationSummary] | None:
    """Gerencia a seleção segura da fonte de dados (Local -> Upload -> Demo Sintética Opt-in)."""
    with st.sidebar.expander("Fonte de Dados (Excel / Nuvem)", expanded=False):
        uploaded = st.file_uploader(
            "Carregar planilha corporativa (.xlsx)",
            type=["xlsx"],
            help="Envie a planilha oficial 'Contabilidade e Finanças.xlsx' caso execute na nuvem sem base local.",
            key="sidebar_excel_uploader",
        )
        if st.session_state.get("use_synthetic_demo", False):
            if st.button("Sair do Modo Demonstração Sintética", use_container_width=True):
                st.session_state["use_synthetic_demo"] = False
                st.rerun()

    if uploaded is not None:
        try:
            raw_b = uploaded.getvalue()
            fp = compute_bytes_fingerprint(raw_b, uploaded.name)
            st.session_state["use_synthetic_demo"] = False
            return load_and_validate_uploaded_store(raw_b, uploaded.name, fp)
        except Exception as exc:
            st.error(f"Não foi possível processar o arquivo enviado: {exc}")
            return None

    if st.session_state.get("use_synthetic_demo", False):
        return load_synthetic_demo_store()

    local_path = discover_excel_path()
    if local_path is not None and local_path.exists():
        try:
            return load_and_validate_local_store(str(local_path))
        except Exception as exc:
            st.error(f"Erro ao carregar a planilha local '{local_path.name}': {exc}")
            return None

    # Caso nenhum arquivo local exista no servidor
    st.markdown("## Integração de Dados — Planilha Corporativa Necessária")
    render_callout(
        "Base Corporativa Não Localizada no Diretório do Servidor",
        "Por governança e confidencialidade corporativa, o arquivo original "
        "<code>Contabilidade e Finanças.xlsx</code> não é versionado publicamente no repositório. "
        "A plataforma <strong>jamais substitui silenciosamente a fonte oficial por dados fictícios</strong>.<br><br>"
        "Envie a planilha oficial corporativa abaixo para ativar todos os cálculos reais ou explore "
        "o modo de demonstração sintética.",
        kind="warning",
    )
    main_upload = st.file_uploader(
        "Selecione o arquivo corporativo oficial 'Contabilidade e Finanças.xlsx':",
        type=["xlsx"],
        key="main_onboarding_uploader",
    )
    if main_upload is not None:
        try:
            raw_b = main_upload.getvalue()
            fp = compute_bytes_fingerprint(raw_b, main_upload.name)
            return load_and_validate_uploaded_store(raw_b, main_upload.name, fp)
        except Exception as exc:
            st.error(f"Arquivo inválido ou incompleto: {exc}")
            return None

    st.divider()
    if st.button("Explorar Interface em Modo Demonstração Sintética (Dados Não Oficiais)"):
        st.session_state["use_synthetic_demo"] = True
        st.rerun()

    return None


def main() -> None:
    inject_corporate_css()

    st.sidebar.markdown(
        "### CTI GLOBAL\n"
        "<span style='font-size:0.80rem;color:#475569;'>Plataforma Analítica de Planejamento Financeiro</span>",
        unsafe_allow_html=True,
    )

    resolved = _resolve_datastore()
    if resolved is None:
        return
    store, val_summary = resolved

    # ------------------------------------------------------------------
    # Navegação Principal (com suporte a deep-linking via query params)
    # ------------------------------------------------------------------
    if "nav_page_radio" not in st.session_state:
        default_page_idx = 0
        qp_page = st.query_params.get("pagina")
        if qp_page:
            for idx, p in enumerate(PAGES):
                if p.startswith(f"{qp_page}.") or qp_page.lower() in p.lower():
                    default_page_idx = idx
                    break
        st.session_state["nav_page_radio"] = PAGES[default_page_idx]

    selected_page = st.sidebar.radio(
        "Navegação Analítica:",
        options=PAGES,
        key="nav_page_radio",
    )

    st.sidebar.divider()
    st.sidebar.markdown("#### Filtros Globais de Exploração")

    all_scenarios = store.scenarios
    default_scen = "Cen_00001" if "Cen_00001" in all_scenarios else all_scenarios[0]
    min_p = int(min(store.periods))
    max_p = int(max(store.periods))
    all_categories = list(dict.fromkeys(m.category for m in KPI_CATALOG.values()))

    # Inicialização determinística do estado dos filtros
    if "flt_search" not in st.session_state:
        st.session_state["flt_search"] = ""
    if "flt_scenario" not in st.session_state or st.session_state["flt_scenario"] not in all_scenarios:
        st.session_state["flt_scenario"] = default_scen
    if "flt_compare" not in st.session_state:
        st.session_state["flt_compare"] = []
    else:
        st.session_state["flt_compare"] = [c for c in st.session_state["flt_compare"] if c in all_scenarios]
    if "flt_periods" not in st.session_state:
        st.session_state["flt_periods"] = (min_p, max_p)
    if "flt_categories" not in st.session_state:
        st.session_state["flt_categories"] = all_categories

    def _reset_all_filters() -> None:
        st.session_state["flt_search"] = ""
        st.session_state["flt_scenario"] = default_scen
        st.session_state["flt_compare"] = []
        st.session_state["flt_periods"] = (min_p, max_p)
        st.session_state["flt_categories"] = all_categories

    search_txt = st.sidebar.text_input(
        "Buscar cenário por código:",
        key="flt_search",
        placeholder="Ex.: Cen_00462 ou 0462",
    )
    if search_txt.strip():
        matching_scenarios = [s for s in all_scenarios if search_txt.strip().lower() in s.lower()]
        if not matching_scenarios:
            st.sidebar.warning("Nenhum cenário coincide com a busca; exibindo lista completa.")
            matching_scenarios = all_scenarios
        elif st.session_state["flt_scenario"] not in matching_scenarios:
            st.session_state["flt_scenario"] = matching_scenarios[0]
    else:
        matching_scenarios = all_scenarios

    active_scenario = st.sidebar.selectbox(
        "Cenário Principal (Foco):",
        options=matching_scenarios,
        key="flt_scenario",
    )

    compare_scenarios = st.sidebar.multiselect(
        "Comparar com outros cenários (até 4):",
        options=[s for s in all_scenarios if s != active_scenario],
        max_selections=4,
        key="flt_compare",
    )

    period_range = st.sidebar.slider(
        "Intervalo de Períodos (Modelo):",
        min_value=min_p,
        max_value=max_p,
        key="flt_periods",
        help="Períodos numerados Ano 1 a Ano 12 do modelo de planejamento financeiro.",
    )
    st.sidebar.caption(
        f"Recorte ativo: **{format_period_label(period_range[0])}** até **{format_period_label(period_range[1])}**"
    )

    selected_categories = st.sidebar.multiselect(
        "Categorias de KPIs:",
        options=all_categories,
        key="flt_categories",
    )

    st.sidebar.button(
        "Limpar todos os filtros",
        on_click=_reset_all_filters,
        use_container_width=True,
    )

    # Roteamento oficial das 14 páginas corporativas
    if selected_page.startswith("1."):
        render_page_visao_executiva(store, val_summary, active_scenario, compare_scenarios, period_range)
    elif selected_page.startswith("2."):
        render_page_dre(store, active_scenario, compare_scenarios, period_range)
    elif selected_page.startswith("3."):
        render_page_balanco(store, active_scenario, compare_scenarios, period_range)
    elif selected_page.startswith("4."):
        render_page_dfc(store, active_scenario, compare_scenarios, period_range)
    elif selected_page.startswith("5."):
        render_page_indicadores(store, active_scenario, compare_scenarios, period_range, selected_categories)
    elif selected_page.startswith("6."):
        render_page_cenarios_rankings(store, active_scenario, compare_scenarios)
    elif selected_page.startswith("7."):
        render_page_evolucao(store, active_scenario, compare_scenarios, period_range)
    elif selected_page.startswith("8."):
        render_page_sensibilidade(store, active_scenario, period_range)
    elif selected_page.startswith("9."):
        render_page_metas(store, active_scenario, period_range)
    elif selected_page.startswith("10."):
        render_page_ticket_simulados(store, active_scenario, period_range)
    elif selected_page.startswith("11."):
        render_page_analise_estatistica(store, active_scenario, period_range)
    elif selected_page.startswith("12."):
        render_page_modelos_analiticos(store, active_scenario, period_range)
    elif selected_page.startswith("13."):
        render_page_governanca_qualidade(store, val_summary, active_scenario, period_range)
    elif selected_page.startswith("14."):
        render_page_relatorios_gerenciais(store, val_summary, active_scenario, compare_scenarios, period_range)


if __name__ == "__main__":
    main()
