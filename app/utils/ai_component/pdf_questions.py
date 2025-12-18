import logging
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, UploadFile

from app.utils.prompts import (
    ENHANCED_SYSTEM_MESSAGE,
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
)

logger = logging.getLogger(__name__)


class PDFQuestionGeneratorMixin:
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
