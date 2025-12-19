from typing import List, Optional

# ============================================
# ENHANCED SYSTEM MESSAGE
# ============================================

ENHANCED_SYSTEM_MESSAGE = """You are an elite educational assessment designer with expertise in cognitive psychology, Bloom's Taxonomy, and evidence-based learning principles.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 MANDATORY REQUIREMENTS - READ CAREFULLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. EXACT QUESTION DISTRIBUTION (NON-NEGOTIABLE):
   ✓ 70% Standard Questions - Direct knowledge assessment
   ✓ 20% Critical Thinking Questions - Higher-order reasoning
   ✓ 10% Linking Questions - Concept integration

2. DIFFICULTY CALIBRATION (STRICTLY ENFORCE):
   • EASY: Simple recall, basic definitions, obvious answers
   • MEDIUM: Requires understanding and application of concepts
   • HARD: Complex analysis, multi-step reasoning, synthesis

3. UNIQUENESS & DIVERSITY:
   • Every question MUST be completely different from previous ones
   • Vary question structure, phrasing, and angles
   • Use different aspects of the topic
   • NO repetition of question patterns or concepts

4. OUTPUT FORMAT:
   • Return ONLY valid JSON
   • NO markdown formatting (no ```json```)
   • NO additional text or explanations outside JSON
   • For explanation_ar fields: Keep medical terms in English and explain in Egyptian Arabic for better understanding

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 QUESTION TYPE DEFINITIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

╔═══════════════════════════════════════════╗
║ STANDARD QUESTIONS (70%)                  ║
╚═══════════════════════════════════════════╝
Purpose: Test fundamental knowledge and comprehension
Cognitive Levels: Remember, Understand, Basic Apply
Characteristics:
  • Direct factual recall
  • Definition-based questions
  • Basic concept identification
  • Straightforward application
Examples:
  ✓ "What is the definition of X?"
  ✓ "Which of the following describes Y?"
  ✓ "What are the main components of Z?"

╔═══════════════════════════════════════════╗
║ CRITICAL THINKING QUESTIONS (20%)         ║
╚═══════════════════════════════════════════╝
Purpose: Require higher-order thinking and deep reasoning
Cognitive Levels: Analyze, Evaluate, Create
Characteristics:
  • Compare and contrast concepts
  • Predict outcomes and consequences
  • Solve complex problems
  • Justify decisions with reasoning
  • Evaluate arguments or solutions
  • Apply concepts to novel scenarios
Examples:
  ✓ "Why would X occur if Y changes?"
  ✓ "What would be the consequences of Z?"
  ✓ "How would you solve this problem using concept A?"
  ✓ "Evaluate the effectiveness of approach B"

╔═══════════════════════════════════════════╗
║ LINKING QUESTIONS (10%)                   ║
╚═══════════════════════════════════════════╝
Purpose: Connect multiple concepts and show relationships
Cognitive Levels: Understand, Analyze, Synthesize
Characteristics:
  • Explicitly connect 2+ concepts
  • Show cause-and-effect relationships
  • Compare different topics/ideas
  • Demonstrate integrated understanding
Examples:
  ✓ "How does concept X relate to concept Y?"
  ✓ "What is the connection between A and B?"
  ✓ "Compare and contrast processes C and D"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ QUALITY ASSURANCE CHECKLIST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Before finalizing your response, verify:
□ Exact distribution matches requirements (70-20-10)
□ Difficulty level is appropriate and consistent
□ Questions are unique and don't repeat patterns
□ Critical thinking questions require actual reasoning
□ Linking questions connect multiple concepts explicitly
□ All explanations are clear and accurate
□ JSON format is valid (no markdown)
□ Options are balanced and plausible for MCQ
□ Correct answers are truly correct

REMEMBER: Quality over speed. Take time to ensure each question meets these standards."""


def get_difficulty_guide(difficulty: str) -> str:
    difficulty_guide = {
        "easy": """
EASY DIFFICULTY GUIDELINES:
• Questions should be straightforward and test basic recall
• Answers should be obvious to someone who studied the material
• Avoid complex reasoning or multi-step problems
• Use simple, clear language
• Focus on fundamental concepts and definitions""",
        "medium": """
MEDIUM DIFFICULTY GUIDELINES:
• Questions require understanding and application of concepts
• Answers require thinking but are achievable with study
• May involve some problem-solving or analysis
• Use clear but more technical language
• Test deeper comprehension beyond memorization""",
        "hard": """
HARD DIFFICULTY GUIDELINES:
• Questions demand complex analysis and synthesis
• Answers require deep understanding and reasoning
• Involve multi-step problem-solving or evaluation
• May include novel scenarios or edge cases
• Test mastery and ability to apply knowledge creatively""",
    }
    return difficulty_guide.get(difficulty.lower(), difficulty_guide["medium"])


def get_pdf_difficulty_guide(difficulty: str) -> str:
    difficulty_guide = {
        "easy": "EASY: Straightforward questions testing basic recall from the content",
        "medium": "MEDIUM: Questions requiring understanding and application of content concepts",
        "hard": "HARD: Complex questions demanding analysis, synthesis, and deep reasoning",
    }
    return difficulty_guide.get(difficulty.lower(), difficulty_guide["medium"])


def get_pdf_path_difficulty_guide(difficulty: str) -> str:
    difficulty_guide = {
        "easy": "EASY: Straightforward recall from text.",
        "medium": "MEDIUM: Understanding and application of text concepts.",
        "hard": "HARD: Analysis and synthesis of text information.",
    }
    return difficulty_guide.get(difficulty.lower(), difficulty_guide["medium"])


def get_previous_questions_context(previous_questions: Optional[List[str]]) -> str:
    if previous_questions and len(previous_questions) > 0:
        questions_list = "\n".join(
            [f"  {i+1}. {q}" for i, q in enumerate(previous_questions[:30])]
        )
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚫 PREVIOUSLY GENERATED QUESTIONS - DO NOT REPEAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{questions_list}

⚠️ CRITICAL: Generate COMPLETELY NEW questions that:
  • Cover different aspects of the topic
  • Use different wording and phrasing
  • Test different knowledge areas
  • Have different question structures
  • Are NOT variations of the above questions

Think: "What haven't I asked yet about this topic?"
"""
    return ""


def get_pdf_previous_questions_context(previous_questions: Optional[List[str]]) -> str:
    if previous_questions and len(previous_questions) > 0:
        questions_list = "\n".join(
            [f"  {i+1}. {q}" for i, q in enumerate(previous_questions[:30])]
        )
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚫 DO NOT REPEAT THESE QUESTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{questions_list}

Generate COMPLETELY DIFFERENT questions from different parts of the content.
"""
    return ""


def get_pdf_path_previous_questions_context(
    previous_questions: Optional[List[str]],
) -> str:
    if previous_questions and len(previous_questions) > 0:
        questions_list = "\n".join([f"- {q}" for q in previous_questions[:20]])
        return f"\n\nDO NOT REPEAT:\n{questions_list}\n"
    return ""


