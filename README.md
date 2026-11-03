# CTI Global | Plataforma Analítica de Planejamento Financeiro

Plataforma corporativa analítica de Business Intelligence, Controladoria, Planejamento Financeiro e Ciência de Dados da **CTI Global**.

> 📌 **DOCUMENTAÇÕES DEDICADAS PARA AS ENTREGAS 2 (FECAP 2026):**
> - 📊 **Contabilidade e Finanças (Entrega 2 - Final):** Acesse [`README_CONTABILIDADE_E_FINANCAS.md`](./README_CONTABILIDADE_E_FINANCAS.md) para o detalhamento das demonstrações financeiras (DRE, Balanço, DFC, DVA), módulos de capital de giro e prazos médios, índices da DFC, sensibilidade e validação contábil.
> - 🔬 **Projeto Interdisciplinar: Ciência de Dados (Entrega 2 - Final):** Acesse [`README_CIENCIA_DE_DADOS.md`](./README_CIENCIA_DE_DADOS.md) para o detalhamento da arquitetura de dados (Raw -> Staging -> Processed), catálogo de 62 KPIs, análises estatísticas descritiva/inferencial, modelo de regressão linear múltipla (OLS) com prevenção de vazamento e documentação técnica.

---

## 1. Visão Geral e Objetivo da Plataforma

Este sistema integra, audita e analisa a base de dados corporativa oficial da CTI Global (`Contabilidade e Finanças.xlsx`, composta por **9 abas**, **1.200 cenários corporativos** `Cen_00001` a `Cen_01200` e **12 períodos numerados** `Ano 1` a `Ano 12`), oferecendo suporte executivo à tomada de decisão financeira e operacional:

- **Painel Executivo e Demonstrações Financeiras Integradas:** Visão Executiva corporativa, DRE (com segregação estrita entre `EBITDA Calculado` e `EBITDA do Modelo`), Balanço Patrimonial, Fluxo de Caixa (DFC gerencial e conciliada no regime de caixa) e Demonstração do Valor Adicionado (DVA com distribuição aos empregados, governo, credores e acionistas).
- **Módulos Especializados da DFC e Capital de Giro:** Índices da Demonstração dos Fluxos de Caixa (Qualidade do Caixa, Investimentos/Capex, Capacidade de Pagamento e Sustentabilidade de Dividendos), além de Capital de Giro e Prazos Médios (CCL, PMR, PMP, Ciclo Financeiro Simplificado e Necessidade de Capital de Giro).
- **Catálogo Auditado de 62 KPIs, Rankings e Evolução Temporal:** Consulta estruturada por categoria/família contábil, posicionamento nos 5 recortes de `Top10_Rankings`, comparador multicenário e evolução `Ano 1` a `Ano 12` com tratamento transparente do `Ano 12` patrimonial incompleto (`N/D`).
- **Planejamento Operacional e Simulações em Memória:** Análise de sensibilidade financeira interativa (desconto comercial, cupom/preço, volume, custos fixos/variáveis e WACC), metas financeiras corporativas configuráveis (sem metas artificiais pré-inventadas) e simulador parametrizado de Ticket Médio, CAC, LTV e Unit Economics.
- **Ciência de Dados e Governança:** Estatística descritiva e inferencial reconciliada em `100%` com `KPIs_Estatisticas`, matriz de correlação, regressão linear múltipla (OLS) com partição Treino/Teste agrupada por `Cenário` (`GroupShuffleSplit`), diagnósticos econométricos (VIF, Jarque-Bera, Breusch-Pagan, erros-padrão robustos), central de relatórios gerenciais em **CSV**, **XLSX multi-abas** e **PDF executivo**, e Dicionário Corporativo dos 62 KPIs.

---

## 2. Tecnologias Utilizadas

| Camada | Tecnologias |
| :--- | :--- |
| **Linguagem & Interface Web** | Python 3.11+ (validado em Python 3.14), Streamlit |
| **Segurança & Autenticação** | Bcrypt (hashing seguro), HMAC tempo-constante, proteção de sessão e rate-limiting |
| **Engenharia de Dados & Cache** | Pandas, NumPy, PyArrow (Parquet com verificação SHA-256), OpenPyXL |
| **Visualização Interativa** | Plotly Graph Objects (padrão numérico brasileiro `pt-BR` e design responsivo) |
| **Estatística & Econometria / ML** | SciPy, Statsmodels (OLS robusto `HC3` / Cluster), Scikit-learn (`GroupShuffleSplit`) |
| **Exportação Documental** | XlsxWriter (`.xlsx` formatado multi-abas), fpdf2 (`.pdf` executivo), CSV UTF-8-BOM |
| **Qualidade & Testes Automatizados** | Pytest + Streamlit `AppTest` (testes unitários, autenticação, reconciliação contábil e E2E UI) |

---

## 3. Estrutura de Pastas do Projeto

