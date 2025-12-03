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

import httpx
import pytesseract
from fastapi import HTTPException, UploadFile
from pdf2image import convert_from_bytes, convert_from_path
from PIL import Image
from PyPDF2 import PdfReader

from app.core.config import settings

logger = logging.getLogger(__name__)


# ============================================
# ENHANCED SYSTEM MESSAGE
# ============================================

ENHANCED_SYSTEM_MESSAGE = """You are an elite educational assessment designer with expertise in cognitive psychology, Bloom's Taxonomy, and evidence-based learning principles.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 MANDATORY REQUIREMENTS - READ CAREFULLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. EXACT QUESTION DISTRIBUTION (NON-NEGOTIABLE):
   ✓ 70% Standard Questions - Direct knowledge assessment
   ✓ 20% Critical Thinking Questions - Higher-order reasoning
   ✓ 10% Linking Questions - Concept integration

2. DIFFICULTY CALIBRATION (STRICTLY ENFORCE):
   • EASY: Simple recall, basic definitions, obvious answers
   • MEDIUM: Requires understanding and application of concepts
   • HARD: Complex analysis, multi-step reasoning, synthesis

3. UNIQUENESS & DIVERSITY:
   • Every question MUST be completely different from previous ones
   • Vary question structure, phrasing, and angles
   • Use different aspects of the topic
   • NO repetition of question patterns or concepts

4. OUTPUT FORMAT:
   • Return ONLY valid JSON
   • NO markdown formatting (no ```json```)
   • NO additional text or explanations outside JSON
   • For explanation_ar fields: Keep medical terms in English and explain in Egyptian Arabic for better understanding

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 QUESTION TYPE DEFINITIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

╔═══════════════════════════════════════════╗
║ STANDARD QUESTIONS (70%)                  ║
╚═══════════════════════════════════════════╝
Purpose: Test fundamental knowledge and comprehension
Cognitive Levels: Remember, Understand, Basic Apply
Characteristics:
  • Direct factual recall
  • Definition-based questions
  • Basic concept identification
  • Straightforward application
Examples:
  ✓ "What is the definition of X?"
  ✓ "Which of the following describes Y?"
  ✓ "What are the main components of Z?"

╔═══════════════════════════════════════════╗
║ CRITICAL THINKING QUESTIONS (20%)         ║
╚═══════════════════════════════════════════╝
Purpose: Require higher-order thinking and deep reasoning
Cognitive Levels: Analyze, Evaluate, Create
Characteristics:
  • Compare and contrast concepts
  • Predict outcomes and consequences
  • Solve complex problems
  • Justify decisions with reasoning
  • Evaluate arguments or solutions
  • Apply concepts to novel scenarios
Examples:
  ✓ "Why would X occur if Y changes?"
  ✓ "What would be the consequences of Z?"
  ✓ "How would you solve this problem using concept A?"
  ✓ "Evaluate the effectiveness of approach B"

╔═══════════════════════════════════════════╗
║ LINKING QUESTIONS (10%)                   ║
╚═══════════════════════════════════════════╝
Purpose: Connect multiple concepts and show relationships
Cognitive Levels: Understand, Analyze, Synthesize
Characteristics:
  • Explicitly connect 2+ concepts
  • Show cause-and-effect relationships
  • Compare different topics/ideas
  • Demonstrate integrated understanding
Examples:
  ✓ "How does concept X relate to concept Y?"
  ✓ "What is the connection between A and B?"
  ✓ "Compare and contrast processes C and D"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ QUALITY ASSURANCE CHECKLIST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Before finalizing your response, verify:
□ Exact distribution matches requirements (70-20-10)
□ Difficulty level is appropriate and consistent
□ Questions are unique and don't repeat patterns
□ Critical thinking questions require actual reasoning
□ Linking questions connect multiple concepts explicitly
□ All explanations are clear and accurate
□ JSON format is valid (no markdown)
□ Options are balanced and plausible for MCQ
□ Correct answers are truly correct

REMEMBER: Quality over speed. Take time to ensure each question meets these standards."""


