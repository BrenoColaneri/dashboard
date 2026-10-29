"""Testes de filtros, estatística, regressão com split por cenário e exportações CSV/XLSX/PDF."""

from __future__ import annotations

import io

import pandas as pd

from src.data_processing import ProcessedDataStore, filter_panel
from src.regression_analysis import detect_algebraic_leakage, fit_ols_regression
from src.reporting import (
    build_excel_report_bytes,
    build_pdf_executive_report,
    dataframe_to_csv_bytes,
)
from src.statistical_analysis import (
    compute_correlation_matrix,
    validate_against_kpis_estatisticas,
)


def test_filter_panel_by_scenario_periods_and_empty_combinations(real_store: ProcessedDataStore) -> None:
    # Cenário único, Anos 1..11
    f1 = filter_panel(real_store.panel, scenarios="Cen_00010", period_range=(1, 11))
    assert len(f1) == 11
    assert set(f1["Cenário"].unique()) == {"Cen_00010"}
    assert f1["Ano"].min() == 1 and f1["Ano"].max() == 11

    # Múltiplos cenários e exclusão de balanço incompleto
    f2 = filter_panel(
        real_store.panel,
        scenarios=["Cen_00001", "Cen_00002", "Cen_00003"],
        period_range=(1, 12),
        exclude_incomplete_balance=True,
    )
    assert len(f2) == 3 * 11
    assert 12 not in set(f2["Ano"].unique())

    # Combinações vazias retornam DataFrame vazio sem erro
    f_empty_scen = filter_panel(real_store.panel, scenarios=[])
    assert f_empty_scen.empty

    f_empty_code = filter_panel(real_store.panel, scenarios="CENARIO_INEXISTENTE")
    assert f_empty_code.empty


def test_kpis_estatisticas_100_percent_validation(real_store: ProcessedDataStore) -> None:
    est_val = validate_against_kpis_estatisticas(real_store)
    assert len(est_val) == 22
    assert (est_val["Status"] == "Validado (100%)").all()


def test_correlation_matrix_excludes_constants_cleanly(real_store: ProcessedDataStore) -> None:
    cols_map = {
        "ROIC": "ROIC",
        "LC": "LC",
        "Endiv. Geral": "Endiv. Geral",
        "CAC simulado (R$/cliente)": "CAC",  # constante = 200 -> deve ser excluída automaticamente
    }
    corr_df, pval_df = compute_correlation_matrix(real_store.resumo, cols_map, method="pearson")
    assert list(corr_df.columns) == ["ROIC", "LC", "Endiv. Geral"]
    assert not corr_df.isna().any().any()
    assert corr_df.shape == pval_df.shape


def test_ols_regression_panel_split_has_zero_scenario_overlap(real_store: ProcessedDataStore) -> None:
    sub = filter_panel(real_store.panel, scenarios=real_store.scenarios[:120], period_range=(1, 11))
    res = fit_ols_regression(
        df=sub,
        target_col="kpi_roic",
        feature_cols=["kpi_margem_contribuicao", "kpi_lc", "kpi_ce"],
        labels_map={
            "kpi_roic": "ROIC",
            "kpi_margem_contribuicao": "Margem Contrib.",
            "kpi_lc": "LC",
            "kpi_ce": "CE",
        },
        target_key="roic",
        feature_keys=["margem_contribuicao", "lc", "ce"],
        granularity="panel",
        test_size=0.25,
    )
    assert res.success is True
    preds = res.predictions_df
    train_scens = set(preds[preds["Partição"] == "Treinamento"]["Cenário"].unique())
    test_scens = set(preds[preds["Partição"] == "Teste (Cenários Isolados)"]["Cenário"].unique())
    assert len(train_scens) > 0 and len(test_scens) > 0
    assert train_scens.isdisjoint(test_scens), "Vazamento detectado: cenários em comum entre treino e teste!"


def test_algebraic_leakage_detector() -> None:
    warns = detect_algebraic_leakage("eva", ["nopat", "capital_investido", "lc"])
    assert len(warns) == 1
    assert "tautologia" in warns[0]

    clean_warns = detect_algebraic_leakage("roic", ["margem_contribuicao", "lc"])
    assert clean_warns == []


def test_csv_xlsx_and_pdf_exports_are_valid(real_store: ProcessedDataStore) -> None:
    sub = filter_panel(real_store.panel, scenarios="Cen_00001", period_range=(1, 5))

    csv_b = dataframe_to_csv_bytes(sub[["Cenário", "Período", "kpi_receita"]])
    assert csv_b.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM

    xlsx_b = build_excel_report_bytes({"Painel": sub[["Cenário", "Período", "kpi_receita"]]}, {"Cenário": "Cen_00001"})
    xl = pd.ExcelFile(io.BytesIO(xlsx_b), engine="openpyxl")
    assert "Metadados_e_Premissas" in xl.sheet_names
    assert "Painel" in xl.sheet_names

    pdf_b = build_pdf_executive_report(
        scenario_code="Cen_00001",
        period_label="Ano 1 a Ano 5",
        source_name=real_store.bundle.source_name,
        is_synthetic=False,
        kpi_summary_rows=[{"Indicador": "Receita", "Media": "R$ 6,95 bi", "Ultimo": "R$ 7,45 bi", "Mediana_Base": "R$ 6,90 bi"}],
    )
    assert pdf_b.startswith(b"%PDF-")
    assert len(pdf_b) > 1500

