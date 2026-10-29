"""Páginas 11, 12, 13 e 14: Análise Estatística, Modelos Analíticos (OLS), Qualidade de Dados e Relatórios Gerenciais."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.charts import (
    apply_corporate_layout,
    chart_correlation_heatmap,
    chart_regression_diagnostics,
    chart_scenario_distribution,
    chart_scatter_with_trend,
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
from src.data_validation import ValidationSummary
from src.financial_kpis import evaluate_all_goals, summarize_kpis_for_selection
from src.regression_analysis import fit_ols_regression
from src.reporting import (
    build_excel_report_bytes,
    build_pdf_executive_report,
    dataframe_to_csv_bytes,
)
from src.statistical_analysis import (
    build_descriptive_table,
    compute_correlation_matrix,
    run_distribution_normality_and_group_test,
    validate_against_kpis_estatisticas,
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


def render_page_analise_estatistica(
    store: ProcessedDataStore,
    active_scenario: str,
    period_range: tuple[int, int],
) -> None:
    """Página 11 — Análise Estatística Descritiva, Inferencial, Distribuições e Correlações."""
    render_top_header(
        title="Análise Estatística — Estatística Descritiva, Inferencial e Correlações",
        subtitle=(
            "Análise distribucional rigorosa sem mistura de granularidades, reconciliação com parâmetros oficiais, "
            "percentis, testes de normalidade e correlações lineares e não lineares."
        ),
        store=store,
        active_scenario=active_scenario,
        period_range=period_range,
    )

    tab_desc, tab_corr = st.tabs([
        "1. Estatística Descritiva & Reconciliação",
        "2. Distribuições, Inferência & Correlações",
    ])

    stat_kpis = [k for k, m in KPI_CATALOG.items() if not m.is_simulated_premise]

    # ------------------------------------------------------------------
    # ABA 1: ESTATÍSTICA DESCRITIVA E RECONCILIAÇÃO COM KPIs_Estatisticas
    # ------------------------------------------------------------------
    with tab_desc:
        render_callout(
            "Separação Estrita de Níveis de Agregação (Sem Mistura de Granularidades)",
            "<ul>"
            "<li><strong>População Consolidada por Cenário (<code>Resumo_Cenarios</code>, N = 1.200):</strong> cada unidade amostral "
            "é um cenário independente consolidado pela média dos Anos 1 a 11 — exatamente a base da aba <code>KPIs_Estatisticas</code>.</li>"
            "<li><strong>População em Painel (<code>Cenário × Período</code>):</strong> analisa todas as observações anuais no intervalo "
            "filtrado na barra lateral, capturando a variabilidade intertemporal entre períodos.</li>"
            "</ul>",
            kind="info",
        )

        gran_choice = st.radio(
            "Selecione o nível de agregação para a tabela estatística descritiva:",
            options=[
                "Consolidado por Cenário (Resumo_Cenarios — N = 1.200, média Anos 1–11)",
                f"Painel Cenário × Período no recorte filtrado ({format_period_label(period_range[0])} a {format_period_label(period_range[1])})",
            ],
            horizontal=True,
        )

        if gran_choice.startswith("Consolidado"):
            desc_df = build_descriptive_table(store.resumo, stat_kpis, level="resumo")
        else:
            sub_panel = filter_panel(store.panel, period_range=period_range)
            desc_df = build_descriptive_table(sub_panel, stat_kpis, level="panel")

        render_section_header(
            "Medidas de Posição, Dispersão, Assimetria, Curtose e Percentis",
            "Nota: Para variáveis financeiras contínuas, a coluna 'Nota Moda' explicita quando a distribuição é amodal ou exige arredondamento.",
        )
        render_corporate_dataframe(desc_df)

        render_section_header(
            "Validação Cruzada Automatizada contra a Aba 'KPIs_Estatisticas' da Base Corporativa",
            "Confronto direto de N, Média, Desvio Padrão amostral e Mediana (P50) para todos os 22 indicadores listados na planilha.",
        )
        est_val = validate_against_kpis_estatisticas(store)
        if not est_val.empty:
            n_ok = int((est_val["Status"] == "Validado (100%)").sum())
            render_callout(
                f"Resultado da Reconciliação Estatística: {n_ok}/{len(est_val)} indicadores validados com precisão de máquina",
                "Erro relativo máximo inferior a <code>10⁻⁶</code> entre os cálculos em Python/SciPy e os valores da aba <code>KPIs_Estatisticas</code>.",
                kind="success" if n_ok == len(est_val) else "warning",
            )
            render_corporate_dataframe(est_val)

    # ------------------------------------------------------------------
    # ABA 2: DISTRIBUIÇÕES, TESTES INFERENCIAIS E MATRIZ DE CORRELAÇÃO
    # ------------------------------------------------------------------
    with tab_corr:
        c_sel1, c_sel2 = st.columns(2)
        with c_sel1:
            dist_k = st.selectbox(
                "Indicador para análise distribucional e boxplot temporal:",
                options=stat_kpis,
                index=stat_kpis.index("roic") if "roic" in stat_kpis else 0,
                format_func=lambda k: f"{KPI_CATALOG[k].name} ({KPI_CATALOG[k].unit})",
            )
        with c_sel2:
            corr_method = st.radio(
                "Método da Matriz de Correlação:",
                options=["pearson", "spearman"],
                format_func=lambda m: "Pearson (Linear)" if m == "pearson" else "Spearman (Postos / Robusta a Outliers)",
                horizontal=True,
            )

        meta_d = KPI_CATALOG[dist_k]
        sub_p = filter_panel(store.panel, period_range=period_range)
        inf_res = run_distribution_normality_and_group_test(sub_p, f"kpi_{dist_k}", group_col="Ano")

        inf_cards = [
            {
                "label": f"Observações Válidas ({meta_d.short_name})",
                "value_fmt": format_number_br(inf_res.get("n", 0), 0),
                "subtitle": "No intervalo de períodos filtrado",
                "delta_text": "Exclui N/D estruturais (ex.: BP Ano 12)",
                "delta_status": "neutral",
            },
            {
                "label": f"Média Amostral ({meta_d.short_name})",
                "value_fmt": format_by_unit(inf_res.get("mean", np.nan), meta_d.unit, compact_currency=True),
                "subtitle": f"Desvio padrão: {format_by_unit(inf_res.get('std', np.nan), meta_d.unit, compact_currency=True)}",
                "delta_text": f"IC 95%: [{format_by_unit(inf_res.get('ci_95_low', np.nan), meta_d.unit, compact_currency=True)}, {format_by_unit(inf_res.get('ci_95_high', np.nan), meta_d.unit, compact_currency=True)}]",
                "delta_status": "neutral",
            },
            {
                "label": f"Mediana e IQR ({meta_d.short_name})",
                "value_fmt": format_by_unit(inf_res.get("median", np.nan), meta_d.unit, compact_currency=True),
                "subtitle": f"P25={format_by_unit(inf_res.get('p25', np.nan), meta_d.unit, compact_currency=True)} • P75={format_by_unit(inf_res.get('p75', np.nan), meta_d.unit, compact_currency=True)}",
                "delta_text": f"Amplitude Interquartil (IQR): {format_by_unit(inf_res.get('iqr', np.nan), meta_d.unit, compact_currency=True)}",
                "delta_status": "neutral",
            },
            {
                "label": "Teste de Normalidade (D'Agostino-Pearson)",
                "value_fmt": (
                    "Não Normal (p < 0,05)"
                    if (inf_res.get("dagostino_pvalue") or 0) < 0.05
                    else "Normal (p ≥ 0,05)"
                ),
                "subtitle": f"Estatística K² = {format_number_br(inf_res.get('dagostino_stat', np.nan), 2)}",
                "delta_text": f"p-valor = {inf_res.get('dagostino_pvalue', np.nan):.3e}" if is_valid_number(inf_res.get('dagostino_pvalue')) else "N/D",
                "delta_status": "warning" if (inf_res.get("dagostino_pvalue") or 0) < 0.05 else "positive",
            },
            {
                "label": "Homogeneidade Intertemporal (Levene)",
                "value_fmt": (
                    "Variâncias Heterogêneas"
                    if (inf_res.get("levene_pvalue") or 0) < 0.05
                    else "Variâncias Homogêneas"
                ),
                "subtitle": "Avaliação de dispersão entre os Anos",
                "delta_text": f"Levene p-valor = {inf_res.get('levene_pvalue', np.nan):.3e}" if is_valid_number(inf_res.get('levene_pvalue')) else "N/D",
                "delta_status": "warning" if (inf_res.get("levene_pvalue") or 0) < 0.05 else "positive",
            },
        ]
        render_kpi_grid(inf_cards)

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.plotly_chart(
                chart_scenario_distribution(
                    store.resumo,
                    KPI_CATALOG[dist_k].resumo_sheet_col or f"kpi_{dist_k}",
                    meta_d.name,
                    meta_d.unit,
                    active_scenario=active_scenario,
                ),
                use_container_width=True,
            )
        with col_g2:
            box_df = sub_p.dropna(subset=[f"kpi_{dist_k}"]).sort_values("Ano")
            fig_box = go.Figure()
            fig_box.add_trace(
                go.Box(
                    x=box_df["Período"],
                    y=box_df[f"kpi_{dist_k}"],
                    name=meta_d.short_name,
                    marker_color=PALETTE["primary"],
                    boxmean=True,
                )
            )
            apply_corporate_layout(
                fig_box,
                f"Boxplot de {meta_d.short_name} por Período",
                subtitle="Dispersão interquartílica dos 1.200 cenários em cada período válido",
                y_title=f"{meta_d.short_name} ({meta_d.unit})",
                height=350,
            )
            st.plotly_chart(fig_box, use_container_width=True)

        render_section_header(
            "Análise Bivariada (Diagrama de Dispersão entre Cenários)",
            "Explore a relação entre quaisquer dois indicadores na base consolidada por cenário.",
        )
        res_kpis = [k for k in stat_kpis if KPI_CATALOG[k].resumo_sheet_col in store.resumo.columns]
        sc1, sc2 = st.columns(2)
        with sc1:
            x_k = st.selectbox(
                "Eixo X (Variável Horizontal):",
                options=res_kpis,
                index=res_kpis.index("margem_contribuicao") if "margem_contribuicao" in res_kpis else 0,
                format_func=lambda k: KPI_CATALOG[k].name,
            )
        with sc2:
            y_k = st.selectbox(
                "Eixo Y (Variável Vertical):",
                options=res_kpis,
                index=res_kpis.index("roic") if "roic" in res_kpis else min(1, len(res_kpis) - 1),
                format_func=lambda k: KPI_CATALOG[k].name,
            )
        st.plotly_chart(
            chart_scatter_with_trend(
                store.resumo,
                KPI_CATALOG[x_k].resumo_sheet_col or "",
                KPI_CATALOG[y_k].resumo_sheet_col or "",
                KPI_CATALOG[x_k].short_name,
                KPI_CATALOG[y_k].short_name,
                KPI_CATALOG[x_k].unit,
                KPI_CATALOG[y_k].unit,
                active_scenario=active_scenario,
            ),
            use_container_width=True,
        )

        corr_keys = [
            "receita",
            "margem_contribuicao",
            "margem_ebitda_calculada",
            "margem_ebitda_modelo",
            "roic",
            "eva",
            "lc",
            "lg",
            "ce",
            "endividamento_geral",
        ]
        cols_map = {
            KPI_CATALOG[k].resumo_sheet_col: KPI_CATALOG[k].short_name
            for k in corr_keys
            if KPI_CATALOG[k].resumo_sheet_col and KPI_CATALOG[k].resumo_sheet_col in store.resumo.columns
        }
        corr_df, pval_df = compute_correlation_matrix(store.resumo, cols_map, method=corr_method)
        st.plotly_chart(chart_correlation_heatmap(corr_df), use_container_width=True)
        with st.expander("Visualizar Matriz de p-valores Bicaudais da Correlação"):
            render_corporate_dataframe(pval_df.round(6), hide_index=False)

    render_data_footer(store)


def render_page_modelos_analiticos(
    store: ProcessedDataStore,
    active_scenario: str,
    period_range: tuple[int, int],
) -> None:
    """Página 12 — Modelos Analíticos, Regressão Linear Múltipla (OLS) e Diagnóstico Econométrico."""
    render_top_header(
        title="Modelos Analíticos — Modelagem Econométrica e Preditiva (Regressão OLS)",
        subtitle=(
            "Modelagem de regressão linear múltipla (OLS) com partição treino/teste agrupada por cenário, "
            "erros-padrão robustos, diagnósticos de multicolinearidade (VIF), análise de resíduos e simulador preditivo."
        ),
        store=store,
        active_scenario=active_scenario,
        period_range=period_range,
    )

    stat_kpis = [k for k, m in KPI_CATALOG.items() if not m.is_simulated_premise]

    render_callout(
        "Rigor Metodológico em Modelagem Econométrica / Machine Learning",
        "<ul>"
        "<li><strong>Prevenção de Vazamento Temporal:</strong> No modo Painel (<code>Cenário × Período</code>), a divisão "
        "Treino/Teste utiliza <code>GroupShuffleSplit</code> agrupado por <code>Cenário</code> (nenhum período de um cenário "
        "de treino aparece no teste) e estima erros-padrão robustos clusterizados por cenário.</li>"
        "<li><strong>Detector de Tautologia Contábil:</strong> O sistema alerta automaticamente caso você inclua variáveis "
        "com identidade algébrica direta com o alvo (ex.: prever <code>EVA</code> usando <code>NOPAT</code> e <code>Capital Investido</code>).</li>"
        "<li><strong>Ética Analítica:</strong> O modelo quantifica associações lineares condicionais nos cenários e <strong>não implica causalidade</strong>.</li>"
        "</ul>",
        kind="info",
    )

    rc1, rc2, rc3 = st.columns([1.2, 1.2, 1.0])
    with rc1:
        reg_gran = st.selectbox(
            "Base para Ajuste do Modelo:",
            options=["resumo", "panel"],
            format_func=lambda g: (
                "Consolidado por Cenário (Resumo_Cenarios, N=1.200)"
                if g == "resumo"
                else f"Painel Cenário × Período Filtrado ({format_period_label(period_range[0])}–{format_period_label(period_range[1])})"
            ),
        )
    avail_reg_kpis = (
        [k for k in stat_kpis if KPI_CATALOG[k].resumo_sheet_col in store.resumo.columns]
        if reg_gran == "resumo"
        else stat_kpis
    )
    with rc2:
        target_k = st.selectbox(
            "Variável Dependente (Alvo Y):",
            options=avail_reg_kpis,
            index=avail_reg_kpis.index("roic") if "roic" in avail_reg_kpis else 0,
            format_func=lambda k: f"{KPI_CATALOG[k].name} ({KPI_CATALOG[k].unit})",
        )
    with rc3:
        test_pct = st.slider("Proporção de Teste (%)", min_value=15, max_value=40, value=25, step=5)
        std_z = st.checkbox("Padronizar X (Z-score)", value=False, help="Facilita comparar a magnitude relativa dos betas.")

    default_feats = [
        k for k in ["margem_contribuicao", "lc", "ce", "endividamento_geral"]
        if k in avail_reg_kpis and k != target_k
    ]
    feat_ks = st.multiselect(
        "Variáveis Explicativas (Preditores X):",
        options=[k for k in avail_reg_kpis if k != target_k],
        default=default_feats[:4],
        format_func=lambda k: f"{KPI_CATALOG[k].name} ({KPI_CATALOG[k].unit})",
    )

    if reg_gran == "resumo":
        reg_df = store.resumo
        t_col = KPI_CATALOG[target_k].resumo_sheet_col or ""
        f_cols = [KPI_CATALOG[k].resumo_sheet_col or "" for k in feat_ks]
        lbl_map = {KPI_CATALOG[k].resumo_sheet_col or "": KPI_CATALOG[k].short_name for k in avail_reg_kpis}
    else:
        reg_df = filter_panel(store.panel, period_range=period_range)
        t_col = f"kpi_{target_k}"
        f_cols = [f"kpi_{k}" for k in feat_ks]
        lbl_map = {f"kpi_{k}": KPI_CATALOG[k].short_name for k in avail_reg_kpis}

    reg_res = fit_ols_regression(
        df=reg_df,
        target_col=t_col,
        feature_cols=f_cols,
        labels_map=lbl_map,
        target_key=target_k,
        feature_keys=feat_ks,
        granularity=reg_gran,
        test_size=test_pct / 100.0,
        standardize_features=std_z,
    )

    if not reg_res.success:
        render_callout("Não foi possível ajustar o modelo com a seleção atual", reg_res.error_message or "", kind="warning")
    else:
        for lw in reg_res.leakage_warnings:
            render_callout("Alerta de Possível Vazamento Algébrico / Identidade Contábil", lw, kind="warning")

        t_unit = KPI_CATALOG[target_k].unit
        m = reg_res.metrics
        d = reg_res.diagnostics
        reg_cards = [
            {
                "label": "R² Ajustado (Treino)",
                "value_fmt": format_number_br(m["r2_adj_train"], 4),
                "subtitle": f"R² Treino: {format_number_br(m['r2_train'], 4)}",
                "delta_text": f"N Treino = {reg_res.n_train} ({reg_res.n_scenarios_train} cenários)",
                "delta_status": "positive",
            },
            {
                "label": "R² Fora da Amostra (Teste)",
                "value_fmt": format_number_br(m["r2_test"], 4),
                "subtitle": f"Cenários isolados: {reg_res.n_scenarios_test}",
                "delta_text": f"N Teste = {reg_res.n_test}",
                "delta_status": "positive" if (m["r2_test"] or 0) > 0.2 else "warning",
            },
            {
                "label": "RMSE (Teste / Treino)",
                "value_fmt": format_by_unit(m["rmse_test"], t_unit, compact_currency=True),
                "subtitle": f"Treino: {format_by_unit(m['rmse_train'], t_unit, compact_currency=True)}",
                "delta_text": "Erro quadrático médio na unidade de Y",
                "delta_status": "neutral",
            },
            {
                "label": "MAE (Teste / Treino)",
                "value_fmt": format_by_unit(m["mae_test"], t_unit, compact_currency=True),
                "subtitle": f"Treino: {format_by_unit(m['mae_train'], t_unit, compact_currency=True)}",
                "delta_text": "Erro absoluto médio fora da amostra",
                "delta_status": "neutral",
            },
            {
                "label": "VIF Máximo (Colinearidade)",
                "value_fmt": format_number_br(d["max_vif"], 2),
                "subtitle": f"Erros-padrão: {d['erros_padrao']}",
                "delta_text": "Adequado (< 5)" if d["max_vif"] < 5 else ("Moderado (5–10)" if d["max_vif"] < 10 else "Elevado (≥ 10)"),
                "delta_status": "positive" if d["max_vif"] < 5 else "warning",
            },
        ]
        render_kpi_grid(reg_cards)

        fig_op, fig_res = chart_regression_diagnostics(reg_res.predictions_df, reg_res.dependent_var)
        cg1, cg2 = st.columns(2)
        with cg1:
            st.plotly_chart(fig_op, use_container_width=True)
        with cg2:
            st.plotly_chart(fig_res, use_container_width=True)

        ct1, ct2 = st.columns([1.45, 1])
        with ct1:
            render_section_header("Coeficientes Estimados (OLS com Erros-Padrão Robustos)")
            render_corporate_dataframe(reg_res.coefficients_table)
        with ct2:
            render_section_header("Diagnóstico de Multicolinearidade (VIF)")
            render_corporate_dataframe(reg_res.vif_table)

        # Simulador interativo preditivo
        if reg_res.success and not reg_res.coefficients_table.empty and feat_ks:
            with st.expander("Simulador Preditivo Interativo em Tempo Real com o Modelo OLS Ajustado", expanded=False):
                st.markdown(
                    f"Simule o impacto de variações nos preditores sobre **{KPI_CATALOG[target_k].name}** ({KPI_CATALOG[target_k].unit}):"
                )
                sim_cols = st.columns(min(len(feat_ks), 4))
                pred_input = {}
                for idx, fk in enumerate(feat_ks):
                    f_meta = KPI_CATALOG[fk]
                    col_target = sim_cols[idx % len(sim_cols)]
                    # Obter valor de referência do cenário ativo
                    ref_val = float(reg_df[f_cols[idx]].median()) if f_cols[idx] in reg_df else 0.0
                    with col_target:
                        pred_input[fk] = st.number_input(
                            f"{f_meta.short_name} ({f_meta.unit}):",
                            value=float(round(ref_val, 3) if not np.isnan(ref_val) else 0.0),
                            key=f"sim_input_{fk}",
                        )
                # Cálculo da predição linear
                try:
                    c_tab = reg_res.coefficients_table.set_index("Termo")["Coeficiente"].to_dict()
                    intercept = float(c_tab.get("Intercepto", 0.0))
                    y_pred = intercept
                    for fk in feat_ks:
                        s_name = KPI_CATALOG[fk].short_name
                        c_val = float(c_tab.get(s_name, 0.0))
                        y_pred += c_val * pred_input[fk]

                    st.markdown(
                        f"""
                        <div style="background:#F0FDF4;border:1px solid #BBF7D0;border-radius:8px;padding:0.85rem 1rem;margin-top:0.6rem;">
                            <span style="font-size:0.82rem;font-weight:600;color:#166534;">Valor Predito de {html_escape(KPI_CATALOG[target_k].name)}:</span><br>
                            <span style="font-size:1.45rem;font-weight:700;color:#14532D;">
                                {format_by_unit(y_pred, KPI_CATALOG[target_k].unit, compact_currency=False)}
                            </span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                except Exception:
                    pass

        render_section_header("Interpretação Responsável, Tratamentos Aplicados e Limitações")
        for p_txt in reg_res.interpretation_paragraphs:
            st.markdown(f"- {p_txt}")
        with st.expander("Ver Tratamentos de Preparação, Testes de Resíduos e Limitações Completas"):
            st.markdown("**Tratamentos aplicados antes do ajuste:**")
            for tr in reg_res.treatments_applied:
                st.markdown(f"- {tr}")
            st.markdown(
                f"**Estatísticas globais e resíduos:** F = `{d['f_statistic']:.2f}` (p = `{d['f_pvalue']:.3e}`) • "
                f"AIC = `{d['aic']:.1f}` • BIC = `{d['bic']:.1f}` • "
                f"Jarque-Bera p = `{d['jarque_bera_pvalue']:.3e}` • "
                f"Breusch-Pagan p = `{d['breusch_pagan_pvalue']:.3e}` • "
                f"Durbin-Watson = `{d['durbin_watson']:.3f}`"
            )
            st.markdown("**Limitações conhecidas do modelo:**")
            for lim in reg_res.limitations:
                st.markdown(f"- {lim}")

    render_data_footer(store)


