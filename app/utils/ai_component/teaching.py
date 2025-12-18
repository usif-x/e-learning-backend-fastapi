import logging
from typing import Dict, List

from app.utils.prompts import (
    get_teaching_greeting_prompt,
    get_teaching_greeting_system_message,
    get_teaching_response_prompt,
    get_teaching_response_system_message,
)

logger = logging.getLogger(__name__)


class TeachingAssistantMixin:
    async def generate_teaching_greeting(
        self,
        content_preview: str,
        language: str = "en",
        user_name: str = None,
        session_type: str = "asking",
    ) -> str:
        """
        Generate an initial greeting message for a teaching chat session

        Args:
            content_preview: Preview of the content to teach
            language: Language for the greeting (en or ar)
            user_name: Student's full name for personalization (optional)
            session_type: Type of session - 'asking' or 'explaining'

        Returns:
            Greeting message from the AI teacher
        """
        system_message = get_teaching_greeting_system_message(
            language, user_name, session_type
        )
        prompt = get_teaching_greeting_prompt(language, content_preview, session_type)

        return await self.generate_completion(
            prompt=prompt,
            system_message=system_message,
            temperature=0.7,
            max_tokens=500,
        )

    async def generate_teaching_response(
        self,
        user_message: str,
        source_content: str,
        conversation_history: List[Dict[str, str]],
        language: str = "en",
        user_name: str = None,
        session_type: str = "asking",
    ) -> str:
        """
        Generate a teaching response using RAG (Retrieval Augmented Generation)

        Args:
            user_message: The user's current message
            source_content: The source content to teach from
            conversation_history: Previous conversation messages
            language: Language for the response (en or ar)
            user_name: Student's full name for personalization (optional)
            session_type: Type of session - 'asking' or 'explaining'

        Returns:
            AI teacher's response
        """
        # Truncate source content if too long
        max_content_length = 6000
        truncated_content = source_content[:max_content_length]
        if len(source_content) > max_content_length:
            truncated_content += "\n\n[Content truncated...]"

        system_message = get_teaching_response_system_message(
            language, user_name, session_type
        )
        prompt = get_teaching_response_prompt(language, truncated_content, user_message)

        # Build conversation context (last 10 messages to avoid context overflow)
        recent_history = (
            conversation_history[-10:]
            if len(conversation_history) > 10
            else conversation_history
        )

        messages = [{"role": "system", "content": system_message}]

        # Add conversation history
        for msg in recent_history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        # Add current prompt
        messages.append({"role": "user", "content": prompt})

        return await self.chat(
            messages=messages,
            temperature=0.7,
            max_tokens=1000,
        )

    async def generate_teaching_response_stream(
        self,
        user_message: str,
        source_content: str,
        conversation_history: List[Dict[str, str]],
        language: str = "en",
        user_name: str = None,
        session_type: str = "asking",
    ):
        """
        Stream a teaching response using RAG (Retrieval Augmented Generation)

        Args:
            user_message: The user's current message
            source_content: The source content to teach from
            conversation_history: Previous conversation messages
            language: Language for the response (en or ar)
            user_name: Student's full name for personalization (optional)

        Yields:
            Chunks of the AI teacher's response
        """
        # Truncate source content if too long
        max_content_length = 6000
        truncated_content = source_content[:max_content_length]
        if len(source_content) > max_content_length:
            truncated_content += "\n\n[Content truncated...]"

        system_message = get_teaching_response_system_message(
            language, user_name, session_type
        )
        prompt = get_teaching_response_prompt(language, truncated_content, user_message)

        # Build conversation context (last 10 messages to avoid context overflow)
        recent_history = (
            conversation_history[-10:]
            if len(conversation_history) > 10
            else conversation_history
        )

        messages = [{"role": "system", "content": system_message}]

        # Add conversation history
        for msg in recent_history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        # Add current prompt
        messages.append({"role": "user", "content": prompt})

        # Stream the response
        async for chunk in self.chat_stream(
            messages=messages,
            temperature=0.7,
            max_tokens=1000,
        ):
            yield chunk
