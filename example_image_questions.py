"""
Example script demonstrating how to generate image-based questions from PDF files

This script shows how to:
1. Generate a mix of normal and image questions (10-15% images)
2. Process questions sequentially to avoid token overflow
3. Store questions with embedded base64 images in database
"""

import asyncio
import json
from pathlib import Path

from app.utils.ai import ai_service


async def generate_mixed_questions_from_file(
    pdf_path: str, difficulty: str = "medium", total_count: int = 20
):
    """
    Generate mixed normal + image questions from a PDF file

    Args:
        pdf_path: Path to the PDF file
        difficulty: Question difficulty (easy, medium, hard)
        total_count: Total number of questions to generate

    Returns:
        Dictionary with normal and image questions
    """
    print(f"🔍 Processing PDF: {pdf_path}")
    print(f"📊 Difficulty: {difficulty}")
    print(f"📝 Total Questions: {total_count}")
    print(f"🖼️  Image Questions: ~{int(total_count * 0.15)} (15%)")
    print(f"📄 Normal Questions: ~{int(total_count * 0.85)} (85%)\n")

    try:
        # Generate mixed questions (normal + image)
        result = await ai_service.generate_questions_with_images_from_pdf_path(
            pdf_path=pdf_path,
            difficulty=difficulty,
            total_count=total_count,
            question_type="multiple_choice",
            image_percentage=0.15,  # 15% image questions
            max_image_size=600,  # Image size
            image_quality=40,  # JPEG quality
        )

        print(f"\n✅ Generation Complete!")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"Total Generated: {result['total_count']}")
        print(f"Normal Questions: {result['normal_count']}")
        print(f"Image Questions: {result['image_count']}")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        # Display summary
        for i, q in enumerate(result["questions"], 1):
            q_type = q.get("question_type", "multiple_choice")
            if q_type == "image":
                print(f"\n{i}. [IMAGE] Page {q['content_page_number']}")
                print(f"   {q['question_text'][:80]}...")
                print(f"   Image size: {len(q['image'])} chars")
            else:
                print(f"\n{i}. [NORMAL] {q['question_text'][:80]}...")

        # Save to JSON file
        output_file = "mixed_questions_output.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"\n💾 Saved to: {output_file}")

        return result

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        raise


async def save_to_database_example(result: dict):
    """
    Example of how to save mixed questions to database

    NOTE: Adapt to your actual database models
    """
    print("\n📝 Database Storage Example:")
    print("=" * 60)

    for q in result["questions"]:
        q_type = q.get("question_type", "multiple_choice")

        if q_type == "image":
            # Image question record
            db_record = {
                "question_type": "image",
                "question_category": q["question_category"],
                "question_text": q["question_text"],
                "image": q["image"],  # base64 encoded
                "options": q.get("options", []),
                "correct_answer": q["correct_answer"],
                "explanation": q["explanation"],
                "explanation_ar": q["explanation_ar"],
                "content_page_number": q["content_page_number"],
            }
            print(f"\n[IMAGE] Page {q['content_page_number']}")
            print(f"  Image: {len(db_record['image'])} chars")
        else:
            # Normal question record
            db_record = {
                "question_type": q_type,
                "question_category": q.get("question_category", "standard"),
                "question_text": q["question_text"],
                "image": None,  # No image for normal questions
                "options": q.get("options", []),
                "correct_answer": q["correct_answer"],
                "explanation": q["explanation"],
                "explanation_ar": q["explanation_ar"],
            }
            print(f"\n[NORMAL] {q['question_text'][:60]}...")

        # TODO: Save to database
        # new_question = PracticeQuiz(**db_record)
        # db.add(new_question)
    # db.commit()


async def main():
    """Main execution function"""
    print("=" * 60)
    print("🎓 Mixed Question Generator (Normal + Image)")
    print("=" * 60)

    pdf_path = "your_file.pdf"  # Replace with actual path

    if not Path(pdf_path).exists():
        print(f"\n⚠️  PDF file not found: {pdf_path}")
        print("Please update the pdf_path variable with a valid PDF file")
        return

    # Generate mixed questions
    result = await generate_mixed_questions_from_file(
        pdf_path=pdf_path, difficulty="medium", total_count=20
    )

    # Show database storage example
    if result["questions"]:
        await save_to_database_example(result)

    print("\n" + "=" * 60)
    print("✅ Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