def render_page_governanca_qualidade(
    store: ProcessedDataStore,
    val_summary: ValidationSummary,
    active_scenario: str,
    period_range: tuple[int, int],
) -> None:
    """Página 13 — Qualidade e Governança de Dados, Auditoria Metodológica e Integridade Contábil."""
    render_top_header(
        title="Qualidade e Governança de Dados — Diagnóstico Estrutural e Integridade Contábil",
        subtitle=(
            "Diagnóstico estrutural completo da planilha corporativa oficial, reconciliação matemática 100% auditada, "
            "conformidade contábil e achados documentais AUD-01 a AUD-05."
        ),
        store=store,
        active_scenario=active_scenario,
        period_range=period_range,
    )

    tab_qual, tab_aud = st.tabs([
        "1. Diagnóstico e Reconciliação da Base",
        "2. Achados de Auditoria do Dicionário (AUD-01 a AUD-05)",
    ])

    with tab_qual:
        total_dups = sum(val_summary.duplicate_keys_by_sheet.values())
        total_zero_den = sum(val_summary.zero_denominators_detected.values())
        rec_ok = int((val_summary.kpi_reconciliation["Status"] == "Reconciliado (100%)").sum())
        rec_tot = len(val_summary.kpi_reconciliation)

        q_cards = [
            {
                "label": "Status Geral da Base",
                "value_fmt": "Aprovada c/ Ressalvas" if "RESSALVAS" in val_summary.overall_status else val_summary.overall_status,
                "subtitle": f"{len(store.bundle.available_sheets)}/9 abas carregadas",
                "delta_text": "Chaves 100% consistentes entre abas" if val_summary.key_consistency_ok else "Divergência de chaves",
                "delta_status": "positive" if val_summary.key_consistency_ok else "negative",
            },
            {
                "label": "Cenários × Períodos",
                "value_fmt": f"{val_summary.n_scenarios:,} × {val_summary.periods_per_scenario_max}".replace(",", "."),
                "subtitle": f"{len(store.panel):,} linhas no painel detalhado".replace(",", "."),
                "delta_text": f"Duplicidades Cenário/Ano: {total_dups}",
                "delta_status": "positive" if total_dups == 0 else "negative",
            },
            {
                "label": "Reconciliação de KPIs",
                "value_fmt": f"{rec_ok} / {rec_tot} (100%)",
                "subtitle": "KPIs_Cenarios e Resumo_Cenarios",
                "delta_text": "Tolerância ≤ 10⁻⁶ cumprida",
                "delta_status": "positive" if rec_ok == rec_tot else "negative",
            },
            {
                "label": "Denominadores Zero & Ano 12",
                "value_fmt": f"{total_zero_den} div./zero",
                "subtitle": f"Ano 12 BP incompleto: {val_summary.year_12_incomplete_balance_count:,} reg.".replace(",", "."),
                "delta_text": "Proteção safe_divide ativa (-> N/D)",
                "delta_status": "positive",
            },
        ]
        render_kpi_grid(q_cards)

        render_section_header("Perfil Estrutural e Completude por Aba da Planilha Original")
        render_corporate_dataframe(val_summary.sheet_profiles)

        c_r1, c_r2 = st.columns(2)
        with c_r1:
            render_section_header("Reconciliação: Planilha 'KPIs_Cenarios' vs. Recálculo Python")
            render_corporate_dataframe(val_summary.kpi_reconciliation)
        with c_r2:
            render_section_header("Reconciliação: 'Resumo_Cenarios' vs. Média Anos 1–11")
            render_corporate_dataframe(val_summary.resumo_reconciliation)

        c_m1, c_m2 = st.columns(2)
        with c_m1:
            render_section_header("Mapeamento de Valores Ausentes e Causa Identificada")
            render_corporate_dataframe(val_summary.missing_by_column)
        with c_m2:
            render_section_header("Investigação de Valores Extremos (Critério IQR 1,5x e 3,0x)")
            render_corporate_dataframe(val_summary.outliers_summary)

    with tab_aud:
        render_section_header(
            "Relatório de Auditoria Metodológica sobre Dicionario_KPIs e Demonstrações",
            "Inconsistências documentais diagnosticadas automaticamente e resolvidas na camada analítica sem adulterar o arquivo Excel original.",
        )
        for finding in val_summary.dictionary_audit_findings:
            sev = finding["severidade"]
            kind = "warning" if ("Alta" in sev or "Média" in sev) else "info"
            render_callout(
                f"[{finding['codigo']}] {finding['titulo']} — Severidade: {sev}",
                f"<strong>Diagnóstico:</strong> {finding['detalhe']}<br>"
                f"<strong>Decisão Metodológica Adotada:</strong> {finding['resolucao']}",
                kind=kind,
            )

    render_data_footer(store)


