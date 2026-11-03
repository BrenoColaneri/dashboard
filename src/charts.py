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


chart_cash_flow_profit_vs_cash = chart_dfc_profit_vs_cash


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



# =============================================================================
# MÓDULO 1 — GRÁFICOS DE ÍNDICES DA DFC
# =============================================================================

def chart_dfc_fco_ebitda(df_scen: pd.DataFrame) -> go.Figure:
    """Gráfico comparativo da evolução do FCO e EBITDA por período com taxa de conversão."""
    df = df_scen.sort_values("Ano").copy()
    x_labels = df["Período"] if "Período" in df.columns else df["Ano"].map(lambda a: f"Ano {a}")

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=x_labels,
            y=df["calc_ebitda_calculado"],
            name="EBITDA",
            marker_color="#94A3B8",
            hovertemplate="%{x}<br>EBITDA: R$ %{y:,.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=x_labels,
            y=df["calc_fco"],
            name="FCO (Caixa Operacional)",
            marker_color=PALETTE["primary"],
            hovertemplate="%{x}<br>FCO: R$ %{y:,.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x_labels,
            y=df["calc_fco_ebitda"],
            name="FCO / EBITDA (%)",
            mode="lines+markers",
            yaxis="y2",
            line=dict(color="#B45309", width=2.5),
            marker=dict(size=7, symbol="diamond"),
            hovertemplate="%{x}<br>FCO/EBITDA: %{y:.1f}%<extra></extra>",
        )
    )

    fig.update_layout(
        yaxis2=dict(
            title="FCO / EBITDA (%)",
            overlaying="y",
            side="right",
            ticksuffix="%",
            showgrid=False,
            tickfont=dict(size=11, color="#B45309"),
            automargin=True,
        ),
        barmode="group",
    )
    return apply_corporate_layout(
        fig,
        "Evolução do FCO vs. EBITDA",
        subtitle="Conversão do resultado operacional potencial em disponibilidade financeira",
        y_title="Valores em R$",
        height=380,
    )


def chart_dfc_conversion(df_scen: pd.DataFrame) -> go.Figure:
    """Comparação entre Receita Faturada e Recebimentos de Clientes com % de conversão."""
    df = df_scen.sort_values("Ano").copy()
    x_labels = df["Período"] if "Período" in df.columns else df["Ano"].map(lambda a: f"Ano {a}")

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=x_labels,
            y=df["calc_receita"],
            name="Receita Operacional (DRE)",
            marker_color="#CBD5E1",
            hovertemplate="%{x}<br>Receita: R$ %{y:,.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=x_labels,
            y=df["calc_entradas_operacionais"],
            name="Recebimentos Efetivos (DFC)",
            marker_color=PALETTE["primary"],
            hovertemplate="%{x}<br>Recebimentos: R$ %{y:,.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x_labels,
            y=df["calc_taxa_conversao_receita"],
            name="Taxa de Conversão (%)",
            mode="lines+markers",
            yaxis="y2",
            line=dict(color="#15803D", width=2.5, dash="dash"),
            marker=dict(size=7),
            hovertemplate="%{x}<br>Conversão: %{y:.1f}%<extra></extra>",
        )
    )

    fig.update_layout(
        yaxis2=dict(
            title="Conversão (%)",
            overlaying="y",
            side="right",
            ticksuffix="%",
            showgrid=False,
            tickfont=dict(size=11, color="#15803D"),
            automargin=True,
        ),
        barmode="group",
    )
    return apply_corporate_layout(
        fig,
        "Conversão da Receita em Caixa",
        subtitle="Comparativo entre faturamento por competência e recebimentos liquidados",
        y_title="Valores em R$",
        height=380,
    )


