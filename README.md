# RAG-InsurMinds

Aplicação RAG para seguro residencial com:
- interface em Streamlit;
- upload de PDFs;
- ingestão automática para PostgreSQL + pgvector;
- recuperação `dense`, `sparse` e `hybrid`.

## Requisitos

- Python `3.12`
- `uv` instalado
- Docker + Docker Compose (para execução em containers)
- Ollama (se `MODELO_LOCAL=true`) **ou** credenciais OpenAI (se `MODELO_LOCAL=false`)

## Estrutura rápida

```text
RAG-InsurMinds/
├── app.py
├── docker-compose.yaml
├── Dockerfile
├── .env
├── .env_sample
├── documentos/                  # PDFs enviados/ingeridos
├── initdb/
├── rag/
│   ├── ingest/
│   │   ├── extract_text.py
│   │   ├── truncate_data.py
│   │   └── reset_project_state.py
│   ├── retrieval/
│   └── graph/
```

## Configuração de ambiente

1. Copie o arquivo de exemplo:

```bash
cp .env_sample .env
```

2. Ajuste `.env` conforme seu modo de execução.

### Principais variáveis

- `MODELO_LOCAL=true|false`
- `LLM_MODEL` e `EMBEDDING_MODEL` (modo local)
- `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_EMBEDDING_MODEL` (modo OpenAI)
- `PGVECTOR_DIM` (deve bater com dimensão do embedding)
- `POSTGRES_*` (conexão de banco)
- `CHUNK_SIZE` e `CHUNK_OVERLAP` (ingestão)

## Como configurar os modelos (passo a passo)

Toda configuração de modelo fica no arquivo [`.env`](/home/marcelo/Development/RAG-InsurMinds/.env).

### Opção A: usar modelo local (Ollama)

Use quando quiser rodar sem OpenAI:

```env
MODELO_LOCAL=true
LLM_MODEL=ministral-3:14b
EMBEDDING_MODEL=nomic-embed-text:latest
OLLAMA_URL=http://host.docker.internal:11434
```

Neste modo, `OPENAI_API_KEY` pode ficar vazio.

### Opção B: usar OpenAI (ChatGPT API)

Use quando quiser rodar com modelos OpenAI:

```env
MODELO_LOCAL=false
OPENAI_API_KEY=cole_sua_chave_aqui
OPENAI_MODEL=gpt-4.1-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-large
```

Ponto mais importante: a chave deve ser colocada em [`.env`](/home/marcelo/Development/RAG-InsurMinds/.env), no campo:

```env
OPENAI_API_KEY=...
```

Sem essa chave (e com `MODELO_LOCAL=false`), a aplicação não consegue chamar a API da OpenAI.

## Uso com Docker (recomendado)

### Subir containers

```bash
docker compose up -d --build
```

### Ver status

```bash
docker compose ps
```

### Acessar app

- URL: `http://localhost:8501`

### Containers criados

- `rag_insurminds_postgres`
- `rag_insurminds_streamlit`

## Uso com uv (host/local)

### Instalar dependências

```bash
uv sync
```

### Rodar app local

```bash
uv run streamlit run app.py
```

## Fluxo de upload e ingestão

No app, pela sidebar:

1. Envie um PDF (somente `.pdf`, até 50 MB, sem nome duplicado).
2. O sistema salva em `documentos/`.
3. A ingestão é executada automaticamente (equivalente à lógica de `rag.ingest.extract_text`).
4. Os chunks e embeddings são gravados na tabela `dados`.

## Ingestão manual (opcional)

### Rodando dentro do container

```bash
docker compose exec streamlit uv run --no-sync python -m rag.ingest.extract_text
```

### Rodando no host

```bash
uv run python -m rag.ingest.extract_text
```

## Limpeza de arquivos e base

No app existe o botão **Remover todos os arquivos**, que:

- remove todos os PDFs de `documentos/`;
- executa `TRUNCATE TABLE dados RESTART IDENTITY`.

## Comandos úteis de operação

### Logs

```bash
docker compose logs -f streamlit
docker compose logs -f postgres
```

### Reiniciar containers

```bash
docker compose down
docker compose up -d --build
```

### Recriar sem rebuild de imagem

```bash
docker compose up -d --force-recreate
```

## Troubleshooting

### `connection refused` no PostgreSQL

- Verifique containers: `docker compose ps`
- Se rodar no host, ajuste `.env` para porta publicada no compose (`54321`):
  - `POSTGRES_HOST=localhost`
  - `POSTGRES_PORT=54321`

### App sobe, mas não responde bem

- Confirme modelos no `.env`.
- Em modo local, valide se Ollama está acessível em `OLLAMA_URL`.

### Upload não aparece na pasta local

- Verifique bind mount no `docker-compose.yaml`:
  - `./documentos:/app/documentos`
