"""Fixtures compartilhadas da suíte Pytest para validação rápida sobre a planilha real."""

from __future__ import annotations

import pytest

from src.data_loader import RawDatasetBundle, load_excel_workbook
from src.data_processing import ProcessedDataStore, process_dataset
from src.data_validation import ValidationSummary, run_full_validation


@pytest.fixture(scope="session")
def real_bundle() -> RawDatasetBundle:
    """Carrega o pacote oficial da base de planejamento (com cache Parquet staging verificado)."""
    return load_excel_workbook(use_staging_cache=True)


@pytest.fixture(scope="session")
def real_store(real_bundle: RawDatasetBundle) -> ProcessedDataStore:
    """Executa o pipeline Staging -> Processed sobre a base oficial."""
    return process_dataset(real_bundle, persist_processed=False)


@pytest.fixture(scope="session")
def real_validation(real_store: ProcessedDataStore) -> ValidationSummary:
    """Executa a validação estrutural e reconciliação completa sobre a base processada."""
    return run_full_validation(real_store)

