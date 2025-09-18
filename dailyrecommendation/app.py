# import groq
# import os
# from dotenv import load_dotenv
# import re
# import fitz
# import numpy as np
# from sentence_transformers import SentenceTransformer
# import pickle
# import hashlib
# import faiss
# import mysql.connector
# from mysql.connector import Error
# from datetime import datetime, timedelta
# import json
# from typing import List, Tuple, Optional
# import nltk
# from nltk.tokenize import sent_tokenize, word_tokenize
# import tiktoken
# from flask import Flask, request, jsonify
# from werkzeug.utils import secure_filename
# import logging

# # Load environment variables
# load_dotenv()

# # Download required NLTK data
# try:
#     nltk.download('punkt', quiet=True)
#     nltk.download('punkt_tab', quiet=True)
# except:
#     pass

# # Initialize Flask app
# app = Flask(__name__)
# app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')

# # Configuration
# UPLOAD_FOLDER = 'uploads'
# VECTOR_DB_PATH = 'vector_db'
# ALLOWED_EXTENSIONS = {'pdf'}
# MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

# # Create directories if they don't exist
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# os.makedirs(VECTOR_DB_PATH, exist_ok=True)

# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# class PregnancyRAGSystem:
#     def __init__(self):
#         # Initialize Groq client
#         try:
#             self.groq_client = groq.Groq(api_key=os.getenv('GROQ_API_KEY'))
#             self.groq_available = True
#         except Exception as e:
#             logger.error(f"Failed to initialize Groq client: {e}")
#             self.groq_client = None
#             self.groq_available = False
        
#         # Initialize sentence transformer
#         self.model = SentenceTransformer('all-MiniLM-L6-v2')
#         self.dimension = 384
        
#         # Initialize FAISS index
#         self.index = faiss.IndexFlatIP(self.dimension)
#         self.document_chunks = []
#         self.chunk_metadata = []
        
#         # Load existing vector database if available
#         self.load_vector_db()
        
#         # Initialize MySQL connection
#         self.init_database()
        
#     def init_database(self):
#         """Initialize MySQL database for user preferences and recommendations history"""
#         try:
#             self.db_connection = mysql.connector.connect(
#                 host=os.getenv('DB_HOST', 'localhost'),
#                 user=os.getenv('DB_USER', 'root'),
#                 password=os.getenv('DB_PASSWORD', ''),
#                 database=os.getenv('DB_NAME', 'pregnancy_rag')
#             )
            
#             cursor = self.db_connection.cursor()
            
#             # Create users table
#             cursor.execute("""
#                 CREATE TABLE IF NOT EXISTS users (
#                     id INT AUTO_INCREMENT PRIMARY KEY,
#                     name VARCHAR(255) NOT NULL,
#                     pregnancy_week INT,
#                     preferences TEXT,
#                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#                 )
#             """)
            
#             # Create recommendations table
#             cursor.execute("""
#                 CREATE TABLE IF NOT EXISTS recommendations (
#                     id INT AUTO_INCREMENT PRIMARY KEY,
#                     user_id INT,
#                     recommendation TEXT,
#                     recommendation_date DATE,
#                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#                     FOREIGN KEY (user_id) REFERENCES users(id)
#                 )
#             """)
            
#             self.db_connection.commit()
#             logger.info("Database initialized successfully")
            
#         except Error as e:
#             logger.error(f"Database initialization error: {e}")
#             self.db_connection = None
    
#     def allowed_file(self, filename):
#         return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    
#     def extract_text_from_pdf(self, pdf_path: str) -> str:
#         """Extract text from PDF using PyMuPDF"""
#         try:
#             doc = fitz.open(pdf_path)
#             text = ""
            
#             for page_num in range(doc.page_count):
#                 page = doc[page_num]
#                 text += page.get_text()
            
#             doc.close()
#             return text
#         except Exception as e:
#             logger.error(f"Error extracting text from PDF: {e}")
#             return ""
    
#     def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
#         """Split text into overlapping chunks"""
#         sentences = sent_tokenize(text)
#         chunks = []
#         current_chunk = ""
        
#         for sentence in sentences:
#             if len(current_chunk) + len(sentence) < chunk_size:
#                 current_chunk += " " + sentence
#             else:
#                 if current_chunk:
#                     chunks.append(current_chunk.strip())
#                 current_chunk = sentence
        
