"""Motor de Análise de Sensibilidade Financeira e Simulação de Unit Economics (Ticket, CAC, LTV).

Garantias de integridade:
- Nenhuma operação altera os DataFrames originais ou a planilha `Contabilidade e Finanças.xlsx`.
- Todos os cálculos ocorrem estritamente em memória sobre cópias isoladas.
- Explicita de forma transparente como descontos, cupons, preço, volume e custos afetam
  Tributos, Custos, Resultado Operacional, EBITDA, NOPAT, ROIC, EVA e Resultado Líquido.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd

from src.config import (
    CAC_SIMULATED_PREMISE,
    LTV_CAC_SIMULATED_PREMISE,
    LTV_SIMULATED_PREMISE,
    WACC_MODEL_PREMISE,
    format_by_unit,
    format_pct_br,
    is_valid_number,
)
from src.financial_kpis import compute_variation, safe_divide


@dataclass(frozen=True)
class SensitivityParams:
    """Parâmetros explícitos para simulação de sensibilidade financeira."""

    desconto_pct: float = 0.0                # Ex.: 0.05 = 5% de desconto comercial sobre o preço/receita
    cupom_preco_pct: float = 0.0             # Ex.: -0.03 = cupom redutor de 3%; +0.04 = reajuste positivo de 4%
    variacao_volume_pct: float = 0.0         # Ex.: +0.10 = +10% em volume físico vendido
    ajuste_receita_adicional_pct: float = 0.0  # Choque adicional direto de receita
    variacao_custos_pct: float = 0.0         # Ex.: +0.08 = +8% de pressão de custos operacionais
    proporcao_custo_variavel: float = 1.0    # Fração de |DRE - Custos| que varia com o volume (1.0 = premissa proxy do modelo)
    tributos_proporcionais_receita: bool = True  # Ajusta DRE - Tributos mantendo a alíquota efetiva sobre a Receita
    wacc_simulado: float = WACC_MODEL_PREMISE  # Custo de capital simulado (padrão 12% do modelo)


@dataclass(frozen=True)
class CustomerSimulationParams:
    """Premissas explícitas para simulação de Ticket Médio, CAC, LTV e LTV/CAC."""

    ticket_medio_simulado: float = 350.0
    compras_por_ano: float = 2.0
    vida_media_anos: float = 3.75
    margem_ltv_pct: float = 0.80             # 350 * 2.0 * 3.75 * 0.80 = R$ 2.100,00 (reproduz a referência do modelo)
    modo_cac: str = "direto"                 # 'direto' ou 'investimento_clientes'
    cac_direto: float = CAC_SIMULATED_PREMISE
    investimento_aquisicao: float = 200_000.0
    novos_clientes: int = 1_000


PRESET_HYPOTHESES: dict[str, SensitivityParams] = {
    "Pessimista (Estresse)": SensitivityParams(
        desconto_pct=0.08,
        cupom_preco_pct=-0.03,
        variacao_volume_pct=-0.06,
        ajuste_receita_adicional_pct=0.0,
        variacao_custos_pct=0.10,
        proporcao_custo_variavel=0.70,
        tributos_proporcionais_receita=True,
        wacc_simulado=0.135,
    ),
    "Realista (Base Original)": SensitivityParams(),
    "Otimista (Expansão & Eficiência)": SensitivityParams(
        desconto_pct=0.02,
        cupom_preco_pct=0.03,
        variacao_volume_pct=0.08,
        ajuste_receita_adicional_pct=0.0,
        variacao_custos_pct=-0.06,
        proporcao_custo_variavel=0.70,
        tributos_proporcionais_receita=True,
        wacc_simulado=0.11,
    ),
}


def run_financial_sensitivity(
    df_selection: pd.DataFrame,
    params: SensitivityParams,
) -> dict[str, Any]:
    """Executa simulação de sensibilidade sobre uma seleção `Cenário × Ano` sem mutar a entrada.

    Mecânica financeira transparente:
    1. Fator Preço Líquido de Descontos/Cupons: `f_preco = (1 - desconto_pct) * (1 + cupom_preco_pct)`
    2. Fator Volume: `f_vol = (1 + variacao_volume_pct)`
    3. Receita Simulada: `Receita_0 * f_preco * f_vol * (1 + ajuste_receita_adicional_pct)`
       (Descontos reduzem receita por unidade sem reduzir o volume físico a produzir!)
    4. Tributos sobre Receita: se `tributos_proporcionais_receita=True`, mantêm a alíquota efetiva
       observada `(Tributos_0 / Receita_0) * Receita_Sim`; caso contrário permanecem fixos.
    5. Custos Operacionais: decompostos pela hipótese configurável `proporcao_custo_variavel` (`p_var`):
       - Parcela fixa `(1 - p_var) * |Custos_0|` sofre apenas o choque de eficiência/inflação `(1 + variacao_custos_pct)`.
       - Parcela variável `p_var * |Custos_0|` responde ao volume `f_vol` e ao choque `(1 + variacao_custos_pct)`.
    6. Resultado Operacional, EBITDA Calculado, EBITDA do Modelo (mantendo o diferencial não operacional
       observado constante, salvo a variação operacional), LAIR, IR/CSLL (pela alíquota efetiva observada quando LAIR > 0),
       Resultado Líquido, NOPAT, ROIC e EVA são integralmente recalculados.
    """
    if df_selection.empty:
        return {
            "simulated_df": pd.DataFrame(),
            "comparison_table": pd.DataFrame(),
            "premises_explanation": [],
            "params": asdict(params),
        }

    sim = df_selection.copy(deep=True)

    f_preco = max(0.0, (1.0 - float(params.desconto_pct)) * (1.0 + float(params.cupom_preco_pct)))
    f_vol = max(0.0, 1.0 + float(params.variacao_volume_pct))
    f_rec_extra = max(0.0, 1.0 + float(params.ajuste_receita_adicional_pct))
    f_receita_total = f_preco * f_vol * f_rec_extra

    p_var = float(np.clip(params.proporcao_custo_variavel, 0.0, 1.0))
    f_custo_unit = max(0.0, 1.0 + float(params.variacao_custos_pct))
    f_custo_total = ((1.0 - p_var) + p_var * f_vol) * f_custo_unit

    rec_0 = sim["DRE - Receita"].abs()
    trib_0 = sim["DRE - Tributos"]  # negativo na DRE
    cust_0_abs = sim["DRE - Custos"].abs()
    da_0_abs = sim["DRE - Depreciação e Amortização"].abs()
    ro_0 = sim["DRE - Resultado Operacional"]
    rf_0 = sim["DRE - Resultado Financeiro"]
    outros_op_0 = sim["DRE - Outros Resultados Operacionais"]
    lair_0 = sim["DRE - Resultado Antes do Imposto de Renda"]
    ir_0 = sim["DRE - Imposto de Renda e Contribuição Social"]
    ebitda_mod_0 = sim["DRE - EBITDA"]

    # Recálculos simulados em memória
    rec_sim = rec_0 * f_receita_total
    if params.tributos_proporcionais_receita:
        aliq_trib = safe_divide(trib_0, rec_0)  # negativo
        trib_sim = rec_sim * aliq_trib
    else:
        trib_sim = trib_0.copy()

    cust_sim_abs = cust_0_abs * f_custo_total
    cust_sim_signed = -cust_sim_abs

    # Variação incremental exata (garante erro de ponto flutuante zero quando choque = 0%)
    delta_rec = rec_sim - rec_0
    delta_trib = trib_sim - trib_0
    delta_cust = cust_sim_signed - (-cust_0_abs)
    delta_ro = delta_rec + delta_trib + delta_cust
    ro_sim = ro_0 + delta_ro

    ebitda_calc_sim = sim["calc_ebitda_calculado"] + delta_ro
    # Ajusta EBITDA do modelo pela mesma variação operacional líquida (preservando os ajustes próprios do modelo)
    ebitda_mod_sim = ebitda_mod_0 + delta_ro

    lair_sim = lair_0 + delta_ro
    aliq_ir_0 = safe_divide(ir_0.abs(), lair_0.abs()).fillna(0.34)
    ir_sim = np.where(
        delta_ro.abs() <= 1e-12,
        ir_0,
        -np.where(lair_sim > 0, lair_sim * aliq_ir_0, 0.0),
    )
    ll_sim = sim["DRE - Resultado Líquido"] + delta_ro + (ir_sim - ir_0)

    rec_liq_sim = rec_sim + trib_sim
    mc_sim = safe_divide(rec_liq_sim - cust_sim_abs, rec_liq_sim)
    mg_ebitda_calc_sim = safe_divide(ebitda_calc_sim, rec_sim)
    mg_ebitda_mod_sim = safe_divide(ebitda_mod_sim, rec_sim)
    mg_liq_sim = safe_divide(ll_sim, rec_sim)

    bal_inc = sim.get("Balanco_Incompleto", pd.Series(False, index=sim.index)).fillna(True)
    cap_inv_0 = sim["calc_capital_investido"]
    nopat_sim = (ro_sim * (1.0 - aliq_ir_0)).where(~bal_inc, np.nan)
    roic_sim = safe_divide(nopat_sim, cap_inv_0).where(~bal_inc, np.nan)
    eva_sim = (nopat_sim - cap_inv_0 * float(params.wacc_simulado)).where(~bal_inc, np.nan)

    sim["sim_receita"] = rec_sim
    sim["sim_tributos"] = trib_sim
    sim["sim_custos_variaveis"] = cust_sim_abs
    sim["sim_resultado_operacional"] = ro_sim
    sim["sim_ebitda_calculado"] = ebitda_calc_sim
    sim["sim_ebitda_modelo"] = ebitda_mod_sim
    sim["sim_margem_contribuicao"] = mc_sim
    sim["sim_margem_ebitda_calculada"] = mg_ebitda_calc_sim
    sim["sim_margem_ebitda_modelo"] = mg_ebitda_mod_sim
    sim["sim_resultado_liquido"] = ll_sim
    sim["sim_margem_liquida"] = mg_liq_sim
    sim["sim_nopat"] = nopat_sim
    sim["sim_roic"] = roic_sim
    sim["sim_eva"] = eva_sim

    # Tabela comparativa consolidada (Média por período válido na seleção)
    metrics_spec = [
        ("Receita Bruta", "calc_receita", "sim_receita", "R$", True),
        ("Tributos sobre Receita (|R$|)", None, None, "R$", False),
        ("Custos Operacionais Proxy", "calc_custos_variaveis", "sim_custos_variaveis", "R$", False),
        ("Margem de Contribuição", "calc_margem_contribuicao", "sim_margem_contribuicao", "%", True),
        ("EBITDA Calculado", "calc_ebitda_calculado", "sim_ebitda_calculado", "R$", True),
        ("Margem EBITDA Calculada", "calc_margem_ebitda_calculada", "sim_margem_ebitda_calculada", "%", True),
        ("EBITDA do Modelo", "calc_ebitda_modelo", "sim_ebitda_modelo", "R$", True),
        ("Margem EBITDA do Modelo", "calc_margem_ebitda_modelo", "sim_margem_ebitda_modelo", "%", True),
        ("Resultado Líquido", "calc_resultado_liquido", "sim_resultado_liquido", "R$", True),
        ("NOPAT (Anos c/ BP completo)", "calc_nopat", "sim_nopat", "R$", True),
        ("ROIC (Anos c/ BP completo)", "calc_roic", "sim_roic", "%", True),
        ("EVA (Anos c/ BP completo)", "calc_eva", "sim_eva", "R$", True),
    ]

    comp_rows = []
    for label, orig_col, sim_col, unit, higher_better in metrics_spec:
        if orig_col is None:
            orig_val = float(trib_0.abs().mean())
            sim_val = float(pd.Series(trib_sim).abs().mean())
        else:
            orig_s = sim[orig_col].dropna()
            sim_s = sim[sim_col].dropna()
            orig_val = float(orig_s.mean()) if not orig_s.empty else np.nan
            sim_val = float(sim_s.mean()) if not sim_s.empty else np.nan

        var = compute_variation(sim_val, orig_val, is_percentage_point_metric=(unit == "%"))
        diff_abs = var["diff_abs"]
        diff_pct = var["diff_pct"]

        if unit == "%" and is_valid_number(diff_abs):
            diff_fmt = f"{format_pct_br(diff_abs, signed=True)} (p.p.)"
        elif is_valid_number(diff_abs):
            sign = "+" if diff_abs > 0 else ""
            diff_fmt = f"{sign}{format_by_unit(diff_abs, unit, compact_currency=False)}"
        else:
            diff_fmt = "N/D"

        var_pct_fmt = format_pct_br(diff_pct, signed=True) if is_valid_number(diff_pct) else "N/D"

        tol_neutral = max(1e-9, abs(orig_val) * 1e-9 if is_valid_number(orig_val) else 1e-9)
        if not is_valid_number(diff_abs) or abs(diff_abs) <= tol_neutral:
            impact = "Neutro"
        else:
            good = (diff_abs > 0) if higher_better else (diff_abs < 0)
            impact = "Favorável" if good else "Desfavorável"

        comp_rows.append({
            "Indicador": label,
            "Unidade": unit,
            "Original (Observado)": orig_val,
            "Simulado (Hipotético)": sim_val,
            "Diferença Absoluta": diff_abs,
            "Variação (%)": diff_pct,
            "Original (Fmt)": format_by_unit(orig_val, unit, compact_currency=False),
            "Simulado (Fmt)": format_by_unit(sim_val, unit, compact_currency=False),
            "Diferença (Fmt)": diff_fmt,
            "Variação % (Fmt)": var_pct_fmt,
            "Impacto": impact,
        })

    explanations = [
        f"Multiplicador combinado sobre a Receita Bruta: {format_pct_br(f_receita_total - 1.0, signed=True)} "
        f"(Desconto: {format_pct_br(-params.desconto_pct, signed=True)}, Cupom/Preço: {format_pct_br(params.cupom_preco_pct, signed=True)}, "
        f"Volume: {format_pct_br(params.variacao_volume_pct, signed=True)}, Ajuste direto: {format_pct_br(params.ajuste_receita_adicional_pct, signed=True)}).",
        (
            "Tributos sobre vendas ajustados proporcionalmente à nova Receita mantendo a alíquota efetiva de cada período."
            if params.tributos_proporcionais_receita
            else "Tributos sobre vendas mantidos fixos nos valores nominais originais (hipótese conservadora)."
        ),
        f"Custos operacionais modelados com {format_pct_br(p_var)} de parcela variável ao volume e {format_pct_br(1.0 - p_var)} "
        f"de parcela fixa, acrescidos do choque de custos de {format_pct_br(params.variacao_custos_pct, signed=True)} "
        f"(multiplicador total de custos: {format_pct_br(f_custo_total - 1.0, signed=True)}).",
        f"Custo de capital (WACC) aplicado no cálculo do EVA simulado: {format_pct_br(params.wacc_simulado)} "
        f"(referência do modelo de planejamento: {format_pct_br(WACC_MODEL_PREMISE)}).",
        "Depreciação/Amortização, Resultado Financeiro e Capital Investido patrimonial mantidos constantes para isolar o efeito operacional.",
    ]

    return {
        "simulated_df": sim,
        "comparison_table": pd.DataFrame(comp_rows),
        "premises_explanation": explanations,
        "multipliers": {
            "f_preco": f_preco,
            "f_vol": f_vol,
            "f_receita_total": f_receita_total,
            "f_custo_total": f_custo_total,
        },
        "params": asdict(params),
    }


def compare_multiple_hypotheses(
    df_selection: pd.DataFrame,
    user_params: SensitivityParams,
) -> pd.DataFrame:
    """Compara lado a lado a Base Original, Cenário Pessimista, Simulação Atual e Cenário Otimista."""
    cases = {
        "Base Observada (Planilha)": SensitivityParams(),
        "Hipótese Pessimista": PRESET_HYPOTHESES["Pessimista (Estresse)"],
        "Sua Simulação Atual": user_params,
        "Hipótese Otimista": PRESET_HYPOTHESES["Otimista (Expansão & Eficiência)"],
    }

    target_indicators = [
        "Receita Bruta",
        "Custos Operacionais Proxy",
        "Margem de Contribuição",
        "EBITDA Calculado",
        "Margem EBITDA Calculada",
        "Margem EBITDA do Modelo",
        "Resultado Líquido",
        "ROIC (Anos c/ BP completo)",
        "EVA (Anos c/ BP completo)",
    ]

    merged_rows: dict[str, dict[str, Any]] = {ind: {"Indicador": ind} for ind in target_indicators}
    for case_name, p in cases.items():
        res = run_financial_sensitivity(df_selection, p)
        tbl = res["comparison_table"].set_index("Indicador")
        for ind in target_indicators:
            if ind in tbl.index:
                merged_rows[ind]["Unidade"] = tbl.loc[ind, "Unidade"]
                merged_rows[ind][case_name] = tbl.loc[ind, "Simulado (Fmt)"]
                merged_rows[ind][f"{case_name}__raw"] = tbl.loc[ind, "Simulado (Hipotético)"]

    return pd.DataFrame(list(merged_rows.values()))


def simulate_customer_unit_economics(params: CustomerSimulationParams) -> dict[str, Any]:
    """Calcula Ticket Médio simulado, CAC simulado, LTV simulado e LTV/CAC conforme fórmulas do Dicionario_KPIs."""
    ticket = max(0.0, float(params.ticket_medio_simulado))
    freq = max(0.0, float(params.compras_por_ano))
    vida = max(0.0, float(params.vida_media_anos))
    margem = float(np.clip(params.margem_ltv_pct, 0.0, 1.0))

    if params.modo_cac == "investimento_clientes":
        cac_sim = safe_divide(max(0.0, float(params.investimento_aquisicao)), max(0, int(params.novos_clientes)))
    else:
        cac_sim = max(0.0, float(params.cac_direto))

    receita_anual_cliente = ticket * freq
    contribuicao_anual_cliente = receita_anual_cliente * margem
    ltv_sim = ticket * freq * vida * margem
    ltv_cac_sim = safe_divide(ltv_sim, cac_sim)
    payback_meses = safe_divide(cac_sim, contribuicao_anual_cliente / 12.0)

    return {
        "is_simulated": True,
        "ticket_medio_simulado": ticket,
        "compras_por_ano": freq,
        "vida_media_anos": vida,
        "margem_ltv_pct": margem,
        "receita_anual_por_cliente": receita_anual_cliente,
        "contribuicao_anual_por_cliente": contribuicao_anual_cliente,
        "cac_simulado": cac_sim,
        "ltv_simulado": ltv_sim,
        "ltv_cac_simulado": ltv_cac_sim,
        "payback_cac_meses": payback_meses,
        "baseline_e1": {
            "cac": CAC_SIMULATED_PREMISE,
            "ltv": LTV_SIMULATED_PREMISE,
            "ltv_cac": LTV_CAC_SIMULATED_PREMISE,
        },
        "diff_vs_e1": {
            "cac_diff": cac_sim - CAC_SIMULATED_PREMISE if is_valid_number(cac_sim) else np.nan,
            "ltv_diff": ltv_sim - LTV_SIMULATED_PREMISE if is_valid_number(ltv_sim) else np.nan,
            "ltv_cac_diff": ltv_cac_sim - LTV_CAC_SIMULATED_PREMISE if is_valid_number(ltv_cac_sim) else np.nan,
        },
    }
