import math
from typing import List, Tuple

from sqlalchemy.orm import Session

from app.models.quiz_source import QuizSource
from app.schemas.quiz_source import QuizSourceCreate, QuizSourceResponse


class QuizSourceService:
    def __init__(self, db: Session):
        self.db = db

    def create_source(
        self, source_in: QuizSourceCreate, uploaded_by: int
    ) -> QuizSource:
        """Create a new quiz source"""
        source = QuizSource(
            filename=source_in.filename,
            file_path=source_in.file_path,
            uploaded_by=uploaded_by,
        )
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source

    def get_source(self, source_id: int) -> QuizSource:
        """Get a source by ID"""
        return self.db.query(QuizSource).filter(QuizSource.id == source_id).first()

    def get_sources(
        self, page: int = 1, size: int = 50
    ) -> Tuple[List[QuizSource], dict]:
        """Get all sources with pagination"""
        query = self.db.query(QuizSource)

        total = query.count()
        offset = (page - 1) * size
        sources = (
            query.order_by(QuizSource.created_at.desc())
            .offset(offset)
            .limit(size)
            .all()
        )

        total_pages = math.ceil(total / size) if size > 0 else 0
        pagination = {
            "total": total,
            "page": page,
            "size": size,
            "total_pages": total_pages,
        }

        return sources, pagination

    def delete_source(self, source_id: int) -> bool:
        """Delete a source"""
        source = self.get_source(source_id)
        if not source:
            return False
        self.db.delete(source)
        self.db.commit()
        return True