class AIService:
    """Service to interact with DeepSeek AI API"""

    def __init__(self):
        self.api_key = settings.ai_api_key
        self.api_endpoint = settings.ai_api_endpoint
        self.model = settings.ai_model
        # Configure timeout with specific read timeout for long API responses
        # connect: time to establish connection, read: time to receive response chunks
        # 15 minutes (900s) read timeout for large PDF explanations
        self.timeout = httpx.Timeout(connect=30.0, read=900.0, write=30.0, pool=30.0)

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

                response_data = response.json()

                # Log response structure for debugging
                if is_thinking_model:
                    logger.info(f"Using thinking model: {self.model}")
                    if "choices" in response_data and len(response_data["choices"]) > 0:
                        message_keys = list(
                            response_data["choices"][0].get("message", {}).keys()
                        )
                        logger.info(f"Response message keys: {message_keys}")

                return response_data

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
        difficulty_guide = {
            "easy": """
EASY DIFFICULTY GUIDELINES:
• Questions should be straightforward and test basic recall
• Answers should be obvious to someone who studied the material
• Avoid complex reasoning or multi-step problems
• Use simple, clear language
• Focus on fundamental concepts and definitions""",
            "medium": """
MEDIUM DIFFICULTY GUIDELINES:
• Questions require understanding and application of concepts
• Answers require thinking but are achievable with study
• May involve some problem-solving or analysis
• Use clear but more technical language
• Test deeper comprehension beyond memorization""",
            "hard": """
HARD DIFFICULTY GUIDELINES:
• Questions demand complex analysis and synthesis
• Answers require deep understanding and reasoning
• Involve multi-step problem-solving or evaluation
• May include novel scenarios or edge cases
• Test mastery and ability to apply knowledge creatively""",
        }

        current_difficulty_guide = difficulty_guide.get(
            difficulty.lower(), difficulty_guide["medium"]
        )

        # Build previous questions context with stronger anti-duplication
        previous_context = ""
        if previous_questions and len(previous_questions) > 0:
            questions_list = "\n".join(
                [f"  {i+1}. {q}" for i, q in enumerate(previous_questions[:30])]
            )
            previous_context = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚫 PREVIOUSLY GENERATED QUESTIONS - DO NOT REPEAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{questions_list}

⚠️ CRITICAL: Generate COMPLETELY NEW questions that:
  • Cover different aspects of the topic
  • Use different wording and phrasing
  • Test different knowledge areas
  • Have different question structures
  • Are NOT variations of the above questions