def chart_dfc_waterfall_fco(row: pd.Series, period_desc: str) -> go.Figure:
    """Waterfall demonstrando a ponte do EBITDA até o FCO."""
    ebitda = float(row.get("calc_ebitda_calculado", 0.0))
    ir_csll = -abs(float(row.get("FLU - Imposto de Renda e Contribuição Social", 0.0)))
    fco = float(row.get("calc_fco", 0.0))
    # Capital de Giro / Outros ajustes operacionais na ponte do EBITDA ao FCO
    cg_outros = fco - (ebitda + ir_csll)

    labels = ["EBITDA", "IR/CSLL Pagos", "Capital Giro / Outros", "FCO"]
    values = [ebitda, ir_csll, cg_outros, fco]
    measures = ["relative", "relative", "relative", "total"]

    fig = go.Figure(
        go.Waterfall(
            name="Ponte EBITDA -> FCO",
            orientation="v",
            measure=measures,
            x=labels,
            textposition="outside",
            text=[f"R$ {abs(v)/1e6:,.1f} mi" if abs(v) >= 1e6 else f"R$ {v:,.0f}" for v in values],
            y=values,
            connector=dict(line=dict(color="#CBD5E1")),
            increasing=dict(marker=dict(color=PALETTE["positive"])),
            decreasing=dict(marker=dict(color=PALETTE["negative"])),
            totals=dict(marker=dict(color=PALETTE["primary"])),
        )
    )
    return apply_corporate_layout(
        fig,
        f"Ponte de Geração de Caixa Operacional — {period_desc}",
        subtitle="Conciliação do resultado operacional bruto (EBITDA) até o FCO",
        y_title="R$",
        height=370,
    )


def chart_dfc_waterfall_free_cash(row: pd.Series, period_desc: str) -> go.Figure:
    """Waterfall do FCO até a geração líquida de caixa após juros e dividendos."""
    fco = float(row.get("calc_fco", 0.0))
    inv = -abs(float(row.get("FLU - Investimentos", 0.0)))
    fcl = fco + inv
    juros_liq = -abs(float(row.get("calc_juros_liquidos", 0.0)))
    div = -abs(float(row.get("FLU - Distribuição para Acionista", 0.0)))
    sobra = fcl + juros_liq + div

    labels = ["FCO", "Capex / Invest.", "FCL (Caixa Livre)", "Juros Líquidos", "Dividendos", "Geração Líquida"]
    values = [fco, inv, fcl, juros_liq, div, sobra]
    measures = ["relative", "relative", "total", "relative", "relative", "total"]

    fig = go.Figure(
        go.Waterfall(
            name="Ponte do FCO à Sobra de Caixa",
            orientation="v",
            measure=measures,
            x=labels,
            textposition="outside",
            text=[f"R$ {abs(v)/1e6:,.1f} mi" if abs(v) >= 1e6 else f"R$ {v:,.0f}" for v in values],
            y=values,
            connector=dict(line=dict(color="#CBD5E1")),
            increasing=dict(marker=dict(color=PALETTE["positive"])),
            decreasing=dict(marker=dict(color=PALETTE["negative"])),
            totals=dict(marker=dict(color=PALETTE["primary_dark"])),
        )
    )
    return apply_corporate_layout(
        fig,
        f"Ponte de Destinação do Caixa — {period_desc}",
        subtitle="FCO -> Capex -> FCL -> Juros Líquidos -> Dividendos",
        y_title="R$",
        height=370,
    )


def chart_dfc_investments_efficiency(df_scen: pd.DataFrame) -> go.Figure:
    """Gráfico de Capex / Receita e Capex / D&A ao longo dos períodos."""
    df = df_scen.sort_values("Ano").copy()
    x_labels = df["Período"] if "Período" in df.columns else df["Ano"].map(lambda a: f"Ano {a}")

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=x_labels,
            y=df["calc_capex_receita"],
            name="Capex / Receita (%)",
            marker_color="#0F766E",
            hovertemplate="%{x}<br>Capex/Receita: %{y:.2f}%<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x_labels,
            y=df["calc_capex_da"],
            name="Capex / D&A (x)",
            mode="lines+markers",
            yaxis="y2",
            line=dict(color="#B45309", width=2.5),
            marker=dict(size=7, symbol="circle"),
            hovertemplate="%{x}<br>Capex/D&A: %{y:.2f}x<extra></extra>",
        )
    )
    fig.add_hline(y=1.0, line_dash="dash", line_color="#64748B", line_width=1.5, yref="y2")

    fig.update_layout(
        yaxis=dict(ticksuffix="%", automargin=True),
        yaxis2=dict(
            title="Capex / D&A (múltiplo)",
            overlaying="y",
            side="right",
            ticksuffix="x",
            showgrid=False,
            tickfont=dict(size=11, color="#B45309"),
            automargin=True,
        ),
    )
    return apply_corporate_layout(
        fig,
        "Eficiência e Intensidade dos Investimentos",
        subtitle="Capex relativo à receita operacional e reposição do desgaste de ativos (linha tracejada em 1,0x)",
        y_title="Capex / Receita (%)",
        height=370,
    )


