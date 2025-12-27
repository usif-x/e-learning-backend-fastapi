# app/services/quiz_attempt.py
import math
from datetime import datetime
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import and_, func
from sqlalchemy.orm import Session, selectinload

from app.models.lecture_content import LectureContent
from app.models.quiz_attempt import QuizAttempt
from app.schemas.lecture import QuizAttemptCreate, QuizAttemptStats


class QuizAttemptService:
    def __init__(self, db: Session):
        self.db = db

    def create_attempt(
        self,
        content_id: int,
        course_id: int,
        lecture_id: int,
        user_id: int,
    ) -> QuizAttempt:
        """Create a new quiz attempt (started but not completed)"""
        # Get the quiz content
        content = (
            self.db.query(LectureContent)
            .filter(
                and_(
                    LectureContent.id == content_id,
                    LectureContent.course_id == course_id,
                    LectureContent.lecture_id == lecture_id,
                    LectureContent.content_type == "quiz",
                )
            )
            .first()
        )

        if not content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quiz not found",
            )

        if not content.questions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quiz has no questions",
            )

        # Check for existing incomplete attempt
        existing_incomplete = (
            self.db.query(QuizAttempt)
            .filter(
                and_(
                    QuizAttempt.content_id == content_id,
                    QuizAttempt.user_id == user_id,
                    QuizAttempt.is_completed == 0,
                )
            )
            .first()
        )

        if existing_incomplete:
            # Return existing incomplete attempt
            return existing_incomplete

        # Check max attempts (only count completed attempts)
        if content.max_attempts:
            completed_attempts_count = (
                self.db.query(QuizAttempt)
                .filter(
                    and_(
                        QuizAttempt.content_id == content_id,
                        QuizAttempt.user_id == user_id,
                        QuizAttempt.is_completed == 1,
                    )
                )
                .count()
            )

            if completed_attempts_count >= content.max_attempts:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Maximum attempts ({content.max_attempts}) reached",
                )

        # Create new attempt
        quiz_attempt = QuizAttempt(
            user_id=user_id,
            content_id=content_id,
            course_id=course_id,
            lecture_id=lecture_id,
            answers=None,
            score=None,
            total_questions=len(content.questions),
            correct_answers=None,
            time_taken=None,
            started_at=datetime.utcnow(),
            completed_at=None,
            is_completed=0,
        )

        self.db.add(quiz_attempt)
        self.db.commit()
        self.db.refresh(quiz_attempt)

        return quiz_attempt

    def submit_attempt(
        self,
        content_id: int,
        course_id: int,
        lecture_id: int,
        user_id: int,
        attempt_in: QuizAttemptCreate,
        attempt_id: Optional[int] = None,
    ) -> QuizAttempt:
        """Submit a quiz attempt (complete an existing attempt or create new one)"""
        # Get the quiz content
        content = (
            self.db.query(LectureContent)
            .filter(
                and_(
                    LectureContent.id == content_id,
                    LectureContent.course_id == course_id,
                    LectureContent.lecture_id == lecture_id,
                    LectureContent.content_type == "quiz",
                )
            )
            .first()
        )

        if not content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quiz not found",
            )

        if not content.questions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quiz has no questions",
            )

        # Check if we're completing an existing attempt
        quiz_attempt = None
        if attempt_id:
            quiz_attempt = (
                self.db.query(QuizAttempt)
                .filter(
                    and_(
                        QuizAttempt.id == attempt_id,
                        QuizAttempt.content_id == content_id,
                        QuizAttempt.user_id == user_id,
                        QuizAttempt.is_completed == 0,
                    )
                )
                .first()
            )

            if not quiz_attempt:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Active attempt not found or already completed",
                )
        else:
            # If no attempt_id provided, check for any incomplete attempt
            quiz_attempt = (
                self.db.query(QuizAttempt)
                .filter(
                    and_(
                        QuizAttempt.content_id == content_id,
                        QuizAttempt.user_id == user_id,
                        QuizAttempt.is_completed == 0,
                    )
                )
                .first()
            )

        # If no existing attempt, check max attempts
        if not quiz_attempt and content.max_attempts:
            completed_attempts_count = (
                self.db.query(QuizAttempt)
                .filter(
                    and_(
                        QuizAttempt.content_id == content_id,
                        QuizAttempt.user_id == user_id,
                        QuizAttempt.is_completed == 1,
                    )
                )
                .count()
            )

            if completed_attempts_count >= content.max_attempts:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Maximum attempts ({content.max_attempts}) reached",
                )

        # Validate answers
        total_questions = len(content.questions)
        if len(attempt_in.answers) != total_questions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Expected {total_questions} answers, got {len(attempt_in.answers)}",
            )

        # Calculate score
        correct_answers = 0
        answers_data = []

        for answer in attempt_in.answers:
            question_idx = answer.question_index
            selected = answer.selected_answer

            if question_idx >= total_questions:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid question index: {question_idx}",
                )

            question = content.questions[question_idx]
            correct_answer = question.get("correct_answer")

            # Handle unanswered questions (selected_answer is None/null)
            if selected is None:
                is_correct = False
            else:
                is_correct = selected == correct_answer
                if is_correct:
                    correct_answers += 1

            answers_data.append(
                {
                    "question_index": question_idx,
                    "selected_answer": selected,
                    "correct_answer": correct_answer,
                    "is_correct": is_correct,
                }
            )

        # Calculate score percentage
        score = (correct_answers / total_questions) * 100 if total_questions > 0 else 0

        # Update existing attempt or create new one
        if quiz_attempt:
            # Update existing incomplete attempt
            quiz_attempt.answers = answers_data
            quiz_attempt.score = score
            quiz_attempt.correct_answers = correct_answers
            quiz_attempt.time_taken = attempt_in.time_taken
            quiz_attempt.completed_at = datetime.utcnow()
            quiz_attempt.is_completed = 1
            self.db.flush()  # Ensure update is flushed to database
        else:
            # Create new completed attempt
            quiz_attempt = QuizAttempt(
                user_id=user_id,
                content_id=content_id,
                course_id=course_id,
                lecture_id=lecture_id,
                answers=answers_data,
                score=score,
                total_questions=total_questions,
                correct_answers=correct_answers,
                time_taken=attempt_in.time_taken,
                started_at=attempt_in.started_at,
                completed_at=datetime.utcnow(),
                is_completed=1,
            )
            self.db.add(quiz_attempt)

        self.db.commit()
        self.db.refresh(quiz_attempt)

        return quiz_attempt

    def get_user_attempts(
        self,
        content_id: int,
        user_id: int,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[Optional[QuizAttempt], List[QuizAttempt], dict]:
        """Get user's attempts for a specific quiz, including incomplete attempt"""
        # Get incomplete attempt (if exists)
        incomplete_attempt = (
            self.db.query(QuizAttempt)
            .filter(
                and_(
                    QuizAttempt.content_id == content_id,
                    QuizAttempt.user_id == user_id,
                    QuizAttempt.is_completed == 0,
                )
            )
            .first()
        )

        # Get completed attempts
        query = self.db.query(QuizAttempt).filter(
            and_(
                QuizAttempt.content_id == content_id,
                QuizAttempt.user_id == user_id,
                QuizAttempt.is_completed == 1,
            )
        )

        # Get total count of completed attempts
        total = query.count()

        # Apply pagination
        offset = (page - 1) * size
        completed_attempts = (
            query.order_by(QuizAttempt.completed_at.desc())
            .offset(offset)
            .limit(size)
            .all()
        )

        # Pagination metadata
        total_pages = math.ceil(total / size) if size > 0 else 0
        pagination = {
            "total": total,
            "page": page,
            "size": size,
            "total_pages": total_pages,
        }

        return incomplete_attempt, completed_attempts, pagination

    def get_attempt_stats(self, content_id: int, user_id: int) -> QuizAttemptStats:
        """Get statistics for a user's quiz attempts"""
        # Get quiz content for passing score
        content = (
            self.db.query(LectureContent)
            .filter(LectureContent.id == content_id)
            .first()
        )

        if not content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quiz not found",
            )

        # Get attempt statistics (only completed attempts)
        stats = (
            self.db.query(
                func.count(QuizAttempt.id).label("total_attempts"),
                func.max(QuizAttempt.score).label("best_score"),
                func.avg(QuizAttempt.score).label("average_score"),
                func.max(QuizAttempt.completed_at).label("last_attempt_at"),
            )
            .filter(
                and_(
                    QuizAttempt.content_id == content_id,
                    QuizAttempt.user_id == user_id,
                    QuizAttempt.is_completed == 1,
                )
            )
            .first()
        )

        total_attempts = stats.total_attempts or 0
        best_score = float(stats.best_score) if stats.best_score else None
        average_score = float(stats.average_score) if stats.average_score else None
        last_attempt_at = stats.last_attempt_at

        # Check if user passed
        passed = False
        if best_score and content.passing_score:
            passed = best_score >= content.passing_score

        return QuizAttemptStats(
            content_id=content_id,
            total_attempts=total_attempts,
            best_score=best_score,
            average_score=average_score,
            last_attempt_at=last_attempt_at,
            passed=passed,
        )

    def get_user_analytics(self, content_id: int, user_id: int) -> Optional[dict]:
        """Get detailed user analytics for a specific quiz content"""
        from app.schemas.lecture import QuizUserAnalytics

        # Get quiz content for passing score
        content = (
            self.db.query(LectureContent)
            .filter(LectureContent.id == content_id)
            .first()
        )

        if not content:
            return None

        # Get all completed attempts for detailed analytics
        attempts = (
            self.db.query(QuizAttempt)
            .filter(
                and_(
                    QuizAttempt.content_id == content_id,
                    QuizAttempt.user_id == user_id,
                    QuizAttempt.is_completed == 1,
                )
            )
            .all()
        )

        if not attempts:
            return None

        total_attempts = len(attempts)
        scores = [
            float(attempt.score) for attempt in attempts if attempt.score is not None
        ]

        if not scores:
            return None

        best_score = max(scores)
        lowest_score = min(scores)
        average_score = sum(scores) / len(scores)

        # Calculate best average question time (fastest time per question)
        best_avg_question_time = None
        total_time_spent = 0

        for attempt in attempts:
            if (
                attempt.time_taken
                and attempt.total_questions
                and attempt.total_questions > 0
            ):
                avg_time = attempt.time_taken / attempt.total_questions
                if best_avg_question_time is None or avg_time < best_avg_question_time:
                    best_avg_question_time = avg_time
                total_time_spent += attempt.time_taken

        average_time_per_attempt = (
            total_time_spent / total_attempts if total_attempts > 0 else None
        )

        # Get last attempt timestamp
        last_attempt_at = max(
            attempt.completed_at for attempt in attempts if attempt.completed_at
        )

        # Check if user passed
        passed = best_score >= (content.passing_score or 0)

        return QuizUserAnalytics(
            total_attempts=total_attempts,
            best_score=best_score,
            lowest_score=lowest_score,
            average_score=average_score,
            best_avg_question_time=best_avg_question_time,
            last_attempt_at=last_attempt_at,
            passed=passed,
            total_time_spent=total_time_spent,
            average_time_per_attempt=average_time_per_attempt,
        )

    def get_all_user_attempts(
        self,
        user_id: int,
        course_id: Optional[int] = None,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[QuizAttempt], dict]:
        """Get all completed quiz attempts for a user, optionally filtered by course"""
        query = self.db.query(QuizAttempt).filter(
            and_(
                QuizAttempt.user_id == user_id,
                QuizAttempt.is_completed == 1,
            )
        )

        if course_id:
            query = query.filter(QuizAttempt.course_id == course_id)

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * size
        attempts = (
            query.order_by(QuizAttempt.completed_at.desc())
            .offset(offset)
            .limit(size)
            .all()
        )

        # Pagination metadata
        total_pages = math.ceil(total / size) if size > 0 else 0
        pagination = {
            "total": total,
            "page": page,
            "size": size,
            "total_pages": total_pages,
        }

        return attempts, pagination
