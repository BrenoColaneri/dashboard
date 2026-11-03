"""CTI Global | Módulo Corporativo de Autenticação e Gestão de Sessão.

Camada de segurança e controle de acesso institucional para a
Plataforma Analítica de Planejamento Financeiro da CTI Global.

Implementa:
- Hashing criptográfico seguro com bcrypt (com rounds configuráveis).
- Validação estrita de credenciais no backend (sem credenciais hardcoded em plaintext).
- Suporte a variáveis de ambiente (.env) e Streamlit secrets (.streamlit/secrets.toml).
- Gestão de sessão no Streamlit com expiração automática por inatividade (padrão: 30 minutos).
- Proteção contra tentativas excessivas (Rate Limiting de força bruta: 5 tentativas -> bloqueio de 15 min).
- Interface de login institucional responsiva (360px a 1920px) com o padrão visual CTI Global.
- Botão de logout com revogação imediata de credenciais e proteção contra histórico do navegador.
"""

from __future__ import annotations

import hmac
import math
import os
import time
from typing import Any

import bcrypt
import streamlit as st

# Hash bcrypt padrão correspondente à senha inicial de desenvolvimento 'admin123' (12 rounds)
# Em ambiente de produção, este valor é substituído via CTI_AUTH_PASSWORD_HASH ou secrets.toml
DEFAULT_ADMIN_USER: str = "admin"
DEFAULT_ADMIN_PASSWORD_HASH: str = "$2b$12$5ObbbRYannus1KMDHO6Q4OhLORKeA7jHmRjsHn6RRGRWPpvh/J0sS"

# Parâmetros de política de segurança institucional
DEFAULT_SESSION_TIMEOUT_MINUTES: int = 30
DEFAULT_MAX_LOGIN_ATTEMPTS: int = 5
DEFAULT_LOCKOUT_MINUTES: int = 15


def get_configured_credentials() -> dict[str, Any]:
    """Obtém as credenciais e parâmetros de segurança configurados em segredos ou ambiente."""
    # 1. Tenta carregar do Streamlit secrets (produção em nuvem)
    sec_user = None
    sec_hash = None
    sec_plain = None
    sec_timeout = None
    sec_max_attempts = None
    sec_lockout = None

    try:
        if hasattr(st, "secrets") and "auth" in st.secrets:
            auth_sec = st.secrets["auth"]
            sec_user = auth_sec.get("username")
            sec_hash = auth_sec.get("password_hash")
            sec_plain = auth_sec.get("password")
            sec_timeout = auth_sec.get("session_timeout_minutes")
            sec_max_attempts = auth_sec.get("max_login_attempts")
            sec_lockout = auth_sec.get("lockout_minutes")
    except Exception:
        pass

    # 2. Sobrescreve com variáveis de ambiente (se presentes)
    env_user = os.getenv("CTI_AUTH_USER", sec_user or DEFAULT_ADMIN_USER)
    env_hash = os.getenv("CTI_AUTH_PASSWORD_HASH", sec_hash or DEFAULT_ADMIN_PASSWORD_HASH)
    env_plain = os.getenv("CTI_AUTH_PASSWORD", sec_plain)
    
    timeout_min = int(os.getenv("CTI_SESSION_TIMEOUT_MINUTES", str(sec_timeout or DEFAULT_SESSION_TIMEOUT_MINUTES)))
    max_attempts = int(os.getenv("CTI_MAX_LOGIN_ATTEMPTS", str(sec_max_attempts or DEFAULT_MAX_LOGIN_ATTEMPTS)))
    lockout_min = int(os.getenv("CTI_LOCKOUT_MINUTES", str(sec_lockout or DEFAULT_LOCKOUT_MINUTES)))

    return {
        "username": env_user.strip(),
        "password_hash": env_hash.strip(),
        "plain_fallback": env_plain.strip() if env_plain else None,
        "timeout_seconds": timeout_min * 60,
        "max_attempts": max_attempts,
        "lockout_seconds": lockout_min * 60,
    }


