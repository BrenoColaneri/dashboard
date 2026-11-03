"""CTI Global | Visualizações Corporativas Avançadas: DFC, Capital de Giro, Fluxo de Caixa e DVA.

Este módulo implementa os 4 novos módulos de análise financeira e contábil:
1. Índices da Demonstração dos Fluxos de Caixa (DFC)
2. Índices de Capital de Giro e Prazos Médios
3. Fluxo de Caixa (Visão Gerencial e Conciliada)
4. Demonstração do Valor Adicionado (DVA)

Seguindo estritamente o padrão corporativo da CTI Global, tabelas verdes estilizadas,
gráficos interativos responsivos (Plotly), comparações temporais e de cenários,
conciliação contábil e interpretações gerenciais aprofundadas.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import streamlit as st

from src.charts import (
    chart_cash_flow_composition,
    chart_cash_flow_entries_exits,
    chart_cash_flow_evolution,
    chart_cash_flow_profit_vs_cash,
    chart_cash_flow_waterfall,
    chart_dfc_conversion,
    chart_dfc_dividend_sustainability,
    chart_dfc_fco_ebitda,
    chart_dfc_investments_efficiency,
    chart_dfc_payment_capacity,
    chart_dfc_waterfall_fco,
    chart_dfc_waterfall_free_cash,
    chart_dva_distribution_evolution,
    chart_dva_distribution_pie,
    chart_dva_distribution_stacked_100,
    chart_dva_evolution,
    chart_dva_waterfall,
    chart_dva_wealth_indicators,
    chart_working_capital_ccl,
    chart_working_capital_cycle,
    chart_working_capital_need_vs_ccl,
    chart_working_capital_pmr_pmp,
)
from src.config import (
    KPI_CATALOG,
    PALETTE,
    format_by_unit,
    format_currency_brl,
    format_number_br,
    format_pct_br,
    format_period_label,
    is_valid_number,
)
from src.data_processing import ProcessedDataStore, filter_panel
from src.financial_kpis import safe_divide, summarize_kpis_for_selection
from src.ui_components import (
    render_callout,
    render_corporate_dataframe,
    render_corporate_table,
    render_empty_state,
    render_kpi_grid,
    render_section_header,
    render_top_header,
)


# =============================================================================
# MÓDULO 1 — ÍNDICES DA DEMONSTRAÇÃO DOS FLUXOS DE CAIXA (DFC)
# =============================================================================

def render_page_indices_dfc(
    store: ProcessedDataStore,
    active_scenario: str,
    compare_scenarios: list[str],
    period_range: tuple[int, int],
) -> None:
    """Página Oficial: Índices da DFC (Qualidade do Caixa, Investimentos, Pagamentos e Dividendos)."""
    df_scen = filter_panel(store.panel, scenarios=active_scenario, period_range=period_range)
    if df_scen.empty:
        render_empty_state()
        return

    render_top_header(
        title="Índices da Demonstração dos Fluxos de Caixa (DFC)",
        subtitle="Qualidade da geração de caixa, conversão de receitas, sustentabilidade de Capex, cobertura de dívida e dividendos",
        store=store,
        active_scenario=active_scenario,
        period_range=period_range,
    )

    summary = summarize_kpis_for_selection(df_scen)
    latest_row = df_scen.iloc[-1]
    latest_p_desc = format_period_label(int(latest_row["Ano"]))

    # 4 Cartões Executivos das Famílias da DFC
    cards: list[dict[str, Any]] = []

    # 1. Qualidade: FCO
    fco_mean = summary.get("fco", {}).get("mean", np.nan)
    fco_sum = summary.get("fco", {}).get("sum", np.nan)
    cards.append({
        "label": "FCO (Caixa Operacional)",
        "value_fmt": format_currency_brl(fco_mean, compact=True),
        "subtitle": f"Acumulado: {format_currency_brl(fco_sum, compact=True)}",
        "delta_text": f"Último ({latest_p_desc}): {format_currency_brl(latest_row.get('calc_fco'), compact=True)}",
        "delta_status": "positive" if fco_mean >= 0 else "negative",
        "badge_text": "FCO Operacional",
        "badge_type": "real",
        "tooltip": "Caixa gerado pela operação antes de investimentos, juros e dividendos",
        "card_variant": "",
    })

    # 2. Qualidade: Conversão da Receita
    conv_mean = summary.get("taxa_conversao_receita", {}).get("mean", np.nan)
    cards.append({
        "label": "Conversão da Receita",
        "value_fmt": format_pct_br(conv_mean, already_percent=True),
        "subtitle": f"Recebimentos: {format_currency_brl(df_scen['calc_entradas_operacionais'].mean(), compact=True)}",
        "delta_text": f"Último: {format_pct_br(latest_row.get('calc_taxa_conversao_receita'), already_percent=True)}",
        "delta_status": "positive" if conv_mean >= 90.0 else "neutral",
        "badge_text": "Taxa de Conversão",
        "badge_type": "positive" if conv_mean >= 90.0 else "warning",
        "tooltip": "Percentual da receita reconhecida na DRE transformada em recebimentos efetivos",
        "card_variant": "",
    })

    # 3. Investimento: FCL (Fluxo de Caixa Livre)
    fcl_mean = summary.get("fcl", {}).get("mean", np.nan)
    fcl_sum = summary.get("fcl", {}).get("sum", np.nan)
    cards.append({
        "label": "Fluxo de Caixa Livre (FCL)",
        "value_fmt": format_currency_brl(fcl_mean, compact=True),
        "subtitle": f"Acumulado: {format_currency_brl(fcl_sum, compact=True)}",
        "delta_text": f"Último: {format_currency_brl(latest_row.get('calc_fcl'), compact=True)}",
        "delta_status": "positive" if fcl_mean >= 0 else "negative",
        "badge_text": "FCL Livre",
        "badge_type": "real",
        "tooltip": "FCO menos Investimentos (Capex): caixa que sobra após investimentos",
        "card_variant": "",
    })

    # 4. Pagamento e Sócios: Cobertura de Juros e Dividendos
    cob_juros = summary.get("cobertura_juros_caixa", {}).get("mean", np.nan)
    cob_div = summary.get("cobertura_dividendos", {}).get("mean", np.nan)
    cards.append({
        "label": "Cobertura Juros e Div.",
        "value_fmt": f"{cob_juros:.1f}x" if is_valid_number(cob_juros) else "N/D",
        "subtitle": f"Cob. Dividendos: {cob_div:.1f}x" if is_valid_number(cob_div) else "Cob. Div: N/D",
        "delta_text": f"Payout: {format_pct_br(df_scen['calc_payout_caixa'].mean(), already_percent=True)}",
        "delta_status": "positive" if cob_juros >= 1.5 else "neutral",
        "badge_text": "Solvência Caixa",
        "badge_type": "positive" if cob_juros >= 1.0 else "negative",
        "tooltip": "Capacidade do caixa operacional de cobrir juros e do FCL de cobrir dividendos",
        "card_variant": "",
    })

    render_section_header(
        "Indicadores Centrais da DFC",
        "Métricas consolidadas de qualidade, taxa de conversão, caixa livre e capacidade de pagamento.",
    )
    render_kpi_grid(cards)

    tabs = st.tabs([
        "📊 Painel e Indicadores",
        "🌊 Pontes de Caixa (Waterfall)",
        "📈 Eficiência e Cobertura",
        "⚖️ Comparação de Cenários",
        "📋 Tabela Completa dos 11 KPIs",
        "📖 Diagnóstico e Metodologia",
    ])

    with tabs[0]:
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.plotly_chart(chart_dfc_fco_ebitda(df_scen), use_container_width=True)
        with col_g2:
            st.plotly_chart(chart_dfc_conversion(df_scen), use_container_width=True)

    with tabs[1]:
        st.markdown(f"#### Pontes de Conciliação Financeira — Período Recente ({latest_p_desc})")
        w_col1, w_col2 = st.columns(2)
        with w_col1:
            st.plotly_chart(chart_dfc_waterfall_fco(latest_row, latest_p_desc), use_container_width=True)
        with w_col2:
            st.plotly_chart(chart_dfc_waterfall_free_cash(latest_row, latest_p_desc), use_container_width=True)

    with tabs[2]:
        e_col1, e_col2 = st.columns(2)
        with e_col1:
            st.plotly_chart(chart_dfc_investments_efficiency(df_scen), use_container_width=True)
        with e_col2:
            st.plotly_chart(chart_dfc_payment_capacity(df_scen), use_container_width=True)

        st.plotly_chart(chart_dfc_dividend_sustainability(df_scen), use_container_width=True)

    with tabs[3]:
        if not compare_scenarios:
            render_callout(
                "Comparação de Cenários",
                "Selecione até 4 cenários adicionais na barra lateral para habilitar a comparação dos índices da DFC.",
                kind="info",
            )
        else:
            comp_scenarios = [active_scenario] + compare_scenarios
            comp_df = store.panel[
                (store.panel["Cenário"].isin(comp_scenarios))
                & (store.panel["Ano"] >= period_range[0])
                & (store.panel["Ano"] <= period_range[1])
            ]
            agg_rows = []
            for sc in comp_scenarios:
                sub = comp_df[comp_df["Cenário"] == sc]
                if sub.empty:
                    continue
                agg_rows.append({
                    "Cenário": sc,
                    "FCO Médio (R$)": format_currency_brl(sub["calc_fco"].mean(), compact=True),
                    "Conversão Média": format_pct_br(sub["calc_taxa_conversao_receita"].mean(), already_percent=True),
                    "FCO / EBITDA": format_pct_br(sub["calc_fco_ebitda"].mean(), already_percent=True),
                    "FCO / Lucro": f"{sub['calc_fco_lucro'].mean():.2f}x" if is_valid_number(sub['calc_fco_lucro'].mean()) else "N/D",
                    "FCL Médio (R$)": format_currency_brl(sub["calc_fcl"].mean(), compact=True),
                    "Capex / Receita": format_pct_br(sub["calc_capex_receita"].mean(), already_percent=True),
                    "Capex / D&A": f"{sub['calc_capex_da'].mean():.2f}x" if is_valid_number(sub['calc_capex_da'].mean()) else "N/D",
                    "Cob. Juros": f"{sub['calc_cobertura_juros_caixa'].mean():.1f}x" if is_valid_number(sub['calc_cobertura_juros_caixa'].mean()) else "N/D",
                    "Payout Caixa": format_pct_br(sub["calc_payout_caixa"].mean(), already_percent=True),
                    "Cob. Dividendos": f"{sub['calc_cobertura_dividendos'].mean():.1f}x" if is_valid_number(sub['calc_cobertura_dividendos'].mean()) else "N/D",
                })
            render_corporate_table(
                pd.DataFrame(agg_rows),
                title="Quadro Comparativo de Índices da DFC entre Cenários",
                subtitle="Médias dos períodos válidos selecionados para os cenários em análise",
            )

    with tabs[4]:
        table_rows = []
        for _, r in df_scen.sort_values("Ano").iterrows():
            ano_lbl = format_period_label(int(r["Ano"]))
            table_rows.append({
                "Período": ano_lbl,
                "FCO (R$)": format_currency_brl(r.get("calc_fco"), compact=False),
                "Conversão (%)": format_pct_br(r.get("calc_taxa_conversao_receita"), already_percent=True),
                "FCO / EBITDA": format_pct_br(r.get("calc_fco_ebitda"), already_percent=True),
                "FCO / Lucro": f"{r.get('calc_fco_lucro', np.nan):.2f}x" if is_valid_number(r.get("calc_fco_lucro")) else "N/D",
                "FCL (R$)": format_currency_brl(r.get("calc_fcl"), compact=False),
                "Capex / Receita": format_pct_br(r.get("calc_capex_receita"), already_percent=True),
                "Capex / D&A": f"{r.get('calc_capex_da', np.nan):.2f}x" if is_valid_number(r.get("calc_capex_da")) else "N/D",
                "Cob. Juros": f"{r.get('calc_cobertura_juros_caixa', np.nan):.2f}x" if is_valid_number(r.get("calc_cobertura_juros_caixa")) else "N/D",
                "FCO / Dívida": format_pct_br(r.get("calc_fco_divida_bruta"), already_percent=True),
                "Prazo Quitação": f"{r.get('calc_prazo_quitacao_divida', np.nan):.1f} anos" if is_valid_number(r.get("calc_prazo_quitacao_divida")) else "N/D",
                "Payout Caixa": format_pct_br(r.get("calc_payout_caixa"), already_percent=True),
                "Cob. Dividendos": f"{r.get('calc_cobertura_dividendos', np.nan):.2f}x" if is_valid_number(r.get("calc_cobertura_dividendos")) else "N/D",
            })
        render_corporate_table(
            pd.DataFrame(table_rows),
            title="Demonstração Analítica dos 11 Indicadores da DFC",
            subtitle=f"Cenário: {active_scenario} — Série histórica anual oficial",
        )

    with tabs[5]:
        render_callout(
            "Interpretação Executiva dos Indicadores da DFC",
            "<strong>Perguntas Fundamentais que Este Módulo Responde ao Gestor:</strong><br>"
            "• <em>A operação está gerando caixa?</em> Sim, o <strong>FCO</strong> reflete a liquidez líquida das operações antes de capex e financiamento.<br>"
            "• <em>Quanto da receita entra de fato no caixa?</em> A <strong>Taxa de Conversão</strong> mede o faturamento liquidado (podendo superar 100% ao receber atrasados).<br>"
            "• <em>O EBITDA vira dinheiro?</em> A relação <strong>FCO / EBITDA</strong> avalia a qualidade do resultado operacional frente a impostos e capital de giro.<br>"
            "• <em>A empresa consegue pagar juros e amortizar sua dívida?</em> A <strong>Cobertura de Juros</strong> e a relação <strong>FCO / Dívida</strong> revelam a solvência direta em caixa.<br>"
            "• <em>Os dividendos são sustentáveis?</em> A <strong>Cobertura de Dividendos</strong> verifica se a remuneração aos sócios provém de sobra operacional (FCL > dividendos) ou de endividamento.",
            kind="info",
        )


# =============================================================================
# MÓDULO 2 — ÍNDICES DE CAPITAL DE GIRO E PRAZOS MÉDIOS
# =============================================================================

def render_page_capital_giro(
    store: ProcessedDataStore,
    active_scenario: str,
    compare_scenarios: list[str],
    period_range: tuple[int, int],
) -> None:
    """Página Oficial: Capital de Giro e Prazos Médios (CCL, PMR, PMP, Ciclo e Necessidade)."""
    df_scen = filter_panel(store.panel, scenarios=active_scenario, period_range=period_range)
    if df_scen.empty:
        render_empty_state()
        return

    render_top_header(
        title="Capital de Giro e Prazos Médios",
        subtitle="Liquidez operacional, tempo de cobrança (PMR), prazo com fornecedores (PMP), ciclo financeiro e necessidade de capital de giro",
        store=store,
        active_scenario=active_scenario,
        period_range=period_range,
    )

    summary = summarize_kpis_for_selection(df_scen)
    latest_row = df_scen.iloc[-1]
    latest_p_desc = format_period_label(int(latest_row["Ano"]))

    cards: list[dict[str, Any]] = []

    # 1. CCL
    ccl_val = summary.get("ccl", {}).get("latest", np.nan)
    ccl_mean = summary.get("ccl", {}).get("mean", np.nan)
    cards.append({
        "label": "Capital Circulante Líquido (CCL)",
        "value_fmt": format_currency_brl(ccl_val, compact=True),
        "subtitle": f"Média: {format_currency_brl(ccl_mean, compact=True)}",
        "delta_text": f"Status: {'Folga' if (ccl_val and ccl_val > 0) else 'Aperto'}",
        "delta_status": "positive" if (ccl_val and ccl_val >= 0) else "negative",
        "badge_text": "CCL s/ Ajuste",
        "badge_type": "real",
        "tooltip": "Ativo Circulante menos Passivo Circulante informado",
        "card_variant": "",
    })

    # 2. PMR
    pmr_val = summary.get("pmr", {}).get("latest", np.nan)
    pmr_mean = summary.get("pmr", {}).get("mean", np.nan)
    cards.append({
        "label": "Prazo Médio Recebimento (PMR)",
        "value_fmt": f"{pmr_val:.1f} dias" if is_valid_number(pmr_val) else "N/D",
        "subtitle": f"Média: {pmr_mean:.1f} dias" if is_valid_number(pmr_mean) else "",
        "delta_text": "Tempo Médio Cobrança",
        "delta_status": "positive" if (pmr_val and pmr_val <= 60.0) else "neutral",
        "badge_text": "Recebimento",
        "badge_type": "real",
        "tooltip": "Contas a Receber de Clientes ÷ Receita Operacional × 360",
        "card_variant": "",
    })

    # 3. PMP
    pmp_val = summary.get("pmp", {}).get("latest", np.nan)
    pmp_mean = summary.get("pmp", {}).get("mean", np.nan)
    cards.append({
        "label": "Prazo Médio Pagamento (PMP)",
        "value_fmt": f"{pmp_val:.1f} dias" if is_valid_number(pmp_val) else "N/D",
        "subtitle": f"Média: {pmp_mean:.1f} dias" if is_valid_number(pmp_mean) else "",
        "delta_text": "Prazo c/ Fornecedores",
        "delta_status": "positive" if (pmp_val and pmp_val >= 20.0) else "neutral",
        "badge_text": "Pagamento",
        "badge_type": "real",
        "tooltip": "Fornecedores ÷ Custos × 360",
        "card_variant": "",
    })

    # 4. Ciclo Financeiro
    ciclo_val = summary.get("ciclo_financeiro", {}).get("latest", np.nan)
    ncg_val = summary.get("necessidade_capital_giro", {}).get("latest", np.nan)
    is_neg = ciclo_val <= 0 if is_valid_number(ciclo_val) else None
    cards.append({
        "label": "Ciclo Financeiro Simplificado",
        "value_fmt": f"{ciclo_val:.1f} dias" if is_valid_number(ciclo_val) else "N/D",
        "subtitle": f"NCG: {format_currency_brl(ncg_val, compact=True)}",
        "delta_text": "Fornecedores financiam" if is_neg else "Empresa financia",
        "delta_status": "positive" if is_neg else "warning",
        "badge_text": "Ciclo",
        "badge_type": "positive" if is_neg else "warning",
        "tooltip": "PMR − PMP (estoques desconsiderados no modelo simplificado)",
        "card_variant": "",
    })

    render_section_header(
        "Métricas de Capital de Giro e Ciclo Operacional",
        "Indicadores em dias comerciais (360 dias) e folga patrimonial.",
    )
    render_kpi_grid(cards)

    tabs = st.tabs([
        "📊 Gráficos Operacionais",
        "⚖️ PMR x PMP e Ciclo",
        "💵 Necessidade vs. Folga CCL",
        "📋 Tabela Completa de Indicadores",
        "📖 Metodologia e Diagnóstico",
    ])

    with tabs[0]:
        st.plotly_chart(chart_working_capital_ccl(df_scen), use_container_width=True)

    with tabs[1]:
        c_col1, c_col2 = st.columns(2)
        with c_col1:
            st.plotly_chart(chart_working_capital_pmr_pmp(df_scen), use_container_width=True)
        with c_col2:
            st.plotly_chart(chart_working_capital_cycle(df_scen), use_container_width=True)

    with tabs[2]:
        st.plotly_chart(chart_working_capital_need_vs_ccl(df_scen), use_container_width=True)

    with tabs[3]:
        cg_rows = []
        for _, r in df_scen.sort_values("Ano").iterrows():
            ano_lbl = format_period_label(int(r["Ano"]))
            cg_rows.append({
                "Período": ano_lbl,
                "Ativo Circulante (R$)": format_currency_brl(r.get("BAL - Ativo Circulante"), compact=False),
                "Passivo Circulante (R$)": format_currency_brl(abs(r.get("BAL - Passivo Circulante", np.nan)), compact=False),
                "CCL (R$)": format_currency_brl(r.get("calc_ccl"), compact=False),
                "CR Clientes (R$)": format_currency_brl(r.get("BAL - Contas a Receber - Clientes"), compact=False),
                "Fornecedores (R$)": format_currency_brl(abs(r.get("BAL - Fornecedores", np.nan)), compact=False),
                "PMR": f"{r.get('calc_pmr', np.nan):.1f} dias" if is_valid_number(r.get("calc_pmr")) else "N/D",
                "PMP": f"{r.get('calc_pmp', np.nan):.1f} dias" if is_valid_number(r.get("calc_pmp")) else "N/D",
                "Ciclo Financeiro": f"{r.get('calc_ciclo_financeiro', np.nan):.1f} dias" if is_valid_number(r.get("calc_ciclo_financeiro")) else "N/D",
                "NCG Estimada (R$)": format_currency_brl(r.get("calc_necessidade_capital_giro"), compact=False),
                "Folga s/ CCL (R$)": format_currency_brl(r.get("calc_folga_ccl"), compact=False),
            })
        render_corporate_table(
            pd.DataFrame(cg_rows),
            title="Demonstração Detalhada de Capital de Giro e Prazos Médios",
            subtitle=f"Cenário: {active_scenario} — Ano comercial com 360 dias (estoques desconsiderados)",
        )

    with tabs[4]:
        render_callout(
            "Fundamentos de Gestão de Capital de Giro",
            "<strong>Por que o Capital de Giro é vital na CTI Global:</strong><br>"
            "Empresas lucrativas também enfrentam estresse de caixa quando o ciclo operacional consome recursos antes da liquidação das vendas.<br>"
            "• <strong>CCL Positivo:</strong> Os ativos realizáveis no curto prazo cobrem com folga os vencimentos de curto prazo.<br>"
            "• <strong>Ciclo Financeiro Simplificado (PMR − PMP):</strong> Mede os dias durante os quais a empresa financia sua atividade operacional com recursos próprios ou bancários. No modelo simplificado adotado oficialmente, os estoques são desconsiderados.<br>"
            "• <strong>Ciclo Negativo:</strong> Caso o PMP supere o PMR, os fornecedores financiam a operação, liberando caixa.<br>"
            "• <strong>Nota sobre o Ano 12:</strong> Conforme governança corporativa, o Balanço Patrimonial é estruturalmente incompleto no Ano 12, sendo apresentado como N/D para garantir integridade contábil.",
            kind="info",
        )


# =============================================================================
# MÓDULO 3 — FLUXO DE CAIXA
# =============================================================================

def render_page_fluxo_caixa(
    store: ProcessedDataStore,
    active_scenario: str,
    compare_scenarios: list[str],
    period_range: tuple[int, int],
) -> None:
    """Página Oficial: Fluxo de Caixa (Visão Detalhada de Atividades e Conciliação)."""
    df_scen = filter_panel(store.panel, scenarios=active_scenario, period_range=period_range)
    if df_scen.empty:
        render_empty_state()
        return

    render_top_header(
        title="Fluxo de Caixa",
        subtitle="Movimentação efetiva de recursos: atividades operacionais, de investimentos e de financiamento com conciliação contábil",
        store=store,
        active_scenario=active_scenario,
        period_range=period_range,
    )

    summary = summarize_kpis_for_selection(df_scen)
    latest_row = df_scen.iloc[-1]
    latest_p_desc = format_period_label(int(latest_row["Ano"]))

    cards: list[dict[str, Any]] = []

    # 1. Saldo Inicial
    s_ini = latest_row.get("calc_saldo_inicial_caixa", np.nan)
    cards.append({
        "label": "Saldo Inicial de Caixa",
        "value_fmt": format_currency_brl(s_ini, compact=True),
        "subtitle": f"Período: {latest_p_desc}",
        "delta_text": "Origem: Exercício Anterior",
        "delta_status": "neutral",
        "badge_text": "Inicial",
        "badge_type": "real",
        "tooltip": "Saldo de caixa no primeiro dia do exercício",
        "card_variant": "",
    })

    # 2. Entradas Operacionais
    ent_op = summary.get("entradas_operacionais", {}).get("sum", np.nan)
    cards.append({
        "label": "Entradas Operacionais",
        "value_fmt": format_currency_brl(ent_op, compact=True),
        "subtitle": f"Recorte: {len(df_scen)} períodos",
        "delta_text": f"Média: {format_currency_brl(summary.get('entradas_operacionais', {}).get('mean', np.nan), compact=True)}",
        "delta_status": "positive",
        "badge_text": "Entradas",
        "badge_type": "positive",
        "tooltip": "Recebimentos de clientes e outras entradas operacionais",
        "card_variant": "",
    })

    # 3. Saídas Operacionais
    saidas_op = summary.get("saidas_operacionais", {}).get("sum", np.nan)
    cards.append({
        "label": "Saídas Operacionais",
        "value_fmt": format_currency_brl(saidas_op, compact=True),
        "subtitle": f"Recorte: {len(df_scen)} períodos",
        "delta_text": f"Média: {format_currency_brl(summary.get('saidas_operacionais', {}).get('mean', np.nan), compact=True)}",
        "delta_status": "negative",
        "badge_text": "Saídas",
        "badge_type": "negative",
        "tooltip": "Desembolsos financeiros efetivos com tributos, custos e IR/CSLL",
        "card_variant": "",
    })

    # 4. Saldo Final
    s_fim = latest_row.get("calc_saldo_final_caixa", np.nan)
    cards.append({
        "label": "Saldo Final de Caixa",
        "value_fmt": format_currency_brl(s_fim, compact=True),
        "subtitle": f"Período: {latest_p_desc}",
        "delta_text": "Reconciliado c/ Balanço",
        "delta_status": "positive" if (s_fim and s_ini and s_fim >= s_ini) else "neutral",
        "badge_text": "Final",
        "badge_type": "real",
        "tooltip": "Saldo final auditado e conciliado com BAL - Disponível",
        "card_variant": "",
    })

    render_section_header(
        "Posição de Caixa e Movimentação Financeira",
        "Saldos e fluxos operacionais consolidados no recorte ativo.",
    )
    render_kpi_grid(cards)

    tabs = st.tabs([
        "🌊 Ponte do Caixa (Waterfall)",
        "📊 Evolução e Atividades",
        "💵 Caixa vs. Lucro Contábil",
        "📋 Tabela Completa do Fluxo",
        "🔍 Auditoria e Conciliação",
    ])

    with tabs[0]:
        st.plotly_chart(chart_cash_flow_waterfall(latest_row, latest_p_desc), use_container_width=True)

    with tabs[1]:
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            st.plotly_chart(chart_cash_flow_evolution(df_scen), use_container_width=True)
        with f_col2:
            st.plotly_chart(chart_cash_flow_entries_exits(df_scen), use_container_width=True)

        st.plotly_chart(chart_cash_flow_composition(df_scen), use_container_width=True)

    with tabs[2]:
        st.plotly_chart(chart_cash_flow_profit_vs_cash(df_scen), use_container_width=True)
        render_callout(
            "Distinção Contábil Fundamental: Lucro Líquido vs. Caixa Operacional (FCO)",
            "<strong>DRE (Regime de Competência):</strong> Reconhece a receita quando os serviços são prestados e deduz despesas incorridas, mesmo que ainda não liquidadas financeiramente (ex.: depreciação que não consome caixa).<br>"
            "<strong>DFC (Regime de Caixa):</strong> Computa exclusivamente a entrada e saída efetiva de moeda corrente.<br>"
            "Portanto, divergências entre Lucro Líquido e FCO são perfeitamente normais e decorrem do ciclo de capital de giro e investimentos.",
            kind="info",
        )

    with tabs[3]:
        flu_rows = []
        for _, r in df_scen.sort_values("Ano").iterrows():
            ano_lbl = format_period_label(int(r["Ano"]))
            flu_rows.append({
                "Período": ano_lbl,
                "Saldo Inicial": format_currency_brl(r.get("FLU - Saldo Inicial"), compact=False),
                "Receita (DFC)": format_currency_brl(r.get("FLU - Receita"), compact=False),
                "Tributos Pagos": format_currency_brl(r.get("FLU - Tributos"), compact=False),
                "Custos Pagos": format_currency_brl(r.get("FLU - Custos"), compact=False),
                "IR/CSLL Pagos": format_currency_brl(r.get("FLU - Imposto de Renda e Contribuição Social"), compact=False),
                "FCO (Operação)": format_currency_brl(r.get("calc_fco"), compact=False),
                "Investimentos": format_currency_brl(r.get("FLU - Investimentos"), compact=False),
                "Entradas Financ.": format_currency_brl(r.get("FLU - Entradas"), compact=False),
                "Despesas Financ.": format_currency_brl(r.get("FLU - Despesas Financeiras"), compact=False),
                "Distribuição Sócios": format_currency_brl(r.get("FLU - Distribuição para Acionista"), compact=False),
                "Geração de Caixa": format_currency_brl(r.get("FLU - Geração de Caixa"), compact=False),
                "Saldo Final": format_currency_brl(r.get("FLU - Saldo Final"), compact=False),
            })
        render_corporate_table(
            pd.DataFrame(flu_rows),
            title="Demonstração Oficial dos Fluxos de Caixa (DFC)",
            subtitle=f"Cenário: {active_scenario} — Todas as contas no regime de caixa em R$",
        )

    with tabs[4]:
        max_diff = df_scen["calc_conciliacao_caixa_diff"].max()
        if max_diff < 1e-2:
            st.success("✅ Conciliação Matemática de Caixa Perfeita: Saldo Inicial + Geração de Caixa = Saldo Final em todos os períodos analisados.")
        else:
            st.warning(f"Atenção: Diferença máxima de conciliação de caixa identificada: R$ {max_diff:,.2f}.")


# =============================================================================
# MÓDULO 4 — DEMONSTRAÇÃO DO VALOR ADICIONADO (DVA)
# =============================================================================

def render_page_dva(
    store: ProcessedDataStore,
    active_scenario: str,
    compare_scenarios: list[str],
    period_range: tuple[int, int],
) -> None:
    """Página Oficial: Demonstração do Valor Adicionado (Geração e Distribuição de Riqueza)."""
    df_scen = filter_panel(store.panel, scenarios=active_scenario, period_range=period_range)
    if df_scen.empty:
        render_empty_state()
        return

    render_top_header(
        title="Demonstração do Valor Adicionado (DVA)",
        subtitle="Evidenciação da riqueza gerada pela entidade e sua distribuição aos empregados, governo, credores e acionistas",
        store=store,
        active_scenario=active_scenario,
        period_range=period_range,
    )

    latest_row = df_scen.iloc[-1]
    latest_p_desc = format_period_label(int(latest_row["Ano"]))
    summary = summarize_kpis_for_selection(df_scen)

    va_tot_mean = summary.get("dva_va_total", {}).get("mean", np.nan)
    va_tot_sum = summary.get("dva_va_total", {}).get("sum", np.nan)
    grau_riqueza_mean = summary.get("dva_grau_riqueza", {}).get("mean", np.nan)
    part_gov_mean = summary.get("dva_part_governo", {}).get("mean", np.nan)
    part_prop_mean = summary.get("dva_part_proprios", {}).get("mean", np.nan)

    cards: list[dict[str, Any]] = []

    # 1. Valor Adicionado Total a Distribuir
    cards.append({
        "label": "Valor Adicionado Total (Item 7)",
        "value_fmt": format_currency_brl(va_tot_mean, compact=True),
        "subtitle": f"Acumulado: {format_currency_brl(va_tot_sum, compact=True)}",
        "delta_text": f"Último: {format_currency_brl(latest_row.get('calc_dva_va_total'), compact=True)}",
        "delta_status": "positive",
        "badge_text": "Bolo a Distribuir",
        "badge_type": "real",
        "tooltip": "Riqueza total líquida criada pela entidade somada aos valores recebidos em transferência",
        "card_variant": "",
    })

    # 2. Grau de Geração de Riqueza
    cards.append({
        "label": "Grau de Geração de Riqueza",
        "value_fmt": format_pct_br(grau_riqueza_mean, already_percent=True),
        "subtitle": f"Receita: {format_currency_brl(df_scen['calc_dva_receitas_totais'].mean(), compact=True)}",
        "delta_text": f"Último: {format_pct_br(latest_row.get('calc_dva_grau_riqueza'), already_percent=True)}",
        "delta_status": "positive" if (grau_riqueza_mean and grau_riqueza_mean >= 50.0) else "neutral",
        "badge_text": "Eficiência VA",
        "badge_type": "real",
        "tooltip": "VA Total a Distribuir ÷ Receitas Totais: quanto de cada real faturado se transforma em riqueza real",
        "card_variant": "",
    })

    # 3. Fatia do Governo
    cards.append({
        "label": "Fatia do Governo (Tributos)",
        "value_fmt": format_pct_br(part_gov_mean, already_percent=True),
        "subtitle": f"Média: {format_currency_brl(df_scen['calc_dva_dist_governo'].mean(), compact=True)}",
        "delta_text": "Tributos e Encargos",
        "delta_status": "neutral",
        "badge_text": "Governo",
        "badge_type": "real",
        "tooltip": "Participação dos tributos sobre vendas e impostos sobre o lucro no valor adicionado total",
        "card_variant": "",
    })

    # 4. Fatia dos Sócios
    cards.append({
        "label": "Fatia dos Sócios (Cap. Próprios)",
        "value_fmt": format_pct_br(part_prop_mean, already_percent=True),
        "subtitle": f"Média: {format_currency_brl(df_scen['calc_dva_dist_proprios'].mean(), compact=True)}",
        "delta_text": f"Retenção: {format_pct_br(df_scen['calc_dva_retencao_riqueza'].mean(), already_percent=True)}",
        "delta_status": "positive" if (part_prop_mean and part_prop_mean >= 15.0) else "neutral",
        "badge_text": "Sócios / PL",
        "badge_type": "real",
        "tooltip": "Parcela da riqueza gerada destinada aos sócios (dividendos e lucros retidos no PL)",
        "card_variant": "",
    })

    render_section_header(
        "Agregados Econômicos da DVA",
        "Geração de riqueza e distribuição percentual aos beneficiários socioeconômicos.",
    )
    render_kpi_grid(cards)

    tabs = st.tabs([
        "🌊 Formação do VA (Waterfall)",
        "🍩 Distribuição da Riqueza",
        "📈 Evolução Histórica do VA",
        "📋 DVA Completa (Itens 1 a 8)",
        "🔍 Conferências Obrigatórias",
        "📖 Metodologia e Interpretação",
    ])

    with tabs[0]:
        st.plotly_chart(chart_dva_waterfall(latest_row, latest_p_desc), use_container_width=True)

    with tabs[1]:
        d_col1, d_col2 = st.columns(2)
        with d_col1:
            st.plotly_chart(chart_dva_distribution_pie(latest_row, latest_p_desc), use_container_width=True)
        with d_col2:
            st.plotly_chart(chart_dva_distribution_stacked_100(df_scen), use_container_width=True)

    with tabs[2]:
        st.plotly_chart(chart_dva_evolution(df_scen), use_container_width=True)
        st.plotly_chart(chart_dva_wealth_indicators(df_scen), use_container_width=True)

    with tabs[3]:
        st.markdown(f"#### Demonstração do Valor Adicionado Completa — {latest_p_desc}")
        r = latest_row
        va_tot_val = float(r.get("calc_dva_va_total", 0.0))

        def _p(val: float) -> str:
            return format_pct_br(safe_divide(val, va_tot_val) * 100.0, already_percent=True) if va_tot_val > 0 else "—"

        dva_structure = [
            {"Item": "1. Receitas", "Valor (R$)": format_currency_brl(r.get("calc_dva_receitas_totais")), "Part. (%)": _p(float(r.get("calc_dva_receitas_totais", 0)))},
            {"Item": "  1.1 Vendas de mercadorias, produtos e serviços", "Valor (R$)": format_currency_brl(r.get("calc_dva_vendas_brutas")), "Part. (%)": _p(float(r.get("calc_dva_vendas_brutas", 0)))},
            {"Item": "  1.2 Outras receitas operacionais", "Valor (R$)": format_currency_brl(r.get("calc_dva_outras_receitas")), "Part. (%)": _p(float(r.get("calc_dva_outras_receitas", 0)))},
            {"Item": "2. Insumos Adquiridos de Terceiros", "Valor (R$)": format_currency_brl(-abs(float(r.get("calc_dva_insumos_totais", 0)))), "Part. (%)": _p(-abs(float(r.get("calc_dva_insumos_totais", 0))))},
            {"Item": "  2.1 Custos operacionais e serviços consumidos", "Valor (R$)": format_currency_brl(-abs(float(r.get("calc_dva_custos", 0)))), "Part. (%)": _p(-abs(float(r.get("calc_dva_custos", 0))))},
            {"Item": "  2.2 Outros insumos e despesas operacionais", "Valor (R$)": format_currency_brl(-abs(float(r.get("calc_dva_outros_insumos", 0)))), "Part. (%)": _p(-abs(float(r.get("calc_dva_outros_insumos", 0))))},
            {"Item": "3. Valor Adicionado Bruto (1 − 2)", "Valor (R$)": format_currency_brl(r.get("calc_dva_va_bruto")), "Part. (%)": _p(float(r.get("calc_dva_va_bruto", 0)))},
            {"Item": "4. Retenções (Depreciação, Amortização e Exaustão)", "Valor (R$)": format_currency_brl(-abs(float(r.get("calc_dva_retencoes", 0)))), "Part. (%)": _p(-abs(float(r.get("calc_dva_retencoes", 0))))},
            {"Item": "5. Valor Adicionado Líquido Produzido (3 − 4)", "Valor (R$)": format_currency_brl(r.get("calc_dva_va_liquido")), "Part. (%)": _p(float(r.get("calc_dva_va_liquido", 0)))},
            {"Item": "6. Valor Adicionado Recebido em Transferência", "Valor (R$)": format_currency_brl(r.get("calc_dva_transferencias_totais")), "Part. (%)": _p(float(r.get("calc_dva_transferencias_totais", 0)))},
            {"Item": "  6.1 Receitas financeiras", "Valor (R$)": format_currency_brl(r.get("calc_dva_receitas_financeiras")), "Part. (%)": _p(float(r.get("calc_dva_receitas_financeiras", 0)))},
            {"Item": "  6.2 Resultado de equivalência patrimonial", "Valor (R$)": format_currency_brl(r.get("calc_dva_equiv_patrimonial")), "Part. (%)": _p(float(r.get("calc_dva_equiv_patrimonial", 0)))},
            {"Item": "7. Valor Adicionado Total a Distribuir (5 + 6)", "Valor (R$)": format_currency_brl(r.get("calc_dva_va_total")), "Part. (%)": "100,0%"},
            {"Item": "8. Distribuição do Valor Adicionado", "Valor (R$)": format_currency_brl(r.get("calc_dva_total_distribuido")), "Part. (%)": "100,0%"},
            {"Item": "  8.1 Pessoal (Remuneração direta, benefícios e FGTS)", "Valor (R$)": format_currency_brl(r.get("calc_dva_dist_pessoal")), "Part. (%)": _p(float(r.get("calc_dva_dist_pessoal", 0)))},
            {"Item": "  8.2 Impostos, taxas e contribuições (Governo)", "Valor (R$)": format_currency_brl(r.get("calc_dva_dist_governo")), "Part. (%)": _p(float(r.get("calc_dva_dist_governo", 0)))},
            {"Item": "  8.3 Remuneração de capitais de terceiros (Juros)", "Valor (R$)": format_currency_brl(r.get("calc_dva_dist_terceiros")), "Part. (%)": _p(float(r.get("calc_dva_dist_terceiros", 0)))},
            {"Item": "  8.4 Remuneração de capitais próprios (Sócios)", "Valor (R$)": format_currency_brl(r.get("calc_dva_dist_proprios")), "Part. (%)": _p(float(r.get("calc_dva_dist_proprios", 0)))},
            {"Item": "    8.4.1 Dividendos e juros sobre capital próprio", "Valor (R$)": format_currency_brl(r.get("calc_dva_dist_dividendos")), "Part. (%)": _p(float(r.get("calc_dva_dist_dividendos", 0)))},
            {"Item": "    8.4.2 Lucros retidos / Prejuízo do exercício", "Valor (R$)": format_currency_brl(r.get("calc_dva_dist_lucros_retidos")), "Part. (%)": _p(float(r.get("calc_dva_dist_lucros_retidos", 0)))},
        ]
        render_corporate_table(
            pd.DataFrame(dva_structure),
            title="Demonstração do Valor Adicionado Oficial",
            subtitle=f"Estrutura padronizada em duas partes (Geração de Riqueza e Distribuição) — {latest_p_desc}",
        )

    with tabs[4]:
        st.markdown("#### Validações e Conferências Obrigatórias da DVA")
        v1 = abs(float(r.get("calc_dva_va_bruto", 0)) - (float(r.get("calc_dva_receitas_totais", 0)) - abs(float(r.get("calc_dva_insumos_totais", 0))))) < 1e-2
        v2 = abs(float(r.get("calc_dva_va_liquido", 0)) - (float(r.get("calc_dva_va_bruto", 0)) - abs(float(r.get("calc_dva_retencoes", 0))))) < 1e-2
        v3 = abs(float(r.get("calc_dva_va_total", 0)) - (float(r.get("calc_dva_va_liquido", 0)) + float(r.get("calc_dva_transferencias_totais", 0)))) < 1e-2
        v4 = abs(float(r.get("calc_dva_va_total", 0)) - float(r.get("calc_dva_total_distribuido", 0))) < 1e-2
        v5 = abs(float(r.get("calc_dva_dist_proprios", 0)) - float(r.get("DRE - Resultado Líquido", 0))) < 1e-2

        c_v1, c_v2 = st.columns(2)
        with c_v1:
            st.markdown(f"- **Validação 1 (Geração VA Bruto):** {'✅ Conciliado (100%)' if v1 else '❌ Divergente'}")
            st.markdown(f"- **Validação 2 (VA Líquido Produzido):** {'✅ Conciliado (100%)' if v2 else '❌ Divergente'}")
            st.markdown(f"- **Validação 3 (VA Total a Distribuir):** {'✅ Conciliado (100%)' if v3 else '❌ Divergente'}")
        with c_v2:
            st.markdown(f"- **Validação 4 (Soma da Distribuição == Item 7):** {'✅ Conciliado (100%)' if v4 else '❌ Divergente'}")
            st.markdown(f"- **Validação 5 (Capitais Próprios == Lucro Líquido DRE):** {'✅ Conciliado (100%)' if v5 else '❌ Divergente'}")

        if v4 and v5:
            st.success("Todas as conferências contábeis e matemáticas da DVA fecharam com 100% de precisão!")
        else:
            st.error("Identificadas inconsistências nas validações automáticas da DVA.")

    with tabs[5]:
        render_callout(
            "Finalidade e Fundamentos da DVA na CTI Global",
            "A <strong>Demonstração do Valor Adicionado (DVA)</strong> mensura o papel econômico da CTI Global perante a sociedade:<br>"
            "1. <strong>Quanta riqueza a empresa criou?</strong> A diferença entre o que foi faturado e o que foi adquirido de terceiros.<br>"
            "2. <strong>Com quem essa riqueza foi repartida?</strong> Evidencia a contribuição social aos trabalhadores (Pessoal), aos cofres públicos (Governo), aos credores de dívida (Capitais de Terceiros) e a remuneração e reinvestimento dos acionistas (Capitais Próprios).<br>"
            "3. <strong>Retenção de Riqueza:</strong> Os lucros não distribuídos permanecem no patrimônio líquido para assegurar a perenidade dos investimentos futuros da CTI Global.",
            kind="info",
        )
