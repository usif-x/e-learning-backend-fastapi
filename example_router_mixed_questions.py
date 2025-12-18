"""
Router Integration Example for Mixed Questions (Normal + Image)

Add this to your existing routers to enable mixed question generation
with 10-15% image-based questions
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.utils.ai import ai_service

router = APIRouter(prefix="/questions", tags=["Question Generation"])


@router.post("/generate-mixed")
async def generate_mixed_questions(
    file: UploadFile = File(...),
    total_count: int = 20,
    difficulty: str = "medium",
    question_type: str = "multiple_choice",
    image_percentage: float = 0.15,  # 15% image questions
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate mixed questions from PDF: 85% normal + 15% image-based

    Process:
    1. Generates normal text questions first (85%)
    2. Extracts images and generates image questions one-by-one (15%)
    3. Merges and returns combined results
    4. Ready to save to database

    Args:
        file: PDF file to process
        total_count: Total number of questions (default: 20)
        difficulty: Question difficulty (easy, medium, hard)
        question_type: Type for normal questions (multiple_choice, true_false, mixed)
        image_percentage: Percentage of image questions (0.10-0.15)

    Returns:
        Combined normal and image questions
    """
    # Validate file
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Validate parameters
    if difficulty not in ["easy", "medium", "hard"]:
        raise HTTPException(
            status_code=400, detail="Difficulty must be easy, medium, or hard"
        )

    if total_count < 5 or total_count > 100:
        raise HTTPException(
            status_code=400, detail="total_count must be between 5 and 100"
        )

    if image_percentage < 0.10 or image_percentage > 0.20:
        raise HTTPException(
            status_code=400,
            detail="image_percentage must be between 0.10 (10%) and 0.20 (20%)",
        )

    try:
        # Generate mixed questions
        result = await ai_service.generate_questions_with_images_from_pdf(
            file=file,
            difficulty=difficulty,
            total_count=total_count,
            question_type=question_type,
            image_percentage=image_percentage,
            max_image_size=600,
            image_quality=40,
        )

        # Save to database
        # TODO: Implement database save logic
        # saved_count = 0
        # for q in result["questions"]:
        #     q_type = q.get("question_type", "multiple_choice")
        #
        #     new_question = PracticeQuiz(
        #         quiz_source_id=quiz_source_id,
        #         question_type=q_type,
        #         question_category=q.get("question_category", "standard"),
        #         question_text=q["question_text"],
        #         image=q.get("image"),  # Only image questions have this
        #         options=q.get("options", []),
        #         correct_answer=q["correct_answer"],
        #         explanation=q["explanation"],
        #         explanation_ar=q["explanation_ar"],
        #         content_page_number=q.get("content_page_number"),
        #     )
        #     db.add(new_question)
        #     saved_count += 1
        #
        # db.commit()

        return {
            "success": True,
            "total_generated": result["total_count"],
            "normal_questions": result["normal_count"],
            "image_questions": result["image_count"],
            "questions": result["questions"],
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate questions: {str(e)}"
        )


@router.post("/generate-mixed-from-source/{quiz_source_id}")
async def generate_mixed_questions_from_source(
    quiz_source_id: int,
    total_count: int = 20,
    difficulty: str = "medium",
    question_type: str = "multiple_choice",
    image_percentage: float = 0.15,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate mixed questions from an existing quiz source PDF

    Args:
        quiz_source_id: ID of the quiz source containing the PDF
        total_count: Total number of questions
        difficulty: Question difficulty
        question_type: Type for normal questions
        image_percentage: Percentage of image questions (0.10-0.15)

    Returns:
        Success status and question counts
    """
    # TODO: Import your QuizSource model
    # from app.models.quiz_source import QuizSource

    # Get quiz source
    # quiz_source = db.query(QuizSource).filter(QuizSource.id == quiz_source_id).first()
    # if not quiz_source:
    #     raise HTTPException(status_code=404, detail="Quiz source not found")

    # Check access
    # if quiz_source.user_id != current_user.id and not current_user.is_admin:
    #     raise HTTPException(status_code=403, detail="Access denied")

    # Get PDF path
    # pdf_path = quiz_source.file_path
    # if not pdf_path or not os.path.exists(pdf_path):
    #     raise HTTPException(status_code=404, detail="PDF file not found")

    try:
        pdf_path = "path/to/pdf/file.pdf"  # Replace with actual path

        # Generate mixed questions
        result = await ai_service.generate_questions_with_images_from_pdf_path(
            pdf_path=pdf_path,
            difficulty=difficulty,
            total_count=total_count,
            question_type=question_type,
            image_percentage=image_percentage,
            max_image_size=600,
            image_quality=40,
        )

        # Save to database
        # saved_count = 0
        # for q in result["questions"]:
        #     q_type = q.get("question_type", "multiple_choice")
        #
        #     new_question = PracticeQuiz(
        #         quiz_source_id=quiz_source_id,
        #         question_type=q_type,
        #         question_category=q.get("question_category", "standard"),
        #         question_text=q["question_text"],
        #         image=q.get("image"),
        #         options=q.get("options", []),
        #         correct_answer=q["correct_answer"],
        #         explanation=q["explanation"],
        #         explanation_ar=q["explanation_ar"],
        #         content_page_number=q.get("content_page_number"),
        #     )
        #     db.add(new_question)
        #     saved_count += 1
        #
        # db.commit()

        return {
            "success": True,
            "total_generated": result["total_count"],
            "normal_questions": result["normal_count"],
            "image_questions": result["image_count"],
            "message": f"Successfully generated {result['total_count']} questions",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate questions: {str(e)}"
        )


# Add this router to your main.py:
# from app.routers import question_generation
# app.include_router(question_generation.router)
