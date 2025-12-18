import json
import logging
import re
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class BaseAIService:
    """Base Service to interact with DeepSeek AI API"""

    def __init__(self):
        self.api_key = settings.ai_api_key
        self.api_endpoint = settings.ai_api_endpoint
        self.model = settings.ai_model

        # Create OpenAI client configured for DeepSeek API
        # OpenAI SDK has built-in retry logic, connection pooling, and better timeout handling
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=(
                self.api_endpoint.replace("/chat/completions", "")
                if self.api_endpoint
                else None
            ),
            timeout=900.0,  # 15 minutes timeout for long-running requests
            max_retries=2,  # Automatic retry on transient failures
        )

        # Validate configuration
        if not self.api_key:
            logger.warning("AI_API_KEY not configured. AI features will be disabled.")
        if not self.api_endpoint:
            logger.warning(
                "AI_API_ENDPOINT not configured. AI features will be disabled."
            )

    async def close(self):
        """Close the OpenAI client and release resources"""
        await self.client.close()

    def is_configured(self) -> bool:
        """Check if AI service is properly configured"""
        return bool(self.api_key and self.api_endpoint and self.model)

    def _extract_json_from_response(self, text: str) -> Any:
        """
        Extract and parse JSON from AI response that may contain markdown formatting

        Args:
            text: Raw text response from AI that may contain ```json``` markers

        Returns:
            Parsed JSON object (dict or list)

        Raises:
            HTTPException: If JSON parsing fails
        """
        try:
            # Remove markdown code block markers if present
            # Pattern matches ```json\n{...}\n``` or ```\n{...}\n```
            json_pattern = r"```(?:json)?\s*\n?([\s\S]*?)\n?```"
            match = re.search(json_pattern, text)

            if match:
                # Extract JSON from code block
                json_text = match.group(1).strip()
            else:
                # No code block, try to parse the whole text
                json_text = text.strip()

            # Parse the JSON
            return json.loads(json_text)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from AI response: {str(e)}")
            logger.error(f"Response length: {len(text)} characters")
            logger.error(f"Full response: {text}")

            # Check if response seems truncated
            if not text.strip().endswith("}") and not text.strip().endswith("]"):
                logger.error(
                    "Response appears to be truncated - missing closing bracket"
                )
                raise HTTPException(
                    status_code=500,
                    detail="AI response was incomplete. Please try again with fewer questions or increase timeout.",
                )

            raise HTTPException(
                status_code=500, detail=f"Failed to parse AI response as JSON: {str(e)}"
            )

    async def _make_request(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> Dict:
        """
        Make a request to DeepSeek AI API with thinking model support

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Controls randomness (0.0 to 2.0)
            max_tokens: Maximum tokens in response

        Returns:
            API response dictionary

        Raises:
            HTTPException: If API request fails
        """
        if not self.is_configured():
            raise HTTPException(
                status_code=500,
                detail="AI service is not configured. Please check API key and endpoint.",
            )

        # Check if using thinking model (deepseek-reasoner)
        is_thinking_model = "reasoner" in self.model.lower()

        try:
            # Use OpenAI SDK which has built-in retry, timeout, and connection management
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Convert to dict for backward compatibility
            response_data = response.model_dump()

            # Log response structure for debugging
            if is_thinking_model:
                logger.info(f"Using thinking model: {self.model}")
                if "choices" in response_data and len(response_data["choices"]) > 0:
                    message_keys = list(
                        response_data["choices"][0].get("message", {}).keys()
                    )
                    logger.info(f"Response message keys: {message_keys}")

            return response_data

        except Exception as e:
            error_msg = str(e)
            logger.error(f"AI API request error: {error_msg}")

            # Map OpenAI SDK errors to appropriate HTTP exceptions
            if "timeout" in error_msg.lower():
                raise HTTPException(
                    status_code=504, detail="AI service request timed out"
                )
            elif "rate limit" in error_msg.lower():
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            elif (
                "authentication" in error_msg.lower() or "api key" in error_msg.lower()
            ):
                raise HTTPException(status_code=401, detail="Invalid API key")
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to connect to AI service: {error_msg}",
                )

    async def generate_completion(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate a text completion from AI with thinking model support

        Args:
            prompt: The user prompt/question
            system_message: Optional system message to set context
            temperature: Controls randomness (0.0 to 2.0)
            max_tokens: Maximum tokens in response

        Returns:
            Generated text response
        """
        messages = []

        if system_message:
            messages.append({"role": "system", "content": system_message})

        messages.append({"role": "user", "content": prompt})

        response = await self._make_request(
            messages=messages, temperature=temperature, max_tokens=max_tokens
        )

        # Check if using thinking model
        is_thinking_model = "reasoner" in self.model.lower()

        try:
            message = response["choices"][0]["message"]

            # For thinking models, handle reasoning_content separately
            if is_thinking_model and "reasoning_content" in message:
                # reasoning_content contains the internal thought process
                reasoning = message.get("reasoning_content", "")
                # The actual response is still in content
                completion = message.get("content", "")

                # Optionally log reasoning for debugging
                if reasoning:
                    logger.debug(f"Model reasoning: {reasoning[:500]}...")

                return completion.strip() if completion else ""
            else:
                # Standard model response
                completion = message["content"]
                return completion.strip()

        except (KeyError, IndexError) as e:
            logger.error(f"Failed to parse AI response: {str(e)}")
            logger.error(f"Response structure: {response}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to parse AI response. Model: {self.model}, Error: {str(e)}",
            )

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Have a multi-turn conversation with AI with thinking model support

        Args:
            messages: List of message dicts with 'role' and 'content'
                     Roles: 'system', 'user', 'assistant'
            temperature: Controls randomness (0.0 to 2.0)
            max_tokens: Maximum tokens in response

        Returns:
            AI's response message
        """
        response = await self._make_request(
            messages=messages, temperature=temperature, max_tokens=max_tokens
        )

        is_thinking_model = "reasoner" in self.model.lower()

        try:
            message = response["choices"][0]["message"]

            if is_thinking_model and "reasoning_content" in message:
                reasoning = message.get("reasoning_content", "")
                completion = message.get("content", "")

                if reasoning:
                    logger.debug(f"Model reasoning: {reasoning[:500]}...")

                return completion.strip() if completion else ""
            else:
                completion = message["content"]
                return completion.strip()

        except (KeyError, IndexError) as e:
            logger.error(f"Failed to parse AI response: {str(e)}")
            logger.error(f"Response structure: {response}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to parse AI response. Model: {self.model}, Error: {str(e)}",
            )

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ):
        """
        Stream a multi-turn conversation with AI (generator for SSE)

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Controls randomness (0.0 to 2.0)
            max_tokens: Maximum tokens in response

        Yields:
            Chunks of the AI's response message
        """
        if not self.is_configured():
            raise HTTPException(
                status_code=500,
                detail="AI service is not configured. Please check API key and endpoint.",
            )

        try:
            # Create streaming completion
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )

            # Stream chunks
            async for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        yield delta.content

        except Exception as e:
            error_msg = str(e)
            logger.error(f"AI streaming error: {error_msg}")

            if "timeout" in error_msg.lower():
                raise HTTPException(
                    status_code=504, detail="AI service request timed out"
                )
            elif "rate limit" in error_msg.lower():
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to stream from AI service: {error_msg}",
                )
