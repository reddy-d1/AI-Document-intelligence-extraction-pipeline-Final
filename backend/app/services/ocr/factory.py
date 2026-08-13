import logging
from app.core.config import settings
from app.services.ocr.base import BaseOCRProvider
from app.services.ocr.tesseract_provider import TesseractOCRProvider
from app.services.ocr.cloud_provider import CloudOCRProvider

logger = logging.getLogger(__name__)


def get_ocr_provider(provider_name: str = None) -> BaseOCRProvider:
    """Factory function returning configured OCR provider instance"""
    name = (provider_name or settings.OCR_PROVIDER or "tesseract").lower()
    
    if name == "cloud":
        logger.info("Initializing Cloud OCR Provider")
        return CloudOCRProvider()
    else:
        logger.info("Initializing Tesseract OCR Provider")
        return TesseractOCRProvider()