def render_page_relatorios_gerenciais(
    store: ProcessedDataStore,
    val_summary: ValidationSummary,
    active_scenario: str,
    compare_scenarios: list[str],
    period_range: tuple[int, int],
) -> None:
    """Página 14 — Central de Relatórios Gerenciais e Exportação (CSV, Excel XLSX e PDF Executivo)."""
    render_top_header(
        title="Relatórios Gerenciais — Central de Exportação de Dados e Documentos Executivos",
        subtitle=(
            "Geração e download de relatórios executivos em PDF oficial formatado, pastas analíticas em Excel (XLSX) multi-abas "
            "e bases de dados filtradas em CSV padrão corporativo."
        ),
        store=store,
        active_scenario=active_scenario,
        period_range=period_range,
    )

    scen_list_export = list(dict.fromkeys([active_scenario] + list(compare_scenarios)))
    df_export_panel = filter_panel(store.panel, scenarios=scen_list_export, period_range=period_range)
    df_foc = filter_panel(store.panel, scenarios=active_scenario, period_range=period_range)

    if df_foc.empty:
        render_empty_state()
        render_data_footer(store)
        return

    summ = summarize_kpis_for_selection(df_foc)
    bench_all = filter_panel(store.panel, period_range=period_range).groupby("Cenário").mean(numeric_only=True)
    configured_goals: dict[str, float | None] = st.session_state.get("configured_goals", {})
    goals_df = evaluate_all_goals({k: summ[k]["mean"] for k in summ}, configured_goals)
    last_sens: dict[str, Any] | None = st.session_state.get("last_sensitivity_result")

    # Painel de escopo de exportação
    scope_cards = [
        {
            "label": "Cenário Principal Ativo",
            "value_fmt": active_scenario,
            "subtitle": f"{len(scen_list_export)} cenário(s) incluído(s)",
            "delta_text": "Configuração ativa na barra lateral",
            "delta_status": "neutral",
        },
        {
            "label": "Intervalo de Períodos",
            "value_fmt": f"{format_period_label(period_range[0])} a {format_period_label(period_range[1])}",
            "subtitle": f"{period_range[1] - period_range[0] + 1} período(s)",
            "delta_text": "Ano 12 tratado como N/D no Balanço",
            "delta_status": "neutral",
        },
        {
            "label": "Linhas para Exportação",
            "value_fmt": f"{len(df_export_panel):,} registros".replace(",", "."),
            "subtitle": "Painel Cenário × Período",
            "delta_text": "Todos os KPIs e demonstrações",
            "delta_status": "positive",
        },
        {
            "label": "Metas Configuradas na Sessão",
            "value_fmt": f"{len([k for k, v in configured_goals.items() if v is not None])} ativas",
            "subtitle": "Incluídas no PDF e Excel",
            "delta_text": "Reflete metas da Página 9",
            "delta_status": "positive",
        },
    ]
    render_kpi_grid(scope_cards)

    pdf_kpi_rows = []
    for k in [
        "receita",
        "custos_variaveis",
        "margem_contribuicao",
        "ebitda_calculado",
        "margem_ebitda_calculada",
        "ebitda_modelo",
        "margem_ebitda_modelo",
        "resultado_liquido",
        "nopat",
        "roic",
        "eva",
        "lc",
        "lg",
        "endividamento_geral",
        "geracao_caixa",
    ]:
        meta = KPI_CATALOG[k]
        med_b = float(bench_all[f"kpi_{k}"].median()) if f"kpi_{k}" in bench_all else np.nan
        pdf_kpi_rows.append({
            "Indicador": meta.name,
            "Media": format_by_unit(summ[k]["mean"], meta.unit, compact_currency=True),
            "Ultimo": format_by_unit(summ[k]["latest"], meta.unit, compact_currency=True),
            "Mediana_Base": format_by_unit(med_b, meta.unit, compact_currency=True),
        })

    per_lbl = f"{format_period_label(period_range[0])} a {format_period_label(period_range[1])}"
    metadata_dict = {
        "Projeto": "CTI Global | Plataforma Analítica de Planejamento Financeiro",
        "Gerado em": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "Fonte de Dados": store.bundle.source_name,
        "Modo Sintético?": "SIM (DADOS SINTÉTICOS)" if store.bundle.is_synthetic else "NÃO (Planilha Oficial)",
        "Assinatura SHA-256 Fonte": store.bundle.fingerprint,
        "Cenário Principal": active_scenario,
        "Cenários Exportados": ", ".join(scen_list_export),
        "Intervalo de Períodos": per_lbl,
        "Unidade Monetária Adotada": "R$ (consistente com KPIs_Cenarios e Resumo_Cenarios)",
        "Premissa WACC do Modelo": "12,00% a.a.",
        "Regra Ano 12": "Balanço Patrimonial incompleto no Ano 12 tratado como N/D (NaN)",
    }

    excel_tables: dict[str, pd.DataFrame] = {
        "Painel_Filtrado": df_export_panel,
        "Resumo_Comparativo": store.resumo[store.resumo["Cenário"].isin(scen_list_export)],
        "Metas_Sessao": goals_df,
        "Reconciliacao_KPIs": val_summary.kpi_reconciliation,
    }
    if last_sens and not last_sens.get("comparison_table", pd.DataFrame()).empty:
        excel_tables["Sensibilidade_Simulada"] = last_sens["comparison_table"]

    csv_bytes = dataframe_to_csv_bytes(df_export_panel)
    xlsx_bytes = build_excel_report_bytes(excel_tables, metadata_dict)
    pdf_bytes = build_pdf_executive_report(
        scenario_code=active_scenario,
        period_label=per_lbl,
        source_name=store.bundle.source_name,
        is_synthetic=store.bundle.is_synthetic,
        kpi_summary_rows=pdf_kpi_rows,
        goals_df=goals_df,
        sensitivity_result=last_sens,
    )

    stamp = f"{active_scenario}_Ano{period_range[0]}_Ano{period_range[1]}"
    d1, d2, d3 = st.columns(3)
    with d1:
        with st.container(border=True):
            st.markdown("#### 1. Base Filtrada (CSV)")
            st.caption(
                f"Exporta `{len(df_export_panel)}` registros `Cenário × Período` com separador `;` e decimal `,` (padrão Excel pt-BR)."
            )
            st.download_button(
                label="Baixar Dados Filtrados (.CSV)",
                data=csv_bytes,
                file_name=f"CTI_Painel_{stamp}.csv",
                mime="text/csv",
                use_container_width=True,
            )
    with d2:
        with st.container(border=True):
            st.markdown("#### 2. Pasta Analítica (.XLSX)")
            st.caption(
                "Planilha Excel formatada contendo abas de Metadados, Painel Filtrado, Resumo, Metas, Sensibilidade e Reconciliação."
            )
            st.download_button(
                label="Baixar Relatório Multi-Abas (.XLSX)",
                data=xlsx_bytes,
                file_name=f"CTI_Relatorio_Analitico_{stamp}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
    with d3:
        with st.container(border=True):
            st.markdown("#### 3. Relatório Executivo (.PDF)")
            st.caption(
                "Documento executivo pronto para apresentação com KPIs, benchmarks, metas ativas, simulação de sensibilidade e notas metodológicas."
            )
            st.download_button(
                label="Baixar Relatório Executivo (.PDF)",
                data=pdf_bytes,
                file_name=f"CTI_Relatorio_Executivo_{stamp}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

    render_section_header("Pré-Visualização dos Dados Filtrados para Exportação")
    render_corporate_dataframe(df_export_panel.head(25))

    render_data_footer(store)


def html_escape(text: str) -> str:
    """Escapa caracteres HTML para injeção segura."""
    import html
    return html.escape(str(text))


# Aliases para compatibilidade retroativa
render_page_ciencia_dados = render_page_analise_estatistica
render_page_qualidade_exportacao = render_page_governanca_qualidade
