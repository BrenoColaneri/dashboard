"""Exportação gerencial em CSV, XLSX multi-abas e Relatório Executivo em PDF.

Todos os artefatos exportados respeitam os filtros globais ativos e registram:
- Fonte original dos dados e data/hora de geração.
- Cenário(s) e intervalo de períodos selecionados.
- Parâmetros de simibilidade/metas configurados pelo usuário (quando aplicável).
- Notas metodológicas, unidades adotadas e limitações conhecidas.
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Any

import pandas as pd
from fpdf import FPDF


def _sanitize_pdf_text(text: Any) -> str:
    """Normaliza símbolos matemáticos Unicode para compatibilidade universal com fontes PDF core (Latin-1)."""
    s = "" if text is None else str(text)
    replacements = {
        "\u2013": "-",   # en-dash
        "\u2014": "-",   # em-dash
        "\u2212": "-",   # minus sign
        "\u2260": "!=",  # not equal
        "\u2265": ">=",  # greater or equal
        "\u2264": "<=",  # less or equal
        "\u2022": "*",   # bullet
        "\u201c": '"',
        "\u201d": '"',
        "\u2018": "'",
        "\u2019": "'",
        "\u2192": "->",
        "\u03b2": "beta",
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    return s.encode("latin-1", errors="replace").decode("latin-1")


def dataframe_to_csv_bytes(df: pd.DataFrame, sep: str = ";", decimal: str = ",") -> bytes:
    """Exporta DataFrame em CSV com BOM UTF-8 (compatível diretamente com Excel pt-BR)."""
    buf = io.StringIO()
    df.to_csv(buf, index=False, sep=sep, decimal=decimal)
    return buf.getvalue().encode("utf-8-sig")


def build_excel_report_bytes(
    tables: dict[str, pd.DataFrame],
    metadata: dict[str, Any],
) -> bytes:
    """Gera pasta de trabalho XLSX formatada com múltiplas abas analíticas e aba de Metadados."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book
        header_fmt = workbook.add_format({
            "bold": True,
            "bg_color": "#0B5D3B",
            "font_color": "#FFFFFF",
            "border": 1,
            "valign": "vcenter",
        })
        meta_key_fmt = workbook.add_format({"bold": True, "bg_color": "#F1F5F9", "border": 1})
        meta_val_fmt = workbook.add_format({"border": 1, "text_wrap": True})

        # Aba 1: Metadados, Filtros, Premissas e Limitações
        meta_rows = [{"Campo": str(k), "Valor / Descrição": str(v)} for k, v in metadata.items()]
        meta_df = pd.DataFrame(meta_rows)
        meta_sheet_name = "Metadados_e_Premissas"
        meta_df.to_excel(writer, sheet_name=meta_sheet_name, index=False)
        ws_meta = writer.sheets[meta_sheet_name]
        ws_meta.set_column(0, 0, 34, meta_key_fmt)
        ws_meta.set_column(1, 1, 85, meta_val_fmt)
        for col_idx, col_name in enumerate(meta_df.columns):
            ws_meta.write(0, col_idx, col_name, header_fmt)

        # Demais abas de dados filtrados
        for raw_name, df in tables.items():
            if df is None or df.empty:
                continue
            safe_name = str(raw_name)[:31].replace("/", "_").replace("\\", "_").replace(":", "")
            clean_df = df.copy()
            clean_df.to_excel(writer, sheet_name=safe_name, index=False)
            ws = writer.sheets[safe_name]
            for col_idx, col_name in enumerate(clean_df.columns):
                ws.write(0, col_idx, str(col_name), header_fmt)
                sample_max = max(
                    [len(str(col_name))]
                    + [len(str(v)) for v in clean_df[col_name].head(50).tolist() if pd.notna(v)]
                )
                ws.set_column(col_idx, col_idx, min(max(sample_max + 3, 12), 46))

    return output.getvalue()


class _CTIPDFReport(FPDF):
    """Template PDF corporativo CTI Global."""

    def __init__(self, report_title: str, source_label: str) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self.report_title = _sanitize_pdf_text(report_title)
        self.source_label = _sanitize_pdf_text(source_label)
        self.set_auto_page_break(auto=True, margin=16)

    def header(self) -> None:
        self.set_fill_color(11, 93, 59)  # #0B5D3B
        self.rect(0, 0, 210, 20, style="F")
        self.set_xy(10, 4)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(255, 255, 255)
        self.cell(0, 6, self.report_title, new_x="LMARGIN", new_y="NEXT")
        self.set_x(10)
        self.set_font("Helvetica", "", 8)
        self.cell(
            0,
            5,
            _sanitize_pdf_text("Plataforma Analitica de Planejamento Financeiro"),
            new_x="LMARGIN",
            new_y="NEXT",
        )
        self.ln(6)
        self.set_text_color(15, 23, 42)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "I", 7.5)
        self.set_text_color(100, 116, 139)
        now_s = datetime.now().strftime("%d/%m/%Y %H:%M")
        self.cell(
            0,
            6,
            _sanitize_pdf_text(f"Fonte: {self.source_label} | Gerado em {now_s} | Pagina {self.page_no()}/{{nb}}"),
            align="C",
        )


