# app/services/user_generated_question.py
import math
from typing import List, Optional, Tuple

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import and_, desc, or_
from sqlalchemy.orm import Session

from app.models.user_generated_question import (
    UserGeneratedQuestion,
    UserGeneratedQuestionAttempt,
)
from app.utils.ai import ai_service


class UserGeneratedQuestionService:
    def __init__(self, db: Session):
        self.db = db

    async def generate_questions_from_topic(
        self,
        user_id: int,
        topic: str,
        title: str,
        description: Optional[str],
        difficulty: str,
        question_type: str,
        count: int,
        is_public: bool,
        notes: Optional[str] = None,
    ) -> UserGeneratedQuestion:
        """
        Generate questions from topic using AI and save to database
        """
        # Generate questions using AI
        result = await ai_service.generate_questions(
            topic=topic,
            difficulty=difficulty,
            count=count,
            question_type=question_type,
            notes=notes,
            previous_questions=None,  # First generation, no previous questions
        )

        questions = result.get("questions", [])

        if not questions:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate questions",
            )

        # Create question set
        question_set = UserGeneratedQuestion(
            user_id=user_id,
            title=title,
            description=description,
            topic=topic,
            difficulty=difficulty,
            question_type=question_type,
            is_public=is_public,
            questions=questions,
            total_questions=len(questions),
            source_type="topic",
        )

        self.db.add(question_set)
        self.db.commit()
        self.db.refresh(question_set)

        return question_set

    async def generate_questions_from_pdf(
        self,
        user_id: int,
        file: UploadFile,
        title: str,
        description: Optional[str],
        difficulty: str,
        question_type: str,
        count: int,
        is_public: bool,
        notes: Optional[str] = None,
    ) -> UserGeneratedQuestion:
        """
        Generate questions from PDF using AI and save to database
        """
        # Validate PDF
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail="File must be a PDF",
            )

        # Save PDF file to server with UUID naming
        from app.utils.file_upload import file_upload_service

        uuid_filename, relative_path = await file_upload_service.save_file(
            file=file, folder="user_questions", allowed_extensions=[".pdf"]
        )

        # Generate questions using AI
        result = await ai_service.generate_questions_from_pdf(
            file=file,
            difficulty=difficulty,
            count=count,
            question_type=question_type,
            notes=notes,
            previous_questions=None,  # First generation
        )

        questions = result.get("questions", [])

        if not questions:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate questions from PDF",
            )

        # Extract topic from PDF content or use title
        topic = title  # Can be enhanced to extract from PDF

        # Create question set
        question_set = UserGeneratedQuestion(
            user_id=user_id,
            title=title,
            description=description,
            topic=topic,
            difficulty=difficulty,
            question_type=question_type,
            is_public=is_public,
            questions=questions,
            total_questions=len(questions),
            source_type="pdf",
            source_file_name=uuid_filename,  # Store UUID filename
        )

        self.db.add(question_set)
        self.db.commit()
        self.db.refresh(question_set)

        return question_set

    async def add_more_questions(
        self,
        question_set_id: int,
        user_id: int,
        count: int,
        notes: Optional[str] = None,
    ) -> UserGeneratedQuestion:
        """
        Add more questions to existing set, AI will avoid duplicates
        """
        # Get existing question set
        question_set = (
            self.db.query(UserGeneratedQuestion)
            .filter(
                UserGeneratedQuestion.id == question_set_id,
                UserGeneratedQuestion.user_id == user_id,
            )
            .first()
        )

        if not question_set:
            raise HTTPException(
                status_code=404,
                detail="Question set not found",
            )

        # Extract previous question texts
        previous_questions = [q.get("question", "") for q in question_set.questions]

        # Generate new questions using AI (with previous questions to avoid duplicates)
        if question_set.source_type == "topic":
            result = await ai_service.generate_questions(
                topic=question_set.topic,
                difficulty=question_set.difficulty,
                count=count,
                question_type=question_set.question_type,
                notes=notes,
                previous_questions=previous_questions,
            )
        else:
            # For PDF-based, check if we have the saved PDF file
            if question_set.source_file_name:
                # Read the saved PDF file
                from app.utils.file_upload import file_upload_service

                pdf_path = file_upload_service.get_absolute_path(
                    f"user_questions/{question_set.source_file_name}"
                )

                if pdf_path and pdf_path.exists():
                    # Read PDF content
                    with open(pdf_path, "rb") as f:
                        pdf_content = f.read()

                    # Create a file-like object with filename attribute
                    from io import BytesIO

                    class PDFFileWrapper:
                        def __init__(self, content, filename):
                            self._content = BytesIO(content)
                            self.filename = filename

                        async def read(self, size=-1):
                            # Since BytesIO operations are synchronous, we need to run them in a thread
                            import asyncio

                            loop = asyncio.get_event_loop()
                            return await loop.run_in_executor(
                                None, self._content.read, size
                            )

                        def seek(self, pos, whence=0):
                            return self._content.seek(pos, whence)

                        def tell(self):
                            return self._content.tell()

                        def close(self):
                            return self._content.close()

                    pdf_file_like = PDFFileWrapper(
                        pdf_content, question_set.source_file_name
                    )

                    # Generate questions from the actual PDF content
                    result = await ai_service.generate_questions_from_pdf(
                        file=pdf_file_like,
                        difficulty=question_set.difficulty,
                        count=count,
                        question_type=question_set.question_type,
                        notes=notes,
                        previous_questions=previous_questions,
                    )
                else:
                    # PDF file not found, fall back to topic-based generation
                    result = await ai_service.generate_questions(
                        topic=question_set.topic,
                        difficulty=question_set.difficulty,
                        count=count,
                        question_type=question_set.question_type,
                        notes=notes or "Generate questions based on the same context",
                        previous_questions=previous_questions,
                    )
            else:
                # No saved PDF file, fall back to topic-based generation
                result = await ai_service.generate_questions(
                    topic=question_set.topic,
                    difficulty=question_set.difficulty,
                    count=count,
                    question_type=question_set.question_type,
                    notes=notes or "Generate questions based on the same context",
                    previous_questions=previous_questions,
                )

        new_questions = result.get("questions", [])

        if not new_questions:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate additional questions",
            )

        # Append new questions to existing ones
        current_questions = question_set.questions or []
        question_set.questions = current_questions + new_questions
        question_set.total_questions = len(question_set.questions)

        # Mark the questions field as modified for SQLAlchemy
        from sqlalchemy.orm import attributes

        attributes.flag_modified(question_set, "questions")

        self.db.commit()
        self.db.refresh(question_set)

        return question_set

    def edit_question(
        self,
        question_set_id: int,
        user_id: int,
        question_index: int,
        question_data: dict,
    ) -> UserGeneratedQuestion:
        """
        Edit a specific question in a question set
        """
        # Get existing question set
        question_set = (
            self.db.query(UserGeneratedQuestion)
            .filter(
                UserGeneratedQuestion.id == question_set_id,
                UserGeneratedQuestion.user_id == user_id,
            )
            .first()
        )

        if not question_set:
            raise HTTPException(
                status_code=404,
                detail="Question set not found",
            )

        # Check if question index is valid
        if question_index < 0 or question_index >= len(question_set.questions):
            raise HTTPException(
                status_code=400,
                detail=f"Question index {question_index} is out of range. Valid range: 0-{len(question_set.questions)-1}",
            )

        # Update the question
        question_set.questions[question_index] = question_data

        # Mark the questions field as modified for SQLAlchemy
        from sqlalchemy.orm import attributes

        attributes.flag_modified(question_set, "questions")

        self.db.commit()
        self.db.refresh(question_set)

        return question_set

    def delete_question(
        self,
        question_set_id: int,
        user_id: int,
        question_index: int,
    ) -> UserGeneratedQuestion:
        """
        Delete a specific question from a question set
        """
        # Get existing question set
        question_set = (
            self.db.query(UserGeneratedQuestion)
            .filter(
                UserGeneratedQuestion.id == question_set_id,
                UserGeneratedQuestion.user_id == user_id,
            )
            .first()
        )

        if not question_set:
            raise HTTPException(
                status_code=404,
                detail="Question set not found",
            )

        # Check if question index is valid
        if question_index < 0 or question_index >= len(question_set.questions):
            raise HTTPException(
                status_code=400,
                detail=f"Question index {question_index} is out of range. Valid range: 0-{len(question_set.questions)-1}",
            )

        # Check if this would leave the question set empty
        if len(question_set.questions) <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete the last question from a question set",
            )

        # Delete the question
        question_set.questions.pop(question_index)

        # Update total questions count
        question_set.total_questions = len(question_set.questions)

        # Mark the questions field as modified for SQLAlchemy
        from sqlalchemy.orm import attributes

        attributes.flag_modified(question_set, "questions")

        self.db.commit()
        self.db.refresh(question_set)

        return question_set

    def get_user_question_sets(
        self,
        user_id: int,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[UserGeneratedQuestion], dict]:
        """
        Get all question sets created by user with pagination
        """
        query = self.db.query(UserGeneratedQuestion).filter(
            UserGeneratedQuestion.user_id == user_id
        )

        total = query.count()
        total_pages = math.ceil(total / size) if size > 0 else 0

        offset = (page - 1) * size
        question_sets = (
            query.order_by(desc(UserGeneratedQuestion.created_at))
            .offset(offset)
            .limit(size)
            .all()
        )

        pagination = {
            "total": total,
            "page": page,
            "size": size,
            "total_pages": total_pages,
        }

        return question_sets, pagination

    def get_question_set_detail(
        self,
        question_set_id: int,
        user_id: int,
    ) -> UserGeneratedQuestion:
        """
        Get detailed question set (only creator can see all details)
        """
        question_set = (
            self.db.query(UserGeneratedQuestion)
            .filter(
                UserGeneratedQuestion.id == question_set_id,
                UserGeneratedQuestion.user_id == user_id,
            )
            .first()
        )

        if not question_set:
            raise HTTPException(
                status_code=404,
                detail="Question set not found",
            )

        return question_set

    def get_public_question_set_detail(
        self,
        question_set_id: int,
    ) -> UserGeneratedQuestion:
        """
        Get detailed public question set (any user can see)
        """
        question_set = (
            self.db.query(UserGeneratedQuestion)
            .filter(
                UserGeneratedQuestion.id == question_set_id,
                UserGeneratedQuestion.is_public == True,
            )
            .first()
        )

        if not question_set:
            raise HTTPException(
                status_code=404,
                detail="Question set not found",
            )
        return question_set

    def update_question_set(
        self,
        question_set_id: int,
        user_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        is_public: Optional[bool] = None,
    ) -> UserGeneratedQuestion:
        """
        Update question set metadata
        """
        question_set = (
            self.db.query(UserGeneratedQuestion)
            .filter(
                UserGeneratedQuestion.id == question_set_id,
                UserGeneratedQuestion.user_id == user_id,
            )
            .first()
        )

        if not question_set:
            raise HTTPException(
                status_code=404,
                detail="Question set not found",
            )

        if title is not None:
            question_set.title = title
        if description is not None:
            question_set.description = description
        if is_public is not None:
            question_set.is_public = is_public

        self.db.commit()
        self.db.refresh(question_set)

        return question_set

    def delete_question_set(
        self,
        question_set_id: int,
        user_id: int,
    ) -> None:
        """
        Delete question set (only creator can delete)
        """
        question_set = (
            self.db.query(UserGeneratedQuestion)
            .filter(
                UserGeneratedQuestion.id == question_set_id,
                UserGeneratedQuestion.user_id == user_id,
            )
            .first()
        )

        if not question_set:
            raise HTTPException(
                status_code=404,
                detail="Question set not found",
            )

        self.db.delete(question_set)
        self.db.commit()

    # ==================== Public Questions ====================

    def get_public_question_sets(
        self,
        current_user_id: int,
        page: int = 1,
        size: int = 20,
        difficulty: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[dict], dict]:
        """
        Get all public question sets with user's attempt status
        """
        query = self.db.query(UserGeneratedQuestion).filter(
            UserGeneratedQuestion.is_public == True
        )

        # Filter by difficulty
        if difficulty:
            query = query.filter(UserGeneratedQuestion.difficulty == difficulty)

        # Search by title or topic
        if search:
            query = query.filter(
                or_(
                    UserGeneratedQuestion.title.ilike(f"%{search}%"),
                    UserGeneratedQuestion.topic.ilike(f"%{search}%"),
                )
            )

        total = query.count()
        total_pages = math.ceil(total / size) if size > 0 else 0

        offset = (page - 1) * size
        question_sets = (
            query.order_by(desc(UserGeneratedQuestion.created_at))
            .offset(offset)
            .limit(size)
            .all()
        )

        # Build response with attempt status
        result = []
        for qs in question_sets:
            # Check if user has completed attempts
            user_attempts = (
                self.db.query(UserGeneratedQuestionAttempt)
                .filter(
                    UserGeneratedQuestionAttempt.question_set_id == qs.id,
                    UserGeneratedQuestionAttempt.user_id == current_user_id,
                    UserGeneratedQuestionAttempt.is_completed == True,
                )
                .all()
            )

            user_has_attempted = len(user_attempts) > 0
            user_best_score = (
                max([a.score for a in user_attempts if a.score is not None])
                if user_attempts
                else None
            )

            # Check for pending (incomplete) attempt
            pending_attempt = (
                self.db.query(UserGeneratedQuestionAttempt)
                .filter(
                    UserGeneratedQuestionAttempt.question_set_id == qs.id,
                    UserGeneratedQuestionAttempt.user_id == current_user_id,
                    UserGeneratedQuestionAttempt.is_completed == False,
                )
                .first()
            )

            result.append(
                {
                    "question_set": qs,
                    "user_has_attempted": user_has_attempted,
                    "user_best_score": user_best_score,
                    "user_has_pending_attempt": pending_attempt is not None,
                    "pending_attempt_id": (
                        pending_attempt.id if pending_attempt else None
                    ),
                    "pending_attempt_started_at": (
                        pending_attempt.started_at if pending_attempt else None
                    ),
                    "creator_name": qs.user.display_name if qs.user else "Unknown",
                }
            )

        pagination = {
            "total": total,
            "page": page,
            "size": size,
            "total_pages": total_pages,
        }

        return result, pagination

    def get_question_set_participants(
        self,
        question_set_id: int,
        page: int = 1,
        size: int = 20,
    ) -> dict:
        """
        Get all participants who attempted a question set with their best scores.
        Returns leaderboard sorted by best score with pagination.
        """
        from sqlalchemy import func

        # Get question set
        question_set = (
            self.db.query(UserGeneratedQuestion)
            .filter(UserGeneratedQuestion.id == question_set_id)
            .first()
        )

        if not question_set:
            raise HTTPException(
                status_code=404,
                detail="Question set not found",
            )

        # Check if public
        if not question_set.is_public:
            raise HTTPException(
                status_code=403,
                detail="This question set is private",
            )

        # Get all completed attempts grouped by user
        from app.models.user import User

        attempts_query = (
            self.db.query(
                UserGeneratedQuestionAttempt.user_id,
                func.max(UserGeneratedQuestionAttempt.score).label("best_score"),
                func.count(UserGeneratedQuestionAttempt.id).label("total_attempts"),
                func.max(UserGeneratedQuestionAttempt.completed_at).label(
                    "last_attempt_at"
                ),
            )
            .filter(
                UserGeneratedQuestionAttempt.question_set_id == question_set_id,
                UserGeneratedQuestionAttempt.is_completed == True,
            )
            .group_by(UserGeneratedQuestionAttempt.user_id)
            .order_by(func.max(UserGeneratedQuestionAttempt.score).desc())
        )

        # Get total count before pagination
        total_participants = attempts_query.count()
        total_pages = math.ceil(total_participants / size) if size > 0 else 0

        # Apply pagination
        offset = (page - 1) * size
        attempts_paginated = attempts_query.offset(offset).limit(size).all()

        # Build participant list with user info and rankings
        participants = []
        # Calculate rank based on page position
        rank = (page - 1) * size + 1
        for attempt in attempts_paginated:
            user = self.db.query(User).filter(User.id == attempt.user_id).first()

            if user:
                participants.append(
                    {
                        "user_id": user.id,
                        "user_name": user.display_name,
                        "profile_picture": user.profile_picture,
                        "best_score": attempt.best_score or 0,
                        "total_attempts": attempt.total_attempts,
                        "last_attempt_at": attempt.last_attempt_at,
                        "rank": rank,
                    }
                )
                rank += 1

        return {
            "participants": participants,
            "total_participants": total_participants,
            "question_set_id": question_set.id,
            "question_set_title": question_set.title,
            "total_attempts": question_set.attempt_count,
            "page": page,
            "size": size,
            "total_pages": total_pages,
        }

    # ==================== Attempts ====================

    def start_attempt(
        self,
        question_set_id: int,
        user_id: int,
    ) -> Tuple[UserGeneratedQuestionAttempt, UserGeneratedQuestion]:
        """
        Start or resume an attempt on a question set.
        If user has an incomplete attempt, returns that instead of creating new one.
        """
        # Get question set
        question_set = (
            self.db.query(UserGeneratedQuestion)
            .filter(UserGeneratedQuestion.id == question_set_id)
            .first()
        )

        if not question_set:
            raise HTTPException(
                status_code=404,
                detail="Question set not found",
            )

        # Check if public or owned by user
        if not question_set.is_public and question_set.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="This question set is private",
            )

        # Check for existing incomplete attempt
        existing_attempt = (
            self.db.query(UserGeneratedQuestionAttempt)
            .filter(
                UserGeneratedQuestionAttempt.question_set_id == question_set_id,
                UserGeneratedQuestionAttempt.user_id == user_id,
                UserGeneratedQuestionAttempt.is_completed == False,
            )
            .first()
        )

        if existing_attempt:
            # Return existing incomplete attempt (resume)
            return existing_attempt, question_set

        # Create new attempt
        attempt = UserGeneratedQuestionAttempt(
            question_set_id=question_set_id,
            user_id=user_id,
            total_questions=question_set.total_questions,
            is_completed=False,
        )

        self.db.add(attempt)
        self.db.commit()
        self.db.refresh(attempt)

        return attempt, question_set

    def submit_attempt(
        self,
        attempt_id: int,
        user_id: int,
        answers: List[dict],
        time_taken: int,
    ) -> UserGeneratedQuestionAttempt:
        """
        Submit attempt and calculate score
        """
        from datetime import datetime

        # Get attempt
        attempt = (
            self.db.query(UserGeneratedQuestionAttempt)
            .filter(
                UserGeneratedQuestionAttempt.id == attempt_id,
                UserGeneratedQuestionAttempt.user_id == user_id,
                UserGeneratedQuestionAttempt.is_completed == False,
            )
            .first()
        )

        if not attempt:
            raise HTTPException(
                status_code=404,
                detail="Attempt not found or already completed",
            )

        # Get question set
        question_set = attempt.question_set

        # Calculate results
        correct_count = 0
        processed_answers = []

        for answer in answers:
            question_idx = answer.get("question_index", 0)
            selected_answer = answer.get("selected_answer")

            if question_idx < len(question_set.questions):
                question = question_set.questions[question_idx]
                correct_answer = question.get("correct_answer")
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

        # Calculate score
        score = (
            round((correct_count / attempt.total_questions) * 100)
            if attempt.total_questions > 0
            else 0
        )

        # Update attempt
        attempt.answers = processed_answers
        attempt.score = score
        attempt.correct_answers = correct_count
        attempt.time_taken = time_taken
        attempt.is_completed = True
        attempt.completed_at = datetime.utcnow()

        # Update question set attempt count
        question_set.attempt_count += 1

        self.db.commit()
        self.db.refresh(attempt)

        return attempt

    def get_user_attempts(
        self,
        user_id: int,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[UserGeneratedQuestionAttempt], dict]:
        """
        Get all attempts by user with pagination
        """
        query = self.db.query(UserGeneratedQuestionAttempt).filter(
            UserGeneratedQuestionAttempt.user_id == user_id,
            UserGeneratedQuestionAttempt.is_completed == True,
        )

        total = query.count()
        total_pages = math.ceil(total / size) if size > 0 else 0

        offset = (page - 1) * size
        attempts = (
            query.order_by(desc(UserGeneratedQuestionAttempt.completed_at))
            .offset(offset)
            .limit(size)
            .all()
        )

        pagination = {
            "total": total,
            "page": page,
            "size": size,
            "total_pages": total_pages,
        }

        return attempts, pagination

    def get_attempt_detail(
        self,
        attempt_id: int,
        user_id: int,
    ) -> UserGeneratedQuestionAttempt:
        """
        Get detailed attempt result with questions and answers
        """
        attempt = (
            self.db.query(UserGeneratedQuestionAttempt)
            .filter(
                UserGeneratedQuestionAttempt.id == attempt_id,
                UserGeneratedQuestionAttempt.user_id == user_id,
            )
            .first()
        )

        if not attempt:
            raise HTTPException(
                status_code=404,
                detail="Attempt not found",
            )

        return attempt

    def get_user_pending_attempts(
        self,
        user_id: int,
    ) -> List[UserGeneratedQuestionAttempt]:
        """
        Get all pending (incomplete) attempts for a user
        """
        pending_attempts = (
            self.db.query(UserGeneratedQuestionAttempt)
            .filter(
                UserGeneratedQuestionAttempt.user_id == user_id,
                UserGeneratedQuestionAttempt.is_completed == False,
            )
            .order_by(desc(UserGeneratedQuestionAttempt.started_at))
            .all()
        )

        return pending_attempts