#         if current_chunk:
#             chunks.append(current_chunk.strip())
        
#         return chunks
    
#     def process_pdf(self, pdf_path: str, filename: str) -> bool:
#         """Process PDF and add to vector database"""
#         try:
#             # Extract text
#             text = self.extract_text_from_pdf(pdf_path)
#             if not text.strip():
#                 logger.error("No text extracted from PDF")
#                 return False
            
#             # Chunk text
#             chunks = self.chunk_text(text)
            
#             # Create embeddings
#             embeddings = self.model.encode(chunks)
            
#             # Add to FAISS index
#             self.index.add(embeddings.astype('float32'))
            
#             # Store chunks and metadata
#             for i, chunk in enumerate(chunks):
#                 self.document_chunks.append(chunk)
#                 self.chunk_metadata.append({
#                     'source': filename,
#                     'chunk_id': len(self.document_chunks) - 1,
#                     'text': chunk
#                 })
            
#             # Save vector database
#             self.save_vector_db()
#             logger.info(f"Successfully processed {filename} with {len(chunks)} chunks")
#             return True
            
#         except Exception as e:
#             logger.error(f"Error processing PDF: {e}")
#             return False
    
#     def save_vector_db(self):
#         """Save FAISS index and metadata"""
#         try:
#             faiss.write_index(self.index, os.path.join(VECTOR_DB_PATH, 'faiss_index.bin'))
            
#             with open(os.path.join(VECTOR_DB_PATH, 'chunks.pkl'), 'wb') as f:
#                 pickle.dump(self.document_chunks, f)
            
#             with open(os.path.join(VECTOR_DB_PATH, 'metadata.pkl'), 'wb') as f:
#                 pickle.dump(self.chunk_metadata, f)
                
#             logger.info("Vector database saved successfully")
#         except Exception as e:
#             logger.error(f"Error saving vector database: {e}")
    
#     def load_vector_db(self):
#         """Load existing FAISS index and metadata"""
#         try:
#             index_path = os.path.join(VECTOR_DB_PATH, 'faiss_index.bin')
#             chunks_path = os.path.join(VECTOR_DB_PATH, 'chunks.pkl')
#             metadata_path = os.path.join(VECTOR_DB_PATH, 'metadata.pkl')
            
#             if all(os.path.exists(path) for path in [index_path, chunks_path, metadata_path]):
#                 self.index = faiss.read_index(index_path)
                
#                 with open(chunks_path, 'rb') as f:
#                     self.document_chunks = pickle.load(f)
                
#                 with open(metadata_path, 'rb') as f:
#                     self.chunk_metadata = pickle.load(f)
                
#                 logger.info(f"Loaded vector database with {len(self.document_chunks)} chunks")
            
#         except Exception as e:
#             logger.error(f"Error loading vector database: {e}")
    
#     def search_similar_chunks(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
#         """Search for similar chunks using vector similarity"""
#         try:
#             if self.index.ntotal == 0:
#                 return []
            
#             query_embedding = self.model.encode([query])
#             scores, indices = self.index.search(query_embedding.astype('float32'), top_k)
            
#             results = []
#             for score, idx in zip(scores[0], indices[0]):
#                 if idx < len(self.document_chunks):
#                     results.append((self.document_chunks[idx], float(score)))
            
#             return results
#         except Exception as e:
#             logger.error(f"Error searching similar chunks: {e}")
#             return []
    
#     def get_fallback_recommendation(self, user_data: dict) -> str:
#         """Generate fallback recommendation without AI"""
#         week = user_data.get('pregnancy_week', 20)
#         name = user_data.get('name', 'User')
#         preferences = user_data.get('preferences', '').lower()
        
#         # Basic recommendations based on pregnancy trimester
#         if week <= 12:  # First trimester
#             base_rec = f"Hi {name}! Focus on taking prenatal vitamins with folic acid, stay hydrated, and get plenty of rest during this important early stage."
#         elif week <= 28:  # Second trimester
#             base_rec = f"Hi {name}! Continue with balanced nutrition, gentle exercise like walking or swimming, and monitor your baby's movements."
#         else:  # Third trimester
#             base_rec = f"Hi {name}! Focus on preparing for birth, practice breathing exercises, and ensure adequate calcium and iron intake."
        
