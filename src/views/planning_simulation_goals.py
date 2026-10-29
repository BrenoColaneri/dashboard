"""Páginas 8 a 10: Sensibilidade Financeira, Metas Financeiras Configuráveis e Ticket Médio / Indicadores Simulados."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.charts import (
    apply_corporate_layout,
    chart_goals_attainment,
    chart_sensitivity_bars,
)
from src.config import (
    CAC_SIMULATED_PREMISE,
    KPI_CATALOG,
    LTV_CAC_SIMULATED_PREMISE,
    LTV_SIMULATED_PREMISE,
    PALETTE,
    WACC_MODEL_PREMISE,
    format_by_unit,
    format_currency_brl,
    format_multiple_br,
    format_number_br,
    format_pct_br,
    is_valid_number,
)
from src.data_processing import ProcessedDataStore, filter_panel
from src.financial_kpis import (
    evaluate_all_goals,
    investigate_ticket_medio,
    summarize_kpis_for_selection,
)
from src.sensitivity_analysis import (
    CustomerSimulationParams,
    SensitivityParams,
    compare_multiple_hypotheses,
    run_financial_sensitivity,
    simulate_customer_unit_economics,
)
from src.ui_components import (
    render_callout,
    render_corporate_dataframe,
    render_data_footer,
    render_empty_state,
    render_kpi_grid,
    render_section_header,
    render_top_header,
)


def render_page_sensibilidade(
    store: ProcessedDataStore,
    active_scenario: str,
    period_range: tuple[int, int],
) -> None:
    """Página 8 — Simulador Interativo de Sensibilidade Financeira em Memória."""
    render_top_header(
        title="Sensibilidade Financeira — Simulador de Choques Operacionais e Custo de Capital",
        subtitle=(
            "Simulação interativa em memória do impacto de descontos, cupons/preço, volume, custos operacionais "
            "e WACC sobre margens, EBITDA, Resultado Líquido, ROIC e EVA — sem alterar a planilha original."
        ),
        store=store,
        active_scenario=active_scenario,
        period_range=period_range,
        extra_pill="Simulação Isolada em Memória",
    )

    df_scen = filter_panel(store.panel, scenarios=active_scenario, period_range=period_range)
    if df_scen.empty:
        render_empty_state()
        render_data_footer(store)
        return

    render_callout(
        "Garantia de Integridade — Dados Originais 100% Preservados",
        "Todos os valores gerados pelos controles abaixo são calculados exclusivamente em cópias temporárias em memória "
        "e identificados com o selo azul <strong>Simulado</strong>. Nenhuma célula de <code>Contabilidade e Finanças.xlsx</code> "
        "ou das camadas <code>raw</code>/<code>staging</code>/<code>processed</code> é alterada.",
        kind="simulated",
    )

    # Presets rápidos
    render_section_header(
        "1. Parâmetros de Choque Comercial, Operacional e Financeiro",
        "Ajuste livremente os controles ou aplique uma hipótese de referência para explorar cenários.",
    )
    b_col1, b_col2, b_col3, b_col4 = st.columns(4)
    if b_col1.button("Carregar Base Original (0%)", use_container_width=True):
        st.session_state["sens_desconto"] = 0.0
        st.session_state["sens_cupom"] = 0.0
        st.session_state["sens_vol"] = 0.0
        st.session_state["sens_rec_extra"] = 0.0
        st.session_state["sens_custos"] = 0.0
        st.session_state["sens_pvar"] = 100.0
        st.session_state["sens_wacc"] = 12.0
    if b_col2.button("Hipótese Pessimista (Estresse)", use_container_width=True):
        st.session_state["sens_desconto"] = 8.0
        st.session_state["sens_cupom"] = -3.0
        st.session_state["sens_vol"] = -6.0
        st.session_state["sens_rec_extra"] = 0.0
        st.session_state["sens_custos"] = 10.0
        st.session_state["sens_pvar"] = 70.0
        st.session_state["sens_wacc"] = 13.5
    if b_col3.button("Campanha Promocional (Desc. + Vol.)", use_container_width=True):
        st.session_state["sens_desconto"] = 6.0
        st.session_state["sens_cupom"] = -2.0
        st.session_state["sens_vol"] = 12.0
        st.session_state["sens_rec_extra"] = 0.0
        st.session_state["sens_custos"] = 2.0
        st.session_state["sens_pvar"] = 75.0
        st.session_state["sens_wacc"] = 12.0
    if b_col4.button("Hipótese Otimista (Expansão)", use_container_width=True):
        st.session_state["sens_desconto"] = 2.0
        st.session_state["sens_cupom"] = 3.0
        st.session_state["sens_vol"] = 8.0
        st.session_state["sens_rec_extra"] = 0.0
        st.session_state["sens_custos"] = -6.0
        st.session_state["sens_pvar"] = 70.0
        st.session_state["sens_wacc"] = 11.0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        desconto_pct = st.slider(
            "Desconto Comercial (%)",
            min_value=0.0,
            max_value=40.0,
            value=float(st.session_state.get("sens_desconto", 5.0)),
            step=0.5,
            key="sens_desconto",
            help="Reduz o preço líquido faturado sem reduzir o volume físico de operação/custos.",
        )
        cupom_pct = st.slider(
            "Cupom (-) ou Reajuste Preço (+) (%)",
            min_value=-30.0,
            max_value=30.0,
            value=float(st.session_state.get("sens_cupom", 0.0)),
            step=0.5,
            key="sens_cupom",
            help="Valores negativos simulam cupons promocionais; valores positivos simulam repasse tarifário/preço.",
        )
    with c2:
        vol_pct = st.slider(
            "Variação de Volume / Demanda (%)",
            min_value=-40.0,
            max_value=50.0,
            value=float(st.session_state.get("sens_vol", 8.0)),
            step=1.0,
            key="sens_vol",
            help="Afeta simultaneamente a Receita Bruta e a parcela variável dos Custos Operacionais.",
        )
        rec_extra_pct = st.slider(
            "Ajuste Adicional de Receita (%)",
            min_value=-25.0,
            max_value=25.0,
            value=float(st.session_state.get("sens_rec_extra", 0.0)),
            step=0.5,
            key="sens_rec_extra",
            help="Choque exógeno direto sobre o faturamento bruto.",
        )
    with c3:
        custos_pct = st.slider(
            "Pressão (+) ou Eficiência (-) em Custos (%)",
            min_value=-35.0,
            max_value=45.0,
            value=float(st.session_state.get("sens_custos", 3.0)),
            step=0.5,
            key="sens_custos",
            help="Choque percentual sobre os custos operacionais (inflação de insumos ou ganho de produtividade).",
        )
        pvar_pct = st.slider(
            "Parcela Variável dos Custos (%)",
            min_value=0.0,
            max_value=100.0,
            value=float(st.session_state.get("sens_pvar", 100.0)),
            step=5.0,
            key="sens_pvar",
            help="No modelo base, 100% de |DRE - Custos| é tratado como proxy variável. Reduza para simular alavancagem operacional com custos fixos.",
        )
    with c4:
        wacc_pct = st.slider(
            "WACC Simulado (% a.a.)",
            min_value=5.0,
            max_value=25.0,
            value=float(st.session_state.get("sens_wacc", 12.0)),
            step=0.25,
            key="sens_wacc",
            help="Taxa de custo médio ponderado de capital para recálculo do EVA (premissa corporativa base = 12,00%).",
        )
        trib_prop = st.checkbox(
            "Tributos proporcionais à Receita",
            value=True,
            help="Mantém a alíquota efetiva de tributos sobre vendas observada em cada período.",
        )

    params = SensitivityParams(
        desconto_pct=desconto_pct / 100.0,
        cupom_preco_pct=cupom_pct / 100.0,
        variacao_volume_pct=vol_pct / 100.0,
        ajuste_receita_adicional_pct=rec_extra_pct / 100.0,
        variacao_custos_pct=custos_pct / 100.0,
        proporcao_custo_variavel=pvar_pct / 100.0,
        tributos_proporcionais_receita=trib_prop,
        wacc_simulado=wacc_pct / 100.0,
    )

    sens_res = run_financial_sensitivity(df_scen, params)
    st.session_state["last_sensitivity_result"] = sens_res
    comp_tbl = sens_res["comparison_table"]

    # Cartões de impacto principal (Original vs Simulado)
    render_section_header(
        "2. Resumo Executivo do Impacto Simulado (Média Anual no Recorte)",
        "Comparação direta entre o valor real observado na planilha e o valor recalculado sob os choques configurados.",
    )
    highlight_names = [
        "Receita Bruta",
        "Margem de Contribuição",
        "EBITDA Calculado",
        "Margem EBITDA Calculada",
        "Resultado Líquido",
        "ROIC (Anos c/ BP completo)",
        "EVA (Anos c/ BP completo)",
    ]
    tbl_idx = comp_tbl.set_index("Indicador")
    sim_cards: list[dict[str, Any]] = []
    for h_name in highlight_names:
        if h_name not in tbl_idx.index:
            continue
        r = tbl_idx.loc[h_name]
        imp = str(r["Impacto"])
        d_status = "positive" if imp == "Favorável" else ("negative" if imp == "Desfavorável" else "neutral")
        sim_cards.append({
            "label": h_name,
            "value_fmt": str(r["Simulado (Fmt)"]),
            "subtitle": f"Original observado: {r['Original (Fmt)']}",
            "delta_text": f"Impacto: {r['Diferença (Fmt)']} ({r['Variação % (Fmt)']})",
            "delta_status": d_status,
            "badge_text": "Simulado",
            "badge_type": "simulated",
            "tooltip": f"Comparação em memória entre Original ({r['Original (Fmt)']}) e Simulado ({r['Simulado (Fmt)']})",
            "card_variant": "is-simulated",
        })
    render_kpi_grid(sim_cards)

    # Gráficos comparativos
    g1, g2 = st.columns(2)
    with g1:
        st.plotly_chart(chart_sensitivity_bars(comp_tbl, unit_filter="R$"), use_container_width=True)
    with g2:
        st.plotly_chart(chart_sensitivity_bars(comp_tbl, unit_filter="%"), use_container_width=True)

    # Trajetória temporal Original vs Simulado do EBITDA Calculado
    sim_df = sens_res["simulated_df"].sort_values("Ano")
    fig_traj = go.Figure()
    fig_traj.add_trace(
        go.Scatter(
            x=sim_df["Período"],
            y=sim_df["calc_ebitda_calculado"],
            mode="lines+markers",
            name="EBITDA Calculado — Observado",
            line=dict(color=PALETTE["primary"], width=2.8),
        )
    )
    fig_traj.add_trace(
        go.Scatter(
            x=sim_df["Período"],
            y=sim_df["sim_ebitda_calculado"],
            mode="lines+markers",
            name="EBITDA Calculado — Simulado",
            line=dict(color=PALETTE["simulated"], width=2.8, dash="dash"),
        )
    )
    apply_corporate_layout(
        fig_traj,
        f"Trajetória por Período: EBITDA Calculado Observado vs. Simulado ({active_scenario})",
        subtitle="Em R$ ao longo dos períodos filtrados",
        y_title="EBITDA Calculado (R$)",
        height=340,
    )
    fig_traj.update_yaxes(tickprefix="R$ ")
    st.plotly_chart(fig_traj, use_container_width=True)

    # Tabela completa Original vs Simulado
    render_section_header(
        "3. Tabela Analítica de Sensibilidade (Observado vs. Simulado)",
        "Detalhamento de diferenças absolutas, variações percentuais/pontos percentuais e sentido econômico.",
    )
    show_cols = [
        "Indicador",
        "Unidade",
        "Original (Fmt)",
        "Simulado (Fmt)",
        "Diferença (Fmt)",
        "Variação % (Fmt)",
        "Impacto",
    ]
    render_corporate_dataframe(comp_tbl[show_cols])

    # Comparativo de múltiplas hipóteses (Base, Pessimista, Simulação Atual, Otimista)
    render_section_header(
        "4. Matriz Comparativa de Hipóteses (Base vs. Pessimista vs. Sua Simulação vs. Otimista)",
        "Permite avaliar a resiliência do cenário selecionado sob condições adversas e favoráveis padronizadas.",
    )
    multi_df = compare_multiple_hypotheses(df_scen, params)
    multi_display = [
        "Indicador",
        "Unidade",
        "Base Observada (Planilha)",
        "Hipótese Pessimista",
        "Sua Simulação Atual",
        "Hipótese Otimista",
    ]
    render_corporate_dataframe(multi_df[multi_display])

    with st.expander("Premissas Matemáticas Aplicadas nesta Simulação"):
        for exp in sens_res["premises_explanation"]:
            st.markdown(f"- {exp}")

    render_data_footer(store)


def render_page_metas(
    store: ProcessedDataStore,
    active_scenario: str,
    period_range: tuple[int, int],
) -> None:
    """Página 9 — Gestão e Monitoramento de Metas Financeiras Configuráveis pelo Usuário."""
    render_top_header(
        title="Metas Financeiras Configuráveis — Monitoramento Real vs. Alvo",
        subtitle=(
            "Definição transparente de metas gerenciais pelo analista e avaliação automática de desvios, "
            "percentual de atingimento e status semântico."
        ),
        store=store,
        active_scenario=active_scenario,
        period_range=period_range,
    )

    df_scen = filter_panel(store.panel, scenarios=active_scenario, period_range=period_range)
    if df_scen.empty:
        render_empty_state()
        render_data_footer(store)
        return

    render_callout(
        "Transparência Metodológica — Ausência de Metas Oficiais Pré-Cadastradas na Planilha",
        "A planilha corporativa oficial (<code>Contabilidade e Finanças.xlsx</code>) não contém metas fixadas a priori. "
        "Em conformidade com as regras de governança do sistema, <strong>nenhuma meta artificial foi inventada como oficial</strong>: "
        "os indicadores iniciam como <em>Não definida</em> até que você ative e informe os alvos desejados abaixo.",
        kind="info",
    )

    if "configured_goals" not in st.session_state:
        st.session_state["configured_goals"] = {}

    summ = summarize_kpis_for_selection(df_scen)
    current_means = {k: summ[k]["mean"] for k in summ}

    goal_candidates = [
        ("receita", "R$ (ex.: 7800000000 = R$ 7,80 bi)", 1.0, 7_800_000_000.0, 50_000_000.0),
        ("margem_contribuicao", "% (ex.: 80,0 para 80,00%)", 100.0, 80.0, 0.5),
        ("ebitda_calculado", "R$ (ex.: 4500000000 = R$ 4,50 bi)", 1.0, 4_500_000_000.0, 50_000_000.0),
        ("margem_ebitda_calculada", "% (ex.: 62,0 para 62,00%)", 100.0, 62.0, 0.5),
        ("margem_ebitda_modelo", "% (ex.: 70,0 para 70,00%)", 100.0, 70.0, 0.5),
        ("roic", "% (ex.: 25,0; WACC modelo = 12,0%)", 100.0, 25.0, 0.5),
        ("eva", "R$ (ex.: 1000000000 = R$ 1,00 bi)", 1.0, 1_000_000_000.0, 50_000_000.0),
        ("lc", "Índice x (ex.: 1,20 para 1,20x)", 1.0, 1.20, 0.05),
        ("endividamento_geral", "% Teto Máx. (ex.: 85,0 para máx. 85%)", 100.0, 85.0, 1.0),
        ("geracao_caixa", "R$ Média Anual (ex.: 100000000)", 1.0, 100_000_000.0, 10_000_000.0),
    ]

    render_section_header(
        "1. Painel de Configuração de Metas da Sessão",
        "Marque os indicadores que deseja monitorar e defina o valor-alvo. As metas configuradas refletem automaticamente na Visão Executiva e nas Exportações.",
    )
    btn_c1, btn_c2 = st.columns([1, 3])
    if btn_c1.button("Limpar todas as metas", use_container_width=True):
        st.session_state["configured_goals"] = {}
        for k, _, _, _, _ in goal_candidates:
            st.session_state[f"goal_chk_{k}"] = False
        st.rerun()

    cols_cfg = st.columns(2)
    configured_goals: dict[str, float | None] = dict(st.session_state.get("configured_goals", {}))

    for idx, (k, unit_hint, scale_factor, suggested_ui_val, step_val) in enumerate(goal_candidates):
        meta = KPI_CATALOG[k]
        obs_fmt = format_by_unit(current_means.get(k), meta.unit, compact_currency=True)
        sense_lbl = "Teto Máx." if meta.higher_is_better is False else "Piso Mín."
        with cols_cfg[idx % 2]:
            with st.container(border=True):
                already_on = configured_goals.get(k) is not None
                active_chk = st.checkbox(
                    f"**{meta.name}** ({sense_lbl}) — Atual: `{obs_fmt}`",
                    value=already_on,
                    key=f"goal_chk_{k}",
                )
                if active_chk:
                    existing_raw = configured_goals.get(k)
                    default_input = (
                        float(existing_raw * scale_factor)
                        if (existing_raw is not None and is_valid_number(existing_raw))
                        else suggested_ui_val
                    )
                    typed_val = st.number_input(
                        f"Meta para {meta.short_name} [{unit_hint}]",
                        value=default_input,
                        step=step_val,
                        key=f"goal_num_{k}",
                    )
                    configured_goals[k] = float(typed_val) / scale_factor
                else:
                    configured_goals[k] = None

    st.session_state["configured_goals"] = configured_goals

    # Avaliação consolidada
    eval_keys = [k for k, _, _, _, _ in goal_candidates]
    goals_df = evaluate_all_goals(current_means, configured_goals, kpi_keys=eval_keys)
    defined_df = goals_df[goals_df["Classificação"] != "Meta Não Definida"]

    render_section_header(
        "2. Diagnóstico de Cumprimento das Metas",
        f"Comparação calculada para {active_scenario} no intervalo selecionado.",
    )

    if defined_df.empty:
        render_callout(
            "Nenhuma meta ativa no momento",
            "Marque uma ou mais caixas de seleção no painel acima para ativar o acompanhamento gráfico, "
            "os cartões de status e os alertas executivos.",
            kind="warning",
        )
    else:
        g_cards: list[dict[str, Any]] = []
        for _, gr in defined_df.iterrows():
            fav = gr["Favorável"]
            status_cls = "positive" if fav is True else ("neutral" if fav is None else "negative")
            g_cards.append({
                "label": str(gr["Indicador"]),
                "value_fmt": str(gr["Valor Observado (Fmt)"]),
                "subtitle": f"Meta: {gr['Meta Configurada (Fmt)']} • Ating.: {gr['Atingimento (Fmt)']}",
                "delta_text": f"Desvio: {gr['Diferença (Fmt)']}",
                "delta_status": status_cls,
                "badge_text": str(gr["Classificação"]),
                "badge_type": status_cls,
                "card_variant": "" if fav is not False else "is-negative",
            })
        render_kpi_grid(g_cards)
        st.plotly_chart(chart_goals_attainment(defined_df), use_container_width=True)

    render_section_header(
        "3. Quadro Geral de Metas (Definidas e Não Definidas)",
        "Visão transparente de todos os indicadores monitoráveis.",
    )
    disp_cols = [
        "Indicador",
        "Sentido Desejado",
        "Valor Observado (Fmt)",
        "Meta Configurada (Fmt)",
        "Diferença (Fmt)",
        "Atingimento (Fmt)",
        "Classificação",
    ]
    render_corporate_dataframe(goals_df[disp_cols])

    render_data_footer(store)


def render_page_ticket_simulados(
    store: ProcessedDataStore,
    active_scenario: str,
    period_range: tuple[int, int],
) -> None:
    """Página 10 — Auditoria de Ticket Médio e Simulador Integrado de Unit Economics (CAC, LTV, LTV/CAC)."""
    render_top_header(
        title="Ticket Médio e Indicadores Simulados — Auditoria e Unit Economics",
        subtitle=(
            "Diagnóstico técnico sobre a indisponibilidade de Ticket Médio empírico na base contábil original "
            "e simulador parametrizado de Ticket Médio, CAC, LTV e LTV/CAC conforme Dicionario_KPIs."
        ),
        store=store,
        active_scenario=active_scenario,
        period_range=period_range,
        extra_pill="Premissas Explícitas de Simulação",
    )

    audit_tm = investigate_ticket_medio(store.bundle.sheets)

    # Bloco 1: Diagnóstico transparente do Ticket Médio na base original
    render_section_header(
        "1. Diagnóstico Técnico: Ticket Médio na Planilha Original",
        "Verificação automatizada de todas as 9 abas e 160+ colunas da base Contabilidade e Finanças.xlsx.",
    )
    top_cards = [
        {
            "label": "Ticket Médio Observado (Base Real)",
            "value_fmt": "N/D (Indisponível)",
            "subtitle": "Sem dados de pedidos, volume físico ou nº de clientes",
            "delta_text": "Verificado nas 9 abas da planilha original",
            "delta_status": "warning",
            "badge_text": "Não Calculável na Fonte",
            "badge_type": "warning",
            "card_variant": "is-warning",
            "tooltip": "Jamais inventamos um ticket médio observado sem denominador transacional real.",
        },
        {
            "label": "CAC de Referência (Base Corporativa)",
            "value_fmt": f"{format_currency_brl(CAC_SIMULATED_PREMISE)}/cliente",
            "subtitle": "Constante nos 1.200 cenários (Resumo_Cenarios)",
            "delta_text": "Premissa simulada documentada",
            "delta_status": "simulated",
            "badge_text": "Premissa do Modelo",
            "badge_type": "simulated",
            "card_variant": "is-simulated",
        },
        {
            "label": "LTV de Referência (Base Corporativa)",
            "value_fmt": f"{format_currency_brl(LTV_SIMULATED_PREMISE)}/cliente",
            "subtitle": "Ticket × Compras/Ano × Vida Média × Margem",
            "delta_text": "Premissa simulada documentada",
            "delta_status": "simulated",
            "badge_text": "Premissa do Modelo",
            "badge_type": "simulated",
            "card_variant": "is-simulated",
        },
        {
            "label": "LTV / CAC e WACC (Base Corporativa)",
            "value_fmt": format_multiple_br(LTV_CAC_SIMULATED_PREMISE),
            "subtitle": f"WACC do modelo: {format_pct_br(WACC_MODEL_PREMISE)} a.a.",
            "delta_text": "R$ 2.100,00 / R$ 200,00 = 10,50x",
            "delta_status": "simulated",
            "badge_text": "Premissa do Modelo",
            "badge_type": "simulated",
            "card_variant": "is-simulated",
        },
    ]
    render_kpi_grid(top_cards)

    req_list_html = "".join(f"<li>{item}</li>" for item in audit_tm["required_fields_for_real_calculation"])
    render_callout(
        "Por que o Ticket Médio real é exibido como N/D e quais dados seriam necessários?",
        f"A auditoria programática confirmou que a planilha da CTI contém exclusivamente demonstrações financeiras "
        f"contábeis agregadas (DRE, Balanço Patrimonial e DFC), sem colunas transacionais comerciais. "
        f"No <code>Dicionario_KPIs</code>, o termo <em>Ticket médio</em> aparece apenas como componente conceitual da "
        f"fórmula simulada do <strong>LTV simulado</strong> (<code>Ticket médio × Compras/ano × Vida média × Margem %</code>).<br>"
        f"<strong>Dados necessários para cálculo empírico futuro:</strong><ul>{req_list_html}</ul>",
        kind="info",
    )

    # Bloco 2: Simulador editável de Ticket Médio, LTV e CAC
    render_section_header(
        "2. Simulador Parametrizado de Ticket Médio e Unit Economics (Claramente Identificado como Simulação)",
        "Insira premissas comerciais explícitas para estimar Ticket Médio, Receita por Cliente, LTV, CAC, LTV/CAC e Payback.",
    )

    df_scen = filter_panel(store.panel, scenarios=active_scenario, period_range=period_range)
    summ = summarize_kpis_for_selection(df_scen)
    mc_obs = summ["margem_contribuicao"]["mean"]
    rec_obs = summ["receita"]["mean"]

    c1, c2, c3 = st.columns(3)
    with c1:
        ticket_sim = st.number_input(
            "Premissa de Ticket Médio por Transação (R$)",
            min_value=1.0,
            max_value=100_000_000.0,
            value=350.0,
            step=25.0,
            help="Valor médio hipotético por fatura/pedido emitido.",
        )
        compras_ano = st.number_input(
            "Frequência Média de Compras / Faturas por Ano",
            min_value=0.1,
            max_value=365.0,
            value=2.0,
            step=0.5,
        )
    with c2:
        vida_anos = st.number_input(
            "Vida Média / Retenção do Cliente (Anos)",
            min_value=0.25,
            max_value=30.0,
            value=3.75,
            step=0.25,
        )
        use_obs_margin = st.checkbox(
            f"Usar Margem de Contribuição observada de {active_scenario} ({format_pct_br(mc_obs)})",
            value=False,
        )
        if use_obs_margin and is_valid_number(mc_obs):
            margem_ltv = float(np.clip(mc_obs * 100.0, 0.0, 100.0))
            st.caption(f"Margem aplicada automaticamente: **{format_pct_br(mc_obs)}**")
        else:
            margem_ltv = st.slider(
                "Margem de Contribuição p/ LTV (%)",
                min_value=5.0,
                max_value=100.0,
                value=80.0,
                step=1.0,
                help="Com Ticket R$ 350 × 2,0 compras/ano × 3,75 anos × 80% = R$ 2.100,00 (referência da base corporativa).",
            )
    with c3:
        modo_cac_lbl = st.radio(
            "Modo de Parametrização do CAC Simulado:",
            options=["Informar CAC unitário direto (R$/cliente)", "Calcular via Investimento / Novos Clientes"],
        )
        if modo_cac_lbl.startswith("Informar"):
            modo_cac = "direto"
            cac_dir = st.number_input(
                "CAC Unitário Simulado (R$/cliente)",
                min_value=1.0,
                max_value=10_000_000.0,
                value=float(CAC_SIMULATED_PREMISE),
                step=10.0,
            )
            inv_aq, nov_cli = 200_000.0, 1000
        else:
            modo_cac = "investimento_clientes"
            cac_dir = CAC_SIMULATED_PREMISE
            inv_aq = st.number_input(
                "Investimento em Aquisição Comercial (R$)",
                min_value=0.0,
                max_value=1_000_000_000.0,
                value=200_000.0,
                step=10_000.0,
            )
            nov_cli = int(
                st.number_input(
                    "Novos Clientes Adquiridos no Período",
                    min_value=1,
                    max_value=100_000_000,
                    value=1000,
                    step=50,
                )
            )

    sim_out = simulate_customer_unit_economics(
        CustomerSimulationParams(
            ticket_medio_simulado=ticket_sim,
            compras_por_ano=compras_ano,
            vida_media_anos=vida_anos,
            margem_ltv_pct=margem_ltv / 100.0,
            modo_cac=modo_cac,
            cac_direto=cac_dir,
            investimento_aquisicao=inv_aq,
            novos_clientes=nov_cli,
        )
    )

    # Estimativa implícita de transações e clientes ativos compatíveis com a Receita observada do cenário
    transacoes_implicitas = (rec_obs / ticket_sim) if (is_valid_number(rec_obs) and ticket_sim > 0) else np.nan
    clientes_implicitos = (
        rec_obs / sim_out["receita_anual_por_cliente"]
        if (is_valid_number(rec_obs) and sim_out["receita_anual_por_cliente"] > 0)
        else np.nan
    )

    sim_cards = [
        {
            "label": "Ticket Médio (Simulado)",
            "value_fmt": format_currency_brl(sim_out["ticket_medio_simulado"]),
            "subtitle": f"Receita anual/cliente: {format_currency_brl(sim_out['receita_anual_por_cliente'])}",
            "delta_text": "Premissa inserida pelo usuário",
            "delta_status": "simulated",
            "badge_text": "Simulação",
            "badge_type": "simulated",
            "card_variant": "is-simulated",
        },
        {
            "label": "LTV Recalculado (Simulado)",
            "value_fmt": f"{format_currency_brl(sim_out['ltv_simulado'])}/cliente",
            "subtitle": f"Ref. Base: {format_currency_brl(LTV_SIMULATED_PREMISE)}/cliente",
            "delta_text": f"Dif. vs Base: {format_currency_brl(sim_out['diff_vs_e1']['ltv_diff'])}/cliente",
            "delta_status": "simulated",
            "badge_text": "Simulação",
            "badge_type": "simulated",
            "card_variant": "is-simulated",
        },
        {
            "label": "CAC Recalculado (Simulado)",
            "value_fmt": f"{format_currency_brl(sim_out['cac_simulado'])}/cliente",
            "subtitle": f"Ref. Base: {format_currency_brl(CAC_SIMULATED_PREMISE)}/cliente",
            "delta_text": f"Dif. vs Base: {format_currency_brl(sim_out['diff_vs_e1']['cac_diff'])}/cliente",
            "delta_status": "simulated",
            "badge_text": "Simulação",
            "badge_type": "simulated",
            "card_variant": "is-simulated",
        },
        {
            "label": "Relação LTV / CAC (Simulada)",
            "value_fmt": format_multiple_br(sim_out["ltv_cac_simulado"]),
            "subtitle": f"Payback estimado do CAC: {format_number_br(sim_out['payback_cac_meses'], 1)} meses",
            "delta_text": f"Ref. Base: {format_multiple_br(LTV_CAC_SIMULATED_PREMISE)}",
            "delta_status": "positive" if (sim_out["ltv_cac_simulado"] or 0) >= 3.0 else "warning",
            "badge_text": "Simulação",
            "badge_type": "simulated",
            "card_variant": "is-simulated",
        },
        {
            "label": f"Volume Implícito p/ Receita de {active_scenario}",
            "value_fmt": f"{format_number_br(transacoes_implicitas, 0)} trans./ano",
            "subtitle": f"Eq. a ~{format_number_br(clientes_implicitos, 0)} clientes ativos/ano",
            "delta_text": f"Sobre Receita média de {format_currency_brl(rec_obs, compact=True)}",
            "delta_status": "simulated",
            "badge_text": "Simulação Implícita",
            "badge_type": "simulated",
            "card_variant": "is-simulated",
        },
    ]
    render_kpi_grid(sim_cards)

    # Curva de sensibilidade do LTV/CAC em função do Ticket Médio Simulado
    tickets_grid = np.linspace(max(10.0, ticket_sim * 0.4), ticket_sim * 1.8, 25)
    ltv_cac_curve = [
        (t * compras_ano * vida_anos * (margem_ltv / 100.0)) / sim_out["cac_simulado"]
        if sim_out["cac_simulado"] > 0 else np.nan
        for t in tickets_grid
    ]
    fig_curve = go.Figure()
    fig_curve.add_trace(
        go.Scatter(
            x=tickets_grid,
            y=ltv_cac_curve,
            mode="lines+markers",
            name="LTV/CAC Simulado",
            line=dict(color=PALETTE["simulated"], width=2.8),
        )
    )
    fig_curve.add_hline(
        y=LTV_CAC_SIMULATED_PREMISE,
        line_dash="dot",
        line_color="#475569",
        annotation_text="Referência Base (10,50x)",
    )
    apply_corporate_layout(
        fig_curve,
        "Sensibilidade da Relação LTV / CAC em Função do Ticket Médio Simulado",
        subtitle="Simulação paramétrica mantendo frequência, retenção, margem e CAC constantes",
        x_title="Ticket Médio Simulado (R$)",
        y_title="Relação LTV / CAC (x)",
        height=340,
    )
    fig_curve.update_xaxes(tickprefix="R$ ")
    fig_curve.update_yaxes(ticksuffix="x")
    st.plotly_chart(fig_curve, use_container_width=True)

    render_data_footer(store)

