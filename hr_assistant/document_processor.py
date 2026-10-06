# document_processor.py
import os
import uuid
from config import Config

class DocumentProcessor:
    @staticmethod
    def process_documents():
        documents = []
        metadatas = []
        ids = []

        for filename in os.listdir(Config.DOCUMENTS_DIR):
            if filename.endswith(".txt"):
                with open(os.path.join(Config.DOCUMENTS_DIR, filename), 'r') as file:
                    chunks = file.read().replace('\n', '.').split('### ')

                    for chunk in chunks:
                        if not chunk.isspace() and not chunk == "":
                            documents.append(chunk)
                            metadatas.append({"source": filename})
                            ids.append(str(uuid.uuid4()))

        return documents, metadatas, ids

    @staticmethod
    def read_first_lines(file_path, n_lines=100):
        with open(file_path, 'r') as file:
            return [line.strip() for line, _ in zip(file, range(n_lines))]