#         # Add preference-based advice
#         if 'vegetarian' in preferences:
#             base_rec += " Make sure to get enough protein from legumes, nuts, and dairy."
#         if 'yoga' in preferences:
#             base_rec += " Prenatal yoga can help with flexibility and relaxation."
#         if 'exercise' in preferences:
#             base_rec += " Continue with safe, approved exercises for your pregnancy stage."
        
#         return base_rec
    
#     def generate_recommendation(self, user_data: dict, context_chunks: List[str]) -> str:
#         """Generate recommendation using Groq or fallback"""
#         # Always try fallback first if no Groq API key or no relevant context
#         if not self.groq_available or not os.getenv('GROQ_API_KEY'):
#             logger.info("No Groq API key available, using fallback")
#             return self.get_fallback_recommendation(user_data)
        
#         # Check if context is relevant to pregnancy
#         context_text = "\n".join(context_chunks[:3]) if context_chunks else ""
#         pregnancy_keywords = ['pregnancy', 'pregnant', 'prenatal', 'maternal', 'fetal', 'trimester', 'nutrition', 'exercise']
        
#         if not any(keyword in context_text.lower() for keyword in pregnancy_keywords):
#             logger.info("Context not relevant to pregnancy, using fallback")
#             return self.get_fallback_recommendation(user_data)
        
#         try:
#             # Prepare context
#             context = context_text
            
#             # Create prompt
#             prompt = f"""
#             Based on the following medical information about pregnancy, provide a daily recommendation for a pregnant woman.
            
#             User Information:
#             - Pregnancy Week: {user_data.get('pregnancy_week', 'Not specified')}
#             - Name: {user_data.get('name', 'User')}
#             - Preferences: {user_data.get('preferences', 'None specified')}
            
#             Medical Context:
#             {context}
            
#             Please provide a personalized daily recommendation that is:
#             1. Safe and appropriate for the pregnancy week
#             2. Evidence-based
#             3. Actionable and practical
#             4. Considering the user's preferences
            
#             Keep the recommendation concise (2-3 sentences) and friendly in tone.
#             """
            
#             response = self.groq_client.chat.completions.create(
#                 messages=[
#                     {"role": "system", "content": "You are a helpful AI assistant providing pregnancy advice based on medical literature."},
#                     {"role": "user", "content": prompt}
#                 ],
#                 model="llama3-8b-8192",
#                 max_tokens=200,
#                 temperature=0.7
#             )
            
#             recommendation = response.choices[0].message.content.strip()
#             logger.info("Successfully generated AI recommendation")
#             return recommendation
            
#         except Exception as e:
#             logger.error(f"Error generating recommendation with Groq: {e}")
#             logger.info("Groq failed, using fallback recommendation")
#             return self.get_fallback_recommendation(user_data)
    
#     def get_daily_recommendation(self, user_id: int) -> str:
#         """Get daily recommendation for user"""
#         try:
#             if not self.db_connection:
#                 logger.error("Database connection not available")
#                 return "Database connection not available"
            
#             cursor = self.db_connection.cursor(dictionary=True)
            
#             # Get user data
#             cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
#             user = cursor.fetchone()
            
#             if not user:
#                 logger.error(f"User {user_id} not found")
#                 return "User not found"
            
#             logger.info(f"Processing recommendation for user {user_id}: {user['name']}, week {user['pregnancy_week']}")
            
#             # Check if recommendation already exists for today
#             today = datetime.now().date()
#             cursor.execute(
#                 "SELECT recommendation FROM recommendations WHERE user_id = %s AND recommendation_date = %s",
#                 (user_id, today)
#             )
#             existing_rec = cursor.fetchone()
            
#             if existing_rec:
#                 logger.info(f"Returning existing recommendation for user {user_id}")
#                 return existing_rec['recommendation']
            
#             # Generate new recommendation
#             query = f"pregnancy week {user['pregnancy_week']} daily advice nutrition exercise"
#             logger.info(f"Searching knowledge base with query: {query}")
#             context_chunks = self.search_similar_chunks(query)
            
#             logger.info(f"Found {len(context_chunks)} relevant chunks")
            
#             # Always generate recommendation (either AI or fallback)
#             if context_chunks:
#                 chunk_texts = [chunk[0] for chunk in context_chunks]
#                 logger.info("Attempting to generate AI recommendation with context")
#                 recommendation = self.generate_recommendation(user, chunk_texts)
#             else:
#                 logger.info("No context chunks found, using fallback recommendation")
#                 recommendation = self.get_fallback_recommendation(user)
            
