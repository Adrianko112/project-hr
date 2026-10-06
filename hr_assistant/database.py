# database.py
import chromadb
from chromadb.utils import embedding_functions
from config import Config


class Database:
    def __init__(self):
        self.openai_ef = embedding_functions.OpenAIEmbeddingFunction(
            api_key=Config.OPENAI_KEY, model_name=Config.MODEL_NAME
        )

        # Initialize persistent client
        self.client = chromadb.PersistentClient(path=Config.PERSISTENT_DIR)

        self.collection = self.client.get_or_create_collection(
            name=Config.COLLECTION_NAME,
            embedding_function=self.openai_ef,
            # TIP: per forzare la distanza tra 0 e 1 aggiungi qui sotto
            # metadata={"hnsw:space": "cosine"},
        )

    def add_documents(self, documents, metadatas, ids):
        self.collection.add(documents=documents, metadatas=metadatas, ids=ids)

    def query(self, query_text, n_results=1):
        return self.collection.query(query_texts=[query_text], n_results=n_results)

    def get_tracked_files(self):
        """Get all unique files and their metadata from the database"""
        result = self.collection.get()
        tracked_files = {}

        if result and result["metadatas"]:
            for metadata in result["metadatas"]:
                source = metadata.get("source")
                if not source:
                    continue

                if source not in tracked_files:
                    tracked_files[source] = {
                        "hash": metadata.get("hash"),
                        "last_modified": metadata.get("last_modified"),
                        "source": source,
                    }

        return tracked_files

    def remove_document_by_source(self, source):
        """Remove all entries for a specific source file"""
        result = self.collection.get(where={"source": source})
        if result and result["ids"]:
            self.collection.delete(ids=result["ids"])

    def get_stats(self):
        """Statistiche della collezione, come stringa"""
        result = self.collection.get()

        # Il set elimina i duplicati: un file ha più chunk ma conta una volta
        valori_distinti = {
            m["source"] for m in (result["metadatas"] or []) if m.get("source")
        }
        numero_files = len(valori_distinti)

        return f"""
            Nome Collezione: {self.collection.name}
            Numero totale Frammenti: {self.collection.count()}
            Numero Files Elaborati: {numero_files}
        """