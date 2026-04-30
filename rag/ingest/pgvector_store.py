import os

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values, Json


class PgVectorStore:
    def __init__(self):
        load_dotenv()
        self.vector_dim = int(os.getenv("PGVECTOR_DIM", "768"))
        self.conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST"),
            port=int(os.getenv("POSTGRES_PORT", 5432)),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            dbname=os.getenv("POSTGRES_DB"),
        )
        self.cur = self.conn.cursor()

    def create_table(self):
        self.cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS dados (
                id SERIAL PRIMARY KEY,
                chunk_id TEXT UNIQUE,
                doc_id TEXT,
                titulo TEXT,
                fonte TEXT,
                data TEXT,
                tipo TEXT,
                text TEXT,
                metadata JSONB,
                embedding VECTOR({self.vector_dim})
            );
        """
        )
        self.conn.commit()

    def add_texts(self, texts, metadatas, embeddings):
        import json

        def _strip_nul(value):
            if isinstance(value, str):
                return value.replace("\x00", "")
            if isinstance(value, dict):
                return {k: _strip_nul(v) for k, v in value.items()}
            if isinstance(value, list):
                return [_strip_nul(v) for v in value]
            if isinstance(value, tuple):
                return tuple(_strip_nul(v) for v in value)
            return value

        if not texts:
            return

        data = []
        for text, meta, emb in zip(texts, metadatas, embeddings):
            if emb is None or len(emb) != self.vector_dim:
                got = 0 if emb is None else len(emb)
                raise RuntimeError(
                    f"Dimensao de embedding invalida: esperado {self.vector_dim}, recebido {got}. "
                    "Ajuste PGVECTOR_DIM/.env e o modelo de embedding para a mesma dimensao antes da ingestao."
                )
            if isinstance(meta, str):
                try:
                    meta_dict = json.loads(meta)
                except Exception:
                    meta_dict = {}
            else:
                meta_dict = meta if isinstance(meta, dict) else {}
            clean_text = _strip_nul(text)
            clean_meta = _strip_nul(meta_dict)

            doc_id = clean_meta.get("doc_id") or clean_meta.get("pdf_name") or "doc_desconhecido"
            meta_chunk_id = clean_meta.get("chunk_id") or f"chunk_{clean_meta.get('chunk_index', '')}"
            chunk_id = f"{doc_id}::{meta_chunk_id}"
            titulo = clean_meta.get("titulo") or clean_meta.get("pdf_name") or "Sem título"
            fonte = clean_meta.get("fonte") or f"Arquivo local: {clean_meta.get('pdf_name', 'desconhecido')}"
            data_field = clean_meta.get("data") or clean_meta.get("data_status") or ""
            tipo = clean_meta.get("tipo") or clean_meta.get("chunk_type") or "texto"
            data.append((chunk_id, doc_id, titulo, fonte, data_field, tipo, clean_text, Json(clean_meta), emb))

        execute_values(
            self.cur,
            (
                "INSERT INTO dados (chunk_id, doc_id, titulo, fonte, data, tipo, text, metadata, embedding) "
                "VALUES %s ON CONFLICT (chunk_id) DO NOTHING"
            ),
            data,
        )
        self.conn.commit()

    def close(self):
        self.cur.close()
        self.conn.close()