def get_notes_context(notes: Optional[str]) -> str:
    if notes:
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 ADDITIONAL INSTRUCTIONS FROM USER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{notes}

Incorporate these instructions while maintaining all other requirements.
"""
    return ""


def get_pdf_notes_context(notes: Optional[str]) -> str:
    if notes:
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 USER INSTRUCTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{notes}

Incorporate these instructions while maintaining all other requirements.
"""
    return ""


def get_pdf_path_notes_context(notes: Optional[str]) -> str:
    return f"\nUSER NOTES: {notes}\n" if notes else ""


def get_multiple_choice_prompt(
    count,
    topic,
    current_difficulty_guide,
    standard_count,
    critical_count,
    linking_count,
    notes_context,
    previous_context,
):
    return f"""Generate {count} UNIQUE multiple choice questions about: {topic}

{current_difficulty_guide}

EXACT DISTRIBUTION REQUIRED:
├─ Standard Questions: {standard_count} questions
├─ Critical Thinking Questions: {critical_count} questions
└─ Linking Questions: {linking_count} questions
   TOTAL: {count} questions

{notes_context}{previous_context}

MULTIPLE CHOICE REQUIREMENTS:
✓ Provide exactly 4 options per question (A, B, C, D)
✓ All options must be plausible and relevant
✓ Avoid "all of the above" or "none of the above"
✓ Distractors should represent common misconceptions
✓ Only ONE option is correct
✓ IMPORTANT: Randomize correct answer position - use ALL indices (0, 1, 2, 3) across questions, NOT just 0 or 1

OUTPUT FORMAT (JSON ONLY):
{{
    "questions": [
        {{
            "question_type": "text",
            "question": "First question text",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_answer": 2,
            "explanation_en": "Detailed explanation (English)",
            "explanation_ar": "شرح تفصيلي (Egyptian Arabic) - احتفظ بالمصطلحات الطبية بالإنجليزية واشرحها بالعربية المصرية للفهم الجيد",
            "question_category": "standard",
            "cognitive_level": "remember"
        }},
        {{
            "question_type": "text",
            "question": "Second question text",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_answer": 0,
            "explanation_en": "Detailed explanation (English)",
            "explanation_ar": "شرح تفصيلي (Egyptian Arabic) - احتفظ بالمصطلحات الطبية بالإنجليزية واشرحها بالعربية المصرية للفهم الجيد",
            "question_category": "critical_thinking",
            "cognitive_level": "analyze"
        }},
        {{
            "question_type": "text",
            "question": "Third question text",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_answer": 3,
            "explanation_en": "Detailed explanation (English)",
            "explanation_ar": "شرح تفصيلي (Egyptian Arabic) - احتفظ بالمصطلحات الطبية بالإنجليزية واشرحها بالعربية المصرية للفهم الجيد",
            "question_category": "linking",
            "cognitive_level": "understand"
        }}
    ]
}}

NOTE: The examples above show correct_answer values of 2, 0, and 3. Make sure to use ALL four indices (0, 1, 2, 3) randomly across your questions.

COGNITIVE LEVELS:
• remember: Recall facts
• understand: Explain concepts
• apply: Use knowledge in new situations
• analyze: Break down and examine
• evaluate: Make judgments and assessments
• create: Generate new ideas or solutions

Begin generation now. Return ONLY the JSON object."""


def get_true_false_prompt(
    count,
    topic,
    current_difficulty_guide,
    standard_count,
    critical_count,
    linking_count,
    notes_context,
    previous_context,
):
    return f"""Generate {count} UNIQUE True/False questions about: {topic}

{current_difficulty_guide}

EXACT DISTRIBUTION REQUIRED:
├─ Standard Questions: {standard_count} questions
├─ Critical Thinking Questions: {critical_count} questions
└─ Linking Questions: {linking_count} questions
   TOTAL: {count} questions

{notes_context}{previous_context}

TRUE/FALSE REQUIREMENTS:
✓ Statements must be clear and unambiguous
✓ Avoid trick questions or double negatives
✓ Balance True and False answers approximately 50/50 (use both 0 and 1 for correct_answer)
✓ Statements should test real understanding, not just memorization
✓ For critical thinking: require analysis of implications
✓ For linking: make statements that connect concepts

OUTPUT FORMAT (JSON ONLY):
{{
    "questions": [
        {{
            "question_type": "text",
            "question": "First True/False statement",
            "options": ["True", "False"],
            "correct_answer": 1,
            "explanation_en": "Why this is false with supporting details (English)",
            "explanation_ar": "لماذا هذا خطأ مع التفاصيل الداعمة (Egyptian Arabic) - احتفظ بالمصطلحات الطبية بالإنجليزية واشرحها بالعربية المصرية للفهم الجيد",
            "question_category": "standard",
            "cognitive_level": "remember"
        }},
        {{
            "question_type": "text",
            "question": "Second True/False statement",
            "options": ["True", "False"],
            "correct_answer": 0,
            "explanation_en": "Why this is true with supporting details (English)",
            "explanation_ar": "لماذا هذا صحيح مع التفاصيل الداعمة (Egyptian Arabic) - احتفظ بالمصطلحات الطبية بالإنجليزية واشرحها بالعربية المصرية للفهم الجيد",
            "question_category": "critical_thinking",
            "cognitive_level": "analyze"
        }}
    ]
}}

NOTE: Mix True (0) and False (1) answers evenly across questions.

QUALITY EXAMPLES:
Standard: "The mitochondria is known as the powerhouse of the cell."
Critical: "If all mitochondria in a cell were destroyed, the cell would eventually die due to lack of energy."
Linking: "The process of cellular respiration in mitochondria is essentially the reverse of photosynthesis in chloroplasts."

Begin generation now. Return ONLY the JSON object."""


def get_essay_prompt(
    count,
    topic,
    current_difficulty_guide,
    standard_count,
    critical_count,
    linking_count,
    notes_context,
    previous_context,
):
    return f"""Generate {count} UNIQUE essay/short answer questions about: {topic}

{current_difficulty_guide}

EXACT DISTRIBUTION REQUIRED:
├─ Standard Questions: {standard_count} questions (explain, describe, define)
├─ Critical Thinking Questions: {critical_count} questions (analyze, evaluate, argue)
└─ Linking Questions: {linking_count} questions (compare, synthesize, relate)
   TOTAL: {count} questions

{notes_context}{previous_context}

ESSAY QUESTION REQUIREMENTS:
✓ Vary length requirements: full essays, paragraphs, short answers
✓ Clear expectations for what should be included
✓ Specific grading criteria
✓ Key points that strong answers should cover

OUTPUT FORMAT (JSON ONLY):
{{
    "questions": [
        {{
            "question_type": "text",
            "question": "Open-ended question requiring written response",
            "key_points": [
                "First key concept to address",
                "Second important point",
                "Third critical element"
            ],
            "suggested_length": "2-3 paragraphs",
            "grading_criteria": "What makes a complete and excellent answer",
            "question_category": "standard",
            "cognitive_level": "understand"
        }}
    ]
}}

LENGTH OPTIONS:
• "One word or phrase" - for simple identification
• "1-2 sentences" - for brief definitions
• "1 paragraph" - for explanations
• "2-3 paragraphs" - for full short essays
• "4-5 paragraphs" - for comprehensive essays

Begin generation now. Return ONLY the JSON object."""


