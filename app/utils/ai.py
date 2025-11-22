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
            notes: Optional instructions for question generation
            previous_questions: Optional list of previously generated question texts to avoid duplicates

        Returns:
            Dictionary with parsed questions
        """
        system_message = """You are an expert educational content creator specializing in cognitive development and assessment design.

CRITICAL REQUIREMENTS - Question Distribution:
Your questions MUST follow this exact distribution:
- 70% Standard Questions: Direct assessment of knowledge and understanding
- 20% Critical Thinking Questions: Require analysis, evaluation, synthesis, or application of concepts
- 10% Linking Questions: Connect multiple concepts, topics, or ideas from the content

Generate UNIQUE and DIVERSE questions. Each request should produce DIFFERENT questions.
Return ONLY valid JSON without any markdown formatting.

QUESTION TYPE DEFINITIONS:

1. STANDARD QUESTIONS (70%):
   - Test recall, comprehension, and basic understanding
   - Straightforward application of concepts
   - Examples: "What is...", "Define...", "Which of the following..."

2. CRITICAL THINKING QUESTIONS (20%):
   - Require higher-order thinking skills (Bloom's Taxonomy: Analyze, Evaluate, Create)
   - Ask students to compare, contrast, justify, predict, or solve problems
   - Examples: "Why would X happen if Y changed?", "What would be the consequences of...", "How would you solve..."
   - Should make students think deeply, not just recall

3. LINKING QUESTIONS (10%):
   - Connect two or more concepts, topics, or ideas
   - Show relationships between different parts of the material
   - Examples: "How does concept X relate to concept Y?", "What is the connection between...", "Compare and contrast..."
   - Encourage holistic understanding of the subject"""

        # Add notes/instructions if provided
        notes_instruction = ""
        if notes:
            notes_instruction = f"\n\nADDITIONAL INSTRUCTIONS:\n{notes}\n"

        # Add previous questions context if provided
        previous_context = ""
        if previous_questions and len(previous_questions) > 0:
            previous_list = "\n".join([f"- {q}" for q in previous_questions[:20]])
            previous_context = f"""\n\nPREVIOUSLY GENERATED QUESTIONS (DO NOT REPEAT):
{previous_list}

Generate COMPLETELY DIFFERENT questions with different angles and perspectives.\n"""

        if question_type == "mixed":
            prompt = f"""Generate {count} UNIQUE and DIVERSE {difficulty} difficulty mixed questions about: {topic}

MANDATORY DISTRIBUTION (strictly follow):
- 70% Standard questions (basic MCQ and True/False)
- 20% Critical Thinking questions (analysis, evaluation, problem-solving)
- 10% Linking questions (connecting multiple concepts)

For {count} questions, this means approximately:
- Standard: {int(count * 0.7)} questions
- Critical Thinking: {int(count * 0.2)} questions  
- Linking: {max(1, int(count * 0.1))} questions

{notes_instruction}{previous_context}

Mix MCQ (4 options) and True/False (2 options) questions intelligently.
- MCQs should be approximately 60-70% of questions
- True/False should be approximately 30-40% of questions

Format as JSON:
{{
    "questions": [
        {{
            "question": "Question text here",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_answer": 0,
            "explanation_en": "Explanation in English",
            "explanation_ar": "شرح بالعربية (Egyptian dialect)",
            "question_category": "standard" | "critical_thinking" | "linking",
            "cognitive_level": "remember" | "understand" | "apply" | "analyze" | "evaluate" | "create"
        }}
    ]
}}

ENSURE:
- Exact distribution: 70% standard, 20% critical thinking, 10% linking
- Critical thinking questions require deep analysis, not just recall
- Linking questions explicitly connect 2+ concepts
- Clear explanations in both English and Egyptian Arabic
- Appropriate difficulty level throughout

Return ONLY the JSON object, no markdown formatting."""

        elif question_type == "true_false":
            prompt = f"""Generate {count} UNIQUE and DIVERSE {difficulty} difficulty True/False questions about: {topic}

MANDATORY DISTRIBUTION:
- 70% Standard questions (straightforward true/false statements)
- 20% Critical Thinking questions (require analysis or evaluation)
- 10% Linking questions (connect multiple concepts)

For {count} questions:
- Standard: {int(count * 0.7)} questions
- Critical Thinking: {int(count * 0.2)} questions
- Linking: {max(1, int(count * 0.1))} questions

{notes_instruction}{previous_context}

Format as JSON:
{{
    "questions": [
        {{
            "question": "True/False statement here",
            "options": ["True", "False"],
            "correct_answer": 0,
            "explanation_en": "Explanation in English",
            "explanation_ar": "شرح بالعربية (Egyptian dialect)",
            "question_category": "standard" | "critical_thinking" | "linking",
            "cognitive_level": "remember" | "understand" | "apply" | "analyze" | "evaluate"
        }}
    ]
}}

Examples:
- Standard: "The mitochondria is the powerhouse of the cell."
- Critical Thinking: "If photosynthesis stopped globally, all animal life would eventually cease to exist."
- Linking: "The process of cellular respiration is essentially the reverse of photosynthesis."

Return ONLY the JSON object, no markdown formatting."""

        elif question_type == "essay":
            prompt = f"""Generate {count} UNIQUE and DIVERSE {difficulty} difficulty essay/short answer questions about: {topic}

MANDATORY DISTRIBUTION:
- 70% Standard questions (describe, explain, define)
- 20% Critical Thinking questions (analyze, evaluate, justify, propose solutions)
- 10% Linking questions (compare, relate, synthesize multiple concepts)

For {count} questions:
- Standard: {int(count * 0.7)} questions
- Critical Thinking: {int(count * 0.2)} questions
- Linking: {max(1, int(count * 0.1))} questions

{notes_instruction}{previous_context}

Mix question lengths: full essays (2-3 paragraphs), short answers (1-2 sentences), definitions (one phrase).

Format as JSON:
{{
    "questions": [
        {{
            "question": "Essay or short answer question",
            "key_points": ["Point 1", "Point 2", "Point 3"],
            "suggested_length": "2-3 paragraphs" | "1-2 sentences" | "One word/phrase",
            "grading_criteria": "What to look for in answers",
            "question_category": "standard" | "critical_thinking" | "linking",
            "cognitive_level": "remember" | "understand" | "apply" | "analyze" | "evaluate" | "create"
        }}
    ]
}}

Examples:
- Standard: "Define photosynthesis and describe its main stages."
- Critical Thinking: "Evaluate the impact of deforestation on global climate patterns and propose three evidence-based solutions."
- Linking: "Compare and contrast cellular respiration and fermentation, explaining when organisms use each process."

Return ONLY the JSON object, no markdown formatting."""

        else:  # multiple_choice
            prompt = f"""Generate {count} UNIQUE and DIVERSE {difficulty} difficulty multiple choice questions about: {topic}

MANDATORY DISTRIBUTION:
- 70% Standard questions (basic knowledge and comprehension)
- 20% Critical Thinking questions (analysis, evaluation, application)
- 10% Linking questions (connecting multiple concepts)

For {count} questions:
- Standard: {int(count * 0.7)} questions
- Critical Thinking: {int(count * 0.2)} questions
- Linking: {max(1, int(count * 0.1))} questions

{notes_instruction}{previous_context}

Format as JSON:
{{
    "questions": [
        {{
            "question": "Question text here",
            "options": ["A", "B", "C", "D"],
            "correct_answer": 0,
            "explanation_en": "Explanation in English",
            "explanation_ar": "شرح بالعربية (Egyptian dialect)",
            "question_category": "standard" | "critical_thinking" | "linking",
            "cognitive_level": "remember" | "understand" | "apply" | "analyze" | "evaluate" | "create"
        }}
    ]
}}

Examples:
- Standard: "What is the primary function of the mitochondria?"
- Critical Thinking: "A scientist observes that a cell's mitochondria are damaged. Which cellular process would be MOST affected?"
- Linking: "How does the function of chloroplasts in plant cells relate to the function of mitochondria in animal cells?"

ENSURE exact distribution and appropriate cognitive levels.

Return ONLY the JSON object, no markdown formatting."""

        response_text = await self.generate_completion(
            prompt=prompt,
            system_message=system_message,
            temperature=0.9,
            max_tokens=4500,
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
            contents = await file.read()
            pdf_file = BytesIO(contents)

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
            file.seek(0)

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
            question_type: Type of questions
            notes: Optional instructions for question generation
            previous_questions: Optional list of previously generated questions

        Returns:
            Dictionary with parsed questions
        """
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="File must be a PDF")

        pdf_content = await self.extract_text_from_pdf(file)

        max_content_length = 6000
        if len(pdf_content) > max_content_length:
            pdf_content = (
                pdf_content[:max_content_length]
                + "\n\n[Content truncated for length...]"
            )

        system_message = """You are an expert educational content creator specializing in cognitive development and assessment design.

CRITICAL REQUIREMENTS - Question Distribution:
Your questions MUST follow this exact distribution:
- 70% Standard Questions: Direct assessment of knowledge from the content
- 20% Critical Thinking Questions: Require analysis, evaluation, synthesis of content
- 10% Linking Questions: Connect multiple concepts or sections from the provided content

Generate UNIQUE and DIVERSE questions based on the provided content.
Return ONLY valid JSON without any markdown formatting.

QUESTION TYPE DEFINITIONS:

1. STANDARD QUESTIONS (70%):
   - Test recall and comprehension of content
   - Direct questions about facts, definitions, processes from the material

2. CRITICAL THINKING QUESTIONS (20%):
   - Apply content to new scenarios
   - Analyze relationships or cause-effect from the material
   - Evaluate arguments or solutions presented in the content
   - Require deeper reasoning beyond memorization

3. LINKING QUESTIONS (10%):
   - Connect concepts from different sections of the content
   - Show how ideas relate across the material
   - Synthesize information from multiple parts of the document"""

        notes_instruction = ""
        if notes:
            notes_instruction = f"\n\nADDITIONAL INSTRUCTIONS:\n{notes}\n"

        previous_context = ""
        if previous_questions and len(previous_questions) > 0:
            previous_list = "\n".join([f"- {q}" for q in previous_questions[:20]])
            previous_context = f"""\n\nPREVIOUSLY GENERATED QUESTIONS (DO NOT REPEAT):
{previous_list}

Generate COMPLETELY DIFFERENT questions.\n"""

        if question_type == "essay":
            prompt = f"""Based on the following content, generate {count} UNIQUE {difficulty} difficulty essay/short answer questions.

MANDATORY DISTRIBUTION:
- 70% Standard: {int(count * 0.7)} questions (describe/explain from content)
- 20% Critical Thinking: {int(count * 0.2)} questions (analyze/evaluate/apply)
- 10% Linking: {max(1, int(count * 0.1))} questions (connect multiple concepts from content)

{notes_instruction}{previous_context}

Content:
{pdf_content}

Format as JSON:
{{
    "questions": [
        {{
            "question": "Essay/short answer question based on content",
            "key_points": ["Point 1 from content", "Point 2", "Point 3"],
            "suggested_length": "2-3 paragraphs" | "1-2 sentences" | "One word/phrase",
            "grading_criteria": "What to look for in answers",
            "question_category": "standard" | "critical_thinking" | "linking",
            "cognitive_level": "understand" | "apply" | "analyze" | "evaluate" | "create"
        }}
    ]
}}

Return ONLY the JSON object, no markdown formatting."""

        elif question_type == "mixed":
            prompt = f"""Based on the following content, generate {count} UNIQUE {difficulty} difficulty mixed questions.

MANDATORY DISTRIBUTION:
- 70% Standard: {int(count * 0.7)} questions
- 20% Critical Thinking: {int(count * 0.2)} questions
- 10% Linking: {max(1, int(count * 0.1))} questions

{notes_instruction}{previous_context}

Content:
{pdf_content}

Mix MCQ (4 options, 60-70%) and True/False (2 options, 30-40%).

Format as JSON:
{{
    "questions": [
        {{
            "question": "Question based on content",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_answer": 0,
            "explanation_en": "Explanation with content reference (English)",
            "explanation_ar": "شرح مع مرجع للمحتوى (Egyptian Arabic)",
            "question_category": "standard" | "critical_thinking" | "linking",
            "cognitive_level": "remember" | "understand" | "apply" | "analyze" | "evaluate"
        }}
    ]
}}

Return ONLY the JSON object, no markdown formatting."""

        elif question_type == "true_false":
            prompt = f"""Based on the following content, generate {count} UNIQUE {difficulty} True/False questions.

MANDATORY DISTRIBUTION:
- 70% Standard: {int(count * 0.7)} questions
- 20% Critical Thinking: {int(count * 0.2)} questions
- 10% Linking: {max(1, int(count * 0.1))} questions

{notes_instruction}{previous_context}

Content:
{pdf_content}

Format as JSON:
{{
    "questions": [
        {{
            "question": "True/False statement from content",
            "options": ["True", "False"],
            "correct_answer": 0,
            "explanation_en": "Explanation with content reference (English)",
            "explanation_ar": "شرح مع مرجع للمحتوى (Egyptian Arabic)",
            "question_category": "standard" | "critical_thinking" | "linking",
            "cognitive_level": "remember" | "understand" | "apply" | "analyze" | "evaluate"
        }}
    ]
}}

Return ONLY the JSON object, no markdown formatting."""

        else:  # multiple_choice
            prompt = f"""Based on the following content, generate {count} UNIQUE {difficulty} multiple choice questions.

MANDATORY DISTRIBUTION:
- 70% Standard: {int(count * 0.7)} questions
- 20% Critical Thinking: {int(count * 0.2)} questions
- 10% Linking: {max(1, int(count * 0.1))} questions

{notes_instruction}{previous_context}

Content:
{pdf_content}

Format as JSON:
{{
    "questions": [
        {{
            "question": "Question based on content",
            "options": ["A", "B", "C", "D"],
            "correct_answer": 0,
            "explanation_en": "Explanation with content reference (English)",
            "explanation_ar": "شرح مع مرجع للمحتوى (Egyptian Arabic)",
            "question_category": "standard" | "critical_thinking" | "linking",
            "cognitive_level": "remember" | "understand" | "apply" | "analyze" | "evaluate"
        }}
    ]
}}

Return ONLY the JSON object, no markdown formatting."""

        response_text = await self.generate_completion(
            prompt=prompt,
            system_message=system_message,
            temperature=0.9,
            max_tokens=5500,
        )

        return self._extract_json_from_response(response_text)
        """
        Extract text content from a PDF file path

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Extracted text content

        Raises:
            HTTPException: If PDF processing fails
        """
        try:
            with open(pdf_path, "rb") as f:
                pdf_file = BytesIO(f.read())

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

        Args:
            pdf_path: Path to the PDF file
            difficulty: Question difficulty (easy, medium, hard)
            count: Number of questions to generate
            question_type: Type of questions
            notes: Optional instructions for question generation
            previous_questions: Optional list of previously generated questions

        Returns:
            Dictionary with parsed questions
        """
        pdf_content = await self.extract_text_from_pdf_path(pdf_path)

        max_content_length = 6000
        if len(pdf_content) > max_content_length:
            pdf_content = (
                pdf_content[:max_content_length]
                + "\n\n[Content truncated for length...]"
            )

        system_message = """You are an expert educational content creator specializing in cognitive development and assessment design.

