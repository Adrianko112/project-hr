# document_processor.py
import os
import uuid
import hashlib
import tempfile
from zipfile import ZipFile
from config import Config
from semantic_chunking import SemanticChunking


class DocumentProcessor:
    # Estensione -> tipo di file. I .txt si leggono direttamente, il resto con MarkItDown
    SUPPORTED_EXTENSIONS = {
        ".txt": "text",
        ".pdf": "document",
        ".doc": "document",
        ".docx": "document",
        ".ppt": "presentation",
        ".pptx": "presentation",
        ".xls": "spreadsheet",
        ".xlsx": "spreadsheet",
        ".html": "web",
        ".htm": "web",
        ".csv": "data",
        ".json": "data",
        ".xml": "data",
        ".zip": "archive",
    }

    _md_converter = None

    @staticmethod
    def get_extension(file_path):
        return os.path.splitext(file_path)[1].lower()

    @staticmethod
    def is_supported(file_path):
        return DocumentProcessor.get_extension(file_path) in DocumentProcessor.SUPPORTED_EXTENSIONS

    @staticmethod
    def _convert_to_markdown(file_path):
        """Converte un file (pdf, docx, xlsx...) in markdown con MarkItDown"""
        # Import qui così chi usa solo file .txt non deve installare markitdown
        from markitdown import MarkItDown

        if DocumentProcessor._md_converter is None:
            DocumentProcessor._md_converter = MarkItDown()

        try:
            return DocumentProcessor._md_converter.convert(file_path).text_content
        except Exception as e:
            print(f"Errore nella conversione di {file_path}: {e}")
            return ""

    @staticmethod
    def _read_zip(file_path):
        """Unisce il contenuto dei file supportati dentro uno zip"""
        content = ""
        with tempfile.TemporaryDirectory() as temp_dir:
            with ZipFile(file_path, "r") as zip_file:
                zip_file.extractall(temp_dir)

            for root, _, files in os.walk(temp_dir):
                for name in files:
                    inner_path = os.path.join(root, name)
                    # niente zip dentro lo zip
                    if not DocumentProcessor.is_supported(inner_path) or name.lower().endswith(".zip"):
                        continue
                    text = DocumentProcessor.read_content(inner_path)
                    if text:
                        content += f"\n\nFile: {name}\n{text}"
        return content

    @staticmethod
    def read_content(file_path):
        """Testo completo di un file, qualunque sia il formato supportato"""
        extension = DocumentProcessor.get_extension(file_path)

        if extension == ".txt":
            with open(file_path, "r", encoding="utf-8") as file:
                return file.read()
        if extension == ".zip":
            return DocumentProcessor._read_zip(file_path)
        if extension in DocumentProcessor.SUPPORTED_EXTENSIONS:
            return DocumentProcessor._convert_to_markdown(file_path)
        return ""

    @staticmethod
    def read_first_lines(file_path, n_lines=100):
        lines = DocumentProcessor.read_content(file_path).splitlines()
        return [line.strip() for line in lines[:n_lines]]

    @staticmethod
    def get_file_hash(file_path):
        """Calculate MD5 hash of file content"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    @staticmethod
    def get_document_metadata(file_path):
        """Get document metadata including hash and last modified time"""
        extension = DocumentProcessor.get_extension(file_path)
        return {
            "hash": DocumentProcessor.get_file_hash(file_path),
            "last_modified": os.path.getmtime(file_path),
            "source": os.path.basename(file_path),
            "file_type": DocumentProcessor.SUPPORTED_EXTENSIONS.get(extension, "unknown"),
            "extension": extension,
        }

    @staticmethod
    def process_single_document(file_path):
        """Process a single document into chunks"""
        documents = []
        metadatas = []
        ids = []

        with open(file_path, "r", encoding="utf-8") as file:
            txt = file.read()
            # OLD
            # chunks = txt.replace("\n", ".").split("### ")
            chunks = SemanticChunking.chunk_it(txt)
            file_metadata = DocumentProcessor.get_document_metadata(file_path)

            for chunk in chunks:
                if not chunk.isspace() and not chunk == "":
                    documents.append(chunk)
                    metadatas.append(file_metadata)
                    ids.append(str(uuid.uuid4()))

        return documents, metadatas, ids

    @staticmethod
    def process_documents(db):
        """Process documents and sync with database"""
        # TIP
        # Dictionary comprehension

        # numeri = [1, 2, 3, 4, 5]
        # quadrati = {n: n**2 for n in numeri if n % 2 == 0}
        # print(quadrati)  # Output: {2: 4, 4: 16}

        # Get current files in directory
        current_files = {
            f: DocumentProcessor.get_document_metadata(
                os.path.join(Config.DOCUMENTS_DIR, f)
            )
            for f in os.listdir(Config.DOCUMENTS_DIR)
            if DocumentProcessor.is_supported(f)
        }
        print("Current files in directory:", current_files)

        # Get existing files from database
        existing_files = db.get_tracked_files()
        print("Existing files in db:", existing_files)

        # Identify files to add, update, and remove
        files_to_add = set(current_files.keys()) - set(existing_files.keys())
        print("Files to add:", files_to_add)

        files_to_remove = set(existing_files.keys()) - set(current_files.keys())
        print("Files to remove:", files_to_remove)

        files_to_update = {
            f
            for f in set(current_files.keys()) & set(existing_files.keys())
            if current_files[f]["hash"] != existing_files[f]["hash"]
        }
        print("Files to update:", files_to_update)

        # Process updates
        # In PHP sarebbe:
        # foreach (["add" => $files_to_add, "update" => $files_to_update] as $action => $files) {
        #     foreach ($files as $filename) { ... }
        # }
        for action, files in [("add", files_to_add), ("update", files_to_update)]:
            for filename in files:
                file_path = os.path.join(Config.DOCUMENTS_DIR, filename)
                documents, metadatas, ids = DocumentProcessor.process_single_document(
                    file_path
                )

                if action == "update":
                    # Remove old entries first
                    db.remove_document_by_source(filename)

                # Add new entries
                if documents:
                    db.add_documents(documents, metadatas, ids)

        # Remove deleted files from database
        for filename in files_to_remove:
            db.remove_document_by_source(filename)

        return len(files_to_add), len(files_to_update), len(files_to_remove)