#             # Save recommendation
#             cursor.execute(
#                 "INSERT INTO recommendations (user_id, recommendation, recommendation_date) VALUES (%s, %s, %s)",
#                 (user_id, recommendation, today)
#             )
#             self.db_connection.commit()
            
#             logger.info(f"Recommendation generated and saved for user {user_id}")
#             return recommendation
            
#         except Exception as e:
#             logger.error(f"Error getting daily recommendation: {e}")
#             # Even in case of error, provide fallback
#             try:
#                 if not self.db_connection:
#                     return "Database connection error - please contact support"
                
#                 cursor = self.db_connection.cursor(dictionary=True)
#                 cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
#                 user = cursor.fetchone()
                
#                 if user:
#                     return self.get_fallback_recommendation(user)
#                 else:
#                     return "User not found"
                    
#             except Exception as e2:
#                 logger.error(f"Error in fallback: {e2}")
#                 return "System temporarily unavailable. Please try again later."

# # Initialize RAG system
# rag_system = PregnancyRAGSystem()

# # API Routes

# @app.route('/api/health', methods=['GET'])
# def health_check():
#     """Health check endpoint"""
#     return jsonify({
#         'status': 'healthy',
#         'timestamp': datetime.now().isoformat(),
#         'vector_db_size': len(rag_system.document_chunks),
#         'database_connected': rag_system.db_connection is not None,
#         'groq_available': rag_system.groq_available
#     })

# @app.route('/api/upload-pdf', methods=['POST'])
# def upload_pdf():
#     """Upload and process PDF file"""
#     try:
#         if 'file' not in request.files:
#             return jsonify({'error': 'No file provided'}), 400
        
#         file = request.files['file']
#         if file.filename == '':
#             return jsonify({'error': 'No file selected'}), 400
        
#         if not rag_system.allowed_file(file.filename):
#             return jsonify({'error': 'Invalid file type. Only PDF files are allowed.'}), 400
        
#         filename = secure_filename(file.filename)
#         file_path = os.path.join(UPLOAD_FOLDER, filename)
#         file.save(file_path)
        
#         # Process PDF
#         success = rag_system.process_pdf(file_path, filename)
        
#         # Clean up
#         os.remove(file_path)
        
#         if success:
#             return jsonify({
#                 'message': f'File {filename} uploaded and processed successfully',
#                 'filename': filename,
#                 'vector_db_size': len(rag_system.document_chunks)
#             })
#         else:
#             return jsonify({'error': 'Failed to process PDF file'}), 500
            
#     except Exception as e:
#         logger.error(f"Upload error: {e}")
#         return jsonify({'error': str(e)}), 500

# @app.route('/api/register', methods=['POST'])
# def register_user():
#     """Register a new user"""
#     try:
#         data = request.get_json()
        
#         if not data:
#             return jsonify({'error': 'No JSON data provided'}), 400
        
#         name = data.get('name')
#         pregnancy_week = data.get('pregnancy_week')
#         preferences = data.get('preferences', '')
        
#         if not name or not pregnancy_week:
#             return jsonify({'error': 'Name and pregnancy_week are required'}), 400
        
#         if not isinstance(pregnancy_week, int) or pregnancy_week < 1 or pregnancy_week > 42:
#             return jsonify({'error': 'Pregnancy week must be between 1 and 42'}), 400
        
#         if not rag_system.db_connection:
#             return jsonify({'error': 'Database connection not available'}), 500
        
#         cursor = rag_system.db_connection.cursor()
#         cursor.execute(
#             "INSERT INTO users (name, pregnancy_week, preferences) VALUES (%s, %s, %s)",
#             (name, pregnancy_week, preferences)
#         )
#         rag_system.db_connection.commit()
#         user_id = cursor.lastrowid
        
#         return jsonify({
#             'message': 'User registered successfully',
#             'user_id': user_id,
#             'name': name,
#             'pregnancy_week': pregnancy_week,
#             'preferences': preferences
#         })
        
#     except Exception as e:
#         logger.error(f"Registration error: {e}")
#         return jsonify({'error': str(e)}), 500

# @app.route('/api/user/<int:user_id>', methods=['GET'])
# def get_user(user_id):
#     """Get user information"""
#     try:
#         if not rag_system.db_connection:
#             return jsonify({'error': 'Database connection not available'}), 500
        
