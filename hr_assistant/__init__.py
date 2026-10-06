import os
import chainlit as cl
from document_processor import DocumentProcessor
from database import Database
from config import Config
from utils import LLMHelper


# Process documents
documents, metadatas, ids = DocumentProcessor.process_documents()

# print("*" * 80)
# print("Chucks, metadata e ids")
# print("*" * 80)
# print(documents, metadatas, ids)

# Initialize database and add documents
db = Database()
db.add_documents(documents, metadatas, ids)

# E' ancora inefficiente
# perche' ricarica sempre tutto nel DB 


@cl.on_chat_start
def start():
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
    results = db.query(user_question)

    filename = results["metadatas"][0][0]["source"]
    context_lines = DocumentProcessor.read_first_lines(
        os.path.join(Config.DOCUMENTS_DIR, filename), 10
    )

    context = f"CONTESTO: nome file {results['metadatas'][0][0]['source']} ecco il paragrafo piu' significativo: {results['documents'][0][0]}"

    candidate_name = await LLMHelper.get_candidate_name(context_lines)

    prompt = LLMHelper.create_prompt(context, user_question, candidate_name)

    messages = cl.user_session.get("messages", [])
    messages.append({"role": "user", "content": prompt})

    # print("*" * 80)
    # print("*" * 80)
    # print("prompt", prompt)
    # print("*" * 80)
    # print("*" * 80)

    response_message = cl.Message(content="")
    await response_message.send()

    try:
        stream = LLMHelper.chat(messages)

        for chunk in stream:
            await response_message.stream_token(str(chunk.choices[0].delta.content))

        messages.append({"role": "assistant", "content": response_message.content})
        await response_message.update()

    except Exception as e:
        error_message = f"An error occurred: {str(e)}"
        await cl.Message(content=error_message).send()
        print(error_message)

    cl.user_session.set("messages", messages)


# @cl.on_chat_end
# def end():
#     cl.Message(content="Grazie per aver utilizzato il nostro assistente. Buona giornata!").send()
