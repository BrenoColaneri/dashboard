"""Análise Estatística Descritiva, Inferencial e Validação contra `KPIs_Estatisticas`.

Distingue rigorosamente as duas populações analíticas:
1. População Consolidada por Cenário (`Resumo_Cenarios`, 1 linha por cenário, média Anos 1–11) —
   diretamente comparável à aba `KPIs_Estatisticas` do modelo de planejamento.
2. População em Painel `Cenário × Período` (`panel`, observações anuais detalhadas) —
   captura variabilidade temporal intrínseca entre os períodos `Ano 1` a `Ano 12`.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from src.config import KPI_CATALOG
from src.data_processing import ProcessedDataStore


def compute_descriptive_stats(series: pd.Series, variable_label: str = "", unit: str = "") -> dict[str, Any]:
    """Calcula medidas completas de posição, dispersão, forma e percentis para uma série numérica."""
    total_len = len(series)
    clean = pd.to_numeric(series, errors="coerce").dropna().astype(float)
    n = len(clean)
    missing = total_len - n

    if n == 0:
        return {
            "Variável": variable_label,
            "Unidade": unit,
            "N": 0,
            "Ausentes": missing,
            "Média": np.nan,
            "Mediana (P50)": np.nan,
            "Moda": np.nan,
            "Nota Moda": "Sem observações válidas",
            "Mínimo": np.nan,
            "Máximo": np.nan,
            "Amplitude": np.nan,
            "Variância (amostral)": np.nan,
            "Desvio Padrão (amostral)": np.nan,
            "Coef. Variação (%)": np.nan,
            "IQR (P75 - P25)": np.nan,
            "P5": np.nan,
            "P10": np.nan,
            "P25": np.nan,
            "P75": np.nan,
            "P90": np.nan,
            "P95": np.nan,
            "Assimetria (Skewness)": np.nan,
            "Curtose": np.nan,
        }

    arr = clean.to_numpy()
    mean_val = float(np.mean(arr))
    std_val = float(np.std(arr, ddof=1)) if n > 1 else 0.0
    var_val = float(np.var(arr, ddof=1)) if n > 1 else 0.0
    min_val = float(np.min(arr))
    max_val = float(np.max(arr))

    # Moda: só é informativa diretamente se houver valores repetidos; para variáveis contínuas usamos arredondamento controlado
    val_counts = clean.value_counts()
    if not val_counts.empty and int(val_counts.iloc[0]) > 1:
        mode_val = float(val_counts.index[0])
        mode_note = f"Moda exata ({int(val_counts.iloc[0])} ocorrências)"
    else:
        rounded = clean.round(4)
        rc = rounded.value_counts()
        if not rc.empty and int(rc.iloc[0]) > 1:
            mode_val = float(rc.index[0])
            mode_note = f"Moda aproximada (4 casas, {int(rc.iloc[0])} ocorrências; variável contínua)"
        else:
            mode_val = np.nan
            mode_note = "Amodal (variável contínua sem repetição)"

    p5, p10, p25, p50, p75, p90, p95 = np.percentile(arr, [5, 10, 25, 50, 75, 90, 95])
    cv_pct = (std_val / abs(mean_val) * 100.0) if abs(mean_val) > 1e-12 else np.nan
    skew_val = float(stats.skew(arr, bias=False)) if (n > 2 and std_val > 1e-12) else 0.0
    kurt_val = float(stats.kurtosis(arr, bias=False)) if (n > 3 and std_val > 1e-12) else 0.0

    return {
        "Variável": variable_label,
        "Unidade": unit,
        "N": n,
        "Ausentes": missing,
        "Média": mean_val,
        "Mediana (P50)": float(p50),
        "Moda": mode_val,
        "Nota Moda": mode_note,
        "Mínimo": min_val,
        "Máximo": max_val,
        "Amplitude": max_val - min_val,
        "Variância (amostral)": var_val,
        "Desvio Padrão (amostral)": std_val,
        "Coef. Variação (%)": cv_pct,
        "IQR (P75 - P25)": float(p75 - p25),
        "P5": float(p5),
        "P10": float(p10),
        "P25": float(p25),
        "P75": float(p75),
        "P90": float(p90),
        "P95": float(p95),
        "Assimetria (Skewness)": skew_val,
        "Curtose": kurt_val,
    }


def build_descriptive_table(
    df: pd.DataFrame,
    kpi_keys: list[str],
    level: str = "panel",
) -> pd.DataFrame:
    """Gera tabela estatística descritiva para múltiplos KPIs respeitando o nível de agregação."""
    rows = []
    for k in kpi_keys:
        if k not in KPI_CATALOG:
            continue
        meta = KPI_CATALOG[k]
        if level == "resumo":
            col = meta.resumo_sheet_col
        else:
            col = f"kpi_{k}"
        if not col or col not in df.columns:
            continue
        rows.append(compute_descriptive_stats(df[col], variable_label=meta.name, unit=meta.unit))
    return pd.DataFrame(rows)


def validate_against_kpis_estatisticas(store: ProcessedDataStore) -> pd.DataFrame:
    """Confronta as estatísticas recalculadas sobre `Resumo_Cenarios` (N=1200) com `KPIs_Estatisticas`."""
    if store.estatisticas_ref.empty or store.resumo.empty:
        return pd.DataFrame()

    est_ref = store.estatisticas_ref.set_index("KPI / Indicador")
    rows = []

    for key, meta in KPI_CATALOG.items():
        if not meta.estatisticas_name or not meta.resumo_sheet_col:
            continue
        if meta.estatisticas_name not in est_ref.index or meta.resumo_sheet_col not in store.resumo.columns:
            continue

        ref_row = est_ref.loc[meta.estatisticas_name]
        s = pd.to_numeric(store.resumo[meta.resumo_sheet_col], errors="coerce").dropna()
        calc = compute_descriptive_stats(s, meta.name, meta.unit)

        mean_diff = abs(float(ref_row["Média"]) - calc["Média"])
        std_diff = abs(float(ref_row["Desvio padrão (amostral)"]) - calc["Desvio Padrão (amostral)"])
        med_diff = abs(float(ref_row["P50 (Mediana)"]) - calc["Mediana (P50)"])
        denom = max(abs(float(ref_row["Média"])), 1.0)
        rel_err = max(mean_diff, std_diff, med_diff) / denom

        rows.append({
            "Indicador": meta.name,
            "Unidade": meta.unit,
            "N (Planilha)": int(ref_row["N"]),
            "N (Calculado)": calc["N"],
            "Média (Planilha)": float(ref_row["Média"]),
            "Média (Calculada)": calc["Média"],
            "DP (Planilha)": float(ref_row["Desvio padrão (amostral)"]),
            "DP (Calculado)": calc["Desvio Padrão (amostral)"],
            "Mediana (Planilha)": float(ref_row["P50 (Mediana)"]),
            "Mediana (Calculada)": calc["Mediana (P50)"],
            "Erro Relativo Máx.": rel_err,
            "Status": "Validado (100%)" if (rel_err <= 1e-6 and int(ref_row["N"]) == calc["N"]) else "Divergente",
        })

    return pd.DataFrame(rows)


def compute_correlation_matrix(
    df: pd.DataFrame,
    columns_map: dict[str, str],
    method: str = "pearson",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Calcula matriz de correlação (Pearson ou Spearman) e matriz de p-valores bicaudais."""
    valid_cols = [c for c in columns_map if c in df.columns]
    sub = df[valid_cols].apply(pd.to_numeric, errors="coerce")
    # Remove colunas constantes (desvio padrão zero, como premissas fixas) para evitar NaN na matriz
    non_const = [c for c in valid_cols if sub[c].dropna().nunique() > 1]
    sub = sub[non_const]
    labels = [columns_map[c] for c in non_const]

    k = len(non_const)
    corr_mat = np.eye(k, dtype=float)
    pval_mat = np.zeros((k, k), dtype=float)

    for i in range(k):
        for j in range(i + 1, k):
            pair = sub[[non_const[i], non_const[j]]].dropna()
            if len(pair) < 3:
                r, p = np.nan, np.nan
            elif method == "spearman":
                res = stats.spearmanr(pair.iloc[:, 0], pair.iloc[:, 1])
                r, p = float(res.statistic), float(res.pvalue)
            else:
                res = stats.pearsonr(pair.iloc[:, 0], pair.iloc[:, 1])
                r, p = float(res.statistic), float(res.pvalue)
            corr_mat[i, j] = corr_mat[j, i] = r
            pval_mat[i, j] = pval_mat[j, i] = p

    return (
        pd.DataFrame(corr_mat, index=labels, columns=labels),
        pd.DataFrame(pval_mat, index=labels, columns=labels),
    )