#         cursor = rag_system.db_connection.cursor(dictionary=True)
#         cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
#         user = cursor.fetchone()
        
#         if not user:
#             return jsonify({'error': 'User not found'}), 404
        
#         return jsonify({
#             'user_id': user['id'],
#             'name': user['name'],
#             'pregnancy_week': user['pregnancy_week'],
#             'preferences': user['preferences'],
#             'created_at': user['created_at'].isoformat() if user['created_at'] else None
#         })
        
#     except Exception as e:
#         logger.error(f"Get user error: {e}")
#         return jsonify({'error': str(e)}), 500

# @app.route('/api/user/<int:user_id>', methods=['PUT'])
# def update_user(user_id):
#     """Update user information"""
#     try:
#         data = request.get_json()
        
#         if not data:
#             return jsonify({'error': 'No JSON data provided'}), 400
        
#         if not rag_system.db_connection:
#             return jsonify({'error': 'Database connection not available'}), 500
        
#         # Check if user exists
#         cursor = rag_system.db_connection.cursor(dictionary=True)
#         cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
#         user = cursor.fetchone()
        
#         if not user:
#             return jsonify({'error': 'User not found'}), 404
        
#         # Update fields
#         name = data.get('name', user['name'])
#         pregnancy_week = data.get('pregnancy_week', user['pregnancy_week'])
#         preferences = data.get('preferences', user['preferences'])
        
#         if isinstance(pregnancy_week, int) and (pregnancy_week < 1 or pregnancy_week > 42):
#             return jsonify({'error': 'Pregnancy week must be between 1 and 42'}), 400
        
#         cursor.execute(
#             "UPDATE users SET name = %s, pregnancy_week = %s, preferences = %s WHERE id = %s",
#             (name, pregnancy_week, preferences, user_id)
#         )
#         rag_system.db_connection.commit()
        
#         return jsonify({
#             'message': 'User updated successfully',
#             'user_id': user_id,
#             'name': name,
#             'pregnancy_week': pregnancy_week,
#             'preferences': preferences
#         })
        
#     except Exception as e:
#         logger.error(f"Update user error: {e}")
#         return jsonify({'error': str(e)}), 500

# @app.route('/api/recommendation/<int:user_id>', methods=['GET'])
# def get_recommendation(user_id):
#     """Get daily recommendation for user"""
#     try:
#         recommendation = rag_system.get_daily_recommendation(user_id)
        
#         return jsonify({
#             'user_id': user_id,
#             'date': datetime.now().strftime('%Y-%m-%d'),
#             'recommendation': recommendation
#         })
        
#     except Exception as e:
#         logger.error(f"Get recommendation error: {e}")
#         return jsonify({'error': str(e)}), 500

# @app.route('/api/search', methods=['POST'])
# def search_knowledge_base():
#     """Search the knowledge base for relevant information"""
#     try:
#         data = request.get_json()
        
#         if not data:
#             return jsonify({'error': 'No JSON data provided'}), 400
        
#         query = data.get('query')
#         top_k = data.get('top_k', 5)
        
#         if not query:
#             return jsonify({'error': 'Query is required'}), 400
        
#         if not isinstance(top_k, int) or top_k < 1 or top_k > 20:
#             return jsonify({'error': 'top_k must be between 1 and 20'}), 400
        
#         results = rag_system.search_similar_chunks(query, top_k)
        
#         formatted_results = []
#         for chunk, score in results:
#             formatted_results.append({
#                 'text': chunk,
#                 'similarity_score': score
#             })
        
#         return jsonify({
#             'query': query,
#             'results_count': len(formatted_results),
#             'results': formatted_results
#         })
        
#     except Exception as e:
#         logger.error(f"Search error: {e}")
#         return jsonify({'error': str(e)}), 500

# @app.route('/api/recommendations/history/<int:user_id>', methods=['GET'])
# def get_recommendation_history(user_id):
#     """Get recommendation history for user"""
#     try:
#         if not rag_system.db_connection:
#             return jsonify({'error': 'Database connection not available'}), 500
        
#         cursor = rag_system.db_connection.cursor(dictionary=True)
        
