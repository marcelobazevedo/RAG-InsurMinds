import os
from pathlib import Path
from typing import List, Dict
from urllib.parse import quote

import psycopg2
import streamlit as st

from rag.graph.rag_graph import run_streaming_rag
from rag.graph.model_provider import embed_text
from rag.ingest.extract_text import process_pdf_file
from rag.ingest.pgvector_store import PgVectorStore


st.set_page_config(
    page_title="RAG-InsurMinds",
)

st.markdown(
    """
    <style>
    section[data-testid="stSidebar"] .kb-card {
        border: 1px solid #d9dee7;
        border-radius: 10px;
        padding: 12px 12px 8px 12px;
        background: #ffffff;
        margin-bottom: 10px;
    }
    section[data-testid="stSidebar"] .kb-title {
        font-size: 1rem;
        font-weight: 600;
        color: #1f2937;
        margin: 0 0 6px 0;
    }
    section[data-testid="stSidebar"] .kb-subtitle {
        font-size: 0.84rem;
        line-height: 1.35;
        color: #6b7280;
        margin: 0 0 10px 0;
    }
    section[data-testid="stSidebar"] .kb-upload-label {
        font-size: 0.8rem;
        font-weight: 600;
        color: #374151;
        margin: 0 0 8px 0;
    }
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
        border: 1px solid #d7deeb;
        border-radius: 8px;
        background: #f7f9fc;
        min-height: 112px;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 10px 8px;
        transition: border-color .15s ease, background-color .15s ease;
    }
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"]:hover {
        border-color: #c6d1e5;
        background: #f3f6fb;
    }
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] > div {
        text-align: center;
        width: 100%;
    }
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"] {
        margin-top: 4px;
    }
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"] > div,
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"] > small,
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"] span {
        color: transparent !important;
        font-size: 0 !important;
        line-height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"]::after {
        content: "Arraste e solte arquivos aqui\\Aou clique para selecionar";
        white-space: pre-line;
        display: block;
        text-align: center;
        font-size: 13px;
        font-weight: 500;
        color: #1f2937;
        line-height: 1.55;
        margin-top: 2px;
    }
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"]::first-line {
        font-weight: 500;
        color: #1f2937;
    }
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] svg {
        width: 22px;
        height: 22px;
        color: #9aa4b5;
    }
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] small {
        font-size: 13px !important;
        font-weight: 400;
        color: #6b7280 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("ChatBOT RAG")
st.write(
    "Faça uma pergunta em linguagem natural sobre seguro residencial."
)

_DOCUMENTS_DIR = Path("documentos")
_MAX_UPLOAD_BYTES = 50 * 1024 * 1024
_DEFAULT_RETRIEVAL_MODE = "hybrid"
_DEFAULT_TOP_K = 5


def _source_label(source: Dict) -> str:
    titulo = (source.get("titulo") or "").strip()
    numero = (source.get("numero_documento") or "").strip()
    tipo = (source.get("tipo") or "").strip()

    if titulo and numero:
        return f"{titulo} n.º {numero}"
    if titulo:
        return titulo
    if numero:
        return numero
    return source.get("pdf_name") or "Documento"


def _render_sources(sources: List[Dict]) -> None:
    unique_sources = []
    seen_pdf_names = set()
    for source in sources:
        pdf_name = source.get("pdf_name")
        if not pdf_name or pdf_name in seen_pdf_names:
            continue
        seen_pdf_names.add(pdf_name)
        unique_sources.append(source)

    if not unique_sources:
        return

    st.markdown("**Fontes consultadas:**")
    lines = []
    for source in unique_sources:
        pdf_name = source["pdf_name"]
        pdf_href = f"/app/static/{quote(pdf_name)}"
        label = _source_label(source)
        lines.append(f"- {label} ([{pdf_name}]({pdf_href})).")

    st.markdown("\n".join(lines))


def _save_uploaded_pdf(uploaded_file) -> tuple[bool, str]:
    _DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = Path(uploaded_file.name).name
    if not safe_name.lower().endswith(".pdf"):
        return False, "Arquivo rejeitado: envie somente PDF (.pdf)."
    if uploaded_file.size is not None and uploaded_file.size > _MAX_UPLOAD_BYTES:
        return False, "Arquivo rejeitado: tamanho máximo permitido é 50 MB."

    target_path = _DOCUMENTS_DIR / safe_name
    if target_path.exists():
        return False, f"Arquivo rejeitado: já existe um PDF com este nome ({safe_name})."
    target_path.write_bytes(uploaded_file.getbuffer())
    return True, f"PDF salvo em: {target_path}"


def _ingest_pdf_to_database(pdf_path: Path) -> tuple[bool, str]:
    vector_store = PgVectorStore()
    try:
        vector_store.create_table()
        chunks = process_pdf_file(str(pdf_path))
        if not chunks:
            return False, "PDF salvo, mas não foi possível extrair texto para ingestão."

        texts = [chunk["text"] for chunk in chunks]
        metadatas = [chunk["metadata"] for chunk in chunks]
        embeddings = [embed_text(text) for text in texts]
        vector_store.add_texts(texts=texts, metadatas=metadatas, embeddings=embeddings)
        return True, f"Ingestão concluída: {len(chunks)} chunk(s) indexado(s)."
    except Exception as exc:
        return False, f"PDF salvo, mas falhou ao ingerir no banco: {exc}"
    finally:
        vector_store.close()


def _remove_all_uploaded_pdfs() -> tuple[bool, str]:
    if not _DOCUMENTS_DIR.exists():
        return True, "Nenhum arquivo para remover."

    removed = 0
    for file_path in _DOCUMENTS_DIR.glob("*.pdf"):
        if file_path.is_file():
            file_path.unlink()
            removed += 1

    if removed == 0:
        return True, "Nenhum arquivo PDF para remover."
    return True, f"{removed} arquivo(s) removido(s) com sucesso."


def _truncate_dados_table() -> tuple[bool, str]:
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            dbname=os.getenv("POSTGRES_DB"),
        )
        cur = conn.cursor()
        cur.execute("TRUNCATE TABLE dados RESTART IDENTITY;")
        conn.commit()
        return True, "Tabela 'dados' limpa com sucesso."
    except Exception as exc:
        return False, f"Falha ao limpar a tabela 'dados': {exc}"
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()


def _clear_documents_and_database() -> tuple[bool, str]:
    files_ok, files_msg = _remove_all_uploaded_pdfs()
    db_ok, db_msg = _truncate_dados_table()
    ok = files_ok and db_ok
    return ok, f"{files_msg} {db_msg}"


with st.sidebar:
    st.markdown(
        """
        <div class="kb-card">
            <p class="kb-title">Base de Conhecimento</p>
            <p class="kb-subtitle">Faça upload de documentos para que o sistema possa responder perguntas com base no seu conteúdo.</p>
            <p class="kb-upload-label">Upload de arquivos</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    uploaded_pdf = st.file_uploader(
        "Arraste e solte aqui ou clique para selecionar",
        type=["pdf"],
        accept_multiple_files=False,
        label_visibility="collapsed",
        help="Somente PDF, tamanho máximo 50 MB e sem nome duplicado.",
    )
    if uploaded_pdf is not None:
        saved_ok, saved_msg = _save_uploaded_pdf(uploaded_pdf)
        if saved_ok:
            st.success(saved_msg)
            pdf_path = _DOCUMENTS_DIR / Path(uploaded_pdf.name).name
            with st.spinner("Processando PDF e salvando no banco..."):
                ingest_ok, ingest_msg = _ingest_pdf_to_database(pdf_path)
            if ingest_ok:
                st.success(ingest_msg)
            else:
                st.error(ingest_msg)
        else:
            st.error(saved_msg)

    if st.button("🗑️  Remover todos os arquivos", use_container_width=True):
        ok, message = _clear_documents_and_database()
        if ok:
            st.success(message)
        else:
            st.error(message)

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ex: O que é um seguro residencial?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        details_expander = st.expander("🔎 **Detalhes da Busca (Chunks Recuperados)**")
        query_placeholder = details_expander.empty()
        filter_placeholder = details_expander.empty()
        chunks_placeholder = details_expander.empty()
        answer_placeholder = st.empty()
        sources_placeholder = st.empty()

        full_answer = ""
        sources: List[Dict] = []

        for event in run_streaming_rag(
            prompt,
            retrieval_mode=_DEFAULT_RETRIEVAL_MODE,
            top_k=_DEFAULT_TOP_K,
        ):
            if event["type"] == "details":
                data = event["data"]
                query_placeholder.markdown(f"**Busca Semântica:** `{data['query']}`")
                filter_placeholder.markdown(f"**Query Expansion:** `{data['filter']}`")
                chunks_placeholder.markdown(
                    f"**Modo:** `{data['mode']}` | **Top-k:** `{data['top_k']}`"
                )
            elif event["type"] == "token":
                token = event["data"]
                full_answer += token
                answer_placeholder.markdown(full_answer + "▌")
            elif event["type"] == "sources":
                answer_placeholder.markdown(full_answer)
                payload = event["data"]
                sources = payload.get("sources", [])
                with sources_placeholder.container():
                    _render_sources(sources)

        st.session_state.messages.append({"role": "assistant", "content": full_answer})
