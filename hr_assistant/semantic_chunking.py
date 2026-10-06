import re
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from custom_embedding import CustomEmbeddingFunction
#
# Spiegazione Generale della Logica:
# Questo codice implementa un sistema di "semantic chunking", ovvero un modo intelligente di dividere un testo lungo in parti più piccole (chunk) che hanno senso semantico. Invece di dividere il testo in modo meccanico (per esempio ogni 500 caratteri), questo sistema usa l'intelligenza artificiale per capire dove il significato del testo cambia significativamente. Lo fa analizzando ogni frase nel suo contesto e utilizzando gli embedding di OpenAI per misurare quanto due frasi consecutive sono semanticamente diverse. Quando trova un punto dove la differenza semantica è particolarmente alta (sopra il 95° percentile per default), usa quel punto come confine per creare un nuovo chunk. Questo approccio è particolarmente utile per sistemi di elaborazione del linguaggio naturale, come chatbot o sistemi di ricerca, perché permette di mantenere insieme le parti di testo che sono semanticamente correlate.
#


class SemanticChunking:
    # Condivisa tra le istanze: un modello locale non va ricaricato per ogni file
    _embedding_function = None

    def __init__(self, breakpoint_percentile=95, buffer_size=1):
        if SemanticChunking._embedding_function is None:
            SemanticChunking._embedding_function = CustomEmbeddingFunction()
        self.embeddings = SemanticChunking._embedding_function
        self.breakpoint_percentile = breakpoint_percentile
        self.buffer_size = buffer_size

    @staticmethod
    def chunk_it(text, breakpoint_percentile=95, buffer_size=1):
        return SemanticChunking(breakpoint_percentile, buffer_size).chunk_text(text)

    @staticmethod
    def _split_into_sentences(text):
        text = text.strip()
        sentences = re.split(r"(?<=[.?!])\s+", text)

        # File come pdf, xlsx o csv convertiti in markdown possono non avere punteggiatura:
        # se esce una sola frase lunga si prova con a capo, ; e :, poi con la virgola
        if len(sentences) == 1 and len(text) > 100:
            sentences = re.split(r"(?<=[;:])\s+|\n+", text)
            if len(sentences) == 1:
                sentences = re.split(r"(?<=,)\s+", text)

        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences or [text]

    def _process_sentences(self, text):
        # Divide il testo in frasi e crea una lista di dizionari con indici
        sentences = [
            {"sentence": s, "index": i}
            for i, s in enumerate(self._split_into_sentences(text))
        ]

        # Combina ogni frase con il suo contesto (frasi precedenti e successive)
        for i, current in enumerate(sentences):
            context_range = range(
                max(0, i - self.buffer_size),
                min(len(sentences), i + self.buffer_size + 1),
            )
            current["combined_sentence"] = " ".join(
                sentences[j]["sentence"] for j in context_range
            )

        return sentences

    def _calculate_distances(self, sentences):
        # Calcola gli embedding per tutte le frasi combinate
        embeddings = self.embeddings(
            [s["combined_sentence"] for s in sentences]
        )

        # Calcola le distanze coseno tra frasi consecutive
        distances = []
        for i in range(len(sentences) - 1):
            distance = 1 - cosine_similarity([embeddings[i]], [embeddings[i + 1]])[0][0]
            distances.append(distance)

        return distances

    def chunk_text(self, text):
        # Processa le frasi
        sentences = self._process_sentences(text)
        if len(sentences) < 2:
            return [text]
        print("SENTENCES:",sentences[:2])
        # Calcola le distanze
        distances = self._calculate_distances(sentences)
        print("DISTANCES:",distances[:2])

        # Determina i punti di divisione basati sul percentile
        threshold = np.percentile(distances, self.breakpoint_percentile)
        split_points = [i for i, d in enumerate(distances) if d > threshold]
        print("SPLIT POINTS: ",split_points)
        # Crea i chunk finali
        chunks = []
        start = 0
        for point in split_points + [len(sentences) - 1]:
            chunk = " ".join(s["sentence"] for s in sentences[start : point + 1])
            print("CHUNK: ",chunk)
            chunks.append(chunk)
            start = point + 1

        return chunks