CRITICAL REQUIREMENTS - Question Distribution:
Your questions MUST follow this exact distribution:
- 70% Standard Questions: Direct assessment of knowledge from the content
- 20% Critical Thinking Questions: Require analysis, evaluation, synthesis of content
- 10% Linking Questions: Connect multiple concepts or sections from the provided content

Generate UNIQUE and DIVERSE questions based on the provided content.
Return ONLY valid JSON without any markdown formatting.

QUESTION TYPE DEFINITIONS:

1. STANDARD QUESTIONS (70%):
   - Test recall and comprehension of content
   - Direct questions about facts, definitions, processes from the material

2. CRITICAL THINKING QUESTIONS (20%):
   - Apply content to new scenarios
   - Analyze relationships or cause-effect from the material
   - Evaluate arguments or solutions presented in the content
   - Require deeper reasoning beyond memorization

3. LINKING QUESTIONS (10%):
   - Connect concepts from different sections of the content
   - Show how ideas relate across the material
   - Synthesize information from multiple parts of the document"""

        notes_instruction = ""
        if notes:
            notes_instruction = f"\n\nADDITIONAL INSTRUCTIONS:\n{notes}\n"

        previous_context = ""
        if previous_questions and len(previous_questions) > 0:
            previous_list = "\n".join([f"- {q}" for q in previous_questions[:20]])
            previous_context = f"""\n\nPREVIOUSLY GENERATED QUESTIONS (DO NOT REPEAT):
{previous_list}

