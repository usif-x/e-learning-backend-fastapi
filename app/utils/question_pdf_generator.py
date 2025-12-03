import json
import logging
import os
import random
import re
from typing import Dict, List, Literal

import pytesseract
import requests
from dotenv import load_dotenv
from pdf2image import convert_from_path
from PyPDF2 import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, mm
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
        replacement = r'<b><u><font color="#c62828">\1</font></u></b>'
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

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        raw_output = response.json()["choices"][0]["message"]["content"]
        result = extract_json_from_response(raw_output)

        if "title" not in result:
            result["title"] = "Assessment"

        return shuffle_mcq_answers(result)

    except Exception as e:
        raise Exception(f"❌ API Error: {str(e)}")


# -------------------------
# PDF Styling
# -------------------------
def create_custom_styles():
    styles = getSampleStyleSheet()

    PRIMARY_COLOR = colors.HexColor("#1565C0")  # Blue
    TEXT_COLOR = colors.HexColor("#263238")  # Dark Grey

    styles.add(
        ParagraphStyle(
            name="ExamTitle",
            parent=styles["Title"],
            fontSize=26,
            textColor=PRIMARY_COLOR,
            spaceAfter=20,
            fontName="Helvetica-Bold",
            leading=32,
        )
    )

    styles.add(
        ParagraphStyle(
            name="Question",
            parent=styles["Normal"],
            fontSize=12,
            textColor=TEXT_COLOR,
            spaceAfter=10,
            fontName="Helvetica-Bold",
            leading=15,
        )
    )

    styles.add(
        ParagraphStyle(
            name="Option",
            parent=styles["Normal"],
            fontSize=11,
            textColor=colors.HexColor("#455A64"),
            spaceAfter=5,
            leftIndent=20,
            leading=14,
        )
    )

    styles.add(
        ParagraphStyle(
            name="EssayPrompt",
            parent=styles["Italic"],
            fontSize=10,
            textColor=colors.HexColor("#78909c"),
            spaceAfter=5,
            leftIndent=20,
        )
    )

    # Style for white text in headers
    styles.add(
        ParagraphStyle(
            name="WhiteHeader",
            parent=styles["Normal"],
            fontSize=12,
            textColor=colors.white,
            fontName="Helvetica-Bold",
            alignment=TA_LEFT,
        )
    )

    return styles


# Function to draw a thick rounded border on every page
def draw_page_border(canvas, doc):
    canvas.saveState()
    stroke_color = colors.HexColor("#1565C0")
    line_width = 3.5
    corner_radius = 15
    margin = 20
    width, height = A4
    canvas.setStrokeColor(stroke_color)
    canvas.setLineWidth(line_width)
    canvas.setFillColor(colors.white)
    canvas.roundRect(
        margin,
        margin,
        width - (2 * margin),
        height - (2 * margin),
        corner_radius,
        stroke=1,
        fill=0,
    )
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.gray)
    canvas.drawCentredString(width / 2, margin + 8, f"Page {doc.page}")
    canvas.restoreState()


