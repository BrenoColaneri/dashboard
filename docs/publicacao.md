# Guia de Publicação na Nuvem e Governança de Dados

**CTI Global | Plataforma Analítica de Planejamento Financeiro — Guia de Publicação e Governança**

---

## 1. Política de Segurança e Privacidade da Planilha Original

O arquivo `Contabilidade e Finanças(4).xlsx` / `Contabilidade e Finanças.xlsx` contém dados financeiros confidenciais da **CTI Global**. Por governança:

1. O arquivo `.gitignore` bloqueia o envio de qualquer planilha `.xlsx` bruta e dos caches locais `data/staging/*.parquet` e `data/processed/*.parquet` para repositórios públicos no GitHub.
2. Na nuvem pública, a aplicação **não falha nem inventa uma base falsa silenciosamente**: ao iniciar sem planilha local no servidor, exibe uma tela institucional limpa que permite:
   - **Enviar a planilha oficial `.xlsx` via upload seguro em memória** (`HTTPS`, processada apenas na sessão em `BytesIO`, sem gravação em disco público); ou
   - **Acionar explicitamente o Modo Demonstração Sintética** (claramente identificado com banner vermelho de dados não oficiais).

---

## 2. Passo a Passo para Publicação no Streamlit Community Cloud (Recomendado)

### Pré-requisitos
- Conta no [GitHub](https://github.com/) e no [Streamlit Community Cloud](https://share.streamlit.io/).
- Repositório Git contendo a estrutura deste projeto (`app.py`, `requirements.txt`, `.streamlit/config.toml`, `src/`, `tests/`, `docs/`).

### Etapa 1 — Versionar o Código no GitHub (Verificando o `.gitignore`)
No terminal, na pasta raiz do projeto:

```bash
git init
git status
```

> **Verificação crítica:** Confirme que `Contabilidade e Finanças.xlsx` **não** aparece na lista de arquivos rastreados pelo `git status` (ele é automaticamente ignorado pelo `.gitignore`).

Em seguida, faça o commit e envie para seu repositório no GitHub:

```bash
git add .
git commit -m "feat: plataforma analitica oficial CTI Global"
git branch -M main
git remote add origin https://github.com/<SEU_USUARIO>/<SEU_REPOSITORIO>.git
git push -u origin main
```

### Etapa 2 — Configurar o App no Streamlit Community Cloud
1. Acesse https://share.streamlit.io/ e clique em **Create app** -> **Yup, I have an app**.
2. Preencha os campos:
   - **Repository:** `<SEU_USUARIO>/<SEU_REPOSITORIO>`
   - **Branch:** `main`
   - **Main file path:** `app.py`
3. Em **Advanced settings**:
   - Selecione **Python version: `3.11` ou `3.12`** (totalmente compatíveis com `requirements.txt`).
   - *(Opcional)* Caso o repositório do GitHub seja **privado** (restrito apenas à equipe e aos equipe de controladoria) e você decida incluir `data/raw/Contabilidade e Finanças.xlsx` de forma privada, a aplicação carregará a base automaticamente sem exigir upload manual.
4. Clique em **Deploy!**.

### Etapa 3 — Validação Pós-Deploy
1. Acesse a URL pública gerada (`https://<seu-app>.streamlit.app`).
2. Faça o upload de `Contabilidade e Finanças(4).xlsx` na tela inicial (ou na barra lateral em *Fonte de Dados*) e verifique:
   - Carregamento das 9 abas e 1.200 cenários;
   - Funcionamento dos filtros globais e do botão *Limpar todos os filtros*;
   - Funcionamento do simulador de Sensibilidade, Metas e Regressão OLS;
   - Download dos relatórios em `.CSV`, `.XLSX` e `.PDF`.

---

## 3. Execução Alternativa via Variáveis de Ambiente

Copie `.env.example` para `.env` (ou exporte variáveis no sistema operacional) caso deseje apontar para um diretório externo seguro de dados:

```bash
CTI_EXCEL_PATH=/caminho/seguro/Contabilidade e Finanças(4).xlsx
CTI_DATA_DIR=/caminho/seguro/data
```