def get_mixed_prompt(
    count,
    topic,
    current_difficulty_guide,
    standard_count,
    critical_count,
    linking_count,
    mcq_count,
    tf_count,
    notes_context,
    previous_context,
):
    return f"""Generate {count} UNIQUE MIXED questions (MCQ + True/False) about: {topic}

{current_difficulty_guide}

EXACT DISTRIBUTION REQUIRED:
├─ Standard Questions: {standard_count} questions
├─ Critical Thinking Questions: {critical_count} questions
└─ Linking Questions: {linking_count} questions
   TOTAL: {count} questions

QUESTION TYPE MIX:
├─ Multiple Choice (4 options): approximately {mcq_count} questions
└─ True/False (2 options): approximately {tf_count} questions

{notes_context}{previous_context}

OUTPUT FORMAT (JSON ONLY):
{{
    "questions": [
        {{
            "question_type": "text",
            "question": "MCQ question text",
            "options": ["A", "B", "C", "D"],
            "correct_answer": 1,
            "explanation_en": "Detailed explanation (English)",
            "explanation_ar": "شرح تفصيلي (Egyptian Arabic) - احتفظ بالمصطلحات الطبية بالإنجليزية واشرحها بالعربية المصرية للفهم الجيد",
            "question_category": "standard",
            "cognitive_level": "remember"
        }},
        {{
            "question_type": "text",
            "question": "True/False question text",
            "options": ["True", "False"],
            "correct_answer": 0,
            "explanation_en": "Detailed explanation (English)",
            "explanation_ar": "شرح تفصيلي (Egyptian Arabic) - احتفظ بالمصطلحات الطبية بالإنجليزية واشرحها بالعربية المصرية للفهم الجيد",
            "question_category": "critical_thinking",
            "cognitive_level": "analyze"
        }}
    ]
}}

NOTE: For MCQ questions, randomize correct_answer across ALL indices (0, 1, 2, 3). For T/F, balance between 0 and 1.

Mix MCQ and T/F questions intelligently throughout the set.

Begin generation now. Return ONLY the JSON object."""


def get_summarize_system_message():
    return "You are an expert at summarizing educational content while preserving key information."


def get_summarize_prompt(content, max_length):
    length_instruction = f" in about {max_length} words" if max_length else ""
    return f"Summarize the following content{length_instruction}:\n\n{content}"


def get_explain_concept_system_message(level, language):
    language_instructions = {
        "en": "Respond in English.",
        "ar": "Respond in Arabic (Egyptian dialect). Use clear Arabic language suitable for Egyptian students.",
    }
    lang_instruction = language_instructions.get(language, language_instructions["en"])
    return f"You are a skilled teacher explaining concepts to {level} level students. Use clear language and examples. {lang_instruction}"


def get_explain_concept_prompt(concept, level):
    return f"Explain the following concept in a way that a {level} level student would understand:\n\n{concept}"


def get_pdf_essay_prompt(
    count,
    current_difficulty_guide,
    standard_count,
    critical_count,
    linking_count,
    notes_context,
    previous_context,
    pdf_content,
):
    return f"""Based on the following content, generate {count} UNIQUE essay/short answer questions.

{current_difficulty_guide}

EXACT DISTRIBUTION REQUIRED:
├─ Standard Questions: {standard_count} questions
├─ Critical Thinking Questions: {critical_count} questions
└─ Linking Questions: {linking_count} questions
   TOTAL: {count} questions

{notes_context}{previous_context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📄 CONTENT TO ANALYZE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{pdf_content}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ESSAY REQUIREMENTS:
✓ Questions must be answerable primarily using the provided content
✓ Grading criteria must reference specific details from the text
✓ Vary question scope (specific details vs. broad themes)

OUTPUT FORMAT (JSON ONLY):
{{
    "questions": [
        {{
            "question_type": "text",
            "question": "Essay/short answer question based on content",
            "key_points": ["Point 1 from text", "Point 2 from text", "Point 3 from text"],
            "suggested_length": "2-3 paragraphs",
            "grading_criteria": "Specific criteria based on source text",
            "question_category": "standard",
            "cognitive_level": "understand"
        }}
    ]
}}

Begin generation now. Return ONLY the JSON object."""


def get_pdf_mixed_prompt(
    count,
    current_difficulty_guide,
    standard_count,
    critical_count,
    linking_count,
    mcq_count,
    tf_count,
    notes_context,
    previous_context,
    pdf_content,
):
    return f"""Based on the following content, generate {count} UNIQUE MIXED questions.

{current_difficulty_guide}

EXACT DISTRIBUTION REQUIRED:
├─ Standard Questions: {standard_count} questions
├─ Critical Thinking Questions: {critical_count} questions
└─ Linking Questions: {linking_count} questions

TYPE MIX:
├─ MCQ (4 options): ~{mcq_count} questions
└─ True/False: ~{tf_count} questions

{notes_context}{previous_context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📄 CONTENT TO ANALYZE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{pdf_content}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OUTPUT FORMAT (JSON ONLY):
{{
    "questions": [
        {{
            "question_type": "text",
            "question": "MCQ question text based on content",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_answer": 2,
            "explanation_en": "Explanation citing the text (English)",
            "explanation_ar": "شرح مع الإشارة للنص (Egyptian Arabic)",
            "question_category": "standard",
            "cognitive_level": "remember"
        }},
        {{
            "question_type": "text",
            "question": "True/False question text based on content",
            "options": ["True", "False"],
            "correct_answer": 1,
            "explanation_en": "Explanation citing the text (English)",
            "explanation_ar": "شرح مع الإشارة للنص (Egyptian Arabic)",
            "question_category": "critical_thinking",
            "cognitive_level": "analyze"
        }}
    ]
}}

NOTE: For MCQ, randomize correct_answer across ALL indices (0, 1, 2, 3). For T/F, balance between 0 and 1.

Begin generation now. Return ONLY the JSON object."""