Generate COMPLETELY DIFFERENT questions.\n"""

        if question_type == "essay":
            prompt = f"""Based on the following content, generate {count} UNIQUE {difficulty} difficulty essay/short answer questions.

MANDATORY DISTRIBUTION:
- 70% Standard: {int(count * 0.7)} questions (describe/explain from content)
- 20% Critical Thinking: {int(count * 0.2)} questions (analyze/evaluate/apply)
- 10% Linking: {max(1, int(count * 0.1))} questions (connect multiple concepts from content)

{notes_instruction}{previous_context}

Content:
{pdf_content}

Format as JSON:
{{
    "questions": [
        {{
            "question": "Essay/short answer question based on content",
            "key_points": ["Point 1 from content", "Point 2", "Point 3"],
            "suggested_length": "2-3 paragraphs" | "1-2 sentences" | "One word/phrase",
            "grading_criteria": "What to look for in answers",
            "question_category": "standard" | "critical_thinking" | "linking",
            "cognitive_level": "understand" | "apply" | "analyze" | "evaluate" | "create"
        }}
    ]
}}

Return ONLY the JSON object, no markdown formatting."""

        elif question_type == "mixed":
            prompt = f"""Based on the following content, generate {count} UNIQUE {difficulty} difficulty mixed questions.

