"""Testes de confiabilidade financeira, reconciliação com a planilha, denominadores zero, Ano 12 e metas."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import (
    KPI_CATALOG,
    format_currency_brl,
    format_multiple_br,
    format_pct_br,
    format_period_label,
)
from src.data_processing import ProcessedDataStore
from src.data_validation import ValidationSummary
from src.financial_kpis import (
    evaluate_all_goals,
    evaluate_goal,
    investigate_ticket_medio,
    safe_divide,
)


def test_100_percent_reconciliation_with_kpis_cenarios(real_validation: ValidationSummary) -> None:
    rec = real_validation.kpi_reconciliation
    assert len(rec) == 19
    assert (rec["Status"] == "Reconciliado (100%)").all(), f"Divergências: {rec[rec['Status'] != 'Reconciliado (100%)']}"
    assert (rec["Divergência N/D"] == 0).all()


def test_100_percent_reconciliation_with_resumo_cenarios(real_validation: ValidationSummary) -> None:
    res_rec = real_validation.resumo_reconciliation
    assert len(res_rec) == 19
    assert (res_rec["Status"] == "Reconciliado (100%)").all()


def test_year_12_incomplete_balance_returns_nan_for_patrimonial_kpis(real_store: ProcessedDataStore) -> None:
    p12 = real_store.panel[real_store.panel["Ano"] == 12]
    assert len(p12) == 1200
    assert p12["Balanco_Incompleto"].all()

    patrimonial_keys = [
        "lc", "ls", "li", "lg", "pct", "ce", "ipl", "endividamento_geral",
        "nopat", "capital_investido", "eva", "roic",
    ]
    for k in patrimonial_keys:
        assert p12[f"calc_{k}"].isna().all(), f"KPI {k} deveria ser NaN (N/D) no Ano 12"

    dre_dfc_keys = [
        "receita", "custos_variaveis", "margem_contribuicao",
        "ebitda_calculado", "ebitda_modelo", "margem_ebitda_calculada",
        "margem_ebitda_modelo", "geracao_caixa", "saldo_final_caixa",
    ]
    for k in dre_dfc_keys:
        assert p12[f"calc_{k}"].notna().all(), f"KPI {k} deveria estar disponível no Ano 12"


def test_ebitda_calculado_and_ebitda_modelo_are_kept_distinct(real_store: ProcessedDataStore) -> None:
    p = real_store.panel
    diff = (p["calc_ebitda_modelo"] - p["calc_ebitda_calculado"]).abs()
    assert (diff > 1e6).all(), "EBITDA calculado e EBITDA do modelo possuem definições distintas na base CTI"


def test_dfc_cash_reconciliation_with_balance_sheet(real_store: ProcessedDataStore) -> None:
    p = real_store.panel
    cash_identity_err = (
        p["FLU - Saldo Inicial"] + p["FLU - Geração de Caixa"] - p["FLU - Saldo Final"]
    ).abs().max()
    assert cash_identity_err < 1e-3

    bal_disp_err = (p["FLU - Saldo Final"] - p["BAL - Disponível"]).abs().max()
    assert bal_disp_err < 1e-3


def test_safe_divide_handles_zero_and_nan_denominators() -> None:
    assert np.isnan(safe_divide(100.0, 0.0))
    assert np.isnan(safe_divide(100.0, np.nan))
    assert np.isnan(safe_divide(None, 5.0))
    assert safe_divide(150.0, 50.0) == 3.0

    s_num = pd.Series([10.0, 20.0, 30.0])
    s_den = pd.Series([2.0, 0.0, np.nan])
    out = safe_divide(s_num, s_den)
    assert out.iloc[0] == 5.0
    assert np.isnan(out.iloc[1])
    assert np.isnan(out.iloc[2])


def test_goal_evaluation_undefined_floor_and_ceiling() -> None:
    # Meta não definida nunca inventa alvo oficial
    ev_undef = evaluate_goal("roic", 0.25, None)
    assert ev_undef.status == "Meta Não Definida"
    assert ev_undef.is_favorable is None

    # Meta do tipo piso (maior é melhor -> ROIC)
    ev_above = evaluate_goal("roic", 0.28, 0.25)
    assert ev_above.status == "Acima da Meta"
    assert ev_above.is_favorable is True

    ev_below = evaluate_goal("roic", 0.15, 0.25)
    assert ev_below.status == "Abaixo da Meta"
    assert ev_below.is_favorable is False

    # Meta do tipo teto (menor é melhor -> Endividamento Geral)
    ev_ceil_ok = evaluate_goal("endividamento_geral", 0.70, 0.85)
    assert ev_ceil_ok.is_favorable is True

    ev_ceil_bad = evaluate_goal("endividamento_geral", 0.95, 0.85)
    assert ev_ceil_bad.is_favorable is False

    tbl = evaluate_all_goals({"roic": 0.28, "lc": np.nan}, {"roic": 0.25, "lc": 1.2})
    assert len(tbl) == len([k for k in KPI_CATALOG if not KPI_CATALOG[k].is_simulated_premise])


def test_ticket_medio_audit_and_pt_br_formatters(real_store: ProcessedDataStore) -> None:
    tm = investigate_ticket_medio(real_store.bundle.sheets)
    assert tm["can_calculate_real_ticket"] is False
    assert "N/D" in tm["status_label"]

    assert format_currency_brl(1234.56) == "R$ 1.234,56"
    assert format_currency_brl(np.nan) == "N/D"
    assert format_pct_br(0.798) == "79,80%"
    assert format_multiple_br(1.25) == "1,25x"
    assert format_period_label(12) == "Ano 12"