def chart_dfc_payment_capacity(df_scen: pd.DataFrame) -> go.Figure:
    """Gráfico de Cobertura de Juros em Caixa e relação FCO / Dívida Bruta."""
    df = df_scen.sort_values("Ano").copy()
    x_labels = df["Período"] if "Período" in df.columns else df["Ano"].map(lambda a: f"Ano {a}")

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=x_labels,
            y=df["calc_cobertura_juros_caixa"],
            name="Cobertura de Juros em Caixa (x)",
            marker_color=PALETTE["primary"],
            hovertemplate="%{x}<br>Cobertura Juros: %{y:.2f}x<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x_labels,
            y=df["calc_fco_divida_bruta"],
            name="FCO / Dívida Bruta (%)",
            mode="lines+markers",
            yaxis="y2",
            line=dict(color="#4338CA", width=2.5),
            marker=dict(size=7),
            hovertemplate="%{x}<br>FCO/Dívida: %{y:.1f}%<extra></extra>",
        )
    )
    fig.add_hline(y=1.0, line_dash="dash", line_color="#EF4444", line_width=1.5)

    fig.update_layout(
        yaxis=dict(ticksuffix="x", automargin=True),
        yaxis2=dict(
            title="FCO / Dívida Bruta (%)",
            overlaying="y",
            side="right",
            ticksuffix="%",
            showgrid=False,
            tickfont=dict(size=11, color="#4338CA"),
            automargin=True,
        ),
    )
    return apply_corporate_layout(
        fig,
        "Capacidade de Pagamento de Credores em Caixa",
        subtitle="Cobertura de encargos de juros e amortização potencial da dívida bruta pelo FCO",
        y_title="Cobertura de Juros (múltiplos)",
        height=370,
    )


def chart_dfc_dividend_sustainability(df_scen: pd.DataFrame) -> go.Figure:
    """Comparação entre Fluxo de Caixa Livre (FCL), Dividendos Pagos e Cobertura."""
    df = df_scen.sort_values("Ano").copy()
    x_labels = df["Período"] if "Período" in df.columns else df["Ano"].map(lambda a: f"Ano {a}")

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=x_labels,
            y=df["calc_fcl"],
            name="Fluxo de Caixa Livre (FCL)",
            marker_color=PALETTE["primary_light"],
            hovertemplate="%{x}<br>FCL: R$ %{y:,.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=x_labels,
            y=df["calc_dva_dist_dividendos"],
            name="Dividendos Pagos",
            marker_color="#94A3B8",
            hovertemplate="%{x}<br>Dividendos: R$ %{y:,.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x_labels,
            y=df["calc_cobertura_dividendos"],
            name="Cobertura de Dividendos (x)",
            mode="lines+markers",
            yaxis="y2",
            line=dict(color="#B45309", width=2.5),
            marker=dict(size=7, symbol="diamond"),
            hovertemplate="%{x}<br>Cobertura Div.: %{y:.2f}x<extra></extra>",
        )
    )
    fig.add_hline(y=1.0, line_dash="dash", line_color="#64748B", line_width=1.5, yref="y2")

    fig.update_layout(
        yaxis2=dict(
            title="Cobertura de Dividendos (x)",
            overlaying="y",
            side="right",
            ticksuffix="x",
            showgrid=False,
            tickfont=dict(size=11, color="#B45309"),
            automargin=True,
        ),
        barmode="group",
    )
    return apply_corporate_layout(
        fig,
        "Sustentabilidade dos Dividendos pelo FCL",
        subtitle="Verificação se a distribuição aos sócios cabe organicamente no caixa livre gerado",
        y_title="Valores em R$",
        height=370,
    )


# =============================================================================
# MÓDULO 2 — GRÁFICOS DE CAPITAL DE GIRO E PRAZOS MÉDIOS
# =============================================================================

