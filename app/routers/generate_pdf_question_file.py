import os
import shutil
import tempfile
from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse

# Import your existing functions
from app.utils.question_pdf_generator import (
    extract_pdf_text,
    generate_questions,
    save_questions_to_pdf,
)

# Create router with prefix and tags
router = APIRouter(prefix="/pdf-question", tags=["AI"])


@router.post("/generate-exam/")
async def generate_exam(
    background_tasks: BackgroundTasks,
    num_questions: int = Form(
        ..., description="Number of questions to generate", ge=1, le=100
    ),
    question_type: Literal["mcq", "true_false", "essay", "mixed"] = Form(
        "mixed", description="Type of questions"
    ),
    difficulty: Literal["easy", "medium", "hard", "mixed"] = Form(
        "mixed", description="Difficulty level"
    ),
    exam_title: str = Form("Examination", description="Title of the exam"),
    include_answers: bool = Form(True, description="Include answer key in PDF"),
    content: Optional[str] = Form(
        None, description="Text content for generating questions"
    ),
    pdf_file: Optional[UploadFile] = File(
        None, description="PDF file to extract content from"
    ),
):
    """
    Generate exam questions and return PDF file.

    You can provide either:
    - `content`: Plain text content
    - `pdf_file`: PDF file to extract text from

    At least one must be provided.
    """

    # Validate input
    if not content and not pdf_file:
        raise HTTPException(
            status_code=400, detail="Either 'content' or 'pdf_file' must be provided"
        )

    try:
        # Extract content from PDF if provided
        if pdf_file:
            # Validate file type
            if not pdf_file.filename.endswith(".pdf"):
                raise HTTPException(
                    status_code=400, detail="Only PDF files are accepted"
                )

            # Save uploaded PDF temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
                shutil.copyfileobj(pdf_file.file, temp_pdf)
                temp_pdf_path = temp_pdf.name

            try:
                content = await run_in_threadpool(extract_pdf_text, temp_pdf_path)
                if len(content.strip()) < 100:
                    raise HTTPException(
                        status_code=400,
                        detail="PDF content too short (minimum 100 characters required)",
                    )
            finally:
                # Clean up temp PDF
                os.unlink(temp_pdf_path)

        # Validate content length
        if not content or len(content.strip()) < 50:
            raise HTTPException(
                status_code=400,
                detail="Content is too short to generate meaningful questions",
            )

        # Generate questions
        questions_data = await run_in_threadpool(
            generate_questions,
            content=content,
            num_questions=num_questions,
            question_type=question_type,
            difficulty=difficulty,
        )

        # Check if enough questions were generated
        generated_count = len(questions_data.get("questions", []))
        if generated_count == 0:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate questions. Please try again.",
            )

        # Create temporary output PDF
        temp_output = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        temp_output.close()

        # Generate PDF
        output_path = await run_in_threadpool(
            save_questions_to_pdf,
            questions_data=questions_data,
            output_file=temp_output.name,
            include_answers=include_answers,
        )

        # Schedule cleanup task
        background_tasks.add_task(cleanup_file, output_path)

        # Return PDF file with explicit CORS headers
        response = FileResponse(
            path=output_path,
            media_type="application/pdf",
            filename=f"{exam_title.replace(' ', '_')}.pdf",
        )
        
        # Add CORS headers explicitly for file downloads
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        
        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating exam: {str(e)}")


@router.post("/generate-from-text/")
async def generate_exam_from_text(
    background_tasks: BackgroundTasks,
    content: str = Form(..., description="Text content for generating questions"),
    num_questions: int = Form(10, ge=1, le=100),
    question_type: Literal["mcq", "true_false", "essay", "mixed"] = Form("mixed"),
    difficulty: Literal["easy", "medium", "hard", "mixed"] = Form("mixed"),
    exam_title: str = Form("Examination"),
    include_answers: bool = Form(True),
):
    """
    Generate exam from plain text content only.
    Simpler endpoint that only accepts text content.
    """
    return await generate_exam(
        background_tasks=background_tasks,
        num_questions=num_questions,
        question_type=question_type,
        difficulty=difficulty,
        exam_title=exam_title,
        include_answers=include_answers,
        content=content,
        pdf_file=None,
    )


@router.post("/generate-from-pdf/")
async def generate_exam_from_pdf(
    background_tasks: BackgroundTasks,
    pdf_file: UploadFile = File(..., description="PDF file to extract content from"),
    num_questions: int = Form(10, ge=1, le=100),
    question_type: Literal["mcq", "true_false", "essay", "mixed"] = Form("mixed"),
    difficulty: Literal["easy", "medium", "hard", "mixed"] = Form("mixed"),
    exam_title: str = Form("Examination"),
    include_answers: bool = Form(True),
):
    """
    Generate exam from PDF file only.
    Simpler endpoint that only accepts PDF uploads.
    """
    return await generate_exam(
        background_tasks=background_tasks,
        num_questions=num_questions,
        question_type=question_type,
        difficulty=difficulty,
        exam_title=exam_title,
        include_answers=include_answers,
        content=None,
        pdf_file=pdf_file,
    )


@router.get("/health")
async def health_check():
    """Health check endpoint for PDF question generator."""
    return {
        "status": "healthy",
        "service": "PDF Question Generator",
        "endpoints": {
            "/pdf-question/generate-exam/": "Generate exam from text or PDF (flexible)",
            "/pdf-question/generate-from-text/": "Generate exam from text only",
            "/pdf-question/generate-from-pdf/": "Generate exam from PDF only",
        },
    }


# Background task to cleanup temporary files
def cleanup_file(file_path: str):
    """Delete temporary file after response is sent."""
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
    except Exception as e:
        print(f"Error cleaning up file {file_path}: {e}")
