# Dicionário Técnico Auditado de Indicadores Financeiros e Operacionais (KPIs)

**CTI Global | Plataforma Analítica de Planejamento Financeiro — Dicionário Técnico de KPIs**

Este documento consolida todos os 22 indicadores catalogados em `src/config.py`, reconciliando a referência conceitual de `Dicionario_KPIs` com as fórmulas auditadas de `KPIs_Cenarios`, `KPIs_Estatisticas` e `Resumo_Cenarios`, além de corrigir o desalinhamento de ordenação da coluna `Regra de validação` (`AUD-01`) e padronizar a convenção monetária `R$` (`AUD-02`).

---

## 1. Tabela Resumo de Todos os Indicadores

| # | Indicador | Categoria | Unidade Adotada | Fórmula Auditada | Cobertura Temporal |
| :-: | :--- | :--- | :---: | :--- | :---: |
| 1 | **Receita** | Complementares e Operacionais | `R$` | `ABS(DRE - Receita)` | Anos 1 a 12 |
| 2 | **Custos Variáveis (Proxy)** | Complementares e Operacionais | `R$` | `ABS(DRE - Custos)` | Anos 1 a 12 |
| 3 | **Margem de Contribuição** | Rentabilidade e Geração de Valor | `%` | `(ABS(Receita) + Tributos - ABS(Custos)) / (ABS(Receita) + Tributos)` | Anos 1 a 12 |
| 4 | **EBITDA Calculado** | Rentabilidade e Geração de Valor | `R$` | `Resultado Operacional + ABS(Depreciação e Amortização)` | Anos 1 a 12 |
| 5 | **EBITDA do Modelo** | Rentabilidade e Geração de Valor | `R$` | `DRE - EBITDA` *(mantido separado do EBITDA Calculado)* | Anos 1 a 12 |
| 6 | **Margem EBITDA Calculada** | Rentabilidade e Geração de Valor | `%` | `EBITDA Calculado / ABS(Receita)` | Anos 1 a 12 |
| 7 | **Margem EBITDA do Modelo** | Rentabilidade e Geração de Valor | `%` | `EBITDA do Modelo / ABS(Receita)` | Anos 1 a 12 |
| 8 | **Resultado Líquido (DRE)** | Rentabilidade e Geração de Valor | `R$` | `DRE - Resultado Líquido` | Anos 1 a 12 |
| 9 | **NOPAT** | Rentabilidade e Geração de Valor | `R$` | `Resultado Operacional × (1 - \|IR/CSLL\| / \|LAIR\|)` | Anos 1 a 11 (`N/D` Ano 12) |
| 10 | **Capital Investido** | Rentabilidade e Geração de Valor | `R$` | `ABS(PC) + ABS(PNC) + ABS(Ativo Total - ABS(PC) - ABS(PNC))` | Anos 1 a 11 (`N/D` Ano 12) |
| 11 | **EVA (Economic Value Added)** | Rentabilidade e Geração de Valor | `R$` | `NOPAT - (Capital Investido × WACC)`, `WACC = 12%` | Anos 1 a 11 (`N/D` Ano 12) |
| 12 | **ROIC** | Rentabilidade e Geração de Valor | `%` | `NOPAT / Capital Investido` | Anos 1 a 11 (`N/D` Ano 12) |
| 13 | **Liquidez Corrente (LC) – Ajustada** | Liquidez | `x` | `Ativo Circulante / ABS(Passivo Circulante)` | Anos 1 a 11 (`N/D` Ano 12) |
| 14 | **Liquidez Seca (LS)** | Liquidez | `x` | `(Ativo Circulante - Estoques Diversos) / ABS(PC)` | Anos 1 a 11 (`N/D` Ano 12) |
| 15 | **Liquidez Imediata (LI)** | Liquidez | `x` | `Disponível / ABS(Passivo Circulante)` | Anos 1 a 11 (`N/D` Ano 12) |
| 16 | **Liquidez Geral (LG)** | Liquidez | `x` | `(AC + Realizável LP) / (ABS(PC) + ABS(Exigível LP))` | Anos 1 a 11 (`N/D` Ano 12) |
| 17 | **Participação de Capital de Terceiros (PCT)** | Endividamento e Estrutura de Capital | `x` | `(ABS(PC) + ABS(PNC)) / ABS(Ativo Total - ABS(PC) - ABS(PNC))` | Anos 1 a 11 (`N/D` Ano 12) |
| 18 | **Composição do Endividamento (CE) – Ajustada** | Endividamento e Estrutura de Capital | `%` | `ABS(PC) / (ABS(PC) + ABS(PNC))` | Anos 1 a 11 (`N/D` Ano 12) |
| 19 | **Imobilização do Patrimônio Líquido (IPL)** | Endividamento e Estrutura de Capital | `x` | `(Ativo Total - AC) / ABS(Ativo Total - ABS(PC) - ABS(PNC))` | Anos 1 a 11 (`N/D` Ano 12) |
| 20 | **Endividamento Geral** | Endividamento e Estrutura de Capital | `%` | `(ABS(PC) + ABS(PNC)) / Ativo Total` | Anos 1 a 11 (`N/D` Ano 12) |
| 21 | **Geração de Caixa (DFC)** | Fluxo de Caixa | `R$` | `FLU - Saldo Final - FLU - Saldo Inicial` (`FLU - Geração de Caixa`) | Anos 1 a 12 |
| 22 | **Saldo Final de Caixa** | Fluxo de Caixa | `R$` | `FLU - Saldo Final` (`= BAL - Disponível`) | Anos 1 a 12 |