def chart_working_capital_ccl(df_scen: pd.DataFrame) -> go.Figure:
    """Evolução temporal do Capital Circulante Líquido (CCL) com destaque de folga."""
    df = df_scen.sort_values("Ano").copy()
    valid = df.dropna(subset=["calc_ccl"])
    x_labels = valid["Período"] if "Período" in valid.columns else valid["Ano"].map(lambda a: f"Ano {a}")

    colors = [PALETTE["positive"] if v >= 0 else PALETTE["negative"] for v in valid["calc_ccl"]]
    fig = go.Figure(
        go.Bar(
            x=x_labels,
            y=valid["calc_ccl"],
            marker_color=colors,
            text=[f"R$ {v/1e6:,.1f} mi" if abs(v) >= 1e6 else f"R$ {v:,.0f}" for v in valid["calc_ccl"]],
            textposition="outside",
            hovertemplate="%{x}<br>CCL: R$ %{y:,.2f}<extra></extra>",
        )
    )
    fig.add_hline(y=0.0, line_color="#334155", line_width=1.5)
    return apply_corporate_layout(
        fig,
        "Evolução do Capital Circulante Líquido (CCL)",
        subtitle="Ativo Circulante menos Passivo Circulante Ajustado (folga operacional de curto prazo)",
        y_title="R$",
        height=370,
    )


def chart_working_capital_pmr_pmp(df_scen: pd.DataFrame) -> go.Figure:
    """Comparativo entre PMR e PMP (em dias comerciais)."""
    df = df_scen.sort_values("Ano").copy()
    valid = df.dropna(subset=["calc_pmr", "calc_pmp"])
    x_labels = valid["Período"] if "Período" in valid.columns else valid["Ano"].map(lambda a: f"Ano {a}")

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=x_labels,
            y=valid["calc_pmr"],
            name="PMR (Prazo Médio de Recebimento)",
            marker_color="#0F766E",
            hovertemplate="%{x}<br>PMR: %{y:.1f} dias<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=x_labels,
            y=valid["calc_pmp"],
            name="PMP (Prazo Médio de Pagamento)",
            marker_color="#B45309",
            hovertemplate="%{x}<br>PMP: %{y:.1f} dias<extra></extra>",
        )
    )
    fig.update_layout(barmode="group", yaxis=dict(ticksuffix=" dias", automargin=True))
    return apply_corporate_layout(
        fig,
        "PMR x PMP — Prazos Médios Operacionais",
        subtitle="Tempo para receber de clientes versus tempo para pagar fornecedores (ano comercial = 360 dias)",
        y_title="Dias",
        height=370,
    )


def chart_working_capital_cycle(df_scen: pd.DataFrame) -> go.Figure:
    """Ciclo Financeiro Simplificado (PMR - PMP) com coloração semântica de financiamento."""
    df = df_scen.sort_values("Ano").copy()
    valid = df.dropna(subset=["calc_ciclo_financeiro"])
    x_labels = valid["Período"] if "Período" in valid.columns else valid["Ano"].map(lambda a: f"Ano {a}")

    # Ciclo > 0: empresa financia operação (laranja); Ciclo <= 0: fornecedores financiam (verde)
    colors = [PALETTE["warning"] if v > 0 else PALETTE["positive"] for v in valid["calc_ciclo_financeiro"]]

    fig = go.Figure(
        go.Bar(
            x=x_labels,
            y=valid["calc_ciclo_financeiro"],
            marker_color=colors,
            text=[f"{v:.1f} dias" for v in valid["calc_ciclo_financeiro"]],
            textposition="outside",
            hovertemplate="%{x}<br>Ciclo: %{y:.1f} dias<extra></extra>",
        )
    )
    fig.add_hline(y=0.0, line_color="#334155", line_width=1.5)
    fig.update_layout(yaxis=dict(ticksuffix=" dias", automargin=True))
    return apply_corporate_layout(
        fig,
        "Ciclo Financeiro Simplificado (PMR − PMP)",
        subtitle="Verde: fornecedores financiam a operação (ciclo negativo); Âmbar: empresa financia o intervalo",
        y_title="Dias Financiados",
        height=370,
    )


