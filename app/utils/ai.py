# app/utils/ai.py
"""
AI utility for connecting with DeepSeek AI API
Used for generating questions, content, and other educational materials
"""

import json
import logging
import re
from io import BytesIO
from typing import Any, Dict, List, Optional

import httpx
from fastapi import HTTPException, UploadFile
from PyPDF2 import PdfReader

from app.core.config import settings

logger = logging.getLogger(__name__)


class AIService:
    """Service to interact with DeepSeek AI API"""

    def __init__(self):
        self.api_key = settings.ai_api_key
        self.api_endpoint = settings.ai_api_endpoint
        self.model = settings.ai_model
        self.timeout = 900.0  # 900 seconds timeout

        # Validate configuration
        if not self.api_key:
            logger.warning("AI_API_KEY not configured. AI features will be disabled.")
        if not self.api_endpoint:
            logger.warning(
                "AI_API_ENDPOINT not configured. AI features will be disabled."
            )

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
        Make a request to DeepSeek AI API

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

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.api_endpoint, headers=headers, json=payload
                )

                if response.status_code != 200:
                    logger.error(
                        f"AI API error: {response.status_code} - {response.text}"
                    )
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"AI API request failed: {response.text}",
                    )

                return response.json()

        except httpx.TimeoutException:
            logger.error("AI API request timed out")
            raise HTTPException(status_code=504, detail="AI service request timed out")
        except httpx.RequestError as e:
            logger.error(f"AI API request error: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Failed to connect to AI service: {str(e)}"
            )

    async def generate_completion(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate a text completion from AI

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

        # Extract the completion text
        try:
            completion = response["choices"][0]["message"]["content"]
            return completion.strip()
        except (KeyError, IndexError) as e:
            logger.error(f"Failed to parse AI response: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to parse AI response")

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Have a multi-turn conversation with AI

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

        try:
            completion = response["choices"][0]["message"]["content"]
            return completion.strip()
        except (KeyError, IndexError) as e:
            logger.error(f"Failed to parse AI response: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to parse AI response")

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
        Generate educational questions for a topic

        Args:
            topic: The subject/topic for questions
            difficulty: Question difficulty (easy, medium, hard)
            count: Number of questions to generate
            question_type: Type of questions (multiple_choice, true_false, essay, mixed)
            notes: Optional instructions for question generation (e.g., "Focus on practical applications", "Avoid theoretical concepts", "Include examples from real life")
            previous_questions: Optional list of previously generated question texts to avoid duplicates

        Returns:
            Dictionary with parsed questions
        """
        system_message = """You are an expert educational content creator. 
Generate UNIQUE and DIVERSE questions for students. Each request should produce DIFFERENT questions.
Generate clear, accurate, and pedagogically sound questions.
Return ONLY valid JSON without any markdown formatting."""

        # Add notes/instructions if provided
        notes_instruction = ""
        if notes:
            notes_instruction = f"\n\nIMPORTANT ADDITIONAL INSTRUCTIONS:\n{notes}\n"

        # Add previous questions context if provided
        previous_context = ""
        if previous_questions and len(previous_questions) > 0:
            previous_list = "\n".join(
                [f"- {q}" for q in previous_questions[:20]]
            )  # Limit to last 20 to avoid token overflow
            previous_context = f"""\n\nPREVIOUSLY GENERATED QUESTIONS (DO NOT REPEAT THESE):
{previous_list}

You MUST generate COMPLETELY DIFFERENT questions. Use different angles, examples, concepts, and perspectives.\n"""

        if question_type == "mixed":
            prompt = f"""Generate {count} UNIQUE and DIVERSE {difficulty} difficulty mixed questions (both multiple choice and true/false) about: {topic}

Ensure questions are DIFFERENT from any previously generated questions. Use various angles, examples, and perspectives.{notes_instruction}{previous_context}

Mix the question types intelligently based on the topic. Guidelines:
- Multiple choice questions (4 options) should generally be MORE prevalent (approximately 60-70% of questions)
- True/False questions (2 options: True, False) should complement the MCQs (approximately 30-40%)
- Adjust the ratio based on what works best for the topic - some topics work better with more MCQs, others may benefit from more True/False
- Ensure a good balance that tests different aspects of understanding

Format the output as JSON with the following structure:
{{
    "questions": [
        {{
            "question": "Question text here",
            "options": ["Option A", "Option B", "Option C", "Option D"],  // 4 options for MCQ
            "correct_answer": 0,  // index of correct option
            "explanation_en": "Why this is correct (in English)",
            "explanation_ar": "لماذا هذا صحيح (in Arabic - Egyptian dialect)"
        }},
        {{
            "question": "True/False question text here",
            "options": ["True", "False"],  // 2 options for True/False
            "correct_answer": 0,  // 0 for True, 1 for False
            "explanation_en": "Explanation why this is true/false (in English)",
            "explanation_ar": "شرح لماذا هذا صحيح/خطأ (in Arabic - Egyptian dialect)"
        }}
    ]
}}

Make sure questions are:
- Clear and unambiguous
- Appropriate for the difficulty level
- Educational and test understanding
- Well-mixed between MCQ (4 options) and True/False (2 options)
- Include explanations in BOTH English (explanation_en) and Arabic/Egyptian (explanation_ar)
- Arabic explanations should use clear Egyptian Arabic dialect

Return ONLY the JSON object, no markdown formatting."""
        elif question_type == "true_false":
            prompt = f"""Generate {count} UNIQUE and DIVERSE {difficulty} difficulty True/False questions about: {topic}

Ensure questions are DIFFERENT from any previously generated questions. Use various angles, examples, and perspectives.{notes_instruction}{previous_context}

Format the output as JSON with the following structure:
{{
    "questions": [
        {{
            "question": "True/False question text here",
            "options": ["True", "False"],  // Always 2 options
            "correct_answer": 0,  // 0 for True, 1 for False
            "explanation_en": "Explanation why this is true/false (in English)",
            "explanation_ar": "شرح لماذا هذا صحيح/خطأ (in Arabic - Egyptian dialect)"
        }}
    ]
}}

Make sure questions are:
- Clear and unambiguous statements that are either true or false
- Appropriate for the difficulty level
- Educational and test understanding of key concepts
- Include explanations in BOTH English (explanation_en) and Arabic/Egyptian (explanation_ar)
- Arabic explanations should use clear Egyptian Arabic dialect

Return ONLY the JSON object, no markdown formatting."""
        elif question_type == "essay":
            prompt = f"""Generate {count} UNIQUE and DIVERSE {difficulty} difficulty essay/short answer questions about: {topic}

Ensure questions are DIFFERENT from any previously generated questions. Use various angles, examples, and perspectives.{notes_instruction}{previous_context}

Mix different types of open-ended questions:
- Full essay questions requiring detailed explanations (2-3 paragraphs)
- Short answer questions requiring brief descriptions (1-2 sentences)
- Definition questions asking to define or name concepts
- Explanation questions asking to describe processes or mechanisms

Format the output as JSON with the following structure:
{{
    "questions": [
        {{
            "question": "Essay or short answer question text here",
            "key_points": ["Point 1", "Point 2", "Point 3"],
            "suggested_length": "2-3 paragraphs" or "1-2 sentences" or "One word/phrase",
            "grading_criteria": "What to look for in answers"
        }}
    ]
}}

Make sure questions:
- Vary between full essays, short answers, and brief definitions
- Require critical thinking appropriate to the difficulty level
- Are open-ended and encourage detailed or concise responses based on question type
- Include clear grading guidance

Return ONLY the JSON object, no markdown formatting."""
        else:
            prompt = f"""Generate {count} UNIQUE and DIVERSE {difficulty} difficulty {question_type} questions about: {topic}

Ensure questions are DIFFERENT from any previously generated questions. Use various angles, examples, and perspectives.{notes_instruction}{previous_context}

Format the output as JSON with the following structure:
{{
    "questions": [
        {{
            "question": "Question text here",
            "options": ["A", "B", "C", "D"],  // for multiple choice
            "correct_answer": 0,  // index of correct option
            "explanation_en": "Why this is correct (in English)",
            "explanation_ar": "لماذا هذا صحيح (in Arabic - Egyptian dialect)"
        }}
    ]
}}

Make sure questions are:
- Clear and unambiguous
- Appropriate for the difficulty level
- Educational and test understanding
- Include explanations in BOTH English (explanation_en) and Arabic/Egyptian (explanation_ar)
- Arabic explanations should use clear Egyptian Arabic dialect

Return ONLY the JSON object, no markdown formatting."""

        response_text = await self.generate_completion(
            prompt=prompt,
            system_message=system_message,
            temperature=0.9,  # Increased for more diverse/unique questions
            max_tokens=4000,  # Increased to prevent truncation with bilingual explanations
        )

        # Parse JSON from response
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
        system_message = "You are an expert at summarizing educational content while preserving key information."

        length_instruction = f" in about {max_length} words" if max_length else ""
        prompt = f"Summarize the following content{length_instruction}:\n\n{content}"

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
        language_instructions = {
            "en": "Respond in English.",
            "ar": "Respond in Arabic (Egyptian dialect). Use clear Arabic language suitable for Egyptian students.",
        }

        lang_instruction = language_instructions.get(
            language, language_instructions["en"]
        )

        system_message = f"You are a skilled teacher explaining concepts to {level} level students. Use clear language and examples. {lang_instruction}"

        prompt = f"Explain the following concept in a way that a {level} level student would understand:\n\n{concept}"

        return await self.generate_completion(
            prompt=prompt, system_message=system_message, temperature=0.7
        )

    async def extract_text_from_pdf(self, file: UploadFile) -> str:
        """
        Extract text content from a PDF file

        Args:
            file: Uploaded PDF file

        Returns:
            Extracted text content

        Raises:
            HTTPException: If PDF processing fails
        """
        try:
            # Read the uploaded file
            contents = await file.read()
            pdf_file = BytesIO(contents)

            # Extract text from PDF
            pdf_reader = PdfReader(pdf_file)
            text_content = []

            for page_num, page in enumerate(pdf_reader.pages, 1):
                try:
                    text = page.extract_text()
                    if text.strip():
                        text_content.append(f"--- Page {page_num} ---\n{text}")
                except Exception as e:
                    logger.warning(
                        f"Failed to extract text from page {page_num}: {str(e)}"
                    )
                    continue

            if not text_content:
                raise HTTPException(
                    status_code=400,
                    detail="No text content found in PDF. The file may be empty or contain only images.",
                )

            return "\n\n".join(text_content)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to process PDF: {str(e)}")
            raise HTTPException(
                status_code=400, detail=f"Failed to process PDF file: {str(e)}"
            )
        finally:
            # Reset file pointer for potential reuse
            await file.seek(0)

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
        Extract content from PDF and generate questions

        Args:
            file: Uploaded PDF file
            difficulty: Question difficulty (easy, medium, hard)
            count: Number of questions to generate
            question_type: Type of questions (multiple_choice, true_false, essay, mixed)
            notes: Optional instructions for question generation (e.g., "Focus on practical applications", "Avoid theoretical concepts", "Include examples from real life")
            previous_questions: Optional list of previously generated question texts to avoid duplicates

        Returns:
            Dictionary with parsed questions
        """
        # Validate file type
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="File must be a PDF")

        # Extract text from PDF
        pdf_content = await self.extract_text_from_pdf(file)

        # Limit content length to avoid token limits
        max_content_length = 4000  # characters
        if len(pdf_content) > max_content_length:
            pdf_content = (
                pdf_content[:max_content_length]
                + "\n\n[Content truncated for length...]"
            )

        # Generate questions based on content
        system_message = """You are an expert educational content creator. 
Generate UNIQUE and DIVERSE questions based on the provided content. Each request should produce DIFFERENT questions.
Generate clear, accurate, and pedagogically sound questions.
Return ONLY valid JSON without any markdown formatting."""

        # Add notes/instructions if provided
        notes_instruction = ""
        if notes:
            notes_instruction = f"\n\nIMPORTANT ADDITIONAL INSTRUCTIONS:\n{notes}\n"

        # Add previous questions context if provided
        previous_context = ""
        if previous_questions and len(previous_questions) > 0:
            previous_list = "\n".join(
                [f"- {q}" for q in previous_questions[:20]]
            )  # Limit to last 20 to avoid token overflow
            previous_context = f"""\n\nPREVIOUSLY GENERATED QUESTIONS (DO NOT REPEAT THESE):
{previous_list}

You MUST generate COMPLETELY DIFFERENT questions. Use different angles, examples, concepts, and perspectives.\n"""

        if question_type == "essay":
            prompt = f"""Based on the following content, generate {count} UNIQUE and DIVERSE {difficulty} difficulty essay/short answer questions.

Ensure questions are DIFFERENT from any previously generated questions. Use various angles, examples, and perspectives.{notes_instruction}{previous_context}

Content:
{pdf_content}

Mix different types of open-ended questions:
- Full essay questions requiring detailed explanations (2-3 paragraphs)
- Short answer questions requiring brief descriptions (1-2 sentences)
- Definition questions asking to define or name concepts
- Explanation questions asking to describe processes or mechanisms

Format the output as JSON:
{{
    "questions": [
        {{
            "question": "Essay or short answer question text here",
            "key_points": ["Point 1", "Point 2", "Point 3"],
            "suggested_length": "2-3 paragraphs" or "1-2 sentences" or "One word/phrase",
            "grading_criteria": "What to look for in answers"
        }}
    ]
}}

Make sure questions:
- Vary between full essays, short answers, and brief definitions
- Are based on the content provided
- Require critical thinking appropriate to the difficulty level
- Include clear grading guidance

Return ONLY the JSON object, no markdown formatting."""
        elif question_type == "mixed":
            prompt = f"""Based on the following content, generate {count} UNIQUE and DIVERSE {difficulty} difficulty mixed questions (both multiple choice and true/false).

Ensure questions are DIFFERENT from any previously generated questions. Use various angles, examples, and perspectives.{notes_instruction}{previous_context}

Content:
{pdf_content}

Mix the question types intelligently based on the content. Guidelines:
- Multiple choice questions (4 options) should generally be MORE prevalent (approximately 60-70% of questions)
- True/False questions (2 options: True, False) should complement the MCQs (approximately 30-40%)
- Adjust the ratio based on what works best for the content - some topics work better with more MCQs, others may benefit from more True/False
- Ensure a good balance that tests different aspects of understanding from the provided content

Format the output as JSON:
{{
    "questions": [
        {{
            "question": "Question text here",
            "options": ["Option A", "Option B", "Option C", "Option D"],  // 4 options for MCQ
            "correct_answer": 0,  // index of correct option
            "explanation_en": "Why this is correct and references to content (in English)",
            "explanation_ar": "لماذا هذا صحيح ومراجع للمحتوى (in Arabic - Egyptian dialect)"
        }},
        {{
            "question": "True/False question text here",
            "options": ["True", "False"],  // 2 options for True/False
            "correct_answer": 0,  // 0 for True, 1 for False
            "explanation_en": "Explanation why this is true/false and references to content (in English)",
            "explanation_ar": "شرح لماذا هذا صحيح/خطأ ومراجع للمحتوى (in Arabic - Egyptian dialect)"
        }}
    ]
}}

Make sure questions:
- Are directly based on the content
- Test understanding of key concepts
- Are appropriate for the difficulty level
- Well-mixed between MCQ (4 options) and True/False (2 options)
- Include explanations in BOTH English (explanation_en) and Arabic/Egyptian (explanation_ar)
- Arabic explanations should use clear Egyptian Arabic dialect

Return ONLY the JSON object, no markdown formatting."""
        elif question_type == "true_false":
            prompt = f"""Based on the following content, generate {count} UNIQUE and DIVERSE {difficulty} difficulty True/False questions.

Ensure questions are DIFFERENT from any previously generated questions. Use various angles, examples, and perspectives.{notes_instruction}{previous_context}

Content:
{pdf_content}

Format the output as JSON:
{{
    "questions": [
        {{
            "question": "True/False question text here based on the content",
            "options": ["True", "False"],  // Always 2 options
            "correct_answer": 0,  // 0 for True, 1 for False
            "explanation_en": "Explanation why this is true/false and references to content (in English)",
            "explanation_ar": "شرح لماذا هذا صحيح/خطأ ومراجع للمحتوى (in Arabic - Egyptian dialect)"
        }}
    ]
}}

Make sure questions:
- Are directly based on the content provided
- Are clear statements that are either true or false
- Test understanding of key concepts from the content
- Are appropriate for the difficulty level
- Include explanations in BOTH English (explanation_en) and Arabic/Egyptian (explanation_ar)
- Arabic explanations should use clear Egyptian Arabic dialect

Return ONLY the JSON object, no markdown formatting."""
        else:
            prompt = f"""Based on the following content, generate {count} UNIQUE and DIVERSE {difficulty} difficulty {question_type} questions.

Ensure questions are DIFFERENT from any previously generated questions. Use various angles, examples, and perspectives.{notes_instruction}{previous_context}

Content:
{pdf_content}

Format the output as JSON:
{{
    "questions": [
        {{
            "question": "Question text here",
            "options": ["A", "B", "C", "D"],  // for multiple_choice
            "correct_answer": 0,  // index of correct option or the answer text
            "explanation_en": "Why this is correct and references to content (in English)",
            "explanation_ar": "لماذا هذا صحيح ومراجع للمحتوى (in Arabic - Egyptian dialect)"
        }}
    ]
}}

Make sure questions:
- Are directly based on the content
- Test understanding of key concepts
- Are appropriate for the difficulty level
- Include explanations in BOTH English (explanation_en) and Arabic/Egyptian (explanation_ar)
- Arabic explanations should use clear Egyptian Arabic dialect

Return ONLY the JSON object, no markdown formatting."""

        response_text = await self.generate_completion(
            prompt=prompt,
            system_message=system_message,
            temperature=0.9,  # Increased for more diverse/unique questions
            max_tokens=5000,  # Increased to prevent truncation with bilingual explanations
        )

        # Parse JSON from response
        return self._extract_json_from_response(response_text)


# Create singleton instance
ai_service = AIService()
