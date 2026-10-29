"""Fábrica de Visualizações Interativas Corporativas (Plotly) em Padrão Brasileiro (pt-BR).

Princípios de visualização:
- Clareza executiva: títulos autoexplicativos, unidades explícitas nos eixos e tooltips em pt-BR (`separators=",."`).
- Proibição de gráficos 3D, velocímetros decorativos ou excesso de gráficos de pizza.
- Contraste rigoroso entre valores Observados (`#0B5D3B`) e Simulados (`#1D4ED8`) ou Metas (`#6D28D9`).
- Responsividade: margens enxutas e legendas horizontais adaptáveis a telas de 360 px, 768 px e 1366 px.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from src.config import KPI_CATALOG, PALETTE, format_by_unit, is_valid_number

SERIES_COLORS = [
    "#0B5D3B",  # Verde institucional
    "#0F766E",  # Teal escuro
    "#334155",  # Slate 700
    "#15803D",  # Verde médio
    "#B45309",  # Âmbar escuro
    "#4338CA",  # Índigo
]


def apply_corporate_layout(
    fig: go.Figure,
    title: str,
    subtitle: str = "",
    y_title: str = "",
    x_title: str = "",
    height: int = 370,
) -> go.Figure:
    """Aplica identidade visual limpa, separadores numéricos pt-BR e layout responsivo."""
    full_title = (
        f"<b>{title}</b><br><span style='font-size:12px;color:#64748B;font-weight:normal'>{subtitle}</span>"
        if subtitle
        else f"<b>{title}</b>"
    )
    fig.update_layout(
        title=dict(text=full_title, x=0.0, xanchor="left", font=dict(size=15, color=PALETTE["neutral_dark"])),
        font=dict(family="Inter, Segoe UI, Roboto, sans-serif", size=12, color=PALETTE["neutral_dark"]),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        separators=",.",
        height=height,
        autosize=True,
        margin=dict(l=10, r=10, t=52 if subtitle else 38, b=78 if x_title else 66),
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.28,
            xanchor="center",
            x=0.5,
            font=dict(size=10.5),
            bgcolor="rgba(255,255,255,0.85)",
        ),
        xaxis=dict(
            title=x_title,
            showgrid=False,
            linecolor=PALETTE["border"],
            tickfont=dict(size=11, color=PALETTE["neutral"]),
            automargin=True,
        ),
        yaxis=dict(
            title=y_title,
            gridcolor="#F1F5F9",
            zerolinecolor="#CBD5E1",
            tickfont=dict(size=11, color=PALETTE["neutral"]),
            automargin=True,
        ),
    )
    return fig


def _axis_format_for_unit(unit: str) -> dict[str, str]:
    if unit == "%":
        return {"tickformat": ".1%", "hoverformat": ".2%"}
    if unit == "x":
        return {"ticksuffix": "x", "hoverformat": ",.2f"}
    if unit in ("R$", "R$ mil"):
        return {"tickprefix": "R$ ", "hoverformat": ",.2f"}
    if unit == "R$/cliente":
        return {"tickprefix": "R$ ", "ticksuffix": "/cli", "hoverformat": ",.2f"}
    return {"hoverformat": ",.2f"}


def chart_kpi_evolution(
    df_scen: pd.DataFrame,
    kpi_key: str,
    scenario_name: str,
    target_value: float | None = None,
    compare_panel: pd.DataFrame | None = None,
    median_by_period: pd.Series | None = None,
) -> go.Figure:
    """Gráfico de evolução temporal (`Ano 1`..`Ano 12`) com benchmark, comparadores e linha de meta."""
    meta = KPI_CATALOG[kpi_key]
    col = f"kpi_{kpi_key}"
    ax_fmt = _axis_format_for_unit(meta.unit)

    fig = go.Figure()
    ordered = df_scen.sort_values("Ano")

    # Mediana de todos os cenários por período (contexto da distribuição)
    if median_by_period is not None and not median_by_period.empty:
        med_aligned = ordered["Ano"].map(median_by_period)
        fig.add_trace(
            go.Scatter(
                x=ordered["Período"],
                y=med_aligned,
                mode="lines",
                name="Mediana da Base (1.200 cenários)",
                line=dict(color="#94A3B8", width=1.8, dash="dot"),
                connectgaps=False,
            )
        )

    # Cenários comparadores adicionais
    if compare_panel is not None and not compare_panel.empty:
        for idx, (c_name, grp) in enumerate(compare_panel.groupby("Cenário")):
            if c_name == scenario_name:
                continue
            g_ord = grp.sort_values("Ano")
            color = SERIES_COLORS[(idx + 1) % len(SERIES_COLORS)]
            fig.add_trace(
                go.Scatter(
                    x=g_ord["Período"],
                    y=g_ord[col],
                    mode="lines+markers",
                    name=str(c_name),
                    line=dict(color=color, width=1.9),
                    marker=dict(size=6),
                    connectgaps=False,
                )
            )

    # Série principal do cenário selecionado
    fig.add_trace(
        go.Scatter(
            x=ordered["Período"],
            y=ordered[col],
            mode="lines+markers",
            name=f"{scenario_name} (Observado)",
            line=dict(color=PALETTE["primary"], width=3.0),
            marker=dict(size=8, color=PALETTE["primary"]),
            connectgaps=False,
        )
    )

    # Linha horizontal de meta configurada pelo usuário
    if target_value is not None and is_valid_number(target_value):
        fig.add_hline(
            y=float(target_value),
            line_dash="dash",
            line_color=PALETTE["target"],
            line_width=2,
            annotation_text=f"Meta: {format_by_unit(target_value, meta.unit, compact_currency=True)}",
            annotation_position="top left",
            annotation_font_color=PALETTE["target"],
        )

    sub = f"Unidade: {meta.unit} • Períodos numerados do modelo"
    if not meta.available_in_year_12:
        sub += " • Ano 12 = N/D (Balanço incompleto na fonte)"

    apply_corporate_layout(fig, f"Evolução de {meta.name}", subtitle=sub, y_title=f"{meta.short_name} ({meta.unit})")
    fig.update_yaxes(**ax_fmt)
    return fig


def chart_dre_waterfall(dre_df: pd.DataFrame, period_desc: str) -> go.Figure:
    """Gráfico em cascata (Waterfall) da formação do Resultado Líquido na DRE."""
    s = dre_df.mean(numeric_only=True)
    rec = abs(float(s.get("DRE - Receita", 0.0)))
    trib = float(s.get("DRE - Tributos", 0.0))
    cust = float(s.get("DRE - Custos", 0.0))
    da = float(s.get("DRE - Depreciação e Amortização", 0.0))
    ro = float(s.get("DRE - Resultado Operacional", 0.0))
    rf = float(s.get("DRE - Resultado Financeiro", 0.0))
    outros = float(s.get("DRE - Outros Resultados Operacionais", 0.0))
    ir = float(s.get("DRE - Imposto de Renda e Contribuição Social", 0.0))
    ll = float(s.get("DRE - Resultado Líquido", 0.0))

    labels = [
        "Receita Bruta",
        "Tributos",
        "Custos (Proxy)",
        "D&A",
        "Result. Operacional",
        "Result. Financeiro",
        "Outros Operac.",
        "IR / CSLL",
        "Resultado Líquido",
    ]
    measures = ["absolute", "relative", "relative", "relative", "total", "relative", "relative", "relative", "total"]
    values = [rec, trib, cust, da, ro, rf, outros, ir, ll]
    texts = [format_by_unit(v, "R$", compact_currency=True) for v in values]

    fig = go.Figure(
        go.Waterfall(
            orientation="v",
            measure=measures,
            x=labels,
            y=values,
            text=texts,
            textposition="outside",
            connector=dict(line=dict(color="#CBD5E1", width=1)),
            increasing=dict(marker=dict(color=PALETTE["primary"])),
            decreasing=dict(marker=dict(color=PALETTE["negative"])),
            totals=dict(marker=dict(color="#1E293B")),
        )
    )
    apply_corporate_layout(
        fig,
        "Formação do Resultado Contábil (DRE — Regime de Competência)",
        subtitle=f"Média anual no recorte ({period_desc}) em R$",
        y_title="Valor (R$)",
        height=400,
    )
    fig.update_yaxes(tickprefix="R$ ")
    return fig


def chart_ebitda_comparison(df_scen: pd.DataFrame) -> go.Figure:
    """Compara separadamente o EBITDA Calculado (RO + |D&A|) e o EBITDA do Modelo (DRE - EBITDA)."""
    ordered = df_scen.sort_values("Ano")
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=ordered["Período"],
            y=ordered["calc_ebitda_calculado"],
            name="EBITDA Calculado (RO + |D&A|)",
            marker_color=PALETTE["primary"],
        )
    )
    fig.add_trace(
        go.Bar(
            x=ordered["Período"],
            y=ordered["calc_ebitda_modelo"],
            name="EBITDA do Modelo (DRE - EBITDA)",
            marker_color="#64748B",
        )
    )
    apply_corporate_layout(
        fig,
        "Comparação Estrita: EBITDA Calculado vs. EBITDA do Modelo",
        subtitle="Indicadores mantidos separados conforme governança metodológica da plataforma (em R$)",
        y_title="EBITDA (R$)",
        height=370,
    )
    fig.update_layout(barmode="group")
    fig.update_yaxes(tickprefix="R$ ")
    return fig


def chart_balance_structure(df_scen: pd.DataFrame) -> go.Figure:
    """Evolução da composição patrimonial do Ativo e Passivo/PL (Anos válidos com Balanço completo)."""
    valid = df_scen[~df_scen["Balanco_Incompleto"]].sort_values("Ano")
    fig = go.Figure()
    if valid.empty:
        apply_corporate_layout(fig, "Estrutura Patrimonial Indisponível no Recorte (Ano 12 = N/D)")
        return fig

    fig.add_trace(
        go.Bar(
            x=valid["Período"],
            y=valid["BAL - Ativo Circulante"],
            name="Ativo Circulante",
            marker_color=PALETTE["primary"],
        )
    )
    fig.add_trace(
        go.Bar(
            x=valid["Período"],
            y=valid["BAL - Realizável a Longo Prazo"],
            name="Realizável a Longo Prazo",
            marker_color="#0F766E",
        )
    )
    fig.add_trace(
        go.Bar(
            x=valid["Período"],
            y=valid["BAL - Permanente"],
            name="Ativo Permanente",
            marker_color="#94A3B8",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=valid["Período"],
            y=valid["BAL - Passivo Circulante"].abs() + valid["BAL - Exigível a Longo Prazo"].abs(),
            mode="lines+markers",
            name="Exigível Total em Módulo (|PC| + |PNC|)",
            line=dict(color=PALETTE["negative"], width=2.5),
            marker=dict(size=7),
        )
    )
    apply_corporate_layout(
        fig,
        "Composição do Ativo Total vs. Passivo Exigível em Módulo",
        subtitle="Exibido apenas para períodos com Balanço completo (Ano 12 omitido como N/D)",
        y_title="Saldo Patrimonial (R$)",
        height=390,
    )
    fig.update_layout(barmode="stack")
    fig.update_yaxes(tickprefix="R$ ")
    return fig


def chart_dfc_profit_vs_cash(df_scen: pd.DataFrame) -> go.Figure:
    """Contrasta Lucro Líquido Contábil (DRE) vs. Geração de Caixa e Saldo Final (DFC)."""
    ordered = df_scen.sort_values("Ano")
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=ordered["Período"],
            y=ordered["FLU - Geração de Caixa"],
            name="Geração Líquida de Caixa (DFC)",
            marker_color=PALETTE["primary"],
        )
    )
    fig.add_trace(
        go.Bar(
            x=ordered["Período"],
            y=ordered["DRE - Resultado Líquido"],
            name="Resultado Líquido Contábil (DRE)",
            marker_color="#94A3B8",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=ordered["Período"],
            y=ordered["FLU - Saldo Final"],
            mode="lines+markers",
            name="Saldo Final de Caixa (= Disponível)",
            line=dict(color="#0F766E", width=2.8),
            marker=dict(size=7),
        )
    )
    apply_corporate_layout(
        fig,
        "Regime de Caixa (DFC) vs. Regime de Competência (Lucro Contábil DRE)",
        subtitle="Evidencia por que lucro contábil positivo pode coexistir com saída líquida de caixa (ex.: dividendos/dívida)",
        y_title="Valor (R$)",
        height=390,
    )
    fig.update_layout(barmode="group")
    fig.update_yaxes(tickprefix="R$ ")
    return fig


def chart_scenario_distribution(
    resumo_df: pd.DataFrame,
    col: str,
    label: str,
    unit: str,
    active_scenario: str = "",
) -> go.Figure:
    """Histograma da distribuição dos 1.200 cenários destacando a posição do cenário selecionado e a mediana."""
    s = pd.to_numeric(resumo_df[col], errors="coerce").dropna()
    fig = go.Figure()
    fig.add_trace(
        go.Histogram(
            x=s,
            nbinsx=36,
            name="Distribuição dos Cenários",
            marker_color="#CBD5E1",
            marker_line=dict(color="#94A3B8", width=0.8),
        )
    )

    med_val = float(s.median()) if not s.empty else np.nan
    if is_valid_number(med_val):
        fig.add_vline(
            x=med_val,
            line_dash="dot",
            line_color="#475569",
            line_width=2,
            annotation_text=f"Mediana: {format_by_unit(med_val, unit, compact_currency=True)}",
            annotation_position="top left",
        )

    scen_row = resumo_df[resumo_df["Cenário"] == active_scenario]
    if not scen_row.empty and is_valid_number(scen_row[col].iloc[0]):
        s_val = float(scen_row[col].iloc[0])
        fig.add_vline(
            x=s_val,
            line_dash="solid",
            line_color=PALETTE["primary"],
            line_width=3,
            annotation_text=f"{active_scenario}: {format_by_unit(s_val, unit, compact_currency=True)}",
            annotation_position="top right",
            annotation_font_color=PALETTE["primary"],
        )

    apply_corporate_layout(
        fig,
        f"Posição de {active_scenario} na Distribuição de {label}",
        subtitle=f"Base consolidada por cenário (N = {len(s)} cenários, média Anos 1–11)",
        x_title=f"{label} ({unit})",
        y_title="Frequência (Nº de Cenários)",
        height=350,
    )
    fig.update_layout(hovermode="closest")
    fig.update_xaxes(**_axis_format_for_unit(unit))
    return fig


def chart_sensitivity_bars(comp_table: pd.DataFrame, unit_filter: str = "R$") -> go.Figure:
    """Compara graficamente Valores Observados vs. Simulados separando grandezas monetárias e percentuais."""
    sub = comp_table[comp_table["Unidade"] == unit_filter].copy()
    fig = go.Figure()
    if sub.empty:
        return fig

    fig.add_trace(
        go.Bar(
            x=sub["Indicador"],
            y=sub["Original (Observado)"],
            name="Observado (Planilha Original)",
            marker_color=PALETTE["primary"],
        )
    )
    fig.add_trace(
        go.Bar(
            x=sub["Indicador"],
            y=sub["Simulado (Hipotético)"],
            name="Simulado (Em Memória)",
            marker_color=PALETTE["simulated"],
        )
    )
    title_unit = "Indicadores Monetários (R$)" if unit_filter == "R$" else "Indicadores de Margem e Retorno (%)"
    apply_corporate_layout(
        fig,
        f"Impacto da Simulação — {title_unit}",
        subtitle="Verde = Dado Real Observado • Azul = Resultado Simulado sob Premissas do Usuário",
        y_title=f"Valor ({unit_filter})",
        height=370,
    )
    fig.update_layout(barmode="group")
    fig.update_yaxes(**_axis_format_for_unit(unit_filter))
    return fig


def chart_goals_attainment(goals_df: pd.DataFrame) -> go.Figure:
    """Gráfico horizontal de percentual de atingimento das metas configuradas pelo usuário."""
    defined = goals_df.dropna(subset=["Atingimento (%)"]).copy()
    fig = go.Figure()
    if defined.empty:
        return fig

    colors = [
        PALETTE["positive"] if fav is True else (PALETTE["warning"] if (att >= 90.0) else PALETTE["negative"])
        for fav, att in zip(defined["Favorável"], defined["Atingimento (%)"])
    ]
    fig.add_trace(
        go.Bar(
            y=defined["Indicador"],
            x=defined["Atingimento (%)"],
            orientation="h",
            marker_color=colors,
            text=defined["Atingimento (Fmt)"],
            textposition="outside",
            name="Atingimento (%)",
        )
    )
    fig.add_vline(
        x=100.0,
        line_dash="dash",
        line_color=PALETTE["target"],
        line_width=2,
        annotation_text="100% da Meta",
        annotation_position="top right",
    )
    apply_corporate_layout(
        fig,
        "Grau de Atingimento das Metas Configuradas (%)",
        subtitle="100% representa cumprimento exato do piso (ou limite de teto) definido pelo usuário",
        x_title="Atingimento (%)",
        height=max(280, 58 * len(defined) + 110),
    )
    fig.update_layout(hovermode="closest", showlegend=False)
    fig.update_xaxes(ticksuffix="%")
    return fig


def chart_correlation_heatmap(corr_df: pd.DataFrame) -> go.Figure:
    """Mapa de calor da matriz de correlação com valores anotados."""
    z = corr_df.to_numpy(dtype=float)
    text = [[f"{val:.2f}".replace(".", ",") if not np.isnan(val) else "" for val in row] for row in z]
    fig = go.Figure(
        go.Heatmap(
            z=z,
            x=corr_df.columns.tolist(),
            y=corr_df.index.tolist(),
            zmin=-1.0,
            zmax=1.0,
            colorscale=[
                [0.0, "#B91C1C"],
                [0.5, "#F8FAFC"],
                [1.0, "#0B5D3B"],
            ],
            text=text,
            texttemplate="%{text}",
            textfont=dict(size=11),
            colorbar=dict(title="Corr (r)"),
        )
    )
    apply_corporate_layout(
        fig,
        "Matriz de Correlação entre Indicadores Financeiros",
        subtitle="Correlação mede associação linear/monotônica entre cenários — não implica causalidade",
        height=460,
    )
    fig.update_layout(hovermode="closest")
    return fig


def chart_scatter_with_trend(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    x_label: str,
    y_label: str,
    x_unit: str = "",
    y_unit: str = "",
    active_scenario: str | None = None,
) -> go.Figure:
    """Diagrama de dispersão bivariado com reta de tendência linear OLS e destaque do cenário ativo."""
    sub = df[["Cenário", x_col, y_col]].dropna().copy() if "Cenário" in df.columns else df[[x_col, y_col]].dropna().copy()
    fig = go.Figure()
    if sub.empty:
        return fig

    fig.add_trace(
        go.Scatter(
            x=sub[x_col],
            y=sub[y_col],
            mode="markers",
            name="Cenários",
            text=sub["Cenário"] if "Cenário" in sub.columns else None,
            marker=dict(color="rgba(11, 93, 59, 0.45)", size=7, line=dict(width=0.5, color="#0B5D3B")),
        )
    )

    if len(sub) >= 3 and sub[x_col].std() > 1e-12:
        slope, intercept = np.polyfit(sub[x_col].to_numpy(dtype=float), sub[y_col].to_numpy(dtype=float), 1)
        xs = np.linspace(float(sub[x_col].min()), float(sub[x_col].max()), 60)
        ys = slope * xs + intercept
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                name="Tendência Linear (OLS)",
                line=dict(color="#1E293B", width=2, dash="dash"),
            )
        )

    if active_scenario and "Cenário" in sub.columns:
        act = sub[sub["Cenário"] == active_scenario]
        if not act.empty:
            fig.add_trace(
                go.Scatter(
                    x=act[x_col],
                    y=act[y_col],
                    mode="markers",
                    name=f"Destaque: {active_scenario}",
                    marker=dict(color="#B45309", size=12, symbol="diamond", line=dict(width=1.5, color="#FFFFFF")),
                )
            )

    apply_corporate_layout(
        fig,
        f"Dispersão: {y_label} vs. {x_label}",
        subtitle=f"N = {len(sub)} observações válidas",
        x_title=f"{x_label} ({x_unit})" if x_unit else x_label,
        y_title=f"{y_label} ({y_unit})" if y_unit else y_label,
        height=390,
    )
    fig.update_layout(hovermode="closest")
    if x_unit:
        fig.update_xaxes(**_axis_format_for_unit(x_unit))
    if y_unit:
        fig.update_yaxes(**_axis_format_for_unit(y_unit))
    return fig


def chart_regression_diagnostics(predictions_df: pd.DataFrame, target_label: str) -> tuple[go.Figure, go.Figure]:
    """Gera gráficos diagnósticos do modelo OLS: (1) Observado vs Predito e (2) Resíduos vs Predito."""
    fig1 = go.Figure()
    fig2 = go.Figure()
    if predictions_df.empty:
        return fig1, fig2

    part_colors = {
        "Treinamento": "rgba(11, 93, 59, 0.55)",
        "Teste (Cenários Isolados)": "rgba(29, 78, 216, 0.72)",
    }

    for part, grp in predictions_df.groupby("Partição"):
        c = part_colors.get(str(part), PALETTE["primary"])
        fig1.add_trace(
            go.Scatter(
                x=grp["Observado"],
                y=grp["Predito"],
                mode="markers",
                name=str(part),
                text=grp["Cenário"],
                marker=dict(color=c, size=7),
            )
        )
        fig2.add_trace(
            go.Scatter(
                x=grp["Predito"],
                y=grp["Resíduo"],
                mode="markers",
                name=str(part),
                text=grp["Cenário"],
                marker=dict(color=c, size=7),
            )
        )

    min_v = float(min(predictions_df["Observado"].min(), predictions_df["Predito"].min()))
    max_v = float(max(predictions_df["Observado"].max(), predictions_df["Predito"].max()))
    fig1.add_trace(
        go.Scatter(
            x=[min_v, max_v],
            y=[min_v, max_v],
            mode="lines",
            name="Linha Ideal (y = x)",
            line=dict(color="#334155", width=1.8, dash="dash"),
        )
    )
    fig2.add_hline(y=0.0, line_dash="dash", line_color="#334155", line_width=1.8)

    apply_corporate_layout(
        fig1,
        f"Valores Observados vs. Preditos — {target_label}",
        subtitle="Validação fora da amostra com cenários isolados no conjunto de Teste",
        x_title="Valor Observado",
        y_title="Valor Predito (OLS)",
        height=360,
    )
    fig1.update_layout(hovermode="closest")

    apply_corporate_layout(
        fig2,
        "Diagnóstico de Resíduos vs. Valores Preditos",
        subtitle="Dispersão aleatória em torno de zero indica ausência de viés sistemático linear",
        x_title="Valor Predito (OLS)",
        y_title="Resíduo (Observado - Predito)",
        height=360,
    )
    fig2.update_layout(hovermode="closest")
    return fig1, fig2