def chart_working_capital_need_vs_ccl(df_scen: pd.DataFrame) -> go.Figure:
    """Comparação entre Necessidade Estimada de Capital de Giro e CCL disponível."""
    df = df_scen.sort_values("Ano").copy()
    valid = df.dropna(subset=["calc_ccl", "calc_necessidade_capital_giro"])
    x_labels = valid["Período"] if "Período" in valid.columns else valid["Ano"].map(lambda a: f"Ano {a}")

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=x_labels,
            y=valid["calc_ccl"],
            name="CCL Disponível",
            marker_color=PALETTE["primary"],
            hovertemplate="%{x}<br>CCL: R$ %{y:,.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=x_labels,
            y=valid["calc_necessidade_capital_giro"],
            name="Necessidade Estimada (NCG)",
            marker_color="#94A3B8",
            hovertemplate="%{x}<br>Necessidade CG: R$ %{y:,.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x_labels,
            y=valid["calc_folga_ccl"],
            name="Folga Líquida (CCL − NCG)",
            mode="lines+markers",
            line=dict(color=PALETTE["positive"], width=2.5),
            marker=dict(size=7),
            hovertemplate="%{x}<br>Folga: R$ %{y:,.2f}<extra></extra>",
        )
    )
    fig.update_layout(barmode="group")
    return apply_corporate_layout(
        fig,
        "Necessidade Estimada de Capital de Giro vs. CCL",
        subtitle="Avaliação da cobertura dos recursos circulantes sobre a necessidade estimada do ciclo",
        y_title="R$",
        height=380,
    )


# =============================================================================
# MÓDULO 3 — GRÁFICOS DE FLUXO DE CAIXA
# =============================================================================

def chart_cash_flow_evolution(df_scen: pd.DataFrame) -> go.Figure:
    """Evolução temporal do Saldo Inicial e Saldo Final de Caixa."""
    df = df_scen.sort_values("Ano").copy()
    x_labels = df["Período"] if "Período" in df.columns else df["Ano"].map(lambda a: f"Ano {a}")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x_labels,
            y=df["calc_saldo_inicial_caixa"],
            name="Saldo Inicial de Caixa",
            mode="lines+markers",
            line=dict(color="#64748B", width=2, dash="dash"),
            marker=dict(size=6),
            hovertemplate="%{x}<br>Saldo Inicial: R$ %{y:,.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x_labels,
            y=df["calc_saldo_final_caixa"],
            name="Saldo Final de Caixa",
            mode="lines+markers",
            line=dict(color=PALETTE["primary"], width=3),
            marker=dict(size=8),
            hovertemplate="%{x}<br>Saldo Final: R$ %{y:,.2f}<extra></extra>",
        )
    )
    return apply_corporate_layout(
        fig,
        "Evolução do Saldo de Caixa",
        subtitle="Trajetória das disponibilidades ao final de cada exercício financeiro",
        y_title="R$",
        height=360,
    )


def chart_cash_flow_entries_exits(df_scen: pd.DataFrame) -> go.Figure:
    """Comparativo entre Entradas Operacionais e Saídas Operacionais."""
    df = df_scen.sort_values("Ano").copy()
    x_labels = df["Período"] if "Período" in df.columns else df["Ano"].map(lambda a: f"Ano {a}")

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=x_labels,
            y=df["calc_entradas_operacionais"],
            name="Entradas Operacionais",
            marker_color=PALETTE["positive"],
            hovertemplate="%{x}<br>Entradas: R$ %{y:,.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=x_labels,
            y=df["calc_saidas_operacionais"],
            name="Saídas Operacionais",
            marker_color=PALETTE["negative"],
            hovertemplate="%{x}<br>Saídas: R$ %{y:,.2f}<extra></extra>",
        )
    )
    fig.update_layout(barmode="group")
    return apply_corporate_layout(
        fig,
        "Entradas vs. Saídas Operacionais",
        subtitle="Movimentação financeira bruta de recursos da operação",
        y_title="R$",
        height=360,
    )


