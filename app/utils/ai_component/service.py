from app.utils.ai_component.base import BaseAIService
from app.utils.ai_component.general import GeneralGeneratorMixin
from app.utils.ai_component.pdf_images import PDFImageGeneratorMixin
from app.utils.ai_component.pdf_questions import PDFQuestionGeneratorMixin
from app.utils.ai_component.pdf_text import PDFTextProcessorMixin
from app.utils.ai_component.teaching import TeachingAssistantMixin


class AIService(
    BaseAIService,
    GeneralGeneratorMixin,
    PDFTextProcessorMixin,
    PDFQuestionGeneratorMixin,
    TeachingAssistantMixin,
    PDFImageGeneratorMixin,
):
    """
    Service to interact with DeepSeek AI API
    Combines all functionality from mixins
    """

    pass


# Create singleton instance
ai_service = AIService()
