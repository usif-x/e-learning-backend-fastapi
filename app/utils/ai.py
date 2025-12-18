# app/utils/ai.py
"""
AI utility for connecting with DeepSeek AI API
Used for generating questions, content, and other educational materials
Enhanced with improved prompts and thinking model support
"""

import json
import logging
import os
import re
import tempfile
from io import BytesIO
from typing import Any, Dict, List, Optional

import fitz  # PyMuPDF
import pytesseract
from fastapi import HTTPException, UploadFile
from openai import AsyncOpenAI
from PIL import Image

from app.core.config import settings
from app.utils.prompts import (
    ENHANCED_SYSTEM_MESSAGE,
    get_difficulty_guide,
    get_essay_prompt,
    get_explain_concept_prompt,
    get_explain_concept_system_message,
    get_explanation_prompt,
    get_explanation_system_message,
    get_mixed_prompt,
    get_multiple_choice_prompt,
    get_notes_context,
    get_pdf_difficulty_guide,
    get_pdf_essay_prompt,
    get_pdf_mcq_prompt,
    get_pdf_mixed_prompt,
    get_pdf_notes_context,
    get_pdf_path_difficulty_guide,
    get_pdf_path_essay_prompt,
    get_pdf_path_mcq_prompt,
    get_pdf_path_mixed_prompt,
    get_pdf_path_notes_context,
    get_pdf_path_previous_questions_context,
    get_pdf_path_true_false_prompt,
    get_pdf_previous_questions_context,
    get_pdf_true_false_prompt,
    get_previous_questions_context,
    get_summarize_prompt,
    get_summarize_system_message,
    get_teaching_greeting_prompt,
    get_teaching_greeting_system_message,
    get_teaching_response_prompt,
    get_teaching_response_system_message,
    get_topic_explanation_prompt,
    get_topic_explanation_system_message,
    get_true_false_prompt,
)

logger = logging.getLogger(__name__)


# ============================================
# ENHANCED SYSTEM MESSAGE
# ============================================

# Imported from app.utils.prompts


