import logging
from app.services.ocr.base import BaseOCRProvider, PageOCRResult, WordBoundingBox

logger = logging.getLogger(__name__)


class CloudOCRProvider(BaseOCRProvider):
    """Cloud OCR provider interface (AWS Textract / Google Vision API stub)"""

    def extract_page_text(self, image_path: str, page_num: int = 1) -> PageOCRResult:
        logger.info(f"Cloud OCR Provider processing page {page_num} for image {image_path}")
        # Stub response matching interface for cloud OCR integration
        return PageOCRResult(
            page_num=page_num,
            text="Cloud OCR Text Extraction Stub",
            confidence=0.95,
            word_boxes=[
                WordBoundingBox(word="Cloud", x=10, y=10, w=50, h=20, confidence=0.99, page_num=page_num),
                WordBoundingBox(word="OCR", x=70, y=10, w=40, h=20, confidence=0.98, page_num=page_num),
                WordBoundingBox(word="Stub", x=120, y=10, w=45, h=20, confidence=0.92, page_num=page_num),
            ]
        )
