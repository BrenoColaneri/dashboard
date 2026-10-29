"""Carregamento seguro e descoberta automática da planilha original (Camada Raw -> Staging).

Regras de governança atendidas:
- Preserva integralmente o arquivo Excel original da base de planejamento (somente leitura).
- Localiza automaticamente `Contabilidade e Finanças(4).xlsx`, `Contabilidade e Finanças.xlsx`
  ou caminho configurado via `CTI_EXCEL_PATH`, na raiz ou em `data/raw/`.
- Suporta upload seguro em memória (`BytesIO`) para execução em nuvem sem exposição pública da base.
- Materializa cache Parquet na camada `data/staging/` vinculado à assinatura (tamanho + mtime + hash parcial)
  do arquivo bruto, reduzindo o tempo de leitura de ~35s para <0,2s sem alterar dados de origem.
- Jamais apresenta dados fictícios como se fossem a planilha real.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO

import numpy as np
import pandas as pd

from src.config import ESSENTIAL_SHEETS, EXPECTED_SHEETS


@dataclass
class RawDatasetBundle:
    """Representa o pacote bruto carregado da fonte original."""

    sheets: dict[str, pd.DataFrame]
    source_name: str
    source_path: str | None
    source_type: str  # 'local_excel' | 'staging_cache' | 'uploaded_excel' | 'synthetic_demo'
    file_size_bytes: int
    file_modified_at: str
    loaded_at: str
    fingerprint: str
    available_sheets: list[str] = field(default_factory=list)
    missing_sheets: list[str] = field(default_factory=list)
    is_synthetic: bool = False


def get_project_root() -> Path:
    """Retorna o diretório raiz do projeto de forma independente do diretório corrente."""
    return Path(__file__).resolve().parent.parent


def get_data_dir(custom_dir: str | Path | None = None) -> Path:
    """Retorna o diretório base das camadas `raw`, `staging` e `processed`."""
    if custom_dir:
        return Path(custom_dir).resolve()
    env_dir = os.environ.get("CTI_DATA_DIR")
    if env_dir:
        p = Path(env_dir)
        return p if p.is_absolute() else (get_project_root() / p).resolve()
    return get_project_root() / "data"


def discover_excel_path(explicit_path: str | Path | None = None) -> Path | None:
    """Localiza a planilha do modelo de planejamento sem presumir caminho fixo codificado.

    Se `explicit_path` for informado explicitamente, valida apenas esse caminho (sem fallback silencioso).
    """
    root = get_project_root()
    data_dir = get_data_dir()

    if explicit_path is not None:
        p = Path(explicit_path)
        resolved = p if p.is_absolute() else (root / p)
        if resolved.exists() and resolved.is_file() and not resolved.name.startswith("~$"):
            return resolved.resolve()
        return None

    candidates: list[Path] = []
    env_path = os.environ.get("CTI_EXCEL_PATH")
    if env_path:
        p = Path(env_path)
        resolved_env = p if p.is_absolute() else (root / p)
        if resolved_env.exists() and resolved_env.is_file() and not resolved_env.name.startswith("~$"):
            return resolved_env.resolve()
        return None

    # Padrões prioritários na pasta data/raw e na raiz do projeto
    search_dirs = [data_dir / "raw", data_dir, root]
    priority_names = [
        "Contabilidade e Finanças(4).xlsx",
        "Contabilidade e Finanças.xlsx",
        "Contabilidade_e_Financas(4).xlsx",
        "Contabilidade_e_Financas.xlsx",
    ]
    for d in search_dirs:
        if d.exists() and d.is_dir():
            for name in priority_names:
                candidates.append(d / name)

    for cand in candidates:
        if cand.exists() and cand.is_file() and not cand.name.startswith("~$"):
            return cand.resolve()

    # Busca ampla por arquivos .xlsx válidos no projeto (ignorando temporários e pastas ocultas)
    excluded_parts = {".venv", "venv", ".git", "__pycache__", ".pytest_cache"}
    for d in search_dirs:
        if not (d.exists() and d.is_dir()):
            continue
        for xlsx in sorted(d.glob("*.xlsx")):
            if xlsx.name.startswith("~$"):
                continue
            if any(part in excluded_parts for part in xlsx.parts):
                continue
            return xlsx.resolve()

    return None


def compute_file_fingerprint(file_path: Path) -> str:
    """Gera assinatura SHA-256 determinística combinando metadados e blocos do arquivo."""
    stat = file_path.stat()
    hasher = hashlib.sha256()
    hasher.update(f"{file_path.name}:{stat.st_size}:{stat.st_mtime_ns}".encode("utf-8"))
    with file_path.open("rb") as fh:
        # Lê primeiro e último 1 MB para validação rápida e confiável de integridade
        head = fh.read(1024 * 1024)
        hasher.update(head)
        if stat.st_size > 2 * 1024 * 1024:
            fh.seek(-1024 * 1024, os.SEEK_END)
            hasher.update(fh.read(1024 * 1024))
    return hasher.hexdigest()[:20]


def compute_bytes_fingerprint(raw_bytes: bytes, filename: str) -> str:
    """Gera assinatura SHA-256 para planilha enviada via upload."""
    hasher = hashlib.sha256()
    hasher.update(filename.encode("utf-8"))
    hasher.update(raw_bytes)
    return hasher.hexdigest()[:20]


def _normalize_sheet_columns_for_parquet(df: pd.DataFrame) -> pd.DataFrame:
    """Converte nomes de colunas para string preservando o conteúdo original para armazenamento Parquet."""
    out = df.copy()
    out.columns = [str(col) for col in out.columns]
    # Colunas do tipo object mistas (ex.: int e str) são convertidas com segurança
    for col in out.columns:
        if out[col].dtype == "object":
            non_null = out[col].dropna()
            if len(non_null) > 0 and not all(isinstance(v, str) for v in non_null):
                out[col] = out[col].astype(str).where(out[col].notna(), None)
    return out


def _save_staging_cache(bundle: RawDatasetBundle, staging_dir: Path) -> None:
    """Persiste as abas lidas na camada `data/staging/` com manifesto rastreável."""
    staging_dir.mkdir(parents=True, exist_ok=True)
    sheet_files: dict[str, str] = {}
    for sheet_name, df in bundle.sheets.items():
        safe_df = _normalize_sheet_columns_for_parquet(df)
        fname = f"staging_{sheet_name}.parquet"
        safe_df.to_parquet(staging_dir / fname, index=False)
        sheet_files[sheet_name] = fname

    manifest = {
        "fingerprint": bundle.fingerprint,
        "source_name": bundle.source_name,
        "source_path": bundle.source_path,
        "file_size_bytes": bundle.file_size_bytes,
        "file_modified_at": bundle.file_modified_at,
        "cached_at": bundle.loaded_at,
        "available_sheets": bundle.available_sheets,
        "missing_sheets": bundle.missing_sheets,
        "sheet_files": sheet_files,
    }
    (staging_dir / "staging_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _try_load_staging_cache(
    fingerprint: str,
    staging_dir: Path,
    source_path: Path,
) -> RawDatasetBundle | None:
    """Carrega da camada `data/staging/` se e somente se a assinatura coincidir com o arquivo bruto."""
    manifest_path = staging_dir / "staging_manifest.json"
    if not manifest_path.exists():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("fingerprint") != fingerprint:
            return None
        sheets: dict[str, pd.DataFrame] = {}
        for sheet_name, fname in manifest.get("sheet_files", {}).items():
            fpath = staging_dir / fname
            if not fpath.exists():
                return None
            sheets[sheet_name] = pd.read_parquet(fpath)
        if not all(req in sheets for req in ESSENTIAL_SHEETS):
            return None
        return RawDatasetBundle(
            sheets=sheets,
            source_name=source_path.name,
            source_path=str(source_path),
            source_type="staging_cache",
            file_size_bytes=int(manifest["file_size_bytes"]),
            file_modified_at=str(manifest["file_modified_at"]),
            loaded_at=datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S"),
            fingerprint=fingerprint,
            available_sheets=list(sheets.keys()),
            missing_sheets=[s for s in EXPECTED_SHEETS if s not in sheets],
            is_synthetic=False,
        )
    except Exception:
        return None


def load_excel_workbook(
    excel_source: str | Path | bytes | BinaryIO | None = None,
    source_filename: str | None = None,
    use_staging_cache: bool = True,
    staging_dir: Path | None = None,
) -> RawDatasetBundle:
    """Carrega todas as abas relevantes da planilha Excel (arquivo local ou upload em memória).

    Levanta `FileNotFoundError` se nenhum arquivo for encontrado/informado, ou `ValueError`
    se o arquivo estiver corrompido ou não contiver as abas essenciais do modelo de planejamento.
    """
    resolved_staging_dir = staging_dir or (get_data_dir() / "staging")
    now_str = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")

    # Caso 1: Bytes ou stream enviado via upload (ex.: Streamlit Community Cloud)
    if isinstance(excel_source, (bytes, bytearray)) or hasattr(excel_source, "read"):
        if isinstance(excel_source, (bytes, bytearray)):
            raw_bytes = bytes(excel_source)
        else:
            pos = excel_source.tell() if hasattr(excel_source, "tell") else None
            raw_bytes = excel_source.read()
            if pos is not None and hasattr(excel_source, "seek"):
                excel_source.seek(pos)

        if not raw_bytes:
            raise ValueError("O arquivo enviado está vazio.")

        fname = source_filename or "Planilha_Enviada_Upload.xlsx"
        fp = compute_bytes_fingerprint(raw_bytes, fname)
        try:
            xl = pd.ExcelFile(io.BytesIO(raw_bytes), engine="openpyxl")
        except Exception as exc:
            raise ValueError(f"Não foi possível abrir o arquivo Excel enviado ({fname}): {exc}") from exc

        available = list(xl.sheet_names)
        missing_essential = [s for s in ESSENTIAL_SHEETS if s not in available]
        if missing_essential:
            raise ValueError(
                f"A planilha '{fname}' não contém as abas essenciais esperadas: {', '.join(missing_essential)}."
            )

        sheets = {s: pd.read_excel(xl, sheet_name=s) for s in available}
        return RawDatasetBundle(
            sheets=sheets,
            source_name=fname,
            source_path=None,
            source_type="uploaded_excel",
            file_size_bytes=len(raw_bytes),
            file_modified_at=now_str,
            loaded_at=now_str,
            fingerprint=fp,
            available_sheets=available,
            missing_sheets=[s for s in EXPECTED_SHEETS if s not in available],
            is_synthetic=False,
        )

    # Caso 2: Caminho em disco (explícito ou descoberto automaticamente)
    path = discover_excel_path(excel_source)
    if path is None or not path.exists():
        raise FileNotFoundError(
            "Base oficial de planejamento financeiro ('Contabilidade e Finanças(4).xlsx' ou 'Contabilidade e Finanças.xlsx') "
            "não localizada em 'data/raw/' nem na raiz do projeto."
        )

    stat = path.stat()
    mtime_str = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    fp = compute_file_fingerprint(path)

    if use_staging_cache:
        cached = _try_load_staging_cache(fp, resolved_staging_dir, path)
        if cached is not None:
            return cached

    try:
        xl = pd.ExcelFile(path, engine="openpyxl")
    except Exception as exc:
        raise ValueError(f"Erro ao abrir a planilha Excel '{path.name}': {exc}") from exc

    available = list(xl.sheet_names)
    missing_essential = [s for s in ESSENTIAL_SHEETS if s not in available]
    if missing_essential:
        raise ValueError(
            f"A planilha '{path.name}' não possui as abas essenciais obrigatórias: {', '.join(missing_essential)}."
        )

    sheets = {s: pd.read_excel(xl, sheet_name=s) for s in available}
    bundle = RawDatasetBundle(
        sheets=sheets,
        source_name=path.name,
        source_path=str(path),
        source_type="local_excel",
        file_size_bytes=stat.st_size,
        file_modified_at=mtime_str,
        loaded_at=now_str,
        fingerprint=fp,
        available_sheets=available,
        missing_sheets=[s for s in EXPECTED_SHEETS if s not in available],
        is_synthetic=False,
    )

    if use_staging_cache:
        try:
            _save_staging_cache(bundle, resolved_staging_dir)
        except Exception:
            # Falha de permissão de escrita em ambiente read-only não deve impedir o uso em memória
            pass

    return bundle


def build_synthetic_demo_bundle(n_scenarios: int = 30) -> RawDatasetBundle:
    """Gera base sintética ESTRITAMENTE IDENTIFICADA para demonstração pública sem dados reais.

    Importante: Esta função NUNCA é chamada silenciosamente como substituta da base original.
    Só pode ser acionada por decisão explícita do usuário para demonstração em nuvem pública.
    """
    rng = np.random.default_rng(42)
    now_str = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")

    dre_rows = []
    bal_rows = []
    dfc_rows = []
    kpi_rows = []

    for i in range(1, n_scenarios + 1):
        scen = f"DEMO_{i:05d}"
        base_rev = rng.uniform(5.8e9, 8.2e9)
        growth = rng.uniform(0.03, 0.065)
        cost_ratio = rng.uniform(0.15, 0.21)
        saldo_caixa = 7.5e8

        for ano in range(1, 13):
            rec = base_rev * ((1 + growth) ** (ano - 1))
            trib = -rec * rng.uniform(0.07, 0.09)
            cust = -rec * cost_ratio * rng.uniform(0.95, 1.05)
            da = -(6.0e8 + ano * 3.5e7)
            ro = rec + trib + cust + da
            rf_in = rng.uniform(3e7, 2e8)
            rf_out = -rng.uniform(1e8, 6.5e8) * max(0.2, 1.1 - 0.07 * ano)
            rf = rf_in + rf_out
            outros_op = 4.5e7 if ano < 12 else 9.0e8
            lair = ro + rf + outros_op
            ir = -0.34 * max(lair, 0.0)
            ll = lair + ir
            ebitda_mod = ro + abs(da) + rng.uniform(2.5e8, 4.5e8)

            dre_rows.append({
                "Cenário": scen,
                "Ano": ano,
                "DRE - Receita": rec,
                "DRE - Tributos": trib,
                "DRE - Custos": cust,
                "DRE - Depreciação e Amortização": da,
                "DRE - Resultado Operacional": ro,
                "DRE - Receitas Financeiras": rf_in,
                "DRE - Despesas Financeiras": rf_out,
                "DRE - Resultado Financeiro": rf,
                "DRE - Outros Resultados Operacionais": outros_op,
                "DRE - Resultado Antes do Imposto de Renda": lair,
                "DRE - Imposto de Renda e Contribuição Social": ir,
                "DRE - Resultado Líquido": ll,
                "DRE - Resultado Líquido após Equivalência": ll,
                "DRE - EBITDA": ebitda_mod,
            })

            inv = -rng.uniform(3e7, 3.5e8)
            div_pag = -ll * rng.uniform(0.65, 0.92)
            ger_caixa = (rec * 0.96) + trib + cust + inv + rf + ir + div_pag
            novo_saldo = max(5e7, saldo_caixa + ger_caixa)
            ger_caixa = novo_saldo - saldo_caixa

            dfc_rows.append({
                "Cenário": scen,
                "Ano": ano,
                "FLU - Saldo Inicial": saldo_caixa,
                "FLU - Receita": rec * 0.96,
                "FLU - Tributos": trib,
                "FLU - Custos": cust,
                "FLU - Investimentos": inv,
                "FLU - Entradas": rf_in,
                "FLU - Despesas Financeiras": rf_out,
                "FLU - Resultado Financeiro": rf,
                "FLU - Imposto de Renda e Contribuição Social": ir,
                "FLU - Distribuição para Acionista": div_pag,
                "FLU - Geração de Caixa": ger_caixa,
                "FLU - Saldo Final": novo_saldo,
            })

            if ano < 12:
                est = 85000.0
                cr_cli = 4.1e8
                ac = novo_saldo + cr_cli + est + 1.2e8
                rlp = 7.0e8 + ano * 1.1e8
                perm = max(1.0e9, 8.2e9 - ano * 6.2e8)
                at = ac + rlp + perm
                pc = -rng.uniform(1.0e9, 2.2e9)
                pnc = -7.2e9
                pl = -(at + pc + pnc)
                bal_rows.append({
                    "Cenário": scen,
                    "Ano": ano,
                    "BAL - Total do Ativo": at,
                    "BAL - Ativo Circulante": ac,
                    "BAL - Disponível": novo_saldo,
                    "BAL - Contas a Receber - SWAP": 1.2e8,
                    "BAL - Contas a Receber - Partes Relacionadas": 5.8e5,
                    "BAL - Contas a Receber - Clientes": cr_cli,
                    "BAL - Estoques Diversos": est,
                    "BAL - Outros Créditos": 0.0,
                    "BAL - Realizável a Longo Prazo": rlp,
                    "BAL - Permanente": perm,
                    "BAL - Investimentos - Imobilizado": 8.5e8,
                    "BAL - Investimentos - Intangível": 1.2e10,
                    "BAL - Depreciação Acumulada": -5.0e8,
                    "BAL - Amortização Acumulada": -1.0e8,
                    "BAL - Amortização - Intangível": -4.0e9,
                    "BAL - Total do Passivo": -at,
                    "BAL - Passivo Circulante": pc,
                    "BAL - Empréstimos": pc * 0.4,
                    "BAL - Fornecedores": pc * 0.15,
                    "BAL - Impostos": pc * 0.25,
                    "BAL - Exigível a Longo Prazo": pnc,
                    "BAL  - Patrimônio Líquido": pl,
                    "BAL  - Capital Social": -3.1e8,
                    "BAL  - Resultado do Período": -ll,
                })
                lc = ac / abs(pc)
                ls = (ac - est) / abs(pc)
                li = novo_saldo / abs(pc)
                lg = (ac + rlp) / (abs(pc) + abs(pnc))
                pl_imp = abs(at - abs(pc) - abs(pnc))
                pct = (abs(pc) + abs(pnc)) / pl_imp
                ce = abs(pc) / (abs(pc) + abs(pnc))
                ipl = (at - ac) / pl_imp
                eg = (abs(pc) + abs(pnc)) / at
                nopat = ro * (1.0 - abs(ir) / abs(lair))
                cap_inv = abs(pc) + abs(pnc) + pl_imp
                eva = nopat - cap_inv * 0.12
                roic = nopat / cap_inv
            else:
                bal_rows.append({
                    "Cenário": scen,
                    "Ano": ano,
                    "BAL - Total do Ativo": 9.0e7,
                    "BAL - Ativo Circulante": novo_saldo,
                    "BAL - Disponível": novo_saldo,
                    "BAL - Estoques Diversos": np.nan,
                    "BAL - Realizável a Longo Prazo": 0.0,
                    "BAL - Permanente": -3.0e8,
                    "BAL - Total do Passivo": -9.0e7,
                    "BAL - Passivo Circulante": -1.1e8,
                    "BAL - Exigível a Longo Prazo": np.nan,
                    "BAL  - Patrimônio Líquido": np.nan,
                })
                lc = ls = li = lg = pct = ce = ipl = eg = nopat = cap_inv = eva = roic = np.nan

            ebitda_calc = ro + abs(da)
            kpi_rows.append({
                "Cenário": scen,
                "Ano": ano,
                "LC ": lc,
                "LS": ls,
                "LI": li,
                "LG": lg,
                "PCT": pct,
                "CE": ce,
                "IPL": ipl,
                "Endividamento Geral": eg,
                "EBITDA calculado (R$)": ebitda_calc,
                "Margem EBITDA calculada": ebitda_calc / abs(rec),
                "Margem EBITDA do modelo": ebitda_mod / abs(rec),
                "NOPAT (R$)": nopat,
                "Capital Investido (R$)": cap_inv,
                "EVA (R$)": eva,
                "ROIC": roic,
                "EBITDA do modelo (R$)": ebitda_mod,
                "Receita (R$)": abs(rec),
                "Custos variáveis (R$)": abs(cust),
                "Margem de contribuição": (abs(rec) + trib - abs(cust)) / (abs(rec) + trib),
            })
            saldo_caixa = novo_saldo

    kpi_df = pd.DataFrame(kpi_rows)
    k11 = kpi_df[kpi_df["Ano"] <= 11].groupby("Cenário", as_index=False).mean(numeric_only=True)
    resumo_df = pd.DataFrame({
        "Cenário": k11["Cenário"],
        "Margem EBITDA modelo": k11["Margem EBITDA do modelo"],
        "Margem EBITDA calculada": k11["Margem EBITDA calculada"],
        "LC": k11["LC "],
        "LS": k11["LS"],
        "LI": k11["LI"],
        "LG": k11["LG"],
        "PCT": k11["PCT"],
        "CE": k11["CE"],
        "IPL": k11["IPL"],
        "Endiv. Geral": k11["Endividamento Geral"],
        "EBITDA calculado (R$)": k11["EBITDA calculado (R$)"],
        "EBITDA modelo (R$)": k11["EBITDA do modelo (R$)"],
        "NOPAT (R$)": k11["NOPAT (R$)"],
        "Capital Investido (R$)": k11["Capital Investido (R$)"],
        "EVA (R$)": k11["EVA (R$)"],
        "ROIC": k11["ROIC"],
        "Score baixo risco": (1.0 / (k11["LC "].clip(lower=0.2))) * 0.4,
        "Receita média (R$)": k11["Receita (R$)"],
        "Custos variáveis proxy médios (R$)": k11["Custos variáveis (R$)"],
        "Margem de contribuição média": k11["Margem de contribuição"],
        "CAC simulado (R$/cliente)": 200,
        "LTV simulado (R$/cliente)": 2100,
        "LTV/CAC": 10.5,
        "EBITDA calculado médio (R$)": k11["EBITDA calculado (R$)"],
        "Margem EBITDA modelo média": k11["Margem EBITDA do modelo"],
    })

    rank_df = resumo_df.sort_values("Margem EBITDA modelo", ascending=False).reset_index(drop=True)
    ranking_sheet = pd.DataFrame({
        "Posição": np.arange(1, len(rank_df) + 1),
        "Cenário": rank_df["Cenário"],
        "Margem EBITDA": rank_df["Margem EBITDA modelo"],
        "LC": rank_df["LC"],
        "LS": rank_df["LS"],
        "LI": rank_df["LI"],
        "LG": rank_df["LG"],
        "PCT": rank_df["PCT"],
        "CE": rank_df["CE"],
        "IPL": rank_df["IPL"],
        "Endiv. Geral": rank_df["Endiv. Geral"],
        "Score baixo risco": rank_df["Score baixo risco"],
    })

    top_rows = []
    for cat, col, asc, crit in [
        ("ALTA RENTABILIDADE", "Margem EBITDA modelo", False, "Maior média da Margem EBITDA do modelo"),
        ("ALTA LIQUIDEZ", "LC", False, "Maior média da LC"),
        ("BAIXA LIQUIDEZ", "LC", True, "Menor média da LC"),
        ("BAIXO RISCO", "Score baixo risco", True, "Menor score composto"),
    ]:
        sub = resumo_df.sort_values(col, ascending=asc).head(10).reset_index(drop=True)
        for idx, row in sub.iterrows():
            top_rows.append({
                "Categoria": cat,
                "Posição": idx + 1,
                "Cenário": row["Cenário"],
                "Indicador": float(row[col]),
                "Critério": crit,
            })

    dic_df = pd.DataFrame([
        {
            "Categoria": "DEMO",
            "KPI / Indicador": "Base Sintética de Demonstração",
            "Descrição": "Dados sintéticos gerados exclusivamente para demonstração pública sem dados confidenciais.",
            "Fórmula / Regra aplicada": "Mesmas identidades algébricas do modelo CTI",
            "Unidade": "R$ / % / x",
            "Nível de cálculo": "Cenário × Ano",
            "Interpretação": "Apenas ilustrativo — carregue a planilha oficial para resultados reais.",
            "Observação / Premissa": "MODO DEMONSTRAÇÃO SINTÉTICA",
            "Fonte": "Gerador sintético interno",
            "Periodicidade": "Anual",
            "Dimensão de análise": "Cenário × Ano",
            "Regra de validação": "Identificação visual obrigatória de dados sintéticos.",
        }
    ])

    est_rows = []
    for label, col, unit in [
        ("Liquidez Corrente (LC) – ajustada", "LC", "x"),
        ("Margem EBITDA calculada", "Margem EBITDA calculada", "%"),
        ("Margem EBITDA do modelo", "Margem EBITDA modelo", "%"),
        ("ROIC", "ROIC", "%"),
        ("EVA", "EVA (R$)", "R$"),
        ("Receita", "Receita média (R$)", "R$"),
    ]:
        s = resumo_df[col]
        est_rows.append({
            "KPI / Indicador": label,
            "Unidade": unit,
            "N": len(s),
            "Média": float(s.mean()),
            "Mínimo": float(s.min()),
            "Máximo": float(s.max()),
            "Desvio padrão (amostral)": float(s.std(ddof=1)),
            "P5": float(np.percentile(s, 5)),
            "P10": float(np.percentile(s, 10)),
            "P25": float(np.percentile(s, 25)),
            "P50 (Mediana)": float(np.percentile(s, 50)),
            "P75": float(np.percentile(s, 75)),
            "P90": float(np.percentile(s, 90)),
            "P95": float(np.percentile(s, 95)),
        })

    sheets = {
        "Balanco_Cenarios": pd.DataFrame(bal_rows),
        "DRE_Cenarios": pd.DataFrame(dre_rows),
        "DFC_Cenarios": pd.DataFrame(dfc_rows),
        "KPIs_Cenarios": kpi_df,
        "KPIs_Estatisticas": pd.DataFrame(est_rows),
        "Dicionario_KPIs": dic_df,
        "Resumo_Cenarios": resumo_df,
        "Ranking_Cenarios": ranking_sheet,
        "Top10_Rankings": pd.DataFrame(top_rows),
    }

    return RawDatasetBundle(
        sheets=sheets,
        source_name="BASE_SINTETICA_DEMONSTRACAO (NÃO OFICIAL)",
        source_path=None,
        source_type="synthetic_demo",
        file_size_bytes=0,
        file_modified_at=now_str,
        loaded_at=now_str,
        fingerprint="synthetic-demo-v1",
        available_sheets=list(sheets.keys()),
        missing_sheets=[],
        is_synthetic=True,
    )
