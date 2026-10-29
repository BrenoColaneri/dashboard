"""Testes automatizados do simulador de sensibilidade financeira e Unit Economics (Ticket, CAC, LTV)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.data_processing import ProcessedDataStore, filter_panel
from src.sensitivity_analysis import (
    CustomerSimulationParams,
    SensitivityParams,
    compare_multiple_hypotheses,
    run_financial_sensitivity,
    simulate_customer_unit_economics,
)


def test_zero_shock_reproduces_original_values(real_store: ProcessedDataStore) -> None:
    sub = filter_panel(real_store.panel, scenarios="Cen_00001", period_range=(1, 11))
    res = run_financial_sensitivity(sub, SensitivityParams())
    tbl = res["comparison_table"]
    assert np.allclose(tbl["Diferença Absoluta"].fillna(0.0), 0.0, atol=1e-4)
    assert (tbl["Impacto"] == "Neutro").all()


def test_sensitivity_does_not_mutate_input_dataframe(real_store: ProcessedDataStore) -> None:
    sub = filter_panel(real_store.panel, scenarios="Cen_00001", period_range=(1, 11))
    snapshot = sub.copy(deep=True)

    _ = run_financial_sensitivity(
        sub,
        SensitivityParams(
            desconto_pct=0.10,
            cupom_preco_pct=-0.05,
            variacao_volume_pct=0.15,
            variacao_custos_pct=0.08,
            wacc_simulado=0.14,
        ),
    )
    pd.testing.assert_frame_equal(sub, snapshot)


def test_discount_and_cost_shocks_produce_coherent_economic_directions(real_store: ProcessedDataStore) -> None:
    sub = filter_panel(real_store.panel, scenarios="Cen_00001", period_range=(1, 11))

    # Desconto comercial puro de 10% reduz Receita, EBITDA, Margem EBITDA e ROIC
    res_disc = run_financial_sensitivity(sub, SensitivityParams(desconto_pct=0.10))
    t_disc = res_disc["comparison_table"].set_index("Indicador")
    assert t_disc.loc["Receita Bruta", "Diferença Absoluta"] < 0
    assert t_disc.loc["EBITDA Calculado", "Diferença Absoluta"] < 0
    assert t_disc.loc["Margem EBITDA Calculada", "Diferença Absoluta"] < 0
    assert t_disc.loc["ROIC (Anos c/ BP completo)", "Diferença Absoluta"] < 0

    # Aumento puro de WACC reduz EVA sem alterar NOPAT
    res_wacc = run_financial_sensitivity(sub, SensitivityParams(wacc_simulado=0.16))
    t_wacc = res_wacc["comparison_table"].set_index("Indicador")
    assert abs(t_wacc.loc["NOPAT (Anos c/ BP completo)", "Diferença Absoluta"]) < 1e-6
    assert t_wacc.loc["EVA (Anos c/ BP completo)", "Diferença Absoluta"] < 0


def test_compare_multiple_hypotheses_columns(real_store: ProcessedDataStore) -> None:
    sub = filter_panel(real_store.panel, scenarios="Cen_00001", period_range=(1, 11))
    multi = compare_multiple_hypotheses(sub, SensitivityParams(desconto_pct=0.04, variacao_volume_pct=0.06))
    for expected_col in [
        "Indicador",
        "Base Observada (Planilha)",
        "Hipótese Pessimista",
        "Sua Simulação Atual",
        "Hipótese Otimista",
    ]:
        assert expected_col in multi.columns


def test_customer_unit_economics_simulation_and_zero_protection() -> None:
    # Parâmetros padrão reproduzem exatamente LTV = R$ 2.100, CAC = R$ 200 e LTV/CAC = 10,50x
    base_sim = simulate_customer_unit_economics(CustomerSimulationParams())
    assert np.isclose(base_sim["ltv_simulado"], 2100.0)
    assert np.isclose(base_sim["cac_simulado"], 200.0)
    assert np.isclose(base_sim["ltv_cac_simulado"], 10.5)

    # Modo investimento / novos clientes = 0 não gera ZeroDivisionError
    zero_cli = simulate_customer_unit_economics(
        CustomerSimulationParams(modo_cac="investimento_clientes", investimento_aquisicao=50000.0, novos_clientes=0)
    )
    assert np.isnan(zero_cli["cac_simulado"])
    assert np.isnan(zero_cli["ltv_cac_simulado"])

