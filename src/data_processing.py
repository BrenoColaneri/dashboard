"""Preparação, tipagem, normalização e integração das camadas Staging -> Processed.

Regras metodológicas aplicadas:
- Respeito estrito à granularidade:
  1. `panel` (granularidade `Cenário × Ano`, 12 períodos numerados `Ano 1`..`Ano 12`):
     integra `DRE_Cenarios`, `Balanco_Cenarios`, `DFC_Cenarios` e `KPIs_Cenarios` por `(Cenário, Ano)`.
  2. `resumo` e `ranking` (granularidade `Cenário`, consolidada pela média dos Anos 1 a 11):
     mantidos em estruturas independentes para evitar duplicação ou agregação indevida.
- Nenhum período numerado (`1`..`12`) é convertido em ano civil (2024, 2025, etc.).
- Os sinais contábeis originais da base CTI são integralmente preservados nas colunas originais;
  colunas derivadas e KPIs recalculados são adicionados com nomes explícitos e auditáveis.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import WACC_MODEL_PREMISE, format_period_label
from src.data_loader import RawDatasetBundle, get_data_dir


@dataclass
class ProcessedDataStore:
    """Repositório analítico em memória da camada Processed."""

    bundle: RawDatasetBundle
    dre: pd.DataFrame
    balanco: pd.DataFrame
    dfc: pd.DataFrame
    kpis_orig: pd.DataFrame
    panel: pd.DataFrame          # Base integrada Cenário × Ano (com KPIs originais e recalculados)
    resumo: pd.DataFrame         # Base consolidada por Cenário (Resumo_Cenarios)
    ranking: pd.DataFrame        # Classificação geral (Ranking_Cenarios)
    top10: pd.DataFrame          # Rankings por categoria (Top10_Rankings)
    estatisticas_ref: pd.DataFrame  # KPIs_Estatisticas do modelo de planejamento
    dicionario_ref: pd.DataFrame    # Dicionario_KPIs original do modelo de planejamento
    scenarios: list[str]
    periods: list[int]
    wacc_premise: float


def clean_column_name(col: object) -> str:
    """Remove espaços duplos e espaços nas extremidades mantendo acentuação e semântica original."""
    text = str(col).strip()
    return re.sub(r"\s+", " ", text)


def _prepare_scenario_period_df(df: pd.DataFrame) -> pd.DataFrame:
    """Padroniza cabeçalhos, chaves `(Cenário, Ano)` e tipos numéricos sem destruir valores."""
    out = df.copy()
    out.columns = [clean_column_name(c) for c in out.columns]

    # Remove colunas auxiliares vazias ou metadados laterais da aba KPIs_Cenarios (ex.: Unnamed: 21, WACC, 0.12)
    drop_cols = [
        c for c in out.columns
        if c.lower().startswith("unnamed:") or c in ("WACC", "0.12", "0,12")
    ]
    if drop_cols:
        out = out.drop(columns=drop_cols, errors="ignore")

    if "Cenário" in out.columns:
        out["Cenário"] = out["Cenário"].astype(str).str.strip()
    if "Ano" in out.columns:
        out["Ano"] = pd.to_numeric(out["Ano"], errors="coerce").astype("Int64")

    # Converte demais colunas para float64 preservando NaNs originais
    for col in out.columns:
        if col not in ("Cenário", "Ano"):
            out[col] = pd.to_numeric(out[col], errors="coerce")

    if "Cenário" in out.columns and "Ano" in out.columns:
        out = out.dropna(subset=["Cenário", "Ano"]).copy()
        out["Ano"] = out["Ano"].astype(int)
        out = out.sort_values(["Cenário", "Ano"]).reset_index(drop=True)
        out["Período"] = out["Ano"].map(format_period_label)

    return out


def _prepare_consolidated_df(df: pd.DataFrame) -> pd.DataFrame:
    """Padroniza abas consolidadas no nível de Cenário (`Resumo_Cenarios`, `Ranking_Cenarios`)."""
    out = df.copy()
    out.columns = [clean_column_name(c) for c in out.columns]
    if "Cenário" in out.columns:
        out["Cenário"] = out["Cenário"].astype(str).str.strip()
    for col in out.columns:
        if col != "Cenário":
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out.reset_index(drop=True)


def _extract_wacc_from_kpis_sheet(raw_kpis_df: pd.DataFrame) -> float:
    """Extrai a premissa de WACC documentada no cabeçalho de `KPIs_Cenarios` (padrão 0.12)."""
    cols = [str(c).strip() for c in raw_kpis_df.columns]
    if "WACC" in cols:
        idx = cols.index("WACC")
        if idx + 1 < len(cols):
            try:
                val = float(str(cols[idx + 1]).replace(",", "."))
                if 0.0 < val < 1.0:
                    return val
            except ValueError:
                pass
    return WACC_MODEL_PREMISE


def process_dataset(
    bundle: RawDatasetBundle,
    persist_processed: bool = True,
    processed_dir: Path | None = None,
) -> ProcessedDataStore:
    """Executa o pipeline completo Staging -> Processed e integra os indicadores recalculados."""
    from src.financial_kpis import compute_recalculated_kpis

    wacc_val = _extract_wacc_from_kpis_sheet(bundle.sheets["KPIs_Cenarios"])

    dre = _prepare_scenario_period_df(bundle.sheets["DRE_Cenarios"])
    balanco = _prepare_scenario_period_df(bundle.sheets["Balanco_Cenarios"])
    dfc = _prepare_scenario_period_df(bundle.sheets["DFC_Cenarios"])
    kpis_orig = _prepare_scenario_period_df(bundle.sheets["KPIs_Cenarios"])
    resumo = _prepare_consolidated_df(bundle.sheets["Resumo_Cenarios"])

    if "Ranking_Cenarios" in bundle.sheets:
        ranking = _prepare_consolidated_df(bundle.sheets["Ranking_Cenarios"])
    else:
        ranking = pd.DataFrame()

    if "Top10_Rankings" in bundle.sheets:
        top10 = bundle.sheets["Top10_Rankings"].copy()
        top10.columns = [clean_column_name(c) for c in top10.columns]
        if "Indicador" in top10.columns:
            top10["Indicador"] = pd.to_numeric(top10["Indicador"], errors="coerce")
        if "Posição" in top10.columns:
            top10["Posição"] = pd.to_numeric(top10["Posição"], errors="coerce").fillna(0).astype(int)
    else:
        top10 = pd.DataFrame()

    if "KPIs_Estatisticas" in bundle.sheets:
        estatisticas_ref = bundle.sheets["KPIs_Estatisticas"].copy()
        estatisticas_ref.columns = [clean_column_name(c) for c in estatisticas_ref.columns]
    else:
        estatisticas_ref = pd.DataFrame()

    dicionario_ref = bundle.sheets["Dicionario_KPIs"].copy()
    dicionario_ref.columns = [clean_column_name(c) for c in dicionario_ref.columns]

    # Integração Cenário × Ano sem perda ou duplicação de granularidade
    merge_keys = ["Cenário", "Ano"]
    panel = (
        dre.merge(balanco.drop(columns=["Período"], errors="ignore"), on=merge_keys, how="outer")
        .merge(dfc.drop(columns=["Período"], errors="ignore"), on=merge_keys, how="outer")
        .merge(
            kpis_orig.drop(columns=["Período"], errors="ignore"),
            on=merge_keys,
            how="outer",
            suffixes=("", "_orig"),
        )
    )
    panel = panel.sort_values(merge_keys).reset_index(drop=True)
    panel["Período"] = panel["Ano"].map(format_period_label)

    # Flag explícita de incompletude estrutural do Balanço Patrimonial (ex.: Ano 12)
    pnc_col = "BAL - Exigível a Longo Prazo"
    pl_col = "BAL - Patrimônio Líquido"
    bal_incomplete = pd.Series(False, index=panel.index)
    if pnc_col in panel.columns:
        bal_incomplete = bal_incomplete | panel[pnc_col].isna()
    if pl_col in panel.columns:
        bal_incomplete = bal_incomplete | panel[pl_col].isna()
    panel["Balanco_Incompleto"] = bal_incomplete

    # Anexa colunas canônicas de KPIs recalculados (`calc_*`) e valores oficiais unificados (`kpi_*`)
    panel = compute_recalculated_kpis(panel, wacc=wacc_val)

    scenarios = sorted(panel["Cenário"].dropna().unique().tolist())
    periods = sorted(panel["Ano"].dropna().astype(int).unique().tolist())

    store = ProcessedDataStore(
        bundle=bundle,
        dre=dre,
        balanco=balanco,
        dfc=dfc,
        kpis_orig=kpis_orig,
        panel=panel,
        resumo=resumo,
        ranking=ranking,
        top10=top10,
        estatisticas_ref=estatisticas_ref,
        dicionario_ref=dicionario_ref,
        scenarios=scenarios,
        periods=periods,
        wacc_premise=wacc_val,
    )

    if persist_processed and not bundle.is_synthetic and bundle.source_type != "uploaded_excel":
        target_dir = processed_dir or (get_data_dir() / "processed")
        try:
            _persist_processed_layer(store, target_dir)
        except Exception:
            pass

    return store


def _persist_processed_layer(store: ProcessedDataStore, processed_dir: Path) -> None:
    """Materializa as tabelas analíticas na camada `data/processed/` com metadados de linhagem."""
    processed_dir.mkdir(parents=True, exist_ok=True)
    manifest_file = processed_dir / "processed_manifest.json"
    if manifest_file.exists():
        try:
            existing = json.loads(manifest_file.read_text(encoding="utf-8"))
            if existing.get("source_fingerprint") == store.bundle.fingerprint:
                if (processed_dir / "panel_cenario_ano.parquet").exists() and (
                    processed_dir / "resumo_cenarios.parquet"
                ).exists():
                    return
        except Exception:
            pass

    store.panel.to_parquet(processed_dir / "panel_cenario_ano.parquet", index=False)
    store.resumo.to_parquet(processed_dir / "resumo_cenarios.parquet", index=False)
    if not store.ranking.empty:
        store.ranking.to_parquet(processed_dir / "ranking_cenarios.parquet", index=False)

    lineage = {
        "source_name": store.bundle.source_name,
        "source_fingerprint": store.bundle.fingerprint,
        "file_modified_at": store.bundle.file_modified_at,
        "processed_at": store.bundle.loaded_at,
        "n_scenarios": len(store.scenarios),
        "n_periods": len(store.periods),
        "panel_rows": int(len(store.panel)),
        "resumo_rows": int(len(store.resumo)),
        "wacc_premise": store.wacc_premise,
        "incomplete_balance_rows": int(store.panel["Balanco_Incompleto"].sum()),
    }
    manifest_file.write_text(json.dumps(lineage, indent=2, ensure_ascii=False), encoding="utf-8")


def filter_panel(
    panel: pd.DataFrame,
    scenarios: list[str] | str | None = None,
    period_range: tuple[int, int] | None = None,
    periods: list[int] | None = None,
    exclude_incomplete_balance: bool = False,
) -> pd.DataFrame:
    """Filtra a base `Cenário × Ano` de forma determinística e segura."""
    df = panel
    if scenarios is not None:
        scen_list = [scenarios] if isinstance(scenarios, str) else list(scenarios)
        if len(scen_list) == 0:
            return df.iloc[0:0].copy()
        df = df[df["Cenário"].isin(scen_list)]

    if period_range is not None:
        p_min, p_max = int(period_range[0]), int(period_range[1])
        df = df[(df["Ano"] >= p_min) & (df["Ano"] <= p_max)]

    if periods is not None:
        if len(periods) == 0:
            return df.iloc[0:0].copy()
        df = df[df["Ano"].isin([int(p) for p in periods])]

    if exclude_incomplete_balance and "Balanco_Incompleto" in df.columns:
        df = df[~df["Balanco_Incompleto"]]

    return df.copy()

