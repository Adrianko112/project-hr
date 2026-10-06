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
        # Non più usata in main: puoi eliminarla
        response = client.chat.completions.create(
            model=Config.LLM_MODEL_LOW,
            messages=[
                {
                    "role": "user",
                    "content": f"""
                      Dato il seguente contesto individua il nome e cognome del candidato e ritorna solo il nome e cognome del candidato. Quello che sto per fornirti e' il curriculum vitae del candidato: {context}
                      """,
                }
            ],
        )
        return response.choices[0].message.content

    @staticmethod
    async def get_db_stats(context):
        response = client.chat.completions.create(
            model=Config.LLM_MODEL_LOW,
            messages=[
                {
                    "role": "user",
                    "content": f"""
                      Il tuo compito è quello di descrivere in modo testuale, ma sintetico, le statistiche legate al database dei frammenti indicizzati da questo sistema. Dammi pure la percentuale di frammenti indicizzati rispetto al totale dei file presenti nel database. Ecco le informazioni necessarie per le statistiche da fornire: {context}
                      """,
                }
            ],
        )
        return response.choices[0].message.content

    @staticmethod
    def create_prompt(context, question):
        return f"""
            Dato il seguente contesto: 
            [[[
            {context}
            ]]].
            Rispondi alla domanda dell'utente: [[[ {question}]]].
            Spiega che nel file individuato c'e' il profilo piu' adatto. 
            Argomenta la scelta utilizzando il contenuto del testo individuato nel contesto.
            Se non trovi corrispondenza in nessun cv non inventare.
            Alla fine crea una sezione per i contatti del candidato indicando il nome, la sua email e il numero di telefono.
            Dopo la sezione dei contatti indica il Nome del file del cv, non lo nominare mai prima di questa sezione.
        """