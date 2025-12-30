import os
import argparse
import glob
import logging
from pathlib import Path
from dotenv import load_dotenv

# Import logic directly from the app to ensure consistency
from app.utils.question_pdf_generator import (
    extract_pdf_text,
    generate_questions,
    save_questions_to_pdf,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def main():
    # Load environment variables
    load_dotenv()

    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Batch generate questions from a folder of numbered PDFs."
    )
    parser.add_argument(
        "folder", type=str, help="Path to the folder containing PDFs (e.g., /path/to/pdfs)"
    )
    args = parser.parse_args()

    input_folder = Path(args.folder)

    if not input_folder.exists() or not input_folder.is_dir():
        logger.error(f"❌ Input folder does not exist: {input_folder}")
        return

    # Find all numbered PDFs: 1.pdf, 2.pdf, etc.
    pdf_files = sorted(input_folder.glob("*.pdf"))
    if not pdf_files:
        logger.warning(f"⚠️ No PDF files found in {input_folder}")
        return

    logger.info(f"📂 Found {len(pdf_files)} PDF files in directory.")

    for pdf_path in pdf_files:
        filename = pdf_path.name
        # Try to extract the number from the filename ("1.pdf" -> "1")
        # Assuming simple format "X.pdf"
        try:
            file_num = filename.rsplit(".", 1)[0]
            # Verify if it looks like a number (optional, but requested numbered PDFs)
            # If user has "Lecture1.pdf" instead of "1.pdf", we can still treat "Lecture1" as the ID.
            # But prompt said: "1.pdf, 2.pdf..."
        except Exception:
            file_num = filename  # Fallback

        logger.info(f"🔹 Processing: {filename} (ID: {file_num})")

        try:
            # 1. Extract Text
            logger.info(f"   📖 Extracting text from {filename}...")
            content = extract_pdf_text(str(pdf_path))

            if not content:
                logger.error(f"   ❌ No content extracted from {filename}. Skipping.")
                continue

            # -----------------------------------------------------
            # 2. Generate Mixed Questions (40 Questions)
            # -----------------------------------------------------
            logger.info("   🧠 Generating 40 Mixed Questions (MCQ/TF)...")
            mixed_data = generate_questions(
                content=content, num_questions=40, question_type="mixed"
            )
            
            # Add metadata titles
            mixed_data["title"] = f"Exam {file_num} - Mixed Assessment"

            mixed_filename = input_folder / f"{file_num}-mixed-multichoice-40.pdf"
            save_questions_to_pdf(mixed_data, str(mixed_filename))
            logger.info(f"   ✅ Saved Mixed PDF: {mixed_filename.name}")

            # -----------------------------------------------------
            # 3. Generate Essay Questions (10 Questions)
            # -----------------------------------------------------
            logger.info("   🧠 Generating 10 Essay Questions...")
            essay_data = generate_questions(
                content=content, num_questions=10, question_type="essay"
            )

            # Add metadata titles
            essay_data["title"] = f"Exam {file_num} - Essay Assessment"

            essay_filename = input_folder / f"{file_num}-essay-10.pdf"
            save_questions_to_pdf(essay_data, str(essay_filename))
            logger.info(f"   ✅ Saved Essay PDF: {essay_filename.name}")

        except Exception as e:
            logger.error(f"   ❌ Failed to process {filename}: {str(e)}")

    logger.info("🎉 Batch generation complete!")


if __name__ == "__main__":
    main()