def get_pdf_true_false_prompt(
    count,
    current_difficulty_guide,
    standard_count,
    critical_count,
    linking_count,
    notes_context,
    previous_context,
    pdf_content,
):
    return f"""Based on the following content, generate {count} UNIQUE True/False questions.

{current_difficulty_guide}

EXACT DISTRIBUTION REQUIRED:
├─ Standard Questions: {standard_count} questions
├─ Critical Thinking Questions: {critical_count} questions
└─ Linking Questions: {linking_count} questions

{notes_context}{previous_context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📄 CONTENT TO ANALYZE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{pdf_content}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TRUE/FALSE REQUIREMENTS:
✓ Statements must be derived directly from the text or logical inferences from it
✓ Avoid outside knowledge not supported by the text
✓ Explanations must reference *why* the text supports/refutes the statement
✓ Balance True (0) and False (1) answers evenly

OUTPUT FORMAT (JSON ONLY):
{{
    "questions": [
        {{
            "question_type": "text",
            "question": "First statement based on text",
            "options": ["True", "False"],
            "correct_answer": 1,
            "explanation_en": "Evidence from text (English)",
            "explanation_ar": "الدليل من النص (Egyptian Arabic) - احتفظ بالمصطلحات الطبية بالإنجليزية واشرحها بالعربية المصرية للفهم الجيد",
            "question_category": "standard",
            "cognitive_level": "remember"
        }},
        {{
            "question_type": "text",
            "question": "Second statement based on text",
            "options": ["True", "False"],
            "correct_answer": 0,
            "explanation_en": "Evidence from text (English)",
            "explanation_ar": "الدليل من النص (Egyptian Arabic) - احتفظ بالمصطلحات الطبية بالإنجليزية واشرحها بالعربية المصرية للفهم الجيد",
            "question_category": "critical_thinking",
            "cognitive_level": "analyze"
        }}
    ]
}}

NOTE: Mix True (0) and False (1) answers evenly.

Begin generation now. Return ONLY the JSON object."""


def get_pdf_mcq_prompt(
    count,
    current_difficulty_guide,
    standard_count,
    critical_count,
    linking_count,
    notes_context,
    previous_context,
    pdf_content,
):
    return f"""Based on the following content, generate {count} UNIQUE multiple choice questions.

{current_difficulty_guide}

EXACT DISTRIBUTION REQUIRED:
├─ Standard Questions: {standard_count} questions
├─ Critical Thinking Questions: {critical_count} questions
└─ Linking Questions: {linking_count} questions

{notes_context}{previous_context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📄 CONTENT TO ANALYZE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{pdf_content}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MCQ REQUIREMENTS:
✓ Questions must be answerable *strictly* using the provided content
✓ Distractors should be plausible misinterpretations of the text
✓ Explanations should quote or reference the specific part of the text
✓ IMPORTANT: Randomize correct answer position - use ALL indices (0, 1, 2, 3), NOT just 0 or 1

OUTPUT FORMAT (JSON ONLY):
{{
    "questions": [
        {{
            "question_type": "text",
            "question": "First question based on content",
            "options": ["A", "B", "C", "D"],
            "correct_answer": 3,
            "explanation_en": "Explanation citing the text (English)",
            "explanation_ar": "شرح مع الإشارة للنص (Egyptian Arabic)",
            "question_category": "standard",
            "cognitive_level": "remember"
        }},
        {{
            "question_type": "text",
            "question": "Second question based on content",
            "options": ["A", "B", "C", "D"],
            "correct_answer": 1,
            "explanation_en": "Explanation citing the text (English)",
            "explanation_ar": "شرح مع الإشارة للنص (Egyptian Arabic)",
            "question_category": "critical_thinking",
            "cognitive_level": "analyze"
        }}
    ]
}}

NOTE: Use ALL four indices (0, 1, 2, 3) randomly across your questions.

Begin generation now. Return ONLY the JSON object."""


def get_pdf_path_essay_prompt(
    count,
    current_difficulty_guide,
    standard_count,
    critical_count,
    linking_count,
    notes_context,
    previous_context,
    pdf_content,
):
    return f"""Based on the content below, generate {count} UNIQUE essay questions.
            
{current_difficulty_guide}
Distribution: {standard_count} Standard, {critical_count} Critical, {linking_count} Linking.
{notes_context}{previous_context}

CONTENT:
{pdf_content}

Format as JSON:
{{
    "questions": [
        {{
            "question_type": "text",
            "question": "Essay question",
            "key_points": ["Point 1", "Point 2"],
            "suggested_length": "Length",
            "grading_criteria": "Criteria",
            "question_category": "standard",
            "cognitive_level": "understand"
        }}
    ]
}}"""


def get_pdf_path_true_false_prompt(
    count,
    current_difficulty_guide,
    standard_count,
    critical_count,
    linking_count,
    notes_context,
    previous_context,
    pdf_content,
):
    return f"""Based on the content below, generate {count} UNIQUE True/False questions.

{current_difficulty_guide}
Distribution: {standard_count} Standard, {critical_count} Critical, {linking_count} Linking.
{notes_context}{previous_context}

CONTENT:
{pdf_content}

Format as JSON:
{{
    "questions": [
        {{
            "question_type": "text",
            "question": "First statement",
            "options": ["True", "False"],
            "correct_answer": 1,
            "explanation_en": "Explanation (English)",
            "explanation_ar": "شرح (Egyptian Arabic) - احتفظ بالمصطلحات الطبية بالإنجليزية واشرحها بالعربية المصرية للفهم الجيد",
            "question_category": "standard",
            "cognitive_level": "remember"
        }},
        {{
            "question_type": "text",
            "question": "Second statement",
            "options": ["True", "False"],
            "correct_answer": 0,
            "explanation_en": "Explanation (English)",
            "explanation_ar": "شرح (Egyptian Arabic) - احتفظ بالمصطلحات الطبية بالإنجليزية واشرحها بالعربية المصرية للفهم الجيد",
            "question_category": "critical_thinking",
            "cognitive_level": "analyze"
        }}
    ]
}}

NOTE: Balance True (0) and False (1) answers evenly."""


def get_pdf_path_mixed_prompt(
    count,
    current_difficulty_guide,
    standard_count,
    critical_count,
    linking_count,
    notes_context,
    previous_context,
    pdf_content,
):
    return f"""Based on the content below, generate {count} UNIQUE MIXED questions (MCQ + T/F).

{current_difficulty_guide}
Distribution: {standard_count} Standard, {critical_count} Critical, {linking_count} Linking.
{notes_context}{previous_context}

CONTENT:
{pdf_content}

Format as JSON:
{{
    "questions": [
        {{
            "question_type": "text",
            "question": "MCQ question",
            "options": ["Option A", "Option B", "Option C", "Option D"], 
            "correct_answer": 2,
            "explanation_en": "Explanation (English)",
            "explanation_ar": "شرح (Egyptian Arabic) - احتفظ بالمصطلحات الطبية بالإنجليزية واشرحها بالعربية المصرية للفهم الجيد",
            "question_category": "standard",
            "cognitive_level": "remember"
        }},
        {{
            "question_type": "text",
            "question": "True/False question",
            "options": ["True", "False"],
            "correct_answer": 1,
            "explanation_en": "Explanation (English)",
            "explanation_ar": "شرح (Egyptian Arabic) - احتفظ بالمصطلحات الطبية بالإنجليزية واشرحها بالعربية المصرية للفهم الجيد",
            "question_category": "critical_thinking",
            "cognitive_level": "analyze"
        }}
    ]
}}

NOTE: For MCQ, use ALL indices (0, 1, 2, 3). For T/F, balance between 0 and 1."""


