"""
Main RAG system implementation with vector similarity search.
"""
import os
import re
import numpy as np
import pickle
import hashlib
import faiss
from sentence_transformers import SentenceTransformer
from datetime import datetime
from typing import List, Dict, Optional, Generator
import logging
import groq

from chatbot.config.settings import RAGConfig, validate_config
from chatbot.utils.pdf_extractor import extract_text_from_pdf
from chatbot.utils.token_manager import TokenManager
from chatbot.utils.text_chunker import TextChunker
from chatbot.database.manager import DatabaseManager

logger = logging.getLogger(__name__)


class VectorRAGSystem:
    """
    Vector based Retrieval Augmented Generation system for pregnancy guidance.
    """
    
    def __init__(self, embedding_model: str = None, chunk_size: int = None, chunk_overlap: int = None):
        """
        Initialize the RAG system.
        
        Args:
            embedding_model (str, optional): Name of embedding model to use
            chunk_size (int, optional): Maximum chunk size
            chunk_overlap (int, optional): Overlap between chunks
        """
        # Validate configuration
        validate_config()
        
        # Initialize API client
        if not RAGConfig.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        
        self.client = groq.Groq(api_key=RAGConfig.GROQ_API_KEY)
        self.knowledge_base = []
        
        # Initialize components with config defaults
        self.token_manager = TokenManager(
            model_name=RAGConfig.LLM_MODEL,
            max_context_tokens=RAGConfig.MAX_CONTEXT_TOKENS
        )
        
        self.chunker = TextChunker(
            max_chunk_size=chunk_size or RAGConfig.CHUNK_SIZE,
            overlap_size=chunk_overlap or RAGConfig.CHUNK_OVERLAP,
            min_chunk_size=RAGConfig.MIN_CHUNK_SIZE
        )
        
        # Initialize embedding model
        embedding_model = embedding_model or RAGConfig.EMBEDDING_MODEL
        logger.info(f"Loading embedding model: {embedding_model}")
        
        try:
            self.embedding_model = SentenceTransformer(embedding_model)
            self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
            logger.info(f"Loaded embedding model with dimension: {self.embedding_dim}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
        
        # Initialize FAISS index
        self.faiss_index = faiss.IndexFlatIP(self.embedding_dim)
        self.faiss_index = faiss.IndexIDMap(self.faiss_index)
        
        # Initialize database manager
        try:
            self.db_manager = DatabaseManager()
        except Exception as e:
            logger.warning(f"Database initialization failed: {e}")
            self.db_manager = None
        
        # Load existing knowledge base
        self.load_knowledge_base()
    
    def _calculate_kb_hash(self) -> str:
        """Calculate hash of current knowledge base for change detection."""
        kb_string = '\n'.join(self.knowledge_base)
        return hashlib.md5(kb_string.encode()).hexdigest()
    
    def _load_cached_data(self) -> bool:
        """Load cached knowledge base and FAISS index if available."""
        try:
            cache_files = [RAGConfig.KB_FILE, RAGConfig.FAISS_INDEX_FILE, RAGConfig.HASH_FILE]
            if not all(os.path.exists(f) for f in cache_files):
                logger.info("Cache files not found, will build fresh index")
                return False
            
            with open(RAGConfig.KB_FILE, 'rb') as f:
                cached_kb = pickle.load(f)
            
            with open(RAGConfig.HASH_FILE, 'r') as f:
                cached_hash = f.read().strip()
            
            current_hash = hashlib.md5('\n'.join(cached_kb).encode()).hexdigest()
            
            if cached_hash == current_hash:
                self.knowledge_base = cached_kb
                self.faiss_index = faiss.read_index(RAGConfig.FAISS_INDEX_FILE)
                
                logger.info(f"Loaded cached knowledge base with {len(self.knowledge_base)} chunks")
                logger.info(f"FAISS index loaded with {self.faiss_index.ntotal} vectors")
                return True
            else:
                logger.info("Cache hash mismatch, will regenerate embeddings")
                return False
                
        except Exception as e:
            logger.warning(f"Error loading cached data: {e}")
            return False
    
    def _save_cached_data(self):
        """Save knowledge base and FAISS index to cache."""
        try:
            os.makedirs(RAGConfig.CACHE_DIR, exist_ok=True)
            
            with open(RAGConfig.KB_FILE, 'wb') as f:
                pickle.dump(self.knowledge_base, f)
            
            faiss.write_index(self.faiss_index, RAGConfig.FAISS_INDEX_FILE)
            
            with open(RAGConfig.HASH_FILE, 'w') as f:
                f.write(self._calculate_kb_hash())
            
            logger.info("Cached knowledge base and FAISS index")
            
        except Exception as e:
            logger.error(f"Error saving cached data: {e}")
    
    def _generate_and_store_embeddings(self, texts: List[str], source_file: str = None):
        """Generate embeddings and store them in FAISS index."""
        logger.info(f"Generating embeddings for {len(texts)} chunks...")
        
        try:
            embeddings = self.embedding_model.encode(texts, show_progress_bar=True)
            embeddings = np.array(embeddings, dtype=np.float32)
            
            # Normalize for cosine similarity
            faiss.normalize_L2(embeddings)
            
            # Add to FAISS index with IDs
            start_id = len(self.knowledge_base)
            ids = np.arange(start_id, start_id + len(texts), dtype=np.int64)
            self.faiss_index.add_with_ids(embeddings, ids)
            
            # Store in database if available
            if self.db_manager:
                for i, (text, embedding_id) in enumerate(zip(texts, ids)):
                    self.db_manager.store_chunk(
                        chunk_text=text,
                        source_file=source_file or "default",
                        chunk_index=i,
                        embedding_vector_id=int(embedding_id),
                        metadata={
                            "chunk_method": "smart_chunk", 
                            "embedding_model": RAGConfig.EMBEDDING_MODEL,
                            "chunk_size": len(text)
                        }
                    )
            
            logger.info(f"Added {len(texts)} vectors to FAISS index")
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
    
    def update_knowledge_base_from_pdf(self, pdf_path: str) -> bool:
        """
        Update the knowledge base with content from a PDF.
        
        Args:
            pdf_path (str): Path to the PDF file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            content = extract_text_from_pdf(pdf_path)
            if not content:
                logger.warning("No content found in the PDF")
                return False
            
            logger.info(f"Extracted {len(content)} characters from PDF")
            
            # Use smart chunking
            new_chunks = self.chunker.smart_chunk(content)
            
            if not new_chunks:
                logger.warning("No valid content chunks found in the PDF")
                return False
            
            # Log chunk statistics
            chunk_stats = self.chunker.get_chunk_stats(new_chunks)
            logger.info(f"Created {chunk_stats['count']} chunks - "
                       f"Min: {chunk_stats['min_length']}, "
                       f"Max: {chunk_stats['max_length']}, "
                       f"Avg: {chunk_stats['avg_length']}")
            
            before = len(self.knowledge_base)
            self.knowledge_base.extend(new_chunks)
            
            # Generate and store embeddings
            source_filename = os.path.basename(pdf_path)
            self._generate_and_store_embeddings(new_chunks, source_filename)
            
            after = len(self.knowledge_base)
            logger.info(f"Added {after - before} new chunks; total is now {after}")
            
            # Save updated cache
            self._save_cached_data()
            return True
            
        except Exception as e:
            logger.error(f"Error updating knowledge base from PDF: {e}")
            return False

    def load_knowledge_base(self):
        """Load and process the default knowledge base."""
        if self._load_cached_data():
            return
        
        try:
            # Try to load default knowledge base file
            if os.path.exists(RAGConfig.DEFAULT_KB_FILE):
                with open(RAGConfig.DEFAULT_KB_FILE, 'r', encoding='utf-8') as file:
                    content = file.read()
                
                # Use smart chunking for initial knowledge base
                self.knowledge_base = self.chunker.smart_chunk(content)
                logger.info(f"Loaded default knowledge base with {len(self.knowledge_base)} chunks")
            else:
                logger.warning("Default knowledge base file not found, creating minimal knowledge base")
                self.knowledge_base = [
                    "General pregnancy information will be provided based on medical guidelines.",
                    "Always consult your healthcare provider for medical advice during pregnancy.",
                    "Maintain a healthy diet with prenatal vitamins during pregnancy.",
                    "Regular prenatal checkups are essential for a healthy pregnancy."
                ]
        
            if self.knowledge_base:
                self._generate_and_store_embeddings(self.knowledge_base, "default_knowledge_base")
                logger.info(f"Initialized FAISS index with {len(self.knowledge_base)} knowledge chunks")
                self._save_cached_data()
            else:
                logger.warning("No knowledge base content available")
                
        except Exception as e:
            logger.error(f"Error loading knowledge base: {e}")
    
    def find_relevant_context(self, query: str, top_k: int = None, similarity_threshold: float = None) -> str:
        """
        Find most relevant context using FAISS vector similarity.
        
        Args:
            query (str): Search query
            top_k (int, optional): Number of top results to retrieve
            similarity_threshold (float, optional): Minimum similarity threshold
            
        Returns:
            str: Relevant context text
        """
        top_k = top_k or RAGConfig.DEFAULT_TOP_K
        similarity_threshold = similarity_threshold or RAGConfig.SIMILARITY_THRESHOLD
        
        if not self.knowledge_base or self.faiss_index.ntotal == 0:
            logger.warning("No knowledge base available for search")
            return ""
        
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query])
            query_embedding = np.array(query_embedding, dtype=np.float32)
            faiss.normalize_L2(query_embedding)
            
            # Search for relevant chunks
            search_k = min(top_k * 3, self.faiss_index.ntotal)
            scores, indices = self.faiss_index.search(query_embedding, search_k)
            
            relevant_chunks = []
            for score, idx in zip(scores[0], indices[0]):
                if idx != -1 and score >= similarity_threshold:
                    relevant_chunks.append(self.knowledge_base[idx])
                    logger.debug(f"Retrieved chunk {idx} with similarity: {score:.3f}")
            
            # If no chunks meet threshold, use best match
            if not relevant_chunks and len(indices[0]) > 0 and indices[0][0] != -1:
                best_idx = indices[0][0]
                relevant_chunks = [self.knowledge_base[best_idx]]
                logger.info(f"Using best match (chunk {best_idx}) with similarity: {scores[0][0]:.3f}")
            
            # Use token manager to truncate context appropriately
            system_prompt = self._get_system_prompt()
            truncated_context = self.token_manager.truncate_context(relevant_chunks, query, system_prompt)
            
            return truncated_context
            
        except Exception as e:
            logger.error(f"Error in FAISS retrieval: {e}")
            return self._fallback_keyword_search(query, top_k)
    
    def _fallback_keyword_search(self, query: str, top_k: int = 3) -> str:
        """Fallback keyword matching method."""
        logger.info("Using fallback keyword search")
        query_lower = query.lower()
        scored_chunks = []
        
        for chunk in self.knowledge_base:
            chunk_lower = chunk.lower()
            score = 0
            query_words = re.findall(r'\w+', query_lower)
            
            for word in query_words:
                if len(word) > 3:
                    score += chunk_lower.count(word)
            
            if score > 0:
                scored_chunks.append((score, chunk))
        
        scored_chunks.sort(reverse=True, key=lambda x: x[0])
        relevant_chunks = [chunk for score, chunk in scored_chunks[:top_k * 2]]
        
        # Use token manager to truncate
        system_prompt = self._get_system_prompt()
        return self.token_manager.truncate_context(relevant_chunks, query, system_prompt)
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the LLM."""
        return """You are a helpful pregnancy guidance assistant. Provide accurate, supportive, and safe information about pregnancy. Always recommend consulting healthcare providers for medical concerns. Be empathetic and understanding."""
    
    def _create_user_prompt(self, query: str, context: str) -> str:
        """Create user prompt with context and query."""
        if context:
            return f"""Context information:
{context}

Question: {query}

Please provide a helpful response based on the context above. If the context doesn't contain relevant information, provide general pregnancy guidance while emphasizing the importance of consulting healthcare providers."""
        else:
            return f"""Question: {query}

Please provide helpful pregnancy guidance while emphasizing the importance of consulting healthcare providers for specific medical concerns."""
    
    def generate_response(self, query: str) -> str:
        """
        Generate response using RAG approach.
        
        Args:
            query (str): User query
            
        Returns:
            str: Generated response
        """
        start_time = datetime.now()
        
        try:
            # Find relevant context
            context = self.find_relevant_context(query)
            context_tokens = self.token_manager.count_tokens(context)
            
            # Create prompts
            system_prompt = self._get_system_prompt()
            user_prompt = self._create_user_prompt(query, context)
            
            # Final token check
            total_tokens = self.token_manager.estimate_response_tokens(context, query, system_prompt)
            
            if total_tokens > 5500:  # Leave buffer for model's limit
                logger.warning("Close to token limit, reducing context further")
                context_lines = context.split('\n\n')
                context = '\n\n'.join(context_lines[:2])
                user_prompt = self._create_user_prompt(query, context)
            
            # Generate response
            response = self.client.chat.completions.create(
                model=RAGConfig.LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=RAGConfig.MAX_RESPONSE_TOKENS,
                temperature=0.7
            )
            
            response_text = response.choices[0].message.content
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Log the search if database is available
            if self.db_manager:
                chunks_count = len(context.split('\n\n')) if context else 0
                self.db_manager.log_search(
                    query, response_text, chunks_count, 
                    RAGConfig.SIMILARITY_THRESHOLD, RAGConfig.DEFAULT_TOP_K,
                    int(response_time), context_tokens
                )
            
            return response_text
            
        except Exception as e:
            error_msg = f"I'm sorry, I encountered an error: {str(e)}. Please try again or consult your healthcare provider."
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            if self.db_manager:
                self.db_manager.log_search(
                    query, error_msg, 0, 
                    RAGConfig.SIMILARITY_THRESHOLD, RAGConfig.DEFAULT_TOP_K,
                    int(response_time), 0
                )
            
            logger.error(f"Error generating response: {e}")
            return error_msg
    
    def generate_response_streaming(self, query: str) -> Generator[str, None, None]:
        """
        Generate streaming response for better user experience.
        
        Args:
            query (str): User query
            
        Yields:
            str: Response chunks
        """
        try:
            # Find relevant context
            context = self.find_relevant_context(query)
            context_tokens = self.token_manager.count_tokens(context)
            
            # Create prompts
            system_prompt = self._get_system_prompt()
            user_prompt = self._create_user_prompt(query, context)
            
            # Stream the response
            stream = self.client.chat.completions.create(
                model=RAGConfig.LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=RAGConfig.MAX_RESPONSE_TOKENS,
                temperature=0.7,
                stream=True
            )
            
            full_response = ""
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield content
            
            # Log the complete response
            if self.db_manager:
                chunks_count = len(context.split('\n\n')) if context else 0
                self.db_manager.log_search(
                    query, full_response, chunks_count, 
                    RAGConfig.SIMILARITY_THRESHOLD, RAGConfig.DEFAULT_TOP_K,
                    None, context_tokens
                )
                
        except Exception as e:
            error_msg = f"I'm sorry, I encountered an error: {str(e)}. Please try again or consult your healthcare provider."
            logger.error(f"Error in streaming response: {e}")
            yield error_msg
    
    def get_system_stats(self) -> Dict:
        """Get comprehensive statistics about the RAG system."""
        base_stats = {
            "total_chunks": len(self.knowledge_base),
            "faiss_index_size": self.faiss_index.ntotal if self.faiss_index else 0,
            "embedding_dimension": self.embedding_dim,
            "embedding_model": RAGConfig.EMBEDDING_MODEL,
            "llm_model": RAGConfig.LLM_MODEL,
            "database_connected": self.db_manager is not None and self.db_manager.connection is not None,
            "max_context_tokens": self.token_manager.max_context_tokens,
            "chunk_size": self.chunker.max_chunk_size,
            "chunk_overlap": self.chunker.overlap_size
        }
        
        return base_stats

    def __del__(self):
        """Cleanup when object is destroyed"""
        if hasattr(self, 'db_manager') and self.db_manager:
            self.db_manager.close()
