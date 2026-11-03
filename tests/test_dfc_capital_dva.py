"""Testes unitários e de integração dos novos módulos: DFC, Capital de Giro, Fluxo de Caixa e DVA.

Verifica conformidade estrita com os exemplos numéricos dos materiais técnicos de referência:
- DFC: Exemplo DataNuvem
- Capital de Giro: Exemplo NuvemDev
- DVA: Exemplo Cia. Exemplo S.A.
- Integração Real: Reconciliação dos 1.200 cenários da base corporativa CTI Global.
"""

from __future__ import annotations

import math
import numpy as np
import pytest

from src.data_processing import ProcessedDataStore
from src.financial_kpis import (
    calculate_dfc_metrics,
    calculate_dva_metrics,
    calculate_working_capital_metrics,
)


def test_dfc_metrics_datanuvem_example() -> None:
    """Valida as fórmulas da DFC usando o caso de teste numérico DataNuvem (Section 27 do prompt)."""
    res = calculate_dfc_metrics(
        fco=1060.0,
        receita=3600.0,
        ebitda=1500.0,
        lucro_liquido=790.0,
        investimentos=350.0,
        depreciacao_amortizacao=250.0,
        juros_pagos=90.0,
        divida_bruta=600.0,
        dividendos_pagos=400.0,
        recebimentos=3540.0,
    )

    # Taxa de conversão: 3.540 / 3.600 = 98,33%
    assert pytest.approx(res["taxa_conversao_receita"], rel=1e-2) == 98.33

    # FCO / EBITDA: 1.060 / 1.500 = 70,67% (~ 70,7%)
    assert pytest.approx(res["fco_ebitda"], rel=1e-2) == 70.67

    # FCO / Lucro: 1.060 / 790 = 1,34x
    assert pytest.approx(res["fco_lucro"], rel=1e-2) == 1.34

    # FCL: 1.060 - 350 = 710
    assert pytest.approx(res["fcl"], rel=1e-4) == 710.0

    # Capex / Receita: 350 / 3.600 = 9,72% (~ 9,7%)
    assert pytest.approx(res["capex_receita"], rel=1e-2) == 9.72

    # Capex / D&A: 350 / 250 = 1,4x
    assert pytest.approx(res["capex_da"], rel=1e-4) == 1.4

    # Cobertura de juros: 1.060 / 90 = 11,78x (~ 11,8x)
    assert pytest.approx(res["cobertura_juros_caixa"], rel=1e-2) == 11.78

    # FCO / Dívida: 1.060 / 600 = 176,67% (~ 177%)
    assert pytest.approx(res["fco_divida_bruta"], rel=1e-2) == 176.67

    # Prazo de quitação: 600 / 1.060 = 0,566 anos (~ 7 meses)
    assert pytest.approx(res["prazo_quitacao_divida"], rel=1e-2) == 0.57

    # Payout em caixa: 400 / 790 = 50,63% (~ 50,6%)
    assert pytest.approx(res["payout_caixa"], rel=1e-2) == 50.63

    # Cobertura de dividendos: 710 / 400 = 1,775x (~ 1,8x)
    assert pytest.approx(res["cobertura_dividendos"], rel=1e-2) == 1.78


def test_working_capital_metrics_nuvemdev_example() -> None:
    """Valida os indicadores de capital de giro usando o caso de teste NuvemDev (Section 27 do prompt)."""
    res = calculate_working_capital_metrics(
        ativo_circulante=1200.0,
        passivo_circulante=950.0,
        contas_receber_clientes=300.0,
        receita_operacional=2160.0,
        fornecedores=120.0,
        custos_operacionais=1440.0,
        ajuste_renegociacao_lp=150.0,
    )

    # Passivo circulante ajustado: 950 - 150 = 800
    assert pytest.approx(res["passivo_circulante_ajustado"], rel=1e-4) == 800.0

    # CCL: 1.200 - 800 = 400
    assert pytest.approx(res["ccl"], rel=1e-4) == 400.0

    # PMR: (300 / 2.160) * 360 = 50 dias
    assert pytest.approx(res["pmr"], rel=1e-4) == 50.0

    # PMP: (120 / 1.440) * 360 = 30 dias
    assert pytest.approx(res["pmp"], rel=1e-4) == 30.0

    # Ciclo Financeiro: 50 - 30 = 20 dias
    assert pytest.approx(res["ciclo_financeiro"], rel=1e-4) == 20.0

    # Necessidade Estimada de Capital de Giro: 20 * (1.440 / 360) = 80
    assert pytest.approx(res["necessidade_capital_giro"], rel=1e-4) == 80.0

    # Folga sobre CCL: 400 - 80 = 320
    assert pytest.approx(res["folga_ccl"], rel=1e-4) == 320.0


