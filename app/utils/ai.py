# app/utils/ai.py
"""
AI utility for connecting with DeepSeek AI API
Used for generating questions, content, and other educational materials
Enhanced with improved prompts and thinking model support
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
        self.timeout = 1800  # 1800 seconds timeout

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
            "explanation_ar": "شرح تفصيلي لماذا الإجابة صحيحة (Egyptian Arabic dialect)",
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
            "explanation_ar": "لماذا هذا صحيح/خطأ مع التفاصيل الداعمة (Egyptian Arabic)",
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
            "explanation_ar": "شرح تفصيلي (Egyptian Arabic)",
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
            max_tokens=64000,
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

    async def extract_text_from_pdf_path(self, pdf_path: str) -> str:
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
            "explanation_ar": "الدليل من النص (Egyptian Arabic)",
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
            max_tokens=64000,
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
            "explanation_ar": "شرح (Egyptian Arabic)",
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
            "explanation_ar": "شرح (Egyptian Arabic)",
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
            "explanation_ar": "شرح (Egyptian Arabic)",
            "question_category": "standard",
            "cognitive_level": "remember"
        }}
    ]
}}"""

        response_text = await self.generate_completion(
            prompt=prompt,
            system_message=ENHANCED_SYSTEM_MESSAGE,
            temperature=0.7,
            max_tokens=64000,
        )

        return self._extract_json_from_response(response_text)


# Create singleton instance
ai_service = AIService()
