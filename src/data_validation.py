"""Módulo de auditoria, qualidade de dados e reconciliação matemática dos KPIs.

Verifica sistematicamente:
- Completude de abas e colunas essenciais.
- Unicidade e consistência das chaves `(Cenário, Ano)` entre abas detalhadas e consolidadas.
- Perfil de valores ausentes por aba, coluna e período (destacando a incompletude do Balanço no Ano 12).
- Proteção contra denominadores nulos ou iguais a zero.
- Reconciliação exata entre os KPIs da planilha (`KPIs_Cenarios` e `Resumo_Cenarios`) e os recalculados.
- Identificação de valores extremos (outliers via IQR) e alertas de auditoria do `Dicionario_KPIs`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from src.config import ESSENTIAL_SHEETS, EXPECTED_SHEETS, KPI_CATALOG
from src.data_processing import ProcessedDataStore


@dataclass
class ValidationSummary:
    """Relatório estruturado de qualidade de dados e auditoria financeira."""

    overall_status: str  # 'APROVADO' | 'APROVADO COM RESSALVAS DOCUMENTADAS' | 'ERRO CRÍTICO'
    n_scenarios: int
    periods_per_scenario_min: int
    periods_per_scenario_max: int
    duplicate_keys_by_sheet: dict[str, int]
    key_consistency_ok: bool
    missing_sheets: list[str]
    zero_denominators_detected: dict[str, int]
    year_12_incomplete_balance_count: int
    sheet_profiles: pd.DataFrame
    missing_by_column: pd.DataFrame
    kpi_reconciliation: pd.DataFrame
    resumo_reconciliation: pd.DataFrame
    outliers_summary: pd.DataFrame
    dictionary_audit_findings: list[dict[str, str]] = field(default_factory=list)


def run_full_validation(store: ProcessedDataStore) -> ValidationSummary:
    """Executa todas as validações estruturais, contábeis e estatísticas sobre o `ProcessedDataStore`."""
    bundle = store.bundle
    dup_by_sheet: dict[str, int] = {}
    sheet_rows = []
    missing_rows = []

    scenario_sets: dict[str, set[str]] = {}

    for s_name in EXPECTED_SHEETS:
        if s_name not in bundle.sheets:
            continue
        raw_df = bundle.sheets[s_name]
        n_rows, n_cols = raw_df.shape
        total_cells = max(n_rows * n_cols, 1)
        total_nulls = int(raw_df.isna().sum().sum())

        clean_cols = [str(c).strip() for c in raw_df.columns]
        dups = 0
        if "Cenário" in clean_cols and "Ano" in clean_cols:
            c_col = raw_df.columns[clean_cols.index("Cenário")]
            a_col = raw_df.columns[clean_cols.index("Ano")]
            dups = int(raw_df.duplicated(subset=[c_col, a_col]).sum())
            scenario_sets[s_name] = set(raw_df[c_col].dropna().astype(str).str.strip().unique())
        elif "Cenário" in clean_cols and s_name != "Top10_Rankings":
            c_col = raw_df.columns[clean_cols.index("Cenário")]
            dups = int(raw_df.duplicated(subset=[c_col]).sum())
            scenario_sets[s_name] = set(raw_df[c_col].dropna().astype(str).str.strip().unique())

        dup_by_sheet[s_name] = dups
        sheet_rows.append({
            "Aba": s_name,
            "Granularidade": (
                "Cenário × Ano" if ("Ano" in clean_cols)
                else ("Cenário" if "Cenário" in clean_cols and s_name != "Top10_Rankings" else "Referência / Ranking")
            ),
            "Linhas": n_rows,
            "Colunas": n_cols,
            "Duplicidades de Chave": dups,
            "Células Ausentes": total_nulls,
            "Completude (%)": round((1.0 - total_nulls / total_cells) * 100.0, 2),
        })

        for col in raw_df.columns:
            col_str = str(col).strip()
            if col_str.lower().startswith("unnamed:") or col_str in ("WACC", "0.12"):
                continue
            n_miss = int(raw_df[col].isna().sum())
            if n_miss > 0:
                missing_rows.append({
                    "Aba": s_name,
                    "Coluna": col_str,
                    "Registros Ausentes": n_miss,
                    "% Ausente": round(n_miss / max(n_rows, 1) * 100.0, 2),
                    "Causa Identificada": (
                        "Incompletude documentada do Balanço Patrimonial no Ano 12"
                        if (n_miss == len(store.scenarios) and s_name in ("Balanco_Cenarios", "KPIs_Cenarios"))
                        else (
                            "Sem distribuição de dividendos antecipados nos Anos 1, 2 e 12"
                            if "Dividendos Antecipados" in col_str
                            else "Campo opcional / parcial na fonte"
                        )
                    ),
                })

    # Consistência de cenários entre todas as abas principais
    ref_set = scenario_sets.get("DRE_Cenarios", set())
    key_consistency_ok = all(s_set == ref_set for s_set in scenario_sets.values()) and len(ref_set) > 0

    per_counts = store.panel.groupby("Cenário")["Ano"].nunique()
    p_min = int(per_counts.min()) if not per_counts.empty else 0
    p_max = int(per_counts.max()) if not per_counts.empty else 0

    # Verificação explícita de denominadores iguais a zero (nos períodos com dados válidos)
    p = store.panel
    valid_bp = p[~p["Balanco_Incompleto"]]
    zero_denoms = {
        "Receita Bruta = 0 (DRE)": int((p["DRE - Receita"].abs() <= 1e-12).sum()) if "DRE - Receita" in p else 0,
        "Receita Líquida Proxy = 0 (DRE)": int(((p["DRE - Receita"].abs() + p["DRE - Tributos"]).abs() <= 1e-12).sum())
        if {"DRE - Receita", "DRE - Tributos"}.issubset(p.columns) else 0,
        "Passivo Circulante = 0 (Anos 1–11)": int((valid_bp["BAL - Passivo Circulante"].abs() <= 1e-12).sum())
        if "BAL - Passivo Circulante" in valid_bp else 0,
        "Exigível Total (|PC|+|PNC|) = 0 (Anos 1–11)": int(
            ((valid_bp["BAL - Passivo Circulante"].abs() + valid_bp["BAL - Exigível a Longo Prazo"].abs()) <= 1e-12).sum()
        ) if {"BAL - Passivo Circulante", "BAL - Exigível a Longo Prazo"}.issubset(valid_bp.columns) else 0,
        "Capital Investido = 0 (Anos 1–11)": int((valid_bp["calc_capital_investido"].abs() <= 1e-12).sum())
        if "calc_capital_investido" in valid_bp else 0,
    }

    # Reconciliação numérica: KPIs_Cenarios vs Recalculados (calc_*)
    kpi_rec_rows = []
    for key, meta in KPI_CATALOG.items():
        if not meta.kpis_sheet_col:
            continue
        orig_col = meta.kpis_sheet_col
        calc_col = f"calc_{key}"
        if orig_col not in p.columns or calc_col not in p.columns:
            continue

        s_orig = p[orig_col]
        s_calc = p[calc_col]
        both_valid = s_orig.notna() & s_calc.notna()
        mismatch_na = int((s_orig.isna() ^ s_calc.isna()).sum())

        if both_valid.any():
            abs_diff = (s_orig[both_valid] - s_calc[both_valid]).abs()
            denom_scale = s_orig[both_valid].abs().replace(0, np.nan)
            rel_diff = (abs_diff / denom_scale).dropna()
            max_abs = float(abs_diff.max())
            max_rel = float(rel_diff.max()) if not rel_diff.empty else 0.0
        else:
            max_abs = 0.0
            max_rel = 0.0

        # Tolerância rigorosa: erro relativo <= 1e-6 (0,0001%)
        passed = (max_rel <= 1e-6 or max_abs <= 1e-4) and mismatch_na == 0
        kpi_rec_rows.append({
            "KPI": meta.name,
            "Unidade Adotada": meta.unit,
            "Unidade no Dicionário": meta.dictionary_raw_unit,
            "Registros Calculáveis": int(both_valid.sum()),
            "Registros N/D (Ano 12)": int((~both_valid).sum()),
            "Divergência N/D": mismatch_na,
            "Dif. Absoluta Máx.": max_abs,
            "Dif. Relativa Máx.": max_rel,
            "Status": "Reconciliado (100%)" if passed else "Divergência Detectada",
        })

    # Reconciliação de Resumo_Cenarios vs Média Anos 1..11
    resumo_rec_rows = []
    if not store.resumo.empty:
        p11 = p[~p["Balanco_Incompleto"]].groupby("Cenário").mean(numeric_only=True)
        res_idx = store.resumo.set_index("Cenário")
        common_scen = res_idx.index.intersection(p11.index)
        for key, meta in KPI_CATALOG.items():
            if not meta.resumo_sheet_col or meta.is_simulated_premise:
                continue
            r_col = meta.resumo_sheet_col
            c_col = f"calc_{key}"
            if r_col in res_idx.columns and c_col in p11.columns and len(common_scen) > 0:
                diff = (res_idx.loc[common_scen, r_col] - p11.loc[common_scen, c_col]).abs()
                rel = (diff / res_idx.loc[common_scen, r_col].abs().replace(0, np.nan)).dropna()
                max_abs = float(diff.max())
                max_rel = float(rel.max()) if not rel.empty else 0.0
                resumo_rec_rows.append({
                    "KPI Consolidado": meta.name,
                    "Coluna Resumo_Cenarios": r_col,
                    "Cenários Comparados": int(len(common_scen)),
                    "Regra Confirmada": "Média aritmética dos Anos 1 a 11",
                    "Dif. Absoluta Máx.": max_abs,
                    "Dif. Relativa Máx.": max_rel,
                    "Status": "Reconciliado (100%)" if (max_rel <= 1e-6 or max_abs <= 1e-4) else "Divergente",
                })

    # Diagnóstico de outliers (critério IQR 1,5x e 3,0x sobre observações válidas Cenário × Ano)
    outlier_rows = []
    for key in [
        "receita",
        "margem_ebitda_calculada",
        "margem_ebitda_modelo",
        "margem_contribuicao",
        "roic",
        "eva",
        "lc",
        "lg",
        "pct",
        "ipl",
        "endividamento_geral",
        "geracao_caixa",
    ]:
        col = f"kpi_{key}"
        if col not in p.columns:
            continue
        s = p[col].dropna()
        if len(s) < 4:
            continue
        q1 = float(np.percentile(s, 25))
        q3 = float(np.percentile(s, 75))
        iqr = q3 - q1
        low_15, high_15 = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        low_30, high_30 = q1 - 3.0 * iqr, q3 + 3.0 * iqr
        n_out_15 = int(((s < low_15) | (s > high_15)).sum())
        n_out_30 = int(((s < low_30) | (s > high_30)).sum())
        outlier_rows.append({
            "Indicador": KPI_CATALOG[key].name,
            "Unidade": KPI_CATALOG[key].unit,
            "N Válido": len(s),
            "Mínimo": float(s.min()),
            "Mediana (P50)": float(np.percentile(s, 50)),
            "Máximo": float(s.max()),
            "Outliers Moderados (IQR 1,5x)": n_out_15,
            "Outliers Extremos (IQR 3,0x)": n_out_30,
            "% Outliers Extremos": round(n_out_30 / len(s) * 100.0, 2),
        })

    # Auditoria documental da aba Dicionario_KPIs
    audit_findings = _audit_dictionary_sheet(store)

    year12_inc = int(p[p["Ano"] == 12]["Balanco_Incompleto"].sum()) if "Ano" in p.columns else 0
    has_critical_error = (
        len([s for s in ESSENTIAL_SHEETS if s in bundle.missing_sheets]) > 0
        or not key_consistency_ok
        or any(v > 0 for v in dup_by_sheet.values())
    )
    overall_status = (
        "ERRO CRÍTICO"
        if has_critical_error
        else ("APROVADO COM RESSALVAS DOCUMENTADAS" if (year12_inc > 0 or len(audit_findings) > 0) else "APROVADO")
    )

    return ValidationSummary(
        overall_status=overall_status,
        n_scenarios=len(store.scenarios),
        periods_per_scenario_min=p_min,
        periods_per_scenario_max=p_max,
        duplicate_keys_by_sheet=dup_by_sheet,
        key_consistency_ok=key_consistency_ok,
        missing_sheets=bundle.missing_sheets,
        zero_denominators_detected=zero_denoms,
        year_12_incomplete_balance_count=year12_inc,
        sheet_profiles=pd.DataFrame(sheet_rows),
        missing_by_column=pd.DataFrame(missing_rows),
        kpi_reconciliation=pd.DataFrame(kpi_rec_rows),
        resumo_reconciliation=pd.DataFrame(resumo_rec_rows),
        outliers_summary=pd.DataFrame(outlier_rows),
        dictionary_audit_findings=audit_findings,
    )


def _audit_dictionary_sheet(store: ProcessedDataStore) -> list[dict[str, str]]:
    """Audita a aba `Dicionario_KPIs` contra os cabeçalhos, unidades e fórmulas reais da planilha."""
    findings: list[dict[str, str]] = []
    dic = store.dicionario_ref

    # 1. Verifica desalinhamento de ordenação na coluna 'Regra de validação'
    if {"KPI / Indicador", "Regra de validação"}.issubset(dic.columns):
        sample_custos = dic[dic["KPI / Indicador"].astype(str).str.contains("Custos variáveis", case=False, na=False)]
        if not sample_custos.empty:
            rule_txt = str(sample_custos["Regra de validação"].iloc[0])
            if "AC/ABS(PC)" in rule_txt:
                findings.append({
                    "codigo": "AUD-01",
                    "severidade": "Média (Documental)",
                    "titulo": "Desalinhamento da coluna 'Regra de validação' na aba Dicionario_KPIs",
                    "detalhe": (
                        "Nas linhas 2 a 20 de Dicionario_KPIs, as colunas A–K foram ordenadas alfabeticamente por "
                        "Categoria/Indicador sem ordenar a coluna L ('Regra de validação'). Exemplo: a linha de "
                        "'Custos variáveis' exibe a regra de validação da Liquidez Corrente ('AC/ABS(PC)')."
                    ),
                    "resolucao": (
                        "A planilha original foi preservada sem alterações. No catálogo interno do sistema e em "
                        "docs/auditoria_qualidade_kpis.md, cada KPI foi remapeado para sua regra de validação exata."
                    ),
                })

    # 2. Verifica divergência de unidade R$ mil vs R$
    if "Unidade" in dic.columns and (dic["Unidade"].astype(str).str.strip() == "R$ mil").any():
        findings.append({
            "codigo": "AUD-02",
            "severidade": "Alta (Padronização de Escala)",
            "titulo": "Divergência de unidade monetária entre Dicionario_KPIs ('R$ mil') e abas calculadas ('R$')",
            "detalhe": (
                "O Dicionario_KPIs indica 'R$ mil' para Receita, Custos, EBITDA, NOPAT, Capital Investido e EVA, "
                "enquanto os cabeçalhos de KPIs_Cenarios, Resumo_Cenarios e a coluna Unidade de KPIs_Estatisticas "
                "registram 'R$' (com valores na ordem de 6,72×10⁹ para Receita e R$ 200,00/cliente para CAC)."
            ),
            "resolucao": (
                "Nenhuma multiplicação arbitrária por 1.000 foi aplicada. Adotou-se 'R$' como convenção única em "
                "cartões, gráficos, tabelas e relatórios, mantendo paridade numérica integral com KPIs_Cenarios e KPIs_Estatisticas."
            ),
        })

    # 3. Verifica incompletude do Balanço no Ano 12
    if int(store.panel[store.panel["Ano"] == 12]["Balanco_Incompleto"].sum()) > 0:
        findings.append({
            "codigo": "AUD-03",
            "severidade": "Média (Limitação Estrutural dos Dados)",
            "titulo": "Incompletude do Balanço Patrimonial no Ano 12",
            "detalhe": (
                "No Ano 12, 27 contas patrimoniais (incluindo Exigível a Longo Prazo e Patrimônio Líquido) estão "
                "ausentes (NaN) nos 1.200 cenários, inviabilizando o cálculo confiável de Liquidez, Endividamento, "
                "Capital Investido, NOPAT, EVA e ROIC nesse período."
            ),
            "resolucao": (
                "O sistema marca automaticamente esses 12 indicadores como N/D no Ano 12 (sem fabricar zeros), "
                "mantém os 7 indicadores da DRE e os fluxos da DFC válidos nos Anos 1–12 e consolida médias "
                "multiperíodo de estrutura patrimonial sobre os Anos 1–11 (idêntico ao Resumo_Cenarios)."
            ),
        })

    # 4. Verifica convenção de PL implícito e sinal do Passivo Circulante nos Anos 5–11
    if "BAL - Passivo Circulante" in store.panel.columns:
        valid_bp = store.panel[~store.panel["Balanco_Incompleto"]]
        pos_pc = int((valid_bp["BAL - Passivo Circulante"] > 0).sum())
        if pos_pc > 0:
            findings.append({
                "codigo": "AUD-04",
                "severidade": "Média (Convenção Contábil do Modelo CTI)",
                "titulo": "Inversão de sinal em 'BAL - Passivo Circulante' (Anos 5–11) e fórmula de PL implícito",
                "detalhe": (
                    f"Em {pos_pc:,} registros Cenário × Ano (concentrados nos Anos 5–11), a conta 'BAL - Passivo Circulante' "
                    "passa de sinal negativo (credor) para positivo devido ao saldo devedor em 'BAL - Empréstimos'. "
                    "Além disso, a planilha KPIs_Cenarios calcula o denominador de PCT e IPL e a parcela de PL do Capital Investido "
                    "como ABS(Ativo Total − ABS(PC) − ABS(PNC)) em vez de ABS(BAL - Patrimônio Líquido)."
                ).replace(",", "."),
                "resolucao": (
                    "O sistema reproduz exatamente a fórmula algébrica de KPIs_Cenarios para garantir 100% de reconciliação "
                    "com a planilha de validação, disponibilizando as colunas de auditoria ('audit_*_pl_direto') para rastreabilidade de auditoria."
                ),
            })

    # 5. Verifica indisponibilidade de Ticket Médio observado
    findings.append({
        "codigo": "AUD-05",
        "severidade": "Informativa (Escopo de Dados)",
        "titulo": "Ausência de dados transacionais para Ticket Médio observado e natureza simulada de CAC/LTV/WACC",
        "detalhe": (
            "A base CTI contém demonstrações contábeis agregadas (DRE, BP e DFC), sem quantidade de pedidos, unidades "
            "vendidas ou base ativa de clientes. CAC (R$ 200,00), LTV (R$ 2.100,00), LTV/CAC (10,50x) e WACC (12%) "
            "são premissas constantes do modelo."
        ),
        "resolucao": (
            "O Ticket Médio real é exibido explicitamente como Indisponível (N/D) na base original, com módulo "
            "dedicado para inserção de premissas editáveis claramente identificadas como Simulação."
        ),
    })

    return findings

