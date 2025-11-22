# app/services/lecture.py
import math
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import and_
from sqlalchemy.orm import Session, selectinload

from app.models.course import Course
from app.models.lecture import Lecture
from app.models.lecture_content import LectureContent
from app.schemas.lecture import (
    LectureContentCreate,
    LectureContentUpdate,
    LectureCreate,
    LectureUpdate,
)


class LectureService:
    def __init__(self, db: Session):
        self.db = db

    def create_lecture(self, course_id: int, lecture_in: LectureCreate) -> Lecture:
        """Create a new lecture in a course"""
        # Verify course exists
        course = self.db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found",
            )

        # Create lecture
        lecture = Lecture(
            course_id=course_id,
            **lecture_in.model_dump(),
        )

        self.db.add(lecture)
        self.db.commit()
        self.db.refresh(lecture)

        return lecture

    def get_lecture(
        self, lecture_id: int, course_id: Optional[int] = None
    ) -> Optional[Lecture]:
        """Get a lecture by ID"""
        query = (
            self.db.query(Lecture)
            .filter(Lecture.id == lecture_id)
            .options(selectinload(Lecture.contents))
        )

        if course_id:
            query = query.filter(Lecture.course_id == course_id)

        return query.first()

    def get_lectures(
        self,
        course_id: int,
        page: int = 1,
        size: int = 50,
    ) -> Tuple[List[Lecture], dict]:
        """Get lectures for a course with pagination"""
        query = (
            self.db.query(Lecture)
            .filter(Lecture.course_id == course_id)
            .options(selectinload(Lecture.contents))
        )

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * size
        lectures = (
            query.order_by(Lecture.position.asc(), Lecture.created_at.asc())
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

        return lectures, pagination

    def update_lecture(
        self,
        lecture_id: int,
        lecture_in: LectureUpdate,
        course_id: Optional[int] = None,
    ) -> Optional[Lecture]:
        """Update a lecture"""
        query = self.db.query(Lecture).filter(Lecture.id == lecture_id)

        if course_id:
            query = query.filter(Lecture.course_id == course_id)

        lecture = query.first()
        if not lecture:
            return None

        # Update fields
        for field, value in lecture_in.model_dump(exclude_unset=True).items():
            setattr(lecture, field, value)

        self.db.commit()
        self.db.refresh(lecture)

        return lecture

    def delete_lecture(self, lecture_id: int, course_id: Optional[int] = None) -> bool:
        """Delete a lecture"""
        query = self.db.query(Lecture).filter(Lecture.id == lecture_id)

        if course_id:
            query = query.filter(Lecture.course_id == course_id)

        lecture = query.first()
        if not lecture:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lecture not found",
            )

        self.db.delete(lecture)
        self.db.commit()

        return True

    # ==================== Lecture Content Methods ====================

    def create_content(
        self, lecture_id: int, course_id: int, content_in: LectureContentCreate
    ) -> LectureContent:
        """Create content for a lecture"""
        # Verify lecture exists and belongs to course
        lecture = (
            self.db.query(Lecture)
            .filter(
                and_(
                    Lecture.id == lecture_id,
                    Lecture.course_id == course_id,
                )
            )
            .first()
        )

        if not lecture:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lecture not found",
            )

        # Validate content based on type
        if content_in.content_type == "quiz":
            if not content_in.questions or len(content_in.questions) == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Quiz content must have questions",
                )
        else:
            if not content_in.source:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{content_in.content_type} content must have a source",
                )

        # Create content
        content = LectureContent(
            course_id=course_id,
            lecture_id=lecture_id,
            **content_in.model_dump(),
        )

        self.db.add(content)
        self.db.commit()
        self.db.refresh(content)

        return content

    def get_content(self, content_id: int) -> Optional[LectureContent]:
        """Get a content item by ID"""
        return (
            self.db.query(LectureContent)
            .filter(LectureContent.id == content_id)
            .first()
        )

    def get_contents(
        self,
        lecture_id: int,
        course_id: int,
        page: int = 1,
        size: int = 50,
        content_type: Optional[str] = None,
    ) -> Tuple[List[LectureContent], dict]:
        """Get contents for a lecture with pagination"""
        query = self.db.query(LectureContent).filter(
            and_(
                LectureContent.lecture_id == lecture_id,
                LectureContent.course_id == course_id,
            )
        )

        # Filter by content type if specified
        if content_type:
            query = query.filter(LectureContent.content_type == content_type)

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * size
        contents = (
            query.order_by(
                LectureContent.position.asc(), LectureContent.created_at.asc()
            )
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

        return contents, pagination

    def update_content(
        self, content_id: int, content_in: LectureContentUpdate
    ) -> Optional[LectureContent]:
        """Update a content item"""
        content = (
            self.db.query(LectureContent)
            .filter(LectureContent.id == content_id)
            .first()
        )

        if not content:
            return None

        # Update fields
        for field, value in content_in.model_dump(exclude_unset=True).items():
            setattr(content, field, value)

        self.db.commit()
        self.db.refresh(content)

        return content

    # ==================== Quiz Question Management (Admin) ====================

    def get_quiz_questions(self, content_id: int) -> Optional[LectureContent]:
        """Return the lecture content (including quiz questions) for admin review."""
        content = (
            self.db.query(LectureContent)
            .filter(LectureContent.id == content_id)
            .first()
        )

        if not content or content.content_type != "quiz":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Quiz content not found"
            )

        return content

    def edit_quiz_question(
        self, content_id: int, question_index: int, question_data: dict
    ) -> LectureContent:
        """Edit a single quiz question inside a lecture content (admin only)."""
        content = (
            self.db.query(LectureContent)
            .filter(LectureContent.id == content_id)
            .first()
        )

        if not content or content.content_type != "quiz":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Quiz content not found"
            )

        questions = content.questions or []
        if question_index < 0 or question_index >= len(questions):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Question index {question_index} out of range",
            )

        # Replace the question at index with provided data
        questions[question_index] = question_data

        # Mark modified and save
        from sqlalchemy.orm import attributes

        content.questions = questions
        attributes.flag_modified(content, "questions")

        self.db.commit()
        self.db.refresh(content)

        return content

    def delete_quiz_question(
        self, content_id: int, question_index: int
    ) -> LectureContent:
        """Delete a single quiz question inside a lecture content (admin only)."""
        content = (
            self.db.query(LectureContent)
            .filter(LectureContent.id == content_id)
            .first()
        )

        if not content or content.content_type != "quiz":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Quiz content not found"
            )

        questions = content.questions or []
        if question_index < 0 or question_index >= len(questions):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Question index {question_index} out of range",
            )

        # Prevent deleting last question
        if len(questions) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the last question from a quiz",
            )

        questions.pop(question_index)

        from sqlalchemy.orm import attributes

        content.questions = questions
        attributes.flag_modified(content, "questions")

        self.db.commit()
        self.db.refresh(content)

        return content

    def add_questions_to_content(
        self, content_id: int, new_questions: List[dict]
    ) -> LectureContent:
        """Add new questions to existing quiz content (admin only)."""
        content = (
            self.db.query(LectureContent)
            .filter(LectureContent.id == content_id)
            .first()
        )

        if not content or content.content_type != "quiz":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Quiz content not found"
            )

        questions = content.questions or []
        questions.extend(new_questions)

        from sqlalchemy.orm import attributes

        content.questions = questions
        attributes.flag_modified(content, "questions")

        self.db.commit()
        self.db.refresh(content)

        return content

    def delete_content(self, content_id: int) -> bool:
        """Delete a content item"""
        content = (
            self.db.query(LectureContent)
            .filter(LectureContent.id == content_id)
            .first()
        )

        if not content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Content not found",
            )

        self.db.delete(content)
        self.db.commit()

        return True