```text
DASHBOARD/
├── app.py                              # Roteamento oficial das 14 páginas corporativas e filtros globais
├── requirements.txt                    # Dependências Python com versões compatíveis para nuvem e local
├── .gitignore                          # Protege a planilha original (.xlsx), caches locais e segredos
├── .env.example                        # Variáveis de ambiente opcionais (CTI_EXCEL_PATH, CTI_DATA_DIR)
├── .streamlit/
│   └── config.toml                     # Tema institucional corporativo (verde-escuro #0B5D3B) e segurança
├── src/
│   ├── auth.py                         # Gatekeeper de autenticação, bcrypt, rate limiting e gestão de sessão
│   ├── config.py                       # Catálogo auditado dos 62 KPIs, paleta corporativa e formatadores pt-BR
│   ├── data_loader.py                  # Descoberta segura do Excel, upload em memória e cache Parquet (Staging)
│   ├── data_processing.py              # Pipeline Staging -> Processed (Painel 14.400 vs Resumo 1.200)
│   ├── financial_kpis.py               # Motor de cálculo dos 62 KPIs (DFC, Capital de Giro, Fluxo e DVA)
│   ├── data_validation.py              # Validação estrutural, reconciliação 100% e auditoria AUD-01 a AUD-05
│   ├── sensitivity_analysis.py         # Simulador de sensibilidade em memória e Unit Economics (Ticket/CAC/LTV)
│   ├── statistical_analysis.py         # Estatística descritiva, reconciliação KPIs_Estatisticas e correlações
│   ├── regression_analysis.py          # Regressão OLS com GroupShuffleSplit por cenário, VIF e detector de tautologia
│   ├── reporting.py                    # Geradores de relatórios CSV, Excel multi-abas e PDF executivo
│   ├── ui_components.py                # Design system CSS responsivo (360px a 1920px) e cartões de KPI
│   ├── charts.py                       # Fábrica de gráficos interativos Plotly padronizados
│   └── views/                          # Módulos das 17 páginas corporativas
│       ├── executive_and_statements.py # Páginas 1 a 3 (Visão Executiva, DRE, Balanço Patrimonial)
│       ├── cashflow_workingcapital_dva.py # Páginas 4, 5, 7 e 8 (Fluxo de Caixa, DVA, Índices DFC e Capital de Giro)
│       ├── kpis_scenarios_evolution.py # Páginas 6, 9 e 10 (Indicadores, Cenários & Rankings, Evolução Financeira)
│       ├── planning_simulation_goals.py# Páginas 11, 12 e 17 (Sensibilidade, Metas, Metodologia & Indicadores)
│       └── datascience_quality_exports.py # Páginas 13 a 16 (Estatística, OLS, Relatórios & Governança)
├── tests/
│   ├── conftest.py                     # Fixtures compartilhadas sobre a base corporativa oficial
│   ├── test_auth.py                    # Testes de autenticação, bcrypt, rate limiting, timeout e logout
│   ├── test_data_loading.py            # Testes de leitura, abas essenciais, erros e modo sintético isolado
│   ├── test_financial_kpis.py          # Reconciliação 100%, Ano 12 N/D, safe_divide, DFC e metas
│   ├── test_dfc_capital_dva.py         # Testes dos 4 novos módulos (DFC, Giro, Fluxo, DVA) e identidades contábeis
│   ├── test_sensitivity.py             # Testes de choques econômicos, imutabilidade da base e LTV/CAC
│   ├── test_filters.py                 # Testes de filtros, KPIs_Estatisticas, OLS sem vazamento e exportações
│   └── test_app_ui.py                  # Teste E2E Headless renderizando todas as 17 páginas corporativas
├── docs/
│   ├── catalogo_dados.md               # Inventário das 9 abas e arquitetura Raw -> Staging -> Processed
│   ├── dicionario_kpis.md              # Fichas completas dos KPIs com fórmulas, regras e interpretações
│   ├── auditoria_qualidade_kpis.md     # Relatório formal dos achados AUD-01 a AUD-05 e reconciliações
│   ├── metodologia.md                  # Metodologia de cálculo, sensibilidade e modelagem econométrica OLS
│   ├── limitacoes.md                   # Limitações contábeis, estatísticas e de escopo de dados
│   └── publicacao.md                   # Guia passo a passo para deploy em nuvem
└── data/
    ├── raw/                            # Camada bruta (somente leitura)
    ├── staging/                        # Cache Parquet tipado verificado por hash SHA-256
    └── processed/                      # Tabelas analíticas processadas e manifesto de linhagem
```

---

## 4. Fonte de Dados e Requisitos para Execução

- **Planilha Oficial:** `Contabilidade e Finanças.xlsx` ou `Contabilidade e Finanças(4).xlsx`, posicionada na raiz do projeto ou em `data/raw/` (ou apontada via `CTI_EXCEL_PATH`).
- **Integridade Garantida:** A planilha original nunca é modificada. Na primeira leitura (~14 segundos), a aplicação constrói automaticamente o cache verificado por SHA-256 em `data/staging/`, reduzindo os carregamentos subsequentes para **menos de 0,15 segundo**.
- **Requisitos:** Python `3.11+`, `pip` e ambiente virtual (`venv`).

