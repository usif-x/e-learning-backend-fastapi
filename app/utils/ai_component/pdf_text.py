import logging
import re
from io import BytesIO
from typing import Any, Dict, List, Optional

import fitz  # PyMuPDF
import pytesseract
from fastapi import HTTPException, UploadFile
from PIL import Image

from app.utils.prompts import get_explanation_prompt, get_explanation_system_message

logger = logging.getLogger(__name__)


class PDFTextProcessorMixin:
    async def extract_text_from_pdf(self, file: UploadFile) -> str:
        """
        Extract text content from a PDF file with OCR support for image-based PDFs

        Args:
            file: Uploaded PDF file

        Returns:
            Extracted text content

        Raises:
            HTTPException: If PDF processing fails
        """
        try:
            contents = await file.read()
            # Open PDF from bytes using PyMuPDF
            doc = fitz.open(stream=contents, filetype="pdf")

            text_content = []
            pages_with_no_text = []

            # First pass: Try to extract text using PyMuPDF
            for page_num, page in enumerate(doc, 1):
                try:
                    text = page.get_text()
                    if text and text.strip():
                        text_content.append(f"--- Page {page_num} ---\n{text}")
                    else:
                        pages_with_no_text.append(page_num)
                except Exception as e:
                    logger.warning(
                        f"Failed to extract text from page {page_num}: {str(e)}"
                    )
                    pages_with_no_text.append(page_num)

            # Also consider pages with very short text (<5 words) as OCR candidates
            # Helper to extract word count from a page string
            def get_page_word_count(page_str: str) -> int:
                # Extract content after the header line
                lines = page_str.split("\n", 1)
                content = lines[1] if len(lines) > 1 else ""
                return len(content.split())

            pages_with_short_text = [
                int(re.search(r"Page (\d+)", p).group(1))
                for p in text_content
                if get_page_word_count(p) < 5
            ]

            pages_needing_ocr = sorted(
                set(pages_with_no_text) | set(pages_with_short_text)
            )

            # Second pass: Use OCR for pages with no text or very short text
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
                                # Prefer OCR if it yields >=5 words
                                if len(ocr_text.split()) >= 5:
                                    # Check if we need to replace existing short-text entry
                                    replaced = False
                                    for idx, entry in enumerate(text_content):
                                        match = re.search(r"Page (\d+)", entry)
                                        if match and int(match.group(1)) == page_num:
                                            text_content[idx] = (
                                                f"--- Page {page_num} (OCR) ---\n{ocr_text}"
                                            )
                                            replaced = True
                                            logger.info(
                                                f"Replaced short text on page {page_num} with OCR content"
                                            )
                                            break
                                    if not replaced:
                                        text_content.append(
                                            f"--- Page {page_num} (OCR) ---\n{ocr_text}"
                                        )
                                        logger.info(
                                            f"Successfully extracted OCR text from page {page_num}"
                                        )
                        except Exception as e:
                            logger.warning(f"OCR failed for page {page_num}: {str(e)}")
                            continue
                except Exception as e:
                    logger.warning(f"Failed to convert PDF to images for OCR: {str(e)}")

            if not text_content:
                raise HTTPException(
                    status_code=400,
                    detail="No text content found in PDF. The file may be empty or OCR failed to extract text.",
                )

            # Sort by page number to maintain order
            text_content.sort(key=lambda x: int(re.search(r"Page (\d+)", x).group(1)))

            return "\n\n".join(text_content)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to process PDF: {str(e)}")
            raise HTTPException(
                status_code=400, detail=f"Failed to process PDF file: {str(e)}"
            )
        finally:
            await file.seek(0)

    async def extract_text_from_pdf_path(self, pdf_path: str) -> str:
        """
        Extract text content from a PDF file path with OCR support for image-based PDFs

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Extracted text content

        Raises:
            HTTPException: If PDF processing fails
        """
        try:
            # Open PDF directly from path using PyMuPDF
            doc = fitz.open(pdf_path)

            text_content = []
            pages_with_no_text = []

            # First pass: Try to extract text using PyMuPDF
            for page_num, page in enumerate(doc, 1):
                try:
                    text = page.get_text()
                    if text and text.strip():
                        text_content.append(f"--- Page {page_num} ---\n{text}")
                    else:
                        pages_with_no_text.append(page_num)
                except Exception as e:
                    logger.warning(
                        f"Failed to extract text from page {page_num}: {str(e)}"
                    )
                    pages_with_no_text.append(page_num)

            # Also consider pages with very short text (<5 words) as OCR candidates
            def get_page_word_count(page_str: str) -> int:
                lines = page_str.split("\n", 1)
                content = lines[1] if len(lines) > 1 else ""
                return len(content.split())

            pages_with_short_text = [
                int(re.search(r"Page (\d+)", p).group(1))
                for p in text_content
                if get_page_word_count(p) < 5
            ]

            pages_needing_ocr = sorted(
                set(pages_with_no_text) | set(pages_with_short_text)
            )

            # Second pass: Use OCR for pages with no text or very short text
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
                                if len(ocr_text.split()) >= 5:
                                    replaced = False
                                    for idx, entry in enumerate(text_content):
                                        match = re.search(r"Page (\d+)", entry)
                                        if match and int(match.group(1)) == page_num:
                                            text_content[idx] = (
                                                f"--- Page {page_num} (OCR) ---\n{ocr_text}"
                                            )
                                            replaced = True
                                            logger.info(
                                                f"Replaced short text on page {page_num} with OCR content"
                                            )
                                            break
                                    if not replaced:
                                        text_content.append(
                                            f"--- Page {page_num} (OCR) ---\n{ocr_text}"
                                        )
                                        logger.info(
                                            f"Successfully extracted OCR text from page {page_num}"
                                        )
                        except Exception as e:
                            logger.warning(f"OCR failed for page {page_num}: {str(e)}")
                            continue
                except Exception as e:
                    logger.warning(f"Failed to convert PDF to images for OCR: {str(e)}")

            if not text_content:
                raise HTTPException(
                    status_code=400,
                    detail="No text content found in PDF. The file may be empty or OCR failed to extract text.",
                )

            # Sort by page number to maintain order
            text_content.sort(key=lambda x: int(re.search(r"Page (\d+)", x).group(1)))

            return "\n\n".join(text_content)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to process PDF: {str(e)}")
            raise HTTPException(
                status_code=400, detail=f"Failed to process PDF file: {str(e)}"
            )

    async def explain_pdf_content(
        self,
        file: UploadFile,
        include_examples: bool = True,
        detailed_explanation: bool = True,
    ) -> Dict[str, Any]:
        """
        Extract and explain PDF content page by page in Egyptian Arabic

        Args:
            file: Uploaded PDF file
            include_examples: Whether to include examples in explanations
            detailed_explanation: Whether to provide detailed explanations

        Returns:
            Dictionary with page explanations in JSON format
        """
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="File must be a PDF")

        # Extract text from each page with OCR support
        contents = await file.read()
        # Use PyMuPDF
        doc = fitz.open(stream=contents, filetype="pdf")

        pages_content = []
        pages_with_no_text = []

        # First pass: Try to extract text using PyMuPDF
        for page_num, page in enumerate(doc, 1):
            try:
                text = page.get_text()
                if text and text.strip():
                    pages_content.append(
                        {"page_number": page_num, "content": text.strip()}
                    )
                else:
                    pages_with_no_text.append(page_num)
            except Exception as e:
                logger.warning(f"Failed to extract text from page {page_num}: {str(e)}")
                pages_with_no_text.append(page_num)

        # Second pass: Use OCR for pages with no text (likely image-based)
        # Also attempt OCR for pages that have very short extracted text
        # (e.g., a title) because the rest of the page might be an image.
        pages_with_short_text = [
            p["page_number"] for p in pages_content if len(p["content"].split()) < 5
        ]

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
                        ocr_text = pytesseract.image_to_string(image, lang="eng+ara")
                        if ocr_text and ocr_text.strip():
                            ocr_text = ocr_text.strip()
                            # Prefer OCR text only if it yields substantive content
                            if len(ocr_text.split()) >= 5:
                                replaced = False
                                for idx, p in enumerate(pages_content):
                                    if p["page_number"] == page_num:
                                        pages_content[idx]["content"] = ocr_text
                                        replaced = True
                                        logger.info(
                                            f"Replaced short text on page {page_num} with OCR content"
                                        )
                                        break
                                if not replaced:
                                    pages_content.append(
                                        {
                                            "page_number": page_num,
                                            "content": ocr_text,
                                        }
                                    )
                            else:
                                logger.info(
                                    f"OCR on page {page_num} returned only {len(ocr_text.split())} words; keeping original text if present"
                                )
                    except Exception as e:
                        logger.warning(f"OCR failed for page {page_num}: {str(e)}")
                        continue
            except Exception as e:
                logger.warning(f"Failed to convert PDF to images for OCR: {str(e)}")

        # Sort pages by page number to maintain order
        pages_content.sort(key=lambda x: x["page_number"])

        if not pages_content:
            raise HTTPException(
                status_code=400,
                detail="No text content found in PDF. The file may be empty or contain only images.",
            )

        # Filter out non-content pages (intro, conclusion, thank you pages, etc.)
        filtered_pages = []
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

        for page_data in pages_content:
            content = page_data["content"].lower()
            page_num = page_data["page_number"]

            # Skip pages that are too short (less than 5 words)
            if len(content.split()) < 5:
                logger.info(
                    f"Skipping page {page_num}: too short ({len(content.split())} words)"
                )
                continue

            # Skip pages containing skip keywords
            should_skip = False
            for keyword in skip_keywords:
                if keyword.lower() in content:
                    logger.info(
                        f"Skipping page {page_num}: contains keyword '{keyword}'"
                    )
                    should_skip = True
                    break

            if should_skip:
                continue

            # Skip first page if it looks like a title page
            if page_num == 1 and len(content.split()) < 50:
                logger.info(f"Skipping page {page_num}: likely title page")
                continue

            # Skip last page if it looks like conclusion/thanks
            if page_num == len(pages_content) and len(content.split()) < 30:
                logger.info(f"Skipping page {page_num}: likely conclusion page")
                continue

            filtered_pages.append(page_data)

        if not filtered_pages:
            raise HTTPException(
                status_code=400,
                detail="No meaningful content pages found in PDF. All pages appear to be introductory, conclusion, or reference pages.",
            )

        # Create system message for PDF explanation
        explanation_system_message = get_explanation_system_message()

        # Process pages in batches to avoid timeout on large PDFs
        # Each batch will be sent as one request
        BATCH_SIZE = (
            10  # Process 10 pages per request - optimized for better throughput
        )
        MAX_BATCH_CONTENT_LENGTH = 8000  # Max chars per batch (smaller for reliability)

        explained_pages = []

        # Split filtered_pages into batches
        for batch_start in range(0, len(filtered_pages), BATCH_SIZE):
            batch_pages = filtered_pages[batch_start : batch_start + BATCH_SIZE]

            # Merge batch content
            merged_content_parts = []
            for page_data in batch_pages:
                page_num = page_data["page_number"]
                content = page_data["content"]
                merged_content_parts.append(f"━━━ صفحة {page_num} ━━━\n{content}")

            merged_content = "\n\n".join(merged_content_parts)

            # Truncate if too long
            if len(merged_content) > MAX_BATCH_CONTENT_LENGTH:
                merged_content = (
                    merged_content[:MAX_BATCH_CONTENT_LENGTH]
                    + "\n\n[Content truncated...]"
                )

            # Build prompt for this batch
            examples_instruction = (
                " وخلي الشرح يشمل أمثلة عملية" if include_examples else ""
            )
            detail_instruction = (
                " شرح مفصل وواضح" if detailed_explanation else "شرح مختصر"
            )

            page_numbers = [p["page_number"] for p in batch_pages]

            prompt = get_explanation_prompt(
                detail_instruction, examples_instruction, merged_content, page_numbers
            )

            # Try with retries
            max_retries = 2
            batch_explained = None

            for attempt in range(max_retries + 1):
                try:
                    response_text = await self.generate_completion(
                        prompt=prompt,
                        system_message=explanation_system_message,
                        temperature=0.7,
                        max_tokens=8000,  # Reduced for faster response
                    )

                    # Parse the JSON response
                    result = self._extract_json_from_response(response_text)

                    if isinstance(result, dict) and "pages" in result:
                        batch_explained = result["pages"]
                    else:
                        # Fallback: treat as single explanation for batch
                        batch_explained = [
                            {
                                "page_number": p["page_number"],
                                "explanation": str(result),
                            }
                            for p in batch_pages
                        ]
                    break  # Success, exit retry loop

                except Exception as e:
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} failed for pages {page_numbers}: {str(e)}"
                    )
                    if attempt < max_retries:
                        # Wait 3 seconds before retrying to give API server time to recover
                        import asyncio

                        await asyncio.sleep(3)
                    if attempt == max_retries:
                        # All retries failed
                        logger.error(
                            f"All retries failed for pages {page_numbers}: {str(e)}"
                        )
                        batch_explained = [
                            {
                                "page_number": p["page_number"],
                                "explanation": "معلش، حصل مشكلة في الشرح. حاول تاني.",
                            }
                            for p in batch_pages
                        ]

            if batch_explained:
                explained_pages.extend(batch_explained)

        # Reset file pointer
        await file.seek(0)

        return {
            "pages": explained_pages,
            "total_pages": len(explained_pages),
            "filtered_pages": len(pages_content) - len(filtered_pages),
            "language": "Egyptian Arabic",
            "medical_terms_preserved": True,
        }
