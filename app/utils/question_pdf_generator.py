import json
import os
import re
from typing import Dict, List, Literal

import requests
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("AI_API_KEY")
DEEPSEEK_MODEL = "deepseek-chat"


# -------------------------
# Extract text from PDF using PyPDF2
# -------------------------
def extract_pdf_text(pdf_path: str) -> str:
    """Extract text content from a PDF file."""
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.strip()
    except Exception as e:
        raise Exception(f"❌ Error reading PDF: {str(e)}")


# -------------------------
# Extract JSON safely from AI output
# -------------------------
def extract_json_from_response(raw_output: str) -> Dict:
    """
    Extract JSON from AI response that may contain markdown code blocks.
    Handles formats like:
    - ```json {...} ```
    - ``` {...} ```
    - Plain JSON {...}
    """
    # First, try to find JSON within markdown code blocks
    code_block_pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
    code_block_match = re.search(code_block_pattern, raw_output, flags=re.DOTALL)

    if code_block_match:
        json_str = code_block_match.group(1)
    else:
        # If no code block, try to find raw JSON
        json_match = re.search(r"\{.*\}", raw_output, flags=re.DOTALL)
        if not json_match:
            print("=" * 60)
            print("RAW OUTPUT:")
            print(raw_output)
            print("=" * 60)
            raise ValueError("❌ No JSON object found in AI output")
        json_str = json_match.group(0)

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print("=" * 60)
        print("FAILED TO PARSE JSON:")
        print(json_str)
        print("=" * 60)
        raise ValueError(f"❌ Invalid JSON format: {str(e)}")


# -------------------------
# Generate questions using DeepSeek API
# -------------------------
def generate_questions(
    content: str,
    num_questions: int,
    question_type: Literal["mcq", "true_false", "essay", "mixed"] = "mixed",
    difficulty: Literal["easy", "medium", "hard", "mixed"] = "mixed",
) -> Dict:
    """
    Generate exam questions using DeepSeek API.

    Args:
        content: Text content to generate questions from
        num_questions: Number of questions to generate
        question_type: Type of questions (mcq, true_false, essay, or mixed)
        difficulty: Difficulty level (easy, medium, hard, or mixed)

    Returns:
        Dictionary containing generated questions
    """
    if not DEEPSEEK_API_KEY:
        raise ValueError("❌ AI_API_KEY not found in environment variables")

    if not content.strip():
        raise ValueError("❌ Content cannot be empty")

    url = "https://api.deepseek.com/v1/chat/completions"

    system_prompt = """You are a professional exam question generator.
Generate questions STRICTLY from the provided content.

YOU MUST OUTPUT ONLY VALID JSON - NO OTHER TEXT BEFORE OR AFTER.

Format:
{
  "questions": [
    {
      "question": "Question text here",
      "answer": "Correct answer here",
      "type": "mcq",
      "difficulty": "medium",
      "options": ["Option 1", "Option 2", "Option 3", "Option 4"]
    }
  ]
}

CRITICAL RULES:
- You MUST generate EXACTLY the number of questions requested - no more, no less
- MCQ: Provide 4-5 realistic options, include the correct answer among them
- true_false: options must be exactly ["True", "False"]
- essay: options should be empty array []
- If type=mixed: randomly mix mcq, true_false, and essay questions
- If difficulty=mixed: vary difficulty across easy, medium, and hard
- Base ALL questions on the provided content only
- Make questions clear, unambiguous, and pedagogically sound
- You can ask questions from different angles, difficulty levels, and detail levels to reach the required count
- Include questions about definitions, applications, comparisons, examples, and implications"""

    user_prompt = f"""Generate EXACTLY {num_questions} questions from this content. This is mandatory.

Content:
{content}

Requirements:
- Number of questions: {num_questions} (MUST BE EXACT)
- Question type: {question_type}
- Difficulty: {difficulty}
- Output ONLY the JSON object, nothing else

Remember: You MUST generate exactly {num_questions} questions. Use different question styles and angles to meet this requirement."""

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 8000,  # Increased for more questions
    }

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        response_json = response.json()

        if "choices" not in response_json or not response_json["choices"]:
            raise ValueError("❌ Invalid API response format")

        raw_output = response_json["choices"][0]["message"]["content"]
        result = extract_json_from_response(raw_output)

        # Verify the number of questions generated
        generated_count = len(result.get("questions", []))
        if generated_count != num_questions:
            print(
                f"⚠️  Warning: Requested {num_questions} questions but got {generated_count}"
            )
            print(
                f"💡 Tip: The content might be too short for {num_questions} questions."
            )

            # If significantly fewer, you might want to raise an error or retry
            if generated_count < num_questions * 0.5:  # Less than 50% of requested
                print(f"❌ Generated only {generated_count}/{num_questions} questions")
                print("💡 Try:")
                print("   - Providing more content")
                print("   - Reducing the number of questions")
                print("   - Using 'mixed' question types for more variety")

        return result

    except requests.exceptions.RequestException as e:
        raise Exception(f"❌ API request failed: {str(e)}")


