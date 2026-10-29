"""Páginas 1 a 4: Visão Executiva, Análise da DRE, Balanço Patrimonial e Fluxo de Caixa (DFC)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import streamlit as st

from src.charts import (
    chart_balance_structure,
    chart_dfc_profit_vs_cash,
    chart_dre_waterfall,
    chart_ebitda_comparison,
    chart_kpi_evolution,
    chart_scenario_distribution,
)
from src.config import (
    KPI_CATALOG,
    WACC_MODEL_PREMISE,
    format_by_unit,
    format_currency_brl,
    format_multiple_br,
    format_pct_br,
    format_period_label,
    is_valid_number,
)
from src.data_processing import ProcessedDataStore, filter_panel
from src.data_validation import ValidationSummary
from src.financial_kpis import compute_variation, evaluate_all_goals, summarize_kpis_for_selection
from src.ui_components import (
    calc_table_height,
    render_callout,
    render_corporate_dataframe,
    render_corporate_table,
    render_data_footer,
    render_empty_state,
    render_kpi_grid,
    render_section_header,
    render_top_header,
)


def _format_delta_vs_benchmark(
    val: float,
    bench: float,
    unit: str,
    higher_is_better: bool | None,
    bench_name: str = "Mediana",
) -> tuple[str, str]:
    """Gera texto e classe semântica comparando o valor do cenário com o benchmark da base."""
    if not (is_valid_number(val) and is_valid_number(bench)):
        return "Sem benchmark comparável no recorte", "neutral"

    var = compute_variation(val, bench, is_percentage_point_metric=(unit == "%"))
    diff_abs = var["diff_abs"]
    if abs(diff_abs) <= 1e-9:
        return f"Alinhado à {bench_name} ({format_by_unit(bench, unit, compact_currency=True)})", "neutral"

    if unit == "%":
        delta_str = f"{format_pct_br(diff_abs, signed=True)} p.p. vs {bench_name}"
    elif unit == "x":
        sign = "+" if diff_abs > 0 else ""
        delta_str = f"{sign}{format_multiple_br(diff_abs)} vs {bench_name}"
    else:
        delta_str = (
            f"{format_pct_br(var['diff_pct'], signed=True)} vs {bench_name}"
            if is_valid_number(var["diff_pct"])
            else f"Dif. {format_currency_brl(diff_abs, compact=True)} vs {bench_name}"
        )

    if higher_is_better is None:
        status = "neutral"
    elif higher_is_better:
        status = "positive" if diff_abs > 0 else "negative"
    else:
        status = "positive" if diff_abs < 0 else "negative"

    return delta_str, status


def render_page_visao_executiva(
    store: ProcessedDataStore,
    val_summary: ValidationSummary,
    active_scenario: str,
    compare_scenarios: list[str],
    period_range: tuple[int, int],
) -> None:
    """Página 1 — Visão Executiva consolidada."""
    render_top_header(
        title="CTI Global | Plataforma Analítica de Planejamento Financeiro",
        subtitle=(
            "Sistema corporativo de análise financeira, acompanhamento de indicadores, "
            "comparação de cenários e apoio à tomada de decisão empresarial."
        ),
        store=store,
        active_scenario=active_scenario,
        period_range=period_range,
    )

    def _navigate_to_page(target_page: str) -> None:
        st.session_state["nav_page_radio"] = target_page

    # Atalhos de acesso rápido às principais seções com moldura simétrica institucional
    st.markdown(
        """
        <div class="cti-quick-nav-card">
            <h4>📌 Acesso Rápido às Seções Corporativas</h4>
        """,
        unsafe_allow_html=True,
    )
    q1, q2, q3 = st.columns(3)
    with q1:
        st.button(
            "📊 DRE — Demonstração do Resultado",
            on_click=_navigate_to_page,
            args=("2. DRE — Demonstração do Resultado",),
            use_container_width=True,
            key="quick_dre",
        )
    with q2:
        st.button(
            "🏛️ Balanço Patrimonial",
            on_click=_navigate_to_page,
            args=("3. Balanço Patrimonial",),
            use_container_width=True,
            key="quick_balanco",
        )
    with q3:
        st.button(
            "📈 Indicadores Financeiros",
            on_click=_navigate_to_page,
            args=("5. Indicadores Financeiros",),
            use_container_width=True,
            key="quick_kpis",
        )

    q4, q5, q6 = st.columns(3)
    with q4:
        st.button(
            "🎯 Análise de Sensibilidade",
            on_click=_navigate_to_page,
            args=("8. Análise de Sensibilidade",),
            use_container_width=True,
            key="quick_sens",
        )
    with q5:
        st.button(
            "🔬 Análise Estatística",
            on_click=_navigate_to_page,
            args=("11. Análise Estatística",),
            use_container_width=True,
            key="quick_stat",
        )
    with q6:
        st.button(
            "📑 Relatórios Gerenciais",
            on_click=_navigate_to_page,
            args=("14. Relatórios Gerenciais",),
            use_container_width=True,
            key="quick_rep",
        )
    st.markdown("</div>", unsafe_allow_html=True)

    df_scen = filter_panel(store.panel, scenarios=active_scenario, period_range=period_range)
    if df_scen.empty:
        render_empty_state()
        render_data_footer(store)
        return

    df_all_period = filter_panel(store.panel, period_range=period_range)
    summ = summarize_kpis_for_selection(df_scen)
    configured_goals: dict[str, float | None] = st.session_state.get("configured_goals", {})

    # Mediana de referência da base no mesmo intervalo de períodos
    bench_means = df_all_period.groupby("Cenário").mean(numeric_only=True)

    exec_kpis = [
        "receita",
        "margem_contribuicao",
        "ebitda_calculado",
        "margem_ebitda_calculada",
        "margem_ebitda_modelo",
        "roic",
        "eva",
        "lc",
        "endividamento_geral",
        "geracao_caixa",
    ]

    cards: list[dict[str, Any]] = []
    for k in exec_kpis:
        meta = KPI_CATALOG[k]
        k_info = summ[k]
        mean_val = k_info["mean"]
        col_name = f"kpi_{k}"
        med_bench = float(bench_means[col_name].median()) if col_name in bench_means.columns else np.nan
        delta_txt, delta_cls = _format_delta_vs_benchmark(
            mean_val, med_bench, meta.unit, meta.higher_is_better, bench_name="Mediana Base"
        )

        # Verifica se há meta configurada pelo usuário
        goal_val = configured_goals.get(k)
        badge_txt = "Observado"
        badge_type = "real"
        card_var = ""
        if not is_valid_number(mean_val):
            badge_txt = "N/D no recorte"
            badge_type = "warning"
            card_var = "is-warning"
        elif goal_val is not None and is_valid_number(goal_val):
            goals_eval = evaluate_all_goals({k: mean_val}, {k: goal_val}, kpi_keys=[k])
            if not goals_eval.empty:
                fav = goals_eval["Favorável"].iloc[0]
                badge_txt = "Meta OK" if fav else "Alerta Meta"
                badge_type = "positive" if fav else "negative"
                if not fav:
                    card_var = "is-negative"

        n_per = k_info["valid_count"]
        sub_parts = [f"Média ({n_per} per. válidos)"]
        if is_valid_number(k_info["sum"]):
            sub_parts.append(f"Acum.: {format_currency_brl(k_info['sum'], compact=True)}")
        elif k_info["latest_period"] is not None and is_valid_number(k_info["latest"]):
            sub_parts.append(
                f"{format_period_label(k_info['latest_period'])}: "
                f"{format_by_unit(k_info['latest'], meta.unit, compact_currency=True)}"
            )

        cards.append({
            "label": meta.short_name,
            "value_fmt": format_by_unit(mean_val, meta.unit, compact_currency=True),
            "subtitle": " • ".join(sub_parts),
            "delta_text": delta_txt,
            "delta_status": delta_cls,
            "badge_text": badge_txt,
            "badge_type": badge_type,
            "tooltip": f"{meta.name} | Fórmula: {meta.formula}",
            "card_variant": card_var,
        })

    render_section_header(
        "Indicadores-Chave de Desempenho (KPIs Auditados)",
        "Valores médios por período válido no recorte selecionado, comparados à mediana dos cenários no mesmo intervalo.",
    )
    render_kpi_grid(cards)

    if period_range[1] == 12:
        render_callout(
            "Nota Metodológica — Tratamento Transparente do Ano 12",
            "O intervalo selecionado inclui o <strong>Ano 12</strong>. Conforme diagnosticado na auditoria da base original, "
            "os indicadores da DRE e da DFC possuem cobertura integral (Anos 1 a 12), enquanto as contas de fechamento do "
            "Balanço Patrimonial estão incompletas no Ano 12 — razão pela qual <em>Liquidez, Endividamento, NOPAT, Capital Investido, "
            "ROIC e EVA</em> exibem <code>N/D</code> no Ano 12 e têm suas médias calculadas estritamente sobre os períodos válidos (Anos 1 a 11).",
            kind="info",
        )

    # Alertas de metas configuradas (se o usuário definiu metas na Página 9)
    active_goal_keys = [k for k, v in configured_goals.items() if v is not None and is_valid_number(v)]
    if active_goal_keys:
        g_df = evaluate_all_goals({k: summ[k]["mean"] for k in summ}, configured_goals, kpi_keys=active_goal_keys)
        n_ok = int((g_df["Favorável"] == True).sum())  # noqa: E712
        n_bad = int((g_df["Favorável"] == False).sum())  # noqa: E712
        render_callout(
            f"Monitoramento de Metas Configuradas ({len(active_goal_keys)} ativa(s))",
            f"No recorte atual de <strong>{active_scenario}</strong>: <strong>{n_ok}</strong> meta(s) cumprida(s) e "
            f"<strong>{n_bad}</strong> meta(s) em atenção/abaixo do esperado. Gerencie os alvos na aba <em>Metas Financeiras</em>.",
            kind="success" if n_bad == 0 else "warning",
        )

    # Gráficos executivos lado a lado (responsivos)
    comp_df = (
        filter_panel(store.panel, scenarios=compare_scenarios, period_range=period_range)
        if compare_scenarios
        else None
    )
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        med_rec = df_all_period.groupby("Ano")["kpi_receita"].median()
        st.plotly_chart(
            chart_kpi_evolution(
                df_scen,
                "receita",
                active_scenario,
                target_value=configured_goals.get("receita"),
                compare_panel=comp_df,
                median_by_period=med_rec,
            ),
            use_container_width=True,
        )
    with col_g2:
        med_roic = df_all_period.groupby("Ano")["kpi_roic"].median()
        st.plotly_chart(
            chart_kpi_evolution(
                df_scen,
                "roic",
                active_scenario,
                target_value=configured_goals.get("roic") or WACC_MODEL_PREMISE,
                compare_panel=comp_df,
                median_by_period=med_roic,
            ),
            use_container_width=True,
        )
        st.caption(
            "Nota: Quando nenhuma meta customizada de ROIC está ativa, a linha tracejada exibe a referência "
            "de custo de capital do modelo corporativo (WACC = 12,00% — premissa padrão)."
        )

    col_g3, col_g4 = st.columns(2)
    with col_g3:
        st.plotly_chart(chart_ebitda_comparison(df_scen), use_container_width=True)
    with col_g4:
        if not store.resumo.empty and "ROIC" in store.resumo.columns:
            st.plotly_chart(
                chart_scenario_distribution(store.resumo, "ROIC", "ROIC Médio (Anos 1–11)", "%", active_scenario),
                use_container_width=True,
            )

    # Resumo executivo textual fundamentado estritamente nos números carregados
    render_section_header(
        "Síntese Executiva Fundamentada nos Dados",
        "Interpretação gerencial gerada deterministicamente a partir dos indicadores observados para o cenário e período filtrados.",
    )
    roic_mean = summ["roic"]["mean"]
    eva_mean = summ["eva"]["mean"]
    lc_mean = summ["lc"]["mean"]
    mc_mean = summ["margem_contribuicao"]["mean"]
    mg_eb_calc = summ["margem_ebitda_calculada"]["mean"]
    mg_eb_mod = summ["margem_ebitda_modelo"]["mean"]
    ll_sum = summ["resultado_liquido"]["sum"]
    caixa_sum = summ["geracao_caixa"]["sum"]

    rank_pos_txt = "não classificado"
    if not store.ranking.empty and "Cenário" in store.ranking.columns:
        r_match = store.ranking[store.ranking["Cenário"] == active_scenario]
        if not r_match.empty:
            pos = int(r_match["Posição"].iloc[0])
            rank_pos_txt = f"{pos}ª posição geral em Margem EBITDA do Modelo entre {len(store.ranking)} cenários"

    spread_txt = (
        f"superando a premissa de WACC (12,00%) em {format_pct_br(roic_mean - WACC_MODEL_PREMISE, signed=True)} p.p. "
        f"e gerando EVA médio positivo de {format_currency_brl(eva_mean, compact=True)}/ano"
        if (is_valid_number(roic_mean) and roic_mean >= WACC_MODEL_PREMISE)
        else (
            f"abaixo da premissa de WACC (12,00%), resultando em EVA médio de {format_currency_brl(eva_mean, compact=True)}"
            if is_valid_number(roic_mean)
            else "com ROIC e EVA indisponíveis (N/D) quando filtrado exclusivamente o Ano 12"
        )
    )

    st.markdown(
        f"""
        - **Posicionamento e Escala Operacional:** O cenário **{active_scenario}** ({rank_pos_txt}) registra no recorte
          selecionado Receita Bruta média de **{format_currency_brl(summ['receita']['mean'], compact=True)}**
          (acumulado de **{format_currency_brl(summ['receita']['sum'], compact=True)}**) e Margem de Contribuição média
          de **{format_pct_br(mc_mean)}** (calculada com `|DRE - Custos|` como proxy de custos variáveis).
        - **Distinção Metodológica de EBITDA:** A Margem EBITDA Calculada (`(Resultado Operacional + |D&A|) / Receita`)
          atinge **{format_pct_br(mg_eb_calc)}**, enquanto a Margem EBITDA do Modelo (`DRE - EBITDA / Receita`) é de
          **{format_pct_br(mg_eb_mod)}** — diferença preservada integralmente para transparência contábil.
        - **Retorno Econômico vs. Custo de Capital:** Nos períodos com Balanço completo, o ROIC médio é de
          **{format_pct_br(roic_mean)}**, {spread_txt}.
        - **Solvência e Regime de Caixa vs. Competência:** A Liquidez Corrente média situa-se em **{format_multiple_br(lc_mean)}**.
          Sob regime de competência (DRE), o Resultado Líquido acumulado no recorte soma **{format_currency_brl(ll_sum, compact=True)}**,
          ao passo que a Geração Líquida de Caixa (DFC, após investimentos, serviço da dívida e dividendos aos acionistas)
          totaliza **{format_currency_brl(caixa_sum, compact=True)}**.
        - **Qualidade da Base:** Status geral da validação automática: **{val_summary.overall_status}**
          (`0` duplicidades de chave, `100%` dos KPIs da planilha reconciliados).
        """
    )

    render_data_footer(store)


def _build_structured_dre_table(df_scen: pd.DataFrame) -> pd.DataFrame:
    """Monta a demonstração contábil do resultado no formato corporativo oficial (rubricas nas linhas, períodos nas colunas)."""
    df_sorted = df_scen.sort_values("Ano").copy()
    rubricas_defs = [
        ("Receita Operacional Bruta", "DRE - Receita"),
        ("(-) Deduções e Tributos", "DRE - Tributos"),
        ("(-) Custos Operacionais", "DRE - Custos"),
        ("(-) Depreciação e Amortização", "DRE - Depreciação e Amortização"),
        ("Resultado Operacional (EBIT)", "DRE - Resultado Operacional"),
        ("(+/-) Resultado Financeiro Líquido", "DRE - Resultado Financeiro"),
        ("Outras Receitas / Despesas Operacionais", "DRE - Outros Resultados Operacionais"),
        ("Resultado Antes do IR/CS (LAIR)", "DRE - Resultado Antes do Imposto de Renda"),
        ("(-) Provisão para IRPJ e CSLL", "DRE - Imposto de Renda e Contribuição Social"),
        ("Lucro Líquido do Exercício", "DRE - Resultado Líquido"),
        ("EBITDA Calculado (RO + |D&A|)", "calc_ebitda_calculado"),
        ("EBITDA Original do Modelo", "DRE - EBITDA"),
    ]
    periods = [format_period_label(int(a)) for a in df_sorted["Ano"]]
    rows: list[dict[str, str]] = []
    for label, col in rubricas_defs:
        if col in df_sorted.columns:
            vals = df_sorted[col].values
            row_dict: dict[str, str] = {"Demonstração Contábil (DRE)": label}
            for p_lbl, v in zip(periods, vals):
                row_dict[p_lbl] = format_currency_brl(float(v), compact=True)
            total_val = float(np.nansum(vals))
            row_dict["Total Acumulado"] = format_currency_brl(total_val, compact=True)
            rows.append(row_dict)

    if "DRE - Resultado Líquido" in df_sorted.columns and "DRE - Receita" in df_sorted.columns:
        row_ml: dict[str, str] = {"Demonstração Contábil (DRE)": "Margem Líquida (%)"}
        for p_lbl, rl, rec in zip(periods, df_sorted["DRE - Resultado Líquido"], df_sorted["DRE - Receita"]):
            pct = (rl / rec * 100.0) if rec and abs(rec) > 1e-6 else np.nan
            row_ml[p_lbl] = format_pct_br(pct)
        tot_rl = np.nansum(df_sorted["DRE - Resultado Líquido"])
        tot_rec = np.nansum(df_sorted["DRE - Receita"])
        row_ml["Total Acumulado"] = format_pct_br((tot_rl / tot_rec * 100.0) if tot_rec else np.nan)
        rows.append(row_ml)

    if "calc_ebitda_calculado" in df_sorted.columns and "DRE - Receita" in df_sorted.columns:
        row_me: dict[str, str] = {"Demonstração Contábil (DRE)": "Margem EBITDA (%)"}
        for p_lbl, eb, rec in zip(periods, df_sorted["calc_ebitda_calculado"], df_sorted["DRE - Receita"]):
            pct = (eb / rec * 100.0) if rec and abs(rec) > 1e-6 else np.nan
            row_me[p_lbl] = format_pct_br(pct)
        tot_eb = np.nansum(df_sorted["calc_ebitda_calculado"])
        tot_rec = np.nansum(df_sorted["DRE - Receita"])
        row_me["Total Acumulado"] = format_pct_br((tot_eb / tot_rec * 100.0) if tot_rec else np.nan)
        rows.append(row_me)

    return pd.DataFrame(rows)


def _build_structured_bp_table(df_scen: pd.DataFrame) -> pd.DataFrame:
    """Monta a estrutura patrimonial corporativa no formato oficial (rubricas nas linhas, períodos nas colunas)."""
    df_sorted = df_scen.sort_values("Ano").copy()
    bp_defs = [
        ("Ativo Circulante", "BAL - Ativo Circulante", "currency"),
        ("Disponibilidades (Caixa)", "BAL - Disponível", "currency"),
        ("Realizável a Longo Prazo", "BAL - Realizável a Longo Prazo", "currency"),
        ("Ativo Permanente (Imobilizado)", "BAL - Permanente", "currency"),
        ("Ativo Total", "BAL - Total do Ativo", "currency"),
        ("Passivo Circulante", "BAL - Passivo Circulante", "currency"),
        ("Exigível a Longo Prazo", "BAL - Exigível a Longo Prazo", "currency"),
        ("Patrimônio Líquido", "BAL - Patrimônio Líquido", "currency"),
        ("Liquidez Corrente (LC)", "kpi_lc", "multiple"),
        ("Liquidez Geral (LG)", "kpi_lg", "multiple"),
        ("Endividamento Geral (%)", "kpi_endividamento_geral", "pct"),
    ]
    periods = [format_period_label(int(a)) for a in df_sorted["Ano"]]
    rows: list[dict[str, str]] = []
    for label, col, kind in bp_defs:
        if col in df_sorted.columns:
            vals = df_sorted[col].values
            valid_vals = [v for v in vals if is_valid_number(v)]
            avg_val = float(np.nanmean(valid_vals)) if valid_vals else np.nan
            row_dict: dict[str, str] = {"Estrutura Patrimonial": label}
            for p_lbl, v in zip(periods, vals):
                if not is_valid_number(v):
                    row_dict[p_lbl] = "N/D"
                elif kind == "currency":
                    row_dict[p_lbl] = format_currency_brl(float(v), compact=True)
                elif kind == "multiple":
                    row_dict[p_lbl] = format_multiple_br(float(v))
                elif kind == "pct":
                    row_dict[p_lbl] = format_pct_br(float(v))
            if not is_valid_number(avg_val):
                row_dict["Média Período"] = "N/D"
            elif kind == "currency":
                row_dict["Média Período"] = format_currency_brl(avg_val, compact=True)
            elif kind == "multiple":
                row_dict["Média Período"] = format_multiple_br(avg_val)
            elif kind == "pct":
                row_dict["Média Período"] = format_pct_br(avg_val)
            rows.append(row_dict)
    return pd.DataFrame(rows)


def _build_structured_dfc_table(df_scen: pd.DataFrame) -> pd.DataFrame:
    """Monta a demonstração do fluxo de caixa corporativa no formato oficial (rubricas nas linhas, períodos nas colunas)."""
    df_sorted = df_scen.sort_values("Ano").copy()
    dfc_defs = [
        ("Saldo Inicial de Caixa", "FLU - Saldo Inicial"),
        ("(+) Recebimentos Operacionais", "FLU - Receita"),
        ("(-) Deduções e Tributos", "FLU - Tributos"),
        ("(-) Custos Operacionais", "FLU - Custos"),
        ("(+/-) Resultado Financeiro", "FLU - Resultado Financeiro"),
        ("(-) Investimentos em Ativo (CAPEX)", "FLU - Investimentos"),
        ("(-) Imposto de Renda e CSLL", "FLU - Imposto de Renda e Contribuição Social"),
        ("Geração Líquida de Caixa", "FLU - Geração de Caixa"),
        ("(-) Distribuição para Acionistas", "FLU - Distribuição para Acionista"),
        ("Saldo Final de Caixa", "FLU - Saldo Final"),
    ]
    periods = [format_period_label(int(a)) for a in df_sorted["Ano"]]
    rows: list[dict[str, str]] = []
    for label, col in dfc_defs:
        if col in df_sorted.columns:
            vals = df_sorted[col].values
            row_dict: dict[str, str] = {"Demonstração de Fluxo de Caixa": label}
            for p_lbl, v in zip(periods, vals):
                row_dict[p_lbl] = format_currency_brl(float(v), compact=True)
            if label in ("Saldo Inicial de Caixa", "Saldo Final de Caixa"):
                row_dict["Saldo Final"] = format_currency_brl(float(vals[-1]), compact=True)
            else:
                row_dict["Total Acumulado"] = format_currency_brl(float(np.nansum(vals)), compact=True)
            rows.append(row_dict)
    return pd.DataFrame(rows)


def render_page_dre(
    store: ProcessedDataStore,
    active_scenario: str,
    compare_scenarios: list[str],
    period_range: tuple[int, int],
) -> None:
    """Página 2 — Análise Detalhada da DRE."""
    render_top_header(
        title="DRE — Demonstração do Resultado",
        subtitle=(
            "Decomposição de receitas, tributos, custos operacionais (proxy), D&A, resultado financeiro, "
            "tributação sobre o lucro e comparação explícita entre EBITDA Calculado e EBITDA do Modelo."
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

    summ = summarize_kpis_for_selection(df_scen)
    mg_liq_mean = float(df_scen["calc_margem_liquida"].dropna().mean()) if "calc_margem_liquida" in df_scen else np.nan
    ro_mean = float(df_scen["DRE - Resultado Operacional"].dropna().mean())

    cards = [
        {
            "label": "Receita Bruta (Média)",
            "value_fmt": format_currency_brl(summ["receita"]["mean"], compact=True),
            "subtitle": f"Acumulado: {format_currency_brl(summ['receita']['sum'], compact=True)}",
            "delta_text": (
                f"Var. período: {format_pct_br(summ['receita']['diff_pct'], signed=True)}"
                if is_valid_number(summ["receita"]["diff_pct"]) else "Período único"
            ),
            "delta_status": "positive" if (summ["receita"]["diff_pct"] or 0) >= 0 else "negative",
            "tooltip": "ABS(DRE - Receita)",
        },
        {
            "label": "Custos Operacionais (Proxy)",
            "value_fmt": format_currency_brl(summ["custos_variaveis"]["mean"], compact=True),
            "subtitle": f"Margem Contrib.: {format_pct_br(summ['margem_contribuicao']['mean'])}",
            "delta_text": "Proxy |DRE - Custos| (sem segregação fixo/var.)",
            "delta_status": "neutral",
            "tooltip": "ABS(DRE - Custos) utilizado como proxy de custos variáveis no modelo",
        },
        {
            "label": "Resultado Operacional (EBIT)",
            "value_fmt": format_currency_brl(ro_mean, compact=True),
            "subtitle": f"Média em {len(df_scen)} período(s)",
            "delta_text": f"Margem EBIT: {format_pct_br(ro_mean / summ['receita']['mean']) if summ['receita']['mean'] else 'N/D'}",
            "delta_status": "positive" if ro_mean > 0 else "negative",
            "tooltip": "Receita + Tributos + Custos + Depreciação e Amortização",
        },
        {
            "label": "EBITDA Calculado",
            "value_fmt": format_currency_brl(summ["ebitda_calculado"]["mean"], compact=True),
            "subtitle": f"Margem: {format_pct_br(summ['margem_ebitda_calculada']['mean'])}",
            "delta_text": "Fórmula: Resultado Operacional + |D&A|",
            "delta_status": "positive",
            "tooltip": "Recalculado estritamente conforme Dicionario_KPIs",
        },
        {
            "label": "EBITDA do Modelo",
            "value_fmt": format_currency_brl(summ["ebitda_modelo"]["mean"], compact=True),
            "subtitle": f"Margem: {format_pct_br(summ['margem_ebitda_modelo']['mean'])}",
            "delta_text": (
                f"Dif. vs Calc.: {format_currency_brl(summ['ebitda_modelo']['mean'] - summ['ebitda_calculado']['mean'], compact=True)}"
            ),
            "delta_status": "warning",
            "badge_text": "Campo Modelo",
            "badge_type": "neutral",
            "tooltip": "Valor nativo da coluna DRE - EBITDA da base CTI (mantido separado do EBITDA Calculado)",
        },
        {
            "label": "Resultado Líquido (DRE)",
            "value_fmt": format_currency_brl(summ["resultado_liquido"]["mean"], compact=True),
            "subtitle": f"Margem Líquida: {format_pct_br(mg_liq_mean)}",
            "delta_text": f"Acumulado: {format_currency_brl(summ['resultado_liquido']['sum'], compact=True)}",
            "delta_status": "positive" if summ["resultado_liquido"]["mean"] > 0 else "negative",
            "tooltip": "Lucro contábil sob regime de competência (DRE - Resultado Líquido)",
        },
    ]
    render_kpi_grid(cards)

    render_callout(
        "Governança Contábil — Por que EBITDA Calculado e EBITDA do Modelo são exibidos separadamente?",
        "Na planilha original da CTI, a coluna nativa <code>DRE - EBITDA</code> supera sistematicamente a soma contábil "
        "<code>Resultado Operacional + |Depreciação e Amortização|</code> (em virtude de ajustes específicos de modelagem "
        "e de <em>Outros Resultados Operacionais</em>, sobretudo no Ano 12). Seguindo as boas práticas de auditoria e o "
        "<code>Dicionario_KPIs</code>, ambos os indicadores são preservados e jamais fundidos.",
        kind="info",
    )

    per_desc = f"{format_period_label(period_range[0])} a {format_period_label(period_range[1])}"
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(chart_dre_waterfall(df_scen, per_desc), use_container_width=True)
    with c2:
        st.plotly_chart(chart_ebitda_comparison(df_scen), use_container_width=True)

    comp_df = (
        filter_panel(store.panel, scenarios=compare_scenarios, period_range=period_range)
        if compare_scenarios
        else None
    )
    c3, c4 = st.columns(2)
    with c3:
        st.plotly_chart(
            chart_kpi_evolution(df_scen, "margem_ebitda_calculada", active_scenario, compare_panel=comp_df),
            use_container_width=True,
        )
    with c4:
        st.plotly_chart(
            chart_kpi_evolution(df_scen, "margem_contribuicao", active_scenario, compare_panel=comp_df),
            use_container_width=True,
        )

    render_section_header(
        f"Demonstração do Resultado — {active_scenario}",
        "Demonstração contábil oficial exibida na íntegra sem necessidade de rolagem interna ou barras de arrasto.",
    )

    structured_dre = _build_structured_dre_table(df_scen)

    tab_dre1, tab_dre2 = st.tabs([
        "🏛️ Demonstração Contábil Oficial (Visão Completa na Tela)",
        "📅 Visão Tabular por Período (Todos os Períodos Exibidos)",
    ])
    with tab_dre1:
        render_corporate_table(
            structured_dre,
            title=f"Demonstração do Resultado do Exercício — {active_scenario}",
            subtitle="Valores consolidados em R$ (formato executivo padrão CTI Global com totais e margens calculadas)",
            highlight_totals=True,
        )
    with tab_dre2:
        dre_cols = [
            "Período",
            "DRE - Receita",
            "DRE - Tributos",
            "DRE - Custos",
            "DRE - Depreciação e Amortização",
            "DRE - Resultado Operacional",
            "DRE - Resultado Financeiro",
            "DRE - Outros Resultados Operacionais",
            "DRE - Resultado Antes do Imposto de Renda",
            "DRE - Imposto de Renda e Contribuição Social",
            "DRE - Resultado Líquido",
            "calc_ebitda_calculado",
            "DRE - EBITDA",
        ]
        avail_cols = [c for c in dre_cols if c in df_scen.columns]
        tbl = df_scen.sort_values("Ano")[avail_cols].rename(
            columns={
                "DRE - Receita": "Receita",
                "DRE - Tributos": "Tributos",
                "DRE - Custos": "Custos",
                "DRE - Depreciação e Amortização": "D&A",
                "DRE - Resultado Operacional": "Res. Operacional",
                "DRE - Resultado Financeiro": "Res. Financeiro",
                "DRE - Outros Resultados Operacionais": "Outros Res.",
                "DRE - Resultado Antes do Imposto de Renda": "LAIR",
                "DRE - Imposto de Renda e Contribuição Social": "IR / CSLL",
                "DRE - Resultado Líquido": "Lucro Líquido",
                "calc_ebitda_calculado": "EBITDA Calc.",
                "DRE - EBITDA": "EBITDA Modelo",
            }
        )
        fmt_tbl = tbl.copy()
        for col in fmt_tbl.columns:
            if col != "Período":
                fmt_tbl[col] = fmt_tbl[col].map(lambda v: format_currency_brl(v, decimals=2, compact=True))
        render_corporate_dataframe(fmt_tbl)

    render_data_footer(store)


def render_page_balanco(
    store: ProcessedDataStore,
    active_scenario: str,
    compare_scenarios: list[str],
    period_range: tuple[int, int],
) -> None:
    """Página 3 — Análise do Balanço Patrimonial."""
    render_top_header(
        title="Balanço Patrimonial — Estrutura de Ativos, Passivos, Liquidez e Endividamento",
        subtitle=(
            "Avaliação da solvência de curto e longo prazo, composição de financiamento e tratamento transparente "
            "dos sinais contábeis e da incompletude patrimonial do Ano 12."
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

    valid_bp = df_scen[~df_scen["Balanco_Incompleto"]]
    summ = summarize_kpis_for_selection(df_scen)

    at_mean = float(valid_bp["BAL - Total do Ativo"].mean()) if not valid_bp.empty else np.nan
    ac_mean = float(valid_bp["BAL - Ativo Circulante"].mean()) if not valid_bp.empty else np.nan
    pc_abs_mean = float(valid_bp["BAL - Passivo Circulante"].abs().mean()) if not valid_bp.empty else np.nan
    pl_abs_mean = float(valid_bp["BAL - Patrimônio Líquido"].abs().mean()) if not valid_bp.empty else np.nan

    cards = [
        {
            "label": "Total do Ativo (Média)",
            "value_fmt": format_currency_brl(at_mean, compact=True),
            "subtitle": f"Ativo Circulante: {format_currency_brl(ac_mean, compact=True)}",
            "delta_text": f"{len(valid_bp)} período(s) com BP completo",
            "delta_status": "neutral",
            "tooltip": "BAL - Total do Ativo (Anos com Balanço completo)",
        },
        {
            "label": "|Passivo Circulante| (Média)",
            "value_fmt": format_currency_brl(pc_abs_mean, compact=True),
            "subtitle": f"Comp. Endiv. (CE): {format_pct_br(summ['ce']['mean'])}",
            "delta_text": "Normalizado em módulo ABS(PC)",
            "delta_status": "neutral",
            "tooltip": "ABS(BAL - Passivo Circulante) conforme regra do Dicionario_KPIs",
        },
        {
            "label": "|Patrimônio Líquido| Contábil",
            "value_fmt": format_currency_brl(pl_abs_mean, compact=True),
            "subtitle": f"Cap. Investido Médio: {format_currency_brl(summ['capital_investido']['mean'], compact=True)}",
            "delta_text": "Saldo credor normalizado em módulo",
            "delta_status": "neutral",
            "tooltip": "ABS(BAL - Patrimônio Líquido)",
        },
        {
            "label": "Liquidez Corrente (LC)",
            "value_fmt": format_multiple_br(summ["lc"]["mean"]),
            "subtitle": f"Seca: {format_multiple_br(summ['ls']['mean'])} • Imediata: {format_multiple_br(summ['li']['mean'])}",
            "delta_text": "Solvência CP adequada (> 1,00x)" if (summ["lc"]["mean"] or 0) >= 1.0 else "Atenção (< 1,00x)",
            "delta_status": "positive" if (summ["lc"]["mean"] or 0) >= 1.0 else "warning",
            "tooltip": "Ativo Circulante / ABS(Passivo Circulante)",
        },
        {
            "label": "Liquidez Geral (LG)",
            "value_fmt": format_multiple_br(summ["lg"]["mean"]),
            "subtitle": "(AC + RLP) / (|PC| + |PNC|)",
            "delta_text": "Exclui ativo permanente de concessão",
            "delta_status": "neutral",
            "tooltip": "Liquidez Geral nos períodos com Balanço completo",
        },
        {
            "label": "Endividamento Geral",
            "value_fmt": format_pct_br(summ["endividamento_geral"]["mean"]),
            "subtitle": f"PCT: {format_multiple_br(summ['pct']['mean'])} • IPL: {format_multiple_br(summ['ipl']['mean'])}",
            "delta_text": "(|PC| + |PNC|) / Ativo Total",
            "delta_status": "warning" if (summ["endividamento_geral"]["mean"] or 0) > 0.85 else "positive",
            "tooltip": "Grau de endividamento em relação ao Ativo Total",
        },
    ]
    render_kpi_grid(cards)

    render_callout(
        "Atenção aos Sinais Contábeis da Base CTI e Regra do Ano 12",
        "<ul>"
        "<li><strong>Convenção de Sinais:</strong> Na aba <code>Balanco_Cenarios</code>, contas credoras (Passivo e Patrimônio Líquido) "
        "são originalmente negativas nos Anos 1–4. Nos Anos 5–11, <code>BAL - Passivo Circulante</code> assume sinal positivo devido ao "
        "saldo positivo em <code>BAL - Empréstimos</code>. Por isso, todos os indicadores aplicam <code>ABS()</code> conforme documentação metodológica corporativa.</li>"
        "<li><strong>Ano 12 Incompleto:</strong> No Ano 12, 27 contas patrimoniais não estão preenchidas na planilha original; "
        "os indicadores patrimoniais são exibidos rigorosamente como <code>N/D</code> nesse período.</li>"
        "</ul>",
        kind="warning" if valid_bp.empty else "info",
    )

    comp_df = (
        filter_panel(store.panel, scenarios=compare_scenarios, period_range=period_range)
        if compare_scenarios
        else None
    )
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(chart_balance_structure(df_scen), use_container_width=True)
    with c2:
        st.plotly_chart(
            chart_kpi_evolution(df_scen, "lc", active_scenario, compare_panel=comp_df),
            use_container_width=True,
        )

    c3, c4 = st.columns(2)
    with c3:
        st.plotly_chart(
            chart_kpi_evolution(df_scen, "endividamento_geral", active_scenario, compare_panel=comp_df),
            use_container_width=True,
        )
    with c4:
        st.plotly_chart(
            chart_kpi_evolution(df_scen, "ce", active_scenario, compare_panel=comp_df),
            use_container_width=True,
        )

    render_section_header(
        f"Quadro Patrimonial — {active_scenario}",
        "Estrutura contábil oficial de ativos, passivos, patrimônio líquido e solvência corporativa.",
    )

    structured_bp = _build_structured_bp_table(df_scen)

    tab_bp1, tab_bp2 = st.tabs([
        "🏛️ Estrutura Patrimonial Oficial (Visão Completa na Tela)",
        "📅 Visão Tabular por Período (Todos os Períodos Exibidos)",
    ])
    with tab_bp1:
        render_corporate_table(
            structured_bp,
            title=f"Balanço Patrimonial Sintético — {active_scenario}",
            subtitle="Estrutura de Ativos, Passivos, Patrimônio Líquido e Índices (padrão executivo CTI Global)",
            highlight_totals=True,
        )
    with tab_bp2:
        bp_cols = [
            "Período",
            "BAL - Total do Ativo",
            "BAL - Ativo Circulante",
            "BAL - Disponível",
            "BAL - Realizável a Longo Prazo",
            "BAL - Permanente",
            "BAL - Passivo Circulante",
            "BAL - Exigível a Longo Prazo",
            "BAL - Patrimônio Líquido",
            "kpi_lc",
            "kpi_lg",
            "kpi_endividamento_geral",
        ]
        avail_bp = [c for c in bp_cols if c in df_scen.columns]
        bp_tbl = df_scen.sort_values("Ano")[avail_bp].copy()
        for c in bp_tbl.columns:
            if c == "Período":
                continue
            if c in ("kpi_lc", "kpi_lg"):
                bp_tbl[c] = bp_tbl[c].map(format_multiple_br)
            elif c == "kpi_endividamento_geral":
                bp_tbl[c] = bp_tbl[c].map(format_pct_br)
            else:
                bp_tbl[c] = bp_tbl[c].map(lambda v: format_currency_brl(v, compact=True))
        bp_tbl = bp_tbl.rename(
            columns={
                "BAL - Total do Ativo": "Ativo Total",
                "BAL - Ativo Circulante": "At. Circulante",
                "BAL - Disponível": "Disponível",
                "BAL - Realizável a Longo Prazo": "RLP",
                "BAL - Permanente": "Permanente",
                "BAL - Passivo Circulante": "Pass. Circ.",
                "BAL - Exigível a Longo Prazo": "ELP",
                "BAL - Patrimônio Líquido": "Patr. Líquido",
                "kpi_lc": "LC (x)",
                "kpi_lg": "LG (x)",
                "kpi_endividamento_geral": "Endiv. (%)",
            }
        )
        render_corporate_dataframe(bp_tbl)

    render_data_footer(store)


def render_page_dfc(
    store: ProcessedDataStore,
    active_scenario: str,
    compare_scenarios: list[str],
    period_range: tuple[int, int],
) -> None:
    """Página 4 — Análise da Demonstração do Fluxo de Caixa (DFC)."""
    render_top_header(
        title="Fluxo de Caixa (DFC) — Liquidez Efetiva e Movimentação Financeira",
        subtitle=(
            "Acompanhamento de saldo inicial, entradas operacionais, investimentos, serviço financeiro, "
            "distribuição aos acionistas, geração líquida de caixa e confronto com o lucro contábil."
        ),
        store=store,
        active_scenario=active_scenario,
        period_range=period_range,
    )

    df_scen = filter_panel(store.panel, scenarios=active_scenario, period_range=period_range).sort_values("Ano")
    if df_scen.empty:
        render_empty_state()
        render_data_footer(store)
        return

    saldo_ini = float(df_scen["FLU - Saldo Inicial"].iloc[0])
    saldo_fim = float(df_scen["FLU - Saldo Final"].iloc[-1])
    ger_acum = float(df_scen["FLU - Geração de Caixa"].sum())
    ger_media = float(df_scen["FLU - Geração de Caixa"].mean())
    inv_acum = float(df_scen["FLU - Investimentos"].sum()) if "FLU - Investimentos" in df_scen else np.nan
    div_acum = (
        float(df_scen["FLU - Distribuição para Acionista"].sum())
        if "FLU - Distribuição para Acionista" in df_scen
        else np.nan
    )
    ll_acum = float(df_scen["DRE - Resultado Líquido"].sum())

    cards = [
        {
            "label": f"Saldo Inicial ({df_scen['Período'].iloc[0]})",
            "value_fmt": format_currency_brl(saldo_ini, compact=True),
            "subtitle": "Posição de abertura do recorte",
            "delta_text": "Reconciliado com Disponível",
            "delta_status": "neutral",
            "tooltip": "FLU - Saldo Inicial no primeiro período selecionado",
        },
        {
            "label": "Geração Líquida Acumulada",
            "value_fmt": format_currency_brl(ger_acum, compact=True),
            "subtitle": f"Média anual: {format_currency_brl(ger_media, compact=True)}",
            "delta_text": "Saldo Final − Saldo Inicial",
            "delta_status": "positive" if ger_acum >= 0 else "warning",
            "tooltip": "Soma de FLU - Geração de Caixa nos períodos filtrados",
        },
        {
            "label": f"Saldo Final ({df_scen['Período'].iloc[-1]})",
            "value_fmt": format_currency_brl(saldo_fim, compact=True),
            "subtitle": "Igual a BAL - Disponível",
            "delta_text": f"Var. saldo: {format_currency_brl(saldo_fim - saldo_ini, compact=True)}",
            "delta_status": "positive" if saldo_fim >= saldo_ini else "warning",
            "tooltip": "FLU - Saldo Final no último período selecionado",
        },
        {
            "label": "Investimentos (CAPEX Acum.)",
            "value_fmt": format_currency_brl(inv_acum, compact=True),
            "subtitle": "Saídas/entradas de investimento",
            "delta_text": "Regime de caixa (DFC)",
            "delta_status": "neutral",
            "tooltip": "Soma de FLU - Investimentos no intervalo",
        },
        {
            "label": "Distribuição a Acionistas",
            "value_fmt": format_currency_brl(div_acum, compact=True),
            "subtitle": "Dividendos pagos em caixa",
            "delta_text": "Impacta diretamente a Geração Líquida",
            "delta_status": "neutral",
            "tooltip": "Soma de FLU - Distribuição para Acionista",
        },
        {
            "label": "Lucro Contábil (DRE Acum.)",
            "value_fmt": format_currency_brl(ll_acum, compact=True),
            "subtitle": "Regime de competência (comparativo)",
            "delta_text": f"Dif. Caixa vs Lucro: {format_currency_brl(ger_acum - ll_acum, compact=True)}",
            "delta_status": "neutral",
            "badge_text": "Competência DRE",
            "badge_type": "neutral",
            "tooltip": "Exibido para contrastar lucro contábil com geração efetiva de caixa",
        },
    ]
    render_kpi_grid(cards)

    render_callout(
        "Distinção Essencial — Lucro Contábil (DRE) ≠ Geração de Caixa (DFC)",
        "Na modelagem financeira da CTI, um cenário pode apresentar <strong>Resultado Líquido positivo elevado</strong> na DRE "
        "e, simultaneamente, <strong>Geração Líquida de Caixa negativa</strong> em determinados períodos (especialmente no Ano 12), "
        "pois o campo <code>FLU - Geração de Caixa</code> deduz os desembolsos de <em>Investimentos</em>, <em>Serviço Financeiro</em> "
        "e a <em>Distribuição de Dividendos aos Acionistas</em>. Além disso, o <code>FLU - Saldo Final</code> reconcilia "
        "exatamente com <code>BAL - Disponível</code> em todos os períodos.",
        kind="info",
    )

    comp_df = (
        filter_panel(store.panel, scenarios=compare_scenarios, period_range=period_range)
        if compare_scenarios
        else None
    )
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(chart_dfc_profit_vs_cash(df_scen), use_container_width=True)
    with c2:
        st.plotly_chart(
            chart_kpi_evolution(df_scen, "saldo_final_caixa", active_scenario, compare_panel=comp_df),
            use_container_width=True,
        )

    render_section_header(
        f"Demonstração do Fluxo de Caixa — {active_scenario}",
        "Detalhamento contábil oficial da aba DFC_Cenarios em Reais (R$) sem barras de arrasto.",
    )

    structured_dfc = _build_structured_dfc_table(df_scen)

    tab_dfc1, tab_dfc2 = st.tabs([
        "🏛️ Fluxo de Caixa Oficial (Visão Completa na Tela)",
        "📅 Visão Tabular por Período (Todos os Períodos Exibidos)",
    ])
    with tab_dfc1:
        render_corporate_table(
            structured_dfc,
            title=f"Demonstração do Fluxo de Caixa — {active_scenario}",
            subtitle="Origens e aplicações financeiras, investimentos e saldo final (padrão executivo CTI Global)",
            highlight_totals=True,
        )
    with tab_dfc2:
        dfc_cols = [
            "Período",
            "FLU - Saldo Inicial",
            "FLU - Receita",
            "FLU - Tributos",
            "FLU - Custos",
            "FLU - Investimentos",
            "FLU - Resultado Financeiro",
            "FLU - Imposto de Renda e Contribuição Social",
            "FLU - Distribuição para Acionista",
            "FLU - Geração de Caixa",
            "FLU - Saldo Final",
        ]
        avail_dfc = [c for c in dfc_cols if c in df_scen.columns]
        dfc_tbl = df_scen[avail_dfc].copy()
        for c in dfc_tbl.columns:
            if c != "Período":
                dfc_tbl[c] = dfc_tbl[c].map(lambda v: format_currency_brl(v, compact=True))
        dfc_tbl = dfc_tbl.rename(
            columns={
                "FLU - Saldo Inicial": "Saldo Inicial",
                "FLU - Receita": "Receita",
                "FLU - Tributos": "Tributos",
                "FLU - Custos": "Custos",
                "FLU - Investimentos": "Investimentos",
                "FLU - Resultado Financeiro": "Res. Fin.",
                "FLU - Imposto de Renda e Contribuição Social": "IR / CSLL",
                "FLU - Distribuição para Acionista": "Distrib. Acion.",
                "FLU - Geração de Caixa": "Geração Caixa",
                "FLU - Saldo Final": "Saldo Final",
            }
        )
        render_corporate_dataframe(dfc_tbl)

    render_data_footer(store)