def chart_cash_flow_composition(df_scen: pd.DataFrame) -> go.Figure:
    """Composição das atividades operacionais, de investimento e financiamento."""
    df = df_scen.sort_values("Ano").copy()
    x_labels = df["Período"] if "Período" in df.columns else df["Ano"].map(lambda a: f"Ano {a}")

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=x_labels,
            y=df["calc_fco"],
            name="Atividades Operacionais (FCO)",
            marker_color=PALETTE["primary"],
            hovertemplate="%{x}<br>FCO: R$ %{y:,.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=x_labels,
            y=df["calc_fluxo_investimentos"],
            name="Atividades de Investimento",
            marker_color="#0F766E",
            hovertemplate="%{x}<br>Investimentos: R$ %{y:,.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=x_labels,
            y=df["calc_fluxo_financiamento"],
            name="Atividades de Financiamento",
            marker_color="#475569",
            hovertemplate="%{x}<br>Financiamento: R$ %{y:,.2f}<extra></extra>",
        )
    )
    fig.update_layout(barmode="relative")
    return apply_corporate_layout(
        fig,
        "Composição dos Fluxos de Caixa por Atividade",
        subtitle="Contribuição líquida das atividades operacionais, de investimentos e financiamento",
        y_title="R$",
        height=380,
    )


def chart_cash_flow_waterfall(row: pd.Series, period_desc: str) -> go.Figure:
    """Waterfall do saldo inicial de caixa até o saldo final."""
    s_ini = float(row.get("calc_saldo_inicial_caixa", 0.0))
    fco = float(row.get("calc_fco", 0.0))
    inv = float(row.get("calc_fluxo_investimentos", 0.0))
    fin = float(row.get("calc_fluxo_financiamento", 0.0))
    s_fim = float(row.get("calc_saldo_final_caixa", 0.0))

    labels = ["Saldo Inicial", "FCO (Operação)", "Investimentos", "Financiamento", "Saldo Final"]
    values = [s_ini, fco, inv, fin, s_fim]
    measures = ["relative", "relative", "relative", "relative", "total"]

    fig = go.Figure(
        go.Waterfall(
            name="Formação do Saldo de Caixa",
            orientation="v",
            measure=measures,
            x=labels,
            textposition="outside",
            text=[f"R$ {abs(v)/1e6:,.1f} mi" if abs(v) >= 1e6 else f"R$ {v:,.0f}" for v in values],
            y=values,
            connector=dict(line=dict(color="#CBD5E1")),
            increasing=dict(marker=dict(color=PALETTE["positive"])),
            decreasing=dict(marker=dict(color=PALETTE["negative"])),
            totals=dict(marker=dict(color=PALETTE["primary"])),
        )
    )
    return apply_corporate_layout(
        fig,
        f"Waterfall de Formação do Saldo de Caixa — {period_desc}",
        subtitle="Transição do saldo inicial ao saldo final conciliado",
        y_title="R$",
        height=370,
    )


# =============================================================================
# MÓDULO 4 — GRÁFICOS DE DEMONSTRAÇÃO DO VALOR ADICIONADO (DVA)
# =============================================================================

def chart_dva_waterfall(row: pd.Series, period_desc: str) -> go.Figure:
    """Waterfall da formação da riqueza gerada na DVA (Itens 1 a 7)."""
    rec = float(row.get("calc_dva_receitas_totais", 0.0))
    ins = -abs(float(row.get("calc_dva_insumos_totais", 0.0)))
    va_bruto = rec + ins
    ret = -abs(float(row.get("calc_dva_retencoes", 0.0)))
    va_liq = va_bruto + ret
    transf = float(row.get("calc_dva_transferencias_totais", 0.0))
    va_total = va_liq + transf

    labels = [
        "1. Receitas",
        "2. (-) Insumos Terceiros",
        "3. VA Bruto",
        "4. (-) Retenções (D&A)",
        "5. VA Líquido Produzido",
        "6. (+) Transferências",
        "7. VA Total a Distribuir",
    ]
    values = [rec, ins, va_bruto, ret, va_liq, transf, va_total]
    measures = ["relative", "relative", "total", "relative", "total", "relative", "total"]

    fig = go.Figure(
        go.Waterfall(
            name="Geração de Riqueza DVA",
            orientation="v",
            measure=measures,
            x=labels,
            textposition="outside",
            text=[f"R$ {abs(v)/1e6:,.1f} mi" if abs(v) >= 1e6 else f"R$ {v:,.0f}" for v in values],
            y=values,
            connector=dict(line=dict(color="#CBD5E1")),
            increasing=dict(marker=dict(color=PALETTE["positive"])),
            decreasing=dict(marker=dict(color=PALETTE["negative"])),
            totals=dict(marker=dict(color=PALETTE["primary"])),
        )
    )
    return apply_corporate_layout(
        fig,
        f"Formação do Valor Adicionado (DVA) — {period_desc}",
        subtitle="Passo a passo da riqueza gerada pela entidade até o montante total a distribuir",
        y_title="R$",
        height=380,
    )


