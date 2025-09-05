import os
import groq
from typing import Dict, List
import logging
from dailyrecommendationAI.config import Config

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        # Initialize Groq client
        try:
            self.groq_client = groq.Groq(api_key=Config.GROQ_API_KEY)
            self.groq_available = True
        except Exception as e:
            logger.error(f"Failed to initialize Groq client: {e}")
            self.groq_client = None
            self.groq_available = False
    
    def is_groq_available(self) -> bool:
        """Check if Groq API is available"""
        return self.groq_available and bool(Config.GROQ_API_KEY)
    
    def get_fallback_recommendation(self, user_data: dict) -> str:
        """Generate fallback recommendation without AI"""
        week = user_data.get('pregnancy_week', 20)
        name = user_data.get('name', 'User')
        preferences = user_data.get('preferences', '').lower()
        
        # Basic recommendations based on pregnancy trimester
        if week <= 12:  # First trimester
            base_rec = f"Hi {name}! Focus on taking prenatal vitamins with folic acid, stay hydrated, and get plenty of rest during this important early stage."
        elif week <= 28:  # Second trimester
            base_rec = f"Hi {name}! Continue with balanced nutrition, gentle exercise like walking or swimming, and monitor your baby's movements."
        else:  # Third trimester
            base_rec = f"Hi {name}! Focus on preparing for birth, practice breathing exercises, and ensure adequate calcium and iron intake."
        
        # Add preference-based advice
        if 'vegetarian' in preferences:
            base_rec += " Make sure to get enough protein from legumes, nuts, and dairy."
        if 'yoga' in preferences:
            base_rec += " Prenatal yoga can help with flexibility and relaxation."
        if 'exercise' in preferences:
            base_rec += " Continue with safe, approved exercises for your pregnancy stage."
        
        return base_rec
    
    def is_context_pregnancy_related(self, context_text: str) -> bool:
        """Check if context is relevant to pregnancy"""
        pregnancy_keywords = ['pregnancy', 'pregnant', 'prenatal', 'maternal', 'fetal', 'trimester', 'nutrition', 'exercise']
        return any(keyword in context_text.lower() for keyword in pregnancy_keywords)
    
    def generate_ai_recommendation(self, user_data: dict, context_chunks: List[str]) -> str:
        """Generate AI recommendation using Groq"""
        if not self.is_groq_available():
            raise Exception("Groq API not available")
        
        # Prepare context
        context = "\n".join(context_chunks[:3])
        
        # Create prompt
        prompt = f"""
        Based on the following medical information about pregnancy, provide a daily recommendation for a pregnant woman.
        
        User Information:
        - Pregnancy Week: {user_data.get('pregnancy_week', 'Not specified')}
        - Name: {user_data.get('name', 'User')}
        - Preferences: {user_data.get('preferences', 'None specified')}
        
        Medical Context:
        {context}
        
        Please provide a personalized daily recommendation that is:
        1. Safe and appropriate for the pregnancy week
        2. Evidence-based
        3. Actionable and practical
        4. Considering the user's preferences
        
        Keep the recommendation concise (2-3 sentences) and friendly in tone.
        """
        
        response = self.groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant providing pregnancy advice based on medical literature."},
                {"role": "user", "content": prompt}
            ],
            model=Config.GROQ_MODEL,
            max_tokens=Config.MAX_TOKENS,
            temperature=Config.TEMPERATURE
        )
        
        return response.choices[0].message.content.strip()
    
    def generate_recommendation(self, user_data: dict, context_chunks: List[str]) -> str:
        """Generate recommendation using AI or fallback"""
        # Always try fallback first if no Groq API key or no relevant context
        if not self.is_groq_available():
            logger.info("No Groq API key available, using fallback")
            return self.get_fallback_recommendation(user_data)
        
        # Check if context is relevant to pregnancy
        context_text = "\n".join(context_chunks[:3]) if context_chunks else ""
        
        if not self.is_context_pregnancy_related(context_text):
            logger.info("Context not relevant to pregnancy, using fallback")
            return self.get_fallback_recommendation(user_data)
        
        try:
            # Generate AI recommendation
            recommendation = self.generate_ai_recommendation(user_data, context_chunks)
            logger.info("Successfully generated AI recommendation")
            return recommendation
            
        except Exception as e:
            logger.error(f"Error generating recommendation with Groq: {e}")
            logger.info("Groq failed, using fallback recommendation")
            return self.get_fallback_recommendation(user_data)
    
    def get_ai_status(self) -> Dict:
        """Get AI service status"""
        return {
            'groq_api_key_configured': bool(Config.GROQ_API_KEY),
            'groq_available': self.groq_available,
            'model': Config.GROQ_MODEL,
            'max_tokens': Config.MAX_TOKENS,
            'temperature': Config.TEMPERATURE
        }