---

## 2. Premissas e Indicadores Simulados de Unit Economics

| Indicador Simulado | Unidade | Fórmula / Valor de Referência (Base Corporativa) | Natureza e Tratamento |
| :--- | :---: | :--- | :--- |
| **Ticket Médio Observado** | `R$` | `Receita / Nº de Transações` -> **Indisponível (`N/D`) na fonte** | Exibido como `N/D` na base original; parametrizável no simulador com selo **Simulação**. |
| **CAC Simulado** | `R$/cliente` | `Investimento em Aquisição / Novos Clientes` (Ref. Base: `R$ 200,00/cliente`) | Premissa constante do modelo; editável em memória na Página 10. |
| **LTV Simulado** | `R$/cliente` | `Ticket Médio × Compras/Ano × Vida Média (anos) × Margem %` (Ref. Base: `R$ 2.100,00/cliente`) | Premissa simulada; recalculada dinamicamente a partir das hipóteses inseridas. |
| **Relação LTV / CAC** | `x` | `LTV Simulado / CAC Simulado` (Ref. Base: `10,50x`) | Protegida contra `CAC = 0` via `safe_divide`. |
| **WACC do Modelo** | `% a.a.` | `12,00%` (`0,12`) | Premissa metodológica utilizada para cálculo do EVA; ajustável no simulador de sensibilidade. |

---

## 3. Fichas Detalhadas por Bloco Analítico (13 Atributos Obrigatórios)

### 3.1. Bloco Operacional e Margens (DRE)

- **Objetivo:** Mensurar faturamento, consumo operacional direto, margem de contribuição e capacidade de geração operacional potencial de caixa sob regime de competência.
- **Fonte dos Dados:** `DRE_Cenarios`, `KPIs_Cenarios` e `Resumo_Cenarios`.
- **Granularidade e Periodicidade:** `Cenário × Período` (anual, períodos numerados `Ano 1` a `Ano 12`); consolidado por `Cenário` pela média dos Anos 1 a 11 em `Resumo_Cenarios`.
- **Premissas:**
  1. `DRE - Tributos` e `DRE - Custos` possuem sinal negativo na DRE.
  2. Como não há separação contábil entre custos fixos e variáveis, `ABS(DRE - Custos)` atua como proxy de custos variáveis.
  3. As Margens EBITDA utilizam a Receita Bruta (`ABS(DRE - Receita)`) no denominador, conforme diretriz contábil corporativa.
- **Regras de Validação e Valores Ausentes:** Verificar denominadores `ABS(Receita) > 0` e `(ABS(Receita) + Tributos) > 0`; retornar `N/D` (`NaN`) via `safe_divide` caso nulos ou zero.
- **Interpretação e Limitações:** Margens mais elevadas sinalizam maior eficiência operacional, mas `EBITDA Calculado` e `EBITDA do Modelo` devem ser analisados separadamente e não equivalem ao fluxo de caixa efetivo da DFC.

### 3.2. Bloco de Liquidez e Estrutura Patrimonial (Balanço)

- **Objetivo:** Avaliar solvência de curto e longo prazo (`LC`, `LS`, `LI`, `LG`) e grau/perfil de alavancagem financeira (`PCT`, `CE`, `IPL`, `Endividamento Geral`).
- **Fonte dos Dados:** `Balanco_Cenarios`, `KPIs_Cenarios` e `Resumo_Cenarios`.
- **Granularidade e Periodicidade:** `Cenário × Período` (anual, disponível nos `Anos 1 a 11`).
- **Premissas:** Passivos e Patrimônio Líquido são tratados em módulo (`ABS`) para neutralizar convenções de sinal credor; `ANC = Ativo Total - Ativo Circulante`; PL implícito do modelo corporativo dado por `ABS(Ativo Total - ABS(PC) - ABS(PNC))`.
- **Regras de Validação e Valores Ausentes:** Detectar automaticamente `Balanco_Incompleto == True` (como ocorre nos 1.200 cenários no `Ano 12`) e denominadores iguais a zero, atribuindo `N/D` sem inventar valores.
- **Interpretação e Limitações:** `LC > 1,00x` indica cobertura positiva das obrigações correntes; `LG < 1,00x` é estruturalmente frequente em concessões intensivas em ativos permanentes de longo prazo. `PCT` e `IPL` apresentam cauda longa (outliers) quando o denominador modular aproxima-se de zero.

### 3.3. Bloco de Criação de Valor Econômico (`NOPAT`, `Capital Investido`, `ROIC`, `EVA`)

- **Objetivo:** Quantificar se o retorno operacional líquido após impostos supera o custo de oportunidade do capital investido (`WACC`).
- **Fonte dos Dados:** `DRE_Cenarios`, `Balanco_Cenarios` e `KPIs_Cenarios`.
- **Granularidade e Periodicidade:** `Cenário × Período` (anual, `Anos 1 a 11`; `N/D` no `Ano 12`).
- **Premissas:** Alíquota efetiva de tributos sobre o lucro apurada por `|IR/CSLL| / |Resultado Antes do IR|`; `WACC = 12,00%` como premissa constante do modelo corporativo.
- **Regras de Validação e Valores Ausentes:** Bloquear divisão quando `LAIR = 0` ou `Capital Investido = 0`; exibir `N/D` no `Ano 12`.
- **Interpretação e Limitações:** `ROIC > 12,00%` e `EVA > R$ 0` indicam criação de valor econômico acima da taxa mínima de atratividade parametrizada no modelo.

