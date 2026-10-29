"""Configurações centrais, metadados auditados de KPIs e formatação brasileira (pt-BR).

Este módulo centraliza:
- Mapeamento oficial das 9 abas de `Contabilidade e Finanças.xlsx` (base de planejamento financeiro da CTI Global).
- Dicionário auditado de KPIs com rastreabilidade entre a aba `Dicionario_KPIs` e as
  fórmulas efetivamente implementadas em `KPIs_Cenarios`, `KPIs_Estatisticas` e `Resumo_Cenarios`.
- Funções de formatação numérica no padrão brasileiro (`R$`, `%`, `x`, `R$/cliente`, `N/D`).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Constantes e premissas documentadas no modelo de planejamento
# ---------------------------------------------------------------------------
EXPECTED_SHEETS: tuple[str, ...] = (
    "Balanco_Cenarios",
    "DRE_Cenarios",
    "DFC_Cenarios",
    "KPIs_Cenarios",
    "KPIs_Estatisticas",
    "Dicionario_KPIs",
    "Resumo_Cenarios",
    "Ranking_Cenarios",
    "Top10_Rankings",
)

ESSENTIAL_SHEETS: tuple[str, ...] = (
    "Balanco_Cenarios",
    "DRE_Cenarios",
    "DFC_Cenarios",
    "KPIs_Cenarios",
    "Dicionario_KPIs",
    "Resumo_Cenarios",
)

WACC_MODEL_PREMISE: float = 0.12
CAC_SIMULATED_PREMISE: float = 200.0
LTV_SIMULATED_PREMISE: float = 2100.0
LTV_CAC_SIMULATED_PREMISE: float = 10.50

# Paleta corporativa discreta (Verde-escuro institucional CTI Global, cinzas neutros e cores semânticas)
PALETTE: dict[str, str] = {
    "primary": "#0B5D3B",        # Verde-escuro principal
    "primary_dark": "#063F27",   # Verde institucional profundo
    "primary_light": "#15803D",  # Verde médio para séries secundárias
    "accent": "#0F766E",         # Teal corporativo
    "neutral_dark": "#0F172A",   # Slate 900
    "neutral": "#475569",        # Slate 600
    "neutral_light": "#94A3B8",  # Slate 400
    "border": "#E2E8F0",         # Slate 200
    "surface": "#FFFFFF",        # Fundo de cartões
    "background": "#F8FAFC",     # Fundo geral
    "positive": "#15803D",       # Variação favorável / meta atingida
    "warning": "#B45309",        # Alerta / atenção
    "negative": "#B91C1C",       # Variação desfavorável / abaixo da meta
    "simulated": "#1D4ED8",      # Azul exclusivo para identificar valores simulados
    "target": "#6D28D9",         # Roxo discreto para linhas de meta configurada
}


def format_period_label(period_num: int | float | str) -> str:
    """Converte o número do período (1..12) para 'Ano 1'..'Ano 12', sem inventar anos civis."""
    if pd.isna(period_num):
        return "N/D"
    if isinstance(period_num, str):
        cleaned = period_num.strip()
        if cleaned.lower().startswith("ano"):
            return cleaned.title()
        try:
            return f"Ano {int(float(cleaned))}"
        except ValueError:
            return cleaned
    return f"Ano {int(period_num)}"


# ---------------------------------------------------------------------------
# Formatação numérica brasileira (pt-BR) com tratamento seguro de N/D
# ---------------------------------------------------------------------------
def is_valid_number(value: Any) -> bool:
    """Retorna True somente se o valor for numérico finito e não nulo."""
    if value is None or isinstance(value, bool):
        return False
    try:
        fval = float(value)
        return not (math.isnan(fval) or math.isinf(fval))
    except (TypeError, ValueError):
        return False


def format_number_br(value: Any, decimals: int = 2, na_label: str = "N/D") -> str:
    """Formata um número no padrão brasileiro (ponto para milhar, vírgula para decimal)."""
    if not is_valid_number(value):
        return na_label
    fval = float(value)
    formatted = f"{fval:,.{decimals}f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def format_currency_brl(
    value: Any,
    decimals: int = 2,
    compact: bool = False,
    na_label: str = "N/D",
) -> str:
    """Formata valores monetários em Reais (R$) na convenção adotada das abas analíticas."""
    if not is_valid_number(value):
        return na_label
    fval = float(value)
    sign = "-" if fval < 0 else ""
    abs_val = abs(fval)
    if compact:
        if abs_val >= 1e9:
            return f"{sign}R$ {format_number_br(abs_val / 1e9, decimals)} bi"
        if abs_val >= 1e6:
            return f"{sign}R$ {format_number_br(abs_val / 1e6, decimals)} mi"
        if abs_val >= 1e3:
            return f"{sign}R$ {format_number_br(abs_val / 1e3, decimals)} mil"
    return f"{sign}R$ {format_number_br(abs_val, decimals)}"


def format_pct_br(
    value: Any,
    decimals: int = 2,
    already_percent: bool = False,
    signed: bool = False,
    na_label: str = "N/D",
) -> str:
    """Formata proporções (ex.: 0.798 -> '79,80%') ou percentuais já multiplicados por 100."""
    if not is_valid_number(value):
        return na_label
    fval = float(value) if already_percent else float(value) * 100.0
    prefix = "+" if (signed and fval > 0) else ""
    return f"{prefix}{format_number_br(fval, decimals)}%"


def format_multiple_br(value: Any, decimals: int = 2, na_label: str = "N/D") -> str:
    """Formata múltiplos e índices financeiros (ex.: 1.2 -> '1,20x')."""
    if not is_valid_number(value):
        return na_label
    return f"{format_number_br(float(value), decimals)}x"


def format_by_unit(
    value: Any,
    unit: str,
    compact_currency: bool = False,
    decimals: int = 2,
    na_label: str = "N/D",
) -> str:
    """Formata qualquer KPI consistentemente de acordo com sua unidade oficial."""
    if not is_valid_number(value):
        return na_label
    u = (unit or "").strip()
    if u == "%":
        return format_pct_br(value, decimals=decimals, na_label=na_label)
    if u == "x":
        return format_multiple_br(value, decimals=decimals, na_label=na_label)
    if u == "R$/cliente":
        return f"{format_currency_brl(value, decimals=decimals, compact=False, na_label=na_label)}/cliente"
    if u in ("R$", "R$ mil"):
        return format_currency_brl(value, decimals=decimals, compact=compact_currency, na_label=na_label)
    return format_number_br(value, decimals=decimals, na_label=na_label)


# ---------------------------------------------------------------------------
# Catálogo Auditado de KPIs Financeiros e Operacionais
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class KPIMetadata:
    key: str
    name: str
    short_name: str
    category: str
    kpis_sheet_col: str | None
    resumo_sheet_col: str | None
    estatisticas_name: str | None
    unit: str
    dictionary_raw_unit: str
    higher_is_better: bool | None
    available_in_year_12: bool
    is_simulated_premise: bool
    objective: str
    formula: str
    source: str
    granularity: str
    periodicity: str
    premises: str
    validation_rule: str
    missing_treatment: str
    interpretation: str
    limitations: str


KPI_CATALOG: dict[str, KPIMetadata] = {
    "receita": KPIMetadata(
        key="receita",
        name="Receita",
        short_name="Receita",
        category="Complementares e Operacionais",
        kpis_sheet_col="Receita (R$)",
        resumo_sheet_col="Receita média (R$)",
        estatisticas_name="Receita",
        unit="R$",
        dictionary_raw_unit="R$ mil",
        higher_is_better=True,
        available_in_year_12=True,
        is_simulated_premise=False,
        objective="Mensurar o volume bruto de faturamento operacional por cenário e período, servindo de base para as margens.",
        formula="ABS(DRE - Receita)",
        source="DRE_Cenarios (campo 'DRE - Receita') e KPIs_Cenarios",
        granularity="Cenário × Período (Ano 1 a Ano 12); média Anos 1–11 no Resumo_Cenarios",
        periodicity="Anual (períodos numerados Ano 1 a Ano 12)",
        premises="Valores preservados na escala monetária original (R$) das abas analíticas do modelo de planejamento.",
        validation_rule="Conferir diretamente com ABS(DRE - Receita) para cada par Cenário × Ano; validar ausência de valores negativos ou nulos.",
        missing_treatment="Exibir N/D caso ausente; se igual a zero, bloquear cálculo de margens dependentes.",
        interpretation="Quanto maior a receita, maior a escala de faturamento bruto antes de tributos, custos e despesas.",
        limitations="Não distingue crescimento por preço versus volume físico, pois a base CTI não contém quantidade transacionada.",
    ),
    "custos_variaveis": KPIMetadata(
        key="custos_variaveis",
        name="Custos Variáveis (Proxy)",
        short_name="Custos Proxy",
        category="Complementares e Operacionais",
        kpis_sheet_col="Custos variáveis (R$)",
        resumo_sheet_col="Custos variáveis proxy médios (R$)",
        estatisticas_name="Custos variáveis",
        unit="R$",
        dictionary_raw_unit="R$ mil",
        higher_is_better=False,
        available_in_year_12=True,
        is_simulated_premise=False,
        objective="Aproximar os custos diretos/variáveis para viabilizar o cálculo gerencial da margem de contribuição.",
        formula="ABS(DRE - Custos)",
        source="DRE_Cenarios (campo 'DRE - Custos') e KPIs_Cenarios",
        granularity="Cenário × Período (Ano 1 a Ano 12); média Anos 1–11 no Resumo_Cenarios",
        periodicity="Anual",
        premises="Como a DRE da CTI não segrega custos fixos e variáveis, adota-se ABS(DRE - Custos) como proxy metodológico.",
        validation_rule="Conferir ABS(DRE - Custos) por Cenário × Ano e registrar explicitamente sua natureza de proxy.",
        missing_treatment="Exibir N/D se DRE - Custos estiver ausente.",
        interpretation="Representa o consumo direto de recursos operacionais antes de depreciação e amortização.",
        limitations="Por ser proxy do custo total da DRE, pode incluir parcelas fixas; em simulações de volume, o percentual variável deve ser parametrizável.",
    ),
    "margem_contribuicao": KPIMetadata(
        key="margem_contribuicao",
        name="Margem de Contribuição",
        short_name="Margem Contrib.",
        category="Rentabilidade e Geração de Valor",
        kpis_sheet_col="Margem de contribuição",
        resumo_sheet_col="Margem de contribuição média",
        estatisticas_name="Margem de contribuição",
        unit="%",
        dictionary_raw_unit="%",
        higher_is_better=True,
        available_in_year_12=True,
        is_simulated_premise=False,
        objective="Medir a fração da receita líquida (Receita ajustada por Tributos) que remanesce após os custos proxy.",
        formula="(ABS(Receita) + Tributos − ABS(Custos)) / (ABS(Receita) + Tributos)",
        source="DRE_Cenarios e KPIs_Cenarios",
        granularity="Cenário × Período (Ano 1 a Ano 12); média Anos 1–11 no Resumo_Cenarios",
        periodicity="Anual",
        premises="Tributos na DRE possuem sinal negativo, portanto (ABS(Receita) + Tributos) corresponde à Receita Líquida.",
        validation_rule="Verificar (ABS(Receita) + Tributos) ≠ 0; recalcular a razão e reconciliar com KPIs_Cenarios.",
        missing_treatment="Retornar N/D caso (ABS(Receita) + Tributos) ≤ 0 ou campos de origem estejam ausentes.",
        interpretation="Indica a eficiência operacional sobre a receita líquida para cobrir depreciação, despesas financeiras, impostos e remunerar o capital.",
        limitations="Sensível à premissa de custos variáveis como proxy integral da linha DRE - Custos.",
    ),
    "ebitda_calculado": KPIMetadata(
        key="ebitda_calculado",
        name="EBITDA Calculado",
        short_name="EBITDA Calc.",
        category="Rentabilidade e Geração de Valor",
        kpis_sheet_col="EBITDA calculado (R$)",
        resumo_sheet_col="EBITDA calculado (R$)",
        estatisticas_name="EBITDA calculado",
        unit="R$",
        dictionary_raw_unit="R$ mil",
        higher_is_better=True,
        available_in_year_12=True,
        is_simulated_premise=False,
        objective="Mensurar a geração operacional potencial de caixa recalculada diretamente a partir do Resultado Operacional e D&A.",
        formula="Resultado Operacional + ABS(Depreciação e Amortização)",
        source="DRE_Cenarios ('DRE - Resultado Operacional', 'DRE - Depreciação e Amortização') e KPIs_Cenarios",
        granularity="Cenário × Período (Ano 1 a Ano 12); média Anos 1–11 no Resumo_Cenarios",
        periodicity="Anual",
        premises="Segue estritamente a regra contábil do modelo de planejamento; mantido separado do campo 'DRE - EBITDA' informado pelo modelo.",
        validation_rule="Recalcular Resultado Operacional + ABS(D&A) e conferir diferença zero frente à coluna 'EBITDA calculado (R$)'.",
        missing_treatment="Exibir N/D se Resultado Operacional ou D&A estiverem ausentes.",
        interpretation="Reflete o desempenho operacional recorrente antes dos efeitos não caixa de depreciação/amortização e antes da estrutura financeira.",
        limitations="Difere sistematicamente do 'EBITDA do modelo' (que inclui outros ajustes específicos do modelo CTI) e não equivale à geração efetiva de caixa da DFC.",
    ),
    "ebitda_modelo": KPIMetadata(
        key="ebitda_modelo",
        name="EBITDA do Modelo",
        short_name="EBITDA Modelo",
        category="Rentabilidade e Geração de Valor",
        kpis_sheet_col="EBITDA do modelo (R$)",
        resumo_sheet_col="EBITDA modelo (R$)",
        estatisticas_name="EBITDA do modelo",
        unit="R$",
        dictionary_raw_unit="R$ mil",
        higher_is_better=True,
        available_in_year_12=True,
        is_simulated_premise=False,
        objective="Preservar e acompanhar o valor de EBITDA reportado nativamente pela linha 'DRE - EBITDA' da modelagem CTI.",
        formula="DRE - EBITDA",
        source="DRE_Cenarios (campo 'DRE - EBITDA') e KPIs_Cenarios",
        granularity="Cenário × Período (Ano 1 a Ano 12); média Anos 1–11 no Resumo_Cenarios",
        periodicity="Anual",
        premises="Nunca deve ser fundido ou tratado como sinônimo do EBITDA Calculado.",
        validation_rule="Conferir igualdade exata com o campo 'DRE - EBITDA' do cenário e período correspondentes.",
        missing_treatment="Exibir N/D caso o campo original não esteja preenchido.",
        interpretation="Permite comparabilidade direta com os rankings oficiais da planilha (que utilizam a Margem EBITDA do modelo).",
        limitations="A composição interna exata da diferença entre o EBITDA do modelo e (Resultado Operacional + |D&A|) decorre de regras proprietárias da base CTI.",
    ),
    "margem_ebitda_calculada": KPIMetadata(
        key="margem_ebitda_calculada",
        name="Margem EBITDA Calculada",
        short_name="Mg. EBITDA Calc.",
        category="Rentabilidade e Geração de Valor",
        kpis_sheet_col="Margem EBITDA calculada",
        resumo_sheet_col="Margem EBITDA calculada",
        estatisticas_name="Margem EBITDA calculada",
        unit="%",
        dictionary_raw_unit="%",
        higher_is_better=True,
        available_in_year_12=True,
        is_simulated_premise=False,
        objective="Avaliar a conversão percentual da Receita Bruta em EBITDA Calculado.",
        formula="EBITDA Calculado / ABS(Receita)",
        source="DRE_Cenarios e KPIs_Cenarios",
        granularity="Cenário × Período (Ano 1 a Ano 12); média Anos 1–11 no Resumo_Cenarios",
        periodicity="Anual",
        premises="Denominador é a Receita Bruta (DRE - Receita), conforme revisão metodológica documentada no modelo de planejamento.",
        validation_rule="Verificar Receita ≠ 0; recalcular EBITDA Calculado / ABS(Receita) e reconciliar com KPIs_Cenarios.",
        missing_treatment="Retornar N/D quando Receita = 0 ou ausente.",
        interpretation="Quanto maior, maior a rentabilidade operacional antes de D&A recalculada por unidade monetária vendida.",
        limitations="Calculada sobre Receita Bruta (não líquida de tributos), devendo ser interpretada em conjunto com a carga tributária.",
    ),
    "margem_ebitda_modelo": KPIMetadata(
        key="margem_ebitda_modelo",
        name="Margem EBITDA do Modelo",
        short_name="Mg. EBITDA Mod.",
        category="Rentabilidade e Geração de Valor",
        kpis_sheet_col="Margem EBITDA do modelo",
        resumo_sheet_col="Margem EBITDA modelo",
        estatisticas_name="Margem EBITDA do modelo",
        unit="%",
        dictionary_raw_unit="%",
        higher_is_better=True,
        available_in_year_12=True,
        is_simulated_premise=False,
        objective="Avaliar a margem operacional considerando o EBITDA nativo do modelo CTI sobre a Receita.",
        formula="EBITDA do Modelo / ABS(Receita)",
        source="DRE_Cenarios, KPIs_Cenarios, Resumo_Cenarios e Ranking_Cenarios",
        granularity="Cenário × Período (Ano 1 a Ano 12); média Anos 1–11 no Resumo_Cenarios",
        periodicity="Anual",
        premises="Indicador-chave utilizado pela planilha para ordenar o ranking principal de Alta Rentabilidade.",
        validation_rule="Verificar Receita ≠ 0; recalcular DRE - EBITDA / ABS(Receita) e conferir com KPIs_Cenarios.",
        missing_treatment="Retornar N/D quando Receita = 0 ou ausente.",
        interpretation="Expressa a eficiência operacional segundo o conceito nativo de EBITDA do modelo CTI.",
        limitations="No Ano 12 apresenta salto atípico (~95%) devido a 'Outros Resultados Operacionais' elevados no encerramento do horizonte.",
    ),
    "nopat": KPIMetadata(
        key="nopat",
        name="NOPAT",
        short_name="NOPAT",
        category="Rentabilidade e Geração de Valor",
        kpis_sheet_col="NOPAT (R$)",
        resumo_sheet_col="NOPAT (R$)",
        estatisticas_name="NOPAT",
        unit="R$",
        dictionary_raw_unit="R$ mil",
        higher_is_better=True,
        available_in_year_12=False,
        is_simulated_premise=False,
        objective="Estimar o lucro operacional líquido de impostos (Net Operating Profit After Taxes) antes do efeito financeiro.",
        formula="Resultado Operacional × (1 − |IR/CSLL| / |Resultado Antes do IR|)",
        source="DRE_Cenarios e KPIs_Cenarios",
        granularity="Cenário × Período (Anos 1 a 11; N/D no Ano 12 conforme planilha)",
        periodicity="Anual",
        premises="Alíquota efetiva derivada diretamente da DRE de cada cenário e período. No Ano 12 é omitido (N/D) em conjunto com o bloco EVA/ROIC.",
        validation_rule="Verificar LAIR ≠ 0; recalcular taxa efetiva de IR/CSLL e reconciliar NOPAT com KPIs_Cenarios nos Anos 1–11.",
        missing_treatment="N/D no Ano 12 (bloco EVA incompleto) ou quando Resultado Antes do IR = 0.",
        interpretation="Representa o lucro gerado estritamente pelos ativos operacionais disponível para remunerar credores e acionistas.",
        limitations="Utiliza a alíquota efetiva total da DRE (que sofre influência do resultado financeiro sobre o LAIR).",
    ),
    "capital_investido": KPIMetadata(
        key="capital_investido",
        name="Capital Investido",
        short_name="Cap. Investido",
        category="Rentabilidade e Geração de Valor",
        kpis_sheet_col="Capital Investido (R$)",
        resumo_sheet_col="Capital Investido (R$)",
        estatisticas_name="Capital Investido",
        unit="R$",
        dictionary_raw_unit="R$ mil",
        higher_is_better=None,
        available_in_year_12=False,
        is_simulated_premise=False,
        objective="Quantificar a base total de capital alocada no negócio para apuração do ROIC e do EVA.",
        formula="ABS(PC) + ABS(PNC) + ABS(Ativo Total − ABS(PC) − ABS(PNC))",
        source="Balanco_Cenarios e KPIs_Cenarios",
        granularity="Cenário × Período (Anos 1 a 11; N/D no Ano 12)",
        periodicity="Anual",
        premises="Reproduz fielmente a fórmula da planilha KPIs_Cenarios com normalização modular de passivos e PL implícito.",
        validation_rule="Nos Anos 1–11, reconciliar com 'Capital Investido (R$)'; no Ano 12 tratar como N/D por incompletude do Balanço.",
        missing_treatment="N/D no Ano 12 (contas patrimoniais ausentes).",
        interpretation="Base monetária total sobre a qual incide o custo médio ponderado de capital (WACC).",
        limitations="Nos Anos 5–11, quando Passivo Circulante assume sinal positivo na base CTI, a soma modular supera o Ativo Total (registrado na auditoria).",
    ),
    "eva": KPIMetadata(
        key="eva",
        name="EVA (Economic Value Added)",
        short_name="EVA",
        category="Rentabilidade e Geração de Valor",
        kpis_sheet_col="EVA (R$)",
        resumo_sheet_col="EVA (R$)",
        estatisticas_name="EVA",
        unit="R$",
        dictionary_raw_unit="R$ mil",
        higher_is_better=True,
        available_in_year_12=False,
        is_simulated_premise=False,
        objective="Mensurar a criação ou destruição de valor econômico após deduzir o custo de oportunidade do capital investido.",
        formula="NOPAT − (Capital Investido × WACC), com WACC = 12% (premissa)",
        source="KPIs_Cenarios, DRE_Cenarios e Balanco_Cenarios",
        granularity="Cenário × Período (Anos 1 a 11; N/D no Ano 12)",
        periodicity="Anual",
        premises="WACC = 12,00% ao ano é premissa metodológica do modelo do modelo de planejamento, não dado observado de mercado.",
        validation_rule="Conferir WACC = 12%; recalcular NOPAT − (Capital Investido × 0,12) nos Anos 1–11; N/D no Ano 12.",
        missing_treatment="N/D no Ano 12 devido à incompletude do Balanço Patrimonial.",
        interpretation="EVA > 0 indica criação de valor econômico acima do custo de capital de 12%; EVA < 0 indica destruição de valor.",
        limitations="Altamente sensível à premissa fixa de WACC (12%) e à convenção de cálculo do Capital Investido.",
    ),
    "roic": KPIMetadata(
        key="roic",
        name="ROIC (Retorno sobre o Capital Investido)",
        short_name="ROIC",
        category="Rentabilidade e Geração de Valor",
        kpis_sheet_col="ROIC",
        resumo_sheet_col="ROIC",
        estatisticas_name="ROIC",
        unit="%",
        dictionary_raw_unit="%",
        higher_is_better=True,
        available_in_year_12=False,
        is_simulated_premise=False,
        objective="Medir a taxa percentual de retorno operacional líquido sobre o Capital Investido.",
        formula="NOPAT / Capital Investido",
        source="KPIs_Cenarios, DRE_Cenarios e Balanco_Cenarios",
        granularity="Cenário × Período (Anos 1 a 11; N/D no Ano 12)",
        periodicity="Anual",
        premises="Comparável diretamente com a premissa de WACC (12%) para avaliar o spread de criação de valor (ROIC − WACC).",
        validation_rule="Verificar Capital Investido ≠ 0 nos Anos 1–11; recalcular NOPAT / Capital Investido; N/D no Ano 12.",
        missing_treatment="N/D no Ano 12 ou se Capital Investido = 0.",
        interpretation="Quando ROIC > WACC (12%), a operação remunera o capital acima do custo mínimo exigido pelo modelo.",
        limitations="Indisponível no Ano 12 devido à ausência de fechamento completo do Balanço Patrimonial.",
    ),
    "lc": KPIMetadata(
        key="lc",
        name="Liquidez Corrente (LC) – Ajustada",
        short_name="Liq. Corrente",
        category="Liquidez",
        kpis_sheet_col="LC",
        resumo_sheet_col="LC",
        estatisticas_name="Liquidez Corrente (LC) – ajustada",
        unit="x",
        dictionary_raw_unit="x",
        higher_is_better=True,
        available_in_year_12=False,
        is_simulated_premise=False,
        objective="Avaliar a capacidade de pagamento das obrigações de curto prazo utilizando o Ativo Circulante.",
        formula="Ativo Circulante / ABS(Passivo Circulante)",
        source="Balanco_Cenarios e KPIs_Cenarios",
        granularity="Cenário × Período (Anos 1 a 11; N/D no Ano 12)",
        periodicity="Anual",
        premises="Aplica-se ABS() ao Passivo Circulante para normalizar a convenção de sinal credor da base CTI.",
        validation_rule="Verificar PC ≠ 0 nos Anos 1–11; recalcular AC / ABS(PC); tratar Ano 12 como N/D.",
        missing_treatment="N/D no Ano 12 ou quando Passivo Circulante = 0.",
        interpretation="LC > 1,00x indica que os ativos realizáveis no curto prazo superam o módulo do passivo circulante.",
        limitations="Não captura o descasamento exato de prazos dentro do ano nem a mudança de sinal contábil de Empréstimos CP nos Anos 5–11.",
    ),
    "ls": KPIMetadata(
        key="ls",
        name="Liquidez Seca (LS)",
        short_name="Liq. Seca",
        category="Liquidez",
        kpis_sheet_col="LS",
        resumo_sheet_col="LS",
        estatisticas_name="Liquidez Seca (LS)",
        unit="x",
        dictionary_raw_unit="x",
        higher_is_better=True,
        available_in_year_12=False,
        is_simulated_premise=False,
        objective="Medir a cobertura do passivo de curto prazo excluindo os estoques (ativos circulantes menos líquidos).",
        formula="(Ativo Circulante − Estoques Diversos) / ABS(Passivo Circulante)",
        source="Balanco_Cenarios e KPIs_Cenarios",
        granularity="Cenário × Período (Anos 1 a 11; N/D no Ano 12)",
        periodicity="Anual",
        premises="Estoques Diversos na base CTI são reduzidos (~R$ 86,6 mil), tornando LS muito próxima de LC.",
        validation_rule="Verificar PC ≠ 0 nos Anos 1–11; recalcular (AC − Estoques) / ABS(PC); N/D no Ano 12.",
        missing_treatment="N/D no Ano 12 ou quando PC = 0.",
        interpretation="Indica a solvência de curto prazo sem depender da realização de estoques.",
        limitations="Inclui 'Outros Créditos' que apresentam saldos redutores negativos em determinados períodos da base CTI.",
    ),
    "li": KPIMetadata(
        key="li",
        name="Liquidez Imediata (LI)",
        short_name="Liq. Imediata",
        category="Liquidez",
        kpis_sheet_col="LI",
        resumo_sheet_col="LI",
        estatisticas_name="Liquidez Imediata (LI)",
        unit="x",
        dictionary_raw_unit="x",
        higher_is_better=True,
        available_in_year_12=False,
        is_simulated_premise=False,
        objective="Mensurar a parcela das obrigações de curto prazo coberta imediatamente pelas disponibilidades de caixa.",
        formula="Disponível / ABS(Passivo Circulante)",
        source="Balanco_Cenarios e KPIs_Cenarios",
        granularity="Cenário × Período (Anos 1 a 11; N/D no Ano 12)",
        periodicity="Anual",
        premises="O campo 'BAL - Disponível' reconcilia exatamente com o 'FLU - Saldo Final' da DFC.",
        validation_rule="Verificar PC ≠ 0 nos Anos 1–11; recalcular Disponível / ABS(PC); N/D no Ano 12.",
        missing_treatment="N/D no Ano 12 ou quando PC = 0.",
        interpretation="Quanto maior, maior o colchão imediato de caixa frente ao passivo circulante.",
        limitations="Liquidez imediata excessivamente alta pode sinalizar caixa ocioso se não remunerado adequadamente.",
    ),
    "lg": KPIMetadata(
        key="lg",
        name="Liquidez Geral (LG)",
        short_name="Liq. Geral",
        category="Liquidez",
        kpis_sheet_col="LG",
        resumo_sheet_col="LG",
        estatisticas_name="Liquidez Geral (LG)",
        unit="x",
        dictionary_raw_unit="x",
        higher_is_better=True,
        available_in_year_12=False,
        is_simulated_premise=False,
        objective="Avaliar a capacidade global de pagamento de curto e longo prazo com ativos circulantes e realizáveis a longo prazo.",
        formula="(Ativo Circulante + Realizável a Longo Prazo) / (ABS(PC) + ABS(Exigível a Longo Prazo))",
        source="Balanco_Cenarios e KPIs_Cenarios",
        granularity="Cenário × Período (Anos 1 a 11; N/D no Ano 12)",
        periodicity="Anual",
        premises="Exclui o Ativo Permanente (imobilizado/intangível de concessão) do numerador, focando em ativos financeiros e créditos.",
        validation_rule="Verificar (ABS(PC) + ABS(PNC)) ≠ 0 nos Anos 1–11; recalcular e reconciliar; N/D no Ano 12.",
        missing_treatment="N/D no Ano 12 ou quando o exigível total for zero.",
        interpretation="Valores abaixo de 1,00x são estruturalmente comuns em concessões intensivas em ativo intangível/imobilizado de longo prazo.",
        limitations="Não considera a geração futura de caixa operacional que amortizará a dívida de longo prazo.",
    ),
    "pct": KPIMetadata(
        key="pct",
        name="Participação de Capital de Terceiros (PCT)",
        short_name="PCT",
        category="Endividamento e Estrutura de Capital",
        kpis_sheet_col="PCT",
        resumo_sheet_col="PCT",
        estatisticas_name="Participação de Capital de Terceiros (PCT)",
        unit="x",
        dictionary_raw_unit="x",
        higher_is_better=False,
        available_in_year_12=False,
        is_simulated_premise=False,
        objective="Relacionar o total de obrigações com terceiros (curto e longo prazo) ao patrimônio líquido implícito.",
        formula="(ABS(PC) + ABS(PNC)) / ABS(Ativo Total − ABS(PC) − ABS(PNC))",
        source="Balanco_Cenarios e KPIs_Cenarios",
        granularity="Cenário × Período (Anos 1 a 11; N/D no Ano 12)",
        periodicity="Anual",
        premises="Segue a fórmula exata de KPIs_Cenarios para manter 100% de paridade com Resumo_Cenarios e Ranking_Cenarios.",
        validation_rule="Verificar denominador ≠ 0 nos Anos 1–11; recalcular e reconciliar; N/D no Ano 12.",
        missing_treatment="N/D no Ano 12 ou quando o denominador for zero.",
        interpretation="Indica quantas vezes o capital de terceiros supera o capital próprio; valores elevados indicam maior alavancagem.",
        limitations="Quando Ativo Total se aproxima de (|PC| + |PNC|), o denominador diminui e gera outliers extremos (até >1.000x em cenários específicos).",
    ),
    "ce": KPIMetadata(
        key="ce",
        name="Composição do Endividamento (CE) – Ajustada",
        short_name="Comp. Endiv.",
        category="Endividamento e Estrutura de Capital",
        kpis_sheet_col="CE",
        resumo_sheet_col="CE",
        estatisticas_name="Composição do Endividamento (CE) – ajustada",
        unit="%",
        dictionary_raw_unit="%",
        higher_is_better=False,
        available_in_year_12=False,
        is_simulated_premise=False,
        objective="Identificar a proporção do endividamento total que vence no curto prazo.",
        formula="ABS(PC) / (ABS(PC) + ABS(PNC))",
        source="Balanco_Cenarios e KPIs_Cenarios",
        granularity="Cenário × Período (Anos 1 a 11; N/D no Ano 12)",
        periodicity="Anual",
        premises="Normaliza passivos em módulo para medir participação relativa entre curto e longo prazo.",
        validation_rule="Verificar (ABS(PC) + ABS(PNC)) ≠ 0 nos Anos 1–11; N/D no Ano 12.",
        missing_treatment="N/D no Ano 12 ou quando exigível total = 0.",
        interpretation="Quanto menor o percentual, mais alongado é o perfil da dívida (menor pressão imediata sobre o caixa).",
        limitations="Sensível à inversão de sinal da conta Empréstimos no Passivo Circulante nos Anos 5–11.",
    ),
    "ipl": KPIMetadata(
        key="ipl",
        name="Imobilização do Patrimônio Líquido (IPL)",
        short_name="Imob. do PL",
        category="Endividamento e Estrutura de Capital",
        kpis_sheet_col="IPL",
        resumo_sheet_col="IPL",
        estatisticas_name="Imobilização do PL (IPL)",
        unit="x",
        dictionary_raw_unit="x",
        higher_is_better=False,
        available_in_year_12=False,
        is_simulated_premise=False,
        objective="Medir quanto do Ativo Não Circulante (RLP + Permanente) é financiado relativamente ao Patrimônio Líquido.",
        formula="(Ativo Total − Ativo Circulante) / ABS(Ativo Total − ABS(PC) − ABS(PNC))",
        source="Balanco_Cenarios e KPIs_Cenarios",
        granularity="Cenário × Período (Anos 1 a 11; N/D no Ano 12)",
        periodicity="Anual",
        premises="Conforme revisão metodológica do modelo, ANC = Ativo Total − Ativo Circulante (incluindo Realizável a Longo Prazo).",
        validation_rule="Verificar denominador ≠ 0 nos Anos 1–11; recalcular ANC / PL_implícito; N/D no Ano 12.",
        missing_treatment="N/D no Ano 12 ou quando o denominador for zero.",
        interpretation="IPL > 1,00x mostra que o capital próprio é insuficiente para financiar todo o ativo não circulante, exigindo dívida de longo prazo.",
        limitations="Assim como o PCT, apresenta valores extremos quando o denominador modular se aproxima de zero.",
    ),
    "endividamento_geral": KPIMetadata(
        key="endividamento_geral",
        name="Endividamento Geral",
        short_name="Endiv. Geral",
        category="Endividamento e Estrutura de Capital",
        kpis_sheet_col="Endividamento Geral",
        resumo_sheet_col="Endiv. Geral",
        estatisticas_name="Endividamento Geral",
        unit="%",
        dictionary_raw_unit="%",
        higher_is_better=False,
        available_in_year_12=False,
        is_simulated_premise=False,
        objective="Relacionar o total de passivos exigíveis em módulo ao Ativo Total.",
        formula="(ABS(PC) + ABS(PNC)) / Ativo Total",
        source="Balanco_Cenarios e KPIs_Cenarios",
        granularity="Cenário × Período (Anos 1 a 11; N/D no Ano 12)",
        periodicity="Anual",
        premises="Indicador complementar de estrutura patrimonial.",
        validation_rule="Verificar Ativo Total ≠ 0 nos Anos 1–11; recalcular (ABS(PC)+ABS(PNC))/Ativo Total; N/D no Ano 12.",
        missing_treatment="N/D no Ano 12 ou quando Ativo Total ≤ 0.",
        interpretation="Expressa o grau de comprometimento dos ativos totais com capital de terceiros.",
        limitations="Pode superar 100% nos períodos em que o Passivo Circulante apresenta saldo contábil positivo na base CTI (ou em caso de passivo a descoberto).",
    ),
    "geracao_caixa": KPIMetadata(
        key="geracao_caixa",
        name="Geração de Caixa (DFC)",
        short_name="Geração Caixa",
        category="Fluxo de Caixa",
        kpis_sheet_col=None,
        resumo_sheet_col=None,
        estatisticas_name=None,
        unit="R$",
        dictionary_raw_unit="R$",
        higher_is_better=True,
        available_in_year_12=True,
        is_simulated_premise=False,
        objective="Acompanhar a variação líquida efetiva de caixa no período (regime de caixa, distinto do lucro contábil).",
        formula="FLU - Saldo Final − FLU - Saldo Inicial (soma dos fluxos operacionais, investimentos, financeiros, IR e dividendos)",
        source="DFC_Cenarios (campo 'FLU - Geração de Caixa')",
        granularity="Cenário × Período (Ano 1 a Ano 12)",
        periodicity="Anual",
        premises="Contempla saídas relevantes de distribuição aos acionistas e amortização/juros financeiros.",
        validation_rule="Verificar que Saldo Inicial + Geração de Caixa = Saldo Final em todos os 14.400 registros.",
        missing_treatment="Exibir N/D se ausente.",
        interpretation="Geração positiva amplia o saldo disponível; geração negativa consome reservas de caixa acumuladas.",
        limitations="Inclui distribuição de dividendos aos acionistas, de modo que geração líquida negativa pode refletir forte remuneração ao acionista (ex.: Ano 12).",
    ),
    "saldo_final_caixa": KPIMetadata(
        key="saldo_final_caixa",
        name="Saldo Final de Caixa",
        short_name="Saldo Caixa",
        category="Fluxo de Caixa",
        kpis_sheet_col=None,
        resumo_sheet_col=None,
        estatisticas_name=None,
        unit="R$",
        dictionary_raw_unit="R$",
        higher_is_better=True,
        available_in_year_12=True,
        is_simulated_premise=False,
        objective="Monitorar a posição acumulada de caixa e equivalentes ao encerramento de cada período.",
        formula="FLU - Saldo Inicial + FLU - Geração de Caixa (= BAL - Disponível)",
        source="DFC_Cenarios ('FLU - Saldo Final') e Balanco_Cenarios ('BAL - Disponível')",
        granularity="Cenário × Período (Ano 1 a Ano 12)",
        periodicity="Anual",
        premises="Reconciliado integralmente entre DFC e Balanço Patrimonial.",
        validation_rule="Verificar igualdade entre 'FLU - Saldo Final' e 'BAL - Disponível'.",
        missing_treatment="Exibir N/D se ausente.",
        interpretation="Representa a reserva financeira efetivamente disponível ao final de cada ano do cenário.",
        limitations="Reflete posição pontual de encerramento do período.",
    ),
    "resultado_liquido": KPIMetadata(
        key="resultado_liquido",
        name="Resultado Líquido (DRE)",
        short_name="Lucro Líquido",
        category="Rentabilidade e Geração de Valor",
        kpis_sheet_col=None,
        resumo_sheet_col=None,
        estatisticas_name=None,
        unit="R$",
        dictionary_raw_unit="R$",
        higher_is_better=True,
        available_in_year_12=True,
        is_simulated_premise=False,
        objective="Medir o resultado contábil final sob regime de competência após tributos, custos, D&A, resultado financeiro e IR/CSLL.",
        formula="Resultado Antes do IR + Imposto de Renda e Contribuição Social",
        source="DRE_Cenarios (campo 'DRE - Resultado Líquido')",
        granularity="Cenário × Período (Ano 1 a Ano 12)",
        periodicity="Anual",
        premises="Regime de competência contábil; não deve ser confundido com a Geração de Caixa da DFC.",
        validation_rule="Verificar reconciliação vertical completa da DRE.",
        missing_treatment="Exibir N/D se ausente.",
        interpretation="Indica o lucro contábil líquido apropriável aos acionistas no exercício.",
        limitations="Difere do fluxo de caixa por efeitos de capital de giro, CAPEX, D&A e distribuição de dividendos.",
    ),
    "cac_simulado": KPIMetadata(
        key="cac_simulado",
        name="CAC Simulado",
        short_name="CAC (Sim.)",
        category="Premissas e Indicadores Simulados",
        kpis_sheet_col=None,
        resumo_sheet_col="CAC simulado (R$/cliente)",
        estatisticas_name="CAC simulado",
        unit="R$/cliente",
        dictionary_raw_unit="R$/cliente",
        higher_is_better=False,
        available_in_year_12=True,
        is_simulated_premise=True,
        objective="Representar o custo médio unitário de aquisição de clientes em simulações comerciais.",
        formula="Investimento em Aquisição / Novos Clientes (Premissa base do modelo: R$ 200,00/cliente)",
        source="Dicionario_KPIs, Resumo_Cenarios e KPIs_Estatisticas (Premissa simulada)",
        granularity="Premissa de Modelo / Simulação",
        periodicity="Por simulação",
        premises="Valor constante de R$ 200,00/cliente definido no modelo de planejamento por ausência de base transacional de marketing/clientes.",
        validation_rule="Garantir Novos Clientes > 0 em simulações; identificar sempre como premissa simulada, nunca dado observado.",
        missing_treatment="Exibir como premissa editável de simulação.",
        interpretation="Quanto menor o CAC frente ao LTV, maior a eficiência teórica do investimento comercial.",
        limitations="Não é um dado empírico observado nas demonstrações contábeis da CTI.",
    ),
    "ltv_simulado": KPIMetadata(
        key="ltv_simulado",
        name="LTV Simulado",
        short_name="LTV (Sim.)",
        category="Premissas e Indicadores Simulados",
        kpis_sheet_col=None,
        resumo_sheet_col="LTV simulado (R$/cliente)",
        estatisticas_name="LTV simulado",
        unit="R$/cliente",
        dictionary_raw_unit="R$/cliente",
        higher_is_better=True,
        available_in_year_12=True,
        is_simulated_premise=True,
        objective="Estimar o valor econômico vitalício gerado por cliente sob premissas parametrizadas.",
        formula="Ticket Médio Simulado × Compras/Ano × Vida Média (anos) × Margem % (Premissa base do modelo: R$ 2.100,00/cliente)",
        source="Dicionario_KPIs, Resumo_Cenarios e KPIs_Estatisticas (Premissa simulada)",
        granularity="Premissa de Modelo / Simulação",
        periodicity="Por simulação",
        premises="Valor de referência de R$ 2.100,00/cliente documentado no modelo de planejamento; recalculável no simulador via premissas explícitas.",
        validation_rule="Verificar fatores > 0; rotular obrigatoriamente como estimativa simulada.",
        missing_treatment="Exibir como premissa simulada editável.",
        interpretation="Estima a contribuição bruta acumulada esperada ao longo do ciclo de retenção de um cliente.",
        limitations="Depende integralmente de hipóteses inseridas pelo analista (ticket, frequência, retenção e margem).",
    ),
    "ltv_cac": KPIMetadata(
        key="ltv_cac",
        name="Relação LTV / CAC (Simulada)",
        short_name="LTV/CAC (Sim.)",
        category="Premissas e Indicadores Simulados",
        kpis_sheet_col=None,
        resumo_sheet_col="LTV/CAC",
        estatisticas_name="LTV/CAC",
        unit="x",
        dictionary_raw_unit="x",
        higher_is_better=True,
        available_in_year_12=True,
        is_simulated_premise=True,
        objective="Relacionar o retorno vitalício estimado por cliente ao seu custo de aquisição sob premissas simuladas.",
        formula="LTV Simulado / CAC Simulado (Premissa base do modelo: 10,50x)",
        source="Dicionario_KPIs, Resumo_Cenarios e KPIs_Estatisticas (Premissa simulada)",
        granularity="Premissa de Modelo / Simulação",
        periodicity="Por simulação",
        premises="Derivado das premissas R$ 2.100,00 / R$ 200,00 = 10,50x do modelo de planejamento.",
        validation_rule="Verificar CAC Simulado > 0 antes da divisão; rotular como indicador simulado.",
        missing_treatment="Retornar N/D caso CAC Simulado ≤ 0.",
        interpretation="Indica quantas vezes o valor gerado pelo cliente cobre seu custo de aquisição no cenário hipotético.",
        limitations="Constante (desvio padrão = 0) na base original por derivar de premissas fixas; ganha variabilidade apenas no módulo de simulação.",
    ),
}

