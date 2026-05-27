import os
import pickle
import faiss
import logging
from typing import List, Tuple, Dict

from sentence_transformers import SentenceTransformer

from dailyrecommendationAI.config import Config

logger = logging.getLogger(__name__)


class VectorDatabase:
    INDEX_FILE = 'faiss_index.bin'
    CHUNKS_FILE = 'chunks.pkl'
    METADATA_FILE = 'metadata.pkl'

    def __init__(self):
        self.model = SentenceTransformer(Config.EMBEDDING_MODEL)
        self.dimension = Config.EMBEDDING_DIMENSION
        self.index = faiss.IndexFlatIP(self.dimension)
        self.document_chunks = []
        self.chunk_metadata = []

        os.makedirs(Config.VECTOR_DB_PATH, exist_ok=True)
        self.load_vector_db()

    def _index_path(self) -> str:
        return os.path.join(Config.VECTOR_DB_PATH, self.INDEX_FILE)

    def _chunks_path(self) -> str:
        return os.path.join(Config.VECTOR_DB_PATH, self.CHUNKS_FILE)

    def _metadata_path(self) -> str:
        return os.path.join(Config.VECTOR_DB_PATH, self.METADATA_FILE)

    def add_chunks(self, chunks: List[str], source: str) -> bool:
        """Add text chunks to the vector database."""
        try:
            if not chunks:
                return True

            embeddings = self.model.encode(chunks)
            self.index.add(embeddings.astype('float32'))

            start_idx = len(self.document_chunks)
            for offset, chunk in enumerate(chunks):
                self.document_chunks.append(chunk)
                self.chunk_metadata.append({
                    'source': source,
                    'chunk_id': start_idx + offset,
                    'text': chunk,
                })

            self.save_vector_db()
            logger.info('Successfully added %s chunks from %s', len(chunks), source)
            return True

        except Exception as e:
            logger.error('Error adding chunks to vector database: %s', e)
            return False

    def search_similar_chunks(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """Search for similar chunks using vector similarity."""
        try:
            if self.index.ntotal == 0:
                return []

            query_embedding = self.model.encode([query])
            scores, indices = self.index.search(query_embedding.astype('float32'), top_k)

            results = []
            for score, idx in zip(scores[0], indices[0]):
                if 0 <= idx < len(self.document_chunks):
                    results.append((self.document_chunks[idx], float(score)))

            return results
        except Exception as e:
            logger.error('Error searching similar chunks: %s', e)
            return []

    def save_vector_db(self):
        """Save FAISS index and metadata."""
        try:
            faiss.write_index(self.index, self._index_path())

            with open(self._chunks_path(), 'wb') as file_obj:
                pickle.dump(self.document_chunks, file_obj)

            with open(self._metadata_path(), 'wb') as file_obj:
                pickle.dump(self.chunk_metadata, file_obj)

            logger.info('Vector database saved successfully')
        except Exception as e:
            logger.error('Error saving vector database: %s', e)

    def load_vector_db(self):
        """Load existing FAISS index and metadata."""
        try:
            paths = [self._index_path(), self._chunks_path(), self._metadata_path()]
            if all(os.path.exists(path) for path in paths):
                self.index = faiss.read_index(self._index_path())

                with open(self._chunks_path(), 'rb') as file_obj:
                    self.document_chunks = pickle.load(file_obj)

                with open(self._metadata_path(), 'rb') as file_obj:
                    self.chunk_metadata = pickle.load(file_obj)

                logger.info('Loaded vector database with %s chunks', len(self.document_chunks))
        except Exception as e:
            logger.error('Error loading vector database: %s', e)

    def get_stats(self) -> Dict:
        """Get vector database statistics."""
        return {
            'total_chunks': len(self.document_chunks),
            'total_documents': len({meta['source'] for meta in self.chunk_metadata}),
            'embedding_dimension': self.dimension,
            'index_size': self.index.ntotal,
        }

    def clear_database(self):
        """Clear all data from the vector database."""
        self.index = faiss.IndexFlatIP(self.dimension)
        self.document_chunks = []
        self.chunk_metadata = []
        self.save_vector_db()
        logger.info('Vector database cleared')