Think: "What haven't I asked yet about this topic?"
"""

        # Build notes context
        notes_context = ""
        if notes:
            notes_context = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 ADDITIONAL INSTRUCTIONS FROM USER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{notes}

Incorporate these instructions while maintaining all other requirements.
"""

        # Question type specific prompts
        if question_type == "multiple_choice":
            prompt = f"""Generate {count} UNIQUE multiple choice questions about: {topic}

{current_difficulty_guide}

EXACT DISTRIBUTION REQUIRED:
├─ Standard Questions: {standard_count} questions
├─ Critical Thinking Questions: {critical_count} questions
└─ Linking Questions: {linking_count} questions
   TOTAL: {count} questions

{notes_context}{previous_context}

MULTIPLE CHOICE REQUIREMENTS:
✓ Provide exactly 4 options per question (A, B, C, D)
✓ All options must be plausible and relevant
✓ Avoid "all of the above" or "none of the above"
✓ Distractors should represent common misconceptions
✓ Only ONE option is correct
✓ Randomize correct answer position

OUTPUT FORMAT (JSON ONLY):
{{
    "questions": [
        {{
            "question": "Clear, specific question text",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_answer": 0,
            "explanation_en": "Detailed explanation of why the answer is correct (English)",
            "explanation_ar": "شرح تفصيلي لماذا الإجابة صحيحة (Egyptian Arabic dialect) - احتفظ بالمصطلحات الطبية بالإنجليزية واشرحها بالعربية المصرية للفهم الجيد",
            "question_category": "standard",
            "cognitive_level": "remember"
        }}
    ]
}}

COGNITIVE LEVELS:
• remember: Recall facts
• understand: Explain concepts
• apply: Use knowledge in new situations
• analyze: Break down and examine
• evaluate: Make judgments and assessments
• create: Generate new ideas or solutions

Begin generation now. Return ONLY the JSON object."""

        elif question_type == "true_false":
            prompt = f"""Generate {count} UNIQUE True/False questions about: {topic}

{current_difficulty_guide}

EXACT DISTRIBUTION REQUIRED:
├─ Standard Questions: {standard_count} questions
├─ Critical Thinking Questions: {critical_count} questions
└─ Linking Questions: {linking_count} questions
   TOTAL: {count} questions

{notes_context}{previous_context}

TRUE/FALSE REQUIREMENTS:
✓ Statements must be clear and unambiguous
✓ Avoid trick questions or double negatives
✓ Balance True and False answers approximately 50/50
✓ Statements should test real understanding, not just memorization
✓ For critical thinking: require analysis of implications
✓ For linking: make statements that connect concepts

OUTPUT FORMAT (JSON ONLY):
{{
    "questions": [
        {{
            "question": "Clear True/False statement",
            "options": ["True", "False"],
            "correct_answer": 0,
            "explanation_en": "Why this is true/false with supporting details (English)",
            "explanation_ar": "لماذا هذا صحيح/خطأ مع التفاصيل الداعمة (Egyptian Arabic) - احتفظ بالمصطلحات الطبية بالإنجليزية واشرحها بالعربية المصرية للفهم الجيد",
            "question_category": "standard",
            "cognitive_level": "remember"
        }}
    ]
}}

QUALITY EXAMPLES:
Standard: "The mitochondria is known as the powerhouse of the cell."
Critical: "If all mitochondria in a cell were destroyed, the cell would eventually die due to lack of energy."
Linking: "The process of cellular respiration in mitochondria is essentially the reverse of photosynthesis in chloroplasts."

Begin generation now. Return ONLY the JSON object."""

        elif question_type == "essay":
            prompt = f"""Generate {count} UNIQUE essay/short answer questions about: {topic}

{current_difficulty_guide}

EXACT DISTRIBUTION REQUIRED:
├─ Standard Questions: {standard_count} questions (explain, describe, define)
├─ Critical Thinking Questions: {critical_count} questions (analyze, evaluate, argue)
└─ Linking Questions: {linking_count} questions (compare, synthesize, relate)
   TOTAL: {count} questions

{notes_context}{previous_context}

ESSAY QUESTION REQUIREMENTS:
✓ Vary length requirements: full essays, paragraphs, short answers
✓ Clear expectations for what should be included
✓ Specific grading criteria
✓ Key points that strong answers should cover

OUTPUT FORMAT (JSON ONLY):
{{
    "questions": [
        {{
            "question": "Open-ended question requiring written response",
            "key_points": [
                "First key concept to address",
                "Second important point",
                "Third critical element"
            ],
            "suggested_length": "2-3 paragraphs",
            "grading_criteria": "What makes a complete and excellent answer",
            "question_category": "standard",
            "cognitive_level": "understand"
        }}
    ]
}}

LENGTH OPTIONS:
• "One word or phrase" - for simple identification
• "1-2 sentences" - for brief definitions
• "1 paragraph" - for explanations
• "2-3 paragraphs" - for full short essays
• "4-5 paragraphs" - for comprehensive essays

Begin generation now. Return ONLY the JSON object."""

        else:  # mixed
            mcq_count = int(count * 0.65)
            tf_count = count - mcq_count

            prompt = f"""Generate {count} UNIQUE MIXED questions (MCQ + True/False) about: {topic}

{current_difficulty_guide}

EXACT DISTRIBUTION REQUIRED:
├─ Standard Questions: {standard_count} questions
├─ Critical Thinking Questions: {critical_count} questions
└─ Linking Questions: {linking_count} questions
   TOTAL: {count} questions

QUESTION TYPE MIX:
├─ Multiple Choice (4 options): approximately {mcq_count} questions
└─ True/False (2 options): approximately {tf_count} questions

{notes_context}{previous_context}

OUTPUT FORMAT (JSON ONLY):
{{
    "questions": [
        {{
            "question": "Question text",
            "options": ["A", "B", "C", "D"],
            "correct_answer": 0,
            "explanation_en": "Detailed explanation (English)",
            "explanation_ar": "شرح تفصيلي (Egyptian Arabic) - احتفظ بالمصطلحات الطبية بالإنجليزية واشرحها بالعربية المصرية للفهم الجيد",
            "question_category": "standard",
            "cognitive_level": "remember"
        }}
    ]
}}

Mix MCQ and T/F questions intelligently throughout the set.

Begin generation now. Return ONLY the JSON object."""

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
            pdf_file = BytesIO(contents)

            pdf_reader = PdfReader(pdf_file)
            text_content = []
            pages_with_no_text = []

            # First pass: Try to extract text using PyPDF2
            for page_num, page in enumerate(pdf_reader.pages, 1):
                try:
                    text = page.extract_text()
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
                    # Convert PDF pages to images
                    images = convert_from_bytes(contents)

                    for page_num in pages_needing_ocr:
                        try:
                            if page_num <= len(images):
                                image = images[page_num - 1]
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
                                            if (
                                                match
                                                and int(match.group(1)) == page_num
                                            ):
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
            await file.seek(0)

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
            with open(pdf_path, "rb") as f:
                pdf_file = BytesIO(f.read())

            pdf_reader = PdfReader(pdf_file)
            text_content = []
            pages_with_no_text = []

            # First pass: Try to extract text using PyPDF2
            for page_num, page in enumerate(pdf_reader.pages, 1):
                try:
                    text = page.extract_text()
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
                    # Convert PDF pages to images using file path
                    images = convert_from_path(pdf_path)

                    for page_num in pages_needing_ocr:
                        try:
                            if page_num <= len(images):
                                image = images[page_num - 1]
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
                                            if (
                                                match
                                                and int(match.group(1)) == page_num
                                            ):
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
        difficulty_guide = {
            "easy": "EASY: Straightforward questions testing basic recall from the content",
            "medium": "MEDIUM: Questions requiring understanding and application of content concepts",
            "hard": "HARD: Complex questions demanding analysis, synthesis, and deep reasoning",
        }

        current_difficulty_guide = difficulty_guide.get(
            difficulty.lower(), difficulty_guide["medium"]
        )

        # Build previous questions context
        previous_context = ""
        if previous_questions and len(previous_questions) > 0:
            questions_list = "\n".join(
                [f"  {i+1}. {q}" for i, q in enumerate(previous_questions[:30])]
            )
            previous_context = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚫 DO NOT REPEAT THESE QUESTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{questions_list}

