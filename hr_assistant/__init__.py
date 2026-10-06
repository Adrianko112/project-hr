import chainlit as cl
import chromadb
import os, uuid
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

openai_key = os.getenv("OPENAI_API_KEY")
client = AsyncOpenAI(api_key=openai_key)
MODEL = "gpt-4o-mini"  # cambialo con il modello che preferisci

## FASE 1 - Lettura Files e Chunking

documents_dir = "resumes"

documents = []
metadatas = []
ids = []

for filename in os.listdir(documents_dir):
    if filename.endswith(".txt"):
        with open(os.path.join(documents_dir, filename), "r", encoding="utf-8") as file:
            chunks = file.read().replace("\n", ".").split("### ")

            for chunk in chunks:
                if not chunk.isspace() and not chunk == "":
                    documents.append(chunk)
                    metadatas.append({"source": filename})
                    # Genera un nuovo GUID per ogni chunk
                    ids.append(str(uuid.uuid4()))

print(documents, metadatas, ids)

## FASE 2 - Embeddings e inserimento nel DB Vettoriale

openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=openai_key, model_name="text-embedding-3-small"
)

chroma_client = chromadb.Client()

collection = chroma_client.get_or_create_collection(
    name="CVs", embedding_function=openai_ef
)

collection.add(documents=documents, metadatas=metadatas, ids=ids)


## FASE 3 - CHAT


@cl.on_chat_start
def on_chat_start():
    """
    Inizializza la sessione utente con un messaggio del sistema.
    Questo messaggio definisce il ruolo del chatbot.
    """
    cl.user_session.set(
        "messages",
        [
            {
                "role": "system",
                "content": """
                      Sei un assistente specializzato nel mondo HR, rispondi in modo professionale, sintetico e pragmatico. Il tuo ruolo è individuare il candidato ideale rispetto alle richieste dell'utente.
                      """,
            }
        ],
    )


def leggi_prime_100_righe(file_path):
    """Legge le prime 100 righe del CV (serve per ricavare nome e cognome)."""
    righe = []
    with open(file_path, "r", encoding="utf-8") as file:
        for i, riga in enumerate(file):
            if i < 100:
                righe.append(riga.strip())
            else:
                break
    return righe


@cl.on_message
async def handle_message(message: cl.Message):
    """
    Gestisce i messaggi inviati dall'utente, li passa al modello e restituisce le risposte.
    """

    user_question = message.content

    results = collection.query(query_texts=[user_question], n_results=1)

    # Prendo la prima parte del file per leggere il nome del candidato
    filename = results["metadatas"][0][0]["source"]
    context_nome_candidato = leggi_prime_100_righe(
        os.path.join(documents_dir, filename)
    )

    resp = await client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": f"""
                      Dato il seguente contesto individua il nome e cognome del candidato e ritorna solo il nome e cognome del candidato. quello che sto per fornirti e' il curriculum vitae del candidato: {context_nome_candidato}
                      """,
            }
        ],
    )

    nome = resp.choices[0].message.content

    context = f"CONTESTO: nome file {results['metadatas'][0][0]['source']} ecco il paragrafo piu' significativo: {results['documents'][0][0]}"

    prompt = f"""
        Dato il seguente contesto: 
        [[[
        {context}
        ]]].
        Rispondi alla domanda dell'utente: [[[ {user_question}]]] .
        Spiega che nel file individuato c'e' il profilo piu' adatto. 
        Assicurati di nominare il Nome dei file.
        Assicurati di indicare il nome del candidato: [[[ {nome} ]]].
        Argomenta la scelta utilizzando il contenuto del testo individuato nel contesto.
        Se non trovi corrispondenza in nessun cv non inventare."""

    print("\n\n\n")
    print("*" * 80)
    print(nome)
    print("*" * 80)
    print(context)
    print("*" * 80)
    print(prompt)
    print("*" * 80)

    # Recupera i messaggi salvati nella sessione utente
    messages = cl.user_session.get("messages", [])
    messages.append({"role": "user", "content": prompt})

    # Inizializza un messaggio vuoto per mostrare lo streaming
    response_message = cl.Message(content="")
    await response_message.send()

    try:
        stream = await client.chat.completions.create(
            model=MODEL, messages=messages, stream=True
        )

        async for chunk in stream:
            if chunk.choices:
                token = chunk.choices[0].delta.content
                if token:
                    await response_message.stream_token(token)

        # Salva la risposta del modello nella sessione
        messages.append({"role": "assistant", "content": response_message.content})
        await response_message.update()
    except Exception as e:
        error_message = f"An error occurred: {str(e)}"
        await cl.Message(content=error_message).send()
        print(error_message)

    # Aggiorna i messaggi nella sessione utente
    cl.user_session.set("messages", messages)


@cl.on_chat_end
async def on_chat_end():
    """
    Messaggio finale alla fine della chat.
    """
    await cl.Message(
        content="""
               Grazie per aver utilizzato il nostro assistente. 
               Buona giornata!
               """
    ).send()