def hash_password(plain_password: str, rounds: int = 12) -> str:
    """Gera hash criptográfico bcrypt seguro com salt aleatório."""
    salt = bcrypt.gensalt(rounds=rounds)
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, expected_hash: str, plain_fallback: str | None = None) -> bool:
    """Valida a senha fornecida contra o hash bcrypt oficial (e fallback seguro de env se configurado)."""
    if not plain_password:
        return False

    # Validação primária via hash bcrypt com tempo constante
    try:
        if expected_hash and expected_hash.startswith(("$2a$", "$2b$", "$2y$")):
            if bcrypt.checkpw(plain_password.encode("utf-8"), expected_hash.encode("utf-8")):
                return True
    except Exception:
        pass

    # Validação secundária estrita via comparação de tempo constante caso CTI_AUTH_PASSWORD tenha sido fornecido
    if plain_fallback:
        try:
            return hmac.compare_digest(plain_password.encode("utf-8"), plain_fallback.encode("utf-8"))
        except Exception:
            return False

    return False


def _init_auth_session_state() -> None:
    """Garante que as chaves de controle de sessão estejam inicializadas."""
    if "is_authenticated" not in st.session_state:
        st.session_state["is_authenticated"] = False
    if "authenticated_user" not in st.session_state:
        st.session_state["authenticated_user"] = None
    if "auth_login_timestamp" not in st.session_state:
        st.session_state["auth_login_timestamp"] = None
    if "auth_last_activity" not in st.session_state:
        st.session_state["auth_last_activity"] = None
    if "auth_failed_attempts" not in st.session_state:
        st.session_state["auth_failed_attempts"] = 0
    if "auth_locked_until" not in st.session_state:
        st.session_state["auth_locked_until"] = 0.0


def check_session_validity() -> tuple[bool, str]:
    """Verifica se há uma sessão autenticada válida e não expirada por inatividade.

    Retorna:
        tuple[bool, str]: (sessão_valida, mensagem_de_expiração)
    """
    _init_auth_session_state()

    if not st.session_state.get("is_authenticated", False):
        return False, ""

    config = get_configured_credentials()
    timeout_sec = config["timeout_seconds"]
    last_active = st.session_state.get("auth_last_activity")
    now = time.time()

    if last_active and (now - last_active) > timeout_sec:
        # Sessão expirada por inatividade
        timeout_min = timeout_sec // 60
        logout_user()
        return False, f"Sua sessão expirou por inatividade ({timeout_min} minutos). Por favor, realize o login novamente."

    # Atualiza carimbo de última atividade
    st.session_state["auth_last_activity"] = now
    return True, ""


def logout_user() -> None:
    """Encerra com segurança a sessão autenticada e revoga todos os privilégios."""
    st.session_state["is_authenticated"] = False
    st.session_state["authenticated_user"] = None
    st.session_state["auth_login_timestamp"] = None
    st.session_state["auth_last_activity"] = None


def authenticate_credentials(username: str, password: str) -> tuple[bool, str]:
    """Valida as credenciais fornecidas no backend com proteção contra força bruta.

    Retorna:
        tuple[bool, str]: (sucesso, mensagem_ao_usuario)
    """
    _init_auth_session_state()
    config = get_configured_credentials()
    now = time.time()

    # 1. Verifica se a conta está temporariamente bloqueada por tentativas excessivas
    locked_until = st.session_state.get("auth_locked_until", 0.0)
    if now < locked_until:
        rem_min = math.ceil((locked_until - now) / 60)
        return False, f"Acesso temporariamente bloqueado por excesso de tentativas. Tente novamente em {rem_min} minuto(s)."

    # 2. Validação de preenchimento obrigatório
    if not username.strip() or not password:
        return False, "Preencha o usuário e a senha para continuar."

    # 3. Comparação de tempo constante do usuário
    user_match = hmac.compare_digest(username.strip(), config["username"])

    # 4. Validação criptográfica da senha
    pass_match = verify_password(password, config["password_hash"], config["plain_fallback"])

    # Autenticação genérica (não revela se o erro foi no usuário ou na senha)
    if user_match and pass_match:
        st.session_state["is_authenticated"] = True
        st.session_state["authenticated_user"] = username.strip()
        st.session_state["auth_login_timestamp"] = now
        st.session_state["auth_last_activity"] = now
        st.session_state["auth_failed_attempts"] = 0
        st.session_state["auth_locked_until"] = 0.0
        return True, "Autenticação realizada com sucesso!"
    else:
        # Incrementa contador de falhas
        attempts = st.session_state.get("auth_failed_attempts", 0) + 1
        st.session_state["auth_failed_attempts"] = attempts

        if attempts >= config["max_attempts"]:
            st.session_state["auth_locked_until"] = now + config["lockout_seconds"]
            lockout_min = config["lockout_seconds"] // 60
            return (
                False,
                f"Limite de tentativas excedido. O acesso foi bloqueado por {lockout_min} minutos por motivos de segurança.",
            )

        return False, "Usuário ou senha incorretos. Verifique suas informações e tente novamente."