def run_distribution_normality_and_group_test(
    df: pd.DataFrame,
    value_col: str,
    group_col: str | None = None,
) -> dict[str, Any]:
    """Executa teste de normalidade e comparação inferencial não paramétrica (Kruskal-Wallis) entre grupos/períodos."""
    s = pd.to_numeric(df[value_col], errors="coerce").dropna()
    out: dict[str, Any] = {"n": len(s)}
    if len(s) < 8:
        out["normality_test"] = "Amostra insuficiente (N < 8)"
        out["normality_pvalue"] = np.nan
        out["is_normal_5pct"] = None
        return out

    # Shapiro-Wilk até 5000 observações (amostra determinística se maior)
    sample_s = s.sample(5000, random_state=42) if len(s) > 5000 else s
    sw_stat, sw_p = stats.shapiro(sample_s)
    out["normality_test"] = "Shapiro-Wilk"
    out["normality_stat"] = float(sw_stat)
    out["normality_pvalue"] = float(sw_p)
    out["is_normal_5pct"] = bool(sw_p >= 0.05)

    if group_col and group_col in df.columns:
        groups = [
            pd.to_numeric(g[value_col], errors="coerce").dropna().to_numpy()
            for _, g in df.groupby(group_col)
        ]
        groups = [g for g in groups if len(g) >= 3]
        if len(groups) >= 2:
            try:
                kw_stat, kw_p = stats.kruskal(*groups)
                out["group_test"] = "Kruskal-Wallis (diferença de medianas entre grupos/períodos)"
                out["group_stat"] = float(kw_stat)
                out["group_pvalue"] = float(kw_p)
                out["groups_differ_5pct"] = bool(kw_p < 0.05)
            except ValueError:
                out["group_test"] = "Variância nula entre grupos"
                out["group_pvalue"] = np.nan
                out["groups_differ_5pct"] = False

    return out

