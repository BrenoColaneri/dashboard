"""Testes automatizados de carregamento, descoberta, validação estrutural e tratamento de erros."""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import pytest

from src.config import ESSENTIAL_SHEETS, EXPECTED_SHEETS
from src.data_loader import (
    RawDatasetBundle,
    build_synthetic_demo_bundle,
    discover_excel_path,
    load_excel_workbook,
)
from src.data_processing import ProcessedDataStore, process_dataset


def test_discover_excel_path_finds_official_file() -> None:
    path = discover_excel_path()
    assert path is not None
    assert path.exists()
    assert path.suffix.lower() == ".xlsx"


def test_real_bundle_contains_all_expected_sheets(real_bundle: RawDatasetBundle) -> None:
    assert not real_bundle.is_synthetic
    assert real_bundle.missing_sheets == []
    for sheet in EXPECTED_SHEETS:
        assert sheet in real_bundle.sheets
        assert not real_bundle.sheets[sheet].empty


def test_processed_store_dimensions_and_keys(real_store: ProcessedDataStore) -> None:
    assert len(real_store.scenarios) == 1200
    assert real_store.periods == list(range(1, 13))
    assert len(real_store.panel) == 14400
    assert len(real_store.resumo) == 1200
    # Nenhuma conversão indevida para anos civis (2024, 2025, etc.)
    unique_labels = set(real_store.panel["Período"].unique())
    assert unique_labels == {f"Ano {i}" for i in range(1, 13)}


def test_missing_file_raises_filenotfound(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    non_existent = tmp_path / "nao_existe.xlsx"
    monkeypatch.setenv("CTI_EXCEL_PATH", str(non_existent))
    with pytest.raises(FileNotFoundError):
        load_excel_workbook(excel_source=non_existent, use_staging_cache=False)


def test_corrupt_or_empty_upload_raises_value_error() -> None:
    with pytest.raises(ValueError, match="vazio"):
        load_excel_workbook(excel_source=b"", source_filename="vazio.xlsx")

    with pytest.raises(ValueError, match="Não foi possível abrir"):
        load_excel_workbook(excel_source=b"conteudo_invalido_nao_zip", source_filename="corrompido.xlsx")


def test_workbook_missing_essential_sheets_raises_value_error() -> None:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pd.DataFrame({"A": [1, 2]}).to_excel(writer, sheet_name="Aba_Qualquer", index=False)
    with pytest.raises(ValueError, match="abas essenciais"):
        load_excel_workbook(excel_source=buf.getvalue(), source_filename="incompleta.xlsx")


def test_synthetic_demo_bundle_is_explicitly_flagged() -> None:
    demo_bundle = build_synthetic_demo_bundle(n_scenarios=8)
    assert demo_bundle.is_synthetic is True
    assert demo_bundle.source_type == "synthetic_demo"
    for req in ESSENTIAL_SHEETS:
        assert req in demo_bundle.sheets
    demo_store = process_dataset(demo_bundle, persist_processed=False)
    assert len(demo_store.scenarios) == 8
    assert len(demo_store.panel) == 8 * 12

