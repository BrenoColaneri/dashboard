"""Motor de cálculo financeiro, validação de denominadores, metas e investigação de ticket médio.

Todas as fórmulas implementadas seguem estritamente o modelo de planejamento (`KPIs_Cenarios` e `Dicionario_KPIs`),
protegendo contra divisões por zero e tratando a incompletude do Balanço Patrimonial no Ano 12 com `NaN` (`N/D`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from src.config import (
    CAC_SIMULATED_PREMISE,
    KPI_CATALOG,
    LTV_CAC_SIMULATED_PREMISE,
    LTV_SIMULATED_PREMISE,
    WACC_MODEL_PREMISE,
    format_by_unit,
    format_pct_br,
    is_valid_number,
)


def safe_divide(
    numerator: pd.Series | np.ndarray | float,
    denominator: pd.Series | np.ndarray | float,
    tol: float = 1e-12,
) -> pd.Series | float:
    """Realiza divisão segura retornando `np.nan` quando o denominador é nulo ou próximo de zero."""
    if isinstance(numerator, pd.Series) or isinstance(denominator, pd.Series):
        num_s = pd.Series(numerator, dtype="float64")
        den_s = pd.Series(denominator, index=num_s.index, dtype="float64") if not isinstance(denominator, pd.Series) else denominator.astype("float64")
        valid = num_s.notna() & den_s.notna() & (den_s.abs() > tol)
        out = pd.Series(np.nan, index=num_s.index, dtype="float64")
        out.loc[valid] = num_s.loc[valid] / den_s.loc[valid]
        return out

    if numerator is None or denominator is None:
        return np.nan
    try:
        n_val = float(numerator)
        d_val = float(denominator)
    except (TypeError, ValueError):
        return np.nan
    if np.isnan(n_val) or np.isnan(d_val) or abs(d_val) <= tol:
        return np.nan
    return n_val / d_val


def compute_variation(
    current_val: Any,
    reference_val: Any,
    is_percentage_point_metric: bool = False,
) -> dict[str, float]:
    """Calcula diferença absoluta e variação percentual quando matematicamente aplicável."""
    if not (is_valid_number(current_val) and is_valid_number(reference_val)):
        return {"diff_abs": np.nan, "diff_pct": np.nan}

    curr = float(current_val)
    ref = float(reference_val)
    diff_abs = curr - ref

    # Variação percentual só é matematicamente coerente quando a base é estritamente positiva
    if abs(ref) <= 1e-12 or ref < 0:
        diff_pct = np.nan
    else:
        diff_pct = (curr - ref) / abs(ref)

    return {
        "diff_abs": diff_abs,
        "diff_pct": diff_pct,
        "diff_pp": diff_abs * 100.0 if is_percentage_point_metric else np.nan,
    }



def calculate_dfc_metrics(
    fco: float,
    receita: float,
    ebitda: float,
    lucro_liquido: float,
    investimentos: float,
    depreciacao_amortizacao: float,
    juros_pagos: float,
    divida_bruta: float,
    dividendos_pagos: float,
    recebimentos: float | None = None,
) -> dict[str, float]:
    """Calcula os 11 KPIs da DFC a partir de valores escalares para testes unitários e auditoria."""
    rec_val = abs(receita) if is_valid_number(receita) else np.nan
    rec_pagos = recebimentos if is_valid_number(recebimentos) else (fco if is_valid_number(fco) else np.nan)

    taxa_conv = (safe_divide(rec_pagos, rec_val) * 100.0) if is_valid_number(recebimentos) else np.nan
    fco_ebitda = safe_divide(fco, ebitda) * 100.0
    fco_lucro = safe_divide(fco, lucro_liquido)
    fcl = fco - abs(investimentos) if is_valid_number(fco) and is_valid_number(investimentos) else np.nan
    capex_rec = safe_divide(abs(investimentos), rec_val) * 100.0
    capex_da = safe_divide(abs(investimentos), abs(depreciacao_amortizacao))
    cob_juros = safe_divide(fco, abs(juros_pagos))
    fco_div = safe_divide(fco, abs(divida_bruta)) * 100.0
    prazo_quitacao = safe_divide(abs(divida_bruta), fco)
    payout = safe_divide(abs(dividendos_pagos), lucro_liquido) * 100.0
    cob_div = safe_divide(fcl, abs(dividendos_pagos))

    return {
        "fco": fco,
        "taxa_conversao_receita": taxa_conv,
        "fco_ebitda": fco_ebitda,
        "fco_lucro": fco_lucro,
        "fcl": fcl,
        "capex_receita": capex_rec,
        "capex_da": capex_da,
        "cobertura_juros_caixa": cob_juros,
        "fco_divida_bruta": fco_div,
        "prazo_quitacao_divida": prazo_quitacao,
        "payout_caixa": payout,
        "cobertura_dividendos": cob_div,
    }


def calculate_working_capital_metrics(
    ativo_circulante: float,
    passivo_circulante: float,
    contas_receber_clientes: float,
    receita_operacional: float,
    fornecedores: float,
    custos_operacionais: float,
    ajuste_renegociacao_lp: float = 0.0,
) -> dict[str, float]:
    """Calcula os indicadores de capital de giro e prazos médios a partir de valores escalares."""
    pc_ajustado = abs(passivo_circulante) - abs(ajuste_renegociacao_lp)
    ccl = ativo_circulante - pc_ajustado
    pmr = safe_divide(contas_receber_clientes, abs(receita_operacional)) * 360.0
    pmp = safe_divide(abs(fornecedores), abs(custos_operacionais)) * 360.0
    ciclo = pmr - pmp if is_valid_number(pmr) and is_valid_number(pmp) else np.nan
    custo_diario = safe_divide(abs(custos_operacionais), 360.0)
    ncg = ciclo * custo_diario if is_valid_number(ciclo) and is_valid_number(custo_diario) else np.nan
    folga = ccl - ncg if is_valid_number(ccl) and is_valid_number(ncg) else np.nan

    return {
        "passivo_circulante_ajustado": pc_ajustado,
        "ccl": ccl,
        "pmr": pmr,
        "pmp": pmp,
        "ciclo_financeiro": ciclo,
        "necessidade_capital_giro": ncg,
        "folga_ccl": folga,
    }


def calculate_dva_metrics(
    receitas: float,
    insumos_terceiros: float,
    retencoes_da: float,
    transferencias: float,
    pessoal: float,
    impostos: float,
    capitais_terceiros: float,
    capitais_proprios: float,
    lucros_retidos: float | None = None,
    num_empregados: float | None = None,
) -> dict[str, float]:
    """Calcula a demonstração do valor adicionado e validações a partir de valores escalares."""
    va_bruto = receitas - insumos_terceiros
    va_liquido = va_bruto - retencoes_da
    va_total = va_liquido + transferencias
    total_distribuido = pessoal + impostos + capitais_terceiros + capitais_proprios
    conciliacao_diff = abs(va_total - total_distribuido)

    grau_riqueza = safe_divide(va_total, receitas) * 100.0
    part_governo = safe_divide(impostos, va_total) * 100.0
    part_pessoal = safe_divide(pessoal, va_total) * 100.0
    part_terceiros = safe_divide(capitais_terceiros, va_total) * 100.0
    part_proprios = safe_divide(capitais_proprios, va_total) * 100.0
    part_transferencias = safe_divide(transferencias, va_total) * 100.0
    retencao_riqueza = safe_divide(lucros_retidos, va_total) * 100.0 if lucros_retidos is not None else np.nan
    va_por_empregado = safe_divide(va_total, num_empregados) if num_empregados is not None else np.nan

    return {
        "dva_va_bruto": va_bruto,
        "dva_va_liquido": va_liquido,
        "dva_va_total": va_total,
        "total_distribuido": total_distribuido,
        "conciliacao_dva_diff": conciliacao_diff,
        "dva_grau_riqueza": grau_riqueza,
        "dva_part_governo": part_governo,
        "dva_part_pessoal": part_pessoal,
        "dva_part_terceiros": part_terceiros,
        "dva_part_proprios": part_proprios,
        "dva_part_transferencias": part_transferencias,
        "dva_retencao_riqueza": retencao_riqueza,
        "dva_va_por_empregado": va_por_empregado,
    }


def compute_recalculated_kpis(panel: pd.DataFrame, wacc: float = WACC_MODEL_PREMISE) -> pd.DataFrame:
    """Recalcula todos os KPIs a partir de DRE, Balanço e DFC e cria colunas canônicas `kpi_*` e `calc_*`."""
    df = panel.copy()

    # --- Campos base DRE ---
    rec_raw = df.get("DRE - Receita", pd.Series(np.nan, index=df.index))
    trib = df.get("DRE - Tributos", pd.Series(np.nan, index=df.index))
    cust = df.get("DRE - Custos", pd.Series(np.nan, index=df.index))
    da = df.get("DRE - Depreciação e Amortização", pd.Series(np.nan, index=df.index))
    ro = df.get("DRE - Resultado Operacional", pd.Series(np.nan, index=df.index))
    lair = df.get("DRE - Resultado Antes do Imposto de Renda", pd.Series(np.nan, index=df.index))
    ir_csll = df.get("DRE - Imposto de Renda e Contribuição Social", pd.Series(np.nan, index=df.index))
    ll = df.get("DRE - Resultado Líquido", pd.Series(np.nan, index=df.index))
    ebitda_mod_dre = df.get("DRE - EBITDA", pd.Series(np.nan, index=df.index))

    rec_abs = rec_raw.abs()
    cust_abs = cust.abs()
    da_abs = da.abs()

    df["calc_receita"] = rec_abs
    df["calc_custos_variaveis"] = cust_abs
    rec_liquida_proxy = rec_abs + trib
    df["calc_receita_liquida"] = rec_liquida_proxy
    df["calc_margem_contribuicao"] = safe_divide(rec_liquida_proxy - cust_abs, rec_liquida_proxy)

    df["calc_ebitda_calculado"] = ro + da_abs
    df["calc_ebitda_modelo"] = ebitda_mod_dre
    df["calc_margem_ebitda_calculada"] = safe_divide(df["calc_ebitda_calculado"], rec_abs)
    df["calc_margem_ebitda_modelo"] = safe_divide(ebitda_mod_dre, rec_abs)
    df["calc_resultado_liquido"] = ll
    df["calc_margem_liquida"] = safe_divide(ll, rec_abs)

    # --- Campos base Balanço Patrimonial ---
    at = df.get("BAL - Total do Ativo", pd.Series(np.nan, index=df.index))
    ac = df.get("BAL - Ativo Circulante", pd.Series(np.nan, index=df.index))
    disp = df.get("BAL - Disponível", pd.Series(np.nan, index=df.index))
    est = df.get("BAL - Estoques Diversos", pd.Series(np.nan, index=df.index))
    rlp = df.get("BAL - Realizável a Longo Prazo", pd.Series(np.nan, index=df.index))
    pc = df.get("BAL - Passivo Circulante", pd.Series(np.nan, index=df.index))
    pnc = df.get("BAL - Exigível a Longo Prazo", pd.Series(np.nan, index=df.index))
    pl_direto = df.get("BAL - Patrimônio Líquido", pd.Series(np.nan, index=df.index))

    bal_incompleto = df.get("Balanco_Incompleto", pd.Series(False, index=df.index)).fillna(True)

    pc_abs = pc.abs()
    pnc_abs = pnc.abs()
    exigivel_total = pc_abs + pnc_abs
    pl_implicito_e1 = (at - pc_abs - pnc_abs).abs()
    anc = at - ac

    # Liquidez (mascarando períodos com balanço incompleto -> NaN / N/D)
    lc = safe_divide(ac, pc_abs).where(~bal_incompleto, np.nan)
    ls = safe_divide(ac - est, pc_abs).where(~bal_incompleto, np.nan)
    li = safe_divide(disp, pc_abs).where(~bal_incompleto, np.nan)
    lg = safe_divide(ac + rlp, exigivel_total).where(~bal_incompleto, np.nan)

    # Endividamento e Estrutura de Capital (fórmula exata da planilha KPIs_Cenarios)
    pct = safe_divide(exigivel_total, pl_implicito_e1).where(~bal_incompleto, np.nan)
    ce = safe_divide(pc_abs, exigivel_total).where(~bal_incompleto, np.nan)
    ipl = safe_divide(anc, pl_implicito_e1).where(~bal_incompleto, np.nan)
    endiv_geral = safe_divide(exigivel_total, at).where(~bal_incompleto, np.nan)

    # NOPAT, Capital Investido, EVA e ROIC (N/D quando Balanço está incompleto no Ano 12, conforme planilha)
    aliq_efetiva = safe_divide(ir_csll.abs(), lair.abs())
    nopat = (ro * (1.0 - aliq_efetiva)).where(~bal_incompleto, np.nan)
    cap_inv = (pc_abs + pnc_abs + pl_implicito_e1).where(~bal_incompleto, np.nan)
    eva = (nopat - cap_inv * float(wacc)).where(~bal_incompleto, np.nan)
    roic = safe_divide(nopat, cap_inv).where(~bal_incompleto, np.nan)

    df["calc_lc"] = lc
    df["calc_ls"] = ls
    df["calc_li"] = li
    df["calc_lg"] = lg
    df["calc_pct"] = pct
    df["calc_ce"] = ce
    df["calc_ipl"] = ipl
    df["calc_endividamento_geral"] = endiv_geral
    df["calc_aliquota_efetiva_ir"] = aliq_efetiva
    df["calc_nopat"] = nopat
    df["calc_capital_investido"] = cap_inv
    df["calc_eva"] = eva
    df["calc_roic"] = roic

    # Variantes alternativas usando |BAL - Patrimônio Líquido| direto exclusivamente para auditoria metodológica
    pl_dir_abs = pl_direto.abs()
    df["audit_pct_pl_direto"] = safe_divide(exigivel_total, pl_dir_abs).where(~bal_incompleto, np.nan)
    df["audit_ipl_pl_direto"] = safe_divide(anc, pl_dir_abs).where(~bal_incompleto, np.nan)
    df["audit_cap_inv_pl_direto"] = (pc_abs + pnc_abs + pl_dir_abs).where(~bal_incompleto, np.nan)

    # --- Fluxo de Caixa (DFC) ---
    df["calc_geracao_caixa"] = df.get("FLU - Geração de Caixa", pd.Series(np.nan, index=df.index))
    df["calc_saldo_final_caixa"] = df.get("FLU - Saldo Final", pd.Series(np.nan, index=df.index))

    # -------------------------------------------------------------------------
    # MÓDULO 1 — ÍNDICES DA DFC (VETORIZADO)
    # -------------------------------------------------------------------------
    flu_rec = df.get("FLU - Receita", pd.Series(np.nan, index=df.index)).abs()
    flu_trib = df.get("FLU - Tributos", pd.Series(np.nan, index=df.index)).abs()
    flu_cust = df.get("FLU - Custos", pd.Series(np.nan, index=df.index)).abs()
    flu_ircs = df.get("FLU - Imposto de Renda e Contribuição Social", pd.Series(np.nan, index=df.index)).abs()
    flu_inv = df.get("FLU - Investimentos", pd.Series(np.nan, index=df.index)).abs()
    flu_desp_fin = df.get("FLU - Despesas Financeiras", pd.Series(np.nan, index=df.index)).abs()
    flu_entradas = df.get("FLU - Entradas", pd.Series(np.nan, index=df.index)).abs()
    flu_dist_acionista = df.get("FLU - Distribuição para Acionista", pd.Series(np.nan, index=df.index)).abs()
    flu_saldo_ini = df.get("FLU - Saldo Inicial", pd.Series(np.nan, index=df.index))
    flu_saldo_fim = df.get("FLU - Saldo Final", pd.Series(np.nan, index=df.index))
    flu_geracao_caixa = df.get("FLU - Geração de Caixa", pd.Series(np.nan, index=df.index))

    # FCO: Recebimentos − Tributos − Custos − IR/CSLL
    fco = flu_rec - flu_trib - flu_cust - flu_ircs
    df["calc_fco"] = fco
    df["calc_fco_fluxo"] = fco
    df["calc_taxa_conversao_receita"] = safe_divide(flu_rec, rec_abs) * 100.0

    # FCO / EBITDA
    ebitda_base = df["calc_ebitda_calculado"]
    df["calc_fco_ebitda"] = safe_divide(fco, ebitda_base) * 100.0
    df["calc_fco_lucro"] = safe_divide(fco, ll)

    # FCL: FCO − Investimentos
    fcl = fco - flu_inv
    df["calc_fcl"] = fcl
    df["calc_geracao_apos_investimentos"] = fcl

    # Capex / Receita e Capex / D&A
    df["calc_capex_receita"] = safe_divide(flu_inv, rec_abs) * 100.0
    df["calc_capex_da"] = safe_divide(flu_inv, da_abs)

    # Cobertura de Juros em Caixa
    df["calc_cobertura_juros_caixa"] = safe_divide(fco, flu_desp_fin)

    # FCO / Dívida Bruta (mascarada com NaN no Ano 12)
    emp_cp = df.get("BAL - Empréstimos", pd.Series(np.nan, index=df.index)).abs()
    emp_lp = df.get("BAL - Emprést", pd.Series(np.nan, index=df.index)).abs()
    divida_bruta = (emp_cp + emp_lp).where(~bal_incompleto, np.nan)
    df["calc_fco_divida_bruta"] = (safe_divide(fco, divida_bruta) * 100.0).where(~bal_incompleto, np.nan)
    df["calc_prazo_quitacao_divida"] = (safe_divide(divida_bruta, fco)).where(~bal_incompleto, np.nan)

    # Payout e Cobertura de Dividendos
    df["calc_payout_caixa"] = safe_divide(flu_dist_acionista, ll) * 100.0
    df["calc_cobertura_dividendos"] = safe_divide(fcl, flu_dist_acionista)

    # -------------------------------------------------------------------------
    # MÓDULO 2 — ÍNDICES DE CAPITAL DE GIRO E PRAZOS MÉDIOS (VETORIZADO)
    # -------------------------------------------------------------------------
    ccl = (ac - pc_abs).where(~bal_incompleto, np.nan)
    cr_cli = df.get("BAL - Contas a Receber - Clientes", pd.Series(np.nan, index=df.index))
    fornec = df.get("BAL - Fornecedores", pd.Series(np.nan, index=df.index)).abs()

    pmr = (safe_divide(cr_cli, rec_abs) * 360.0).where(~bal_incompleto, np.nan)
    pmp = (safe_divide(fornec, cust_abs) * 360.0).where(~bal_incompleto, np.nan)
    ciclo_fin = (pmr - pmp).where(~bal_incompleto, np.nan)
    custo_diario = safe_divide(cust_abs, 360.0)
    ncg = (ciclo_fin * custo_diario).where(~bal_incompleto, np.nan)
    folga_ccl = (ccl - ncg).where(~bal_incompleto, np.nan)

    df["calc_ccl"] = ccl
    df["calc_pmr"] = pmr
    df["calc_pmp"] = pmp
    df["calc_ciclo_financeiro"] = ciclo_fin
    df["calc_necessidade_capital_giro"] = ncg
    df["calc_folga_ccl"] = folga_ccl

    # -------------------------------------------------------------------------
    # MÓDULO 3 — FLUXO DE CAIXA (VETORIZADO)
    # -------------------------------------------------------------------------
    df["calc_saldo_inicial_caixa"] = flu_saldo_ini
    df["calc_entradas_operacionais"] = flu_rec
    saidas_op = flu_trib + flu_cust + flu_ircs
    df["calc_saidas_operacionais"] = saidas_op
    df["calc_fluxo_investimentos"] = df.get("FLU - Investimentos", pd.Series(np.nan, index=df.index))
    df["calc_fluxo_financiamento"] = df.get("FLU - Despesas Financeiras", pd.Series(0.0, index=df.index)) + df.get("FLU - Distribuição para Acionista", pd.Series(0.0, index=df.index))
    juros_liq = flu_desp_fin - flu_entradas
    df["calc_juros_liquidos"] = juros_liq
    df["calc_geracao_apos_juros_div"] = fcl - juros_liq - flu_dist_acionista
    df["calc_saldo_final_caixa"] = flu_saldo_fim
    df["calc_conciliacao_caixa_diff"] = (flu_saldo_ini + flu_geracao_caixa - flu_saldo_fim).abs()

    # -------------------------------------------------------------------------
    # MÓDULO 4 — DEMONSTRAÇÃO DO VALOR ADICIONADO - DVA (VETORIZADO)
    # -------------------------------------------------------------------------
    rec_oper = df.get("DRE - Outros Resultados Operacionais", pd.Series(0.0, index=df.index))
    outras_rec = rec_oper.apply(lambda v: float(v) if v > 0 else 0.0)
    outros_ins = rec_oper.apply(lambda v: abs(float(v)) if v < 0 else 0.0)

    # Item 1: Receitas
    dva_item1 = rec_abs + outras_rec
    df["calc_dva_receitas_totais"] = dva_item1
    df["calc_dva_vendas_brutas"] = rec_abs
    df["calc_dva_outras_receitas"] = outras_rec

    # Item 2: Insumos de terceiros
    dva_item2 = cust_abs + outros_ins
    df["calc_dva_insumos_totais"] = dva_item2
    df["calc_dva_custos"] = cust_abs
    df["calc_dva_outros_insumos"] = outros_ins

    # Item 3: VA Bruto
    va_bruto = dva_item1 - dva_item2
    df["calc_dva_va_bruto"] = va_bruto

    # Item 4: Retenções (Depreciação, Amortização e Exaustão)
    df["calc_dva_retencoes"] = da_abs

    # Item 5: VA Líquido Produzido
    va_liq = va_bruto - da_abs
    df["calc_dva_va_liquido"] = va_liq

    # Item 6: Transferências
    rec_fin = df.get("DRE - Receitas Financeiras", pd.Series(0.0, index=df.index)).abs()
    rl_pos_equiv = df.get("DRE - Resultado Líquido após Equivalência", ll)
    equiv_patr = (rl_pos_equiv - ll).abs()
    transf_total = rec_fin + equiv_patr
    df["calc_dva_receitas_financeiras"] = rec_fin
    df["calc_dva_equiv_patrimonial"] = equiv_patr
    df["calc_dva_transferencias_totais"] = transf_total

    # Item 7: VA Total a Distribuir
    va_total = va_liq + transf_total
    df["calc_dva_va_total"] = va_total

    # Item 8: Distribuição da Riqueza
    dist_pessoal = pd.Series(0.0, index=df.index)
    dist_gov = trib.abs() + ir_csll.abs()
    dist_terc = df.get("DRE - Despesas Financeiras", pd.Series(0.0, index=df.index)).abs()
    dist_div = flu_dist_acionista
    dist_retidos = ll - dist_div
    dist_proprios = ll

    df["calc_dva_dist_pessoal"] = dist_pessoal
    df["calc_dva_dist_governo"] = dist_gov
    df["calc_dva_dist_terceiros"] = dist_terc
    df["calc_dva_dist_dividendos"] = dist_div
    df["calc_dva_dist_lucros_retidos"] = dist_retidos
    df["calc_dva_dist_proprios"] = dist_proprios
    total_dist = dist_pessoal + dist_gov + dist_terc + dist_proprios
    df["calc_dva_total_distribuido"] = total_dist
    df["calc_dva_conciliacao_diff"] = (va_total - total_dist).abs()

    # Indicadores da DVA
    df["calc_dva_grau_riqueza"] = safe_divide(va_total, dva_item1) * 100.0
    df["calc_dva_va_por_empregado"] = pd.Series(np.nan, index=df.index)
    df["calc_dva_part_governo"] = safe_divide(dist_gov, va_total) * 100.0
    df["calc_dva_part_pessoal"] = safe_divide(dist_pessoal, va_total) * 100.0
    df["calc_dva_part_terceiros"] = safe_divide(dist_terc, va_total) * 100.0
    df["calc_dva_part_proprios"] = safe_divide(dist_proprios, va_total) * 100.0
    df["calc_dva_part_transferencias"] = safe_divide(transf_total, va_total) * 100.0
    df["calc_dva_retencao_riqueza"] = safe_divide(dist_retidos, va_total) * 100.0


    # --- Colunas canônicas unificadas `kpi_<key>` para consumo consistente em todo o sistema ---
    kpi_cols: dict[str, Any] = {}
    for key, meta in KPI_CATALOG.items():
        if meta.is_simulated_premise:
            if key == "cac_simulado":
                kpi_cols[f"kpi_{key}"] = CAC_SIMULATED_PREMISE
            elif key == "ltv_simulado":
                kpi_cols[f"kpi_{key}"] = LTV_SIMULATED_PREMISE
            elif key == "ltv_cac":
                kpi_cols[f"kpi_{key}"] = LTV_CAC_SIMULATED_PREMISE
            continue

        calc_col = f"calc_{key}"
        if meta.kpis_sheet_col and meta.kpis_sheet_col in df.columns:
            kpi_cols[f"kpi_{key}"] = df[meta.kpis_sheet_col]
        elif calc_col in df.columns:
            kpi_cols[f"kpi_{key}"] = df[calc_col]
        else:
            kpi_cols[f"kpi_{key}"] = np.nan

    df = pd.concat([df, pd.DataFrame(kpi_cols, index=df.index)], axis=1)
    return df


def summarize_kpis_for_selection(df_scenario: pd.DataFrame) -> dict[str, dict[str, Any]]:
    """Consolida KPIs para um cenário no intervalo filtrado (média nos períodos válidos + último período + variação).

    Observação importante:
    - Para múltiplos períodos, `mean` corresponde exatamente à metodologia de `Resumo_Cenarios` (média dos períodos válidos).
    - Para indicadores monetários de fluxo (Receita, EBITDA, Resultado Líquido, Geração de Caixa),
      também disponibiliza `sum` (total acumulado no intervalo), mantendo `mean` separado para nunca somar índices/margens.
    """
    flow_keys = {
        "receita",
        "custos_variaveis",
        "ebitda_calculado",
        "ebitda_modelo",
        "nopat",
        "eva",
        "geracao_caixa",
        "resultado_liquido",
        "fco",
        "fco_fluxo",
        "fcl",
        "entradas_operacionais",
        "saidas_operacionais",
        "geracao_apos_investimentos",
        "geracao_apos_juros_div",
        "dva_va_bruto",
        "dva_va_liquido",
        "dva_va_total",
    }
    ordered = df_scenario.sort_values("Ano") if "Ano" in df_scenario.columns else df_scenario
    results: dict[str, dict[str, Any]] = {}

    for key, meta in KPI_CATALOG.items():
        col = f"kpi_{key}"
        if col not in ordered.columns or ordered.empty:
            results[key] = {
                "mean": np.nan,
                "sum": np.nan,
                "latest": np.nan,
                "first": np.nan,
                "latest_period": None,
                "first_period": None,
                "valid_count": 0,
                "diff_abs": np.nan,
                "diff_pct": np.nan,
            }
            continue

        valid_rows = ordered.dropna(subset=[col])
        n_valid = len(valid_rows)
        if n_valid == 0:
            results[key] = {
                "mean": np.nan,
                "sum": np.nan,
                "latest": np.nan,
                "first": np.nan,
                "latest_period": None,
                "first_period": None,
                "valid_count": 0,
                "diff_abs": np.nan,
                "diff_pct": np.nan,
            }
            continue

        s = valid_rows[col].astype(float)
        first_val = float(s.iloc[0])
        latest_val = float(s.iloc[-1])
        first_per = int(valid_rows["Ano"].iloc[0])
        latest_per = int(valid_rows["Ano"].iloc[-1])
        var_info = compute_variation(
            latest_val,
            first_val,
            is_percentage_point_metric=(meta.unit == "%"),
        ) if n_valid >= 2 else {"diff_abs": np.nan, "diff_pct": np.nan, "diff_pp": np.nan}

        results[key] = {
            "mean": float(s.mean()),
            "sum": float(s.sum()) if key in flow_keys else np.nan,
            "latest": latest_val,
            "first": first_val,
            "latest_period": latest_per,
            "first_period": first_per,
            "valid_count": n_valid,
            "diff_abs": var_info["diff_abs"],
            "diff_pct": var_info["diff_pct"],
            "diff_pp": var_info.get("diff_pp", np.nan),
        }

    return results


@dataclass
class GoalEvaluation:
    """Resultado auditável da comparação entre valor real observado e meta configurada pelo usuário."""

    kpi_key: str
    kpi_name: str
    unit: str
    current_value: float
    target_value: float | None
    difference: float
    attainment_ratio: float
    status: str  # 'Acima da Meta' | 'Meta Atingida' | 'Em Atenção' | 'Abaixo da Meta' | 'Meta Não Definida' | 'N/D'
    is_favorable: bool | None


def evaluate_goal(
    kpi_key: str,
    current_value: Any,
    target_value: float | None,
) -> GoalEvaluation:
    """Compara o valor atual de um KPI com a meta configurada sem inventar metas padrão."""
    meta = KPI_CATALOG[kpi_key]
    curr = float(current_value) if is_valid_number(current_value) else np.nan

    if target_value is None or not is_valid_number(target_value):
        return GoalEvaluation(
            kpi_key=kpi_key,
            kpi_name=meta.name,
            unit=meta.unit,
            current_value=curr,
            target_value=None,
            difference=np.nan,
            attainment_ratio=np.nan,
            status="Meta Não Definida",
            is_favorable=None,
        )

    tgt = float(target_value)
    if np.isnan(curr):
        return GoalEvaluation(
            kpi_key=kpi_key,
            kpi_name=meta.name,
            unit=meta.unit,
            current_value=np.nan,
            target_value=tgt,
            difference=np.nan,
            attainment_ratio=np.nan,
            status="Dado Indisponível (N/D)",
            is_favorable=None,
        )

    diff = curr - tgt
    higher_better = True if meta.higher_is_better is None else meta.higher_is_better

    if higher_better:
        # Ex.: Receita, Margem EBITDA, ROIC, LC -> quanto maior, melhor
        attainment = safe_divide(curr, tgt) if tgt > 0 else (1.0 if curr >= tgt else 0.0)
        if curr > tgt * 1.0001:
            status = "Acima da Meta"
            favorable = True
        elif abs(curr - tgt) <= abs(tgt) * 0.0001 + 1e-9:
            status = "Meta Atingida"
            favorable = True
        elif is_valid_number(attainment) and attainment >= 0.90:
            status = "Em Atenção (≥90%)"
            favorable = False
        else:
            status = "Abaixo da Meta"
            favorable = False
    else:
        # Ex.: Endividamento Geral, Custos Variáveis, PCT -> teto máximo (quanto menor, melhor)
        attainment = safe_divide(tgt, curr) if curr > 0 else (1.0 if curr <= tgt else 0.0)
        if curr < tgt * 0.9999:
            status = "Melhor que o Teto (Meta Atingida)"
            favorable = True
        elif abs(curr - tgt) <= abs(tgt) * 0.0001 + 1e-9:
            status = "No Limite da Meta"
            favorable = True
        elif is_valid_number(attainment) and attainment >= 0.90:
            status = "Em Atenção (Próximo ao Teto)"
            favorable = False
        else:
            status = "Acima do Teto (Desfavorável)"
            favorable = False

    return GoalEvaluation(
        kpi_key=kpi_key,
        kpi_name=meta.name,
        unit=meta.unit,
        current_value=curr,
        target_value=tgt,
        difference=diff,
        attainment_ratio=float(attainment) if is_valid_number(attainment) else np.nan,
        status=status,
        is_favorable=favorable,
    )


def evaluate_all_goals(
    current_kpis: dict[str, float],
    configured_goals: dict[str, float | None],
    kpi_keys: list[str] | None = None,
) -> pd.DataFrame:
    """Gera tabela consolidada de acompanhamento de metas apenas para os KPIs selecionados."""
    keys = kpi_keys or [k for k in KPI_CATALOG if not KPI_CATALOG[k].is_simulated_premise]
    rows = []
    for k in keys:
        if k not in KPI_CATALOG:
            continue
        ev = evaluate_goal(k, current_kpis.get(k, np.nan), configured_goals.get(k))
        rows.append({
            "kpi_key": ev.kpi_key,
            "Indicador": ev.kpi_name,
            "Unidade": ev.unit,
            "Sentido Desejado": "Menor é melhor (Teto)" if KPI_CATALOG[k].higher_is_better is False else "Maior é melhor (Piso)",
            "Valor Observado": ev.current_value,
            "Valor Observado (Fmt)": format_by_unit(ev.current_value, ev.unit, compact_currency=False),
            "Meta Configurada": ev.target_value,
            "Meta Configurada (Fmt)": (
                format_by_unit(ev.target_value, ev.unit, compact_currency=False)
                if ev.target_value is not None
                else "Não definida"
            ),
            "Diferença (Atual - Meta)": ev.difference,
            "Diferença (Fmt)": (
                format_pct_br(ev.difference, signed=True) + " (p.p.)"
                if (ev.unit == "%" and is_valid_number(ev.difference))
                else format_by_unit(ev.difference, ev.unit, compact_currency=False)
            ),
            "Atingimento (%)": ev.attainment_ratio * 100.0 if is_valid_number(ev.attainment_ratio) else np.nan,
            "Atingimento (Fmt)": format_pct_br(ev.attainment_ratio) if is_valid_number(ev.attainment_ratio) else "N/D",
            "Classificação": ev.status,
            "Favorável": ev.is_favorable,
        })
    return pd.DataFrame(rows)


def investigate_ticket_medio(sheets: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """Audita programaticamente todas as abas da planilha para verificar se há dados para Ticket Médio real."""
    transaction_keywords = (
        "ticket",
        "quantidade",
        "qtd",
        "volume",
        "pedidos",
        "transacoes",
        "transações",
        "numero de clientes",
        "número de clientes",
        "clientes ativos",
        "unidades vendidas",
    )
    matched_columns: list[dict[str, str]] = []
    for sheet_name, df in sheets.items():
        for col in df.columns:
            col_low = str(col).lower()
            for kw in transaction_keywords:
                if kw in col_low:
                    matched_columns.append({"aba": sheet_name, "coluna": str(col), "termo": kw})
                    break

    dictionary_mentions: list[dict[str, str]] = []
    if "Dicionario_KPIs" in sheets:
        dic = sheets["Dicionario_KPIs"]
        for _, row in dic.iterrows():
            row_text = " | ".join(str(v) for v in row.values if pd.notna(v))
            if "ticket" in row_text.lower():
                dictionary_mentions.append({
                    "kpi": str(row.get("KPI / Indicador", "")),
                    "formula": str(row.get("Fórmula / Regra aplicada", "")),
                    "observacao": str(row.get("Observação / Premissa", "")),
                })

    can_calculate_real = len(matched_columns) > 0
    return {
        "can_calculate_real_ticket": can_calculate_real,
        "status_label": "Calculável na base original" if can_calculate_real else "Indisponível na base original (N/D)",
        "matched_columns": matched_columns,
        "dictionary_mentions": dictionary_mentions,
        "required_fields_for_real_calculation": [
            "Quantidade total de transações, faturas ou pedidos emitidos por cenário e período (Ticket Médio = Receita / Nº de Transações); ou",
            "Base de clientes pagantes ativos e frequência média de faturamento anual (Ticket Médio = Receita / [Clientes Ativos × Compras por Ano]).",
        ],
        "documented_simulated_premises": {
            "cac_simulado": CAC_SIMULATED_PREMISE,
            "ltv_simulado": LTV_SIMULATED_PREMISE,
            "ltv_cac": LTV_CAC_SIMULATED_PREMISE,
            "wacc_modelo": WACC_MODEL_PREMISE,
        },
    }

