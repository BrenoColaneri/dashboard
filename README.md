# CTI Global | Plataforma Analítica de Planejamento Financeiro

Plataforma corporativa analítica de Business Intelligence, Controladoria, Planejamento Financeiro e Ciência de Dados da **CTI Global**.

---

## 1. Visão Geral e Objetivo da Plataforma

Este sistema integra, audita e analisa a base de dados corporativa oficial da CTI Global (`Contabilidade e Finanças.xlsx`, composta por **9 abas**, **1.200 cenários corporativos** `Cen_00001` a `Cen_01200` e **12 períodos numerados** `Ano 1` a `Ano 12`), oferecendo suporte executivo à tomada de decisão financeira e operacional:

- **Painel Executivo e Demonstrações Financeiras Integradas:** Visão Executiva corporativa, DRE (com segregação estrita entre `EBITDA Calculado` e `EBITDA do Modelo`), Balanço Patrimonial e Fluxo de Caixa (DFC, distinguindo lucro contábil por competência de geração efetiva de caixa).
- **Catálogo Auditado de KPIs, Rankings e Evolução Temporal:** Consulta estruturada por categoria, posicionamento nos 5 recortes de `Top10_Rankings`, comparador multicenário e evolução `Ano 1` a `Ano 12` com tratamento transparente do `Ano 12` patrimonial incompleto (`N/D`).
- **Planejamento Operacional e Simulações em Memória:** Análise de sensibilidade financeira interativa (desconto comercial, cupom/preço, volume, custos fixos/variáveis e WACC), metas financeiras corporativas configuráveis (sem metas artificiais pré-inventadas) e simulador parametrizado de Ticket Médio, CAC, LTV e Unit Economics.
- **Ciência de Dados e Governança:** Estatística descritiva e inferencial reconciliada em `100%` com `KPIs_Estatisticas`, matriz de correlação, regressão linear múltipla (OLS) com partição Treino/Teste agrupada por `Cenário` (`GroupShuffleSplit`), diagnósticos econométricos (VIF, Jarque-Bera, Breusch-Pagan, erros-padrão robustos) e central de relatórios gerenciais em **CSV**, **XLSX multi-abas** e **PDF executivo**.

---

## 2. Tecnologias Utilizadas

| Camada | Tecnologias |
| :--- | :--- |
| **Linguagem & Interface Web** | Python 3.11+ (validado em Python 3.14), Streamlit |
| **Engenharia de Dados & Cache** | Pandas, NumPy, PyArrow (Parquet com verificação SHA-256), OpenPyXL |
| **Visualização Interativa** | Plotly Graph Objects (padrão numérico brasileiro `pt-BR` e design responsivo) |
| **Estatística & Econometria / ML** | SciPy, Statsmodels (OLS robusto `HC3` / Cluster), Scikit-learn (`GroupShuffleSplit`) |
| **Exportação Documental** | XlsxWriter (`.xlsx` formatado multi-abas), fpdf2 (`.pdf` executivo), CSV UTF-8-BOM |
| **Qualidade & Testes Automatizados** | Pytest + Streamlit `AppTest` (testes unitários, reconciliação contábil e E2E UI) |

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
│   ├── config.py                       # Catálogo auditado dos 22 KPIs, paleta corporativa e formatadores pt-BR
│   ├── data_loader.py                  # Descoberta segura do Excel, upload em memória e cache Parquet (Staging)
│   ├── data_processing.py              # Pipeline Staging -> Processed (Painel 14.400 vs Resumo 1.200)
│   ├── financial_kpis.py               # Motor de recálculo contábil, safe_divide, metas e auditoria de Ticket Médio
│   ├── data_validation.py              # Validação estrutural, reconciliação 100% e auditoria AUD-01 a AUD-05
│   ├── sensitivity_analysis.py         # Simulador de sensibilidade em memória e Unit Economics (Ticket/CAC/LTV)
│   ├── statistical_analysis.py         # Estatística descritiva, reconciliação KPIs_Estatisticas e correlações
│   ├── regression_analysis.py          # Regressão OLS com GroupShuffleSplit por cenário, VIF e detector de tautologia
│   ├── reporting.py                    # Geradores de relatórios CSV, Excel multi-abas e PDF executivo
│   ├── ui_components.py                # Design system CSS responsivo (360px a 1920px) e cartões de KPI
│   ├── charts.py                       # Fábrica de gráficos interativos Plotly padronizados
│   └── views/                          # Módulos das 14 páginas corporativas
│       ├── executive_and_statements.py # Páginas 1 a 4 (Visão Executiva, DRE, Balanço, Fluxo de Caixa)
│       ├── kpis_scenarios_evolution.py # Páginas 5 a 7 (Indicadores, Cenários & Rankings, Evolução Financeira)
│       ├── planning_simulation_goals.py# Páginas 8 a 10 (Sensibilidade, Metas, Ticket Médio & Unit Economics)
│       └── datascience_quality_exports.py # Páginas 11 a 14 (Estatística, OLS, Governança & Relatórios)
├── tests/
│   ├── conftest.py                     # Fixtures compartilhadas sobre a base corporativa oficial
│   ├── test_data_loading.py            # Testes de leitura, abas essenciais, erros e modo sintético isolado
│   ├── test_financial_kpis.py          # Reconciliação 100%, Ano 12 N/D, safe_divide, DFC e metas
│   ├── test_sensitivity.py             # Testes de choques econômicos, imutabilidade da base e LTV/CAC
│   ├── test_filters.py                 # Testes de filtros, KPIs_Estatisticas, OLS sem vazamento e exportações
│   └── test_app_ui.py                  # Teste E2E Headless renderizando todas as 14 páginas corporativas
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

## 6. Como Executar os Testes Automatizados

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

A suíte executa testes automatizados cobrindo leitura de dados, reconciliação de `100%` dos KPIs com `KPIs_Cenarios`, `Resumo_Cenarios` e `KPIs_Estatisticas`, proteção contra divisão por zero, tratamento de `N/D` no `Ano 12`, imutabilidade na análise de sensibilidade, ausência de vazamento entre cenários na regressão OLS, validade de arquivos CSV/XLSX/PDF e renderização ponta a ponta das **14 páginas corporativas** via `AppTest`.

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
