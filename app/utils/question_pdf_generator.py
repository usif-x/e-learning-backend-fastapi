import json
import logging
import os
import random
import re
from datetime import datetime
from typing import Dict, List, Literal

import pytesseract
import requests
from dotenv import load_dotenv
from pdf2image import convert_from_path
from PyPDF2 import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("AI_API_KEY")
DEEPSEEK_MODEL = "deepseek-chat"

logger = logging.getLogger(__name__)


# -------------------------
# Extract text from PDF with OCR support
# -------------------------
def extract_pdf_text(pdf_path: str) -> str:
    """
    Extract text from PDF with OCR support for image-based pages.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Extracted text content
    """
    try:
        reader = PdfReader(pdf_path)
        text_content = []
        pages_with_no_text = []

        # First pass: Try to extract text using PyPDF2
        for page_num, page in enumerate(reader.pages, 1):
            try:
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    text_content.append(f"--- Page {page_num} ---\n{page_text}")
                else:
                    pages_with_no_text.append(page_num)
            except Exception as e:
                logger.warning(f"Failed to extract text from page {page_num}: {str(e)}")
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

        pages_needing_ocr = sorted(set(pages_with_no_text) | set(pages_with_short_text))

        # Second pass: Use OCR for pages with no text or very short text
        if pages_needing_ocr:
            logger.info(f"Using OCR for pages: {pages_needing_ocr}")
            try:
                # Convert PDF pages to images
                images = convert_from_path(pdf_path)

                for page_num in pages_needing_ocr:
                    try:
                        if page_num <= len(images):
                            image = images[page_num - 1]
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
            raise Exception(
                "No text content found in PDF. The file may be empty or OCR failed."
            )

        # Sort by page number to maintain order
        text_content.sort(key=lambda x: int(re.search(r"Page (\d+)", x).group(1)))

        return "\n\n".join(text_content)

    except Exception as e:
        raise Exception(f"❌ Error reading PDF: {str(e)}")


# -------------------------
# Extract JSON safely
# -------------------------
def extract_json_from_response(raw_output: str) -> Dict:
    code_block_pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
    code_block_match = re.search(code_block_pattern, raw_output, flags=re.DOTALL)

    if code_block_match:
        json_str = code_block_match.group(1)
    else:
        json_match = re.search(r"\{.*\}", raw_output, flags=re.DOTALL)
        if not json_match:
            print("=" * 60)
            print("RAW OUTPUT:", raw_output)
            print("=" * 60)
            raise ValueError("❌ No JSON object found in AI output")
        json_str = json_match.group(0)

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"❌ Invalid JSON format: {str(e)}")


# -------------------------
# Shuffle MCQ answers
# -------------------------
def shuffle_mcq_answers(questions_data: Dict) -> Dict:
    for q in questions_data["questions"]:
        if q["type"] == "mcq" and q["options"]:
            correct_answer_text = q["answer"]
            random.shuffle(q["options"])
            try:
                correct_index = q["options"].index(correct_answer_text)
                q["answer"] = chr(65 + correct_index)
            except ValueError:
                for i, opt in enumerate(q["options"]):
                    if correct_answer_text.lower() in opt.lower():
                        q["answer"] = chr(65 + i)
                        break
                else:
                    q["answer"] = "A"
    return questions_data


# -------------------------
# Format text with emphasis
# -------------------------
def format_text_with_emphasis(text: str) -> str:
    emphasis_keywords = [
        "NOT",
        "EXCEPT",
        "ALWAYS",
        "NEVER",
        "ONLY",
        "ALL",
        "NONE",
        "MUST",
        "CANNOT",
        "BEST",
        "MOST",
        "LEAST",
    ]
    formatted_text = text
    for keyword in emphasis_keywords:
        pattern = r"\b(" + re.escape(keyword) + r")\b"
        replacement = r'<b><u><font color="#D32F2F">\1</font></u></b>'
        formatted_text = re.sub(
            pattern, replacement, formatted_text, flags=re.IGNORECASE
        )
    return formatted_text


