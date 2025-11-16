# app/services/practice_quiz.py
from typing import List, Optional

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from app.models.lecture_content import LectureContent
from app.models.practice_quiz import PracticeQuiz
from app.models.quiz_attempt import QuizAttempt


class PracticeQuizService:
    def __init__(self, db: Session):
        self.db = db

    def get_incorrect_questions(
        self,
        user_id: int,
        course_id: Optional[int] = None,
        lecture_ids: Optional[List[int]] = None,
        question_count: int = 10,
        include_unanswered: bool = True,
    ) -> List[dict]:
        """
        Get incorrect and/or unanswered questions from user's past attempts.
        Returns questions with their original quiz context.
        Can filter by course_id and/or lecture_ids.
        """
        # Query all completed attempts
        query = self.db.query(QuizAttempt).filter(
            and_(
                QuizAttempt.user_id == user_id,
                QuizAttempt.is_completed == 1,
            )
        )

        if course_id:
            query = query.filter(QuizAttempt.course_id == course_id)

        if lecture_ids:
            query = query.filter(QuizAttempt.lecture_id.in_(lecture_ids))

        attempts = query.all()

        # Collect incorrect/unanswered questions
        incorrect_questions = []
        seen_questions = set()  # Track unique questions (by text)

        for attempt in attempts:
            if not attempt.answers:
                continue

            # Get the quiz content for this attempt
            content = (
                self.db.query(LectureContent)
                .filter(LectureContent.id == attempt.content_id)
                .first()
            )

            if not content or not content.questions:
                continue

            # Find incorrect or unanswered questions
            for answer_data in attempt.answers:
                is_correct = answer_data.get("is_correct", False)
                selected_answer = answer_data.get("selected_answer")
                question_idx = answer_data.get("question_index")

                # Skip if correct answer
                if is_correct:
                    continue

                # Skip if unanswered and we don't want those
                if selected_answer is None and not include_unanswered:
                    continue

                # Get the question
                if question_idx < len(content.questions):
                    question = content.questions[question_idx]
                    question_text = question.get("question", "")

                    # Avoid duplicates
                    if question_text in seen_questions:
                        continue

                    seen_questions.add(question_text)

                    incorrect_questions.append(
                        {
                            "question": question_text,
                            "options": question.get("options", []),
                            "correct_answer": question.get("correct_answer"),
                            "explanation_en": question.get("explanation_en"),
                            "explanation_ar": question.get("explanation_ar"),
                            "source_course_id": attempt.course_id,
                            "source_lecture_id": attempt.lecture_id,
                            "source_quiz_title": content.title,
                        }
                    )

                    # Stop if we have enough questions
                    if len(incorrect_questions) >= question_count:
                        break

            if len(incorrect_questions) >= question_count:
                break

        return incorrect_questions

    def get_questions_from_lectures(
        self,
        lecture_ids: List[int],
        question_count: int = 10,
    ) -> List[dict]:
        """
        Get questions from specific lectures.
        Returns questions from all quiz content in the specified lectures.
        """
        # Get all quiz content from the specified lectures
        quiz_contents = (
            self.db.query(LectureContent)
            .filter(
                and_(
                    LectureContent.lecture_id.in_(lecture_ids),
                    LectureContent.content_type == "quiz",
                    LectureContent.questions.isnot(None),
                )
            )
            .all()
        )

        # Collect all questions from these lectures
        all_questions = []
        seen_questions = set()  # Track unique questions (by text)

        for content in quiz_contents:
            if not content.questions:
                continue

            for question in content.questions:
                question_text = question.get("question", "")

                # Avoid duplicates
                if question_text in seen_questions:
                    continue

                seen_questions.add(question_text)

                all_questions.append(
                    {
                        "question": question_text,
                        "options": question.get("options", []),
                        "correct_answer": question.get("correct_answer"),
                        "explanation_en": question.get("explanation_en"),
                        "explanation_ar": question.get("explanation_ar"),
                        "source_course_id": content.course_id,
                        "source_lecture_id": content.lecture_id,
                        "source_quiz_title": content.title,
                    }
                )

        # Randomly select questions if we have more than requested
        import random

        if len(all_questions) > question_count:
            all_questions = random.sample(all_questions, question_count)

        return all_questions

    def get_questions_from_quizzes(
        self,
        quiz_ids: List[int],
        question_count: int = 10,
    ) -> List[dict]:
        """
        Get questions from specific quiz content IDs.
        Returns questions from the specified quiz contents.
        """
        # Get the specified quiz contents
        quiz_contents = (
            self.db.query(LectureContent)
            .filter(
                and_(
                    LectureContent.id.in_(quiz_ids),
                    LectureContent.content_type == "quiz",
                    LectureContent.questions.isnot(None),
                )
            )
            .all()
        )

        # Collect all questions from these specific quizzes
        all_questions = []
        seen_questions = set()  # Track unique questions (by text)

        for content in quiz_contents:
            if not content.questions:
                continue

            for question in content.questions:
                question_text = question.get("question", "")

                # Avoid duplicates
                if question_text in seen_questions:
                    continue

                seen_questions.add(question_text)

                all_questions.append(
                    {
                        "question": question_text,
                        "options": question.get("options", []),
                        "correct_answer": question.get("correct_answer"),
                        "explanation_en": question.get("explanation_en"),
                        "explanation_ar": question.get("explanation_ar"),
                        "source_course_id": content.course_id,
                        "source_lecture_id": content.lecture_id,
                        "source_quiz_title": content.title,
                    }
                )

        # Randomly select questions if we have more than requested
        import random

        if len(all_questions) > question_count:
            all_questions = random.sample(all_questions, question_count)

        return all_questions

    def create_practice_content(
        self,
        user_id: int,
        questions: List[dict],
        course_id: Optional[int] = None,
        lecture_ids: Optional[List[int]] = None,
        quiz_ids: Optional[List[int]] = None,
    ) -> PracticeQuiz:
        """
        Create a practice quiz for a specific user.
        Does NOT add to course content - this is user-specific practice only.
        """
        # Build title and description based on generation mode
        if quiz_ids:
            # Generated from specific quizzes
            title = f"Practice Quiz - Selected Quizzes"
            if course_id:
                title += f" (Course {course_id})"
            description = (
                f"Practice quiz generated from {len(quiz_ids)} selected quiz(es)"
            )
        elif lecture_ids:
            # Generated from specific lectures
            title = f"Practice Quiz - Selected Lectures"
            if course_id:
                title += f" (Course {course_id})"
            description = (
                f"Practice quiz generated from {len(lecture_ids)} selected lecture(s)"
            )
        else:
            # Generated from incorrect answers
            title = f"Practice Quiz - Review Mistakes" + (
                f" (Course {course_id})" if course_id else ""
            )
            description = (
                "Practice quiz generated from your incorrect and unanswered questions"
            )

        # Create a PracticeQuiz record (user-specific, not added to course)
        practice_quiz = PracticeQuiz(
            user_id=user_id,
            course_id=course_id,
            title=title,
            description=description,
            questions=questions,  # Store full questions with explanations
            total_questions=len(questions),
            is_completed=0,  # Not completed yet
        )

        self.db.add(practice_quiz)
        self.db.commit()
        self.db.refresh(practice_quiz)

        return practice_quiz

    def start_practice_attempt(
        self,
        practice_quiz_id: int,
        user_id: int,
    ) -> dict:
        """
        Start or resume a practice quiz attempt.
        Returns the practice quiz with only questions and options (no correct answers).
        """
        from datetime import datetime

        practice_quiz = (
            self.db.query(PracticeQuiz)
            .filter(
                PracticeQuiz.id == practice_quiz_id,
                PracticeQuiz.user_id == user_id,
            )
            .first()
        )

        if not practice_quiz:
            from fastapi import HTTPException, status

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Practice quiz not found",
            )

        # If already completed, user can review but not retake
        if practice_quiz.is_completed:
            from fastapi import HTTPException, status

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Practice quiz already completed. Use the result endpoint to view results.",
            )

        # Strip correct answers and explanations from questions
        questions_for_attempt = []
        for question in practice_quiz.questions:
            questions_for_attempt.append(
                {
                    "question": question["question"],
                    "options": question["options"],
                }
            )

        return {
            "practice_quiz_id": practice_quiz.id,
            "questions": questions_for_attempt,
            "total_questions": practice_quiz.total_questions,
            "title": practice_quiz.title,
            "description": practice_quiz.description,
            "started_at": datetime.utcnow(),
        }

    def submit_practice_attempt(
        self,
        practice_quiz_id: int,
        user_id: int,
        answers: List[dict],
        time_taken: int,
    ) -> PracticeQuiz:
        """
        Submit a practice quiz and calculate results.
        """
        from datetime import datetime

        practice_quiz = (
            self.db.query(PracticeQuiz)
            .filter(
                PracticeQuiz.id == practice_quiz_id,
                PracticeQuiz.user_id == user_id,
                PracticeQuiz.is_completed == 0,
            )
            .first()
        )

        if not practice_quiz:
            from fastapi import HTTPException, status

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Practice quiz not found or already completed",
            )

        # Calculate results
        correct_count = 0
        processed_answers = []

        for answer in answers:
            question_idx = answer["question_index"]
            selected_answer = answer.get("selected_answer")

            if question_idx < len(practice_quiz.questions):
                question = practice_quiz.questions[question_idx]
                correct_answer = question["correct_answer"]
                is_correct = selected_answer == correct_answer

                if is_correct:
                    correct_count += 1

                processed_answers.append(
                    {
                        "question_index": question_idx,
                        "selected_answer": selected_answer,
                        "correct_answer": correct_answer,
                        "is_correct": is_correct,
                    }
                )

        # Calculate score percentage
        score = (
            (correct_count / practice_quiz.total_questions) * 100
            if practice_quiz.total_questions > 0
            else 0
        )

        # Update practice quiz with results
        practice_quiz.answers = processed_answers
        practice_quiz.score = round(score, 2)
        practice_quiz.correct_answers = correct_count
        practice_quiz.time_taken = time_taken
        practice_quiz.is_completed = 1
        practice_quiz.completed_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(practice_quiz)

        return practice_quiz

    def update_practice_quiz_results(
        self,
        practice_quiz_id: int,
        attempt_id: int,
        answers: List[dict],
        score: float,
        correct_answers: int,
        time_taken: int,
    ) -> PracticeQuiz:
        """
        Update a practice quiz record with completion results.
        """
        from datetime import datetime

        practice_quiz = (
            self.db.query(PracticeQuiz)
            .filter(PracticeQuiz.id == practice_quiz_id)
            .first()
        )

        if practice_quiz:
            practice_quiz.attempt_id = attempt_id
            practice_quiz.answers = answers
            practice_quiz.score = score
            practice_quiz.correct_answers = correct_answers
            practice_quiz.time_taken = time_taken
            practice_quiz.is_completed = 1
            practice_quiz.completed_at = datetime.utcnow()

            self.db.commit()
            self.db.refresh(practice_quiz)

        return practice_quiz

    def get_user_practice_quizzes(
        self,
        user_id: int,
        course_id: Optional[int] = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[List[PracticeQuiz], int]:
        """
        Get all practice quizzes for a user with pagination.
        Returns (quizzes, total_count)
        """
        query = self.db.query(PracticeQuiz).filter(
            PracticeQuiz.user_id == user_id,
        )

        if course_id:
            query = query.filter(PracticeQuiz.course_id == course_id)

        # Get total count
        total = query.count()

        # Apply pagination and ordering
        offset = (page - 1) * size
        quizzes = (
            query.order_by(desc(PracticeQuiz.created_at))
            .offset(offset)
            .limit(size)
            .all()
        )

        return quizzes, total
