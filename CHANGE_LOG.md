## 03

- Sync Documenti

## 04

- tasti db info e db reindex

## 05

- Semantic Chunking

## 06

- Refactoring Semantic Chunking

## 06.1

- Embedding intercambiabili: OpenAI, SentenceTransformer in locale, Ollama

## 06.2

- User intent: distinzione tra ricerca di un CV e domande su un CV già trovato

## 07

- Lettura di file di tipo diverso (pdf, docx, pptx, xlsx, csv, html, zip...) con MarkItDown
- Semantic Chunking: _split_into_sentences per evitare che un file produca una sola frase

## 08

- Upload di uno o più file in resumes da interfaccia, con aggiornamento del database degli embeddings
- Nuova action per svuotare il database

## 09 - Tema UI

- Tema personalizzato (public/theme.json) e CSS (public/app.css) impostato in .chainlit/config.toml
- Logo, favicon e avatar per gli autori dei messaggi (system_assistant, hr_assistant)
- Tema scuro coerente con quello chiaro, testo di benvenuto in chainlit.md, icone dedicate ai pulsanti