# -------------------------
# Generate Questions (AI)
# -------------------------
def generate_questions(
    content: str,
    num_questions: int,
    question_type: Literal["mcq", "true_false", "essay", "mixed"] = "mixed",
    difficulty: Literal["easy", "medium", "hard", "mixed"] = "mixed",
) -> Dict:
    if not DEEPSEEK_API_KEY:
        raise ValueError("❌ AI_API_KEY not found")

    url = "https://api.deepseek.com/v1/chat/completions"

    system_prompt = """You are a professional academic examiner. Output ONLY valid JSON.

JSON STRUCTURE:
{
  "title": "Exam Title",
  "questions": [
    {
      "question": "Question text here?",
      "answer": "Answer text here",
      "type": "mcq", // or "true_false", "essay"
      "difficulty": "medium",
      "options": ["Option A", "Option B", "Option C", "Option D"] // Empty [] for essay
    }
  ]
}

CRITICAL RULES:
1. **SOURCE MATERIAL**: All questions must be strictly derived from the provided content.
2. **FORMATTING**: Use keywords like NOT, EXCEPT, MOST, BEST where appropriate.
3. **MCQ**: 4 distinct options. "answer" must match one option EXACTLY.
4. **TRUE/FALSE**: Options must be ["True", "False"].

**RULES FOR ESSAY QUESTIONS (STRICT):**
- **CONCISE ANSWERS**: The 'answer' field for essays must be short and direct (Maximum 2-3 sentences).
- **NO FLUFF**: Get straight to the point.
- **Example**: "Mitochondria produce ATP through cellular respiration. They are known as the powerhouse of the cell."
"""

    user_prompt = f"""Create an exam based on this content:
---
{content}
---

Requirements:
- Count: EXACTLY {num_questions} questions.
- Type: {question_type}
- Difficulty: {difficulty}
- **Essay Answers**: Keep them very short (2-3 sentences max).
- Return ONLY the JSON.
"""

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.5,
        "max_tokens": 8000,
    }

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    # Retry logic for API calls
    max_retries = 2
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            raw_output = response.json()["choices"][0]["message"]["content"]
            result = extract_json_from_response(raw_output)

            if "title" not in result:
                result["title"] = "Assessment"

            return shuffle_mcq_answers(result)

        except Exception as e:
            last_error = e
            logger.warning(
                f"API attempt {attempt + 1}/{max_retries + 1} failed: {str(e)}"
            )
            if attempt < max_retries:
                import time

                time.sleep(1)  # Brief delay before retry
                continue
            break

    raise Exception(f"❌ API Error after {max_retries + 1} attempts: {str(last_error)}")


# -------------------------
# Modern PDF Styling
# -------------------------
def create_custom_styles():
    """Create modern, professional PDF styles"""
    styles = getSampleStyleSheet()

    # Modern Color Palette
    PRIMARY_COLOR = colors.HexColor("#2563EB")  # Modern Blue
    SECONDARY_COLOR = colors.HexColor("#7C3AED")  # Purple
    ACCENT_COLOR = colors.HexColor("#10B981")  # Green
    TEXT_PRIMARY = colors.HexColor("#1F2937")  # Dark Gray
    TEXT_SECONDARY = colors.HexColor("#6B7280")  # Medium Gray
    DANGER_COLOR = colors.HexColor("#EF4444")  # Red

    # Title Style - Modern and Bold
    styles.add(
        ParagraphStyle(
            name="ExamTitle",
            parent=styles["Title"],
            fontSize=32,
            textColor=PRIMARY_COLOR,
            spaceAfter=8,
            fontName="Helvetica-Bold",
            leading=38,
            alignment=TA_CENTER,
        )
    )

    # Subtitle Style
    styles.add(
        ParagraphStyle(
            name="Subtitle",
            parent=styles["Normal"],
            fontSize=14,
            textColor=TEXT_SECONDARY,
            spaceAfter=20,
            fontName="Helvetica",
            alignment=TA_CENTER,
            leading=18,
        )
    )

    # Question Style - Enhanced
    styles.add(
        ParagraphStyle(
            name="Question",
            parent=styles["Normal"],
            fontSize=12,
            textColor=TEXT_PRIMARY,
            spaceAfter=12,
            fontName="Helvetica",
            leading=16,
            leftIndent=0,
        )
    )

    # Option Style - Modern
    styles.add(
        ParagraphStyle(
            name="Option",
            parent=styles["Normal"],
            fontSize=11,
            textColor=TEXT_PRIMARY,
            spaceAfter=8,
            leftIndent=25,
            leading=15,
            fontName="Helvetica",
        )
    )

    # Essay Prompt Style
    styles.add(
        ParagraphStyle(
            name="EssayPrompt",
            parent=styles["Italic"],
            fontSize=10,
            textColor=TEXT_SECONDARY,
            spaceAfter=8,
            leftIndent=25,
            fontName="Helvetica-Oblique",
        )
    )

    # White Header for Tables
    styles.add(
        ParagraphStyle(
            name="WhiteHeader",
            parent=styles["Normal"],
            fontSize=13,
            textColor=colors.white,
            fontName="Helvetica-Bold",
            alignment=TA_LEFT,
        )
    )

    # Section Header
    styles.add(
        ParagraphStyle(
            name="SectionHeader",
            parent=styles["Heading1"],
            fontSize=20,
            textColor=PRIMARY_COLOR,
            fontName="Helvetica-Bold",
            spaceAfter=15,
            spaceBefore=10,
            leading=24,
        )
    )

    # Badge Style for Question Numbers
    styles.add(
        ParagraphStyle(
            name="QuestionBadge",
            parent=styles["Normal"],
            fontSize=11,
            textColor=colors.white,
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
        )
    )

    return styles