Generate COMPLETELY DIFFERENT questions from different parts of the content.
"""

        notes_context = ""
        if notes:
            notes_context = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 USER INSTRUCTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{notes}

Incorporate these instructions while maintaining all other requirements.
"""

        # ==========================================
        # PROMPT GENERATION BASED ON TYPE
        # ==========================================

        if question_type == "essay":
            prompt = f"""Based on the following content, generate {count} UNIQUE essay/short answer questions.

{current_difficulty_guide}

EXACT DISTRIBUTION REQUIRED:
├─ Standard Questions: {standard_count} questions
├─ Critical Thinking Questions: {critical_count} questions
└─ Linking Questions: {linking_count} questions
   TOTAL: {count} questions

{notes_context}{previous_context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📄 CONTENT TO ANALYZE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{pdf_content}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ESSAY REQUIREMENTS:
✓ Questions must be answerable primarily using the provided content
✓ Grading criteria must reference specific details from the text
✓ Vary question scope (specific details vs. broad themes)

OUTPUT FORMAT (JSON ONLY):
{{
    "questions": [
        {{
            "question": "Essay/short answer question based on content",
            "key_points": ["Point 1 from text", "Point 2 from text", "Point 3 from text"],
            "suggested_length": "2-3 paragraphs",
            "grading_criteria": "Specific criteria based on source text",
            "question_category": "standard",
            "cognitive_level": "understand"
        }}
    ]
}}

Begin generation now. Return ONLY the JSON object."""

        elif question_type == "mixed":
            mcq_count = int(count * 0.65)
            tf_count = count - mcq_count

            prompt = f"""Based on the following content, generate {count} UNIQUE MIXED questions.

{current_difficulty_guide}

EXACT DISTRIBUTION REQUIRED:
├─ Standard Questions: {standard_count} questions
├─ Critical Thinking Questions: {critical_count} questions
└─ Linking Questions: {linking_count} questions

TYPE MIX:
├─ MCQ (4 options): ~{mcq_count} questions
└─ True/False: ~{tf_count} questions

{notes_context}{previous_context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📄 CONTENT TO ANALYZE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{pdf_content}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OUTPUT FORMAT (JSON ONLY):
{{
    "questions": [
        {{
            "question": "Question text based on content",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_answer": 0,
            "explanation_en": "Explanation citing the text (English)",
            "explanation_ar": "شرح مع الإشارة للنص (Egyptian Arabic)",
            "question_category": "standard",
            "cognitive_level": "remember"
        }}
    ]
}}

Begin generation now. Return ONLY the JSON object."""

        elif question_type == "true_false":
            prompt = f"""Based on the following content, generate {count} UNIQUE True/False questions.

{current_difficulty_guide}

EXACT DISTRIBUTION REQUIRED:
├─ Standard Questions: {standard_count} questions
├─ Critical Thinking Questions: {critical_count} questions
└─ Linking Questions: {linking_count} questions

{notes_context}{previous_context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📄 CONTENT TO ANALYZE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{pdf_content}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TRUE/FALSE REQUIREMENTS:
✓ Statements must be derived directly from the text or logical inferences from it
✓ Avoid outside knowledge not supported by the text
✓ Explanations must reference *why* the text supports/refutes the statement

OUTPUT FORMAT (JSON ONLY):
{{
    "questions": [
        {{
            "question": "Statement based on text",
            "options": ["True", "False"],
            "correct_answer": 0,
            "explanation_en": "Evidence from text (English)",
            "explanation_ar": "الدليل من النص (Egyptian Arabic) - احتفظ بالمصطلحات الطبية بالإنجليزية واشرحها بالعربية المصرية للفهم الجيد",
            "question_category": "standard",
            "cognitive_level": "remember"
        }}
    ]
}}

Begin generation now. Return ONLY the JSON object."""

        else:  # multiple_choice
            prompt = f"""Based on the following content, generate {count} UNIQUE multiple choice questions.

{current_difficulty_guide}

EXACT DISTRIBUTION REQUIRED:
├─ Standard Questions: {standard_count} questions
├─ Critical Thinking Questions: {critical_count} questions
└─ Linking Questions: {linking_count} questions

{notes_context}{previous_context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📄 CONTENT TO ANALYZE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{pdf_content}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MCQ REQUIREMENTS:
✓ Questions must be answerable *strictly* using the provided content
✓ Distractors should be plausible misinterpretations of the text
✓ Explanations should quote or reference the specific part of the text

OUTPUT FORMAT (JSON ONLY):
{{
    "questions": [
        {{
            "question": "Question based on content",
            "options": ["A", "B", "C", "D"],
            "correct_answer": 0,
            "explanation_en": "Explanation citing the text (English)",
            "explanation_ar": "شرح مع الإشارة للنص (Egyptian Arabic)",
            "question_category": "standard",
            "cognitive_level": "remember"
        }}
    ]
}}

Begin generation now. Return ONLY the JSON object."""

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
        current_difficulty_guide = difficulty_guide.get(
            difficulty.lower(), difficulty_guide["medium"]
        )

        previous_context = ""
        if previous_questions and len(previous_questions) > 0:
            questions_list = "\n".join([f"- {q}" for q in previous_questions[:20]])
            previous_context = f"\n\nDO NOT REPEAT:\n{questions_list}\n"

        notes_context = f"\nUSER NOTES: {notes}\n" if notes else ""

        # Select Prompt
        if question_type == "essay":
            prompt = f"""Based on the content below, generate {count} UNIQUE essay questions.
            
{current_difficulty_guide}
Distribution: {standard_count} Standard, {critical_count} Critical, {linking_count} Linking.
{notes_context}{previous_context}

CONTENT:
{pdf_content}

Format as JSON:
{{
    "questions": [
        {{
            "question": "Essay question",
            "key_points": ["Point 1", "Point 2"],
            "suggested_length": "Length",
            "grading_criteria": "Criteria",
            "question_category": "standard",
            "cognitive_level": "understand"
        }}
    ]
}}"""
        elif question_type == "true_false":
            prompt = f"""Based on the content below, generate {count} UNIQUE True/False questions.

{current_difficulty_guide}
Distribution: {standard_count} Standard, {critical_count} Critical, {linking_count} Linking.
{notes_context}{previous_context}

CONTENT:
{pdf_content}

Format as JSON:
{{
    "questions": [
        {{
            "question": "Statement",
            "options": ["True", "False"],
            "correct_answer": 0,
            "explanation_en": "Explanation (English)",
            "explanation_ar": "شرح (Egyptian Arabic) - احتفظ بالمصطلحات الطبية بالإنجليزية واشرحها بالعربية المصرية للفهم الجيد",
            "question_category": "standard",
            "cognitive_level": "remember"
        }}
    ]
}}"""
        elif question_type == "mixed":
            prompt = f"""Based on the content below, generate {count} UNIQUE MIXED questions (MCQ + T/F).

{current_difficulty_guide}
Distribution: {standard_count} Standard, {critical_count} Critical, {linking_count} Linking.
{notes_context}{previous_context}

CONTENT:
{pdf_content}

Format as JSON:
{{
    "questions": [
        {{
            "question": "Question",
            "options": ["Option A", "Option B", "Option C", "Option D"], 
            "correct_answer": 0,
            "explanation_en": "Explanation (English)",
            "explanation_ar": "شرح (Egyptian Arabic) - احتفظ بالمصطلحات الطبية بالإنجليزية واشرحها بالعربية المصرية للفهم الجيد",
            "question_category": "standard",
            "cognitive_level": "remember"
        }}
    ]
}}"""
        else:  # Multiple Choice
            prompt = f"""Based on the content below, generate {count} UNIQUE Multiple Choice questions.

{current_difficulty_guide}
Distribution: {standard_count} Standard, {critical_count} Critical, {linking_count} Linking.
{notes_context}{previous_context}

CONTENT:
{pdf_content}

Format as JSON:
{{
    "questions": [
        {{
            "question": "Question",
            "options": ["A", "B", "C", "D"],
            "correct_answer": 0,
            "explanation_en": "Explanation (English)",
            "explanation_ar": "شرح (Egyptian Arabic) - احتفظ بالمصطلحات الطبية بالإنجليزية واشرحها بالعربية المصرية للفهم الجيد",
            "question_category": "standard",
            "cognitive_level": "remember"
        }}
    ]
}}"""

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
        pdf_file = BytesIO(contents)

        pdf_reader = PdfReader(pdf_file)
        pages_content = []
        pages_with_no_text = []

        # First pass: Try to extract text using PyPDF2
        for page_num, page in enumerate(pdf_reader.pages, 1):
            try:
                text = page.extract_text()
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
                # Convert PDF pages to images (do a single conversion for efficiency)
                images = convert_from_bytes(contents)

                for page_num in pages_needing_ocr:
                    try:
                        if page_num <= len(images):
                            image = images[page_num - 1]
                            # Perform OCR on the image
                            ocr_text = pytesseract.image_to_string(
                                image, lang="eng+ara"
                            )
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
        explanation_system_message = """You are an expert medical educator explaining content to Egyptian students.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 EXPLANATION REQUIREMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. LANGUAGE: Explain in Egyptian Arabic dialect only (اللغة المصرية العامية)
2. MEDICAL TERMS: Keep all medical and scientific terms in English as they are, and BOLD them with **asterisks**
   ✓ Examples: "**diabetes**", "**hypertension**", "**myocardial infarction**", "**electrocardiogram**"
   ✓ Do NOT translate these terms - keep them in English and bold them
   ✓ Bold ALL medical/scientific terms: "**monosaccharides**", "**homeostasis**", "**glucose**", etc.

3. CLARITY: Use simple, clear Egyptian Arabic that students understand
4. STRUCTURE: Explain concepts step by step with logical flow
5. EXAMPLES: Include practical examples when relevant
6. CONNECTIONS: Show how concepts relate to each other

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 EGYPTIAN ARABIC STYLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Use natural Egyptian Arabic like:
✓ "يعني" (means)
✓ "مثلاً" (for example)
✓ "المهم" (important)
✓ "لو عايز تفهم" (if you want to understand)
✓ "المشكلة إن" (the problem is)
✓ "السبب" (the reason)

⚠️ IMPORTANT: Start directly with the explanation content. DO NOT use conversational openers like:
- "طيب يا جماعة" (Okay guys)
- "هاشرحلكم" (Let me explain to you)
- "في الصفحة دي" (In this page)
- "محتوى الصفحة" (Page content)
- Any phrases that reference "the page" or introduce the explanation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📤 OUTPUT FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Return ONLY a JSON object with this exact structure:
{
    "pages": [
        {
            "page_number": 1,
            "explanation": "الشرح بالعربية المصرية هنا..."
        },
        {
            "page_number": 2,
            "explanation": "الشرح بالعربية المصرية هنا..."
        }
    ]
}

⚠️ IMPORTANT: Return ONLY the JSON object, no additional text or markdown."""

        # Process pages in batches to avoid timeout on large PDFs
        # Each batch will be sent as one request
        BATCH_SIZE = 2  # Process 2 pages per request - smaller batches = faster response, less timeout risk
        MAX_BATCH_CONTENT_LENGTH = 3000  # Max chars per batch (smaller for reliability)

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

            prompt = f"""{detail_instruction} للمحتوى ده بالعربية المصرية بس، وابقِ المصطلحات الطبية زي ما هي بالإنجليزية{examples_instruction}:

{merged_content}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

المطلوب: شرح واضح ومفيد للطلاب المصريين لكل صفحة.

أرجع JSON فيه شرح لكل صفحة من الصفحات: {page_numbers}

الformat المطلوب:
{{
    "pages": [
        {{"page_number": رقم_الصفحة, "explanation": "الشرح هنا..."}}
    ]
}}"""

            # Try with retries
            max_retries = 2
            batch_explained = None

            for attempt in range(max_retries + 1):
                try:
                    response_text = await self.generate_completion(
                        prompt=prompt,
                        system_message=explanation_system_message,
                        temperature=0.7,
                        max_tokens=3000,  # Reduced for faster response
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
        explanation_system_message = """You are an expert medical educator explaining topics to Egyptian students.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 EXPLANATION REQUIREMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. LANGUAGE: Explain in Egyptian Arabic dialect only (اللغة المصرية العامية)
2. MEDICAL TERMS: Keep all medical and scientific terms in English as they are, and BOLD them with **asterisks**
   ✓ Examples: "**diabetes**", "**hypertension**", "**myocardial infarction**", "**electrocardiogram**"
   ✓ Do NOT translate these terms - keep them in English and bold them
   ✓ Bold ALL medical/scientific terms: "**monosaccharides**", "**homeostasis**", "**glucose**", etc.

3. STRUCTURE: Organize explanation by SUBJECTS/SUB-TOPICS, not by pages
4. CLARITY: Use simple, clear Egyptian Arabic that students understand
5. LOGICAL FLOW: Explain concepts step by step with smooth transitions
6. EXAMPLES: Include practical examples when relevant
7. CONNECTIONS: Show how concepts relate to each other

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 EGYPTIAN ARABIC STYLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Use natural Egyptian Arabic like:
✓ "يعني" (means)
✓ "مثلاً" (for example)
✓ "المهم" (important)
✓ "لو عايز تفهم" (if you want to understand)
✓ "المشكلة إن" (the problem is)
✓ "السبب" (the reason)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📤 OUTPUT FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Return ONLY a JSON object with this exact structure:
{
    "topic": "Main topic name",
    "subjects": [
        {
            "subject_title": "First Subject Title",
            "explanation": "Complete explanation of this subject in Egyptian Arabic"
        },
        {
            "subject_title": "Second Subject Title",
            "explanation": "Complete explanation of this subject in Egyptian Arabic"
        }
    ],
    "language": "Egyptian Arabic",
    "medical_terms_preserved": true
}

⚠️ IMPORTANT: 
- Start directly with educational content - NO conversational openers
- Break down the topic into logical SUBJECTS/SUB-TOPICS
- Each subject should have a clear title and comprehensive explanation
- Use **bold** for all medical terms
- Return ONLY the JSON object, no additional text"""

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

        prompt = f"""{detail_instruction} للموضوع الطبي ده بالعربية المصرية بس، وابقِ المصطلحات الطبية زي ما هي بالإنجليزية مع وضع ** حوالين كل مصطلح{examples_instruction}{breakdown_instruction}:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 الموضوع: {topic}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

المطلوب: شرح شامل وواضح للموضوع ده، مقسم لأقسام فرعية منطقية كل قسم له عنوان وشرح كامل.

الأقسام المطلوبة عادة:
• التعريف والمفهوم الأساسي
• الأسباب والعوامل المؤثرة
• الأعراض والعلامات
• التشخيص والفحوصات
• العلاج والإدارة
• المضاعفات والوقاية
• أي أقسام أخرى مهمة متعلقة بالموضوع

شرح كل قسم بالتفصيل بالعربية المصرية، واستخدم ** للتأكيد على المصطلحات الطبية."""

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
