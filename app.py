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
    section[data-testid="stSidebar"] {
        width: 320px !important;
        min-width: 320px !important;
    }
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
    section[data-testid="stSidebar"] [data-testid="stFileUploaderFile"] {
        display: none !important;
    }
    section[data-testid="stSidebar"] [data-testid="stFileUploaderPagination"] {
        display: none !important;
    }
    section[data-testid="stSidebar"] [data-testid="stFileUploader"] > div:nth-child(3) {
        display: none !important;
    }
    section[data-testid="stSidebar"] [data-testid="stFileUploader"] input[type="text"] {
        display: none !important;
        height: 0 !important;
        min-height: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
        border: 0 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stFileUploader"] input[type="file"] {
        opacity: 0 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stFileUploader"] [data-baseweb="input"] {
        display: none !important;
    }
    section[data-testid="stSidebar"] [data-testid="stFileUploader"] [role="textbox"] {
        display: none !important;
    }
    section[data-testid="stSidebar"] [data-testid="stFileUploader"] .st-emotion-cache-1h9usn1 {
        display: none !important;
    }
    section[data-testid="stSidebar"] .saved-files-box {
        border: 1px solid #d2d9e5;
        border-radius: 8px;
        background: #edf1f6;
        padding: 8px;
        margin-top: 8px;
        margin-bottom: 10px;
    }
    section[data-testid="stSidebar"] .saved-file-text {
        line-height: 1.15;
        margin-top: 2px;
    }
    section[data-testid="stSidebar"] .saved-file-name {
        font-size: 15px;
        color: #2d3442;
        font-weight: 500;
    }
    section[data-testid="stSidebar"] .saved-file-size {
        font-size: 12px;
        color: #8a94a6;
        margin-top: 4px;
    }
    section[data-testid="stSidebar"] .saved-file-icon {
        width: 34px;
        height: 34px;
        border-radius: 8px;
        background: #2f3647;
        color: #d7deeb;
        font-size: 18px;
        font-weight: 600;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-top: 2px;
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
_MAX_FILES_PER_BATCH = 20
_DEFAULT_RETRIEVAL_MODE = "hybrid"
_DEFAULT_TOP_K = 5

if "uploader_nonce" not in st.session_state:
    st.session_state["uploader_nonce"] = 0
if "is_processing_uploads" not in st.session_state:
    st.session_state["is_processing_uploads"] = False
if "last_upload_feedback" not in st.session_state:
    st.session_state["last_upload_feedback"] = None
if "last_uploader_selected_names" not in st.session_state:
    st.session_state["last_uploader_selected_names"] = []


def _upload_signature(uploaded_files) -> str:
    parts = []
    for f in uploaded_files or []:
        parts.append(f"{Path(f.name).name}:{getattr(f, 'size', 0)}")
    return "|".join(sorted(parts))


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


def _save_uploaded_pdf(uploaded_file) -> tuple[str, str]:
    _DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = Path(uploaded_file.name).name
    if not safe_name.lower().endswith(".pdf"):
        return "error", "Arquivo rejeitado: envie somente PDF (.pdf)."
    if uploaded_file.size is not None and uploaded_file.size > _MAX_UPLOAD_BYTES:
        return "error", "Arquivo rejeitado: tamanho máximo permitido é 50 MB."

    target_path = _DOCUMENTS_DIR / safe_name
    if target_path.exists():
        return "duplicate", f"Arquivo já existente (ignorado): {safe_name}."
    target_path.write_bytes(uploaded_file.getbuffer())
    return "saved", f"PDF salvo em: {target_path}"


def _prepare_batch_upload(uploaded_files) -> tuple[List[Path], List[str], List[str], List[str]]:
    _DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    saved_paths: List[Path] = []
    saved_msgs: List[str] = []
    rejected_msgs: List[str] = []
    duplicate_msgs: List[str] = []

    for uploaded_file in uploaded_files:
        status, msg = _save_uploaded_pdf(uploaded_file)
        if status == "saved":
            safe_name = Path(uploaded_file.name).name
            saved_paths.append(_DOCUMENTS_DIR / safe_name)
            saved_msgs.append(msg)
        elif status == "duplicate":
            duplicate_msgs.append(f"{uploaded_file.name}: {msg}")
        else:
            rejected_msgs.append(f"{uploaded_file.name}: {msg}")

    return saved_paths, saved_msgs, rejected_msgs, duplicate_msgs


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


def _remove_single_pdf(file_name: str) -> tuple[bool, str]:
    target_path = _DOCUMENTS_DIR / file_name
    if not target_path.exists():
        return True, f"Arquivo já não existia em documentos/: {file_name}"
    try:
        target_path.unlink()
        return True, f"Arquivo removido: {file_name}"
    except Exception as exc:
        return False, f"Falha ao remover arquivo {file_name}: {exc}"


def _delete_pdf_rows_from_database(file_name: str) -> tuple[bool, str]:
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
        cur.execute("DELETE FROM dados WHERE metadata ->> 'pdf_name' = %s", (file_name,))
        removed_rows = cur.rowcount
        conn.commit()
        return True, f"Registros removidos da base para {file_name}: {removed_rows}"
    except Exception as exc:
        return False, f"Falha ao remover registros do banco para {file_name}: {exc}"
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()


def _clear_single_document(file_name: str) -> tuple[bool, str]:
    file_ok, file_msg = _remove_single_pdf(file_name)
    db_ok, db_msg = _delete_pdf_rows_from_database(file_name)
    ok = file_ok and db_ok
    return ok, f"{file_msg} {db_msg}"


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


def _list_saved_pdfs() -> List[str]:
    if not _DOCUMENTS_DIR.exists():
        return []
    return sorted([p.name for p in _DOCUMENTS_DIR.glob("*.pdf") if p.is_file()], key=str.lower)


def _human_file_size(size_bytes: int) -> str:
    if size_bytes < 1024 * 1024:
        return f"{max(1, size_bytes // 1024)}KB"
    return f"{size_bytes / (1024 * 1024):.1f}MB"


def _truncate_filename(name: str, max_len: int = 26) -> str:
    if len(name) <= max_len:
        return name
    left = 10
    right = 12
    return f"{name[:left]}...{name[-right:]}"


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
    uploaded_pdfs = st.file_uploader(
        "Arraste e solte aqui ou clique para selecionar",
        type=["pdf"],
        accept_multiple_files=True,
        key=f"pdf_batch_uploader_{st.session_state['uploader_nonce']}",
        label_visibility="collapsed",
        help=(
            "Somente PDF, tamanho máximo 50 MB por arquivo, "
            f"sem nome duplicado e até {_MAX_FILES_PER_BATCH} arquivos por envio."
        ),
    )
    selected_names = [Path(f.name).name for f in (uploaded_pdfs or [])]
    st.session_state["last_uploader_selected_names"] = selected_names
    feedback = st.session_state.get("last_upload_feedback")
    if feedback:
        if feedback.get("saved"):
            st.success(
                f"{feedback['saved']} arquivo(s) salvo(s) em documentos/. "
                f"Ingestão concluída para {feedback['ingested_ok']} arquivo(s). "
                f"Total aproximado de chunks indexados: {feedback['total_chunks']}."
            )
        if feedback.get("rejected_msgs"):
            st.warning(
                "Alguns arquivos foram rejeitados:\n- "
                + "\n- ".join(feedback["rejected_msgs"])
            )
        if feedback.get("duplicate_count"):
            st.info(
                f"{feedback['duplicate_count']} arquivo(s) já existiam e foram ignorados."
            )
        if feedback.get("ingest_err_msgs"):
            st.error(
                "Falha de ingestão em alguns arquivos:\n- "
                + "\n- ".join(feedback["ingest_err_msgs"])
            )
        st.session_state["last_upload_feedback"] = None

    if uploaded_pdfs:
        batch_signature = _upload_signature(uploaded_pdfs)
        if st.session_state.get("last_processed_upload_signature") == batch_signature:
            uploaded_pdfs = []
        else:
            st.session_state["last_processed_upload_signature"] = batch_signature

    if uploaded_pdfs:
        if len(uploaded_pdfs) > _MAX_FILES_PER_BATCH:
            st.error(
                f"Lote rejeitado: envie no máximo {_MAX_FILES_PER_BATCH} arquivos por vez. "
                f"Recebidos: {len(uploaded_pdfs)}."
            )
        else:
            saved_paths, saved_msgs, rejected_msgs, duplicate_msgs = _prepare_batch_upload(uploaded_pdfs)

            if saved_msgs:
                st.success(
                    f"{len(saved_msgs)} arquivo(s) salvo(s) em documentos/. "
                    "Iniciando ingestão..."
                )
            if rejected_msgs:
                st.warning(
                    "Alguns arquivos foram rejeitados:\n- "
                    + "\n- ".join(rejected_msgs)
                )
            if duplicate_msgs:
                st.info(
                    "Arquivos já existentes foram ignorados:\n- "
                    + "\n- ".join(duplicate_msgs)
                )

            if saved_paths:
                st.session_state["is_processing_uploads"] = True
                progress = st.progress(0.0, text="Ingestão em andamento...")
                ingest_ok_msgs: List[str] = []
                ingest_err_msgs: List[str] = []
                total_chunks = 0
                total_files = len(saved_paths)
                try:
                    for idx, pdf_path in enumerate(saved_paths, start=1):
                        progress.progress(
                            idx / total_files,
                            text=f"Ingerindo {idx}/{total_files}: {pdf_path.name}",
                        )
                        ok, msg = _ingest_pdf_to_database(pdf_path)
                        if ok:
                            ingest_ok_msgs.append(f"{pdf_path.name}: {msg}")
                            try:
                                total_chunks += int(msg.split(":")[1].split("chunk")[0].strip())
                            except Exception:
                                pass
                        else:
                            ingest_err_msgs.append(f"{pdf_path.name}: {msg}")
                finally:
                    st.session_state["is_processing_uploads"] = False

                progress.progress(1.0, text="Ingestão finalizada.")
                st.session_state["last_upload_feedback"] = {
                    "saved": len(saved_msgs),
                    "rejected_msgs": rejected_msgs,
                    "duplicate_count": len(duplicate_msgs),
                    "ingested_ok": len(ingest_ok_msgs),
                    "ingest_err_msgs": ingest_err_msgs,
                    "total_chunks": total_chunks,
                }
                st.session_state["uploader_nonce"] += 1
                st.session_state["last_processed_upload_signature"] = None
                st.rerun()

    if st.session_state.get("is_processing_uploads"):
        st.info("Processando uploads. A exclusão de documentos ficará disponível após a conclusão.")

    saved_pdf_names = _list_saved_pdfs()
    if saved_pdf_names:
        # st.markdown('<div class="saved-files-box">', unsafe_allow_html=True)
        for idx, file_name in enumerate(saved_pdf_names):
            file_path = _DOCUMENTS_DIR / file_name
            file_size = _human_file_size(file_path.stat().st_size) if file_path.exists() else "-"
            display_name = _truncate_filename(file_name)

            icon_col, name_col, remove_col = st.columns([0.16, 0.68, 0.16], vertical_alignment="center")
            with icon_col:
                st.markdown('<div class="saved-file-icon">▤</div>', unsafe_allow_html=True)
            with name_col:
                st.markdown(
                    (
                        '<div class="saved-file-text">'
                        f'<div class="saved-file-name">{display_name}</div>'
                        f'<div class="saved-file-size">{file_size}</div>'
                        "</div>"
                    ),
                    unsafe_allow_html=True,
                )
            with remove_col:
                if st.button(
                    "✖",
                    key=f"remove_saved_pdf_{idx}_{file_name}",
                    disabled=st.session_state.get("is_processing_uploads", False),
                    help=f"Remover {file_name}",
                    use_container_width=True,
                ):
                    ok, message = _clear_single_document(file_name)
                    if ok:
                        st.success(message)
                    else:
                        st.error(message)
                    st.session_state["last_processed_upload_signature"] = None
                    st.session_state["last_uploader_selected_names"] = []
                    st.session_state["uploader_nonce"] += 1
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    if st.button("🗑️  Remover todos os arquivos", use_container_width=True, disabled=st.session_state.get("is_processing_uploads", False)):
        ok, message = _clear_documents_and_database()
        if ok:
            st.success(message)
        else:
            st.error(message)
        st.session_state["last_processed_upload_signature"] = None
        st.session_state["last_uploader_selected_names"] = []
        st.session_state["uploader_nonce"] += 1
        st.rerun()

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