# Modern page decoration with gradient-like effect
def draw_modern_page_decoration(canvas, doc):
    """Draw modern, professional page decorations"""
    canvas.saveState()
    
    width, height = A4
    
    # Top accent bar with gradient effect
    canvas.setFillColor(colors.HexColor("#2563EB"))
    canvas.rect(0, height - 8, width, 8, fill=1, stroke=0)
    
    canvas.setFillColor(colors.HexColor("#3B82F6"))
    canvas.rect(0, height - 16, width, 8, fill=1, stroke=0)
    
    # Bottom accent bar
    canvas.setFillColor(colors.HexColor("#2563EB"))
    canvas.rect(0, 0, width, 8, fill=1, stroke=0)
    
    canvas.setFillColor(colors.HexColor("#3B82F6"))
    canvas.rect(0, 8, width, 8, fill=1, stroke=0)
    
    # Side decorative elements
    canvas.setFillColor(colors.HexColor("#EFF6FF"))
    canvas.rect(0, 16, 4, height - 32, fill=1, stroke=0)
    canvas.rect(width - 4, 16, 4, height - 32, fill=1, stroke=0)
    
    # Page number in modern style
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(colors.HexColor("#6B7280"))
    
    # Center page number
    page_text = f"Page {doc.page}"
    canvas.drawCentredString(width / 2, 22, page_text)
    
    # Add timestamp on first page
    if doc.page == 1:
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#9CA3AF"))
        timestamp = datetime.now().strftime("%B %d, %Y")
        canvas.drawRightString(width - 50, 22, timestamp)
    
    canvas.restoreState()