def get_pdf_path_mcq_prompt(
    count,
    current_difficulty_guide,
    standard_count,
    critical_count,
    linking_count,
    notes_context,
    previous_context,
    pdf_content,
):
    return f"""Based on the content below, generate {count} UNIQUE Multiple Choice questions.

{current_difficulty_guide}
Distribution: {standard_count} Standard, {critical_count} Critical, {linking_count} Linking.
{notes_context}{previous_context}

CONTENT:
{pdf_content}

Format as JSON:
{{
    "questions": [
        {{
            "question_type": "text",
            "question": "First question",
            "options": ["A", "B", "C", "D"],
            "correct_answer": 3,
            "explanation_en": "Explanation (English)",
            "explanation_ar": "شرح (Egyptian Arabic) - احتفظ بالمصطلحات الطبية بالإنجليزية واشرحها بالعربية المصرية للفهم الجيد",
            "question_category": "standard",
            "cognitive_level": "remember"
        }},
        {{
            "question_type": "text",
            "question": "Second question",
            "options": ["A", "B", "C", "D"],
            "correct_answer": 1,
            "explanation_en": "Explanation (English)",
            "explanation_ar": "شرح (Egyptian Arabic) - احتفظ بالمصطلحات الطبية بالإنجليزية واشرحها بالعربية المصرية للفهم الجيد",
            "question_category": "critical_thinking",
            "cognitive_level": "analyze"
        }}
    ]
}}

NOTE: Randomize correct_answer across ALL indices (0, 1, 2, 3)."""


def get_explanation_system_message():
    return """You are an expert medical educator explaining content to Egyptian students.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 EXPLANATION REQUIREMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. LANGUAGE: Explain in Egyptian Arabic dialect only (اللغة المصرية العامية)
2. MEDICAL TERMS: Keep all medical and scientific terms in English as they are, and BOLD them with **asterisks**
   ✓ Examples: "**diabetes**", "**hypertension**", "**myocardial infarction**", "**electrocardiogram**"
   ✓ Do NOT translate these terms - keep them in English and bold them
   ✓ Bold ALL medical/scientific terms: "**monosaccharides**", "**homeostasis**", "**glucose**", etc.

3. CLARITY: Use simple, clear Egyptian Arabic that students understand
4. STRUCTURE: Explain concepts step by step with logical flow
5. EXAMPLES: Include practical examples when relevant
6. CONNECTIONS: Show how concepts relate to each other

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 EGYPTIAN ARABIC STYLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Use natural Egyptian Arabic like:
✓ "يعني" (means)
✓ "مثلاً" (for example)
✓ "المهم" (important)
✓ "لو عايز تفهم" (if you want to understand)
✓ "المشكلة إن" (the problem is)
✓ "السبب" (the reason)

⚠️ IMPORTANT: Start directly with the explanation content. DO NOT use conversational openers like:
- "طيب يا جماعة" (Okay guys)
- "هاشرحلكم" (Let me explain to you)
- "في الصفحة دي" (In this page)
- "محتوى الصفحة" (Page content)
- Any phrases that reference "the page" or introduce the explanation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📤 OUTPUT FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Return ONLY a JSON object with this exact structure:
{
    "pages": [
        {
            "page_number": 1,
            "explanation": "الشرح بالعربية المصرية هنا..."
        },
        {
            "page_number": 2,
            "explanation": "الشرح بالعربية المصرية هنا..."
        }
    ]
}

⚠️ IMPORTANT: Return ONLY the JSON object, no additional text or markdown."""


def get_explanation_prompt(
    detail_instruction, examples_instruction, merged_content, page_numbers
):
    return f"""{detail_instruction} للمحتوى ده بالعربية المصرية بس، وابقِ المصطلحات الطبية زي ما هي بالإنجليزية{examples_instruction}:

{merged_content}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

المطلوب: شرح واضح ومفيد للطلاب المصريين لكل صفحة.

أرجع JSON فيه شرح لكل صفحة من الصفحات: {page_numbers}

الformat المطلوب:
{{
    "pages": [
        {{"page_number": رقم_الصفحة, "explanation": "الشرح هنا..."}}
    ]
}}"""


def get_teaching_greeting_system_message(language, user_name, session_type):
    if language == "ar":
        student_name_instruction = (
            f"\n\nاسم الطالب: {user_name}\nاستخدم اسم الطالب في الترحيب."
            if user_name
            else ""
        )

        if session_type == "explaining":
            return f"""أنت معلم خبير ودود. مهمتك هي الترحيب بالطالب وشرح المحتوى له بطريقة واضحة خطوة بخطوة.{student_name_instruction}

            قواعد مهمة:
            - رحب بالطالب بطريقة ودية
            - اشرح أنك ستشرح له المحتوى بالتفصيل خطوة بخطوة
            - ابدأ بشرح الصفحة الأولى من المحتوى بالتفصيل
            - اشرح صفحة واحدة في كل مرة
            - بعد شرح كل صفحة، اسأل الطالب إذا كان مستعد للانتقال للصفحة التالية
            - احتفظ بالمصطلحات الطبية والعلمية باللغة الإنجليزية مع الشرح بالعربية المصرية
            - استخدم **نجمتين** حول المصطلحات الطبية
            - استخدم أمثلة توضيحية عند الحاجة

            أسلوب التحية:
            - طبيعي وودي
            - محفز ومشجع
            - مباشر للموضوع
            - ابدأ بشرح الصفحة الأولى فوراً بعد الترحيب"""
        else:  # asking session
            return f"""أنت معلم خبير ودود. مهمتك هي الترحيب بالطالب وبدء جلسة تعليمية تفاعلية.{student_name_instruction}

قواعد مهمة:
- رحب بالطالب بطريقة ودية
- اشرح أنك ستساعده في فهم المحتوى من خلال طرح أسئلة
- اسأل سؤالًا بسيطًا أو متوسطًا عن المحتوى للبدء
- احتفظ بالمصطلحات الطبية والعلمية باللغة الإنجليزية مع الشرح بالعربية المصرية
- استخدم **نجمتين** حول المصطلحات الطبية

أسلوب التحية:
- طبيعي وودي
- محفز ومشجع
- مباشر للموضوع"""
    else:  # English
        student_name_instruction = (
            f"\n\nStudent's name: {user_name}\nUse the student's name in the greeting."
            if user_name
            else ""
        )

        if session_type == "explaining":
            return f"""You are a friendly expert teacher. Your task is to welcome the student and start explaining the content step by step.{student_name_instruction}

Important rules:
- Greet the student in a friendly manner
- Explain that you'll explain the content in detail step by step
- Start by explaining the first page of the content immediately after greeting
- Explain one page at a time
- After each page, ask if they're ready to move to the next page
- Keep medical and scientific terms in English and **bold them**
- Be encouraging and supportive
- Use examples when needed

Greeting style:
- Natural and friendly
- Motivating and encouraging
- Straight to the topic
- Begin explaining the first page right after the welcome"""
        else:  # asking session
            return f"""You are a friendly expert teacher. Your task is to welcome the student and start an interactive learning session.{student_name_instruction}

Important rules:
- Greet the student in a friendly manner
- Explain that you'll help them understand the content through questions
- Ask a simple to medium difficulty question about the content to start
- Keep medical and scientific terms in English and **bold them**
- Be encouraging and supportive

Greeting style:
- Natural and friendly
- Motivating and encouraging
- Straight to the topic"""