MANDATORY DISTRIBUTION:
- 70% Standard: {int(count * 0.7)} questions
- 20% Critical Thinking: {int(count * 0.2)} questions
- 10% Linking: {max(1, int(count * 0.1))} questions

{notes_instruction}{previous_context}

Content:
{pdf_content}

Mix MCQ (4 options, 60-70%) and True/False (2 options, 30-40%).

Format as JSON:
{{
    "questions": [
        {{
            "question": "Question based on content",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_answer": 0,
            "explanation_en": "Explanation with content reference (English)",
            "explanation_ar": "شرح مع مرجع للمحتوى (Egyptian Arabic)",
            "question_category": "standard" | "critical_thinking" | "linking",
            "cognitive_level": "remember" | "understand" | "apply" | "analyze" | "evaluate"
        }}
    ]
}}

Return ONLY the JSON object, no markdown formatting."""

        elif question_type == "true_false":
            prompt = f"""Based on the following content, generate {count} UNIQUE {difficulty} True/False questions.

MANDATORY DISTRIBUTION:
- 70% Standard: {int(count * 0.7)} questions
- 20% Critical Thinking: {int(count * 0.2)} questions
- 10% Linking: {max(1, int(count * 0.1))} questions

{notes_instruction}{previous_context}

Content:
{pdf_content}