#         # Get recent recommendations
#         cursor.execute(
#             """SELECT recommendation, recommendation_date, created_at 
#                FROM recommendations 
#                WHERE user_id = %s 
#                ORDER BY recommendation_date DESC 
#                LIMIT 30""",
#             (user_id,)
#         )
#         recommendations = cursor.fetchall()
        
#         formatted_recommendations = []
#         for rec in recommendations:
#             formatted_recommendations.append({
#                 'date': rec['recommendation_date'].isoformat() if rec['recommendation_date'] else None,
#                 'recommendation': rec['recommendation'],
#                 'created_at': rec['created_at'].isoformat() if rec['created_at'] else None
#             })
        
#         return jsonify({
#             'user_id': user_id,
#             'recommendations_count': len(formatted_recommendations),
#             'recommendations': formatted_recommendations
#         })
        
#     except Exception as e:
#         logger.error(f"Get recommendation history error: {e}")
#         return jsonify({'error': str(e)}), 500

# @app.route('/api/debug/recommendation/<int:user_id>', methods=['GET'])
# def debug_recommendation(user_id):
#     """Debug endpoint to check recommendation generation process"""
#     try:
#         debug_info = {
#             'user_id': user_id,
#             'groq_api_key_configured': bool(os.getenv('GROQ_API_KEY')),
#             'groq_available': rag_system.groq_available,
#             'database_connected': rag_system.db_connection is not None,
#             'vector_db_size': len(rag_system.document_chunks),
#             'timestamp': datetime.now().isoformat()
#         }
        
#         if rag_system.db_connection:
#             cursor = rag_system.db_connection.cursor(dictionary=True)
#             cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
#             user = cursor.fetchone()
            
#             if user:
#                 debug_info['user_found'] = True
#                 debug_info['user_data'] = {
#                     'name': user['name'],
#                     'pregnancy_week': user['pregnancy_week'],
#                     'preferences': user['preferences']
#                 }
                
#                 # Test search
#                 query = f"pregnancy week {user['pregnancy_week']} daily advice nutrition exercise"
#                 context_chunks = rag_system.search_similar_chunks(query)
#                 debug_info['search_results'] = len(context_chunks)
                
#                 if context_chunks:
#                     debug_info['top_result'] = {
#                         'text_preview': context_chunks[0][0][:200] + "..." if len(context_chunks[0][0]) > 200 else context_chunks[0][0],
#                         'similarity_score': context_chunks[0][1]
#                     }
                
#                 # Generate fallback recommendation
#                 fallback_rec = rag_system.get_fallback_recommendation(user)
#                 debug_info['fallback_recommendation'] = fallback_rec
                
#             else:
#                 debug_info['user_found'] = False
        
#         return jsonify(debug_info)
        
#     except Exception as e:
#         logger.error(f"Debug error: {e}")
#         return jsonify({'error': str(e)}), 500

# @app.route('/api/stats', methods=['GET'])
# def get_stats():
#     """Get system statistics"""
#     try:
#         stats = {
#             'vector_database': {
#                 'total_chunks': len(rag_system.document_chunks),
#                 'total_documents': len(set([meta['source'] for meta in rag_system.chunk_metadata]))
#             },
#             'database_status': rag_system.db_connection is not None,
#             'groq_available': rag_system.groq_available
#         }
        
#         if rag_system.db_connection:
#             cursor = rag_system.db_connection.cursor()
            
#             # Count users
#             cursor.execute("SELECT COUNT(*) FROM users")
#             stats['total_users'] = cursor.fetchone()[0]
            
#             # Count recommendations
#             cursor.execute("SELECT COUNT(*) FROM recommendations")
#             stats['total_recommendations'] = cursor.fetchone()[0]
            
#             # Count today's recommendations
#             today = datetime.now().date()
#             cursor.execute("SELECT COUNT(*) FROM recommendations WHERE recommendation_date = %s", (today,))
#             stats['todays_recommendations'] = cursor.fetchone()[0]
        
#         return jsonify(stats)
        
#     except Exception as e:
#         logger.error(f"Get stats error: {e}")
#         return jsonify({'error': str(e)}), 500

# @app.errorhandler(404)
# def not_found(error):
#     return jsonify({'error': 'Endpoint not found'}), 404

# @app.errorhandler(500)
# def internal_error(error):
#     return jsonify({'error': 'Internal server error'}), 500

# if __name__ == '__main__':
#     app.run(debug=True, port=5000)