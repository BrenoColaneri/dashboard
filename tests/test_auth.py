"""Testes automatizados da camada de autenticação, segurança e gestão de sessão da CTI Global."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

from src.auth import (
    DEFAULT_ADMIN_USER,
    authenticate_credentials,
    check_session_validity,
    get_configured_credentials,
    hash_password,
    logout_user,
    verify_password,
)


def test_hash_and_verify_password_bcrypt() -> None:
    raw = "minhasenha_segura_2026"
    h = hash_password(raw, rounds=10)
    assert h.startswith("$2b$")
    assert verify_password(raw, h) is True
    assert verify_password("senha_errada", h) is False
    assert verify_password("", h) is False


def test_default_credentials_verification() -> None:
    creds = get_configured_credentials()
    assert creds["username"] == "admin"
    # Valida que a senha inicial oficial 'admin123' confere com o hash configurado
    assert verify_password("admin123", creds["password_hash"]) is True
    assert verify_password("admin321", creds["password_hash"]) is False


def test_authenticate_credentials_success(monkeypatch: pytest.MonkeyPatch) -> None:
    # Simula session_state limpo
    fake_session: dict = {}
    monkeypatch.setattr("streamlit.session_state", fake_session)

    ok, msg = authenticate_credentials("admin", "admin123")
    assert ok is True
    assert "sucesso" in msg.lower()
    assert fake_session.get("is_authenticated") is True
    assert fake_session.get("authenticated_user") == "admin"


def test_authenticate_credentials_wrong_user(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_session: dict = {}
    monkeypatch.setattr("streamlit.session_state", fake_session)

    ok, msg = authenticate_credentials("usuario_inexistente", "admin123")
    assert ok is False
    assert "Usuário ou senha incorretos" in msg
    assert fake_session.get("is_authenticated") is False


def test_authenticate_credentials_wrong_password(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_session: dict = {}
    monkeypatch.setattr("streamlit.session_state", fake_session)

    ok, msg = authenticate_credentials("admin", "senha_incorreta_xyz")
    assert ok is False
    assert "Usuário ou senha incorretos" in msg
    assert fake_session.get("is_authenticated") is False


def test_authenticate_credentials_empty_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_session: dict = {}
    monkeypatch.setattr("streamlit.session_state", fake_session)

    ok, msg = authenticate_credentials("", "")
    assert ok is False
    assert "Preencha o usuário e a senha" in msg

    ok2, msg2 = authenticate_credentials("admin", "")
    assert ok2 is False
    assert "Preencha o usuário e a senha" in msg2


def test_rate_limiting_brute_force_lockout(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_session: dict = {}
    monkeypatch.setattr("streamlit.session_state", fake_session)

    # 4 tentativas inválidas
    for _ in range(4):
        ok, msg = authenticate_credentials("admin", "senha_errada")
        assert ok is False
        assert "Usuário ou senha incorretos" in msg

    # 5ª tentativa inválida (atinge o limite de 5)
    ok5, msg5 = authenticate_credentials("admin", "senha_errada")
    assert ok5 is False
    assert "Limite de tentativas excedido" in msg5

    # 6ª tentativa imediata: deve ser bloqueada sem verificar a senha
    ok6, msg6 = authenticate_credentials("admin", "admin123")
    assert ok6 is False
    assert "bloqueado por excesso de tentativas" in msg6


def test_session_inactivity_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    now = time.time()
    fake_session = {
        "is_authenticated": True,
        "authenticated_user": "admin",
        "auth_last_activity": now - (31 * 60),  # 31 minutos atrás (limite = 30 min)
    }
    monkeypatch.setattr("streamlit.session_state", fake_session)

    is_valid, msg = check_session_validity()
    assert is_valid is False
    assert "expirou por inatividade" in msg
    assert fake_session.get("is_authenticated") is False


def test_logout_user(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_session = {
        "is_authenticated": True,
        "authenticated_user": "admin",
        "auth_last_activity": time.time(),
        "auth_login_timestamp": time.time(),
    }
    monkeypatch.setattr("streamlit.session_state", fake_session)

    logout_user()
    assert fake_session.get("is_authenticated") is False
    assert fake_session.get("authenticated_user") is None


def test_apptest_unauthenticated_access_is_blocked() -> None:
    """Verifica que abrir o app sem autenticação exibe a tela de login e bloqueia dados protegidos."""
    app_path = str(Path(__file__).resolve().parent.parent / "app.py")
    at = AppTest.from_file(app_path, default_timeout=60)
    at.run()

    assert len(at.exception) == 0
    # O formulário de login corporativo deve estar presente
    assert len(at.text_input) >= 2  # usuário e senha
    # O rádio de navegação analítica NÃO deve estar visível no sidebar
    assert len(at.sidebar.radio) == 0


def test_apptest_login_flow_and_dashboard_unlock() -> None:
    """Testa o fluxo interativo de login e desbloqueio completo das 17 páginas."""
    app_path = str(Path(__file__).resolve().parent.parent / "app.py")
    at = AppTest.from_file(app_path, default_timeout=60)
    at.run()
    assert len(at.exception) == 0

    # 1. Preenche usuário e senha incorretos
    at.text_input(key="login_user_input").set_value("admin")
    at.text_input(key="login_pass_input").set_value("senha_errada")
    at.button(key="cti_corporate_login_form_submit").click()
    at.run()
    assert len(at.exception) == 0
    # Ainda bloqueado
    assert len(at.sidebar.radio) == 0

    # 2. Preenche credenciais oficiais corretas
    at.text_input(key="login_user_input").set_value("admin")
    at.text_input(key="login_pass_input").set_value("admin123")
    at.button(key="cti_corporate_login_form_submit").click()
    at.run()
    assert len(at.exception) == 0

    # Dashboard desbloqueado com sucesso!
    assert at.session_state["is_authenticated"] is True
    assert len(at.sidebar.radio) > 0  # Navegação das 17 páginas liberada

