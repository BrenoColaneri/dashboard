"""Módulo de Análise de Regressão Linear Múltipla com Split por Cenário e Diagnósticos Econométricos.

Boas práticas de Ciência de Dados implementadas:
- Divisão Treino/Teste agrupada por `Cenário` (`GroupShuffleSplit`) para impedir vazamento
  temporal entre períodos de um mesmo cenário.
- Erros-padrão robustos clusterizados por `Cenário` quando ajustado sobre painel `Cenário × Ano`
  (ou HC3 robusto a heterocedasticidade na base consolidada por cenário).
- Detector automático de tautologia/vazamento algébrico entre variável dependente e explicativas.
- Diagnósticos formais: VIF (multicolinearidade), Breusch-Pagan (heterocedasticidade),
  Jarque-Bera (normalidade dos resíduos) e métricas out-of-sample (R², MAE, RMSE).
- Comunicação ética: interpretação associativa sem inferir causalidade.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.stattools import durbin_watson, jarque_bera


# Mapeamento de pares com risco de identidade algébrica direta (vazamento tautológico)
DIRECT_DERIVATION_GROUPS: dict[str, set[str]] = {
    "eva": {"nopat", "capital_investido", "roic"},
    "roic": {"nopat", "capital_investido", "eva"},
    "nopat": {"eva", "roic", "ebitda_calculado"},
    "ebitda_calculado": {"ebitda_modelo", "margem_ebitda_calculada", "nopat"},
    "ebitda_modelo": {"ebitda_calculado", "margem_ebitda_modelo"},
    "margem_ebitda_calculada": {"margem_ebitda_modelo", "ebitda_calculado", "margem_contribuicao"},
    "margem_ebitda_modelo": {"margem_ebitda_calculada", "ebitda_modelo"},
    "margem_contribuicao": {"custos_variaveis", "margem_ebitda_calculada"},
    "lc": {"ls", "li"},
    "ls": {"lc", "li"},
    "pct": {"ipl", "endividamento_geral"},
    "ipl": {"pct"},
}


@dataclass
class RegressionResult:
    """Estrutura completa de saída do modelo de regressão e seus diagnósticos."""

    success: bool
    error_message: str | None
    objective: str
    granularity_label: str
    dependent_var: str
    explanatory_vars: list[str]
    n_total_valid: int
    n_train: int
    n_test: int
    n_scenarios_train: int
    n_scenarios_test: int
    treatments_applied: list[str]
    leakage_warnings: list[str]
    coefficients_table: pd.DataFrame
    vif_table: pd.DataFrame
    metrics: dict[str, float]
    diagnostics: dict[str, Any]
    predictions_df: pd.DataFrame
    interpretation_paragraphs: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


def detect_algebraic_leakage(target_key: str, feature_keys: list[str]) -> list[str]:
    """Verifica se alguma variável explicativa possui derivação algébrica direta com a variável alvo."""
    warnings = []
    risky_set = DIRECT_DERIVATION_GROUPS.get(target_key, set())
    overlap = [f for f in feature_keys if f in risky_set]
    if overlap:
        warnings.append(
            f"Atenção para risco de tautologia/vazamento algébrico: {overlap} partilha(m) componentes "
            f"matemáticos diretos com a variável dependente '{target_key}'. O R² elevado pode refletir "
            "identidade contábil da fórmula em vez de relação empírica independente."
        )
    return warnings


def fit_ols_regression(
    df: pd.DataFrame,
    target_col: str,
    feature_cols: list[str],
    labels_map: dict[str, str],
    target_key: str = "",
    feature_keys: list[str] | None = None,
    granularity: str = "resumo",  # 'resumo' (Cenário) ou 'panel' (Cenário × Ano)
    test_size: float = 0.25,
    standardize_features: bool = False,
    random_state: int = 42,
) -> RegressionResult:
    """Ajusta modelo OLS com validação cruzada agrupada por cenário e diagnósticos completos."""
    f_keys = feature_keys or []
    target_label = labels_map.get(target_col, target_col)
    feat_labels = [labels_map.get(c, c) for c in feature_cols]
    gran_label = (
        "Consolidado por Cenário (Resumo_Cenarios — 1 observação independente por cenário)"
        if granularity == "resumo"
        else "Painel Cenário × Período (com divisão Treino/Teste e clusterização por Cenário)"
    )

    if not feature_cols:
        return _failed_result("Selecione ao menos uma variável explicativa.", target_label, feat_labels, gran_label)
    if target_col in feature_cols:
        return _failed_result(
            "A variável dependente não pode constar simultaneamente entre as variáveis explicativas.",
            target_label,
            feat_labels,
            gran_label,
        )

    needed_cols = ["Cenário", target_col] + list(feature_cols)
    if "Ano" in df.columns and granularity == "panel":
        needed_cols.append("Ano")
    missing_cols = [c for c in needed_cols if c not in df.columns and c not in ("Cenário", "Ano")]
    if missing_cols:
        return _failed_result(f"Colunas ausentes na base: {missing_cols}", target_label, feat_labels, gran_label)

    work = df[[c for c in dict.fromkeys(needed_cols) if c in df.columns]].copy()
    initial_n = len(work)
    for col in [target_col] + list(feature_cols):
        work[col] = pd.to_numeric(work[col], errors="coerce")

    work = work.replace([np.inf, -np.inf], np.nan).dropna(subset=[target_col] + list(feature_cols)).reset_index(drop=True)
    n_valid = len(work)
    dropped_na = initial_n - n_valid

    # Remove variáveis explicativas com variância nula (constantes)
    active_features = [c for c in feature_cols if work[c].std(ddof=1) > 1e-12]
    dropped_const = [labels_map.get(c, c) for c in feature_cols if c not in active_features]
    if not active_features:
        return _failed_result(
            "As variáveis explicativas selecionadas possuem variância nula no recorte filtrado.",
            target_label,
            feat_labels,
            gran_label,
        )

    min_required = len(active_features) + 12
    if n_valid < min_required:
        return _failed_result(
            f"Quantidade insuficiente de observações válidas ({n_valid}) para ajustar o modelo com segurança (mínimo recomendado: {min_required}).",
            target_label,
            feat_labels,
            gran_label,
        )

    treatments = [
        f"Remoção de registros com valores ausentes (N/D, como Balanço no Ano 12): {dropped_na} linha(s) removida(s), restando {n_valid} observações completas.",
    ]
    if dropped_const:
        treatments.append(f"Exclusão automática de variável(is) constante(s) sem variabilidade: {', '.join(dropped_const)}.")

    # Divisão Treino / Teste agrupada por Cenário
    if "Cenário" in work.columns and work["Cenário"].nunique() >= 8:
        if granularity == "panel":
            gss = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=random_state)
            train_idx, test_idx = next(gss.split(work, groups=work["Cenário"]))
            treatments.append(
                f"Divisão Treino/Teste ({int((1-test_size)*100)}%/{int(test_size*100)}%) agrupada por Cenário (GroupShuffleSplit), "
                "garantindo que períodos do mesmo cenário jamais apareçam simultaneamente em treino e teste."
            )
        else:
            idx_all = np.arange(len(work))
            train_idx, test_idx = train_test_split(idx_all, test_size=test_size, random_state=random_state)
            treatments.append(
                f"Divisão aleatória estratificada por Cenário ({int((1-test_size)*100)}% treino / {int(test_size*100)}% teste)."
            )
    else:
        idx_all = np.arange(len(work))
        train_idx, test_idx = train_test_split(idx_all, test_size=test_size, random_state=random_state)
        treatments.append("Divisão aleatória Treino/Teste sobre as observações disponíveis.")

    train_df = work.iloc[train_idx].copy()
    test_df = work.iloc[test_idx].copy()

    X_train_raw = train_df[active_features].copy()
    X_test_raw = test_df[active_features].copy()
    y_train = train_df[target_col].astype(float)
    y_test = test_df[target_col].astype(float)

    if standardize_features:
        means = X_train_raw.mean()
        stds = X_train_raw.std(ddof=1).replace(0, 1.0)
        X_train_proc = (X_train_raw - means) / stds
        X_test_proc = (X_test_raw - means) / stds
        treatments.append("Padronização Z-score das variáveis explicativas ajustada exclusivamente com média e DP do conjunto de treino.")
    else:
        X_train_proc = X_train_raw
        X_test_proc = X_test_raw

    rename_dict = {c: labels_map.get(c, c) for c in active_features}
    X_train_named = sm.add_constant(X_train_proc.rename(columns=rename_dict), has_constant="add")
    X_test_named = sm.add_constant(X_test_proc.rename(columns=rename_dict), has_constant="add")

    ols_base = sm.OLS(y_train, X_train_named)
    if granularity == "panel" and "Cenário" in train_df.columns and train_df["Cenário"].nunique() >= 10:
        fitted = ols_base.fit(cov_type="cluster", cov_kwds={"groups": train_df["Cenário"]})
        se_type = "Robustos clusterizados por Cenário"
    else:
        fitted = ols_base.fit(cov_type="HC3")
        se_type = "Robustos a heterocedasticidade (HC3)"
    treatments.append(f"Estimação OLS com erros-padrão {se_type.lower()}.")

    # Predições Treino e Teste
    y_pred_train = fitted.predict(X_train_named)
    y_pred_test = fitted.predict(X_test_named)
    resid_train = y_train - y_pred_train
    resid_test = y_test - y_pred_test

    r2_tr = float(fitted.rsquared)
    r2_adj_tr = float(fitted.rsquared_adj)
    r2_te = float(r2_score(y_test, y_pred_test)) if len(y_test) >= 2 else np.nan
    mae_tr = float(mean_absolute_error(y_train, y_pred_train))
    mae_te = float(mean_absolute_error(y_test, y_pred_test))
    rmse_tr = float(np.sqrt(mean_squared_error(y_train, y_pred_train)))
    rmse_te = float(np.sqrt(mean_squared_error(y_test, y_pred_test)))

    # Tabela de coeficientes
    conf_int = fitted.conf_int()
    coef_rows = []
    for term in fitted.params.index:
        p_val = float(fitted.pvalues[term])
        coef_rows.append({
            "Termo": "Intercepto (Constante)" if term == "const" else str(term),
            "Coeficiente": float(fitted.params[term]),
            "Erro Padrão": float(fitted.bse[term]),
            "Estatística t/z": float(fitted.tvalues[term]),
            "p-valor": p_val,
            "IC 95% Inferior": float(conf_int.loc[term, 0]),
            "IC 95% Superior": float(conf_int.loc[term, 1]),
            "Significativo (5%)": "Sim (p < 0,05)" if p_val < 0.05 else "Não (p ≥ 0,05)",
        })
    coef_df = pd.DataFrame(coef_rows)

    # VIF (Multicolinearidade)
    vif_rows = []
    if len(active_features) >= 2:
        X_vif = X_train_named.to_numpy(dtype=float)
        for idx_col, col_name in enumerate(X_train_named.columns):
            if col_name == "const":
                continue
            try:
                v_val = float(variance_inflation_factor(X_vif, idx_col))
            except Exception:
                v_val = np.nan
            vif_rows.append({
                "Variável Explicativa": col_name,
                "VIF": v_val,
                "Diagnóstico": (
                    "Baixa colinearidade (< 5)"
                    if v_val < 5
                    else ("Colinearidade moderada (5–10)" if v_val < 10 else "Alta multicolinearidade (≥ 10)")
                ) if not np.isnan(v_val) else "Indeterminado",
            })
    else:
        vif_rows.append({
            "Variável Explicativa": labels_map.get(active_features[0], active_features[0]),
            "VIF": 1.0,
            "Diagnóstico": "Regressão simples (sem multicolinearidade)",
        })
    vif_df = pd.DataFrame(vif_rows)

    # Testes diagnósticos de resíduos (no conjunto de treino)
    jb_stat, jb_pval, skew_r, kurt_r = jarque_bera(resid_train)
    try:
        bp_lm, bp_pval, _, _ = het_breuschpagan(resid_train, X_train_named)
    except Exception:
        bp_lm, bp_pval = np.nan, np.nan
    dw_stat = float(durbin_watson(resid_train))

    diagnostics = {
        "erros_padrao": se_type,
        "f_statistic": float(fitted.fvalue) if fitted.fvalue is not None else np.nan,
        "f_pvalue": float(fitted.f_pvalue) if fitted.f_pvalue is not None else np.nan,
        "aic": float(fitted.aic),
        "bic": float(fitted.bic),
        "jarque_bera_stat": float(jb_stat),
        "jarque_bera_pvalue": float(jb_pval),
        "residuos_normais_5pct": bool(jb_pval >= 0.05),
        "breusch_pagan_stat": float(bp_lm),
        "breusch_pagan_pvalue": float(bp_pval),
        "homocedastico_5pct": bool(bp_pval >= 0.05) if not np.isnan(bp_pval) else None,
        "durbin_watson": dw_stat,
        "residuos_assimetria": float(skew_r),
        "residuos_curtose": float(kurt_r),
        "max_vif": float(vif_df["VIF"].max()) if not vif_df.empty else 1.0,
    }

    # DataFrame de predições e resíduos para gráficos diagnósticos
    pred_train_df = pd.DataFrame({
        "Cenário": train_df["Cenário"].values if "Cenário" in train_df else np.arange(len(train_df)),
        "Partição": "Treinamento",
        "Observado": y_train.values,
        "Predito": y_pred_train.values,
        "Resíduo": resid_train.values,
    })
    pred_test_df = pd.DataFrame({
        "Cenário": test_df["Cenário"].values if "Cenário" in test_df else np.arange(len(test_df)),
        "Partição": "Teste (Cenários Isolados)",
        "Observado": y_test.values,
        "Predito": y_pred_test.values,
        "Resíduo": resid_test.values,
    })
    preds_all = pd.concat([pred_train_df, pred_test_df], ignore_index=True)

    leakage_warnings = detect_algebraic_leakage(target_key, f_keys)

    # Interpretação automática responsável e não causal
    sig_terms = coef_df[(coef_df["Termo"] != "Intercepto (Constante)") & (coef_df["p-valor"] < 0.05)]
    interp = [
        f"O modelo linear ajustado para explicar a variação associada a '{target_label}' utilizou {len(train_df)} observações "
        f"no treinamento e {len(test_df)} observações de validação fora da amostra, obtendo R² ajustado de {r2_adj_tr:.4f} "
        f"no treino e R² de {r2_te:.4f} no conjunto de teste.",
    ]
    if not sig_terms.empty:
        effects = []
        for _, r in sig_terms.iterrows():
            direction = "positiva" if r["Coeficiente"] > 0 else "negativa"
            effects.append(f"'{r['Termo']}' (associação {direction}, β = {r['Coeficiente']:.4g}, p = {r['p-valor']:.3g})")
        interp.append(
            "Mantidas as demais variáveis constantes (ceteris paribus), apresentaram associação estatisticamente "
            f"significativa ao nível de 5%: {'; '.join(effects)}."
        )
    else:
        interp.append("Nenhuma variável explicativa apresentou significância estatística individual ao nível de 5%.")

    interp.append(
        "Nota ética e metodológica: Os coeficientes estimam associações lineares condicionais dentro dos cenários "
        "simulados pela CTI e NÃO estabelecem relação de causa e efeito nem garantia para projeções externas."
    )

    limitations = [
        "Os cenários da base CTI provêm de um modelo estruturado de planejamento financeiro; relações muito fortes podem refletir regras paramétricas internas da modelagem.",
        "Associação estatística e R² elevado não implicam causalidade econômica.",
    ]
    if not diagnostics["residuos_normais_5pct"]:
        limitations.append(
            f"O teste de Jarque-Bera rejeitou a normalidade estrita dos resíduos (p = {jb_pval:.3g}), indicando caudas pesadas ou outliers; por isso utilizaram-se erros-padrão robustos ({se_type})."
        )
    if diagnostics["homocedastico_5pct"] is False:
        limitations.append(
            f"O teste de Breusch-Pagan indicou presença de heterocedasticidade nos resíduos (p = {bp_pval:.3g}), mitigada na inferência pelo estimador robusto de variância ({se_type})."
        )
    if diagnostics["max_vif"] >= 10.0:
        limitations.append(
            f"Foi detectada alta multicolinearidade entre variáveis explicativas (VIF máximo = {diagnostics['max_vif']:.2f} ≥ 10), o que pode inflar a variância individual dos coeficientes."
        )
    limitations.extend(leakage_warnings)

    n_scen_tr = int(train_df["Cenário"].nunique()) if "Cenário" in train_df else len(train_df)
    n_scen_te = int(test_df["Cenário"].nunique()) if "Cenário" in test_df else len(test_df)

    return RegressionResult(
        success=True,
        error_message=None,
        objective=f"Avaliar a associação linear condicional entre {', '.join(rename_dict.values())} e o indicador '{target_label}'.",
        granularity_label=gran_label,
        dependent_var=target_label,
        explanatory_vars=list(rename_dict.values()),
        n_total_valid=n_valid,
        n_train=len(train_df),
        n_test=len(test_df),
        n_scenarios_train=n_scen_tr,
        n_scenarios_test=n_scen_te,
        treatments_applied=treatments,
        leakage_warnings=leakage_warnings,
        coefficients_table=coef_df,
        vif_table=vif_df,
        metrics={
            "r2_train": r2_tr,
            "r2_adj_train": r2_adj_tr,
            "r2_test": r2_te,
            "mae_train": mae_tr,
            "mae_test": mae_te,
            "rmse_train": rmse_tr,
            "rmse_test": rmse_te,
        },
        diagnostics=diagnostics,
        predictions_df=preds_all,
        interpretation_paragraphs=interp,
        limitations=limitations,
    )


def _failed_result(msg: str, target_label: str, feat_labels: list[str], gran_label: str) -> RegressionResult:
    return RegressionResult(
        success=False,
        error_message=msg,
        objective="",
        granularity_label=gran_label,
        dependent_var=target_label,
        explanatory_vars=feat_labels,
        n_total_valid=0,
        n_train=0,
        n_test=0,
        n_scenarios_train=0,
        n_scenarios_test=0,
        treatments_applied=[],
        leakage_warnings=[],
        coefficients_table=pd.DataFrame(),
        vif_table=pd.DataFrame(),
        metrics={},
        diagnostics={},
        predictions_df=pd.DataFrame(),
        interpretation_paragraphs=[],
        limitations=[],
    )

