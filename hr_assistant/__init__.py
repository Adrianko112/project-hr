import os
import chainlit as cl
from document_processor import DocumentProcessor
from database import Database
from config import Config
from utils import LLMHelper

# Controllo che la chiave OpenAI sia stata caricata dal .env
if not Config.OPENAI_KEY:
    raise RuntimeError("OPENAI_API_KEY non trovata: controlla il file .env")

db = Database()

# Process documents
added, updated, removed = DocumentProcessor.process_documents(db)
print(f"Document sync complete: {added} added, {updated} updated, {removed} removed")


@cl.action_callback("db_stats")
async def on_db_stats(action: cl.Action):
    db_info = db.get_stats()
    response = await LLMHelper.get_db_stats(db_info)
    await cl.Message(content=response).send()


@cl.action_callback("db_reindex")
async def on_db_reindex(action: cl.Action):
    added, updated, removed = DocumentProcessor.process_documents(db)
    message = (
        "DB reindicizzato con successo. "
        f"Document sync complete: {added} added, {updated} updated, {removed} removed"
    )
    await cl.Message(content=message).send()


@cl.on_chat_start
async def start():
    actions = [
        cl.Action(
            name="db_stats",
            icon="mouse-pointer-click",
            payload={"value": "db_stats"},
            label="Statistiche Database",
        ),
        cl.Action(
            name="db_reindex",
            icon="mouse-pointer-click",
            payload={"value": "db_reindex"},
            label="Reindex Database",
        ),
    ]

    await cl.Message(content="Informazioni del sistema:", actions=actions).send()

    cl.user_session.set(
        "messages",
        [
            {
                "role": "system",
                "content": """
                    Sei un assistente specializzato nel mondo HR, rispondi in modo professionale, sintetico e pragmatico.
                    Il tuo ruolo è individuare il candidato ideale rispetto alle richieste dell'utente.
                """,
            }
        ],
    )


@cl.on_message
async def handle_message(message: cl.Message):
    user_question = message.content
    last_context = cl.user_session.get("last_cv_context")

    # Senza un CV già trovato non c'è nulla su cui chiedere info: si cerca sempre
    intent = LLMHelper.classify_intent(user_question) if last_context else "search_cv"

    if intent == "info_cv":
        context = last_context
        prompt = LLMHelper.create_info_prompt(context, user_question)
    else:
        results = db.query(user_question, 3)
        if not results["documents"][0]:
            await cl.Message(content="Nessun curriculum trovato per la richiesta.").send()
            return

        filename = results["metadatas"][0][0]["source"]
        candidate_info = DocumentProcessor.read_first_lines(
            os.path.join(Config.DOCUMENTS_DIR, filename), 10
        )

        context = (
            f"CONTESTO: nome file {filename} "
            f"ecco il paragrafo piu' significativo: {results['documents'][0][0]}, "
            f"qui trovi le informazioni del candidato: {candidate_info}"
        )
        cl.user_session.set("last_cv_context", context)
        prompt = LLMHelper.create_prompt(context, user_question)

    messages = cl.user_session.get("messages", [])
    messages.append({"role": "user", "content": prompt})

    response_message = cl.Message(content="")
    await response_message.send()

    try:
        stream = LLMHelper.chat(messages)

        for chunk in stream:
            if chunk.choices:
                token = chunk.choices[0].delta.content
                if token:
                    await response_message.stream_token(token)

        messages.append({"role": "assistant", "content": response_message.content})
        await response_message.update()

    except Exception as e:
        error_message = f"An error occurred: {str(e)}"
        await cl.Message(content=error_message).send()
        print(error_message)

    cl.user_session.set("messages", messages)


@cl.on_chat_end
async def end():
    await cl.Message(
        content="Grazie per aver utilizzato il nostro assistente. Buona giornata!"
    ).send()