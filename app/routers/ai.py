# app/routers/ai.py
"""
AI-powered educational content generation endpoints
"""

from typing import List, Optional

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile

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
    notes: Optional[str] = Form(None),
    previous_questions: Optional[List[str]] = Body(None),
    current_user: User = Depends(get_current_user),
):
    """
    Generate educational questions for a specific topic

    Args:
        topic: The subject/topic for questions
        difficulty: Question difficulty (easy, medium, hard)
        count: Number of questions to generate (1-10)
        question_type: Type (multiple_choice, true_false, essay, mixed)
        notes: Optional custom instructions (e.g., "Focus on practical applications", "Avoid topic X", "Include real-world examples")
        previous_questions: Optional list of previously generated question texts to avoid duplicates
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

    if question_type not in ["multiple_choice", "true_false", "essay", "mixed"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid question type. Choose: multiple_choice, true_false, essay, mixed",
        )

    questions = await ai_service.generate_questions(
        topic=topic,
        difficulty=difficulty,
        count=count,
        question_type=question_type,
        notes=notes,
        previous_questions=previous_questions,
    )

    return {"success": True, "topic": topic, "questions": questions}


@router.post("/generate-questions-from-pdf")
async def generate_questions_from_pdf(
    file: UploadFile = File(...),
    difficulty: str = Form("medium"),
    count: int = Form(5),
    question_type: str = Form("multiple_choice"),
    notes: Optional[str] = Form(None),
    previous_questions: Optional[List[str]] = Body(None),
    current_user: User = Depends(get_current_user),
):
    """
    Extract content from PDF and generate questions

    Args:
        file: PDF file to extract content from
        difficulty: Question difficulty (easy, medium, hard)
        count: Number of questions to generate (1-10)
        question_type: Type (multiple_choice, true_false, essay, mixed)
        notes: Optional custom instructions (e.g., "Focus on practical applications", "Avoid topic X", "Include real-world examples")
        previous_questions: Optional list of previously generated question texts to avoid duplicates
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

    if question_type not in ["multiple_choice", "true_false", "essay", "mixed"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid question type. Choose: multiple_choice, true_false, essay, mixed",
        )

    questions = await ai_service.generate_questions_from_pdf(
        file=file,
        difficulty=difficulty,
        count=count,
        question_type=question_type,
        notes=notes,
        previous_questions=previous_questions,
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
    notes: Optional[str] = Form(None),
    previous_questions: Optional[List[str]] = Body(None),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Admin endpoint to generate educational questions

    Args:
        topic: The subject/topic for questions
        difficulty: Question difficulty (easy, medium, hard)
        count: Number of questions to generate (1-60 for admins)
        question_type: Type of questions
        notes: Optional custom instructions (e.g., "Focus on practical applications", "Avoid topic X", "Include real-world examples")
        previous_questions: Optional list of previously generated question texts to avoid duplicates
        current_admin: Authenticated admin

    Returns:
        Generated questions in JSON format with bilingual explanations
    """
    if count < 1 or count > 60:
        raise HTTPException(status_code=400, detail="Count must be between 1 and 60")

    questions = await ai_service.generate_questions(
        topic=topic,
        difficulty=difficulty,
        count=count,
        question_type=question_type,
        notes=notes,
        previous_questions=previous_questions,
    )

    return {
        "success": True,
        "topic": topic,
        "questions": questions,
        "admin_id": current_admin.id,
    }


@router.post("/admin/pdf-generate-questions")
async def admin_generate_questions_from_pdf(
    file: UploadFile = File(...),
    difficulty: str = Form("medium"),
    count: int = Form(5),
    question_type: str = Form("multiple_choice"),
    notes: Optional[str] = Form(None),
    previous_questions: Optional[List[str]] = Body(None),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Admin endpoint to generate questions from PDF

    Args:
        file: PDF file to extract content from
        difficulty: Question difficulty (easy, medium, hard)
        count: Number of questions to generate (1-60 for admins)
        question_type: Type (multiple_choice, true_false, essay, mixed)
        notes: Optional custom instructions (e.g., "Focus on practical applications", "Avoid topic X", "Include real-world examples")
        previous_questions: Optional list of previously generated question texts to avoid duplicates
        current_admin: Authenticated admin

    Returns:
        Generated questions based on PDF content with bilingual explanations
    """
    if count < 1 or count > 60:
        raise HTTPException(status_code=400, detail="Count must be between 1 and 60")

    if difficulty not in ["easy", "medium", "hard"]:
        raise HTTPException(
            status_code=400, detail="Difficulty must be easy, medium, or hard"
        )

    if question_type not in ["multiple_choice", "true_false", "essay", "mixed"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid question type. Choose: multiple_choice, true_false, essay, mixed",
        )

    questions = await ai_service.generate_questions_from_pdf(
        file=file,
        difficulty=difficulty,
        count=count,
        question_type=question_type,
        notes=notes,
        previous_questions=previous_questions,
    )

    return {
        "success": True,
        "filename": file.filename,
        "questions": questions,
        "admin_id": current_admin.id,
    }


@router.post("/explain-pdf-content")
async def explain_pdf_content(
    file: UploadFile = File(...),
    include_examples: bool = Form(True),
    detailed_explanation: bool = Form(True),
    current_user: User = Depends(get_current_user),
):
    """
    Extract and explain PDF content page by page in Egyptian Arabic

    Args:
        file: PDF file to explain
        include_examples: Whether to include examples in explanations (default: True)
        detailed_explanation: Whether to provide detailed explanations (default: True)
        current_user: Authenticated user

    Returns:
        Page-by-page explanations in Egyptian Arabic with medical terms preserved
    """
    explanation_result = await ai_service.explain_pdf_content(
        file=file,
        include_examples=include_examples,
        detailed_explanation=detailed_explanation,
    )

    return {
        "success": True,
        "filename": file.filename,
        "pages": explanation_result["pages"],
        "total_pages": explanation_result["total_pages"],
        "filtered_pages": explanation_result.get("filtered_pages", 0),
        "language": explanation_result["language"],
        "medical_terms_preserved": explanation_result["medical_terms_preserved"],
    }


@router.post("/generate-mixed-questions-from-pdf")
async def generate_mixed_questions_from_pdf(
    file: UploadFile = File(...),
    difficulty: str = Form("medium"),
    total_count: int = Form(20),
    question_type: str = Form("multiple_choice"),
    notes: Optional[str] = Form(None),
    previous_questions: Optional[List[str]] = Body(None),
    image_percentage: float = Form(0.15),
    current_user: User = Depends(get_current_user),
):
    """
    Generate mixed questions from PDF: 85% normal + 15% image-based questions

    This endpoint processes the PDF in two steps:
    1. Generates normal text-based questions (85%)
    2. Extracts images and generates image-based questions one-by-one (15%)
    3. Merges both types and returns combined results

    Args:
        file: PDF file to process
        difficulty: Question difficulty (easy, medium, hard)
        total_count: Total number of questions to generate (5-30 for users)
        question_type: Type for normal questions (multiple_choice, true_false, mixed)
        notes: Optional custom instructions
        previous_questions: Optional list of previously generated questions to avoid
        image_percentage: Percentage of image questions (0.10-0.20, default: 0.15)
        current_user: Authenticated user

    Returns:
        Combined normal and image-based questions with embedded base64 images
    """
    if total_count < 5 or total_count > 30:
        raise HTTPException(
            status_code=400, detail="Total count must be between 5 and 30"
        )

    if difficulty not in ["easy", "medium", "hard"]:
        raise HTTPException(
            status_code=400, detail="Difficulty must be easy, medium, or hard"
        )

    if question_type not in ["multiple_choice", "true_false", "mixed"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid question type. Choose: multiple_choice, true_false, mixed",
        )

    if image_percentage < 0.10 or image_percentage > 0.20:
        raise HTTPException(
            status_code=400,
            detail="Image percentage must be between 0.10 (10%) and 0.20 (20%)",
        )

    result = await ai_service.generate_questions_with_images_from_pdf(
        file=file,
        difficulty=difficulty,
        total_count=total_count,
        question_type=question_type,
        notes=notes,
        previous_questions=previous_questions,
        image_percentage=image_percentage,
        max_image_size=600,
        image_quality=40,
    )

    return {
        "success": True,
        "filename": file.filename,
        "total_generated": result["total_count"],
        "normal_questions": result["normal_count"],
        "image_questions": result["image_count"],
        "questions": result["questions"],
    }


@router.post("/explain-topic-content")
async def explain_topic_content(
    topic: str = Form(...),
    include_examples: bool = Form(True),
    detailed_explanation: bool = Form(True),
    subject_breakdown: bool = Form(True),
    current_user: User = Depends(get_current_user),
):
    """
    Explain a medical topic comprehensively in Egyptian Arabic, organized by subjects

    Args:
        topic: The medical topic to explain (e.g., "diabetes", "hypertension", "cardiology")
        include_examples: Whether to include examples in explanations (default: True)
        detailed_explanation: Whether to provide detailed explanations (default: True)
        subject_breakdown: Whether to break down into sub-subjects (default: True)
        current_user: Authenticated user

    Returns:
        Comprehensive topic explanation organized by subjects in Egyptian Arabic
    """
    if len(topic.strip()) < 2:
        raise HTTPException(
            status_code=400, detail="Topic must be at least 2 characters"
        )

    explanation_result = await ai_service.explain_topic_content(
        topic=topic.strip(),
        include_examples=include_examples,
        detailed_explanation=detailed_explanation,
        subject_breakdown=subject_breakdown,
    )

    return {
        "success": True,
        "topic": explanation_result.get("topic", topic),
        "subjects": explanation_result["subjects"],
        "language": explanation_result["language"],
        "medical_terms_preserved": explanation_result["medical_terms_preserved"],
    }


@router.post("/admin/explain-topic-content")
async def admin_explain_topic_content(
    topic: str = Form(...),
    include_examples: bool = Form(True),
    detailed_explanation: bool = Form(True),
    subject_breakdown: bool = Form(True),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Admin endpoint to explain a medical topic comprehensively in Egyptian Arabic, organized by subjects

    Args:
        topic: The medical topic to explain (e.g., "diabetes", "hypertension", "cardiology")
        include_examples: Whether to include examples in explanations (default: True)
        detailed_explanation: Whether to provide detailed explanations (default: True)
        subject_breakdown: Whether to break down into sub-subjects (default: True)
        current_admin: Authenticated admin

    Returns:
        Comprehensive topic explanation organized by subjects in Egyptian Arabic
    """
    if len(topic.strip()) < 2:
        raise HTTPException(
            status_code=400, detail="Topic must be at least 2 characters"
        )

    explanation_result = await ai_service.explain_topic_content(
        topic=topic.strip(),
        include_examples=include_examples,
        detailed_explanation=detailed_explanation,
        subject_breakdown=subject_breakdown,
    )

    return {
        "success": True,
        "topic": explanation_result.get("topic", topic),
        "subjects": explanation_result["subjects"],
        "language": explanation_result["language"],
        "medical_terms_preserved": explanation_result["medical_terms_preserved"],
        "admin_id": current_admin.id,
    }


@router.post("/admin/generate-mixed-questions-from-pdf")
async def admin_generate_mixed_questions_from_pdf(
    file: UploadFile = File(...),
    difficulty: str = Form("medium"),
    total_count: int = Form(20),
    question_type: str = Form("multiple_choice"),
    notes: Optional[str] = Form(None),
    previous_questions: Optional[List[str]] = Body(None),
    image_percentage: float = Form(0.15),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Admin endpoint to generate mixed questions from PDF: 85% normal + 15% image-based

    Process:
    1. Generates normal text-based questions (85%)
    2. Extracts images and generates image-based questions one-by-one (15%)
    3. Merges both types and returns combined results

    Args:
        file: PDF file to process
        difficulty: Question difficulty (easy, medium, hard)
        total_count: Total number of questions to generate (5-100 for admins)
        question_type: Type for normal questions (multiple_choice, true_false, mixed)
        notes: Optional custom instructions
        previous_questions: Optional list of previously generated questions to avoid
        image_percentage: Percentage of image questions (0.10-0.20, default: 0.15)
        current_admin: Authenticated admin

    Returns:
        Combined normal and image-based questions with embedded base64 images
    """
    if total_count < 5 or total_count > 100:
        raise HTTPException(
            status_code=400, detail="Total count must be between 5 and 100"
        )

    if difficulty not in ["easy", "medium", "hard"]:
        raise HTTPException(
            status_code=400, detail="Difficulty must be easy, medium, or hard"
        )

    if question_type not in ["multiple_choice", "true_false", "mixed"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid question type. Choose: multiple_choice, true_false, mixed",
        )

    if image_percentage < 0.10 or image_percentage > 0.20:
        raise HTTPException(
            status_code=400,
            detail="Image percentage must be between 0.10 (10%) and 0.20 (20%)",
        )

    result = await ai_service.generate_questions_with_images_from_pdf(
        file=file,
        difficulty=difficulty,
        total_count=total_count,
        question_type=question_type,
        notes=notes,
        previous_questions=previous_questions,
        image_percentage=image_percentage,
        max_image_size=600,
        image_quality=40,
    )

    return {
        "success": True,
        "filename": file.filename,
        "total_generated": result["total_count"],
        "normal_questions": result["normal_count"],
        "image_questions": result["image_count"],
        "questions": result["questions"],
        "admin_id": current_admin.id,
    }
