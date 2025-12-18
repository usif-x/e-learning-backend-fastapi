"""
Router Integration Example for Image-Based Questions

Add this to your existing routers to enable image question generation
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.utils.ai import ai_service

router = APIRouter(prefix="/image-questions", tags=["Image Questions"])


@router.post("/generate-from-upload")
async def generate_image_questions_from_upload(
    file: UploadFile = File(...),
    difficulty: str = "medium",
    questions_per_image: int = 1,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate image-based questions from an uploaded PDF file

    Args:
        file: PDF file to process
        difficulty: Question difficulty (easy, medium, hard)
        questions_per_image: Number of questions to generate per image

    Returns:
        List of generated questions with embedded images
    """
    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Validate difficulty
    if difficulty not in ["easy", "medium", "hard"]:
        raise HTTPException(
            status_code=400, detail="Difficulty must be easy, medium, or hard"
        )

    # Validate questions per image
    if questions_per_image < 1 or questions_per_image > 3:
        raise HTTPException(
            status_code=400,
            detail="questions_per_image must be between 1 and 3",
        )

    try:
        # Generate questions from images
        questions = await ai_service.generate_questions_from_pdf_images(
            file=file,
            difficulty=difficulty,
            questions_per_image=questions_per_image,
            max_size=600,
            quality=40,
        )

        if not questions:
            return {
                "success": True,
                "message": "No images with text found in the PDF",
                "questions_generated": 0,
                "questions": [],
            }

        # TODO: Save to database here
        # Example:
        # for q in questions:
        #     new_question = PracticeQuiz(
        #         quiz_source_id=quiz_source_id,
        #         question_type="image",
        #         question_category=q["question_category"],
        #         question_text=q["question_text"],
        #         image=q["image"],
        #         options=q["options"],
        #         correct_answer=q["correct_answer"],
        #         explanation=q["explanation"],
        #         explanation_ar=q["explanation_ar"],
        #         content_page_number=q["content_page_number"],
        #     )
        #     db.add(new_question)
        # db.commit()

        return {
            "success": True,
            "questions_generated": len(questions),
            "questions": questions,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate questions from images: {str(e)}",
        )


@router.post("/generate-from-quiz-source/{quiz_source_id}")
async def generate_image_questions_from_quiz_source(
    quiz_source_id: int,
    difficulty: str = "medium",
    questions_per_image: int = 1,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate image-based questions from an existing quiz source PDF

    Args:
        quiz_source_id: ID of the quiz source containing the PDF
        difficulty: Question difficulty
        questions_per_image: Number of questions per image

    Returns:
        Generated questions saved to database
    """
    # TODO: Import your QuizSource model
    # from app.models.quiz_source import QuizSource

    # Get the quiz source
    # quiz_source = db.query(QuizSource).filter(QuizSource.id == quiz_source_id).first()
    # if not quiz_source:
    #     raise HTTPException(status_code=404, detail="Quiz source not found")

    # Check if user has access
    # if quiz_source.user_id != current_user.id and not current_user.is_admin:
    #     raise HTTPException(status_code=403, detail="Access denied")

    # Get PDF file path
    # pdf_path = quiz_source.file_path
    # if not pdf_path or not os.path.exists(pdf_path):
    #     raise HTTPException(status_code=404, detail="PDF file not found")

    try:
        # For demo purposes, using a placeholder path
        pdf_path = "path/to/pdf/file.pdf"

        # Generate questions
        questions = await ai_service.generate_questions_from_pdf_path_images(
            pdf_path=pdf_path,
            difficulty=difficulty,
            questions_per_image=questions_per_image,
            max_size=600,
            quality=40,
        )

        if not questions:
            return {
                "success": True,
                "message": "No images with text found in the PDF",
                "questions_generated": 0,
            }

        # Save questions to database
        # saved_count = 0
        # for q in questions:
        #     new_question = PracticeQuiz(
        #         quiz_source_id=quiz_source_id,
        #         question_type="image",
        #         question_category=q["question_category"],
        #         question_text=q["question_text"],
        #         image=q["image"],
        #         options=q["options"],
        #         correct_answer=q["correct_answer"],
        #         explanation=q["explanation"],
        #         explanation_ar=q["explanation_ar"],
        #         content_page_number=q["content_page_number"],
        #     )
        #     db.add(new_question)
        #     saved_count += 1
        #
        # db.commit()

        return {
            "success": True,
            "questions_generated": len(questions),
            "message": f"Successfully generated {len(questions)} image-based questions",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate questions: {str(e)}",
        )


@router.get("/preview/{question_id}")
async def preview_image_question(
    question_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Preview an image-based question

    Returns the question with decoded image for frontend display
    """
    # TODO: Import your PracticeQuiz model
    # from app.models.practice_quiz import PracticeQuiz

    # Get the question
    # question = db.query(PracticeQuiz).filter(PracticeQuiz.id == question_id).first()
    # if not question:
    #     raise HTTPException(status_code=404, detail="Question not found")

    # Check if it's an image question
    # if question.question_type != "image":
    #     raise HTTPException(status_code=400, detail="Not an image question")

    # Return question data for frontend
    return {
        "id": question_id,
        "question_text": "Sample question text",
        "image": "base64_encoded_image_here",
        "options": ["Option A", "Option B", "Option C", "Option D"],
        "correct_answer": "Option A",
        "explanation": "Explanation here",
        "explanation_ar": "الشرح بالعربي",
        "content_page_number": 1,
    }


# Add this router to your main.py:
# from app.routers import image_questions
# app.include_router(image_questions.router)
