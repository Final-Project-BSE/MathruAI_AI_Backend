import os
import pickle
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Tuple, Dict
import logging
from dailyrecommendationAI.config import Config

logger = logging.getLogger(__name__)

class VectorDatabase:
    def __init__(self):
        self.model = SentenceTransformer(Config.EMBEDDING_MODEL)
        self.dimension = Config.EMBEDDING_DIMENSION
        
        # Initialize FAISS index
        self.index = faiss.IndexFlatIP(self.dimension)
        self.document_chunks = []
        self.chunk_metadata = []
        
        # Create directories if they don't exist
        os.makedirs(Config.VECTOR_DB_PATH, exist_ok=True)
        
        # Load existing vector database if available
        self.load_vector_db()
    
    def add_chunks(self, chunks: List[str], source: str) -> bool:
        """Add text chunks to the vector database"""
        try:
            # Create embeddings
            embeddings = self.model.encode(chunks)
            
            # Add to FAISS index
            self.index.add(embeddings.astype('float32'))
            
            # Store chunks and metadata
            for i, chunk in enumerate(chunks):
                self.document_chunks.append(chunk)
                self.chunk_metadata.append({
                    'source': source,
                    'chunk_id': len(self.document_chunks) - 1,
                    'text': chunk
                })
            
            # Save vector database
            self.save_vector_db()
            logger.info(f"Successfully added {len(chunks)} chunks from {source}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding chunks to vector database: {e}")
            return False
    
    def search_similar_chunks(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """Search for similar chunks using vector similarity"""
        try:
            if self.index.ntotal == 0:
                return []
            
            query_embedding = self.model.encode([query])
            scores, indices = self.index.search(query_embedding.astype('float32'), top_k)
            
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < len(self.document_chunks):
                    results.append((self.document_chunks[idx], float(score)))
            
            return results
        except Exception as e:
            logger.error(f"Error searching similar chunks: {e}")
            return []
    
    def save_vector_db(self):
        """Save FAISS index and metadata"""
        try:
            faiss.write_index(self.index, os.path.join(Config.VECTOR_DB_PATH, 'faiss_index.bin'))
            
            with open(os.path.join(Config.VECTOR_DB_PATH, 'chunks.pkl'), 'wb') as f:
                pickle.dump(self.document_chunks, f)
            
            with open(os.path.join(Config.VECTOR_DB_PATH, 'metadata.pkl'), 'wb') as f:
                pickle.dump(self.chunk_metadata, f)
                
            logger.info("Vector database saved successfully")
        except Exception as e:
            logger.error(f"Error saving vector database: {e}")
    
    def load_vector_db(self):
        """Load existing FAISS index and metadata"""
        try:
            index_path = os.path.join(Config.VECTOR_DB_PATH, 'faiss_index.bin')
            chunks_path = os.path.join(Config.VECTOR_DB_PATH, 'chunks.pkl')
            metadata_path = os.path.join(Config.VECTOR_DB_PATH, 'metadata.pkl')
            
            if all(os.path.exists(path) for path in [index_path, chunks_path, metadata_path]):
                self.index = faiss.read_index(index_path)
                
                with open(chunks_path, 'rb') as f:
                    self.document_chunks = pickle.load(f)
                
                with open(metadata_path, 'rb') as f:
                    self.chunk_metadata = pickle.load(f)
                
                logger.info(f"Loaded vector database with {len(self.document_chunks)} chunks")
            
        except Exception as e:
            logger.error(f"Error loading vector database: {e}")
    
    def get_stats(self) -> Dict:
        """Get vector database statistics"""
        return {
            'total_chunks': len(self.document_chunks),
            'total_documents': len(set([meta['source'] for meta in self.chunk_metadata])),
            'embedding_dimension': self.dimension,
            'index_size': self.index.ntotal
        }
    
    def clear_database(self):
        """Clear all data from the vector database"""
        self.index = faiss.IndexFlatIP(self.dimension)
        self.document_chunks = []
        self.chunk_metadata = []
        self.save_vector_db()
        logger.info("Vector database cleared")