---

## 5. Como Instalar as Dependências e Executar Localmente

No Windows (PowerShell):

```powershell
# 1. Criar e ativar o ambiente virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Instalar as dependências
pip install -r requirements.txt

# 3. Iniciar o dashboard Streamlit
streamlit run app.py
```

No Linux / macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Acesse no navegador: `http://localhost:8501`

---

## 6. Controle de Acesso, Autenticação e Gestão de Sessão

A aplicação abre diretamente na tela institucional de autenticação da CTI Global, bloqueando o acesso a todas as 17 páginas e impedindo o carregamento prévio de dados financeiros confidenciais:

- **Credenciais Iniciais (Ambiente de Desenvolvimento):**
  - **Usuário:** `admin`
  - **Senha:** `admin123`
- **Validação Segura no Backend:** A verificação utiliza hash criptográfico **bcrypt** (`$2b$12$...`) com salt aleatório e comparação de tempo constante (`hmac.compare_digest`). Nenhuma senha em texto puro é mantida fixa no código-fonte.
- **Configuração de Produção e Troca de Senha:**
  - Configure as variáveis de ambiente no arquivo `.env` (ou nos Secrets da plataforma de nuvem em `.streamlit/secrets.toml`):
    ```toml
    # Exemplo em .streamlit/secrets.toml
    [auth]
    username = "admin"
    password_hash = "$2b$12$..." # Hash gerado via bcrypt
    session_timeout_minutes = 30
    max_login_attempts = 5
    lockout_minutes = 15
    ```
  - Para gerar um novo hash para uma nova senha forte, execute no terminal:
    ```powershell
    python -c "import bcrypt; print(bcrypt.hashpw(b'SuaSenhaForteAqui', bcrypt.gensalt(12)).decode())"
    ```
- **Expiração por Inatividade:** Sessões inativas por mais de **30 minutos** são invalidadas automaticamente pelo servidor, exigindo nova autenticação.
- **Proteção contra Força Bruta (Rate Limiting):** Após **5 tentativas incorretas consecutivas**, o acesso é bloqueado temporariamente por **15 minutos**.
- **Botão de Logout Institucional:** Disponível na barra lateral e cabeçalho corporativo (`👤 Administrador | 🚪 Sair do Sistema`). O clique revoga a sessão no servidor e impede o retorno através do botão "Voltar" do navegador.

---

## 7. Como Executar os Testes Automatizados

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

A suíte executa testes automatizados cobrindo leitura de dados, reconciliação de `100%` dos KPIs com `KPIs_Cenarios`, `Resumo_Cenarios` e `KPIs_Estatisticas`, cálculo dos 4 novos módulos e suas identidades contábeis, proteção contra divisão por zero, tratamento de `N/D` no `Ano 12`, imutabilidade na análise de sensibilidade, ausência de vazamento entre cenários na regressão OLS, validade de arquivos CSV/XLSX/PDF e renderização ponta a ponta das **17 páginas corporativas** via `AppTest`.

---

## 7. Como Publicar na Nuvem

Consulte o guia detalhado em [`docs/publicacao.md`](docs/publicacao.md):
1. Inicialize o repositório Git e verifique com `git status` que o arquivo `.xlsx` bruto está protegido pelo `.gitignore`.
2. Conecte o repositório ao serviço de hospedagem em nuvem apontando para `app.py`.
3. Na URL publicada, envie o arquivo corporativo oficial pelo componente de upload seguro em memória (ou utilize o botão de *Modo Demonstração Sintética* para demonstração corporativa).

---

## 8. Principais Decisões Metodológicas e Limitações Conhecidas

- **Unidade Monetária (`R$`):** Padronizada em `R$` conforme `KPIs_Cenarios`, `KPIs_Estatisticas` e `Resumo_Cenarios`, sem multiplicação artificial por 1.000 (`AUD-02`).
- **Separação de EBITDAs:** `EBITDA Calculado` (`Resultado Operacional + |D&A|`) e `EBITDA do Modelo` (`DRE - EBITDA`) são sempre exibidos separadamente.
- **Períodos Numerados e `Ano 12`:** Os períodos `Ano 1` a `Ano 12` não são convertidos em anos civis. No `Ano 12`, os 12 KPIs dependentes do Balanço incompleto são reportados como `N/D` (`AUD-03`).
- **Ticket Médio, Metas e Premissas:** O Ticket Médio empírico é reportado como `N/D` na base original; metas iniciam como `Não definida`; valores simulados (`CAC`, `LTV`, `Ticket Médio simulado` e choques de sensibilidade) recebem identificação visual exclusiva em azul (**Simulado**).
- Consulte [`docs/auditoria_qualidade_kpis.md`](docs/auditoria_qualidade_kpis.md), [`docs/metodologia.md`](docs/metodologia.md) e [`docs/limitacoes.md`](docs/limitacoes.md) para o detalhamento completo.