# -------------------------
# Validate questions data
# -------------------------
def validate_questions(questions_data: Dict) -> bool:
    """Validate the structure of generated questions."""
    if "questions" not in questions_data:
        raise ValueError("❌ Missing 'questions' key in data")

    for idx, q in enumerate(questions_data["questions"], 1):
        required_keys = ["question", "answer", "type", "difficulty", "options"]
        for key in required_keys:
            if key not in q:
                raise ValueError(f"❌ Question {idx} missing '{key}' field")

        # Validate question types
        if q["type"] not in ["mcq", "true_false", "essay"]:
            raise ValueError(f"❌ Question {idx} has invalid type: {q['type']}")

        # Validate options based on type
        if q["type"] == "true_false" and q["options"] != ["True", "False"]:
            q["options"] = ["True", "False"]  # Auto-fix

        if q["type"] == "mcq" and len(q["options"]) < 2:
            raise ValueError(f"❌ Question {idx} (MCQ) needs at least 2 options")

    return True


# -------------------------
# Save Questions as PDF
# -------------------------
def save_questions_to_pdf(
    questions_data: Dict,
    title: str = "Exam",
    output_file: str = "exam.pdf",
    include_answers: bool = True,
) -> str:
    """
    Generate a PDF file with questions and optional answer key.

    Args:
        questions_data: Dictionary containing questions
        title: Title for the exam
        output_file: Output PDF filename
        include_answers: Whether to include answer key

    Returns:
        Path to generated PDF file
    """
    from reportlab.lib import colors
    from reportlab.lib.units import inch

    # Validate questions first
    validate_questions(questions_data)

    styles = getSampleStyleSheet()
    story = []

    # Title with styling
    story.append(Spacer(1, 0.3 * inch))
    story.append(
        Paragraph(
            f"<b><font size=20 color='#2c3e50'>{title}</font></b>", styles["Title"]
        )
    )
    story.append(Spacer(1, 0.1 * inch))

    # Horizontal line
    from reportlab.platypus import HRFlowable

    story.append(
        HRFlowable(
            width="100%",
            thickness=2,
            color=colors.HexColor("#3498db"),
            spaceBefore=6,
            spaceAfter=12,
        )
    )

    story.append(
        Paragraph(
            f"<font size=11 color='#7f8c8d'><b>Total Questions:</b> {len(questions_data['questions'])}</font>",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 0.4 * inch))

    answer_data = []

    # Generate questions
    for idx, q in enumerate(questions_data["questions"], start=1):
        # Question text - clean format
        question_text = (
            f"<b><font size=11 color='#2c3e50'>{idx}. {q['question']}</font></b>"
        )
        story.append(Paragraph(question_text, styles["Normal"]))
        story.append(Spacer(1, 8))

        # Options based on type
        if q["type"] == "mcq":
            for i, opt in enumerate(q["options"]):
                letter = chr(65 + i)  # A, B, C, D...
                option_text = f"<font size=10><b>{letter}.</b> {opt}</font>"
                story.append(Paragraph(option_text, styles["Normal"]))
                story.append(Spacer(1, 4))

            answer_data.append([str(idx), q["answer"]])

        elif q["type"] == "true_false":
            story.append(
                Paragraph("<font size=10><b>A.</b> True</font>", styles["Normal"])
            )
            story.append(Spacer(1, 4))
            story.append(
                Paragraph("<font size=10><b>B.</b> False</font>", styles["Normal"])
            )
            story.append(Spacer(1, 4))
            answer_data.append([str(idx), q["answer"]])

        else:  # essay
            story.append(Spacer(1, 6))
            story.append(
                Paragraph(
                    "<font size=9 color='#95a5a6'><i>Write your answer below:</i></font>",
                    styles["Italic"],
                )
            )
            story.append(Spacer(1, 0.5 * inch))
            # Add lines for writing
            story.append(Paragraph("_" * 100, styles["Normal"]))
            story.append(Spacer(1, 8))
            story.append(Paragraph("_" * 100, styles["Normal"]))
            story.append(Spacer(1, 8))
            story.append(Paragraph("_" * 100, styles["Normal"]))
            answer_data.append([str(idx), "See suggested answer"])

        story.append(Spacer(1, 0.3 * inch))

    # Answer key on separate page
    if include_answers:
        story.append(PageBreak())
        story.append(Spacer(1, 0.3 * inch))
        story.append(
            Paragraph(
                "<b><font size=20 color='#2c3e50'>Answer Key</font></b>",
                styles["Title"],
            )
        )
        story.append(
            HRFlowable(
                width="100%",
                thickness=2,
                color=colors.HexColor("#3498db"),
                spaceBefore=6,
                spaceAfter=20,
            )
        )

        # Answer table with better styling
        table_data = [["Question", "Answer"]] + answer_data
        table = Table(table_data, colWidths=[80, 420])
        table.setStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3498db")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 12),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("TOPPADDING", (0, 0), (-1, 0), 12),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bdc3c7")),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#ecf0f1")],
                ),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 1), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 10),
            ]
        )
        story.append(table)

        # Detailed essay answers
        essay_questions = [
            (idx + 1, q)
            for idx, q in enumerate(questions_data["questions"])
            if q["type"] == "essay"
        ]

        if essay_questions:
            story.append(Spacer(1, 0.4 * inch))
            story.append(
                Paragraph(
                    "<b><font size=14 color='#2c3e50'>Essay Question - Suggested Answers</font></b>",
                    styles["Heading2"],
                )
            )
            story.append(Spacer(1, 0.2 * inch))

            for q_num, q in essay_questions:
                story.append(
                    Paragraph(
                        f"<b><font size=11 color='#2c3e50'>Question {q_num}:</font></b> <font size=10>{q['question']}</font>",
                        styles["Normal"],
                    )
                )
                story.append(Spacer(1, 8))
                story.append(
                    Paragraph(
                        f"<font size=10 color='#34495e'><i>Suggested Answer:</i> {q['answer']}</font>",
                        styles["Normal"],
                    )
                )
                story.append(Spacer(1, 0.2 * inch))

    # Build PDF
    try:
        doc = SimpleDocTemplate(output_file, pagesize=A4)
        doc.build(story)
        return output_file
    except Exception as e:
        raise Exception(f"❌ Error creating PDF: {str(e)}")


