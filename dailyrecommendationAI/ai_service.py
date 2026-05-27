import groq
import logging
from typing import Dict, List

from dailyrecommendationAI.config import Config

logger = logging.getLogger(__name__)


class AIService:
    def __init__(self):
        try:
            self.groq_client = groq.Groq(api_key=Config.GROQ_API_KEY)
            self.groq_available = True
        except Exception as e:
            logger.error('Failed to initialize Groq client: %s', e)
            self.groq_client = None
            self.groq_available = False

    def is_groq_available(self) -> bool:
        """Check if Groq API is available."""
        return self.groq_available and bool(Config.GROQ_API_KEY)

    def get_fallback_recommendation(self, user_data: dict) -> str:
        """Generate fallback recommendation without AI."""
        week = user_data.get('pregnancy_week', 20)
        name = user_data.get('name', 'User')
        preferences = str(user_data.get('preferences', '')).lower()

        if week <= 12:
            base_rec = (
                f'Hi {name}! Focus on taking prenatal vitamins with folic acid, '
                'stay hydrated, and get plenty of rest during this important early stage.'
            )
        elif week <= 28:
            base_rec = (
                f'Hi {name}! Continue with balanced nutrition, gentle exercise like walking '
                'or swimming, and monitor your baby\'s movements.'
            )
        else:
            base_rec = (
                f'Hi {name}! Focus on preparing for birth, practice breathing exercises, '
                'and ensure adequate calcium and iron intake.'
            )

        if 'vegetarian' in preferences:
            base_rec += ' Make sure to get enough protein from legumes, nuts, and dairy.'
        if 'yoga' in preferences:
            base_rec += ' Prenatal yoga can help with flexibility and relaxation.'
        if 'exercise' in preferences:
            base_rec += ' Continue with safe, approved exercises for your pregnancy stage.'

        return base_rec

    def is_context_pregnancy_related(self, context_text: str) -> bool:
        """Check if context is relevant to pregnancy."""
        pregnancy_keywords = [
            'pregnancy', 'pregnant', 'prenatal', 'maternal',
            'fetal', 'trimester', 'nutrition', 'exercise'
        ]
        text = context_text.lower()
        return any(keyword in text for keyword in pregnancy_keywords)

    def generate_ai_recommendation(self, user_data: dict, context_chunks: List[str]) -> str:
        """Generate AI recommendation using Groq."""
        if not self.is_groq_available():
            raise Exception('Groq API not available')

        context = '\n'.join(context_chunks[:3])
        prompt = f"""
Based on the following pregnancy-related medical information, provide a daily recommendation.

User Information:
- Pregnancy Week: {user_data.get('pregnancy_week', 'Not specified')}
- Name: {user_data.get('name', 'User')}
- Preferences: {user_data.get('preferences', 'None specified')}

Medical Context:
{context}

Rules:
- Return ONLY 3 to 6 checklist bullet points.
- Each bullet must start with "- ".
- Each bullet must be actionable for today.
- Each bullet must be under 18 words.
- Keep the advice safe and pregnancy-appropriate.
- Consider the user's preferences.
- No greeting, no heading, no intro, no paragraph.

Do not include text like "Hi {user_data.get('name', 'User')}" or "here's a recommendation".
""".strip()

        response = self.groq_client.chat.completions.create(
            messages=[
                {
                    'role': 'system',
                    'content': 'You are a helpful AI assistant providing pregnancy advice based on medical literature.'
                },
                {'role': 'user', 'content': prompt}
            ],
            model=Config.GROQ_MODEL,
            max_tokens=Config.MAX_TOKENS,
            temperature=Config.TEMPERATURE
        )

        return response.choices[0].message.content.strip()

    def generate_recommendation(self, user_data: dict, context_chunks: List[str]) -> str:
        """Generate recommendation using AI or fallback."""
        if not self.is_groq_available():
            logger.info('No Groq API key available, using fallback')
            return self.get_fallback_recommendation(user_data)

        context_text = '\n'.join(context_chunks[:3]) if context_chunks else ''
        logger.debug('Context text for relevance check: %s', context_text)

        if not self.is_context_pregnancy_related(context_text):
            logger.info('Context not relevant to pregnancy, using fallback')
            return self.get_fallback_recommendation(user_data)

        try:
            recommendation = self.generate_ai_recommendation(user_data, context_chunks)
            logger.info('Successfully generated AI recommendation')
            return recommendation
        except Exception as e:
            logger.error('Error generating recommendation with Groq: %s', e)
            logger.info('Groq failed, using fallback recommendation')
            return self.get_fallback_recommendation(user_data)

    def get_ai_status(self) -> Dict:
        """Get AI service status."""
        return {
            'groq_api_key_configured': bool(Config.GROQ_API_KEY),
            'groq_available': self.groq_available,
            'model': Config.GROQ_MODEL,
            'max_tokens': Config.MAX_TOKENS,
            'temperature': Config.TEMPERATURE,
        }
