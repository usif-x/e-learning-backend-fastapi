# app/utils/ai.py
"""
AI utility for connecting with DeepSeek AI API
Used for generating questions, content, and other educational materials
Enhanced with improved prompts and thinking model support
"""

from app.utils.ai_component.image_utils import (
    process_image,
    remove_text_from_image,
    should_skip_image,
)
from app.utils.ai_component.service import AIService, ai_service

__all__ = [
    "AIService",
    "ai_service",
    "remove_text_from_image",
    "process_image",
    "should_skip_image",
]