def get_teaching_greeting_prompt(language, content_preview, session_type):
    if language == "ar":
        if session_type == "explaining":
            return f"""رحب بالطالب وابدأ بشرح الصفحة الأولى من المحتوى التالي خطوة بخطوة:

{content_preview}

ابدأ بترحيب قصير ثم ابدأ فوراً بشرح الصفحة الأولى بالتفصيل خطوة بخطوة."""
        else:
            return f"""رحب بالطالب واسأله سؤالًا عن هذا المحتوى:

{content_preview}

ابدأ بترحيب قصير ثم اطرح سؤالًا واحدًا لاختبار الفهم الأساسي."""
    else:
        if session_type == "explaining":
            return f"""Welcome the student and start explaining the first page of the following content step by step:

            {content_preview}

            Start with a brief welcome, then immediately begin explaining the first page in detail, step by step."""
        else:
            return f"""Welcome the student and ask them a question about this content:

{content_preview}

Start with a brief welcome, then ask ONE question to test basic understanding."""


def get_teaching_response_system_message(language, user_name, session_type):
    if language == "ar":
        student_name_instruction = (
            f"\n\n👤 اسم الطالب: {user_name}\nاستخدم اسم الطالب بشكل طبيعي في المحادثة لجعلها أكثر شخصية وودية."
            if user_name
            else ""
        )

        if session_type == "explaining":
            return f"""أنت معلم خبير تشرح المحتوى للطالب بطريقة واضحة ومبسطة صفحة بصفحة.{student_name_instruction}

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    🎯 دورك كمعلم (شرح المحتوى)
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    1. **الشرح خطوة بخطوة**: اشرح المحتوى صفحة بصفحة بالترتيب
    2. **ابدأ بالصفحة الأولى**: ابدأ دائماً بشرح الصفحة الأولى من المحتوى بالتفصيل
    3. **صفحة واحدة في كل مرة**: ركز على شرح صفحة واحدة فقط ثم اسأل الطالب إذا كان مستعد للانتقال للصفحة التالية
    4. **الشرح الواضح**: اشرح كل صفحة بطريقة مبسطة وواضحة
    5. **الإجابة على الأسئلة**: أجب على أسئلة الطالب بدقة من المحتوى المتاح
    6. **الأمثلة التوضيحية**: استخدم أمثلة عند الحاجة لتوضيح الأفكار

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    📋 قواعد مهمة
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    ✓ احتفظ بالمصطلحات الطبية والعلمية بالإنجليزية
    ✓ استخدم **نجمتين** حول المصطلحات الطبية
    ✓ اشرح بالعربية المصرية البسيطة
    ✓ كن ودودًا ومشجعًا
    ✓ إذا لم يكن المحتوى المتاح كافيًا، قل ذلك بوضوح
    ✓ لا تخترع معلومات غير موجودة في المحتوى
    ✓ قدم شرح كامل وواضح لكل صفحة
    ✓ لا تنتقل للصفحة التالية إلا بعد موافقة الطالب

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    🔄 تدفق المحادثة (الترتيب مهم)
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    **الرسالة الأولى:**
    1. رحب بالطالب
    2. ابدأ فوراً بشرح الصفحة الأولى بالكامل والتفصيل
    3. بعد الانتهاء من شرح الصفحة الأولى، اسأل: "فهمت الصفحة الأولى؟ مستعد ننتقل للصفحة التالية؟"

    **الرسائل التالية:**
    1. إذا سأل الطالب سؤال عن الصفحة الحالية: أجب بالتفصيل
    2. إذا قال الطالب إنه مستعد للصفحة التالية: انتقل للصفحة التالية واشرحها بالكامل
    3. بعد كل صفحة، اسأل: "فهمت صفحة X؟ مستعد للصفحة التالية؟"
    4. إذا طلب توضيح نقطة معينة: وضح له بالتفصيل
    5. إذا طلب أمثلة: قدم أمثلة توضيحية

    مثال للأسئلة التفاعلية:
    - "فهمت الصفحة دي كويس؟ جاهز ننتقل للصفحة اللي بعدها؟"
    - "في نقطة في الصفحة دي تحب أشرحها أكتر؟"
    - "عايز أمثلة إضافية على موضوع معين من الصفحة؟"
    """
        else:  # asking session
            return f"""أنت معلم خبير تساعد الطالب على فهم المحتوى من خلال محادثة تفاعلية.{student_name_instruction}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 دورك كمعلم
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. **الإجابة على الأسئلة**: استخدم المحتوى المتاح للإجابة بدقة
2. **الشرح عند عدم المعرفة**: إذا لم يعرف الطالب الإجابة، اشرح النقطة بوضوح
3. **طرح أسئلة المتابعة**: اسأل أسئلة لاختبار الفهم
4. **التوجيه**: اسأل الطالب إذا كان يريد:
   - الاستمرار في الأسئلة
   - شرح نقاط معينة بالتفصيل
   - مراجعة أجزاء من المحتوى

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 قواعد مهمة
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ احتفظ بالمصطلحات الطبية والعلمية بالإنجليزية
✓ استخدم **نجمتين** حول المصطلحات الطبية
✓ اشرح بالعربية المصرية البسيطة
✓ كن ودودًا ومشجعًا
✓ إذا لم يكن المحتوى المتاح كافيًا، قل ذلك بوضوح
✓ لا تخترع معلومات غير موجودة في المحتوى

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ قواعد تقييم الإجابات (مهم جداً)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

عند سؤال الطالب:

❌ لا تقبل إجابات مبهمة أو غير واضحة مثل:
   - "أيوة أنا عارف"
   - "نعم أعرف الإجابة"
   - "طبعاً"
   - "أكيد"
   - "بالتأكيد"
   - "فاهم"
   - نقاط أو رموز فقط مثل: "...", ".....", "......", "???", "!!!"
   - رموز تعبيرية فقط
   - أي رد لا يحتوي على كلمات واضحة

✅ اقبل فقط:
   1. إجابة محددة تحتوي على المعلومة الصحيحة
   2. "مش عارف" أو "لا أعرف" أو ما يشبهها

🔄 إذا أجاب الطالب بشكل مبهم أو بنقاط/رموز فقط:
   - قل له بوضوح: "محتاج تكتب إجابة واضحة، مش نقاط أو رموز. ⌨️"
   - اطلب منه إما كتابة الإجابة المحددة أو قول "مش عارف"
   - مثال: "عايزك تكتب إجابتك بكلمات واضحة، أو لو مش عارف قول 'مش عارف'. إيه الإجابة؟"
   - كرر نفس السؤال
   - لا تنتقل لسؤال جديد حتى يجيب بشكل محدد أو يقول "مش عارف"

✏️ تصحيح الأخطاء الإملائية:
   - إذا كتب الطالب كلمة بشكل خاطئ لكن المفهوم صحيح:
     * اقبل الإجابة واعتبرها صحيحة
     * نبّه بلطف على الخطأ الإملائي
     * مثال: "ممتاز! الإجابة صحيحة. ✓ بس ملحوظة بسيطة: الكتابة الصحيحة هي **BiConcave** مش Bycancave"
   - إذا كان الخطأ الإملائي يغير المعنى تماماً، وضح الفرق

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 تدفق المحادثة
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. أجب على سؤال الطالب أو قيّم إجابته
2. إذا أجاب بشكل صحيح ومحدد: امدحه واشرح المزيد ثم انتقل لسؤال جديد
3. إذا أجاب بشكل مبهم (مثل "أيوة عارف"): اطلب منه الإجابة المحددة وكرر نفس السؤال
4. إذا أجاب بشكل خاطئ أو قال "مش عارف": اشرح الإجابة الصحيحة ثم اسأل سؤال جديد

مثال للأسئلة التوجيهية:
- "هل تحب نكمل في أسئلة تانية؟"
- "في نقطة معينة عايز أشرحها أكتر؟"
- "جاهز للسؤال التالي؟"
"""
    else:  # English
        student_name_instruction = (
            f"\n\n👤 Student's Name: {user_name}\nUse the student's name naturally in the conversation to make it more personal and friendly."
            if user_name
            else ""
        )
        return f"""You are an expert teacher helping the student understand content through interactive conversation.{student_name_instruction}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 Your Role as Teacher
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. **Answer Questions**: Use the available content to answer accurately
2. **Explain When Unknown**: If student doesn't know, explain the point clearly
3. **Ask Follow-up Questions**: Test understanding with questions
4. **Provide Guidance**: Ask the student if they want to:
   - Continue with more questions
   - Explain specific points in detail
   - Review parts of the content

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Important Rules
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ Keep medical and scientific terms in English
✓ **Bold** medical terms with asterisks
✓ Explain in simple, clear English
✓ Be friendly and encouraging
✓ If available content is insufficient, say so clearly
✓ Don't make up information not in the content

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ Answer Validation Rules (CRITICAL)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

When asking the student a question:

❌ Do NOT accept vague or unclear responses like:
   - "Yes I know it"
   - "Of course"
   - "Sure"
   - "Definitely"
   - "I understand"
   - "Yeah I got it"
   - Only dots or symbols like: "...", ".....", "......", "???", "!!!"
   - Only emojis
   - Any response without clear words

✅ Only accept:
   1. A specific answer containing the actual information
   2. "I don't know" or similar explicit admission

🔄 If student gives a vague response or only dots/symbols:
   - Say clearly: "I need you to type a clear answer, not dots or symbols. ⌨️"
   - Ask them to either write the specific answer or say "I don't know"
   - Example: "Please type your answer in clear words, or if you don't know, just say 'I don't know'. What's the answer?"
   - Repeat the same question
   - Do NOT move to a new question until they provide specific answer or say "I don't know"

✏️ Spelling Correction:
   - If the student writes a word incorrectly but the concept is right:
     * Accept the answer as correct
     * Gently note the spelling error
     * Example: "Excellent! Your answer is correct. ✓ Just a small note: the correct spelling is **BiConcave** not Bycancave"
   - If the spelling error completely changes the meaning, clarify the difference

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔥 Progressive Difficulty (CRITICAL)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 Make questions progressively harder based on performance:

✅ When answer is correct:
   - Praise the student
   - Elaborate with more details
   - Ask a HARDER question about same topic:
     * "Why does this happen?" instead of "What is it?"
     * Clinical cases and practical applications
     * Connect multiple concepts
     * Analysis and comparisons

❌ When answer is wrong:
   - Explain the correct answer
   - Ask a SIMPLE or MEDIUM question about another topic
   - Do NOT increase difficulty after mistakes

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 Conversation Flow
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Respond to student's question or evaluate their answer
2. If correct and specific answer: Praise, elaborate, then ask HARDER question
3. If vague answer (like "Yes I know") or only dots/symbols: Ask for specific answer and repeat same question
4. If wrong or says "I don't know": Explain the correct answer, then ask SIMPLE question

Example guidance questions:
- "Would you like to continue with more questions?"
- "Is there any specific point you'd like me to explain further?"
- "Ready for the next question?"
"""


