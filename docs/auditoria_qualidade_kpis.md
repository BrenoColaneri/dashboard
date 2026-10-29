# Relatório de Auditoria Metodológica e Qualidade de KPIs

**CTI Global | Plataforma Analítica de Planejamento Financeiro — Auditoria e Governança de Dados**

Durante a auditoria automatizada da planilha `Contabilidade e Finanças.xlsx`, confrontamos linha a linha a aba `Dicionario_KPIs` com as fórmulas e valores efetivamente calculados nas abas `KPIs_Cenarios`, `KPIs_Estatisticas`, `Resumo_Cenarios`, `DRE_Cenarios`, `Balanco_Cenarios` e `DFC_Cenarios`.

A planilha original foi **100% preservada sem edições**, e todas as tratativas abaixo foram codificadas de forma transparente e reproduzível nos módulos `src/config.py`, `src/financial_kpis.py` e `src/data_validation.py`.

---

## Resumo dos 5 Achados Formais de Auditoria

### `AUD-01` — Desalinhamento de Ordenação na Coluna `Regra de validação` de `Dicionario_KPIs`
- **Severidade:** Média (Documental).
- **Evidência observada:** Nas linhas 2 a 20 da aba `Dicionario_KPIs`, as colunas `A` a `K` (`Categoria` até `Dimensão de análise`) foram ordenadas alfabeticamente sem incluir a coluna `L` (`Regra de validação`) na seleção de ordenação do Excel. Como consequência, a linha de *Custos variáveis* exibe a regra `Verificar PC ≠ 0; conferir AC/ABS(PC)` (pertencente à *Liquidez Corrente*), a linha de *Liquidez Corrente* exibe a regra de *Margem EBITDA calculada*, e assim sucessivamente.
- **Resolução adotada:** No catálogo interno auditado (`KPI_CATALOG` em `src/config.py`) e em `docs/dicionario_kpis.md`, cada indicador foi remapeado para sua regra de validação matemática verdadeira, mantendo um alerta explicativo sempre que a tabela bruta de `Dicionario_KPIs` é exibida na interface.

---

### `AUD-02` — Divergência de Unidade Monetária (`R$ mil` no Dicionário vs. `R$` nas Abas Analíticas)
- **Severidade:** Alta (Padronização de Escala Monetária).
- **Evidência observada:** A coluna `Unidade` de `Dicionario_KPIs` indica `R$ mil` para *Receita*, *Custos variáveis*, *EBITDA calculado*, *EBITDA do modelo*, *NOPAT*, *Capital Investido* e *EVA*. Contudo:
  1. Os cabeçalhos de `KPIs_Cenarios` e `Resumo_Cenarios` rotulam explicitamente `(R$)` — ex.: `Receita (R$)`, `EBITDA calculado (R$)`, `EVA (R$)`.
  2. A aba `KPIs_Estatisticas` registra `R$` na coluna `Unidade` para todos esses indicadores.
  3. Os valores numéricos já estão na escala de bilhões de unidades monetárias (ex.: Receita média de `6.726.329.882,04` no Ano 1 e `CAC simulado = 200,00 R$/cliente`).
- **Resolução adotada:** **Nenhuma multiplicação arbitrária por 1.000 foi realizada.** Adotou-se `R$` como convenção única em todo o dashboard, gráficos e relatórios, garantindo **100% de paridade numérica** com `KPIs_Cenarios`, `KPIs_Estatisticas` e `Resumo_Cenarios`, além de documentar a unidade bruta do dicionário na ficha de cada KPI.

---

### `AUD-03` — Incompletude Estrutural do Balanço Patrimonial no `Ano 12`
- **Severidade:** Média (Limitação Estrutural da Fonte).
- **Evidência observada:** No período `Ano 12`, 27 das 43 contas da aba `Balanco_Cenarios` (incluindo `BAL - Estoques Diversos`, `BAL - Exigível a Longo Prazo` e `BAL - Patrimônio Líquido`) encontram-se vazias (`NaN`) para todos os 1.200 cenários. Coerentemente, a própria aba `KPIs_Cenarios` deixa em branco (`NaN`) os 12 indicadores patrimoniais e de valor econômico (`LC`, `LS`, `LI`, `LG`, `PCT`, `CE`, `IPL`, `Endividamento Geral`, `NOPAT`, `Capital Investido`, `EVA` e `ROIC`) no `Ano 12`, mantendo preenchidos os 7 indicadores da DRE (`Receita`, `Custos variáveis`, `Margem de contribuição`, `EBITDA calculado`, `EBITDA do modelo`, `Margem EBITDA calculada`, `Margem EBITDA do modelo`), além da `DFC_Cenarios` completa.
- **Resolução adotada:**
  - A flag `Balanco_Incompleto` identifica automaticamente registros sem fechamento patrimonial.
  - Os 12 indicadores afetados retornam `NaN` e são apresentados como `N/D` no `Ano 12` (nunca substituídos por zero).
  - As médias multiperíodo seguem a mesma regra comprovada de `Resumo_Cenarios`: média aritmética dos períodos válidos (Anos 1 a 11 para KPIs patrimoniais/EVA).

