import logging
from io import BytesIO
from typing import Any, Dict, List, Optional

import fitz  # PyMuPDF
import pytesseract
from fastapi import HTTPException, UploadFile
from PIL import Image

from app.utils.ai_component.image_utils import (
    process_image,
    remove_text_from_image,
    should_skip_image,
)
from app.utils.prompts import (
    get_image_question_prompt,
    get_image_question_system_message,
)

logger = logging.getLogger(__name__)


class PDFImageGeneratorMixin:
    async def generate_questions_from_pdf_images(
        self,
        file: UploadFile,
        difficulty: str = "medium",
        questions_per_image: int = 1,
        max_size: int = 600,
        quality: int = 40,
    ) -> List[Dict[str, Any]]:
        """
        Extract images from PDF, OCR the text, and generate questions based on image content

        Args:
            file: Uploaded PDF file
            difficulty: Question difficulty (easy, medium, hard)
            questions_per_image: Number of questions to generate per image
            max_size: Maximum image dimension for compression
            quality: JPEG compression quality (lower = smaller file)

        Returns:
            List of question dictionaries with embedded images
        """
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="File must be a PDF")

        try:
            contents = await file.read()
            doc = fitz.open(stream=contents, filetype="pdf")

            # Track which pages should be skipped (same logic as extract_text_from_pdf)
            skip_pages = set()
            pages_content = {}

            # First pass: Extract text from all pages and determine which to skip
            for page_num, page in enumerate(doc, 1):
                try:
                    text = page.get_text()
                    if text and text.strip():
                        pages_content[page_num] = text.strip()
                    else:
                        # No text found, might need OCR but mark as potential skip
                        skip_pages.add(page_num)
                except Exception as e:
                    logger.warning(
                        f"Failed to extract text from page {page_num}: {str(e)}"
                    )
                    skip_pages.add(page_num)

            # Apply the same filtering logic as in explain_pdf_content
            skip_keywords = [
                "thank you",
                "thanks",
                "شكراً",
                "شكر",
                "any questions",
                "أي أسئلة",
                "prof.",
                "professor",
                "dr.",
                "doctor",
                "د.",
                "دكتور",
                "بروفيسور",
                "introduction",
                "مقدمة",
                "by prof",
                "بواسطة",
                "author",
                "مؤلف",
                "references",
                "مراجع",
                "bibliography",
                "قائمة المراجع",
                "acknowledgments",
                "شكر وتقدير",
                "table of contents",
                "فهرس",
                "index",
                "دليل",
                "glossary",
                "قاموس مصطلحات",
            ]

            for page_num, content in list(pages_content.items()):
                content_lower = content.lower()

                # Skip pages that are too short (less than 5 words)
                if len(content_lower.split()) < 5:
                    skip_pages.add(page_num)
                    continue

                # Skip pages containing skip keywords
                for keyword in skip_keywords:
                    if keyword.lower() in content_lower:
                        skip_pages.add(page_num)
                        break

                # Skip first page if it looks like a title page
                if page_num == 1 and len(content_lower.split()) < 50:
                    skip_pages.add(page_num)
                    continue

                # Skip last page if it looks like conclusion/thanks
                if page_num == doc.page_count and len(content_lower.split()) < 30:
                    skip_pages.add(page_num)
                    continue

            logger.info(f"Skipping pages: {sorted(skip_pages)}")

            # Second pass: Extract images from non-skipped pages
            all_questions = []

            for page_num, page in enumerate(doc, 1):
                # Skip if page is in skip list
                if page_num in skip_pages:
                    logger.info(f"Skipping page {page_num} (filtered out)")
                    continue

                page_full_text = pages_content.get(page_num, "")
                images = page.get_images(full=True)

                for img_index, img in enumerate(images):
                    try:
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]

                        # Load image with PIL
                        image = Image.open(BytesIO(image_bytes))

                        # Skip unwanted images
                        if should_skip_image(image):
                            logger.info(
                                f"Skipping small/transparent image on page {page_num}"
                            )
                            continue

                        # OCR to detect text in image
                        text_in_image = pytesseract.image_to_string(
                            image, lang="eng+ara"
                        ).strip()
                        if not text_in_image:
                            logger.info(
                                f"Skipping image on page {page_num} - no text detected"
                            )
                            continue

                        # Remove text from image before processing
                        image_without_text = remove_text_from_image(image)

                        # Process and compress image (without text)
                        img_base64 = process_image(
                            image_without_text, max_size, quality
                        )

                        logger.info(
                            f"Processing image on page {page_num}: {len(img_base64)} chars"
                        )

                        # Generate questions for this image
                        prompt = get_image_question_prompt(
                            image_text=text_in_image,
                            page_text=page_full_text,
                            page_number=page_num,
                            difficulty=difficulty,
                            count=questions_per_image,
                        )

                        response_text = await self.generate_completion(
                            prompt=prompt,
                            system_message=get_image_question_system_message(),
                            temperature=0.75,
                            max_tokens=2000,
                        )

                        result = self._extract_json_from_response(response_text)

                        # Add the encoded image to each question
                        if isinstance(result, dict) and "questions" in result:
                            for question in result["questions"]:
                                question["image"] = img_base64
                                question["content_page_number"] = page_num
                                question["question_type"] = "image"
                                all_questions.append(question)
                        else:
                            logger.warning(
                                f"Unexpected response format for page {page_num}"
                            )

                    except Exception as e:
                        logger.error(
                            f"Error processing page {page_num}, image {img_index + 1}: {str(e)}"
                        )
                        continue

            doc.close()
            await file.seek(0)

            if not all_questions:
                logger.warning("No images with text found in PDF")
                return []

            logger.info(f"Generated {len(all_questions)} image-based questions")
            return all_questions

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to process PDF for image questions: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=f"Failed to process PDF file for images: {str(e)}",
            )
        finally:
            await file.seek(0)

    async def generate_questions_from_pdf_path_images(
        self,
        pdf_path: str,
        difficulty: str = "medium",
        questions_per_image: int = 1,
        max_size: int = 600,
        quality: int = 40,
    ) -> List[Dict[str, Any]]:
        """
        Extract images from PDF path, OCR the text, and generate questions based on image content
        Useful for background tasks or admin scripts where file is already saved.

        Args:
            pdf_path: Path to the PDF file
            difficulty: Question difficulty (easy, medium, hard)
            questions_per_image: Number of questions to generate per image
            max_size: Maximum image dimension for compression
            quality: JPEG compression quality (lower = smaller file)

        Returns:
            List of question dictionaries with embedded images
        """
        try:
            doc = fitz.open(pdf_path)

            # Track which pages should be skipped (same logic as extract_text_from_pdf_path)
            skip_pages = set()
            pages_content = {}

            # First pass: Extract text from all pages and determine which to skip
            for page_num, page in enumerate(doc, 1):
                try:
                    text = page.get_text()
                    if text and text.strip():
                        pages_content[page_num] = text.strip()
                    else:
                        skip_pages.add(page_num)
                except Exception as e:
                    logger.warning(
                        f"Failed to extract text from page {page_num}: {str(e)}"
                    )
                    skip_pages.add(page_num)

            # Apply the same filtering logic
            skip_keywords = [
                "thank you",
                "thanks",
                "شكراً",
                "شكر",
                "any questions",
                "أي أسئلة",
                "prof.",
                "professor",
                "dr.",
                "doctor",
                "د.",
                "دكتور",
                "بروفيسور",
                "introduction",
                "مقدمة",
                "by prof",
                "بواسطة",
                "author",
                "مؤلف",
                "references",
                "مراجع",
                "bibliography",
                "قائمة المراجع",
                "acknowledgments",
                "شكر وتقدير",
                "table of contents",
                "فهرس",
                "index",
                "دليل",
                "glossary",
                "قاموس مصطلحات",
            ]

            for page_num, content in list(pages_content.items()):
                content_lower = content.lower()

                if len(content_lower.split()) < 5:
                    skip_pages.add(page_num)
                    continue

                for keyword in skip_keywords:
                    if keyword.lower() in content_lower:
                        skip_pages.add(page_num)
                        break

                if page_num == 1 and len(content_lower.split()) < 50:
                    skip_pages.add(page_num)
                    continue

                if page_num == doc.page_count and len(content_lower.split()) < 30:
                    skip_pages.add(page_num)
                    continue

            logger.info(f"Skipping pages: {sorted(skip_pages)}")

            # Second pass: Extract images from non-skipped pages
            all_questions = []

            for page_num, page in enumerate(doc, 1):
                if page_num in skip_pages:
                    logger.info(f"Skipping page {page_num} (filtered out)")
                    continue

                page_full_text = pages_content.get(page_num, "")
                images = page.get_images(full=True)

                for img_index, img in enumerate(images):
                    try:
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]

                        image = Image.open(BytesIO(image_bytes))

                        if should_skip_image(image):
                            logger.info(
                                f"Skipping small/transparent image on page {page_num}"
                            )
                            continue

                        text_in_image = pytesseract.image_to_string(
                            image, lang="eng+ara"
                        ).strip()
                        if not text_in_image:
                            logger.info(
                                f"Skipping image on page {page_num} - no text detected"
                            )
                            continue

                        image_without_text = remove_text_from_image(image)
                        img_base64 = process_image(
                            image_without_text, max_size, quality
                        )

                        logger.info(
                            f"Processing image on page {page_num}: {len(img_base64)} chars"
                        )

                        prompt = get_image_question_prompt(
                            image_text=text_in_image,
                            page_text=page_full_text,
                            page_number=page_num,
                            difficulty=difficulty,
                            count=questions_per_image,
                        )

                        response_text = await self.generate_completion(
                            prompt=prompt,
                            system_message=get_image_question_system_message(),
                            temperature=0.75,
                            max_tokens=2000,
                        )

                        result = self._extract_json_from_response(response_text)

                        if isinstance(result, dict) and "questions" in result:
                            for question in result["questions"]:
                                question["image"] = img_base64
                                question["content_page_number"] = page_num
                                question["question_type"] = "image"
                                all_questions.append(question)
                        else:
                            logger.warning(
                                f"Unexpected response format for page {page_num}"
                            )

                    except Exception as e:
                        logger.error(
                            f"Error processing page {page_num}, image {img_index + 1}: {str(e)}"
                        )
                        continue

            doc.close()

            if not all_questions:
                logger.warning("No images with text found in PDF")
                return []

            logger.info(f"Generated {len(all_questions)} image-based questions")
            return all_questions

        except Exception as e:
            logger.error(f"Failed to process PDF for image questions: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=f"Failed to process PDF file for images: {str(e)}",
            )

    async def generate_questions_with_images_from_pdf(
        self,
        file: UploadFile,
        difficulty: str = "medium",
        total_count: int = 10,
        question_type: str = "multiple_choice",
        notes: Optional[str] = None,
        previous_questions: Optional[List[str]] = None,
        image_percentage: float = 0.15,  # 15% image questions by default
        max_image_size: int = 600,
        image_quality: int = 40,
    ) -> Dict[str, Any]:
        """
        Generate questions from PDF with a mix of text-based and image-based questions

        Process:
        1. Extract and filter pages ONCE (skip intro/conclusion/reference pages)
        2. Generate normal text questions using filtered pages (85-90% of total)
        3. Extract images from THE SAME filtered pages and generate image questions (10-15% of total)
        4. Merge and return combined results

        Args:
            file: Uploaded PDF file
            difficulty: Question difficulty (easy, medium, hard)
            total_count: Total number of questions to generate
            question_type: Type of text questions (multiple_choice, true_false, essay, mixed)
            notes: Optional instructions for question generation
            previous_questions: Optional list of previously generated questions
            image_percentage: Percentage of image questions (0.10 = 10%, 0.15 = 15%)
            max_image_size: Maximum image dimension for compression
            image_quality: JPEG compression quality

        Returns:
            Dictionary with combined normal and image questions
        """
        # Calculate question distribution
        image_count = max(1, int(total_count * image_percentage))  # At least 1
        normal_count = total_count - image_count

        logger.info(
            f"Generating {total_count} total questions: {normal_count} normal + {image_count} image-based"
        )

        # Step 0: Extract and filter pages ONCE to ensure consistency
        logger.info("Step 0/3: Extracting and filtering PDF pages...")
        try:
            contents = await file.read()
            doc = fitz.open(stream=contents, filetype="pdf")

            skip_pages = set()
            pages_content = {}
            pages_with_no_text = []

            # First pass: Extract text from all pages
            for page_num, page in enumerate(doc, 1):
                try:
                    text = page.get_text()
                    if text and text.strip():
                        pages_content[page_num] = text.strip()
                    else:
                        pages_with_no_text.append(page_num)
                except Exception as e:
                    logger.warning(
                        f"Failed to extract text from page {page_num}: {str(e)}"
                    )
                    pages_with_no_text.append(page_num)

            # Second pass: Use OCR for pages with no text or very short text
            # This matches logic in app/utils/ai_component/pdf_text.py
            pages_with_short_text = [
                p_num for p_num, content in pages_content.items() 
                if len(content.split()) < 5
            ]
            
            # Combine pages that need OCR
            pages_needing_ocr = sorted(set(pages_with_no_text) | set(pages_with_short_text))
            
            if pages_needing_ocr:
                logger.info(f"Using OCR for pages: {pages_needing_ocr}")
                try:
                    for page_num in pages_needing_ocr:
                        try:
                            # Load page (0-indexed)
                            page = doc.load_page(page_num - 1)
                            # Get image from page
                            pix = page.get_pixmap(
                                matrix=fitz.Matrix(2, 2)
                            )  # 2x zoom for better OCR
                            img_data = pix.tobytes("png")
                            image = Image.open(BytesIO(img_data))

                            # Perform OCR on the image
                            ocr_text = pytesseract.image_to_string(
                                image, lang="eng+ara"
                            )
                            
                            if ocr_text and ocr_text.strip():
                                ocr_text = ocr_text.strip()
                                # Only use OCR text if it yields substantive content (>= 5 words)
                                if len(ocr_text.split()) >= 5:
                                    pages_content[page_num] = ocr_text
                                    # Remove from no_text list if it was there
                                    if page_num in pages_with_no_text:
                                        pages_with_no_text.remove(page_num)
                                    logger.info(f"Replaced/Added text on page {page_num} with OCR content")
                                else:
                                    # Still empty/short after OCR
                                    if page_num in pages_with_no_text:
                                        skip_pages.add(page_num)
                            else:
                                if page_num in pages_with_no_text:
                                    skip_pages.add(page_num)
                        except Exception as e:
                            logger.warning(f"OCR failed for page {page_num}: {str(e)}")
                            if page_num in pages_with_no_text:
                                skip_pages.add(page_num)
                            continue
                except Exception as e:
                     logger.warning(f"Failed to setup OCR: {str(e)}")

            # Apply robust filtering (Title, Keywords, Conclusion)
            skip_keywords = [
                "thank you",
                "thanks",
                "شكراً",
                "شكر",
                "any questions",
                "أي أسئلة",
                "prof.",
                "professor",
                "dr.",
                "doctor",
                "د.",
                "دكتور",
                "بروفيسور",
                "introduction",
                "مقدمة",
                "by prof",
                "بواسطة",
                "author",
                "مؤلف",
                "references",
                "مراجع",
                "bibliography",
                "قائمة المراجع",
                "acknowledgments",
                "شكر وتقدير",
                "table of contents",
                "فهرس",
                "index",
                "دليل",
                "glossary",
                "قاموس مصطلحات",
            ]

            for page_num, content in list(pages_content.items()):
                content_lower = content.lower()
                
                # Filter 1: Too short
                if len(content_lower.split()) < 5:
                    logger.info(f"Skipping page {page_num}: too short")
                    skip_pages.add(page_num)
                    continue

                # Filter 2: Keywords
                should_skip = False
                for keyword in skip_keywords:
                    if keyword.lower() in content_lower:
                        logger.info(f"Skipping page {page_num}: matches keyword '{keyword}'")
                        skip_pages.add(page_num)
                        should_skip = True
                        break
                if should_skip:
                    continue

                # Filter 3: Title Page (First page with limited content)
                if page_num == 1 and len(content_lower.split()) < 50:
                    logger.info(f"Skipping page {page_num}: likely title page")
                    skip_pages.add(page_num)
                    continue
                
                # Filter 4: Conclusion/Last Page
                if page_num == doc.page_count and len(content_lower.split()) < 30:
                    logger.info(f"Skipping page {page_num}: likely conclusion page")
                    skip_pages.add(page_num)
                    continue

            doc.close()

            # Get valid pages (non-skipped)
            valid_pages = sorted(
                [p for p in pages_content.keys() if p not in skip_pages]
            )
            logger.info(f"Pages to use: {valid_pages} (skipped: {sorted(list(skip_pages))})")

            if not valid_pages:
                raise HTTPException(
                    status_code=400,
                    detail="No valid content pages found in PDF after filtering",
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to extract PDF pages: {str(e)}")
            raise HTTPException(
                status_code=400, detail=f"Failed to process PDF: {str(e)}"
            )
        finally:
            await file.seek(0)

        # Step 1: Generate normal text-based questions
        # Note: We pass the ORIGINAL file. If we wanted to enforce filtering on text questions,
        # we would need to pass filtered text. Currently, this restricts IMAGE questions to filtered pages.

        normal_questions = await self.generate_questions_from_pdf(
            file=file,
            difficulty=difficulty,
            count=normal_count,
            question_type=question_type,
            notes=notes,
            previous_questions=previous_questions,
        )

        # Reset file pointer for image processing
        await file.seek(0)

        # Step 2: Generate image-based questions from THE SAME filtered pages
        logger.info(
            f"Step 2/3: Generating {image_count} image questions from filtered pages..."
        )

        try:
            contents = await file.read()
            doc = fitz.open(stream=contents, filetype="pdf")

            # Collect all valid images from ONLY the valid (non-skipped) pages
            image_data_list = []

            for page_num in valid_pages:  # Use ONLY valid pages
                page = doc.load_page(page_num - 1)  # 0-indexed
                page_full_text = pages_content.get(page_num, "")
                images = page.get_images(full=True)

                for img_index, img in enumerate(images):
                    try:
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        image = Image.open(BytesIO(image_bytes))

                        if should_skip_image(image):
                            continue

                        text_in_image = pytesseract.image_to_string(
                            image, lang="eng+ara"
                        ).strip()
                        if not text_in_image:
                            continue

                        image_without_text = remove_text_from_image(image)
                        img_base64 = process_image(
                            image_without_text, max_image_size, image_quality
                        )

                        image_data_list.append(
                            {
                                "page_number": page_num,
                                "page_text": page_full_text,
                                "image_text": text_in_image,
                                "image_base64": img_base64,
                            }
                        )

                        # Stop if we have enough images
                        if len(image_data_list) >= image_count:
                            break

                    except Exception as e:
                        logger.error(
                            f"Error processing image on page {page_num}: {str(e)}"
                        )
                        continue

                if len(image_data_list) >= image_count:
                    break

            doc.close()

            # Generate questions one by one for each image
            image_questions = []
            for idx, img_data in enumerate(image_data_list[:image_count], 1):
                try:
                    logger.info(
                        f"Generating question {idx}/{image_count} for image on page {img_data['page_number']}"
                    )

                    prompt = get_image_question_prompt(
                        image_text=img_data["image_text"],
                        page_text=img_data["page_text"],
                        page_number=img_data["page_number"],
                        difficulty=difficulty,
                        count=1,  # One question at a time
                    )

                    response_text = await self.generate_completion(
                        prompt=prompt,
                        system_message=get_image_question_system_message(),
                        temperature=0.75,
                        max_tokens=1500,
                    )

                    result = self._extract_json_from_response(response_text)

                    # Add image to the question (not sent to AI)
                    if isinstance(result, dict) and "questions" in result:
                        for question in result["questions"]:
                            question["image"] = img_data["image_base64"]
                            question["content_page_number"] = img_data["page_number"]
                            question["question_type"] = "image"
                            image_questions.append(question)

                except Exception as e:
                    logger.error(f"Failed to generate image question {idx}: {str(e)}")
                    continue

            logger.info(
                f"Successfully generated {len(image_questions)} image questions"
            )

        except Exception as e:
            logger.error(f"Failed to process images: {str(e)}")
            image_questions = []

        finally:
            await file.seek(0)

        # Step 3: Merge questions
        logger.info("Step 3/3: Merging questions...")
        all_questions = []

        # Add normal questions
        if isinstance(normal_questions, dict) and "questions" in normal_questions:
            all_questions.extend(normal_questions["questions"])
        elif isinstance(normal_questions, list):
            all_questions.extend(normal_questions)

        # Add image questions
        all_questions.extend(image_questions)

        logger.info(
            f"Total questions generated: {len(all_questions)} ({len(all_questions) - len(image_questions)} normal + {len(image_questions)} image)"
        )

        return {
            "questions": all_questions,
            "total_count": len(all_questions),
            "normal_count": len(all_questions) - len(image_questions),
            "image_count": len(image_questions),
            "pages_used": valid_pages,
            "pages_skipped": sorted(skip_pages),
        }

    async def generate_questions_with_images_from_pdf_path(
        self,
        pdf_path: str,
        difficulty: str = "medium",
        total_count: int = 10,
        question_type: str = "multiple_choice",
        notes: Optional[str] = None,
        previous_questions: Optional[List[str]] = None,
        image_percentage: float = 0.15,
        max_image_size: int = 600,
        image_quality: int = 40,
    ) -> Dict[str, Any]:
        """
        Generate questions from PDF path with a mix of text-based and image-based questions
        Useful for background tasks or admin scripts where file is already saved.

        Process:
        0. Extract and filter all pages ONCE (skip intro/conclusion/reference pages)
        1. Generate normal text questions (85-90% of total) using filtered pages
        2. Extract images ONLY from valid pages and generate questions one-by-one (10-15% of total)
        3. Merge and return combined results

        Args:
            pdf_path: Path to the PDF file
            difficulty: Question difficulty
            total_count: Total number of questions
            question_type: Type of text questions
            notes: Optional instructions
            previous_questions: Optional list of previous questions
            image_percentage: Percentage of image questions (0.10-0.15)
            max_image_size: Maximum image dimension
            image_quality: JPEG quality

        Returns:
            Dictionary with combined normal and image questions, plus pages_used and pages_skipped
        """
        # Calculate distribution
        image_count = max(1, int(total_count * image_percentage))
        normal_count = total_count - image_count

        logger.info(
            f"Generating {total_count} total questions from {pdf_path}: {normal_count} normal + {image_count} image-based"
        )

        # Step 0: Extract and filter all pages ONCE
        logger.info("Step 0/3: Extracting and filtering PDF pages...")
        try:
            doc = fitz.open(pdf_path)

            skip_pages = set()
            pages_content = {}

            # Extract text from all pages
            for page_num, page in enumerate(doc, 1):
                try:
                    text = page.get_text()
                    if text and text.strip():
                        pages_content[page_num] = text.strip()
                    else:
                        skip_pages.add(page_num)
                except Exception as e:
                    logger.warning(
                        f"Failed to extract text from page {page_num}: {str(e)}"
                    )
                    skip_pages.add(page_num)

            # Apply content-based filtering (same keywords as generate_questions_from_pdf_path)
            skip_keywords = [
                "thank you",
                "thanks",
                "شكراً",
                "شكر",
                "any questions",
                "أي أسئلة",
                "prof.",
                "professor",
                "dr.",
                "doctor",
                "د.",
                "دكتور",
                "بروفيسور",
                "introduction",
                "مقدمة",
                "by prof",
                "بواسطة",
                "author",
                "مؤلف",
                "references",
                "مراجع",
                "bibliography",
                "قائمة المراجع",
                "acknowledgments",
                "شكر وتقدير",
                "table of contents",
                "فهرس",
                "index",
                "دليل",
                "glossary",
                "قاموس مصطلحات",
            ]

            for page_num, content in list(pages_content.items()):
                content_lower = content.lower()
                # Skip pages with very little content
                if len(content_lower.split()) < 5:
                    skip_pages.add(page_num)
                    continue
                # Skip pages with specific keywords
                for keyword in skip_keywords:
                    if keyword.lower() in content_lower:
                        skip_pages.add(page_num)
                        break
                # Skip first page if it's an intro/title page
                if page_num == 1 and len(content_lower.split()) < 50:
                    skip_pages.add(page_num)
                    continue
                # Skip last page if it's a conclusion/thank you page
                if page_num == doc.page_count and len(content_lower.split()) < 30:
                    skip_pages.add(page_num)
                    continue

            # Get list of valid pages
            valid_pages = [p for p in pages_content.keys() if p not in skip_pages]

            logger.info(
                f"Filtered pages: {len(valid_pages)} valid, {len(skip_pages)} skipped. "
                f"Valid pages: {valid_pages}, Skipped pages: {sorted(skip_pages)}"
            )

            doc.close()

        except Exception as e:
            logger.error(f"Failed to filter PDF pages: {str(e)}")
            valid_pages = []
            skip_pages = set()

        # Step 1: Generate normal questions (using filtered content)
        logger.info(
            f"Step 1/3: Generating {normal_count} normal questions from valid pages..."
        )
        normal_questions = await self.generate_questions_from_pdf_path(
            pdf_path=pdf_path,
            difficulty=difficulty,
            count=normal_count,
            question_type=question_type,
            notes=notes,
            previous_questions=previous_questions,
        )

        # Step 2: Generate image questions one by one (ONLY from valid pages)
        logger.info(
            f"Step 2/3: Generating {image_count} image questions from valid pages..."
        )

        try:
            doc = fitz.open(pdf_path)

            # Collect valid images (ONLY from pages not in skip_pages)
            image_data_list = []

            for page_num in valid_pages:  # Use ONLY valid_pages, not all pages
                page = doc.load_page(page_num - 1)  # PyMuPDF uses 0-based indexing
                page_full_text = pages_content.get(page_num, "")
                images = page.get_images(full=True)

                for img_index, img in enumerate(images):
                    try:
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        image = Image.open(BytesIO(image_bytes))

                        if should_skip_image(image):
                            continue

                        text_in_image = pytesseract.image_to_string(
                            image, lang="eng+ara"
                        ).strip()
                        if not text_in_image:
                            continue

                        image_without_text = remove_text_from_image(image)
                        img_base64 = process_image(
                            image_without_text, max_image_size, image_quality
                        )

                        image_data_list.append(
                            {
                                "page_number": page_num,
                                "page_text": page_full_text,
                                "image_text": text_in_image,
                                "image_base64": img_base64,
                            }
                        )

                        # Stop if we have enough images
                        if len(image_data_list) >= image_count:
                            break

                    except Exception as e:
                        logger.error(
                            f"Error processing image on page {page_num}: {str(e)}"
                        )
                        continue

                if len(image_data_list) >= image_count:
                    break

            doc.close()

            # Generate questions one by one for each image
            image_questions = []
            for idx, img_data in enumerate(image_data_list[:image_count], 1):
                try:
                    logger.info(
                        f"Generating question {idx}/{image_count} for image on page {img_data['page_number']}"
                    )

                    prompt = get_image_question_prompt(
                        image_text=img_data["image_text"],
                        page_text=img_data["page_text"],
                        page_number=img_data["page_number"],
                        difficulty=difficulty,
                        count=1,  # One question at a time
                    )

                    response_text = await self.generate_completion(
                        prompt=prompt,
                        system_message=get_image_question_system_message(),
                        temperature=0.75,
                        max_tokens=1500,
                    )

                    result = self._extract_json_from_response(response_text)

                    # Add image to the question (not sent to AI)
                    if isinstance(result, dict) and "questions" in result:
                        for question in result["questions"]:
                            question["image"] = img_data["image_base64"]
                            question["content_page_number"] = img_data["page_number"]
                            question["question_type"] = "image"
                            image_questions.append(question)

                except Exception as e:
                    logger.error(f"Failed to generate image question {idx}: {str(e)}")
                    continue

            logger.info(
                f"Successfully generated {len(image_questions)} image questions"
            )

        except Exception as e:
            logger.error(f"Failed to process images: {str(e)}")
            image_questions = []

        # Step 3: Merge questions
        logger.info("Step 3/3: Merging questions...")
        all_questions = []

        # Add normal questions
        if isinstance(normal_questions, dict) and "questions" in normal_questions:
            all_questions.extend(normal_questions["questions"])
        elif isinstance(normal_questions, list):
            all_questions.extend(normal_questions)

        # Add image questions
        all_questions.extend(image_questions)

        logger.info(
            f"Total questions generated: {len(all_questions)} ({len(all_questions) - len(image_questions)} normal + {len(image_questions)} image)"
        )

        return {
            "questions": all_questions,
            "total_count": len(all_questions),
            "normal_count": len(all_questions) - len(image_questions),
            "image_count": len(image_questions),
            "pages_used": valid_pages,
            "pages_skipped": sorted(skip_pages),
        }