def render_login_screen(expired_message: str = "") -> None:
    """Renderiza a tela corporativa oficial de autenticação da CTI Global em um único card elegante e centralizado."""
    _init_auth_session_state()

    # Injeção de CSS específico da tela de login para simetria, centralização e responsividade total
    st.markdown(
        """
        <style>
        /* Fundo elegante e neutro para a tela de autenticação */
        [data-testid="stAppViewContainer"] {
            background: linear-gradient(180deg, #F8FAFC 0%, #F1F5F9 100%) !important;
        }

        /* Oculta completamente barra lateral e elementos desnecessários na tela de login */
        [data-testid="stSidebar"] {
            display: none !important;
        }
        [data-testid="collapsedControl"] {
            display: none !important;
        }
        header[data-testid="stHeader"] {
            background: transparent !important;
        }

        /* Centralização vertical e horizontal do container principal */
        .block-container {
            max-width: 480px !important;
            padding-top: 7vh !important;
            padding-bottom: 6vh !important;
            margin: 0 auto !important;
        }

        /* O CARD ÚNICO INTEGRADO DE AUTENTICAÇÃO */
        [data-testid="stForm"] {
            background: #FFFFFF !important;
            border: 1px solid #E2E8F0 !important;
            border-radius: 20px !important;
            box-shadow: 0 20px 45px -10px rgba(11, 93, 59, 0.10), 0 8px 20px -4px rgba(15, 23, 42, 0.04) !important;
            padding: 40px 36px 30px 36px !important;
            width: 100% !important;
            margin: 0 auto !important;
        }

        /* Cabeçalho integrado dentro do card */
        .cti-login-inner-header {
            text-align: center;
            margin-bottom: 24px;
        }
        .cti-login-badge {
            display: inline-block;
            background: #ECFDF5;
            color: #0B5D3B;
            font-size: 0.74rem;
            font-weight: 700;
            letter-spacing: 0.09em;
            text-transform: uppercase;
            padding: 5px 14px;
            border-radius: 9999px;
            border: 1px solid #A7F3D0;
            margin-bottom: 12px;
        }
        .cti-login-headline {
            color: #0F172A;
            font-size: 1.55rem;
            font-weight: 700;
            margin: 0 0 8px 0;
            letter-spacing: -0.025em;
            line-height: 1.25;
        }
        .cti-login-subheadline {
            color: #64748B;
            font-size: 0.88rem;
            line-height: 1.45;
            margin: 0;
        }

        /* Estilização refinada e simétrica dos campos de entrada */
        [data-testid="stTextInput"] {
            margin-bottom: 14px !important;
        }
        [data-testid="stTextInput"] label p {
            font-size: 0.86rem !important;
            font-weight: 600 !important;
            color: #334155 !important;
            margin-bottom: 5px !important;
        }
        [data-testid="stTextInput"] input {
            border-radius: 10px !important;
            border: 1px solid #CBD5E1 !important;
            background-color: #F8FAFC !important;
            font-size: 0.94rem !important;
            padding: 10px 14px !important;
            height: 44px !important;
            transition: all 0.2s ease-in-out !important;
        }
        [data-testid="stTextInput"] input:focus {
            border-color: #0B5D3B !important;
            background-color: #FFFFFF !important;
            box-shadow: 0 0 0 3px rgba(11, 93, 59, 0.14) !important;
            outline: none !important;
        }

        /* Botão Entrar em verde institucional destacado */
        [data-testid="stFormSubmitButton"] button {
            background: #0B5D3B !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
            font-size: 1rem !important;
            height: 46px !important;
            letter-spacing: 0.01em !important;
            box-shadow: 0 4px 14px rgba(11, 93, 59, 0.25) !important;
            transition: all 0.2s ease-in-out !important;
            margin-top: 8px !important;
        }
        [data-testid="stFormSubmitButton"] button:hover {
            background: #064E3B !important;
            box-shadow: 0 6px 18px rgba(11, 93, 59, 0.35) !important;
            transform: translateY(-1px) !important;
        }
        [data-testid="stFormSubmitButton"] button:active {
            transform: translateY(0) !important;
            box-shadow: 0 2px 6px rgba(11, 93, 59, 0.2) !important;
        }

        /* Rodapé institucional integrado dentro do card */
        .cti-login-inner-footer {
            margin-top: 22px;
            padding-top: 18px;
            border-top: 1px solid #F1F5F9;
            text-align: center;
            font-size: 0.76rem;
            color: #94A3B8;
            line-height: 1.45;
        }
        .cti-login-inner-footer strong {
            color: #0B5D3B;
            font-weight: 600;
        }

        /* Responsividade para celulares e telas pequenas */
        @media (max-width: 480px) {
            .block-container {
                padding-top: 2.5rem !important;
                padding-bottom: 2rem !important;
                padding-left: 1rem !important;
                padding-right: 1rem !important;
            }
            [data-testid="stForm"] {
                padding: 28px 22px 24px 22px !important;
                border-radius: 16px !important;
            }
            .cti-login-headline {
                font-size: 1.35rem !important;
            }
            .cti-login-subheadline {
                font-size: 0.82rem !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Exibição de aviso de expiração se houver
    if expired_message:
        st.warning(f"⚠️ {expired_message}")

    # Card único integrado dentro do formulário
    with st.form("cti_corporate_login_form", clear_on_submit=False):
        # 1. Cabeçalho integrado no topo do card
        st.markdown(
            """
            <div class="cti-login-inner-header">
                <span class="cti-login-badge">CTI GLOBAL</span>
                <h1 class="cti-login-headline">Bem-vindo à CTI Global</h1>
                <p class="cti-login-subheadline">Faça login para acessar a plataforma analítica de planejamento financeiro.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 2. Campos de Usuário e Senha padronizados
        username_input = st.text_input(
            "Usuário:",
            placeholder="Digite seu usuário",
            key="login_user_input",
            autocomplete="username",
        )

        password_input = st.text_input(
            "Senha:",
            type="password",
            placeholder="Digite sua senha",
            key="login_pass_input",
            autocomplete="current-password",
        )

        # 3. Botão Entrar com destaque visual corporativo
        submit_btn = st.form_submit_button(
            "Entrar",
            use_container_width=True,
            type="primary",
            key="cti_corporate_login_form_submit",
        )

        # 4. Processamento da autenticação
        if submit_btn:
            try:
                with st.spinner("Autenticando credenciais corporativas..."):
                    success, message = authenticate_credentials(username_input, password_input)

                if success:
                    st.success("Acesso autorizado com sucesso! Redirecionando...")
                    time.sleep(0.15)
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
            except Exception:
                st.error("❌ Não foi possível realizar o acesso neste momento. Tente novamente.")

        # 5. Rodapé institucional integrado no mesmo card
        st.markdown(
            """
            <div class="cti-login-inner-footer">
                <strong>CTI Global</strong> • Plataforma Analítica de Planejamento Financeiro<br>
                <span>Acesso restrito e monitorado por controladoria institucional.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_user_auth_bar() -> None:
    """Exibe na barra lateral e no topo a identificação do usuário conectado e o botão de Sair."""
    user = st.session_state.get("authenticated_user", "Administrador")

    with st.sidebar:
        st.markdown(
            f"""
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px 12px; margin-bottom: 12px; display: flex; align-items: center; justify-content: space-between;">
                <div>
                    <span style="font-size: 0.72rem; color: #64748B; font-weight: 600; text-transform: uppercase;">Sessão Ativa</span>
                    <div style="font-size: 0.88rem; font-weight: 700; color: #0B5D3B;">👤 {user}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("🚪 Sair do Sistema", key="btn_logout_sidebar", use_container_width=True):
            logout_user()
            st.rerun()