def get_teaching_response_prompt(language, truncated_content, user_message):
    if language == "ar":
        return f"""المحتوى المصدر:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{truncated_content}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

رسالة الطالب الحالية: {user_message}

رد كمعلم بناءً على المحتوى والمحادثة السابقة. احتفظ بالمصطلحات الطبية بالإنجليزية مع وضع **نجمتين** حولها."""
    else:
        return f"""Source Content:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{truncated_content}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Current student message: {user_message}

Respond as a teacher based on the content and previous conversation. Keep medical terms in English and **bold them**."""


def get_topic_explanation_system_message():
    return """You are an expert medical educator explaining topics to Egyptian students.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 EXPLANATION REQUIREMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. LANGUAGE: Explain in Egyptian Arabic dialect only (اللغة المصرية العامية)
2. MEDICAL TERMS: Keep all medical and scientific terms in English as they are, and BOLD them with **asterisks**
   ✓ Examples: "**diabetes**", "**hypertension**", "**myocardial infarction**", "**electrocardiogram**"
   ✓ Do NOT translate these terms - keep them in English and bold them
   ✓ Bold ALL medical/scientific terms: "**monosaccharides**", "**homeostasis**", "**glucose**", etc.

3. STRUCTURE: Organize explanation by SUBJECTS/SUB-TOPICS, not by pages
4. CLARITY: Use simple, clear Egyptian Arabic that students understand
5. LOGICAL FLOW: Explain concepts step by step with smooth transitions
6. EXAMPLES: Include practical examples when relevant
7. CONNECTIONS: Show how concepts relate to each other

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 EGYPTIAN ARABIC STYLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Use natural Egyptian Arabic like:
✓ "يعني" (means)
✓ "مثلاً" (for example)
✓ "المهم" (important)
✓ "لو عايز تفهم" (if you want to understand)
✓ "المشكلة إن" (the problem is)
✓ "السبب" (the reason)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📤 OUTPUT FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Return ONLY a JSON object with this exact structure:
{
    "topic": "Main topic name",
    "subjects": [
        {
            "subject_title": "First Subject Title",
            "explanation": "Complete explanation of this subject in Egyptian Arabic"
        },
        {
            "subject_title": "Second Subject Title",
            "explanation": "Complete explanation of this subject in Egyptian Arabic"
        }
    ],
    "language": "Egyptian Arabic",
    "medical_terms_preserved": true
}

⚠️ IMPORTANT: 
- Start directly with educational content - NO conversational openers
- Break down the topic into logical SUBJECTS/SUB-TOPICS
- Each subject should have a clear title and comprehensive explanation
- Use **bold** for all medical terms
- Return ONLY the JSON object, no additional text"""


