from langchain.chains.query_constructor.schema import AttributeInfo

metadata_field_info = [
    AttributeInfo(
        name="numero_documento",
        description=(
            "- Numero identificador do documento (ex.: apolice, proposta, endosso ou anexo).\n"
            "- Use este campo quando o usuario perguntar por um documento especifico."
        ),
        type="string",
    ),
    AttributeInfo(
        name="tipo",
        description="Tipo do documento (ex.: 'apolice', 'manual', 'faq', 'comunicado', 'outro').",
        type="string",
    ),
    AttributeInfo(
        name="data",
        description=("Data textual do documento no formato 'DD/MM/AAAA' (string), quando disponivel.\n"),
        type="string",
    ),
    AttributeInfo(
        name="assunto",
        description=(
            "Assunto principal do documento (ex.: coberturas, franquia, carencia, exclusoes, assistencia).\n"
            "- Pode ser usado para refinar busca por tema de seguro residencial.\n"
        ),
        type="string",
    ),
    AttributeInfo(
        name="pdf_name",
        description="Nome do arquivo PDF de origem.",
        type="string",
    ),
    AttributeInfo(
        name="chunk_type",
        description="Tipo do chunk: 'coberturas', 'exclusoes', 'franquia', 'sinistro', 'assistencia' ou 'conteudo_geral'.",
        type="string",
    ),
    AttributeInfo(
        name="chunk_index",
        description="Índice do chunk no documento.",
        type="integer",
    ),
]
document_content_description = """
    Colecao de trechos (chunks) de documentos de seguro residencial,
    com metadados como numero_documento,
    tipo, assunto, data, nome do arquivo (pdf_name) e tipo de trecho (chunk_type).\n\n
"""

SYSTEM_PROMPT_SEGURO_RESIDENCIAL = """
Voce e um Assistente Especialista em Seguro Residencial.

## Contexto

Voce recebera uma pergunta "{question}" do usuario e um conjunto de trechos de documentos "{context}".

Sua diretriz principal e a FIDELIDADE AO TEXTO. Voce deve responder usando apenas os trechos dos documentos fornecidos no contexto.

Estruture sua resposta da seguinte maneira:

1.  **Introducao Direta**: Comece com uma frase objetiva respondendo a pergunta do usuario.

2.  **Apresentacao Organizada**: Para cada documento ou trecho relevante encontrado no contexto, crie uma secao clara e separada.

3.  **Formato de Citação**: Use o seguinte formato para cada seção:
    "**Conforme o documento [doc_id#chunk_id]:**"

4.  **Extracao Literal**: Abaixo do titulo, insira o trecho literal relevante do documento.

**Restrições Obrigatórias:**
- Fundamente TODA a sua resposta exclusivamente no contexto fornecido.
- Nao adicione opinioes, interpretacoes, exemplos ou informacoes externas de qualquer natureza.
"""
