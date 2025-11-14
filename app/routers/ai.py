# app/routers/ai.py
"""
AI-powered educational content generation endpoints
"""

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.core.dependencies import get_current_admin, get_current_user
from app.models.admin import Admin
from app.models.user import User
from app.utils.ai import ai_service

router = APIRouter(prefix="/ai", tags=["AI"])


@router.post("/generate-questions")
async def generate_questions(
    topic: str = Form(...),
    difficulty: str = Form("medium"),
    count: int = Form(5),
    question_type: str = Form("multiple_choice"),
    current_user: User = Depends(get_current_user),
):
    """
    Generate educational questions for a specific topic

    Args:
        topic: The subject/topic for questions
        difficulty: Question difficulty (easy, medium, hard)
        count: Number of questions to generate (1-10)
        question_type: Type (multiple_choice, essay, short_answer, true_false)
        current_user: Authenticated user

    Returns:
        Generated questions in JSON format with bilingual explanations
    """
    if count < 1 or count > 10:
        raise HTTPException(status_code=400, detail="Count must be between 1 and 10")

    if difficulty not in ["easy", "medium", "hard"]:
        raise HTTPException(
            status_code=400, detail="Difficulty must be easy, medium, or hard"
        )

    if question_type not in ["multiple_choice", "essay", "short_answer", "true_false"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid question type. Choose: multiple_choice, essay, short_answer, true_false",
        )

    questions = await ai_service.generate_questions(
        topic=topic,
        difficulty=difficulty,
        count=count,
        question_type=question_type,
    )

    return {"success": True, "topic": topic, "questions": questions}


@router.post("/generate-questions-from-pdf")
async def generate_questions_from_pdf(
    file: UploadFile = File(...),
    difficulty: str = Form("medium"),
    count: int = Form(5),
    question_type: str = Form("multiple_choice"),
    current_user: User = Depends(get_current_user),
):
    """
    Extract content from PDF and generate questions

    Args:
        file: PDF file to extract content from
        difficulty: Question difficulty (easy, medium, hard)
        count: Number of questions to generate (1-10)
        question_type: Type (multiple_choice, essay, short_answer)
        current_user: Authenticated user

    Returns:
        Generated questions based on PDF content with bilingual explanations
    """
    if count < 1 or count > 10:
        raise HTTPException(status_code=400, detail="Count must be between 1 and 10")

    if difficulty not in ["easy", "medium", "hard"]:
        raise HTTPException(
            status_code=400, detail="Difficulty must be easy, medium, or hard"
        )

    if question_type not in ["multiple_choice", "essay", "short_answer"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid question type. Choose: multiple_choice, essay, short_answer",
        )

    questions = await ai_service.generate_questions_from_pdf(
        file=file,
        difficulty=difficulty,
        count=count,
        question_type=question_type,
    )

    return {
        "success": True,
        "filename": file.filename,
        "questions": questions,
    }


@router.post("/summarize")
async def summarize_content(
    content: str = Form(...),
    max_length: Optional[int] = Form(None),
    current_user: User = Depends(get_current_user),
):
    """
    Summarize educational content

    Args:
        content: The content to summarize
        max_length: Optional maximum length in words
        current_user: Authenticated user

    Returns:
        Summarized content
    """
    if len(content) < 50:
        raise HTTPException(
            status_code=400, detail="Content must be at least 50 characters"
        )

    summary = await ai_service.summarize_content(content=content, max_length=max_length)

    return {"success": True, "summary": summary}


@router.post("/explain")
async def explain_concept(
    concept: str = Form(...),
    level: str = Form("beginner"),
    language: str = Form("en"),
    current_user: User = Depends(get_current_user),
):
    """
    Explain a concept at different complexity levels and languages

    Args:
        concept: The concept to explain
        level: Complexity level (beginner, intermediate, advanced)
        language: Language for explanation (en for English, ar for Arabic/Egypt)
        current_user: Authenticated user

    Returns:
        Explanation text in requested language
    """
    if level not in ["beginner", "intermediate", "advanced"]:
        raise HTTPException(
            status_code=400,
            detail="Level must be beginner, intermediate, or advanced",
        )

    if language not in ["en", "ar"]:
        raise HTTPException(
            status_code=400,
            detail="Language must be en (English) or ar (Arabic/Egypt)",
        )

    explanation = await ai_service.explain_concept(
        concept=concept, level=level, language=language
    )

    return {
        "success": True,
        "concept": concept,
        "level": level,
        "language": language,
        "explanation": explanation,
    }


@router.post("/extract-pdf-text")
async def extract_pdf_text(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Extract text content from a PDF file

    Args:
        file: PDF file to extract text from
        current_user: Authenticated user

    Returns:
        Extracted text content
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    text_content = await ai_service.extract_text_from_pdf(file)

    return {
        "success": True,
        "filename": file.filename,
        "content": text_content,
        "length": len(text_content),
    }


# Admin-only endpoints
@router.post("/admin/generate-questions")
async def admin_generate_questions(
    topic: str = Form(...),
    difficulty: str = Form("medium"),
    count: int = Form(5),
    question_type: str = Form("multiple_choice"),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Admin endpoint to generate educational questions

    Args:
        topic: The subject/topic for questions
        difficulty: Question difficulty (easy, medium, hard)
        count: Number of questions to generate (1-20 for admins)
        question_type: Type of questions
        current_admin: Authenticated admin

    Returns:
        Generated questions in JSON format with bilingual explanations
    """
    if count < 1 or count > 20:
        raise HTTPException(status_code=400, detail="Count must be between 1 and 20")

    questions = await ai_service.generate_questions(
        topic=topic,
        difficulty=difficulty,
        count=count,
        question_type=question_type,
    )

    return {
        "success": True,
        "topic": topic,
        "questions": questions,
        "admin_id": current_admin.id,
    }