def get_topic_explanation_prompt(
    detail_instruction, examples_instruction, breakdown_instruction, topic
):
    return f"""{detail_instruction} للموضوع الطبي ده بالعربية المصرية بس، وابقِ المصطلحات الطبية زي ما هي بالإنجليزية مع وضع ** حوالين كل مصطلح{examples_instruction}{breakdown_instruction}:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 الموضوع: {topic}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

المطلوب: شرح شامل وواضح للموضوع ده، مقسم لأقسام فرعية منطقية كل قسم له عنوان وشرح كامل.

الأقسام المطلوبة عادة:
• التعريف والمفهوم الأساسي
• الأسباب والعوامل المؤثرة
• الأعراض والعلامات
• التشخيص والفحوصات
• العلاج والإدارة
• المضاعفات والوقاية
• أي أقسام أخرى مهمة متعلقة بالموضوع

شرح كل قسم بالتفصيل بالعربية المصرية، واستخدم ** للتأكيد على المصطلحات الطبية."""


def get_exam_generator_system_prompt(num_questions, type_constraints, difficulty):
    return f"""You are a professional academic examiner. Output ONLY valid JSON.

JSON STRUCTURE:
{{
  "title": "Exam Title",
  "questions": [
    {{
      "question": "Question text here?",
      "answer": "Answer text here",
      "type": "mcq", // MUST be one of: "mcq", "true_false", "essay"
      "difficulty": "medium",
      "options": ["Option A", "Option B", "Option C", "Option D"] // REQUIRED for MCQ, Empty [] for essay or true_false
    }}
  ]
}}

CRITICAL RULES:
1. **QUESTION COUNT**: You MUST generate exactly {num_questions} questions.
2. **SOURCE MATERIAL**: All questions must be strictly derived from the provided content.
3. **TYPE RESTRICTION**: {type_constraints}
4. **MCQ FORMAT**: Must have 4 distinct options. "answer" must match one option EXACTLY.
5. **TRUE/FALSE FORMAT**: Options must be explicitly ["True", "False"].
6. **DIFFICULTY**: Target difficulty level: {difficulty}.

**RULES FOR ESSAY QUESTIONS (STRICT):**
- **CONCISE ANSWERS**: The 'answer' field for essays must be short and direct (Maximum 2-3 sentences).
- **NO FLUFF**: Get straight to the point.
"""


def get_exam_generator_user_prompt(content, num_questions, question_type, difficulty):
    return f"""Create an exam based on this content:
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


# ============================================
# IMAGE-BASED QUESTION PROMPTS
# ============================================


def get_image_question_system_message() -> str:
    """System message for image-based question generation"""
    return """You are an elite educational assessment designer specializing in visual learning materials.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 IMAGE-BASED QUESTION GENERATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Your task is to create questions that test understanding of diagrams, charts, and visual content.

IMPORTANT CRITICAL CONTEXT:
1. The student sees the image with **ALL TEXT/LABELS REMOVED** (hidden).
2. You have access to the original text (OCR) so YOU know what the image shows.
3. The student MUST visually recognize the structure/diagram without reading labels.
4. Do NOT refer to specific labels like "What is label A?" unless you are certain markers exist.
5. Instead, ask them to IDENTIFY the structure shown, or deduce its properties.

GOAL: Test if the student can recognize the visual indications without textual help.

QUESTION TYPES:
• Identification: "The image shows a specific structure. Identify it."
• Description: "Which statement best describes the diagram shown?"
• Function: "What is the primary function of the organelle depicted?"
• Pathology: "What condition is suggested by the visual appearance shown?"

OUTPUT FORMAT:
{
  "questions": [
    {
      "question_type": "image",
      "question_category": "standard|critical|linking",
      "cognitive_level": "remember|understand|analyze|evaluate",
      "question": "Question referencing the image",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": 1,
      "explanation_en": "Why this answer is correct",
      "explanation_ar": "Explanation in Egyptian Arabic"
    }
  ]
}

NOTE: Do NOT include the image in your response. The image will be added automatically.

QUALITY REQUIREMENTS:
✓ Questions must valid even without seeing the original labels
✓ Focus on *visual recognition* and *conceptual understanding*
✓ Use the hidden text to confirm what the subject is, then ask about it
✓ Avoid "What does the text say?" type questions
✓ Maintain proper difficulty level"""


def get_image_question_prompt(
    image_text: str,
    page_text: str,
    page_number: int,
    difficulty: str,
    count: int = 1,
) -> str:
    """
    Generate prompt for creating questions from an image

    Args:
        image_text: OCR extracted text from the image
        page_text: Full text content of the page
        page_number: Page number where image was found
        difficulty: Question difficulty level
        count: Number of questions to generate per image

    Returns:
        Formatted prompt string
    """
    difficulty_guides = {
        "easy": "EASY: Simple identification and recall from the image labels",
        "medium": "MEDIUM: Understanding relationships and functions shown in the image",
        "hard": "HARD: Analysis, synthesis, and application of concepts from the image",
    }

    current_difficulty = difficulty_guides.get(difficulty, difficulty_guides["medium"])

    return f"""Generate {count} high-quality educational question(s) based on this image from page {page_number}.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 IMAGE CONTENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TEXT EXTRACTED FROM IMAGE (Labels, Annotations):
{image_text}

FULL PAGE CONTEXT:
{page_text[:1000]}{"..." if len(page_text) > 1000 else ""}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚙️ GENERATION PARAMETERS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Difficulty: {current_difficulty}
Questions to Generate: {count}
Question Type: Multiple Choice (image-based)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 INSTRUCTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. The provided "TEXT EXTRACTED FROM IMAGE" is HIDDEN from the student
2. Use that hidden text to understand WHAT the image is
3. Create questions that require identifying the subject VISUALLY
4. Include 4 plausible options (A, B, C, D)
5. Provide clear explanations for the correct answer
6. Include Egyptian Arabic explanation with English medical terms

EXAMPLE QUESTION PATTERNS:
✓ "Identify the organ shown in this diagram."
✓ "The medical scan above depicts which condition?"
✓ "What is the primary function of the structure shown?"
✓ "Which of the following characteristics best describes the image content?"

Return ONLY valid JSON. DO NOT include ```json``` markers."""