def chart_dva_distribution_pie(row: pd.Series, period_desc: str) -> go.Figure:
    """Gráfico de rosca corporativo da distribuição da riqueza entre os 4 agentes econômicos."""
    pessoal = float(row.get("calc_dva_dist_pessoal", 0.0))
    governo = float(row.get("calc_dva_dist_governo", 0.0))
    terceiros = float(row.get("calc_dva_dist_terceiros", 0.0))
    proprios = float(row.get("calc_dva_dist_proprios", 0.0))

    labels = ["Pessoal (Empregados)", "Governo (Tributos)", "Capitais de Terceiros (Juros)", "Capitais Próprios (Sócios)"]
    values = [max(0.0, pessoal), max(0.0, governo), max(0.0, terceiros), max(0.0, proprios)]
    colors = ["#0F766E", "#15803D", "#B45309", "#0B5D3B"]

    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.48,
            marker=dict(colors=colors, line=dict(color="#FFFFFF", width=2)),
            textinfo="percent+label",
            hovertemplate="<b>%{label}</b><br>R$ %{value:,.2f}<br>Fatia: %{percent}<extra></extra>",
        )
    )
    fig.update_layout(
        title=dict(
            text=f"<b>Distribuição da Riqueza (DVA) — {period_desc}</b><br><span style='font-size:12px;color:#64748B;'>Repartição do Valor Adicionado Total entre os agentes econômicos</span>",
            x=0.0,
            xanchor="left",
            font=dict(size=15, color=PALETTE["neutral_dark"]),
        ),
        font=dict(family="Inter, Segoe UI, Roboto, sans-serif", size=12),
        paper_bgcolor="#FFFFFF",
        height=380,
        margin=dict(l=10, r=10, t=55, b=25),
        legend=dict(orientation="h", yanchor="top", y=-0.12, xanchor="center", x=0.5, font=dict(size=10.5)),
    )
    return fig


def chart_dva_distribution_stacked_100(df_scen: pd.DataFrame) -> go.Figure:
    """Barras empilhadas 100% da distribuição da riqueza ao longo dos períodos."""
    df = df_scen.sort_values("Ano").copy()
    x_labels = df["Período"] if "Período" in df.columns else df["Ano"].map(lambda a: f"Ano {a}")

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=x_labels,
            y=df["calc_dva_part_pessoal"],
            name="Pessoal (%)",
            marker_color="#0F766E",
            hovertemplate="%{x}<br>Pessoal: %{y:.1f}%<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=x_labels,
            y=df["calc_dva_part_governo"],
            name="Governo (%)",
            marker_color="#15803D",
            hovertemplate="%{x}<br>Governo: %{y:.1f}%<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=x_labels,
            y=df["calc_dva_part_terceiros"],
            name="Capitais Terceiros (%)",
            marker_color="#B45309",
            hovertemplate="%{x}<br>Terceiros: %{y:.1f}%<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=x_labels,
            y=df["calc_dva_part_proprios"],
            name="Capitais Próprios (%)",
            marker_color=PALETTE["primary"],
            hovertemplate="%{x}<br>Sócios: %{y:.1f}%<extra></extra>",
        )
    )

    fig.update_layout(barmode="stack", yaxis=dict(ticksuffix="%", range=[0, 100], automargin=True))
    return apply_corporate_layout(
        fig,
        "Participação dos Agentes Econômicos (100% Empilhado)",
        subtitle="Evolução percentual da fatia destinada a pessoal, governo, terceiros e sócios",
        y_title="Participação no VA Total (%)",
        height=380,
    )


