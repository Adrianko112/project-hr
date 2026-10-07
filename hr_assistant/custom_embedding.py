import os
from chromadb.api.types import EmbeddingFunction
from chromadb.utils import embedding_functions
from config import Config


class CustomEmbeddingFunction(EmbeddingFunction):
    """
    Funzione di embedding compatibile con ChromaDB.
    Il provider si sceglie in Config.EMBEDDING_PROVIDER:
    - openai: API OpenAI
    - local: modello SentenceTransformer in locale
    - ollama: modello servito da Ollama
    """

    def __init__(self):
        self.provider = Config.EMBEDDING_PROVIDER
        self.model_name = Config.MODEL_NAME

        if self.provider == "openai":
            self._setup_openai()
        elif self.provider == "local":
            self._setup_local()
        elif self.provider == "ollama":
            print(f"Embedding con Ollama: {self.model_name}")
        else:
            raise ValueError(
                f"EMBEDDING_PROVIDER '{self.provider}' non supportato "
                "(usa 'openai', 'local' oppure 'ollama')"
            )

    def _setup_openai(self):
        print(f"Embedding con OpenAI: {self.model_name}")
        self.model = embedding_functions.OpenAIEmbeddingFunction(
            api_key=Config.OPENAI_KEY, model_name=self.model_name
        )

    def _setup_local(self):
        # Import qui così chi usa solo OpenAI non deve installare torch
        from sentence_transformers import SentenceTransformer

        if os.path.exists(Config.MODEL_PATH):
            print(f"Carico il modello locale da {Config.MODEL_PATH}")
            self.model = SentenceTransformer(Config.MODEL_PATH)
        else:
            print(f"Scarico il modello {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            self.model.save(Config.MODEL_PATH)

    # Chroma richiede che il parametro si chiami "input"
    def __call__(self, input):
        if self.provider == "openai":
            return self.model(input)

        if self.provider == "local":
            return self.model.encode(input).tolist()

        # Import qui così chi usa solo OpenAI non deve installare ollama
        import ollama

        return ollama.embed(model=self.model_name, input=list(input))["embeddings"]
