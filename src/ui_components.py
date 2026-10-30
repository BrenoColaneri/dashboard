"""Sistema de Design Corporativo e Componentes Reutilizáveis de Interface (UI).

Identidade visual institucional CTI Global:
- Paleta predominante: Verde-escuro corporativo (`#0B5D3B`), branco (`#FFFFFF`) e cinzas neutros (`#0F172A`, `#475569`, `#E2E8F0`).
- Cores semânticas exclusivas:
  - Verde (`#15803D`): variação favorável / meta atingida / dado reconciliado.
  - Âmbar (`#B45309`): alerta metodológico / atenção / Ano 12 parcial.
  - Vermelho (`#B91C1C`): variação desfavorável / abaixo da meta / erro.
  - Azul (`#1D4ED8`): identificação estrita de valores simulados ou premissas editáveis.
- Responsividade total testada para viewports de 360 px (mobile), 768 px (tablet) e 1366 px+ (desktop).
"""

from __future__ import annotations

import html
from typing import Any

import pandas as pd
import streamlit as st

from src.config import PALETTE, format_period_label
from src.data_processing import ProcessedDataStore


def inject_corporate_css() -> None:
    """Injeta folha de estilos CSS responsiva e discreta para toda a aplicação Streamlit."""
    st.markdown(
        f"""
        <style>
        /* Streamlit Header transparente para não sobrepor o cabeçalho executivo */
        [data-testid="stHeader"] {{
            background: transparent !important;
            z-index: 100 !important;
        }}

        /* Layout geral e tipografia corporativa com espaçamento simétrico */
        .block-container {{
            padding-top: 4.2rem !important;
            padding-bottom: 2.5rem !important;
            max-width: 1440px !important;
        }}

        /* Barra lateral institucional */
        [data-testid="stSidebar"] {{
            background-color: #F8FAFC;
            border-right: 1px solid {PALETTE["border"]};
        }}
        [data-testid="stSidebar"] .block-container {{
            padding-top: 2rem !important;
        }}

        /* Cabeçalho executivo da página com cantos perfeitamente arredondados em todas as pontas */
        .cti-hero {{
            background: linear-gradient(135deg, {PALETTE["primary_dark"]} 0%, {PALETTE["primary"]} 100%);
            color: #FFFFFF;
            border-radius: 14px !important;
            overflow: hidden !important;
            padding: 1.25rem 1.6rem;
            margin-top: 0.35rem;
            margin-bottom: 1.25rem;
            box-shadow: 0 4px 14px rgba(11, 93, 59, 0.12);
            border: 1px solid rgba(255, 255, 255, 0.12);
            box-sizing: border-box !important;
        }}
        .cti-hero-eyebrow {{
            font-size: 0.74rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #A7F3D0;
            font-weight: 700;
            margin-bottom: 0.35rem;
        }}
        .cti-hero-title {{
            font-size: 1.42rem;
            font-weight: 700;
            margin: 0 0 0.25rem 0;
            line-height: 1.25;
            color: #FFFFFF !important;
        }}
        .cti-hero-subtitle {{
            font-size: 0.88rem;
            color: #E2E8F0;
            margin: 0 0 0.7rem 0;
            line-height: 1.45;
        }}
        .cti-pill-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            align-items: center;
        }}
        .cti-context-pill {{
            background: rgba(255, 255, 255, 0.14);
            border: 1px solid rgba(255, 255, 255, 0.24);
            color: #FFFFFF;
            padding: 0.2rem 0.6rem;
            border-radius: 999px;
            font-size: 0.76rem;
            font-weight: 500;
            white-space: nowrap;
        }}

        /* Grid fluido de cartões de KPI (responsivo nativo 360px / 768px / 1366px) */
        .cti-kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(225px, 1fr));
            gap: 0.85rem;
            margin-bottom: 1.1rem;
            width: 100%;
        }}
        .cti-kpi-card {{
            background: {PALETTE["surface"]};
            border: 1px solid {PALETTE["border"]};
            border-top: 3px solid {PALETTE["primary"]};
            border-radius: 10px;
            padding: 0.9rem 1rem;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            min-width: 0;
            overflow-wrap: anywhere;
        }}
        .cti-kpi-card.is-simulated {{
            border-top-color: {PALETTE["simulated"]};
            background: #F8FAFF;
        }}
        .cti-kpi-card.is-warning {{
            border-top-color: {PALETTE["warning"]};
        }}
        .cti-kpi-card.is-negative {{
            border-top-color: {PALETTE["negative"]};
        }}
        .cti-kpi-top {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 0.4rem;
            margin-bottom: 0.4rem;
        }}
        .cti-kpi-label {{
            font-size: 0.80rem;
            font-weight: 600;
            color: {PALETTE["neutral"]};
            line-height: 1.3;
        }}
        .cti-tooltip-icon {{
            display: inline-block;
            cursor: help;
            color: {PALETTE["neutral_light"]};
            font-size: 0.78rem;
            margin-left: 0.22rem;
        }}
        .cti-badge {{
            font-size: 0.68rem;
            font-weight: 600;
            padding: 0.14rem 0.48rem;
            border-radius: 999px;
            white-space: nowrap;
            flex-shrink: 0;
        }}
        .cti-badge.real {{
            background: #ECFDF5;
            color: {PALETTE["primary"]};
            border: 1px solid #A7F3D0;
        }}
        .cti-badge.simulated {{
            background: #EFF6FF;
            color: {PALETTE["simulated"]};
            border: 1px solid #BFDBFE;
        }}
        .cti-badge.positive {{
            background: #F0FDF4;
            color: {PALETTE["positive"]};
            border: 1px solid #BBF7D0;
        }}
        .cti-badge.warning {{
            background: #FFFBEB;
            color: {PALETTE["warning"]};
            border: 1px solid #FDE68A;
        }}
        .cti-badge.negative {{
            background: #FEF2F2;
            color: {PALETTE["negative"]};
            border: 1px solid #FECACA;
        }}
        .cti-badge.neutral {{
            background: #F1F5F9;
            color: {PALETTE["neutral"]};
            border: 1px solid #CBD5E1;
        }}

        .cti-kpi-value {{
            font-size: 1.36rem;
            font-weight: 700;
            color: {PALETTE["neutral_dark"]};
            font-variant-numeric: tabular-nums;
            line-height: 1.2;
            margin-bottom: 0.35rem;
            word-break: break-word;
        }}
        .cti-kpi-delta {{
            font-size: 0.76rem;
            font-weight: 600;
            margin-bottom: 0.22rem;
            line-height: 1.3;
        }}
        .cti-kpi-delta.positive {{ color: {PALETTE["positive"]}; }}
        .cti-kpi-delta.negative {{ color: {PALETTE["negative"]}; }}
        .cti-kpi-delta.warning  {{ color: {PALETTE["warning"]}; }}
        .cti-kpi-delta.simulated {{ color: {PALETTE["simulated"]}; }}
        .cti-kpi-delta.neutral  {{ color: {PALETTE["neutral"]}; }}

        .cti-kpi-sub {{
            font-size: 0.73rem;
            color: #64748B;
            line-height: 1.35;
        }}

        /* Cabeçalhos de seção */
        .cti-section-hdr {{
            border-left: 4px solid {PALETTE["primary"]};
            padding-left: 0.7rem;
            margin: 1.25rem 0 0.65rem 0;
        }}
        .cti-section-hdr h3 {{
            font-size: 1.06rem !important;
            font-weight: 700 !important;
            color: {PALETTE["neutral_dark"]} !important;
            margin: 0 !important;
            padding: 0 !important;
        }}
        .cti-section-hdr p {{
            font-size: 0.82rem;
            color: {PALETTE["neutral"]};
            margin: 0.15rem 0 0 0;
        }}

        /* Caixas de aviso metodológico e governança */
        .cti-callout {{
            border-radius: 8px;
            padding: 0.8rem 1rem;
            margin-bottom: 0.9rem;
            font-size: 0.84rem;
            line-height: 1.48;
            border: 1px solid {PALETTE["border"]};
        }}
        .cti-callout-title {{
            font-weight: 700;
            margin-bottom: 0.2rem;
        }}
        .cti-callout.info {{
            background: #F8FAFC;
            border-left: 4px solid {PALETTE["primary"]};
            color: {PALETTE["neutral_dark"]};
        }}
        .cti-callout.warning {{
            background: #FFFBEB;
            border-left: 4px solid {PALETTE["warning"]};
            color: #78350F;
        }}
        .cti-callout.simulated {{
            background: #EFF6FF;
            border-left: 4px solid {PALETTE["simulated"]};
            color: #1E3A8A;
        }}
        .cti-callout.danger {{
            background: #FEF2F2;
            border-left: 4px solid {PALETTE["negative"]};
            color: #7F1D1D;
        }}
        .cti-callout.success {{
            background: #F0FDF4;
            border-left: 4px solid {PALETTE["positive"]};
            color: #14532D;
        }}

        /* Rodapé institucional de rastreabilidade */
        .cti-footer {{
            margin-top: 2rem;
            padding-top: 0.85rem;
            border-top: 1px solid {PALETTE["border"]};
            font-size: 0.76rem;
            color: #64748B;
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            gap: 0.5rem;
        }}

        /* Prevenção de overflow horizontal e quebra em mobile */
        html, body, [data-testid="stAppViewContainer"], .main, .block-container {{
            overflow-x: hidden !important;
            max-width: 100vw !important;
            box-sizing: border-box !important;
        }}

        /* Container simétrico para o painel de acesso rápido */
        .cti-quick-nav-card {{
            background: #FFFFFF;
            border: 1px solid {PALETTE["border"]};
            border-radius: 12px;
            padding: 1.1rem 1.3rem;
            margin-bottom: 1.25rem;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
        }}
        .cti-quick-nav-card h4 {{
            margin: 0 0 0.85rem 0 !important;
            font-size: 0.98rem !important;
            font-weight: 700 !important;
            color: {PALETTE["neutral_dark"]} !important;
            display: flex;
            align-items: center;
            gap: 0.45rem;
        }}

        /* Tabelas Corporativas HTML Nativas CTI Global — 100% Responsivas e Padronizadas em Verde */
        .cti-table-container {{
            width: 100% !important;
            margin: 0.85rem 0 1.25rem 0 !important;
            border: 1px solid {PALETTE["border"]};
            border-radius: 10px;
            overflow: hidden;
            background: #FFFFFF;
            box-shadow: 0 1px 4px rgba(15, 23, 42, 0.05);
        }}
        .cti-table-scroll {{
            width: 100% !important;
            overflow-x: auto !important;
            -webkit-overflow-scrolling: touch;
        }}
        .cti-table-scroll.has-vertical-scroll {{
            max-height: 540px !important;
            overflow-y: auto !important;
        }}
        .cti-table-scroll::-webkit-scrollbar {{
            width: 7px;
            height: 7px;
        }}
        .cti-table-scroll::-webkit-scrollbar-track {{
            background: #F8FAFC;
        }}
        .cti-table-scroll::-webkit-scrollbar-thumb {{
            background: #CBD5E1;
            border-radius: 4px;
        }}
        .cti-table-scroll::-webkit-scrollbar-thumb:hover {{
            background: {PALETTE["primary"]};
        }}
        .cti-html-table {{
            width: 100% !important;
            table-layout: auto !important;
            border-collapse: separate !important;
            border-spacing: 0 !important;
            font-family: inherit;
            font-size: 0.78rem;
            line-height: 1.35;
        }}
        .cti-html-table.table-narrow {{
            min-width: 100% !important;
        }}
        .cti-html-table.table-medium {{
            min-width: 720px !important;
        }}
        .cti-html-table.table-wide {{
            min-width: 1050px !important;
        }}
        .cti-html-table th {{
            background-color: {PALETTE["primary"]} !important;
            color: #FFFFFF !important;
            font-weight: 600 !important;
            padding: 0.55rem 0.65rem !important;
            border-bottom: 2px solid {PALETTE["primary_dark"]} !important;
            border-right: 1px solid rgba(255, 255, 255, 0.15) !important;
            text-align: right;
            white-space: nowrap !important;
            min-width: 75px;
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        .cti-html-table th.col-left {{
            text-align: left !important;
        }}
        .cti-html-table th.col-center {{
            text-align: center !important;
        }}
        .cti-html-table th.col-right {{
            text-align: right !important;
        }}
        .cti-html-table th:first-child {{
            position: sticky;
            top: 0;
            left: 0;
            z-index: 20;
            background-color: {PALETTE["primary"]} !important;
            box-shadow: 2px 0 5px rgba(0, 0, 0, 0.08);
        }}
        .cti-html-table.first-col-short th:first-child,
        .cti-html-table.first-col-short td:first-child {{
            min-width: 80px !important;
            width: 80px !important;
            max-width: 95px !important;
        }}
        .cti-html-table.first-col-med th:first-child,
        .cti-html-table.first-col-med td:first-child {{
            min-width: 140px !important;
            width: 140px !important;
            max-width: 165px !important;
        }}
        .cti-html-table.first-col-wide th:first-child,
        .cti-html-table.first-col-wide td:first-child {{
            min-width: 240px !important;
            width: 240px !important;
        }}
        .cti-html-table th:last-child {{
            background-color: {PALETTE["primary_dark"]} !important;
            border-left: 2px solid rgba(255, 255, 255, 0.25) !important;
            min-width: 95px;
        }}
        .cti-html-table td {{
            padding: 0.50rem 0.65rem !important;
            border-bottom: 1px solid #E2E8F0 !important;
            border-right: 1px solid #F1F5F9 !important;
            color: #0F172A !important;
            text-align: right;
            font-variant-numeric: tabular-nums;
            white-space: nowrap !important;
            min-width: 75px;
        }}
        .cti-html-table td.col-left {{
            text-align: left !important;
        }}
        .cti-html-table td.col-center {{
            text-align: center !important;
        }}
        .cti-html-table td.col-right {{
            text-align: right !important;
        }}
        .cti-html-table td:first-child {{
            font-weight: 600;
            color: {PALETTE["neutral_dark"]};
            white-space: normal !important;
            line-height: 1.25 !important;
            position: sticky;
            left: 0;
            z-index: 5;
            box-shadow: 2px 0 5px rgba(0, 0, 0, 0.05);
            background-color: inherit;
        }}
        .cti-html-table td:last-child {{
            font-weight: 700;
            border-left: 2px solid #E2E8F0 !important;
            min-width: 95px;
        }}
        .cti-html-table tr:nth-child(even) td {{
            background-color: #F8FAFC;
        }}
        .cti-html-table tr:nth-child(odd) td {{
            background-color: #FFFFFF;
        }}
        .cti-html-table tr:hover td {{
            background-color: #F0FDF4 !important;
        }}
        .cti-html-table tr.is-total td {{
            background-color: #ECFDF5 !important;
            border-top: 2px solid {PALETTE["primary"]} !important;
            border-bottom: 2px solid {PALETTE["primary"]} !important;
            font-weight: 700 !important;
            color: {PALETTE["primary_dark"]} !important;
        }}
        .cti-table-badge {{
            display: inline-block;
            padding: 0.14rem 0.52rem;
            border-radius: 999px;
            font-size: 0.72rem;
            font-weight: 600;
            white-space: nowrap;
            line-height: 1.25;
        }}
        .cti-table-badge.success {{
            background-color: #ECFDF5;
            color: #065F46;
            border: 1px solid #A7F3D0;
        }}
        .cti-table-badge.warning {{
            background-color: #FFFBEB;
            color: #92400E;
            border: 1px solid #FDE68A;
        }}
        .cti-table-badge.danger {{
            background-color: #FEF2F2;
            color: #991B1B;
            border: 1px solid #FECACA;
        }}
        .cti-table-badge.neutral {{
            background-color: #F1F5F9;
            color: #334155;
            border: 1px solid #CBD5E1;
        }}

        /* Tabelas nativas Streamlit estilizadas no padrão corporativo */
        [data-testid="stDataFrame"] {{
            width: 100% !important;
            overflow-x: auto !important;
            max-width: 100% !important;
            border: 1px solid {PALETTE["primary"]} !important;
            border-radius: 8px !important;
            box-shadow: 0 1px 3px rgba(11, 93, 59, 0.08) !important;
        }}

        /* Gráficos Plotly fluidos */
        .js-plotly-plot, .plot-container {{
            width: 100% !important;
            max-width: 100% !important;
        }}

        /* Abas responsivas com quebra de texto elegante */
        [data-testid="stTabs"] button {{
            font-size: 0.84rem !important;
            padding: 0.35rem 0.65rem !important;
            white-space: normal !important;
            word-break: break-word !important;
        }}

        /* Botões corporativos e atalhos rápidos */
        .stButton > button {{
            border-radius: 8px !important;
            font-weight: 600 !important;
            transition: all 0.15s ease-in-out !important;
        }}

        /* Empilhamento inteligente de colunas nativas em telas pequenas */
        @media (max-width: 640px) {{
            [data-testid="column"],
            [data-testid="stColumn"],
            div[data-testid="stHorizontalBlock"] > div {{
                width: 100% !important;
                flex: 1 1 100% !important;
                min-width: 100% !important;
                max-width: 100% !important;
                margin-bottom: 0.45rem !important;
                box-sizing: border-box !important;
            }}
            div[data-testid="stHorizontalBlock"] {{
                flex-wrap: wrap !important;
                gap: 0.5rem !important;
            }}
            div[data-baseweb="slider"], input {{
                max-width: 100% !important;
            }}
        }}

        /* Media queries para Tablet (<= 768px) e Mobile (<= 420px / 360px) */
        @media (max-width: 768px) {{
            .block-container {{
                padding-left: 0.8rem !important;
                padding-right: 0.8rem !important;
                padding-top: 3.6rem !important;
            }}
            .cti-hero {{
                padding: 0.9rem 1rem;
            }}
            .cti-hero-title {{
                font-size: 1.18rem;
            }}
            .cti-kpi-grid {{
                grid-template-columns: repeat(auto-fit, minmax(165px, 1fr));
                gap: 0.65rem;
            }}
            .cti-kpi-value {{
                font-size: 1.18rem;
            }}
            .cti-context-pill {{
                white-space: normal;
            }}
        }}

        @media (max-width: 420px) {{
            .cti-kpi-grid {{
                grid-template-columns: 1fr;
            }}
            .cti-hero-title {{
                font-size: 1.06rem;
            }}
            .cti-hero-subtitle {{
                font-size: 0.81rem;
            }}
            .cti-kpi-card {{
                padding: 0.78rem 0.85rem;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_top_header(
    title: str,
    subtitle: str,
    store: ProcessedDataStore,
    active_scenario: str,
    period_range: tuple[int, int],
    extra_pill: str | None = None,
) -> None:
    """Renderiza o cabeçalho corporativo com contexto de filtros e status da fonte de dados."""
    p_start, p_end = period_range
    per_text = (
        format_period_label(p_start)
        if p_start == p_end
        else f"{format_period_label(p_start)} a {format_period_label(p_end)}"
    )
    src_type_map = {
        "local_excel": "Planilha Oficial Local",
        "staging_cache": "Planilha Oficial (Cache Staging Verificado)",
        "uploaded_excel": "Planilha Carregada via Upload",
        "synthetic_demo": "MODO DEMONSTRAÇÃO SINTÉTICA (NÃO OFICIAL)",
    }
    src_badge = src_type_map.get(store.bundle.source_type, store.bundle.source_name)

    pills_html = [
        f'<span class="cti-context-pill">Cenário Foco: <strong>{html.escape(active_scenario)}</strong></span>',
        f'<span class="cti-context-pill">Período: <strong>{html.escape(per_text)}</strong></span>',
        f'<span class="cti-context-pill">Base: <strong>{len(store.scenarios):,} cenários</strong></span>'.replace(",", "."),
        f'<span class="cti-context-pill">Fonte: <strong>{html.escape(src_badge)}</strong></span>',
    ]
    if extra_pill:
        pills_html.append(f'<span class="cti-context-pill">{html.escape(extra_pill)}</span>')

    st.markdown(
        f"""
        <div class="cti-hero">
            <div class="cti-hero-eyebrow">CTI GLOBAL • PLATAFORMA ANALÍTICA DE PLANEJAMENTO FINANCEIRO</div>
            <div class="cti-hero-title">{html.escape(title)}</div>
            <div class="cti-hero-subtitle">{html.escape(subtitle)}</div>
            <div class="cti-pill-row">
                {''.join(pills_html)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if store.bundle.is_synthetic:
        render_callout(
            "Aviso de Governança — Modo Demonstração Sintética Ativo",
            "Os dados exibidos nesta sessão foram gerados sinteticamente apenas para demonstração funcional e "
            "<strong>não representam a base de dados corporativa oficial da CTI Global</strong>. Para analisar os resultados oficiais, "
            "carregue <code>Contabilidade e Finanças(4).xlsx</code> no seletor da barra lateral.",
            kind="danger",
        )


def build_kpi_card_html(
    label: str,
    value_fmt: str,
    subtitle: str = "",
    delta_text: str | None = None,
    delta_status: str = "neutral",
    badge_text: str | None = "Observado",
    badge_type: str = "real",
    tooltip: str = "",
    card_variant: str = "",
) -> str:
    """Constrói o HTML seguro e responsivo de um cartão de KPI."""
    safe_label = html.escape(label)
    safe_val = html.escape(value_fmt)
    safe_sub = html.escape(subtitle)
    tooltip_html = (
        f'<span class="cti-tooltip-icon" title="{html.escape(tooltip)}">&#9432;</span>'
        if tooltip
        else ""
    )
    badge_html = (
        f'<span class="cti-badge {html.escape(badge_type)}">{html.escape(badge_text)}</span>'
        if badge_text
        else ""
    )
    delta_html = (
        f'<div class="cti-kpi-delta {html.escape(delta_status)}">{html.escape(delta_text)}</div>'
        if delta_text
        else ""
    )
    variant_cls = f" {html.escape(card_variant)}" if card_variant else ""
    return (
        f'<div class="cti-kpi-card{variant_cls}">'
        f'<div class="cti-kpi-top">'
        f'<div class="cti-kpi-label">{safe_label}{tooltip_html}</div>'
        f'{badge_html}'
        f'</div>'
        f'<div>'
        f'<div class="cti-kpi-value">{safe_val}</div>'
        f'{delta_html}'
        f'<div class="cti-kpi-sub">{safe_sub}</div>'
        f'</div>'
        f'</div>'
    )


def render_kpi_grid(cards: list[dict[str, Any]]) -> None:
    """Renderiza uma grade responsiva de cartões de KPI (auto-fit para mobile, tablet e desktop)."""
    if not cards:
        return
    inner = "".join(
        build_kpi_card_html(
            label=c.get("label", ""),
            value_fmt=c.get("value_fmt", "N/D"),
            subtitle=c.get("subtitle", ""),
            delta_text=c.get("delta_text"),
            delta_status=c.get("delta_status", "neutral"),
            badge_text=c.get("badge_text", "Observado"),
            badge_type=c.get("badge_type", "real"),
            tooltip=c.get("tooltip", ""),
            card_variant=c.get("card_variant", ""),
        )
        for c in cards
    )
    st.markdown(f'<div class="cti-kpi-grid">{inner}</div>', unsafe_allow_html=True)


def render_section_header(title: str, description: str = "") -> None:
    """Renderiza título de seção padronizado com barra lateral verde-escura."""
    desc_html = f"<p>{html.escape(description)}</p>" if description else ""
    st.markdown(
        f'<div class="cti-section-hdr"><h3>{html.escape(title)}</h3>{desc_html}</div>',
        unsafe_allow_html=True,
    )


def render_callout(title: str, body_html: str, kind: str = "info") -> None:
    """Renderiza caixa de destaque metodológico (`info`, `warning`, `simulated`, `danger`, `success`)."""
    st.markdown(
        f"""
        <div class="cti-callout {html.escape(kind)}">
            <div class="cti-callout-title">{html.escape(title)}</div>
            <div>{body_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state(
    title: str = "Nenhum registro encontrado para os filtros selecionados",
    suggestion: str = "Amplie o intervalo de períodos ou utilize o botão 'Limpar todos os filtros' na barra lateral.",
) -> None:
    """Exibe estado vazio claro e orientativo quando uma combinação de filtros não retorna linhas."""
    render_callout(title, html.escape(suggestion), kind="warning")


def render_data_footer(store: ProcessedDataStore) -> None:
    """Exibe rodapé de rastreabilidade com fonte original, data do arquivo e convenções metodológicas."""
    b = store.bundle
    st.markdown(
        f"""
        <div class="cti-footer">
            <div>
                <strong>Fonte de Dados:</strong> {html.escape(b.source_name)}
                &nbsp;|&nbsp; <strong>Modificação da Fonte:</strong> {html.escape(b.file_modified_at)}
                &nbsp;|&nbsp; <strong>Assinatura SHA-256:</strong> <code>{html.escape(b.fingerprint)}</code>
            </div>
            <div>
                <strong>Convenções:</strong> Unidade monetária <code>R$</code> (paridade com KPIs_Cenarios) •
                Períodos numerados <code>Ano 1</code> a <code>Ano 12</code> •
                Balanço Ano 12 incompleto &rarr; <code>N/D</code>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def calc_table_height(
    df: pd.DataFrame | None,
    row_height: int = 36,
    header_height: int = 40,
    min_height: int = 130,
    max_height: int = 1400,
) -> int:
    """Calcula a altura exata necessária para exibir todas as linhas da tabela sem rolagem vertical."""
    if df is None or len(df) == 0:
        return min_height
    extra_scroll_padding = 22 if (len(df.columns) > 6) else 10
    calculated = len(df) * row_height + header_height + extra_scroll_padding
    return max(min_height, min(calculated, max_height))


def _get_table_col_align(col_name: str, col_idx: int) -> str:
    """Retorna classe CSS de alinhamento para cada coluna da tabela corporativa."""
    c_low = str(col_name).lower().strip()
    if c_low in ("posição", "ano", "período", "n", "vif", "sentido", "piso/teto", "status", "classificação"):
        return "col-center"
    if col_idx == 0 or any(kw in c_low for kw in [
        "cenário", "indicador", "demonstração", "rubrica", "descrição", "aba", "chave",
        "variável", "preditor", "critério", "mapeamento", "tipo", "origem", "regra", "métrica"
    ]):
        return "col-left"
    return "col-right"


def _format_corporate_cell(val: Any) -> tuple[str, str]:
    """Formata valor de célula com badges semânticos e sanitização HTML segura."""
    if pd.isna(val) or str(val).strip().lower() in ("nan", "none", "<na>"):
        return "—", "—"
    raw_str = str(val).strip()
    raw_low = raw_str.lower()

    # Identificação de pílulas de status e classificação
    if any(w in raw_low for w in ["validado", "conforme", "no alvo", "superada", "baixo risco", "normal", "ok", "ativo", "excelente"]):
        return f'<span class="cti-table-badge success">{html.escape(raw_str)}</span>', raw_str
    elif any(w in raw_low for w in ["atenção", "alerta", "abaixo da meta", "incompleto", "médio risco", "moderado"]):
        return f'<span class="cti-table-badge warning">{html.escape(raw_str)}</span>', raw_str
    elif any(w in raw_low for w in ["crítica", "erro", "desconforme", "alto risco", "reprovado"]):
        return f'<span class="cti-table-badge danger">{html.escape(raw_str)}</span>', raw_str
    elif any(w in raw_low for w in ["simulado", "premissa"]):
        return f'<span class="cti-table-badge neutral">{html.escape(raw_str)}</span>', raw_str

    return html.escape(raw_str), raw_str


def render_corporate_table(
    df: pd.DataFrame,
    title: str = "",
    subtitle: str = "",
    highlight_totals: bool = True,
    compact: bool = False,
) -> None:
    """Renderiza tabela corporativa CTI Global, 100% responsiva, com cabeçalhos verdes e design padronizado."""
    if df is None or len(df) == 0:
        render_empty_state()
        return

    # Determina classe de largura geral da tabela
    num_cols = len(df.columns)
    if num_cols <= 4:
        table_width_cls = "table-narrow"
    elif num_cols <= 7:
        table_width_cls = "table-medium"
    else:
        table_width_cls = "table-wide"

    # Determina largura da primeira coluna com base no conteúdo
    first_col_name = str(df.columns[0])
    first_col_vals = [str(v) for v in df.iloc[:, 0].dropna()[:30]]
    max_len_first = max([len(first_col_name)] + [len(v) for v in first_col_vals]) if first_col_vals else len(first_col_name)
    if max_len_first <= 8:
        first_col_cls = "first-col-short"
    elif max_len_first <= 16:
        first_col_cls = "first-col-med"
    else:
        first_col_cls = "first-col-wide"

    # Define se terá scroll vertical
    scroll_vert_cls = " has-vertical-scroll" if len(df) > 20 else ""

    # Cabeçalhos
    headers_html = []
    for col_idx, col in enumerate(df.columns):
        align_cls = _get_table_col_align(str(col), col_idx)
        headers_html.append(f'<th class="{align_cls}" title="{html.escape(str(col))}">{html.escape(str(col))}</th>')

    total_keywords = [
        "total", "lucro líquido", "ebitda", "saldo final", "patrimônio líquido",
        "ativo total", "passivo total", "média", "acumulado", "subtotal"
    ]

    rows_html = []
    for row_idx, (_, row) in enumerate(df.iterrows()):
        first_val = str(row.iloc[0]).lower() if len(row) > 0 else ""
        is_total = highlight_totals and any(kw in first_val for kw in total_keywords)
        tr_class = ' class="is-total"' if is_total else ""

        tds = []
        for col_idx, col in enumerate(df.columns):
            align_cls = _get_table_col_align(str(col), col_idx)
            val_html, val_plain = _format_corporate_cell(row[col])
            tds.append(f'<td class="{align_cls}" title="{html.escape(val_plain)}">{val_html}</td>')

        rows_html.append(f'<tr{tr_class}>{"".join(tds)}</tr>')

    hdr_block = ""
    if title:
        sub_html = f'<div style="font-size: 0.78rem; color: #64748B; margin-top: 0.15rem;">{html.escape(subtitle)}</div>' if subtitle else ""
        hdr_block = (
            f'<div style="padding: 0.65rem 0.9rem 0.4rem 0.9rem; border-bottom: 1px solid #E2E8F0; background: #F8FAFC;">'
            f'<div style="font-weight: 700; font-size: 0.95rem; color: #0F172A; display: flex; align-items: center; gap: 0.4rem;">'
            f'<span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background-color: #0B5D3B;"></span>'
            f'{html.escape(title)}'
            f'</div>'
            f'{sub_html}'
            f'</div>'
        )

    table_html = (
        f'<div class="cti-table-container">'
        f'{hdr_block}'
        f'<div class="cti-table-scroll{scroll_vert_cls}">'
        f'<table class="cti-html-table {table_width_cls} {first_col_cls}">'
        f'<thead><tr>{"".join(headers_html)}</tr></thead>'
        f'<tbody>{"".join(rows_html)}</tbody>'
        f'</table></div></div>'
    )
    st.markdown(table_html, unsafe_allow_html=True)


def render_corporate_dataframe(
    df: pd.DataFrame,
    title: str = "",
    subtitle: str = "",
    use_container_width: bool = True,
    hide_index: bool = True,
    max_height: int = 1400,
    **kwargs: Any,
) -> None:
    """Renderiza tabelas corporativas no padrão oficial CTI Global (com cabeçalhos verdes e dados completos)."""
    if df is None or len(df) == 0:
        render_empty_state()
        return

    display_df = df.copy()
    if not hide_index and not isinstance(display_df.index, pd.RangeIndex):
        display_df = display_df.reset_index()
    elif not hide_index and display_df.index.name:
        display_df = display_df.reset_index()

    render_corporate_table(
        display_df,
        title=title,
        subtitle=subtitle,
        highlight_totals=kwargs.get("highlight_totals", True),
        compact=kwargs.get("compact", False),
    )


