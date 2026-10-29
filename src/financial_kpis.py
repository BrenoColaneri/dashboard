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

    # --- Colunas canônicas unificadas `kpi_<key>` para consumo consistente em todo o sistema ---
    for key, meta in KPI_CATALOG.items():
        if meta.is_simulated_premise:
            if key == "cac_simulado":
                df[f"kpi_{key}"] = CAC_SIMULATED_PREMISE
            elif key == "ltv_simulado":
                df[f"kpi_{key}"] = LTV_SIMULATED_PREMISE
            elif key == "ltv_cac":
                df[f"kpi_{key}"] = LTV_CAC_SIMULATED_PREMISE
            continue

        calc_col = f"calc_{key}"
        if meta.kpis_sheet_col and meta.kpis_sheet_col in df.columns:
            # Usa o valor da planilha quando presente e preenche eventuais ausências válidas com o recalculado
            df[f"kpi_{key}"] = df[meta.kpis_sheet_col]
        elif calc_col in df.columns:
            df[f"kpi_{key}"] = df[calc_col]
        else:
            df[f"kpi_{key}"] = np.nan

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

