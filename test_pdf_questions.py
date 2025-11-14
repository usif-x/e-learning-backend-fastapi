"""
Test script for PDF question generation
Creates a sample PDF and tests the AI service
"""

import asyncio
from io import BytesIO

from fastapi import UploadFile
from PyPDF2 import PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.utils.ai import ai_service


def create_sample_pdf() -> BytesIO:
    """Create a sample PDF with educational content"""
    buffer = BytesIO()

    # Create PDF with reportlab (if not available, use simple text)
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        # Add content
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, height - 100, "Introduction to Machine Learning")

        c.setFont("Helvetica", 12)
        y_position = height - 140

        content = [
            "Machine Learning is a subset of artificial intelligence that enables",
            "systems to learn and improve from experience without being explicitly",
            "programmed. The main types of machine learning are:",
            "",
            "1. Supervised Learning: The algorithm learns from labeled training data,",
            "   helping it to predict outcomes for unforeseen data.",
            "",
            "2. Unsupervised Learning: The algorithm finds patterns in data without",
            "   pre-existing labels.",
            "",
            "3. Reinforcement Learning: The algorithm learns by interacting with an",
            "   environment, receiving rewards or penalties for its actions.",
            "",
            "Key concepts in machine learning include:",
            "- Training data: The dataset used to train the model",
            "- Features: The input variables used to make predictions",
            "- Labels: The output variable we're trying to predict",
            "- Model: The mathematical representation of the learning algorithm",
            "",
            "Popular algorithms include Linear Regression, Decision Trees,",
            "Neural Networks, and Support Vector Machines.",
        ]

        for line in content:
            c.drawString(100, y_position, line)
            y_position -= 20

        c.save()
    except ImportError:
        # Fallback: Create simple PDF with PyPDF2
        from PyPDF2 import PdfWriter

        writer = PdfWriter()
        # Note: This is a simplified version, reportlab is better
        print("Warning: reportlab not available, using simplified PDF")

    buffer.seek(0)
    return buffer


async def test_pdf_questions():
    """Test PDF question generation"""
    print("\n" + "=" * 60)
    print("Testing PDF Question Generation")
    print("=" * 60)

    # Check configuration
    if not ai_service.is_configured():
        print("❌ AI service is not configured!")
        print("Please check your .env file for AI_API_KEY and AI_API_ENDPOINT")
        return

    print("✅ AI service is configured")

    # Create sample PDF
    print("\n📄 Creating sample PDF with ML content...")
    pdf_buffer = create_sample_pdf()

    # Create UploadFile object
    upload_file = UploadFile(
        filename="ml_introduction.pdf",
        file=pdf_buffer,
    )

    # Test 1: Multiple Choice Questions
    print("\n🔄 Testing Multiple Choice Questions...")
    try:
        result = await ai_service.generate_questions_from_pdf(
            file=upload_file,
            difficulty="medium",
            count=3,
            question_type="multiple_choice",
        )
        print("✅ Multiple Choice Questions Generated!")
        print(f"Response length: {len(result)} characters")
        print(f"\nSample output:\n{result[:500]}...")
    except Exception as e:
        print(f"❌ Failed: {str(e)}")

    # Reset file pointer
    pdf_buffer.seek(0)
    upload_file = UploadFile(filename="ml_introduction.pdf", file=pdf_buffer)

    # Test 2: Essay Questions
    print("\n🔄 Testing Essay Questions...")
    try:
        result = await ai_service.generate_questions_from_pdf(
            file=upload_file, difficulty="hard", count=2, question_type="essay"
        )
        print("✅ Essay Questions Generated!")
        print(f"Response length: {len(result)} characters")
        print(f"\nSample output:\n{result[:500]}...")
    except Exception as e:
        print(f"❌ Failed: {str(e)}")

    # Reset file pointer
    pdf_buffer.seek(0)
    upload_file = UploadFile(filename="ml_introduction.pdf", file=pdf_buffer)

    # Test 3: Extract text only
    print("\n🔄 Testing PDF Text Extraction...")
    try:
        text = await ai_service.extract_text_from_pdf(upload_file)
        print("✅ Text Extracted Successfully!")
        print(f"Extracted {len(text)} characters")
        print(f"\nSample text:\n{text[:300]}...")
    except Exception as e:
        print(f"❌ Failed: {str(e)}")

    print("\n" + "=" * 60)
    print("Testing Complete!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(test_pdf_questions())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {str(e)}")
        import traceback

        traceback.print_exc()