def test_dva_metrics_cia_exemplo_sa() -> None:
    """Valida a DVA e suas 5 conferências usando o caso de teste Cia. Exemplo S.A. (Section 27 do prompt)."""
    res = calculate_dva_metrics(
        receitas=975000.0,
        insumos_terceiros=430000.0,
        retencoes_da=20000.0,
        transferencias=27000.0,
        pessoal=118000.0,
        impostos=264000.0,
        capitais_terceiros=54000.0,
        capitais_proprios=116000.0,
        lucros_retidos=66000.0,
        num_empregados=8,
    )

    # Validação 1: VA Bruto = 975.000 - 430.000 = 545.000
    assert pytest.approx(res["dva_va_bruto"], rel=1e-4) == 545000.0

    # Validação 2: VA Líquido = 545.000 - 20.000 = 525.000
    assert pytest.approx(res["dva_va_liquido"], rel=1e-4) == 525000.0

    # Validação 3: VA Total = 525.000 + 27.000 = 552.000
    assert pytest.approx(res["dva_va_total"], rel=1e-4) == 552000.0

    # Validação 4: Total Distribuído = 118.000 + 264.000 + 54.000 + 116.000 = 552.000
    assert pytest.approx(res["total_distribuido"], rel=1e-4) == 552000.0
    assert pytest.approx(res["conciliacao_dva_diff"], abs=1e-4) == 0.0

    # Grau de Geração de Riqueza: 552.000 / 975.000 = 56,615% (~ 56,6%)
    assert pytest.approx(res["dva_grau_riqueza"], rel=1e-2) == 56.62

    # Participação do Governo: 264.000 / 552.000 = 47,826% (~ 47,8%)
    assert pytest.approx(res["dva_part_governo"], rel=1e-2) == 47.83

    # Participação dos Empregados: 118.000 / 552.000 = 21,376% (~ 21,4%)
    assert pytest.approx(res["dva_part_pessoal"], rel=1e-2) == 21.38

    # Participação de Capitais de Terceiros: 54.000 / 552.000 = 9,782% (~ 9,8%)
    assert pytest.approx(res["dva_part_terceiros"], rel=1e-2) == 9.78

    # Participação de Capitais Próprios: 116.000 / 552.000 = 21,014% (~ 21,0%)
    assert pytest.approx(res["dva_part_proprios"], rel=1e-2) == 21.01

    # Riqueza Recebida em Transferência: 27.000 / 552.000 = 4,891% (~ 4,9%)
    assert pytest.approx(res["dva_part_transferencias"], rel=1e-2) == 4.89

    # Retenção de Riqueza: 66.000 / 552.000 = 11,956% (~ 12,0%)
    assert pytest.approx(res["dva_retencao_riqueza"], rel=1e-2) == 11.96

    # Valor Adicionado por Empregado: 552.000 / 8 = R$ 69.000
    assert pytest.approx(res["dva_va_por_empregado"], rel=1e-4) == 69000.0


def test_real_dataset_dva_and_cash_flow_reconciliation(real_store: ProcessedDataStore) -> None:
    """Verifica a consistência e a conciliação das demonstrações no painel integrado dos 1.200 cenários."""
    p = real_store.panel

    # 1. Conciliação matemática obrigatória da DVA (VA Total == Total Distribuído)
    dva_diff_max = p["calc_dva_conciliacao_diff"].max()
    assert dva_diff_max < 1e-2, f"Erro máximo de conciliação DVA: {dva_diff_max}"

    # 2. Conciliação matemática do Fluxo de Caixa (Saldo Inicial + Geração == Saldo Final)
    cash_diff_max = p["calc_conciliacao_caixa_diff"].max()
    assert cash_diff_max < 1e-2, f"Erro máximo de conciliação Caixa: {cash_diff_max}"

    # 3. Geração após Investimentos, Juros e Dividendos == Geração de Caixa da DFC
    # FLU - Geração de Caixa = FCL - Juros Líquidos - Dividendos
    geracao_liquida_diff = (p["calc_geracao_apos_juros_div"] - p["FLU - Geração de Caixa"]).abs().max()
    assert geracao_liquida_diff < 1e-2, f"Erro na ponte de geração líquida de caixa: {geracao_liquida_diff}"

    # 4. Tratamento de Ano 12: Indicadores patrimoniais devem ser NaN, indicadores de fluxo válidos
    p12 = p[p["Ano"] == 12]
    assert p12["calc_ccl"].isna().all()
    assert p12["calc_pmr"].isna().all()
    assert p12["calc_pmp"].isna().all()
    assert p12["calc_ciclo_financeiro"].isna().all()
    assert p12["calc_fco_divida_bruta"].isna().all()

    # DFC e DVA continuam válidos no Ano 12 pois derivam de DRE e DFC
    assert p12["calc_fco"].notna().all()
    assert p12["calc_fcl"].notna().all()
    assert p12["calc_dva_va_total"].notna().all()
    assert p12["calc_dva_grau_riqueza"].notna().all()
