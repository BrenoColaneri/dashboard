"""Páginas 5 a 7: Indicadores Financeiros (KPIs), Cenários & Rankings e Análise de Evolução (Ano 1 a Ano 12)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.charts import (
    SERIES_COLORS,
    apply_corporate_layout,
    chart_kpi_evolution,
    chart_scenario_distribution,
)
from src.config import (
    KPI_CATALOG,
    PALETTE,
    format_by_unit,
    format_number_br,
    format_pct_br,
    format_period_label,
    is_valid_number,
)
from src.data_processing import ProcessedDataStore, filter_panel
from src.financial_kpis import compute_variation, summarize_kpis_for_selection
from src.ui_components import (
    render_callout,
    render_corporate_dataframe,
    render_data_footer,
    render_empty_state,
    render_kpi_grid,
    render_section_header,
    render_top_header,
)


def render_page_indicadores(
    store: ProcessedDataStore,
    active_scenario: str,
    compare_scenarios: list[str],
    period_range: tuple[int, int],
    selected_categories: list[str],
) -> None:
    """Página 5 — Catálogo Analítico de Indicadores Financeiros e Dicionário de KPIs."""
    render_top_header(
        title="Indicadores Financeiros — Catálogo Auditado e Dicionário de KPIs",
        subtitle=(
            "Consulta estruturada por categoria (Liquidez, Endividamento, Rentabilidade, Fluxo de Caixa e Premissas), "
            "com fórmulas documentadas, interpretação gerencial, premissas e comparação com KPIs_Estatisticas."
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

    filtered_keys = [
        k for k, m in KPI_CATALOG.items()
        if (not selected_categories or m.category in selected_categories)
    ]
    if not filtered_keys:
        render_empty_state(
            "Nenhuma categoria de indicador selecionada",
            "Selecione ao menos uma categoria de KPI no filtro da barra lateral.",
        )
        render_data_footer(store)
        return

    summ = summarize_kpis_for_selection(df_scen)

    # Agrupamento por categoria em cartões claros
    categories_in_order = list(dict.fromkeys(KPI_CATALOG[k].category for k in filtered_keys))
    for cat in categories_in_order:
        cat_keys = [k for k in filtered_keys if KPI_CATALOG[k].category == cat]
        render_section_header(cat, f"{len(cat_keys)} indicador(es) nesta dimensão analítica.")
        cards: list[dict[str, Any]] = []
        for k in cat_keys:
            meta = KPI_CATALOG[k]
            info = summ[k]
            val = info["mean"]
            is_sim = meta.is_simulated_premise
            cards.append({
                "label": meta.short_name,
                "value_fmt": format_by_unit(val, meta.unit, compact_currency=True),
                "subtitle": f"Fórmula: {meta.formula[:54]}{'...' if len(meta.formula) > 54 else ''}",
                "delta_text": (
                    "Premissa constante do modelo corporativo"
                    if is_sim
                    else (
                        f"Var. recorte: {format_pct_br(info['diff_pct'], signed=True)}"
                        if is_valid_number(info["diff_pct"])
                        else f"{info['valid_count']} período(s) válido(s)"
                    )
                ),
                "delta_status": "simulated" if is_sim else "neutral",
                "badge_text": "Premissa Simulada" if is_sim else ("Observado" if is_valid_number(val) else "N/D"),
                "badge_type": "simulated" if is_sim else ("real" if is_valid_number(val) else "warning"),
                "tooltip": f"{meta.name} | {meta.interpretation}",
                "card_variant": "is-simulated" if is_sim else "",
            })
        render_kpi_grid(cards)

    # Explorador profundo de indicador individual
    render_section_header(
        "Ficha Metodológica Completa e Benchmark Estatístico do Indicador",
        "Selecione qualquer indicador para inspecionar sua evolução, distribuição, fórmula auditada e limitações.",
    )
    non_sim_keys = [k for k in filtered_keys if not KPI_CATALOG[k].is_simulated_premise] or filtered_keys
    sel_kpi = st.selectbox(
        "Selecione o indicador para inspeção detalhada:",
        options=non_sim_keys,
        format_func=lambda k: f"{KPI_CATALOG[k].name} ({KPI_CATALOG[k].unit}) — {KPI_CATALOG[k].category}",
    )
    meta_sel = KPI_CATALOG[sel_kpi]

    col_info, col_chart = st.columns([1, 1.25])
    with col_info:
        st.markdown(
            f"""
            | Atributo | Especificação Auditada |
            | :--- | :--- |
            | **Indicador** | **{meta_sel.name}** |
            | **Categoria** | {meta_sel.category} |
            | **Unidade Adotada** | `{meta_sel.unit}` *(Dicionário bruto: `{meta_sel.dictionary_raw_unit}`)* |
            | **Fórmula Aplicada** | `{meta_sel.formula}` |
            | **Fonte / Abas** | {meta_sel.source} |
            | **Granularidade** | {meta_sel.granularity} |
            | **Disponível no Ano 12?** | {"Sim (Anos 1 a 12)" if meta_sel.available_in_year_12 else "Não — Exibido como N/D (Balanço incompleto)"} |
            | **Natureza do Dado** | {"Premissa Simulada de Modelo" if meta_sel.is_simulated_premise else "Dado Observado / Recalculado Auditável"} |
            """
        )
        render_callout(
            "Interpretação, Premissas e Limitações",
            f"<strong>Objetivo:</strong> {meta_sel.objective}<br>"
            f"<strong>Interpretação:</strong> {meta_sel.interpretation}<br>"
            f"<strong>Premissas:</strong> {meta_sel.premises}<br>"
            f"<strong>Limitações:</strong> {meta_sel.limitations}",
            kind="simulated" if meta_sel.is_simulated_premise else "info",
        )

    with col_chart:
        if not meta_sel.is_simulated_premise:
            comp_df = (
                filter_panel(store.panel, scenarios=compare_scenarios, period_range=period_range)
                if compare_scenarios
                else None
            )
            med_series = filter_panel(store.panel, period_range=period_range).groupby("Ano")[f"kpi_{sel_kpi}"].median()
            st.plotly_chart(
                chart_kpi_evolution(
                    df_scen,
                    sel_kpi,
                    active_scenario,
                    compare_panel=comp_df,
                    median_by_period=med_series,
                ),
                use_container_width=True,
            )
            if meta_sel.resumo_sheet_col and meta_sel.resumo_sheet_col in store.resumo.columns:
                st.plotly_chart(
                    chart_scenario_distribution(
                        store.resumo,
                        meta_sel.resumo_sheet_col,
                        meta_sel.short_name,
                        meta_sel.unit,
                        active_scenario,
                    ),
                    use_container_width=True,
                )

    with st.expander("Consultar Aba Original 'Dicionario_KPIs' e 'KPIs_Estatisticas' da Planilha"):
        st.caption(
            "Nota de Auditoria (AUD-01): Na planilha original preservada abaixo, a coluna 'Regra de validação' "
            "sofreu desalinhamento de ordenação nas linhas 2–20. O catálogo auditado acima corrige o mapeamento sem alterar o Excel."
        )
        render_corporate_dataframe(store.dicionario_ref)
        if not store.estatisticas_ref.empty:
            st.markdown("**Estatísticas Consolidadas de Referência (`KPIs_Estatisticas`, N = 1.200 cenários):**")
            render_corporate_dataframe(store.estatisticas_ref)

    render_data_footer(store)


def render_page_cenarios_rankings(
    store: ProcessedDataStore,
    active_scenario: str,
    compare_scenarios: list[str],
) -> None:
    """Página 6 — Cenários, Rankings Multidimensionais e Comparador Multicenário."""
    render_top_header(
        title="Cenários e Rankings — Análise Comparativa Multidimensional",
        subtitle=(
            "Classificação dos 1.200 cenários consolidados (média Anos 1 a 11) por Rentabilidade, Liquidez, "
            "Retorno Moderado e Baixo Risco, com comparador multicenário."
        ),
        store=store,
        active_scenario=active_scenario,
        period_range=(1, 11),
        extra_pill="Granularidade: Consolidado por Cenário (Anos 1–11)",
    )

    if store.resumo.empty:
        render_empty_state("Aba Resumo_Cenarios não disponível.")
        render_data_footer(store)
        return

    render_callout(
        "Princípio de Análise Multidimensional — Não existe 'melhor cenário absoluto' em uma única métrica",
        "Um cenário classificado em <strong>1º lugar em Alta Rentabilidade</strong> (maior Margem EBITDA do Modelo) "
        "não é necessariamente o melhor em <em>Liquidez</em>, <em>Alavancagem (PCT)</em> ou <em>Baixo Risco</em>. "
        "Abaixo apresentamos as cinco dimensões oficiais de <code>Top10_Rankings</code> e o posicionamento relativo completo. "
        "Observação: na métrica <code>Score baixo risco</code>, <strong>quanto menor o valor numérico do score, menor é o risco composto</strong>.",
        kind="info",
    )

    # Posição do cenário ativo nas principais dimensões
    res = store.resumo.copy()
    n_tot = len(res)
    res["rank_rentab"] = res["Margem EBITDA modelo"].rank(ascending=False, method="min")
    res["rank_roic"] = res["ROIC"].rank(ascending=False, method="min")
    res["rank_lc"] = res["LC"].rank(ascending=False, method="min")
    res["rank_risco"] = res["Score baixo risco"].rank(ascending=True, method="min")

    act_row = res[res["Cenário"] == active_scenario]
    if not act_row.empty:
        r0 = act_row.iloc[0]
        cards = [
            {
                "label": f"Ranking Rentabilidade ({active_scenario})",
                "value_fmt": f"{int(r0['rank_rentab'])}º / {n_tot}",
                "subtitle": f"Mg. EBITDA Modelo: {format_pct_br(r0['Margem EBITDA modelo'])}",
                "delta_text": f"Mg. EBITDA Calc.: {format_pct_br(r0['Margem EBITDA calculada'])}",
                "delta_status": "positive" if r0["rank_rentab"] <= n_tot * 0.25 else "neutral",
                "tooltip": "Ordenado pela maior média da Margem EBITDA do Modelo (Anos 1–11)",
            },
            {
                "label": "Ranking ROIC",
                "value_fmt": f"{int(r0['rank_roic'])}º / {n_tot}",
                "subtitle": f"ROIC Médio: {format_pct_br(r0['ROIC'])}",
                "delta_text": f"EVA Médio: {format_by_unit(r0['EVA (R$)'], 'R$', compact_currency=True)}",
                "delta_status": "positive" if r0["ROIC"] >= 0.12 else "warning",
                "tooltip": "Ordenado pelo maior Retorno sobre o Capital Investido (Anos 1–11)",
            },
            {
                "label": "Ranking Liquidez Corrente",
                "value_fmt": f"{int(r0['rank_lc'])}º / {n_tot}",
                "subtitle": f"LC Média: {format_by_unit(r0['LC'], 'x')}",
                "delta_text": f"Endiv. Geral: {format_pct_br(r0['Endiv. Geral'])}",
                "delta_status": "positive" if r0["LC"] >= 1.0 else "warning",
                "tooltip": "Ordenado pela maior Liquidez Corrente média (Anos 1–11)",
            },
            {
                "label": "Ranking Baixo Risco",
                "value_fmt": f"{int(r0['rank_risco'])}º / {n_tot}",
                "subtitle": f"Score Baixo Risco: {format_number_br(r0['Score baixo risco'], 4)}",
                "delta_text": "Menor score = menor risco composto",
                "delta_status": "positive" if r0["rank_risco"] <= n_tot * 0.25 else "neutral",
                "tooltip": "Ordenado pelo menor valor de Score baixo risco",
            },
        ]
        render_kpi_grid(cards)

    # Top 10 oficiais da aba Top10_Rankings + Ranking customizável
    c_top, c_dist = st.columns([1.05, 1])
    with c_top:
        render_section_header(
            "Top 10 Cenários por Categoria Oficial (Top10_Rankings)",
            "Categorias extraídas diretamente da classificação consolidada do plano de contas.",
        )
        if not store.top10.empty and "Categoria" in store.top10.columns:
            cats = store.top10["Categoria"].dropna().unique().tolist()
            sel_cat = st.selectbox("Categoria do Top 10:", options=cats)
            sub_top = store.top10[store.top10["Categoria"] == sel_cat].copy()
            # Formata o indicador conforme a categoria
            cat_up = str(sel_cat).upper()
            if "LIQUIDEZ" in cat_up:
                sub_top["Valor Formatado"] = sub_top["Indicador"].map(lambda v: format_by_unit(v, "x"))
            elif "RISCO" in cat_up:
                sub_top["Valor Formatado"] = sub_top["Indicador"].map(lambda v: format_number_br(v, 4))
            else:
                sub_top["Valor Formatado"] = sub_top["Indicador"].map(format_pct_br)
            render_corporate_dataframe(
                sub_top[["Posição", "Cenário", "Valor Formatado", "Critério"]],
            )

    with c_dist:
        render_section_header(
            "Distribuição Estatística entre todos os Cenários",
            "Posição do cenário selecionado frente à população completa de cenários.",
        )
        dist_metric_map = {
            "Margem EBITDA calculada": ("Margem EBITDA Calculada", "%"),
            "Margem EBITDA modelo": ("Margem EBITDA do Modelo", "%"),
            "ROIC": ("ROIC Médio", "%"),
            "EVA (R$)": ("EVA Médio", "R$"),
            "LC": ("Liquidez Corrente (LC)", "x"),
            "Endiv. Geral": ("Endividamento Geral", "%"),
            "Score baixo risco": ("Score Baixo Risco", "score"),
            "Receita média (R$)": ("Receita Média", "R$"),
        }
        avail_m = [m for m in dist_metric_map if m in store.resumo.columns]
        sel_m = st.selectbox(
            "Métrica da distribuição:",
            options=avail_m,
            format_func=lambda m: dist_metric_map[m][0],
        )
        m_label, m_unit = dist_metric_map[sel_m]
        st.plotly_chart(
            chart_scenario_distribution(store.resumo, sel_m, m_label, m_unit, active_scenario),
            use_container_width=True,
        )

    # Comparação multicenário lado a lado
    render_section_header(
        "Comparação Multicenário Lado a Lado (Médias Anos 1 a 11)",
        "Inclui automaticamente o cenário foco e os cenários comparadores escolhidos na barra lateral.",
    )
    scen_to_compare = list(dict.fromkeys([active_scenario] + list(compare_scenarios)))
    if len(scen_to_compare) == 1 and len(store.scenarios) >= 3:
        # Sugere o 1º do ranking de rentabilidade e o 1º de baixo risco para enriquecer a comparação inicial
        top_rent = res.sort_values("rank_rentab").iloc[0]["Cenário"]
        top_risk = res.sort_values("rank_risco").iloc[0]["Cenário"]
        scen_to_compare = list(dict.fromkeys([active_scenario, str(top_rent), str(top_risk)]))
        st.caption(
            f"Dica: Como nenhum comparador extra foi marcado na barra lateral, incluímos automaticamente "
            f"**{top_rent}** (1º em Margem EBITDA Modelo) e **{top_risk}** (1º em Baixo Risco) como referências."
        )

    sub_comp = res[res["Cenário"].isin(scen_to_compare)].copy()
    display_rows = []
    for _, row in sub_comp.iterrows():
        display_rows.append({
            "Cenário": row["Cenário"],
            "Pos. Rentab.": f"{int(row['rank_rentab'])}º",
            "Pos. Baixo Risco": f"{int(row['rank_risco'])}º",
            "Receita Média": format_by_unit(row.get("Receita média (R$)"), "R$", compact_currency=True),
            "Mg. Contribuição": format_pct_br(row.get("Margem de contribuição média")),
            "Mg. EBITDA Calc.": format_pct_br(row.get("Margem EBITDA calculada")),
            "Mg. EBITDA Modelo": format_pct_br(row.get("Margem EBITDA modelo")),
            "ROIC": format_pct_br(row.get("ROIC")),
            "EVA Médio": format_by_unit(row.get("EVA (R$)"), "R$", compact_currency=True),
            "LC": format_by_unit(row.get("LC"), "x"),
            "Endiv. Geral": format_pct_br(row.get("Endiv. Geral")),
            "Score Baixo Risco": format_number_br(row.get("Score baixo risco"), 4),
        })
    render_corporate_dataframe(pd.DataFrame(display_rows))

    # Busca rápida e tabela explorável de Ranking_Cenarios
    render_section_header(
        "Explorador Completo de Cenários (Busca e Ordenação Customizada)",
        "Filtre por código ou ordene os 1.200 cenários por qualquer critério.",
    )
    col_s1, col_s2, col_s3 = st.columns([1.2, 1.2, 0.8])
    with col_s1:
        q_code = st.text_input("Filtrar tabela por código (ex.: Cen_00462 ou 0015):", value="")
    with col_s2:
        sort_col = st.selectbox(
            "Ordenar cenários por:",
            options=avail_m,
            format_func=lambda m: dist_metric_map[m][0],
        )
    with col_s3:
        asc_default = True if sort_col == "Score baixo risco" else False
        sort_asc = st.checkbox("Ordem crescente", value=asc_default)

    explorer_df = store.resumo.copy()
    if q_code.strip():
        explorer_df = explorer_df[explorer_df["Cenário"].str.contains(q_code.strip(), case=False, na=False)]
    explorer_df = explorer_df.sort_values(sort_col, ascending=sort_asc).head(100)

    exp_cols = [
        "Cenário",
        "Receita média (R$)",
        "Margem de contribuição média",
        "Margem EBITDA calculada",
        "Margem EBITDA modelo",
        "ROIC",
        "EVA (R$)",
        "LC",
        "LG",
        "Endiv. Geral",
        "Score baixo risco",
    ]
    exp_cols = [c for c in exp_cols if c in explorer_df.columns]
    render_corporate_dataframe(explorer_df[exp_cols])

    render_data_footer(store)


def render_page_evolucao(
    store: ProcessedDataStore,
    active_scenario: str,
    compare_scenarios: list[str],
    period_range: tuple[int, int],
) -> None:
    """Página 7 — Análise de Evolução Temporal (Ano 1 a Ano 12)."""
    render_top_header(
        title="Análise de Evolução Temporal — Períodos Ano 1 a Ano 12",
        subtitle=(
            "Trajetória histórica/projetada ao longo dos 12 períodos numerados do modelo, variações de ponta a ponta "
            "(Ano 1 vs. Ano 11 e Ano 1 vs. Ano 12) e comparação conjunta de indicadores."
        ),
        store=store,
        active_scenario=active_scenario,
        period_range=period_range,
    )

    df_full_scen = filter_panel(store.panel, scenarios=active_scenario).sort_values("Ano")
    df_scen = filter_panel(store.panel, scenarios=active_scenario, period_range=period_range).sort_values("Ano")
    if df_scen.empty:
        render_empty_state()
        render_data_footer(store)
        return

    render_callout(
        "Regra Temporal — Períodos Numerados (Ano 1 a Ano 12) e Fechamento do Ano 12",
        "Os períodos <code>Ano 1</code> a <code>Ano 12</code> representam períodos sequenciais numerados da modelagem da CTI "
        "(jamais convertidos arbitrariamente em anos civis como 2024 ou 2025). Na comparação estrutural abaixo, "
        "exibimos tanto <strong>Ano 1 vs. Ano 11</strong> (último período com Balanço Patrimonial completo) quanto "
        "<strong>Ano 1 vs. Ano 12</strong> (disponível para Receita, Custos, Margens da DRE e Fluxo de Caixa).",
        kind="info",
    )

    # Seletor multi-KPI para evolução comparada
    evol_candidates = [
        k for k, m in KPI_CATALOG.items()
        if not m.is_simulated_premise
    ]
    sel_kpis = st.multiselect(
        "Selecione até 4 indicadores para visualizar a evolução temporal:",
        options=evol_candidates,
        default=["receita", "ebitda_calculado", "roic", "lc"],
        max_selections=4,
        format_func=lambda k: f"{KPI_CATALOG[k].name} ({KPI_CATALOG[k].unit})",
    )

    comp_df = (
        filter_panel(store.panel, scenarios=compare_scenarios, period_range=period_range)
        if compare_scenarios
        else None
    )
    all_period_df = filter_panel(store.panel, period_range=period_range)

    if sel_kpis:
        cols = st.columns(2 if len(sel_kpis) > 1 else 1)
        for idx, k in enumerate(sel_kpis):
            with cols[idx % len(cols)]:
                med_s = all_period_df.groupby("Ano")[f"kpi_{k}"].median()
                st.plotly_chart(
                    chart_kpi_evolution(
                        df_scen,
                        k,
                        active_scenario,
                        compare_panel=comp_df,
                        median_by_period=med_s,
                    ),
                    use_container_width=True,
                )

    # Gráfico de índice base 100 (Ano inicial do recorte = 100) para comparar trajetórias de unidades distintas
    render_section_header(
        "Trajetória Normalizada em Base 100 (Primeiro Período do Recorte = 100)",
        "Permite comparar a velocidade relativa de crescimento entre grandezas de unidades diferentes (R$, %, x).",
    )
    idx_fig = go.Figure()
    base_keys = sel_kpis or ["receita", "ebitda_calculado", "resultado_liquido"]
    for i, k in enumerate(base_keys):
        col = f"kpi_{k}"
        s = df_scen[["Período", col]].dropna()
        if len(s) >= 2 and abs(float(s[col].iloc[0])) > 1e-9 and float(s[col].iloc[0]) > 0:
            norm_vals = (s[col].astype(float) / float(s[col].iloc[0])) * 100.0
            idx_fig.add_trace(
                go.Scatter(
                    x=s["Período"],
                    y=norm_vals,
                    mode="lines+markers",
                    name=KPI_CATALOG[k].short_name,
                    line=dict(color=SERIES_COLORS[i % len(SERIES_COLORS)], width=2.4),
                )
            )
    idx_fig.add_hline(y=100.0, line_dash="dot", line_color="#94A3B8")
    apply_corporate_layout(
        idx_fig,
        f"Índice de Evolução Relativa — {active_scenario} (Base 100)",
        subtitle="Exibe indicadores com valor inicial estritamente positivo no recorte filtrado",
        y_title="Índice (Base 100)",
        height=350,
    )
    st.plotly_chart(idx_fig, use_container_width=True)

    # Tabela comparativa Ano 1 vs Ano 11 vs Ano 12
    render_section_header(
        f"Quadro Comparativo de Ponta a Ponta — {active_scenario} (Ano 1 vs. Ano 11 e Ano 12)",
        "Variação percentual calculada apenas quando a base inicial é positiva; indicadores em % exibem variação em pontos percentuais (p.p.).",
    )
    by_year = df_full_scen.set_index("Ano")
    comp_rows = []
    for k in evol_candidates:
        meta = KPI_CATALOG[k]
        col = f"kpi_{k}"
        v1 = by_year.loc[1, col] if (1 in by_year.index and col in by_year.columns) else np.nan
        v11 = by_year.loc[11, col] if (11 in by_year.index and col in by_year.columns) else np.nan
        v12 = by_year.loc[12, col] if (12 in by_year.index and col in by_year.columns) else np.nan

        var_1_11 = compute_variation(v11, v1, is_percentage_point_metric=(meta.unit == "%"))
        var_1_12 = compute_variation(v12, v1, is_percentage_point_metric=(meta.unit == "%"))

        def _fmt_var(var_d: dict[str, float], unit: str) -> str:
            if not is_valid_number(var_d["diff_abs"]):
                return "N/D"
            if unit == "%":
                return f"{format_pct_br(var_d['diff_abs'], signed=True)} (p.p.)"
            if is_valid_number(var_d["diff_pct"]):
                return format_pct_br(var_d["diff_pct"], signed=True)
            return format_by_unit(var_d["diff_abs"], unit, compact_currency=True)

        comp_rows.append({
            "Indicador": meta.name,
            "Unidade": meta.unit,
            "Ano 1": format_by_unit(v1, meta.unit, compact_currency=True),
            "Ano 11 (BP Completo)": format_by_unit(v11, meta.unit, compact_currency=True),
            "Var. Ano 1 -> Ano 11": _fmt_var(var_1_11, meta.unit),
            "Ano 12": format_by_unit(v12, meta.unit, compact_currency=True),
            "Var. Ano 1 -> Ano 12": _fmt_var(var_1_12, meta.unit),
        })
    render_corporate_dataframe(pd.DataFrame(comp_rows))

    render_data_footer(store)