# -------------------------
# Save to PDF
# -------------------------
def save_questions_to_pdf(
    questions_data: Dict, output_file: str = "exam.pdf", include_answers: bool = True
):
    custom_styles = create_custom_styles()
    story = []

    # --- Header Section ---
    story.append(Spacer(1, 0.2 * inch))
    story.append(
        Paragraph(
            f"<b>{questions_data.get('title', 'Exam')}</b>", custom_styles["ExamTitle"]
        )
    )

    meta_text = f"<b>Total Questions:</b> {len(questions_data['questions'])}"
    story.append(
        Paragraph(
            meta_text,
            ParagraphStyle(
                "Meta",
                parent=custom_styles["Normal"],
                alignment=TA_CENTER,
                textColor=colors.gray,
            ),
        )
    )

    story.append(
        HRFlowable(
            width="90%",
            thickness=2,
            color=colors.HexColor("#1565C0"),
            spaceBefore=10,
            spaceAfter=20,
        )
    )

    answer_data = []

    # --- Questions Loop ---
    # Store indices of essay questions for later
    essay_indices = []

    for idx, q in enumerate(questions_data["questions"], 1):
        q_content = []

        # Question Text
        q_text = f"<font color='#1565C0'>Q{idx}.</font> {format_text_with_emphasis(q['question'])}"
        q_content.append(Paragraph(q_text, custom_styles["Question"]))

        # Options
        if q["type"] == "mcq":
            for i, opt in enumerate(q["options"]):
                letter = chr(65 + i)
                opt_text = f"<b>{letter}.</b> {format_text_with_emphasis(opt)}"
                q_content.append(Paragraph(opt_text, custom_styles["Option"]))

            answer_data.append([f"Q{idx}", q["answer"], "MCQ"])

        elif q["type"] == "true_false":
            q_content.append(Paragraph("<b>A.</b> True", custom_styles["Option"]))
            q_content.append(Paragraph("<b>B.</b> False", custom_styles["Option"]))
            ans = "A" if q["answer"] == "True" else "B"
            answer_data.append([f"Q{idx}", ans, "T/F"])

        elif q["type"] == "essay":
            essay_indices.append((idx, q))  # Save index and question for later
            q_content.append(
                Paragraph("<i>Answer briefly below:</i>", custom_styles["EssayPrompt"])
            )
            q_content.append(Spacer(1, 5))

            # 3 lines for essay
            for _ in range(3):
                q_content.append(
                    HRFlowable(
                        width="95%",
                        thickness=0.5,
                        color=colors.lightgrey,
                        spaceAfter=18,
                        dash=[2, 2],
                    )
                )

            answer_data.append([f"Q{idx}", "See Key", "Essay"])

        q_content.append(Spacer(1, 15))
        story.append(KeepTogether(q_content))

    # --- Answer Key Page ---
    if include_answers:
        story.append(PageBreak())
        story.append(
            Paragraph("<b>Answer Key & Explanations</b>", custom_styles["ExamTitle"])
        )
        story.append(Spacer(1, 10))

        # 1. Quick Answer Table (Exclude Essays)
        short_answers = [row for row in answer_data if row[2] != "Essay"]
        if short_answers:
            table_style = TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1565C0")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#E3F2FD")],
                    ),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                ]
            )
            header = ["Q#", "Answer", "Type"]
            t = Table([header] + short_answers, colWidths=[50, 300, 80])
            t.setStyle(table_style)
            story.append(t)
            story.append(Spacer(1, 25))

        # 2. Detailed Essay Answers (Designed as Cards)
        if essay_indices:
            story.append(
                Paragraph("<b>Model Answers for Essays</b>", custom_styles["Question"])
            )
            story.append(Spacer(1, 5))

            for q_num, q_data in essay_indices:
                # --- The Card Structure ---

                # Header Row Content: "QUESTION 5"
                header_p = Paragraph(f"QUESTION {q_num}", custom_styles["WhiteHeader"])

                # Body Row Content: Question Text + Divider + Answer
                q_text_p = Paragraph(
                    f"<b>Question:</b><br/>{q_data['question']}",
                    custom_styles["Normal"],
                )

                divider = HRFlowable(
                    width="100%",
                    thickness=1,
                    color=colors.HexColor("#A5D6A7"),
                    spaceBefore=8,
                    spaceAfter=8,
                )

                ans_text_p = Paragraph(
                    f"<b><font color='#2E7D32'>Model Answer:</font></b><br/>{q_data['answer']}",
                    custom_styles["Normal"],
                )

                # We pack the body content into a list for the Table cell
                body_content = [q_text_p, divider, ans_text_p]

                # Table Data: [[Header], [Body]]
                card_data = [[header_p], [body_content]]

                # Create Table
                t = Table(card_data, colWidths=[460])  # Width fits A4 margins

                # Style the Card
                card_style = TableStyle(
                    [
                        # Header Style (Dark Green Bar)
                        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#2E7D32")),
                        ("BOTTOMPADDING", (0, 0), (0, 0), 8),
                        ("TOPPADDING", (0, 0), (0, 0), 8),
                        ("LEFTPADDING", (0, 0), (0, 0), 12),
                        # Body Style (Light Green Box)
                        ("BACKGROUND", (0, 1), (0, 1), colors.HexColor("#F1F8E9")),
                        ("BOTTOMPADDING", (0, 1), (0, 1), 12),
                        ("TOPPADDING", (0, 1), (0, 1), 12),
                        ("LEFTPADDING", (0, 1), (0, 1), 12),
                        ("RIGHTPADDING", (0, 1), (0, 1), 12),
                        # Outer Border (Matches Header)
                        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#2E7D32")),
                        (
                            "LINEABOVE",
                            (0, 1),
                            (0, 1),
                            1,
                            colors.HexColor("#2E7D32"),
                        ),  # Line between header and body
                    ]
                )

                t.setStyle(card_style)
                story.append(t)
                story.append(Spacer(1, 15))  # Space between cards

    # Build PDF
    doc = SimpleDocTemplate(
        output_file,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    doc.build(story, onFirstPage=draw_page_border, onLaterPages=draw_page_border)
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
        print("🧠 Generating Exam...")
        # Generating a mixed exam to test both MCQ and Essay formatting
        exam_data = generate_questions(
            sample_content, num_questions=5, question_type="mixed"
        )

        print("🎨 Creating PDF with improved Essay Cards...")
        pdf_name = save_questions_to_pdf(exam_data, "Biology_Exam.pdf")

        print(f"✅ Success! Saved to {pdf_name}")

    except Exception as e:
        print(f"❌ Error: {e}")