# -------------------------
# Example usage
# -------------------------
if __name__ == "__main__":
    # Example 1: Generate from text content
    content = """
    The human nervous system consists of the central nervous system and peripheral nervous system.
    The central nervous system includes the brain and spinal cord, which process information and 
    coordinate bodily functions. The peripheral nervous system connects the CNS to limbs and organs.
    
    Neurons are specialized cells that transmit electrical signals, allowing communication throughout 
    the body. They consist of a cell body, dendrites that receive signals, and an axon that transmits 
    signals to other neurons or target cells.
    
    The nervous system can be divided functionally into the somatic nervous system (voluntary control)
    and the autonomic nervous system (involuntary control). The autonomic system further divides into
    sympathetic (fight-or-flight) and parasympathetic (rest-and-digest) divisions.
    """

    try:
        print("🔄 Generating questions...")
        result = generate_questions(
            content=content, num_questions=6, question_type="mixed", difficulty="mixed"
        )

        print(f"✅ Generated {len(result['questions'])} questions")

        print("\n🔄 Creating PDF...")
        file_path = save_questions_to_pdf(
            questions_data=result,
            title="Nervous System Exam",
            output_file="nervous_system_exam.pdf",
            include_answers=True,
        )

        print(f"✅ PDF saved successfully: {file_path}")

        # Display summary
        print("\n📊 Question Summary:")
        types = {}
        for q in result["questions"]:
            types[q["type"]] = types.get(q["type"], 0) + 1

        for qtype, count in types.items():
            print(f"  - {qtype.upper()}: {count}")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


# -------------------------
# Example 2: Generate from PDF file
# -------------------------
def generate_exam_from_pdf(
    pdf_path: str,
    num_questions: int = 10,
    question_type: str = "mixed",
    difficulty: str = "mixed",
    output_file: str = None,
) -> str:
    """
    Extract content from PDF and generate exam questions.

    Args:
        pdf_path: Path to PDF file
        num_questions: Number of questions to generate
        question_type: Type of questions
        difficulty: Difficulty level
        output_file: Output PDF filename (auto-generated if None)

    Returns:
        Path to generated exam PDF
    """
    print(f"📄 Reading PDF: {pdf_path}")
    content = extract_pdf_text(pdf_path)

    if len(content) < 100:
        raise ValueError("❌ PDF content too short to generate meaningful questions")

    print(f"✅ Extracted {len(content)} characters from PDF")

    print("🔄 Generating questions...")
    questions = generate_questions(content, num_questions, question_type, difficulty)

    if output_file is None:
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        output_file = f"{base_name}_exam.pdf"

    print("🔄 Creating exam PDF...")
    return save_questions_to_pdf(
        questions_data=questions,
        title=f"Exam: {os.path.splitext(os.path.basename(pdf_path))[0]}",
        output_file=output_file,
    )