def chart_dva_evolution(df_scen: pd.DataFrame) -> go.Figure:
    """Evolução temporal de VA Bruto, VA Líquido Produzido e VA Total a Distribuir."""
    df = df_scen.sort_values("Ano").copy()
    x_labels = df["Período"] if "Período" in df.columns else df["Ano"].map(lambda a: f"Ano {a}")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x_labels,
            y=df["calc_dva_va_bruto"],
            name="VA Bruto",
            mode="lines+markers",
            line=dict(color="#64748B", width=2),
            marker=dict(size=6),
            hovertemplate="%{x}<br>VA Bruto: R$ %{y:,.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x_labels,
            y=df["calc_dva_va_liquido"],
            name="VA Líquido Produzido",
            mode="lines+markers",
            line=dict(color="#0F766E", width=2.5),
            marker=dict(size=7),
            hovertemplate="%{x}<br>VA Líquido: R$ %{y:,.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x_labels,
            y=df["calc_dva_va_total"],
            name="VA Total a Distribuir",
            mode="lines+markers",
            line=dict(color=PALETTE["primary"], width=3.5),
            marker=dict(size=8, symbol="diamond"),
            hovertemplate="%{x}<br>VA Total: R$ %{y:,.2f}<extra></extra>",
        )
    )
    return apply_corporate_layout(
        fig,
        "Evolução da Geração de Riqueza (DVA)",
        subtitle="Progressão temporal dos agregados econômicos produzidos e distribuídos",
        y_title="R$",
        height=380,
    )


def chart_dva_wealth_indicators(df_scen: pd.DataFrame) -> go.Figure:
    """Indicadores de Geração de Riqueza, Retenção e Transferências."""
    df = df_scen.sort_values("Ano").copy()
    x_labels = df["Período"] if "Período" in df.columns else df["Ano"].map(lambda a: f"Ano {a}")

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=x_labels,
            y=df["calc_dva_grau_riqueza"],
            name="Grau de Geração de Riqueza (%)",
            marker_color=PALETTE["primary"],
            hovertemplate="%{x}<br>Grau Geração: %{y:.1f}%<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=x_labels,
            y=df["calc_dva_retencao_riqueza"],
            name="Retenção de Riqueza (%)",
            marker_color="#0F766E",
            hovertemplate="%{x}<br>Retenção: %{y:.1f}%<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x_labels,
            y=df["calc_dva_part_transferencias"],
            name="Riqueza em Transferência (%)",
            mode="lines+markers",
            line=dict(color="#B45309", width=2),
            marker=dict(size=6),
            hovertemplate="%{x}<br>Transferências: %{y:.1f}%<extra></extra>",
        )
    )
    fig.update_layout(barmode="group", yaxis=dict(ticksuffix="%", automargin=True))
    return apply_corporate_layout(
        fig,
        "Indicadores Analíticos de Riqueza",
        subtitle="Grau de transformação de receita em valor, taxa de retenção interna e dependência de transferências",
        y_title="Percentual (%)",
        height=370,
    )


def chart_dva_distribution_evolution(df_scen: pd.DataFrame) -> go.Figure:
    """Evolução monetária (em R$) dos 4 grupos de distribuição da riqueza na DVA."""
    df = df_scen.sort_values("Ano").copy()
    x_labels = df["Período"] if "Período" in df.columns else df["Ano"].map(lambda a: f"Ano {a}")

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=x_labels,
            y=df["calc_dva_dist_pessoal"],
            name="Pessoal",
            marker_color="#0F766E",
            hovertemplate="%{x}<br>Pessoal: R$ %{y:,.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=x_labels,
            y=df["calc_dva_dist_governo"],
            name="Governo",
            marker_color="#15803D",
            hovertemplate="%{x}<br>Governo: R$ %{y:,.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=x_labels,
            y=df["calc_dva_dist_terceiros"],
            name="Capitais de Terceiros",
            marker_color="#B45309",
            hovertemplate="%{x}<br>Terceiros: R$ %{y:,.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=x_labels,
            y=df["calc_dva_dist_proprios"],
            name="Capitais Próprios",
            marker_color=PALETTE["primary"],
            hovertemplate="%{x}<br>Sócios: R$ %{y:,.2f}<extra></extra>",
        )
    )
    fig.update_layout(barmode="stack")
    return apply_corporate_layout(
        fig,
        "Evolução da Distribuição da Riqueza (R$)",
        subtitle="Montantes anuais alocados a pessoal, governo, credores e sócios",
        y_title="R$",
        height=380,
    )
