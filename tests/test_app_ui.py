"""Teste funcional ponta a ponta (E2E Headless) de todas as 14 páginas da interface Streamlit."""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

from app import PAGES


def test_all_14_dashboard_pages_render_without_exceptions() -> None:
    app_path = str(Path(__file__).resolve().parent.parent / "app.py")
    at = AppTest.from_file(app_path, default_timeout=60)
    at.run()
    assert len(at.exception) == 0, f"Exceção na carga inicial: {at.exception}"

    # Valida que exatamente as 14 páginas corporativas estão cadastradas
    assert len(PAGES) == 14

    # Navega sequencialmente pelas 14 páginas verificando ausência total de erros em runtime
    for page_label in PAGES:
        at.sidebar.radio(key="nav_page_radio").set_value(page_label)
        at.run()
        assert len(at.exception) == 0, f"Exceção ao renderizar '{page_label}': {at.exception}"


def test_quick_navigation_buttons_transition_correctly() -> None:
    app_path = str(Path(__file__).resolve().parent.parent / "app.py")
    at = AppTest.from_file(app_path, default_timeout=60)
    at.run()
    assert len(at.exception) == 0

    quick_targets = [
        ("quick_dre", "2. DRE"),
        ("quick_balanco", "3. Balanço"),
        ("quick_kpis", "5. Indicadores"),
        ("quick_sens", "8. Análise"),
        ("quick_stat", "11. Análise"),
        ("quick_rep", "14. Relatórios"),
    ]

    for btn_key, expected_prefix in quick_targets:
        # Retorna para a página 1 (onde estão os atalhos)
        at.sidebar.radio(key="nav_page_radio").set_value("1. Visão Executiva")
        at.run()
        assert len(at.exception) == 0

        # Clica no atalho rápido
        btn = at.button(key=btn_key)
        assert btn is not None, f"Botão '{btn_key}' não encontrado na Visão Executiva"
        btn.click()
        at.run()
        assert len(at.exception) == 0, f"Erro após clicar no atalho '{btn_key}': {at.exception}"

        # Verifica se navegou para a página esperada
        current_page = at.sidebar.radio(key="nav_page_radio").value
        assert expected_prefix in current_page, f"Esperava '{expected_prefix}' mas obteve '{current_page}'"