# -------------------------
# Save to Modern PDF
# -------------------------
def save_questions_to_pdf(
    questions_data: Dict, output_file: str = "exam.pdf", include_answers: bool = True
):
    """Generate a modern, professional PDF with enhanced styling"""
    custom_styles = create_custom_styles()
    story = []

    # --- Modern Header Section ---
    story.append(Spacer(1, 0.3 * inch))
    
    # Title with modern styling
    title_text = questions_data.get('title', 'Professional Assessment')
    story.append(
        Paragraph(f"<b>{title_text}</b>", custom_styles["ExamTitle"])
    )
    
    # Subtitle with metadata
    total_questions = len(questions_data['questions'])
    mcq_count = sum(1 for q in questions_data['questions'] if q['type'] == 'mcq')
    tf_count = sum(1 for q in questions_data['questions'] if q['type'] == 'true_false')
    essay_count = sum(1 for q in questions_data['questions'] if q['type'] == 'essay')
    
    meta_parts = []
    if mcq_count > 0:
        meta_parts.append(f"{mcq_count} Multiple Choice")
    if tf_count > 0:
        meta_parts.append(f"{tf_count} True/False")
    if essay_count > 0:
        meta_parts.append(f"{essay_count} Essay")
    
    subtitle = f"Total Questions: {total_questions} • " + " • ".join(meta_parts)
    story.append(
        Paragraph(subtitle, custom_styles["Subtitle"])
    )

    # Modern divider
    story.append(
        HRFlowable(
            width="100%",
            thickness=2,
            color=colors.HexColor("#2563EB"),
            spaceBefore=5,
            spaceAfter=25,
        )
    )

    answer_data = []
    essay_indices = []

    # --- Questions Loop with Modern Design ---
    for idx, q in enumerate(questions_data["questions"], 1):
        q_content = []

        # Modern Question Number Badge + Question Text
        difficulty_colors = {
            "easy": "#10B981",
            "medium": "#F59E0B", 
            "hard": "#EF4444"
        }
        diff_color = difficulty_colors.get(q.get("difficulty", "medium"), "#6B7280")
        
        # Question header with badge
        q_header_data = [
            [
                Paragraph(f"<b>{idx}</b>", custom_styles["QuestionBadge"]),
                Paragraph(format_text_with_emphasis(q['question']), custom_styles["Question"])
            ]
        ]
        
        q_header_table = Table(q_header_data, colWidths=[35, 485])
        q_header_table.setStyle(TableStyle([
            # Badge styling
            ('BACKGROUND', (0, 0), (0, 0), colors.HexColor("#2563EB")),
            ('ROUNDEDCORNERS', [8, 8, 8, 8]),
            ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ('LEFTPADDING', (0, 0), (0, 0), 8),
            ('RIGHTPADDING', (0, 0), (0, 0), 8),
            ('TOPPADDING', (0, 0), (0, 0), 6),
            ('BOTTOMPADDING', (0, 0), (0, 0), 6),
            # Question text styling
            ('VALIGN', (1, 0), (1, 0), 'MIDDLE'),
            ('LEFTPADDING', (1, 0), (1, 0), 12),
        ]))
        
        q_content.append(q_header_table)
        q_content.append(Spacer(1, 8))

        # Options with modern styling
        if q["type"] == "mcq":
            for i, opt in enumerate(q["options"]):
                letter = chr(65 + i)
                # Create option with circular bullet
                opt_text = f'<font color="#2563EB"><b>●</b></font> <b>{letter}.</b> {format_text_with_emphasis(opt)}'
                q_content.append(Paragraph(opt_text, custom_styles["Option"]))

            answer_data.append([f"Q{idx}", q["answer"], "MCQ"])

        elif q["type"] == "true_false":
            opt_text_true = f'<font color="#2563EB"><b>●</b></font> <b>A.</b> True'
            opt_text_false = f'<font color="#2563EB"><b>●</b></font> <b>B.</b> False'
            q_content.append(Paragraph(opt_text_true, custom_styles["Option"]))
            q_content.append(Paragraph(opt_text_false, custom_styles["Option"]))
            ans = "A" if q["answer"] == "True" else "B"
            answer_data.append([f"Q{idx}", ans, "T/F"])

        elif q["type"] == "essay":
            essay_indices.append((idx, q))
            q_content.append(
                Paragraph(
                    '<font color="#6B7280"><i>✍ Write your answer below:</i></font>',
                    custom_styles["EssayPrompt"]
                )
            )
            q_content.append(Spacer(1, 8))

            # Modern answer lines with better spacing
            for line_num in range(4):
                q_content.append(
                    HRFlowable(
                        width="95%",
                        thickness=0.8,
                        color=colors.HexColor("#E5E7EB"),
                        spaceAfter=20,
                    )
                )

            answer_data.append([f"Q{idx}", "See Answer Key", "Essay"])

        # Add spacing between questions
        q_content.append(Spacer(1, 20))
        
        # Light separator between questions
        q_content.append(
            HRFlowable(
                width="100%",
                thickness=0.5,
                color=colors.HexColor("#F3F4F6"),
                spaceAfter=20,
            )
        )
        
        story.append(KeepTogether(q_content))

    # --- Modern Answer Key Page ---
    if include_answers:
        story.append(PageBreak())
        
        # Answer key header
        story.append(Spacer(1, 0.2 * inch))
        story.append(
            Paragraph("<b>Answer Key & Solutions</b>", custom_styles["ExamTitle"])
        )
        story.append(Spacer(1, 5))
        story.append(
            Paragraph(
                "Comprehensive answers and explanations for all questions",
                custom_styles["Subtitle"]
            )
        )
        story.append(Spacer(1, 15))

        # Modern Quick Reference Table
        short_answers = [row for row in answer_data if row[2] != "Essay"]
        if short_answers:
            story.append(
                Paragraph("<b>Quick Reference</b>", custom_styles["SectionHeader"])
            )
            
            # Modern table styling
            table_style = TableStyle([
                # Header styling
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2563EB")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('TOPPADDING', (0, 0), (-1, 0), 12),
                # Body styling
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 11),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
                ('TOPPADDING', (0, 1), (-1, -1), 10),
                # Rounded corners effect
                ('LINEABOVE', (0, 0), (-1, 0), 2, colors.HexColor("#2563EB")),
            ])
            
            header = [
                Paragraph("<b>Question</b>", custom_styles["WhiteHeader"]),
                Paragraph("<b>Correct Answer</b>", custom_styles["WhiteHeader"]),
                Paragraph("<b>Type</b>", custom_styles["WhiteHeader"])
            ]
            
            table_data = [header] + short_answers
            t = Table(table_data, colWidths=[100, 280, 100])
            t.setStyle(table_style)
            story.append(t)
            story.append(Spacer(1, 30))

        # Modern Essay Answer Cards
        if essay_indices:
            story.append(
                Paragraph("<b>Essay Model Answers</b>", custom_styles["SectionHeader"])
            )
            story.append(Spacer(1, 10))

            for q_num, q_data in essay_indices:
                # Modern card design
                header_p = Paragraph(
                    f"<b>QUESTION {q_num}</b>",
                    custom_styles["WhiteHeader"]
                )

                question_p = Paragraph(
                    f'<b><font color="#2563EB">Question:</font></b><br/>{q_data["question"]}',
                    custom_styles["Normal"],
                )

                divider = HRFlowable(
                    width="100%",
                    thickness=1.5,
                    color=colors.HexColor("#10B981"),
                    spaceBefore=10,
                    spaceAfter=10,
                )

                answer_p = Paragraph(
                    f'<b><font color="#10B981">✓ Model Answer:</font></b><br/>{q_data["answer"]}',
                    custom_styles["Normal"],
                )

                body_content = [question_p, divider, answer_p]
                card_data = [[header_p], [body_content]]
                
                card_table = Table(card_data, colWidths=[480])
                
                # Modern card styling with shadow effect
                card_style = TableStyle([
                    # Header
                    ('BACKGROUND', (0, 0), (0, 0), colors.HexColor("#2563EB")),
                    ('ROUNDEDCORNERS', [10, 10, 0, 0]),
                    ('BOTTOMPADDING', (0, 0), (0, 0), 10),
                    ('TOPPADDING', (0, 0), (0, 0), 10),
                    ('LEFTPADDING', (0, 0), (0, 0), 15),
                    # Body
                    ('BACKGROUND', (0, 1), (0, 1), colors.HexColor("#F0FDF4")),
                    ('BOTTOMPADDING', (0, 1), (0, 1), 15),
                    ('TOPPADDING', (0, 1), (0, 1), 15),
                    ('LEFTPADDING', (0, 1), (0, 1), 15),
                    ('RIGHTPADDING', (0, 1), (0, 1), 15),
                    # Border
                    ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor("#10B981")),
                    ('LINEABOVE', (0, 1), (0, 1), 1.5, colors.HexColor("#10B981")),
                ])

                card_table.setStyle(card_style)
                story.append(card_table)
                story.append(Spacer(1, 18))

    # Build PDF with modern styling
    doc = SimpleDocTemplate(
        output_file,
        pagesize=A4,
        rightMargin=45,
        leftMargin=45,
        topMargin=50,
        bottomMargin=45,
    )

    doc.build(
        story,
        onFirstPage=draw_modern_page_decoration,
        onLaterPages=draw_modern_page_decoration
    )
    
    return output_file


# -------------------------
# Main Execution
# -------------------------
if __name__ == "__main__":
    sample_content = """
    Photosynthesis is the process used by plants, algae and certain bacteria to harness energy from sunlight 
    and turn it into chemical energy. There are two main stages: light-dependent reactions and the Calvin cycle.
    Light-dependent reactions take place in the thylakoid membrane and require sunlight to produce ATP and NADPH. 
    The Calvin cycle takes place in the stroma and uses ATP and NADPH to convert carbon dioxide into glucose.
    Chlorophyll is the green pigment responsible for capturing light energy.
    """

    try:
        print("🧠 Generating Modern Exam...")
        # Generating a mixed exam to showcase modern design
        exam_data = generate_questions(
            sample_content, num_questions=6, question_type="mixed"
        )

        print("🎨 Creating Modern Professional PDF...")
        pdf_name = save_questions_to_pdf(exam_data, "Modern_Biology_Exam.pdf")

        print(f"✅ Success! Modern PDF saved to {pdf_name}")

    except Exception as e:
        print(f"❌ Error: {e}")
