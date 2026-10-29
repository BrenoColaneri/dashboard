# Limitações Conhecidas, Riscos Analíticos e Ressalvas Metodológicas

**CTI Global | Plataforma Analítica de Planejamento Financeiro — Limitações e Ressalvas**

A transparência sobre o que os dados permitem — e o que **não** permitem — concluir é requisito central de governança analítica. Abaixo estão documentadas todas as limitações identificadas no projeto.

---

## 1. Limitações da Fonte de Dados e Escopo Contábil

1. **Incompletude Patrimonial no `Ano 12`:** A aba `Balanco_Cenarios` não apresenta fechamento completo no `Ano 12` (27 contas ausentes, incluindo Exigível a Longo Prazo e Patrimônio Líquido). Consequentemente, nenhum indicador de Liquidez, Endividamento, Capital Investido, NOPAT, ROIC ou EVA pode ser calculado de forma confiável no `Ano 12`, sendo exibido como `N/D`.
2. **Ausência de Segregação entre Custos Fixos e Variáveis:** A DRE da CTI Global reporta apenas a rubrica agregada `DRE - Custos`. A adoção de `ABS(DRE - Custos)` como `Custos Variáveis (Proxy)` segue a premissa documentada no modelo de referência corporativo, mas pode subestimar a alavancagem operacional caso parcela relevante desses custos seja fixa. Para mitigar essa limitação em simulações, o módulo de **Sensibilidade Financeira** permite parametrizar o percentual variável dos custos (`0%` a `100%`).
3. **Ausência de Dados Transacionais Comerciais (Ticket Médio, Volume Físico e Clientes):** Não existem colunas de quantidade vendida, número de pedidos/contratos ou base ativa de clientes. Portanto:
   - O **Ticket Médio real** é reportado como **Indisponível (`N/D`)**.
   - A variação da Receita entre períodos ou cenários não pode ser decomposta empiricamente entre efeito-preço e efeito-volume sem premissas adicionais.
   - Os valores de `CAC (R$ 200,00/cliente)`, `LTV (R$ 2.100,00/cliente)` e `LTV/CAC (10,50x)` são premissas simuladas constantes.
4. **Períodos Numerados sem Calendário Civil Oficial:** Os períodos `Ano 1` a `Ano 12` não possuem mapeamento documental para anos civis específicos e são mantidos estritamente como períodos numerados do modelo.
5. **Ausência de Metas Corporativas Oficiais na Planilha:** A base original não traz metas orçamentárias oficiais. O sistema não inventa metas padrão e exibe-as como `Não definida` até que o analista configure seus próprios alvos na sessão.

---

## 2. Limitações Contábeis e de Modelagem Financeira

1. **Diferença Estrutural entre `EBITDA Calculado` e `EBITDA do Modelo`:** O campo nativo `DRE - EBITDA` inclui ajustes internos da modelagem CTI (com salto expressivo no `Ano 12` associado a `Outros Resultados Operacionais`) que não compõem a fórmula contábil padrão `Resultado Operacional + |D&A|`. Ambos são exibidos separadamente para evitar distorções de interpretação.
2. **Sensibilidade do EVA à Premissa Fixa de WACC (`12%`):** Na base original, o custo médio ponderado de capital é fixado em `12,00% a.a.` para todos os cenários e períodos. Em condições reais de mercado, cenários com maior alavancagem financeira (`PCT` elevado) tenderiam a enfrentar maior custo de capital.
3. **Outliers em `PCT` e `IPL`:** Quando a soma modular de passivos (`|PC| + |PNC|`) aproxima-se numericamente do `Ativo Total`, o denominador `ABS(Ativo Total - |PC| - |PNC|)` aproxima-se de zero, gerando múltiplos extremos em cenários pontuais. Por essa razão, análises comparativas priorizam simultaneamente a **mediana (`P50`)** e o **intervalo interquartílico (`IQR`)** ao lado da média aritmética.

---

## 3. Limitações Estatísticas e Econométricas (Regressão OLS)

1. **Correlação e Regressão Não Implicam Causalidade:** Como os 1.200 cenários derivam de um modelo paramétrico de simulação corporativa da CTI, associações estatísticas fortes refletem a estrutura conjunta dos cenários simulados, e não experimentos causais controlados.
2. **Assimetria e Caudas Pesadas:** Diversos indicadores financeiros (especialmente múltiplos de alavancagem e liquidez) rejeitam normalidade estrita nos testes de Shapiro-Wilk e Jarque-Bera. Para garantir inferência válida, o módulo OLS aplica **erros-padrão robustos** (`HC3` no nível de cenário e clusterizados por `Cenário` no painel) e complementa correlações de Pearson com correlações por postos de Spearman.
3. **Risco de Tautologia Contábil:** Regredir um indicador diretamente sobre os componentes exatos de sua própria fórmula (ex.: `EVA` contra `NOPAT` e `Capital Investido`) produz ajuste artificialmente próximo de `1,0`. O sistema possui detector automático (`detect_algebraic_leakage`) que emite alerta explícito ao usuário nesses casos.

