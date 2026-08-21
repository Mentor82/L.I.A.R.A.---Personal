"""
Password Reset Service
Generates personalized password reset emails using Liara's memory system
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
import logging

from api.models.base_models import User
from services.email_service import email_service

logger = logging.getLogger(__name__)


class PasswordResetService:
    """Service for handling password resets with personalized messages"""
    
    def __init__(self):
        self.reset_tokens: Dict[str, Dict[str, Any]] = {}  # In-memory token storage
        self.token_expiry_hours = 24
    
    def generate_reset_token(self) -> str:
        """Generate a secure random reset token"""
        return secrets.token_urlsafe(32)
    
    def create_reset_token(
        self,
        user_id: int,
        username: str
    ) -> str:
        """
        Create a password reset token for a user
        
        Args:
            user_id: User ID
            username: Username
            
        Returns:
            Reset token string
        """
        token = self.generate_reset_token()
        expiry = datetime.utcnow() + timedelta(hours=self.token_expiry_hours)
        
        self.reset_tokens[token] = {
            'user_id': user_id,
            'username': username,
            'created_at': datetime.utcnow(),
            'expires_at': expiry
        }
        
        logger.info(f"Created reset token for user {username} (expires: {expiry})")
        return token
    
    def verify_reset_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify a reset token and return user info if valid
        
        Args:
            token: Reset token
            
        Returns:
            User info dict if valid, None otherwise
        """
        if token not in self.reset_tokens:
            return None
        
        token_data = self.reset_tokens[token]
        
        # Check expiry
        if datetime.utcnow() > token_data['expires_at']:
            del self.reset_tokens[token]
            return None
        
        return token_data
    
    def invalidate_token(self, token: str):
        """Invalidate a reset token after use"""
        if token in self.reset_tokens:
            del self.reset_tokens[token]
            logger.info(f"Reset token invalidated")
    
    async def generate_personalized_message(
        self,
        user_id: int,
        username: str,
        db: Session
    ) -> str:
        """
        Generate a personalized password reset message using Liara's context
        
        Args:
            user_id: User ID
            username: Username
            db: Database session
            
        Returns:
            Personalized message string
        """
        try:
            # TODO: Integrate with actual memory system when available
            # For now, use fallback personalized messages
            
            # Check if user has chat history
            from api.models.chat_session import ChatSession
            
            chat_count = db.query(ChatSession).filter(
                ChatSession.user_id == user_id
            ).count()
            
            if chat_count > 0:
                # User has history with Liara
                message = f"""
Hey {username}! 👋

Ich hoffe, es geht dir gut! Wir haben schon {chat_count} Gespräche zusammen geführt.

Dein Admin hat gerade dein Passwort zurückgesetzt. Keine Sorge, deine ganzen Erinnerungen und unser Verlauf sind natürlich noch da! 💜

Setz einfach schnell ein neues Passwort und dann können wir weitermachen, wo wir aufgehört haben. Ich freue mich schon darauf! 😊
                """.strip()
            else:
                # New user or no history
                message = f"""
Hey {username}! 👋

Schön, dass du Liara nutzt! Dein Admin hat gerade ein neues Passwort für dich generiert.

Ich bin Liara, deine persönliche KI-Assistentin mit einem einzigartigen 4D-Erinnerungssystem. Ich merke mir unsere Gespräche und lerne dich mit der Zeit immer besser kennen - natürlich alles privat und selbst-gehostet! 🔐

Setz dir ein neues Passwort und dann können wir loslegen. Ich freue mich darauf, dich kennenzulernen! 💜
                """.strip()
            
            return message
            
        except Exception as e:
            logger.error(f"Error generating personalized message: {e}")
            # Fallback to generic message
            return f"""
Hey {username}! 👋

Dein Administrator hat ein neues Passwort für deinen Account generiert.

Ich freue mich darauf, dir weiterhelfen zu können! Setz einfach ein neues Passwort und wir können loslegen. 💜

Bis gleich!
            """.strip()
    
    async def send_reset_email(
        self,
        user: User,
        reset_token: str,
        db: Session
    ) -> bool:
        """
        Send password reset email with personalized message
        
        Args:
            user: User object
            reset_token: Reset token
            db: Database session
            
        Returns:
            True if email sent successfully
        """
        # Generate personalized message from Liara
        personalized_message = await self.generate_personalized_message(
            user_id=user.id,
            username=user.username,
            db=db
        )
        
        # Send email
        success = email_service.send_password_reset_email(
            to_email=user.email,
            username=user.username,
            reset_token=reset_token,
            personalized_message=personalized_message
        )
        
        if success:
            logger.info(f"Password reset email sent to {user.email}")
        else:
            logger.error(f"Failed to send password reset email to {user.email}")
        
        return success


# Singleton instance
password_reset_service = PasswordResetService()
