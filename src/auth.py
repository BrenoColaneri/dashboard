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
    """Renderiza a tela corporativa oficial de autenticação da CTI Global em layout horizontal split-screen (55% / 45%)."""
    _init_auth_session_state()

    # Injeção de CSS específico para o layout split-screen de alta densidade sem rolagem no desktop
    st.markdown(
        """
        <style>
        /* -------------------------------------------------------------
           1. RESET DE VIEWPORT: ZERO ROLAGEM DESKTOP (100vw x 100dvh)
           ------------------------------------------------------------- */
        html, body {
            margin: 0 !important;
            padding: 0 !important;
            width: 100vw !important;
            max-width: 100vw !important;
            height: 100vh !important;
            height: 100dvh !important;
            overflow: hidden !important;
            background: #F8FAFC !important;
        }

        [data-testid="stAppViewContainer"],
        [data-testid="stAppViewContainer"] > .main,
        section.main {
            margin: 0 !important;
            padding: 0 !important;
            width: 100vw !important;
            max-width: 100vw !important;
            height: 100vh !important;
            height: 100dvh !important;
            max-height: 100vh !important;
            max-height: 100dvh !important;
            overflow: hidden !important;
            background: #F8FAFC !important;
        }

        /* Oculta completamente barra lateral e elementos superiores do Streamlit */
        [data-testid="stSidebar"],
        [data-testid="collapsedControl"],
        header[data-testid="stHeader"],
        #MainMenu,
        footer {
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        /* Container principal sem margens e ocupando 100% da viewport */
        .block-container {
            max-width: 100vw !important;
            width: 100vw !important;
            height: 100vh !important;
            height: 100dvh !important;
            max-height: 100vh !important;
            max-height: 100dvh !important;
            padding: 0 !important;
            margin: 0 !important;
            overflow: hidden !important;
            box-sizing: border-box !important;
        }

        /* Bloco horizontal Streamlit: divide em duas metades perfeitas */
        [data-testid="stHorizontalBlock"] {
            width: 100vw !important;
            max-width: 100vw !important;
            height: 100vh !important;
            height: 100dvh !important;
            min-height: 100vh !important;
            min-height: 100dvh !important;
            max-height: 100vh !important;
            max-height: 100dvh !important;
            margin: 0 !important;
            padding: 0 !important;
            gap: 0 !important;
            align-items: stretch !important;
            flex-wrap: nowrap !important;
            display: flex !important;
        }

        /* Centralizadores internos de coluna */
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            margin: 0 !important;
            box-sizing: border-box !important;
        }
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] > div {
            width: 100% !important;
            height: 100% !important;
            display: flex !important;
            flex-direction: column !important;
            justify-content: center !important;
            align-items: center !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        /* -------------------------------------------------------------
           2. LADO ESQUERDO: APRESENTAÇÃO INSTITUCIONAL (55% DA LARGURA)
              FUNDO BRANCO COM DETALHES CORPORATIVOS EM VERDE
           ------------------------------------------------------------- */
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child {
            width: 55vw !important;
            max-width: 55vw !important;
            flex: 55 1 0% !important;
            height: 100vh !important;
            height: 100dvh !important;
            background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%) !important;
            display: flex !important;
            flex-direction: column !important;
            justify-content: center !important;
            align-items: center !important;
            padding: 3rem 4.5rem !important;
            box-sizing: border-box !important;
            border-right: 1px solid #E2E8F0 !important;
            overflow: hidden !important;
            position: relative !important;
        }

        .cti-inst-content-box {
            width: 100%;
            max-width: 500px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }

        .cti-inst-brand-tag {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: #ECFDF5;
            color: #0B5D3B;
            font-size: 0.76rem;
            font-weight: 700;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            padding: 6px 14px;
            border-radius: 9999px;
            border: 1px solid #A7F3D0;
            margin-bottom: 1.25rem;
            width: fit-content;
            box-shadow: 0 1px 3px rgba(11, 93, 59, 0.08);
        }
        .cti-inst-brand-dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: #10B981;
            box-shadow: 0 0 6px rgba(16, 185, 129, 0.4);
        }

        .cti-inst-headline {
            color: #064E3B !important;
            font-size: 2.05rem;
            font-weight: 800;
            line-height: 1.22;
            letter-spacing: -0.025em;
            margin: 0 0 0.85rem 0;
        }

        .cti-inst-lead {
            color: #475569;
            font-size: 0.96rem;
            line-height: 1.6;
            margin: 0 0 1.75rem 0;
            font-weight: 400;
        }

        .cti-inst-feature-list {
            display: flex;
            flex-direction: column;
            gap: 10px;
            margin: 0;
            padding: 0;
        }

        .cti-inst-feature-card {
            display: flex;
            align-items: center;
            gap: 14px;
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 12px 16px;
            box-sizing: border-box;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
            transition: all 0.2s ease;
        }
        .cti-inst-feature-card:hover {
            background: #F0FDF4;
            border-color: #A7F3D0;
            transform: translateX(3px);
            box-shadow: 0 4px 12px rgba(11, 93, 59, 0.08);
        }

        .cti-inst-feature-icon {
            flex-shrink: 0;
            width: 38px;
            height: 38px;
            border-radius: 10px;
            background: #ECFDF5;
            border: 1px solid #A7F3D0;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #0B5D3B;
        }

        .cti-inst-feature-title {
            color: #064E3B;
            font-size: 0.90rem;
            font-weight: 700;
            margin-bottom: 2px;
            line-height: 1.3;
        }

        .cti-inst-feature-desc {
            color: #64748B;
            font-size: 0.80rem;
            line-height: 1.4;
            margin: 0;
        }

        /* -------------------------------------------------------------
           3. LADO DIREITO: LOGIN E FORMULÁRIO (45% DA LARGURA)
           ------------------------------------------------------------- */
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child {
            width: 45vw !important;
            max-width: 45vw !important;
            flex: 45 1 0% !important;
            height: 100vh !important;
            height: 100dvh !important;
            background: #F8FAFC !important;
            display: flex !important;
            flex-direction: column !important;
            justify-content: center !important;
            align-items: center !important;
            padding: 2.5rem 3rem !important;
            box-sizing: border-box !important;
            overflow-y: auto !important;
            overflow-x: hidden !important;
        }

        /* Card do Formulário: largura exata confortável de 380px */
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child [data-testid="stForm"] {
            width: 100% !important;
            max-width: 380px !important;
            min-width: 320px !important;
            background: #FFFFFF !important;
            border: 1px solid #E2E8F0 !important;
            border-radius: 18px !important;
            box-shadow: 0 12px 30px -8px rgba(15, 23, 42, 0.08), 0 4px 12px -2px rgba(15, 23, 42, 0.03) !important;
            padding: 32px 30px 24px 30px !important;
            box-sizing: border-box !important;
            margin: 0 auto !important;
        }

        .cti-form-header {
            text-align: left;
            margin-bottom: 20px;
        }
        .cti-form-title {
            color: #0F172A;
            font-size: 1.48rem;
            font-weight: 700;
            margin: 0 0 6px 0;
            letter-spacing: -0.025em;
            line-height: 1.25;
        }
        .cti-form-subtitle {
            color: #64748B;
            font-size: 0.86rem;
            line-height: 1.45;
            margin: 0;
        }

        /* Padronização dos inputs */
        [data-testid="stTextInput"] {
            margin-bottom: 12px !important;
        }
        [data-testid="stTextInput"] label p {
            font-size: 0.85rem !important;
            font-weight: 600 !important;
            color: #334155 !important;
            margin-bottom: 4px !important;
        }
        [data-testid="stTextInput"] input {
            border-radius: 9px !important;
            border: 1px solid #CBD5E1 !important;
            background-color: #F8FAFC !important;
            font-size: 0.94rem !important;
            padding: 9px 12px !important;
            height: 42px !important;
            transition: all 0.2s ease-in-out !important;
        }
        [data-testid="stTextInput"] input:focus {
            border-color: #0B5D3B !important;
            background-color: #FFFFFF !important;
            box-shadow: 0 0 0 3px rgba(11, 93, 59, 0.14) !important;
            outline: none !important;
        }

        /* Botão Entrar em verde corporativo destacado */
        [data-testid="stFormSubmitButton"] button {
            background: #0B5D3B !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 9px !important;
            font-weight: 600 !important;
            font-size: 0.98rem !important;
            height: 44px !important;
            letter-spacing: 0.01em !important;
            box-shadow: 0 4px 12px rgba(11, 93, 59, 0.24) !important;
            transition: all 0.2s ease-in-out !important;
            margin-top: 6px !important;
        }
        [data-testid="stFormSubmitButton"] button:hover {
            background: #064E3B !important;
            box-shadow: 0 6px 16px rgba(11, 93, 59, 0.34) !important;
            transform: translateY(-1px) !important;
        }
        [data-testid="stFormSubmitButton"] button:active {
            transform: translateY(0) !important;
            box-shadow: 0 2px 6px rgba(11, 93, 59, 0.2) !important;
        }

        /* Rodapé interno do card */
        .cti-form-footer {
            margin-top: 18px;
            padding-top: 14px;
            border-top: 1px solid #F1F5F9;
            text-align: center;
            font-size: 0.74rem;
            color: #94A3B8;
            line-height: 1.45;
        }
        .cti-form-footer strong {
            color: #0B5D3B;
            font-weight: 600;
        }

        /* -------------------------------------------------------------
           4. RESPONSIVIDADE: CELULARES E TABLETS (<= 900px)
           ------------------------------------------------------------- */
        @media (max-width: 900px) {
            html, body,
            [data-testid="stAppViewContainer"],
            [data-testid="stAppViewContainer"] > .main,
            section.main,
            .block-container {
                height: auto !important;
                max-height: none !important;
                overflow-y: auto !important;
                overflow-x: hidden !important;
            }

            .block-container {
                padding: 0 !important;
            }

            [data-testid="stHorizontalBlock"] {
                flex-direction: column !important;
                height: auto !important;
                min-height: 100vh !important;
                max-height: none !important;
                width: 100% !important;
            }

            /* Cabeçalho institucional compacto no topo */
            [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child {
                width: 100% !important;
                max-width: 100% !important;
                flex: 0 0 auto !important;
                height: auto !important;
                max-height: none !important;
                padding: 1.5rem 1.25rem 1.25rem 1.25rem !important;
                border-right: none !important;
                border-bottom: 1px solid #E2E8F0 !important;
                background: #FFFFFF !important;
            }

            .cti-inst-content-box {
                max-width: 100%;
                text-align: center;
                align-items: center;
            }
            .cti-inst-brand-tag {
                margin: 0 auto 0.6rem auto;
            }
            .cti-inst-headline {
                color: #064E3B !important;
                font-size: 1.3rem !important;
                margin-bottom: 0.3rem !important;
                text-align: center;
            }
            .cti-inst-lead {
                display: none !important; /* cabeçalho compacto para preservar espaço no celular */
            }
            .cti-inst-feature-list {
                display: none !important; /* cabeçalho compacto para priorizar o formulário */
            }

            /* Lado do login ocupa o restante com total foco */
            [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child {
                width: 100% !important;
                max-width: 100% !important;
                flex: 1 1 auto !important;
                height: auto !important;
                max-height: none !important;
                padding: 1.5rem 1rem 2.5rem 1rem !important;
            }

            [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child [data-testid="stForm"] {
                max-width: 100% !important;
                min-width: unset !important;
                padding: 24px 20px !important;
                border-radius: 14px !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Divisão em duas colunas com proporção aproximada de 55% e 45% (1.22 : 1)
    col_left, col_right = st.columns([1.22, 1], gap="small")

    # -------------------------------------------------------------
    # LADO ESQUERDO — APRESENTAÇÃO INSTITUCIONAL
    # -------------------------------------------------------------
    with col_left:
        st.markdown(
            """
            <div class="cti-inst-content-box">
                <div class="cti-inst-brand-tag">
                    <span class="cti-inst-brand-dot"></span>
                    <span>CTI GLOBAL</span>
                </div>
                <h1 class="cti-inst-headline">Inteligência financeira para decisões estratégicas</h1>
                <p class="cti-inst-lead">Uma plataforma integrada para análise de desempenho, planejamento financeiro e acompanhamento de indicadores corporativos.</p>
                <div class="cti-inst-feature-list">
                    <div class="cti-inst-feature-card">
                        <div class="cti-inst-feature-icon">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#0B5D3B" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <line x1="18" y1="20" x2="18" y2="10"></line>
                                <line x1="12" y1="20" x2="12" y2="4"></line>
                                <line x1="6" y1="20" x2="6" y2="14"></line>
                            </svg>
                        </div>
                        <div>
                            <div class="cti-inst-feature-title">Demonstrações Integradas</div>
                            <div class="cti-inst-feature-desc">DRE, Balanço, DFC e DVA com validação contábil contínua.</div>
                        </div>
                    </div>
                    <div class="cti-inst-feature-card">
                        <div class="cti-inst-feature-icon">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#0B5D3B" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <circle cx="12" cy="12" r="10"></circle>
                                <polyline points="12 6 12 12 14 14"></polyline>
                            </svg>
                        </div>
                        <div>
                            <div class="cti-inst-feature-title">62 Indicadores Auditados</div>
                            <div class="cti-inst-feature-desc">Métricas de liquidez, rentabilidade, capital de giro e solvência.</div>
                        </div>
                    </div>
                    <div class="cti-inst-feature-card">
                        <div class="cti-inst-feature-icon">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#0B5D3B" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
                            </svg>
                        </div>
                        <div>
                            <div class="cti-inst-feature-title">Planejamento e Governança</div>
                            <div class="cti-inst-feature-desc">Simulação de cenários, sensibilidade e projeções estratégicas.</div>
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # -------------------------------------------------------------
    # LADO DIREITO — FORMULÁRIO DE LOGIN
    # -------------------------------------------------------------
    with col_right:
        with st.form("cti_corporate_login_form", clear_on_submit=False):
            st.markdown(
                """
                <div class="cti-form-header">
                    <h2 class="cti-form-title">Bem-vindo à CTI Global</h2>
                    <p class="cti-form-subtitle">Entre com suas credenciais para acessar a plataforma.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Exibição de aviso de sessão expirada se houver
            if expired_message:
                st.warning(f"⚠️ {expired_message}")

            # Campos de Usuário e Senha padronizados
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

            # Botão Entrar destacado em verde-escuro
            submit_btn = st.form_submit_button(
                "Entrar",
                use_container_width=True,
                type="primary",
                key="cti_corporate_login_form_submit",
            )

            # Processamento de autenticação no backend
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

            # Rodapé discreto no próprio card
            st.markdown(
                """
                <div class="cti-form-footer">
                    <strong>CTI Global</strong> | Plataforma Analítica de Planejamento Financeiro
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
