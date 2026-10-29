# Catálogo de Dados e Arquitetura de Camadas (`Raw → Staging → Processed`)

**CTI Global | Plataforma Analítica de Planejamento Financeiro — Catálogo de Dados**

---

## 1. Fonte Primária de Dados (`Raw`)

- **Arquivo oficial corporativo:** `Contabilidade e Finanças.xlsx` / `Contabilidade e Finanças(4).xlsx`
- **Política de preservação:** O arquivo original é tratado estritamente em modo **somente leitura (read-only)**. Nenhuma célula, fórmula, aba ou formatação da planilha original é sobrescrita ou alterada pela aplicação.
- **Proteção de versionamento:** Arquivos `.xlsx` brutos e artefatos derivados em `data/raw/`, `data/staging/` e `data/processed/` estão protegidos no `.gitignore` para impedir exposição pública acidental de dados da empresa parceira (CTI).

---

## 2. Inventário Auditado das 9 Abas da Planilha Original

| # | Aba | Granularidade | Chave Primária | Dimensão Observada | Descrição e Papel Analítico |
| :-: | :--- | :--- | :--- | :---: | :--- |
| 1 | `Balanco_Cenarios` | `Cenário × Ano` | `(Cenário, Ano)` | `14.400 × 45` | Contas patrimoniais de Ativo, Passivo Circulante, Exigível a Longo Prazo e Patrimônio Líquido para 1.200 cenários (`Cen_00001` a `Cen_01200`) nos períodos `1` a `12`. **Nota:** No `Ano 12`, 27 contas patrimoniais estão ausentes (`NaN`). |
| 2 | `DRE_Cenarios` | `Cenário × Ano` | `(Cenário, Ano)` | `14.400 × 16` | Demonstração do Resultado do Exercício completa nos Anos `1` a `12` (`100%` preenchida), contendo Receita, Tributos, Custos, D&A, Resultado Operacional, Resultado Financeiro, Outros Resultados Operacionais, LAIR, IR/CSLL, Resultado Líquido e `DRE - EBITDA`. |
| 3 | `DFC_Cenarios` | `Cenário × Ano` | `(Cenário, Ano)` | `14.400 × 14` | Demonstração do Fluxo de Caixa completa nos Anos `1` a `12`, iniciando em `FLU - Saldo Inicial`, fluxos operacionais, investimentos, resultado financeiro, IR/CSLL, distribuição a acionistas, `FLU - Geração de Caixa` e `FLU - Saldo Final`. |
| 4 | `KPIs_Cenarios` | `Cenário × Ano` | `(Cenário, Ano)` | `14.400 × 24` | 19 indicadores financeiros calculados por cenário e período + metadado lateral `WACC = 0,12` (`12%`). Os 12 indicadores dependentes do Balanço/EVA apresentam `NaN` no `Ano 12`. |
| 5 | `KPIs_Estatisticas` | `Indicador` | `KPI / Indicador` | `22 × 14` | Estatísticas descritivas consolidadas (`N = 1.200`, Média, Mínimo, Máximo, Desvio Padrão amostral e percentis `P5` a `P95`) calculadas sobre `Resumo_Cenarios`. |
| 6 | `Dicionario_KPIs` | `Indicador` | `KPI / Indicador` | `22 × 12` | Referência conceitual com categoria, descrição, fórmula aplicada, unidade, nível de cálculo, interpretação, premissas, fonte, periodicidade e regras de validação. |
| 7 | `Resumo_Cenarios` | `Cenário` | `Cenário` | `1.200 × 26` | Consolidação de cada cenário pela **média aritmética dos Anos 1 a 11**, acrescida de `Score baixo risco` e das premissas constantes `CAC simulado` (`R$ 200`), `LTV simulado` (`R$ 2.100`) e `LTV/CAC` (`10,50x`). |
| 8 | `Ranking_Cenarios` | `Cenário` | `Cenário` | `1.200 × 12` | Classificação geral (`Posição` `1` a `1.200`) ordenada de forma decrescente pela `Margem EBITDA` do modelo. |
| 9 | `Top10_Rankings` | `Categoria × Posição` | `(Categoria, Posição)` | `50 × 5` | Top 10 cenários em 5 recortes: `ALTA RENTABILIDADE`, `ALTA LIQUIDEZ`, `BAIXA LIQUIDEZ`, `RETORNO MODERADO` e `BAIXO RISCO`. |

---

## 3. Convenções Contábeis, Temporais e de Sinais na Base

1. **Períodos Numerados (`Ano 1` a `Ano 12`):** Os valores `1` a `12` do campo `Ano` representam períodos sequenciais numerados do modelo financeiro. Em conformidade com as regras de governança, o sistema formata-os exclusivamente como `Ano 1` a `Ano 12`, sem convertê-los em anos civis (`2024`, `2025`, etc.).
2. **Sinais na DRE (`DRE_Cenarios`):** Deduções, tributos sobre vendas, custos operacionais, depreciação/amortização, despesas financeiras e IR/CSLL possuem **sinal negativo**. Assim, a Receita Líquida proxy é obtida por `ABS(DRE - Receita) + DRE - Tributos`.
3. **Sinais no Balanço (`Balanco_Cenarios`):** Contas credoras de Passivo e Patrimônio Líquido são originalmente negativas nos Anos 1–4; nos Anos 5–11, `BAL - Passivo Circulante` assume sinal positivo em função da conta `BAL - Empréstimos`. Por isso, todas as fórmulas patrimoniais aplicam `ABS()` conforme documentação metodológica corporativa.
4. **Higienização Não Destrutiva de Cabeçalhos:** Espaços duplos ou finais presentes nos cabeçalhos originais (como `'BAL  - Patrimônio Líquido'` e `'LC '`) são normalizados para espaço simples (`'BAL - Patrimônio Líquido'`, `'LC'`) na camada `Staging → Processed`.

---

## 4. Fluxo das Três Camadas de Engenharia de Dados

1. **`data/raw/` (Camada Bruta):** Recebe ou referencia o arquivo Excel original intacto.
2. **`data/staging/` (Camada de Preparação e Cache Auditável):**
   - Implementada em `src/data_loader.py`.
   - Ao abrir o arquivo Excel, calcula uma assinatura criptográfica parcial SHA-256 (`fingerprint`) baseada no nome, tamanho em bytes, timestamp de modificação e blocos inicial/final de 1 MB.
   - Materializa arquivos Parquet tipados (`staging_<Aba>.parquet`) acompanhados de `staging_manifest.json`. Se o arquivo Excel original for substituído ou atualizado, a assinatura muda e o cache é reconstruído automaticamente.
3. **`data/processed/` (Camada Analítica):**
   - Implementada em `src/data_processing.py` e `src/financial_kpis.py`.
   - Mantém duas estruturas separadas para **impedir duplicação de granularidade**:
     - `panel_cenario_ano.parquet` (`14.400` linhas — granularidade `Cenário × Ano`, integrando DRE, Balanço, DFC, KPIs originais, flag `Balanco_Incompleto` e colunas auditáveis `calc_*` e `kpi_*`).
     - `resumo_cenarios.parquet` (`1.200` linhas — granularidade `Cenário`, consolidada sobre os Anos 1 a 11).
   - Registra metadados completos de linhagem em `processed_manifest.json`.

