# database.py
import chromadb
from config import Config
from custom_embedding import CustomEmbeddingFunction


class Database:
    def __init__(self):
        self.embedding_function = CustomEmbeddingFunction()

        # Initialize persistent client
        self.client = chromadb.PersistentClient(path=Config.PERSISTENT_DIR)

        self._init_collection()

    def _init_collection(self):
        self.collection = self.client.get_or_create_collection(
            name=Config.COLLECTION_NAME,
            embedding_function=self.embedding_function,
            # TIP: per forzare la distanza tra 0 e 1 aggiungi qui sotto
            # metadata={"hnsw:space": "cosine"},
        )

    def delete_collection(self):
        """Elimina la collezione e ne ricrea una vuota"""
        self.client.delete_collection(Config.COLLECTION_NAME)
        self._init_collection()

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