class AIService:
    """Service to interact with DeepSeek AI API"""

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

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

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

    async def generate_questions(
        self,
        topic: str,
        difficulty: str = "medium",
        count: int = 5,
        question_type: str = "multiple_choice",
        notes: Optional[str] = None,
        previous_questions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Generate educational questions for a topic with improved prompts

        Args:
            topic: The subject/topic for questions
            difficulty: Question difficulty (easy, medium, hard)
            count: Number of questions to generate
            question_type: Type of questions (multiple_choice, true_false, essay, mixed)
            notes: Optional instructions for question generation
            previous_questions: Optional list of previously generated question texts to avoid duplicates

        Returns:
            Dictionary with parsed questions
        """
        # Calculate exact distribution
        standard_count = int(count * 0.7)
        critical_count = int(count * 0.2)
        linking_count = max(
            1, count - standard_count - critical_count
        )  # Ensure we hit exact count

        # Difficulty guidelines
        current_difficulty_guide = get_difficulty_guide(difficulty)

        # Build previous questions context with stronger anti-duplication
        previous_context = get_previous_questions_context(previous_questions)

        # Build notes context
        notes_context = get_notes_context(notes)

        # Question type specific prompts
        if question_type == "multiple_choice":
            prompt = get_multiple_choice_prompt(
                count,
                topic,
                current_difficulty_guide,
                standard_count,
                critical_count,
                linking_count,
                notes_context,
                previous_context,
            )

        elif question_type == "true_false":
            prompt = get_true_false_prompt(
                count,
                topic,
                current_difficulty_guide,
                standard_count,
                critical_count,
                linking_count,
                notes_context,
                previous_context,
            )

        elif question_type == "essay":
            prompt = get_essay_prompt(
                count,
                topic,
                current_difficulty_guide,
                standard_count,
                critical_count,
                linking_count,
                notes_context,
                previous_context,
            )

        else:  # mixed
            mcq_count = int(count * 0.65)
            tf_count = count - mcq_count

            prompt = get_mixed_prompt(
                count,
                topic,
                current_difficulty_guide,
                standard_count,
                critical_count,
                linking_count,
                mcq_count,
                tf_count,
                notes_context,
                previous_context,
            )

        response_text = await self.generate_completion(
            prompt=prompt,
            system_message=ENHANCED_SYSTEM_MESSAGE,
            temperature=0.85,  # Slightly lower for more consistency
            max_tokens=8000,
        )

        return self._extract_json_from_response(response_text)

    async def summarize_content(
        self, content: str, max_length: Optional[int] = None
    ) -> str:
        """
        Summarize educational content

        Args:
            content: The content to summarize
            max_length: Optional maximum length of summary

        Returns:
            Summarized content
        """
        system_message = get_summarize_system_message()

        prompt = get_summarize_prompt(content, max_length)

        return await self.generate_completion(
            prompt=prompt, system_message=system_message, temperature=0.5
        )

    async def explain_concept(
        self, concept: str, level: str = "beginner", language: str = "en"
    ) -> str:
        """
        Explain a concept at different complexity levels and languages

        Args:
            concept: The concept to explain
            level: Complexity level (beginner, intermediate, advanced)
            language: Language for explanation (en for English, ar for Arabic/Egypt)

        Returns:
            Explanation text in requested language
        """
        system_message = get_explain_concept_system_message(level, language)

        prompt = get_explain_concept_prompt(concept, level)

        return await self.generate_completion(
            prompt=prompt, system_message=system_message, temperature=0.7
        )

    async def extract_text_from_pdf(self, file: UploadFile) -> str:
        """
        Extract text content from a PDF file with OCR support for image-based PDFs

        Args:
            file: Uploaded PDF file

        Returns:
            Extracted text content

        Raises:
            HTTPException: If PDF processing fails
        """
        try:
            contents = await file.read()
            # Open PDF from bytes using PyMuPDF
            doc = fitz.open(stream=contents, filetype="pdf")

            text_content = []
            pages_with_no_text = []

            # First pass: Try to extract text using PyMuPDF
            for page_num, page in enumerate(doc, 1):
                try:
                    text = page.get_text()
                    if text and text.strip():
                        text_content.append(f"--- Page {page_num} ---\n{text}")
                    else:
                        pages_with_no_text.append(page_num)
                except Exception as e:
                    logger.warning(
                        f"Failed to extract text from page {page_num}: {str(e)}"
                    )
                    pages_with_no_text.append(page_num)

            # Also consider pages with very short text (<5 words) as OCR candidates
            # Helper to extract word count from a page string
            def get_page_word_count(page_str: str) -> int:
                # Extract content after the header line
                lines = page_str.split("\n", 1)
                content = lines[1] if len(lines) > 1 else ""
                return len(content.split())

            pages_with_short_text = [
                int(re.search(r"Page (\d+)", p).group(1))
                for p in text_content
                if get_page_word_count(p) < 5
            ]

            pages_needing_ocr = sorted(
                set(pages_with_no_text) | set(pages_with_short_text)
            )

            # Second pass: Use OCR for pages with no text or very short text
            if pages_needing_ocr:
                logger.info(f"Using OCR for pages: {pages_needing_ocr}")
                try:
                    for page_num in pages_needing_ocr:
                        try:
                            # Load page (0-indexed)
                            page = doc.load_page(page_num - 1)
                            # Get image from page
                            pix = page.get_pixmap(
                                matrix=fitz.Matrix(2, 2)
                            )  # 2x zoom for better OCR
                            img_data = pix.tobytes("png")
                            image = Image.open(BytesIO(img_data))

                            # Perform OCR on the image
                            ocr_text = pytesseract.image_to_string(
                                image, lang="eng+ara"
                            )
                            if ocr_text and ocr_text.strip():
                                ocr_text = ocr_text.strip()
                                # Prefer OCR if it yields >=5 words
                                if len(ocr_text.split()) >= 5:
                                    # Check if we need to replace existing short-text entry
                                    replaced = False
                                    for idx, entry in enumerate(text_content):
                                        match = re.search(r"Page (\d+)", entry)
                                        if match and int(match.group(1)) == page_num:
                                            text_content[idx] = (
                                                f"--- Page {page_num} (OCR) ---\n{ocr_text}"
                                            )
                                            replaced = True
                                            logger.info(
                                                f"Replaced short text on page {page_num} with OCR content"
                                            )
                                            break
                                    if not replaced:
                                        text_content.append(
                                            f"--- Page {page_num} (OCR) ---\n{ocr_text}"
                                        )
                                        logger.info(
                                            f"Successfully extracted OCR text from page {page_num}"
                                        )
                        except Exception as e:
                            logger.warning(f"OCR failed for page {page_num}: {str(e)}")
                            continue
                except Exception as e:
                    logger.warning(f"Failed to convert PDF to images for OCR: {str(e)}")

            if not text_content:
                raise HTTPException(
                    status_code=400,
                    detail="No text content found in PDF. The file may be empty or OCR failed to extract text.",
                )

            # Sort by page number to maintain order
            text_content.sort(key=lambda x: int(re.search(r"Page (\d+)", x).group(1)))

            return "\n\n".join(text_content)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to process PDF: {str(e)}")
            raise HTTPException(
                status_code=400, detail=f"Failed to process PDF file: {str(e)}"
            )
        finally:
            file.seek(0)

    async def extract_text_from_pdf_path(self, pdf_path: str) -> str:
        """
        Extract text content from a PDF file path with OCR support for image-based PDFs

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Extracted text content

        Raises:
            HTTPException: If PDF processing fails
        """
        try:
            # Open PDF directly from path using PyMuPDF
            doc = fitz.open(pdf_path)

            text_content = []
            pages_with_no_text = []

            # First pass: Try to extract text using PyMuPDF
            for page_num, page in enumerate(doc, 1):
                try:
                    text = page.get_text()
                    if text and text.strip():
                        text_content.append(f"--- Page {page_num} ---\n{text}")
                    else:
                        pages_with_no_text.append(page_num)
                except Exception as e:
                    logger.warning(
                        f"Failed to extract text from page {page_num}: {str(e)}"
                    )
                    pages_with_no_text.append(page_num)

            # Also consider pages with very short text (<5 words) as OCR candidates
            def get_page_word_count(page_str: str) -> int:
                lines = page_str.split("\n", 1)
                content = lines[1] if len(lines) > 1 else ""
                return len(content.split())

            pages_with_short_text = [
                int(re.search(r"Page (\d+)", p).group(1))
                for p in text_content
                if get_page_word_count(p) < 5
            ]

            pages_needing_ocr = sorted(
                set(pages_with_no_text) | set(pages_with_short_text)
            )

            # Second pass: Use OCR for pages with no text or very short text
            if pages_needing_ocr:
                logger.info(f"Using OCR for pages: {pages_needing_ocr}")
                try:
                    for page_num in pages_needing_ocr:
                        try:
                            # Load page (0-indexed)
                            page = doc.load_page(page_num - 1)
                            # Get image from page
                            pix = page.get_pixmap(
                                matrix=fitz.Matrix(2, 2)
                            )  # 2x zoom for better OCR
                            img_data = pix.tobytes("png")
                            image = Image.open(BytesIO(img_data))

                            # Perform OCR on the image
                            ocr_text = pytesseract.image_to_string(
                                image, lang="eng+ara"
                            )
                            if ocr_text and ocr_text.strip():
                                ocr_text = ocr_text.strip()
                                if len(ocr_text.split()) >= 5:
                                    replaced = False
                                    for idx, entry in enumerate(text_content):
                                        match = re.search(r"Page (\d+)", entry)
                                        if match and int(match.group(1)) == page_num:
                                            text_content[idx] = (
                                                f"--- Page {page_num} (OCR) ---\n{ocr_text}"
                                            )
                                            replaced = True
                                            logger.info(
                                                f"Replaced short text on page {page_num} with OCR content"
                                            )
                                            break
                                    if not replaced:
                                        text_content.append(
                                            f"--- Page {page_num} (OCR) ---\n{ocr_text}"
                                        )
                                        logger.info(
                                            f"Successfully extracted OCR text from page {page_num}"
                                        )
                        except Exception as e:
                            logger.warning(f"OCR failed for page {page_num}: {str(e)}")
                            continue
                except Exception as e:
                    logger.warning(f"Failed to convert PDF to images for OCR: {str(e)}")

            if not text_content:
                raise HTTPException(
                    status_code=400,
                    detail="No text content found in PDF. The file may be empty or OCR failed to extract text.",
                )

            # Sort by page number to maintain order
            text_content.sort(key=lambda x: int(re.search(r"Page (\d+)", x).group(1)))

            return "\n\n".join(text_content)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to process PDF: {str(e)}")
            raise HTTPException(
                status_code=400, detail=f"Failed to process PDF file: {str(e)}"
            )

    async def generate_questions_from_pdf(
        self,
        file: UploadFile,
        difficulty: str = "medium",
        count: int = 5,
        question_type: str = "multiple_choice",
        notes: Optional[str] = None,
        previous_questions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Extract content from PDF and generate questions with improved prompts

        Args:
            file: Uploaded PDF file
            difficulty: Question difficulty (easy, medium, hard)
            count: Number of questions to generate
            question_type: Type of questions
            notes: Optional instructions for question generation
            previous_questions: Optional list of previously generated questions

        Returns:
            Dictionary with parsed questions
        """
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="File must be a PDF")

        pdf_content = await self.extract_text_from_pdf(file)

        max_content_length = 8000  # Increased for better context
        if len(pdf_content) > max_content_length:
            pdf_content = (
                pdf_content[:max_content_length] + "\n\n[Content truncated...]"
            )

        # Calculate exact distribution
        standard_count = int(count * 0.7)
        critical_count = int(count * 0.2)
        linking_count = max(1, count - standard_count - critical_count)

        # Difficulty guidelines
        current_difficulty_guide = get_pdf_difficulty_guide(difficulty)

        # Build previous questions context
        previous_context = get_pdf_previous_questions_context(previous_questions)

        notes_context = get_pdf_notes_context(notes)

        # ==========================================
        # PROMPT GENERATION BASED ON TYPE
        # ==========================================

        if question_type == "essay":
            prompt = get_pdf_essay_prompt(
                count,
                current_difficulty_guide,
                standard_count,
                critical_count,
                linking_count,
                notes_context,
                previous_context,
                pdf_content,
            )

        elif question_type == "mixed":
            mcq_count = int(count * 0.65)
            tf_count = count - mcq_count

            prompt = get_pdf_mixed_prompt(
                count,
                current_difficulty_guide,
                standard_count,
                critical_count,
                linking_count,
                mcq_count,
                tf_count,
                notes_context,
                previous_context,
                pdf_content,
            )

        elif question_type == "true_false":
            prompt = get_pdf_true_false_prompt(
                count,
                current_difficulty_guide,
                standard_count,
                critical_count,
                linking_count,
                notes_context,
                previous_context,
                pdf_content,
            )

        else:  # multiple_choice
            prompt = get_pdf_mcq_prompt(
                count,
                current_difficulty_guide,
                standard_count,
                critical_count,
                linking_count,
                notes_context,
                previous_context,
                pdf_content,
            )

        response_text = await self.generate_completion(
            prompt=prompt,
            system_message=ENHANCED_SYSTEM_MESSAGE,
            temperature=0.7,  # Lower temperature for content fidelity
            max_tokens=8000,
        )

        return self._extract_json_from_response(response_text)

    async def generate_questions_from_pdf_path(
        self,
        pdf_path: str,
        difficulty: str = "medium",
        count: int = 5,
        question_type: str = "multiple_choice",
        notes: Optional[str] = None,
        previous_questions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Extract content from PDF path and generate questions
        Useful for background tasks or admin scripts where file is already saved.

        Args:
            pdf_path: Path to the PDF file
            difficulty: Question difficulty
            count: Number of questions
            question_type: Type of questions
            notes: Optional instructions
            previous_questions: Optional list of previous questions

        Returns:
            Dictionary with parsed questions
        """
        # Extract text using the path-based helper
        pdf_content = await self.extract_text_from_pdf_path(pdf_path)

        # Truncate content if necessary to fit context window
        max_content_length = 8000
        if len(pdf_content) > max_content_length:
            pdf_content = (
                pdf_content[:max_content_length] + "\n\n[Content truncated...]"
            )

        # Reuse the logic from generate_questions_from_pdf by calling it?
        # No, UploadFile is different from string content. We must replicate the prompt logic
        # or refactor. For safety and speed, we replicate the prompt construction.

        standard_count = int(count * 0.7)
        critical_count = int(count * 0.2)
        linking_count = max(1, count - standard_count - critical_count)

        difficulty_guide = {
            "easy": "EASY: Straightforward recall from text.",
            "medium": "MEDIUM: Understanding and application of text concepts.",
            "hard": "HARD: Analysis and synthesis of text information.",
        }
        current_difficulty_guide = get_pdf_path_difficulty_guide(difficulty)

        previous_context = get_pdf_path_previous_questions_context(previous_questions)

        notes_context = get_pdf_path_notes_context(notes)

        # Select Prompt
        if question_type == "essay":
            prompt = get_pdf_path_essay_prompt(
                count,
                current_difficulty_guide,
                standard_count,
                critical_count,
                linking_count,
                notes_context,
                previous_context,
                pdf_content,
            )
        elif question_type == "true_false":
            prompt = get_pdf_path_true_false_prompt(
                count,
                current_difficulty_guide,
                standard_count,
                critical_count,
                linking_count,
                notes_context,
                previous_context,
                pdf_content,
            )
        elif question_type == "mixed":
            prompt = get_pdf_path_mixed_prompt(
                count,
                current_difficulty_guide,
                standard_count,
                critical_count,
                linking_count,
                notes_context,
                previous_context,
                pdf_content,
            )
        else:  # Multiple Choice
            prompt = get_pdf_path_mcq_prompt(
                count,
                current_difficulty_guide,
                standard_count,
                critical_count,
                linking_count,
                notes_context,
                previous_context,
                pdf_content,
            )

        response_text = await self.generate_completion(
            prompt=prompt,
            system_message=ENHANCED_SYSTEM_MESSAGE,
            temperature=0.7,
            max_tokens=8000,
        )

        return self._extract_json_from_response(response_text)

    async def explain_pdf_content(
        self,
        file: UploadFile,
        include_examples: bool = True,
        detailed_explanation: bool = True,
    ) -> Dict[str, Any]:
        """
        Extract and explain PDF content page by page in Egyptian Arabic

        Args:
            file: Uploaded PDF file
            include_examples: Whether to include examples in explanations
            detailed_explanation: Whether to provide detailed explanations

        Returns:
            Dictionary with page explanations in JSON format
        """
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="File must be a PDF")

        # Extract text from each page with OCR support
        contents = await file.read()
        # Use PyMuPDF
        doc = fitz.open(stream=contents, filetype="pdf")

        pages_content = []
        pages_with_no_text = []

        # First pass: Try to extract text using PyMuPDF
        for page_num, page in enumerate(doc, 1):
            try:
                text = page.get_text()
                if text and text.strip():
                    pages_content.append(
                        {"page_number": page_num, "content": text.strip()}
                    )
                else:
                    pages_with_no_text.append(page_num)
            except Exception as e:
                logger.warning(f"Failed to extract text from page {page_num}: {str(e)}")
                pages_with_no_text.append(page_num)

        # Second pass: Use OCR for pages with no text (likely image-based)
        # Also attempt OCR for pages that have very short extracted text
        # (e.g., a title) because the rest of the page might be an image.
        pages_with_short_text = [
            p["page_number"] for p in pages_content if len(p["content"].split()) < 5
        ]

        pages_needing_ocr = sorted(set(pages_with_no_text) | set(pages_with_short_text))

        if pages_needing_ocr:
            logger.info(f"Using OCR for pages: {pages_needing_ocr}")
            try:
                for page_num in pages_needing_ocr:
                    try:
                        # Load page (0-indexed)
                        page = doc.load_page(page_num - 1)
                        # Get image from page
                        pix = page.get_pixmap(
                            matrix=fitz.Matrix(2, 2)
                        )  # 2x zoom for better OCR
                        img_data = pix.tobytes("png")
                        image = Image.open(BytesIO(img_data))

                        # Perform OCR on the image
                        ocr_text = pytesseract.image_to_string(image, lang="eng+ara")
                        if ocr_text and ocr_text.strip():
                            ocr_text = ocr_text.strip()
                            # Prefer OCR text only if it yields substantive content
                            if len(ocr_text.split()) >= 5:
                                replaced = False
                                for idx, p in enumerate(pages_content):
                                    if p["page_number"] == page_num:
                                        pages_content[idx]["content"] = ocr_text
                                        replaced = True
                                        logger.info(
                                            f"Replaced short text on page {page_num} with OCR content"
                                        )
                                        break
                                if not replaced:
                                    pages_content.append(
                                        {
                                            "page_number": page_num,
                                            "content": ocr_text,
                                        }
                                    )
                            else:
                                logger.info(
                                    f"OCR on page {page_num} returned only {len(ocr_text.split())} words; keeping original text if present"
                                )
                    except Exception as e:
                        logger.warning(f"OCR failed for page {page_num}: {str(e)}")
                        continue
            except Exception as e:
                logger.warning(f"Failed to convert PDF to images for OCR: {str(e)}")

        # Sort pages by page number to maintain order
        pages_content.sort(key=lambda x: x["page_number"])

        if not pages_content:
            raise HTTPException(
                status_code=400,
                detail="No text content found in PDF. The file may be empty or contain only images.",
            )

        # Filter out non-content pages (intro, conclusion, thank you pages, etc.)
        filtered_pages = []
        skip_keywords = [
            "thank you",
            "thanks",
            "شكراً",
            "شكر",
            "any questions",
            "أي أسئلة",
            "prof.",
            "professor",
            "dr.",
            "doctor",
            "د.",
            "دكتور",
            "بروفيسور",
            "introduction",
            "مقدمة",
            "by prof",
            "بواسطة",
            "author",
            "مؤلف",
            "references",
            "مراجع",
            "bibliography",
            "قائمة المراجع",
            "acknowledgments",
            "شكر وتقدير",
            "table of contents",
            "فهرس",
            "index",
            "دليل",
            "glossary",
            "قاموس مصطلحات",
        ]

        for page_data in pages_content:
            content = page_data["content"].lower()
            page_num = page_data["page_number"]

            # Skip pages that are too short (less than 5 words)
            if len(content.split()) < 5:
                logger.info(
                    f"Skipping page {page_num}: too short ({len(content.split())} words)"
                )
                continue

            # Skip pages containing skip keywords
            should_skip = False
            for keyword in skip_keywords:
                if keyword.lower() in content:
                    logger.info(
                        f"Skipping page {page_num}: contains keyword '{keyword}'"
                    )
                    should_skip = True
                    break

            if should_skip:
                continue

            # Skip first page if it looks like a title page
            if page_num == 1 and len(content.split()) < 50:
                logger.info(f"Skipping page {page_num}: likely title page")
                continue

            # Skip last page if it looks like conclusion/thanks
            if page_num == len(pages_content) and len(content.split()) < 30:
                logger.info(f"Skipping page {page_num}: likely conclusion page")
                continue

            filtered_pages.append(page_data)

        if not filtered_pages:
            raise HTTPException(
                status_code=400,
                detail="No meaningful content pages found in PDF. All pages appear to be introductory, conclusion, or reference pages.",
            )

        # Create system message for PDF explanation
        explanation_system_message = get_explanation_system_message()

        # Process pages in batches to avoid timeout on large PDFs
        # Each batch will be sent as one request
        BATCH_SIZE = (
            10  # Process 10 pages per request - optimized for better throughput
        )
        MAX_BATCH_CONTENT_LENGTH = 8000  # Max chars per batch (smaller for reliability)

        explained_pages = []

        # Split filtered_pages into batches
        for batch_start in range(0, len(filtered_pages), BATCH_SIZE):
            batch_pages = filtered_pages[batch_start : batch_start + BATCH_SIZE]

            # Merge batch content
            merged_content_parts = []
            for page_data in batch_pages:
                page_num = page_data["page_number"]
                content = page_data["content"]
                merged_content_parts.append(f"━━━ صفحة {page_num} ━━━\n{content}")

            merged_content = "\n\n".join(merged_content_parts)

            # Truncate if too long
            if len(merged_content) > MAX_BATCH_CONTENT_LENGTH:
                merged_content = (
                    merged_content[:MAX_BATCH_CONTENT_LENGTH]
                    + "\n\n[Content truncated...]"
                )

            # Build prompt for this batch
            examples_instruction = (
                " وخلي الشرح يشمل أمثلة عملية" if include_examples else ""
            )
            detail_instruction = (
                " شرح مفصل وواضح" if detailed_explanation else "شرح مختصر"
            )

            page_numbers = [p["page_number"] for p in batch_pages]

            prompt = get_explanation_prompt(
                detail_instruction, examples_instruction, merged_content, page_numbers
            )

            # Try with retries
            max_retries = 2
            batch_explained = None

            for attempt in range(max_retries + 1):
                try:
                    response_text = await self.generate_completion(
                        prompt=prompt,
                        system_message=explanation_system_message,
                        temperature=0.7,
                        max_tokens=8000,  # Reduced for faster response
                    )

                    # Parse the JSON response
                    result = self._extract_json_from_response(response_text)

                    if isinstance(result, dict) and "pages" in result:
                        batch_explained = result["pages"]
                    else:
                        # Fallback: treat as single explanation for batch
                        batch_explained = [
                            {
                                "page_number": p["page_number"],
                                "explanation": str(result),
                            }
                            for p in batch_pages
                        ]
                    break  # Success, exit retry loop

                except Exception as e:
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} failed for pages {page_numbers}: {str(e)}"
                    )
                    if attempt < max_retries:
                        # Wait 3 seconds before retrying to give API server time to recover
                        import asyncio

                        await asyncio.sleep(3)
                    if attempt == max_retries:
                        # All retries failed
                        logger.error(
                            f"All retries failed for pages {page_numbers}: {str(e)}"
                        )
                        batch_explained = [
                            {
                                "page_number": p["page_number"],
                                "explanation": "معلش، حصل مشكلة في الشرح. حاول تاني.",
                            }
                            for p in batch_pages
                        ]

            if batch_explained:
                explained_pages.extend(batch_explained)

        # Reset file pointer
        await file.seek(0)

        return {
            "pages": explained_pages,
            "total_pages": len(explained_pages),
            "filtered_pages": len(pages_content) - len(filtered_pages),
            "language": "Egyptian Arabic",
            "medical_terms_preserved": True,
        }

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

        # Use "asking" session type for streaming response as it implies interactive conversation
        session_type = "asking"
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

    async def explain_topic_content(
        self,
        topic: str,
        include_examples: bool = True,
        detailed_explanation: bool = True,
        subject_breakdown: bool = True,
    ) -> Dict[str, Any]:
        """
        Explain a medical topic comprehensively in Egyptian Arabic, organized by subjects

        Args:
            topic: The medical topic to explain
            include_examples: Whether to include examples in explanations
            detailed_explanation: Whether to provide detailed explanations
            subject_breakdown: Whether to break down into sub-subjects

        Returns:
            Dictionary with topic explanations organized by subjects
        """
        # Create system message for topic explanation
        explanation_system_message = get_topic_explanation_system_message()

        # Build explanation prompt
        examples_instruction = (
            " وخلي الشرح يشمل أمثلة عملية كتير" if include_examples else ""
        )
        detail_instruction = (
            " شرح مفصل وواضح وشامل" if detailed_explanation else "شرح مختصر"
        )
        breakdown_instruction = (
            " وقسم الموضوع لأقسام فرعية منطقية" if subject_breakdown else ""
        )

        prompt = get_topic_explanation_prompt(
            detail_instruction, examples_instruction, breakdown_instruction, topic
        )

        try:
            response_text = await self.generate_completion(
                prompt=prompt,
                system_message=explanation_system_message,
                temperature=0.7,
                max_tokens=4000,  # Allow longer responses for comprehensive explanations
            )

            # Parse the JSON response
            result = self._extract_json_from_response(response_text)

            # Validate the structure
            if not isinstance(result, dict) or "subjects" not in result:
                raise HTTPException(
                    status_code=500,
                    detail="AI response format is invalid. Please try again.",
                )

            # Ensure medical_terms_preserved is set
            result["medical_terms_preserved"] = True
            result["language"] = "Egyptian Arabic"

            return result

        except Exception as e:
            logger.error(f"Failed to explain topic {topic}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate topic explanation: {str(e)}",
            )


# Create singleton instance
ai_service = AIService()
