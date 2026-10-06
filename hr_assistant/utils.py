# utils.py
from config import Config
from openai import OpenAI

client = OpenAI(base_url=Config.AI_API_URL, api_key=Config.AI_API_KEY)


class LLMHelper:

    @staticmethod
    def chat(messages):
        return client.chat.completions.create(
            model=Config.LLM_MODEL, messages=messages, stream=True
        )

    @staticmethod
    async def get_candidate_name(context):
        response = client.chat.completions.create(
            model=Config.LLM_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": f"""
                      Dato il seguente contesto individua il nome e cognome del candidato e ritorna solo il nome e cognome del candidato. Quello che sto per fornirti e' l'inizio del curriculum vitae del candidato: {context}
                      """,
                }
            ],
        )
        return response.choices[0].message.content

    @staticmethod
    def create_prompt(context, question, candidate_name):
        return f"""
            Dato il seguente contesto: 
            [[[
            {context}
            ]]].
            Rispondi alla domanda dell'utente: [[[ {question}]]] .
            Spiega che nel file individuato c'e' il profilo piu' adatto. 
            Assicurati di nominare il Nome dei file.
            Assicurati di indicare il nome del candidato: [[[ {candidate_name} ]]].
            Argometa la scelta utilizzando il contenuto del testo individuato nel contesto.
            Se non trovi corrispondeza in nessun cv non inventare.
        """
