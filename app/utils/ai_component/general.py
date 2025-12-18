import logging
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from app.utils.prompts import (
    ENHANCED_SYSTEM_MESSAGE,
    get_difficulty_guide,
    get_essay_prompt,
    get_explain_concept_prompt,
    get_explain_concept_system_message,
    get_mixed_prompt,
    get_multiple_choice_prompt,
    get_notes_context,
    get_previous_questions_context,
    get_summarize_prompt,
    get_summarize_system_message,
    get_topic_explanation_prompt,
    get_topic_explanation_system_message,
    get_true_false_prompt,
)

logger = logging.getLogger(__name__)


class GeneralGeneratorMixin:
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