Format as JSON:
{{
    "questions": [
        {{
            "question": "True/False statement from content",
            "options": ["True", "False"],
            "correct_answer": 0,
            "explanation_en": "Explanation with content reference (English)",
            "explanation_ar": "شرح مع مرجع للمحتوى (Egyptian Arabic)",
            "question_category": "standard" | "critical_thinking" | "linking",
            "cognitive_level": "remember" | "understand" | "apply" | "analyze" | "evaluate"
        }}
    ]
}}

Return ONLY the JSON object, no markdown formatting."""

        else:  # multiple_choice
            prompt = f"""Based on the following content, generate {count} UNIQUE {difficulty} multiple choice questions.

MANDATORY DISTRIBUTION:
- 70% Standard: {int(count * 0.7)} questions
- 20% Critical Thinking: {int(count * 0.2)} questions
- 10% Linking: {max(1, int(count * 0.1))} questions

{notes_instruction}{previous_context}

Content:
{pdf_content}

Format as JSON:
{{
    "questions": [
        {{
            "question": "Question based on content",
            "options": ["A", "B", "C", "D"],
            "correct_answer": 0,
            "explanation_en": "Explanation with content reference (English)",
            "explanation_ar": "شرح مع مرجع للمحتوى (Egyptian Arabic)",
            "question_category": "standard" | "critical_thinking" | "linking",
            "cognitive_level": "remember" | "understand" | "apply" | "analyze" | "evaluate"
        }}
    ]
}}

Return ONLY the JSON object, no markdown formatting."""

        response_text = await self.generate_completion(
            prompt=prompt,
            system_message=system_message,
            temperature=0.9,
            max_tokens=5500,
        )

        return self._extract_json_from_response(response_text)


# Create singleton instance
ai_service = AIService()