def build_pdf_executive_report(
    scenario_code: str,
    period_label: str,
    source_name: str,
    is_synthetic: bool,
    kpi_summary_rows: list[dict[str, str]],
    goals_df: pd.DataFrame | None = None,
    sensitivity_result: dict[str, Any] | None = None,
    methodology_notes: list[str] | None = None,
) -> bytes:
    """Gera relatório executivo e analítico em PDF respeitando filtros, metas e simulação."""
    pdf = _CTIPDFReport(
        report_title="CTI - Relatorio Executivo e Financeiro de Apoio a Decisao",
        source_label=source_name,
    )
    pdf.alias_nb_pages()
    pdf.add_page()

    if is_synthetic:
        pdf.set_fill_color(254, 242, 242)
        pdf.set_text_color(185, 28, 28)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(
            0,
            6,
            _sanitize_pdf_text(
                "AVISO IMPORTANTE: Este relatorio foi gerado em MODO DEMONSTRACAO SINTETICA. "
                "Os valores abaixo NAO representam dados reais da planilha original da CTI."
            ),
            border=1,
            fill=True,
            new_x="LMARGIN",
            new_y="NEXT",
        )
        pdf.ln(3)
        pdf.set_text_color(15, 23, 42)

    # Bloco 1: Contexto e Filtros Selecionados
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(11, 93, 59)
    pdf.set_x(pdf.l_margin)
    pdf.cell(0, 7, _sanitize_pdf_text("1. Escopo da Analise e Parametros de Filtro"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(15, 23, 42)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(
        0,
        5.5,
        _sanitize_pdf_text(
            f"Cenario principal selecionado: {scenario_code}\n"
            f"Recorte temporal analisado: {period_label} (periodos numerados do modelo; nao correspondem a anos civis)\n"
            f"Fonte de dados utilizada: {source_name}\n"
            f"Unidade monetaria adotada: R$ (consistente com KPIs_Cenarios, KPIs_Estatisticas e Resumo_Cenarios)"
        ),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(3)

    # Bloco 2: Tabela de KPIs Principais
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(11, 93, 59)
    pdf.cell(0, 7, _sanitize_pdf_text("2. Resumo Executivo de Indicadores Financeiros (KPIs)"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(15, 23, 42)

    col_w = [66, 38, 42, 44]
    headers = ["Indicador", "Media no Recorte", "Ultimo Periodo Valido", "Benchmark (Mediana Base)"]
    pdf.set_fill_color(226, 232, 240)
    pdf.set_font("Helvetica", "B", 8.5)
    for w, h in zip(col_w, headers):
        pdf.cell(w, 6.5, _sanitize_pdf_text(h), border=1, fill=True)
    pdf.ln()

    pdf.set_font("Helvetica", "", 8)
    for row in kpi_summary_rows:
        pdf.cell(col_w[0], 6, _sanitize_pdf_text(row.get("Indicador", ""))[:38], border=1)
        pdf.cell(col_w[1], 6, _sanitize_pdf_text(row.get("Media", "N/D")), border=1, align="R")
        pdf.cell(col_w[2], 6, _sanitize_pdf_text(row.get("Ultimo", "N/D")), border=1, align="R")
        pdf.cell(col_w[3], 6, _sanitize_pdf_text(row.get("Mediana_Base", "N/D")), border=1, align="R")
        pdf.ln()
    pdf.ln(4)

    # Bloco 3: Metas Configuradas (quando existirem metas definidas pelo usuário)
    if goals_df is not None and not goals_df.empty:
        defined = goals_df[goals_df["Classificação"] != "Meta Não Definida"]
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(11, 93, 59)
        pdf.cell(0, 7, _sanitize_pdf_text("3. Acompanhamento de Metas Financeiras Configuradas"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(15, 23, 42)
        if defined.empty:
            pdf.set_font("Helvetica", "I", 8.5)
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(
                0,
                5,
                _sanitize_pdf_text(
                    "Nenhuma meta oficial foi pre-definida na planilha original nem configurada nesta sessao."
                ),
                new_x="LMARGIN",
                new_y="NEXT",
            )
        else:
            gw = [58, 36, 36, 24, 36]
            gh = ["Indicador", "Observado", "Meta Config.", "Atingim.", "Status"]
            pdf.set_fill_color(226, 232, 240)
            pdf.set_font("Helvetica", "B", 8)
            for w, h in zip(gw, gh):
                pdf.cell(w, 6, _sanitize_pdf_text(h), border=1, fill=True)
            pdf.ln()
            pdf.set_font("Helvetica", "", 7.8)
            for _, gr in defined.iterrows():
                pdf.cell(gw[0], 5.8, _sanitize_pdf_text(gr["Indicador"])[:34], border=1)
                pdf.cell(gw[1], 5.8, _sanitize_pdf_text(gr["Valor Observado (Fmt)"]), border=1, align="R")
                pdf.cell(gw[2], 5.8, _sanitize_pdf_text(gr["Meta Configurada (Fmt)"]), border=1, align="R")
                pdf.cell(gw[3], 5.8, _sanitize_pdf_text(gr["Atingimento (Fmt)"]), border=1, align="R")
                pdf.cell(gw[4], 5.8, _sanitize_pdf_text(gr["Classificação"])[:22], border=1)
                pdf.ln()
        pdf.ln(4)

    # Bloco 4: Análise de Sensibilidade (quando fornecida)
    if sensitivity_result and not sensitivity_result.get("comparison_table", pd.DataFrame()).empty:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(11, 93, 59)
        pdf.cell(
            0,
            7,
            _sanitize_pdf_text("4. Analise de Sensibilidade Financeira (Valores Simulados em Memoria)"),
            new_x="LMARGIN",
            new_y="NEXT",
        )
        pdf.set_text_color(15, 23, 42)
        pdf.set_font("Helvetica", "", 8)
        for exp in sensitivity_result.get("premises_explanation", []):
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(0, 4.8, _sanitize_pdf_text(f"* {exp}"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        sw = [58, 36, 36, 34, 26]
        sh = ["Indicador", "Original", "Simulado", "Diferenca", "Var. %"]
        pdf.set_fill_color(219, 234, 254)
        pdf.set_font("Helvetica", "B", 8)
        for w, h in zip(sw, sh):
            pdf.cell(w, 6, _sanitize_pdf_text(h), border=1, fill=True)
        pdf.ln()
        pdf.set_font("Helvetica", "", 7.8)
        for _, sr in sensitivity_result["comparison_table"].iterrows():
            pdf.cell(sw[0], 5.8, _sanitize_pdf_text(sr["Indicador"])[:34], border=1)
            pdf.cell(sw[1], 5.8, _sanitize_pdf_text(sr["Original (Fmt)"]), border=1, align="R")
            pdf.cell(sw[2], 5.8, _sanitize_pdf_text(sr["Simulado (Fmt)"]), border=1, align="R")
            pdf.cell(sw[3], 5.8, _sanitize_pdf_text(sr["Diferença (Fmt)"])[:20], border=1, align="R")
            pdf.cell(sw[4], 5.8, _sanitize_pdf_text(sr["Variação % (Fmt)"]), border=1, align="R")
            pdf.ln()
        pdf.ln(4)

    # Bloco 5: Metodologia, Premissas e Limitações Conhecidas
    notes = methodology_notes or [
        "Os indicadores seguem estritamente o Dicionario_KPIs e as formulas auditadas do modelo de planejamento.",
        "No Ano 12, o Balanco Patrimonial encontra-se estruturalmente incompleto na base original; por isso, Liquidez, Endividamento, NOPAT, Capital Investido, ROIC e EVA sao tratados como N/D nesse periodo.",
        "O EBITDA Calculado (Resultado Operacional + |D&A|) e mantido separado do EBITDA do Modelo (campo nativo DRE - EBITDA).",
        "Custos variaveis correspondem ao proxy |DRE - Custos|, pois a base CTI nao segrega custos fixos e variaveis.",
        "WACC (12%), CAC (R$ 200,00/cliente), LTV (R$ 2.100,00/cliente) e Ticket Medio inserido pelo usuario sao premissas simuladas de modelagem, nao dados observados de mercado.",
        "Analises de correlacao e regressao descrevem associacoes estatisticas nos cenarios e nao implicam causalidade.",
    ]
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(11, 93, 59)
    pdf.set_x(pdf.l_margin)
    pdf.cell(0, 7, _sanitize_pdf_text("5. Notas Metodologicas, Governanca e Limitacoes"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(15, 23, 42)
    pdf.set_font("Helvetica", "", 8.2)
    for note in notes:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 5, _sanitize_pdf_text(f"* {note}"), new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())