---

### `AUD-04` — Inversão de Sinal do `Passivo Circulante` (Anos 5–11) e Fórmula do Patrimônio Líquido Implícito
- **Severidade:** Média (Convenção Contábil do Modelo CTI).
- **Evidência observada:**
  1. Nos Anos 1 a 4, `BAL - Passivo Circulante` é negativo (convenção credora), mas nos Anos 5 a 11 passa a apresentar saldo positivo em decorrência de valores positivos na subconta `BAL - Empréstimos`.
  2. Nas fórmulas reais da aba `KPIs_Cenarios` para `PCT`, `IPL` e `Capital Investido`, a parcela referente ao Patrimônio Líquido foi implementada na planilha como `ABS(BAL - Total do Ativo - ABS(PC) - ABS(PNC))` (PL implícito modular), que coincide com `ABS(BAL - Patrimônio Líquido)` nos Anos 1–4, mas diverge nos Anos 5–11 quando `PC > 0`.
- **Resolução adotada:** Para assegurar **100% de reconciliação matemática** com a planilha oficial de validação (`KPIs_Cenarios`, `Resumo_Cenarios` e `KPIs_Estatisticas`), o motor principal (`calc_pct`, `calc_ipl`, `calc_capital_investido`) reproduz exatamente a expressão algébrica da base corporativa original, enquanto disponibiliza colunas paralelas de auditoria (`audit_pct_pl_direto`, `audit_ipl_pl_direto`, `audit_cap_inv_pl_direto`) calculadas com `ABS(BAL - Patrimônio Líquido)`.

---

### `AUD-05` — Separação de EBITDAs, Indisponibilidade de Ticket Médio Real e Premissas Constantes
- **Severidade:** Informativa / Governança Analítica.
- **Evidência observada:**
  1. `DRE - EBITDA` (modelo) difere de `Resultado Operacional + |D&A|` (EBITDA calculado) em todos os períodos.
  2. Não há registros de pedidos, faturas, unidades vendidas ou quantidade de clientes ativos em nenhuma das 9 abas.
  3. `WACC = 12%`, `CAC simulado = R$ 200,00/cliente`, `LTV simulado = R$ 2.100,00/cliente` e `LTV/CAC = 10,50x` são constantes paramétricas invariantes entre os 1.200 cenários.
- **Resolução adotada:**
  - `EBITDA Calculado` e `EBITDA do Modelo` jamais são misturados.
  - `Ticket Médio` observado é reportado como `Indisponível (N/D)` na fonte original, disponibilizando simulador parametrizado claramente rotulado em azul como **Simulação**.

---

## Resultado Final dos Testes de Reconciliação

| Escopo de Validação | Indicadores Verificados | Critério de Aceitação | Resultado Obtido |
| :--- | :---: | :---: | :---: |
| `KPIs_Cenarios` (`14.400` linhas) vs. Recálculo Python | 19 KPIs | Erro relativo máx. `≤ 10⁻⁶` e `0` divergências `N/D` | **19 / 19 Reconciliados (100%)** |
| `Resumo_Cenarios` (`1.200` cenários) vs. Média Anos 1–11 | 19 KPIs | Erro relativo máx. `≤ 10⁻⁶` | **19 / 19 Reconciliados (100%)** |
| `KPIs_Estatisticas` (`N = 1.200`) vs. Motor Estatístico Python | 22 KPIs | Média, DP amostral e Mediana com erro `≤ 10⁻⁶` | **22 / 22 Validados (100%)** |
| Identidade de Caixa DFC (`Saldo Inicial + Geração = Saldo Final = Disponível`) | 14.400 registros | Diferença absoluta `< R$ 0,001` | **100% Reconciliado** |

